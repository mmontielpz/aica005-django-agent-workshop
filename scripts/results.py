#!/usr/bin/env python3
"""Turn executed checks and participant evidence into reviewable A/B results."""
import csv
import datetime
import hashlib
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORTS = ROOT / 'reports'
BASE = '93e892bb645b16ebaf287beb5fe7f3ffe8d10408'
CHECKS = ('issue_regression', 'forms_media', 'admin_widgets')
DJANGO = ROOT / 'workspace' / 'django'
MAX_EVIDENCE_BYTES = 5 * 1024 * 1024
SECRET_PATTERNS = (
    re.compile(rb'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
    re.compile(rb'gh[pousr]_[A-Za-z0-9]{25,}'),
    re.compile(rb'github_pat_[A-Za-z0-9_]{25,}'),
    re.compile(rb'AKIA[0-9A-Z]{16}'),
    re.compile(rb'Authorization\s*:\s*Bearer\s+\S+', re.I),
)


def git(*args):
    return subprocess.check_output(['git', '-C', str(DJANGO)] + list(args), text=True).strip()


def safe_content(name, content):
    if len(content) > MAX_EVIDENCE_BYTES:
        raise ValueError('Evidence file exceeds 5 MiB: {}'.format(name))
    if any(pattern.search(content) for pattern in SECRET_PATTERNS):
        raise ValueError('Possible credential in evidence file: {}'.format(name))


def candidate_patch():
    numstat = subprocess.check_output(['git', '-C', str(DJANGO), 'diff', '--numstat', 'HEAD'])
    if any(line.split(b'\t', 1)[0] == b'-' for line in numstat.splitlines()):
        raise ValueError('Binary Django changes need manual review before packaging')
    patch = subprocess.check_output(['git', '-C', str(DJANGO), 'diff', '--binary', 'HEAD'])
    paths = subprocess.check_output(['git', '-C', str(DJANGO), 'ls-files', '--others', '--exclude-standard', '-z']).split(b'\0')
    for raw in paths:
        if not raw:
            continue
        relative = os.fsdecode(raw)
        source = DJANGO / relative
        if source.is_symlink() or not source.is_file():
            raise ValueError('Untracked candidate file is not a regular file: {}'.format(relative))
        data = source.read_bytes()
        if b'\0' in data:
            raise ValueError('Binary untracked file needs manual review: {}'.format(relative))
        safe_content(relative, data)
        diff = subprocess.run(['git', 'diff', '--no-index', '--binary', '--', '/dev/null', relative],
                              cwd=str(DJANGO), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if diff.returncode not in (0, 1):
            raise ValueError('Could not capture untracked candidate file: {}'.format(relative))
        patch += diff.stdout
    safe_content('candidate.patch', patch)
    return patch


def package_evidence(run_dir, checks, obs):
    names = ['candidate.patch', 'status.tsv', 'report.md', 'result.json']
    names += [checks[name]['log'] for name in CHECKS]
    if (run_dir / 'observations.json').is_file():
        names.append('observations.json')
    for ref in (obs['transcript_ref'], obs['tokens']['evidence_ref'], obs['tool_calls']['evidence_ref'],
                obs['verification_attempts']['evidence_ref'], obs['cost']['evidence_ref']):
        if ref is not None:
            if pathlib.PurePath(ref).suffix.lower() == '.zip':
                raise ValueError('Nested ZIP evidence is not supported')
            evidence_file(run_dir, ref)
            names.append(ref)
    files = []
    for name in sorted(set(names)):
        path = evidence_file(run_dir, name)
        safe_content(name, path.read_bytes())
        files.append((name, path))
    with tempfile.NamedTemporaryFile(dir=str(run_dir), prefix='.evidence-', suffix='.tmp', delete=False) as stream:
        temporary = pathlib.Path(stream.name)
    try:
        with zipfile.ZipFile(str(temporary), 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, path in files:
                entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, path.read_bytes())
        target = run_dir / 'evidence.zip'
        if target.is_file():
            previous = target.read_bytes()
            if previous == temporary.read_bytes():
                return target
            backup = run_dir / 'evidence-{}.zip'.format(hashlib.sha256(previous).hexdigest()[:12])
            if not backup.exists():
                backup.write_bytes(previous)
        temporary.replace(target)
        return target
    finally:
        if temporary.exists():
            temporary.unlink()


def duration(start, end):
    if start is None and end is None:
        return None
    if not isinstance(start, str) or not isinstance(end, str):
        raise ValueError('Both UTC start and end timestamps are required')
    first = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
    last = datetime.datetime.fromisoformat(end.replace('Z', '+00:00'))
    if first.utcoffset() != datetime.timedelta(0) or last.utcoffset() != datetime.timedelta(0) or last < first:
        raise ValueError('Timestamps must be UTC and end must follow start')
    return round((last - first).total_seconds(), 3)


def evidence_file(run_dir, ref):
    if not isinstance(ref, str) or not ref or '..' in pathlib.PurePath(ref).parts or pathlib.PurePath(ref).is_absolute():
        raise ValueError('Evidence reference must be a file inside the run report directory')
    path = run_dir / ref
    if not path.is_file() or os.path.commonpath((str(run_dir.resolve()), str(path.resolve()))) != str(run_dir.resolve()):
        raise ValueError('Evidence file is missing: {}'.format(run_dir / ref))
    return path


def count(value, label):
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
        raise ValueError('{} must be a nonnegative integer or null'.format(label))
    return value


def observations(run, run_dir):
    path = run_dir / 'observations.json'
    raw = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    if raw and raw.get('run_id') != run:
        raise ValueError('observations.json run_id must be {}'.format(run))
    limits_note = raw.get('resource_limits_note', 'NOT_AVAILABLE')
    if not isinstance(limits_note, str) or not limits_note.strip():
        raise ValueError('resource_limits_note must be a nonempty string')
    status = raw.get('agent_execution_status', 'NOT_OBSERVED')
    if status not in ('NOT_OBSERVED', 'COMPLETED', 'STOPPED', 'FAILED'):
        raise ValueError('Invalid agent execution status')
    transcript = raw.get('transcript_ref')
    if status != 'NOT_OBSERVED' or transcript is not None:
        evidence_file(run_dir, transcript)
    tokens = raw.get('tokens') or {}
    token_counts = {name: count(tokens.get(name), 'tokens.{}'.format(name))
                    for name in ('input', 'cached_input', 'output', 'total')}
    semantics = tokens.get('total_semantics', 'NOT_AVAILABLE')
    if semantics not in ('input_plus_output', 'cached_included_in_input', 'cached_separate', 'NOT_AVAILABLE'):
        raise ValueError('Unknown token total semantics')
    if token_counts['cached_input'] is not None and semantics == 'input_plus_output':
        raise ValueError('Cached input requires explicit total semantics')
    if (semantics == 'cached_included_in_input' and token_counts['cached_input'] is not None
            and token_counts['input'] is not None and token_counts['cached_input'] > token_counts['input']):
        raise ValueError('Cached input cannot exceed input when included in input')
    if any(value is not None for value in token_counts.values()):
        if tokens.get('source_type') not in ('provider_report', 'provider_ui_rounded'):
            raise ValueError('Token values require a provider record or identified rounded UI observation')
        evidence_file(run_dir, tokens.get('evidence_ref'))
        if all(token_counts[name] is not None for name in ('input', 'output', 'total')):
            expected = token_counts['input'] + token_counts['output']
            if semantics == 'cached_separate':
                if token_counts['cached_input'] is None:
                    raise ValueError('Cached-separate total requires cached input')
                expected += token_counts['cached_input']
            if semantics != 'NOT_AVAILABLE' and expected != token_counts['total']:
                raise ValueError('Token parts do not match the declared provider total semantics')
    tools = raw.get('tool_calls') or {}
    tool_count = count(tools.get('count'), 'tool_calls.count')
    if tool_count is not None:
        evidence_file(run_dir, tools.get('evidence_ref'))
    attempts = raw.get('verification_attempts') or {}
    attempt_count = count(attempts.get('count'), 'verification_attempts.count')
    if attempt_count is not None:
        evidence_file(run_dir, attempts.get('evidence_ref'))
    cost = raw.get('cost') or {}
    amount = cost.get('amount')
    if amount is not None:
        if (isinstance(amount, bool) or not isinstance(amount, (int, float))
                or not math.isfinite(amount) or amount < 0):
            raise ValueError('Cost amount must be a nonnegative number')
        if not all(isinstance(cost.get(key), str) and cost[key].strip()
                   for key in ('currency', 'pricing_basis', 'evidence_ref')):
            raise ValueError('Cost requires currency, pricing basis, and evidence')
        evidence_file(run_dir, cost['evidence_ref'])
    return {
        'provider': raw.get('provider'), 'model': raw.get('model'), 'agent_mode': raw.get('agent_mode'),
        'resource_limits_note': limits_note,
        'agent_execution_status': status, 'agent_outcome': raw.get('agent_outcome', 'NOT_AVAILABLE'),
        'transcript_ref': transcript, 'setup_start_utc': raw.get('setup_start_utc'),
        'setup_end_utc': raw.get('setup_end_utc'),
        'setup_seconds': duration(raw.get('setup_start_utc'), raw.get('setup_end_utc')),
        'agent_start_utc': raw.get('agent_start_utc'), 'agent_end_utc': raw.get('agent_end_utc'),
        'agent_seconds': duration(raw.get('agent_start_utc'), raw.get('agent_end_utc')),
        'tokens': dict(token_counts, source_type=tokens.get('source_type', 'NOT_AVAILABLE'),
                       total_semantics=semantics, evidence_ref=tokens.get('evidence_ref')),
        'tool_calls': {'count': tool_count, 'evidence_ref': tools.get('evidence_ref')},
        'verification_attempts': {'count': attempt_count, 'evidence_ref': attempts.get('evidence_ref')},
        'cost': {'amount': amount, 'currency': cost.get('currency'),
                 'pricing_basis': cost.get('pricing_basis'), 'evidence_ref': cost.get('evidence_ref')},
        'provenance': 'PARTICIPANT_SUPPLIED' if raw else 'NOT_AVAILABLE',
    }


def shown(value):
    return 'NOT_AVAILABLE' if value is None else str(value)


def patch_statistics(patch):
    lines = patch.splitlines()
    return {
        'added_lines': sum(line.startswith(b'+') and not line.startswith(b'+++ ') for line in lines),
        'removed_lines': sum(line.startswith(b'-') and not line.startswith(b'--- ') for line in lines),
        'provenance': 'CANDIDATE_PATCH',
    }


def patch_files():
    tracked = subprocess.check_output(['git', '-C', str(DJANGO), 'diff', '--name-only', '-z', 'HEAD'])
    untracked = subprocess.check_output(['git', '-C', str(DJANGO), 'ls-files', '--others', '--exclude-standard', '-z'])
    return sorted({os.fsdecode(path) for path in (tracked + untracked).split(b'\0') if path})


def report(run):
    if run not in ('A', 'B', 'BASELINE'):
        raise ValueError('Usage: bash scripts/report.sh A|B|BASELINE')
    run_dir = REPORTS / run
    status_path = run_dir / 'status.tsv'
    if not status_path.is_file():
        raise ValueError('Run bash scripts/verify.sh {} first'.format(run))
    with status_path.open(newline='') as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    if [row['check'] for row in rows] != list(CHECKS):
        raise ValueError('Verification log must contain the three fixed checks')
    checks = {row['check']: {'exit_code': int(row['exit_code']), 'seconds': int(row['seconds']), 'log': row['check'] + '.log'} for row in rows}
    obs = observations(run, run_dir)
    patch = candidate_patch()
    (run_dir / 'candidate.patch').write_bytes(patch)
    result = {
        'schema_version': 1, 'run_id': run, 'task': 'django__django-11019',
        'baseline_commit': BASE, 'current_commit': git('rev-parse', 'HEAD'),
        'python_version': subprocess.check_output([str(ROOT / '.venv' / 'bin' / 'python'), '--version'], text=True).strip(),
        'verification': {'checks': checks, 'all_passed': all(item['exit_code'] == 0 for item in checks.values()), 'provenance': 'EXECUTED_BY_VERIFY_SH'},
        'changed_files': len(git('status', '--porcelain', '--untracked-files=all').splitlines()),
        'changed_files_provenance': 'GIT_STATUS_AT_REPORT_TIME', 'candidate_patch': 'candidate.patch',
        'patch_statistics': patch_statistics(patch), 'patch_files': patch_files(),
        'observations': obs,
    }
    (run_dir / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    lines = ['# AICA005 run {} evidence'.format(run), '',
             '- Task: `django__django-11019`', '- Baseline: `{}`'.format(BASE),
             '- Current Django HEAD: `{}`'.format(result['current_commit']),
             '- Verification: {}'.format('PASS' if result['verification']['all_passed'] else 'FAIL'),
             '- Changed files: {} (git status at report time)'.format(result['changed_files']),
             '- Candidate patch: `candidate.patch` (tracked and untracked Django changes)',
             '- Patch lines added / removed: {} / {}'.format(
                 result['patch_statistics']['added_lines'], result['patch_statistics']['removed_lines']),
             '- Patch files: {}'.format(', '.join(result['patch_files']) or 'NONE'),
             '- Agent execution: {} ({})'.format(obs['agent_execution_status'], obs['provenance']),
             '- Provider / model / mode: {} / {} / {}'.format(shown(obs['provider']), shown(obs['model']), shown(obs['agent_mode'])),
             '- Available resource limits: {}'.format(obs['resource_limits_note']),
             '- Setup seconds: {}; agent seconds: {}'.format(shown(obs['setup_seconds']), shown(obs['agent_seconds'])),
             '- Input / cached input / output / total tokens: {} / {} / {} / {} (source: {}; total semantics: {})'.format(
                 shown(obs['tokens']['input']), shown(obs['tokens']['cached_input']),
                 shown(obs['tokens']['output']), shown(obs['tokens']['total']),
                 obs['tokens']['source_type'], obs['tokens']['total_semantics']),
             '- Tool calls: {} (participant evidence)'.format(shown(obs['tool_calls']['count'])),
             '- Verification attempts: {} (participant evidence)'.format(shown(obs['verification_attempts']['count'])),
             '- Cost: {} {} (pricing basis: {})'.format(
                 shown(obs['cost']['amount']), shown(obs['cost']['currency']), shown(obs['cost']['pricing_basis'])),
             '- Agent outcome: {}'.format(obs['agent_outcome']), '',
             '## Executed verification', '', '| Check | Exit | Seconds | Log |', '| --- | ---: | ---: | --- |']
    for name in CHECKS:
        item = checks[name]
        lines.append('| {} | {} | {} | `{}` |'.format(name, item['exit_code'], item['seconds'], item['log']))
    lines += ['', '## Evidence boundary', '',
              'Verification values come from executed commands. Agent observations come from `observations.json` and attached evidence; this script does not run Copilot.',
              'A task-level PASS still requires engineer review of the patch and remaining risks.', '']
    (run_dir / 'report.md').write_text('\n'.join(lines), encoding='utf-8')
    archive = package_evidence(run_dir, checks, obs)
    print(run_dir / 'report.md')
    print(run_dir / 'result.json')
    print(archive)


def token_reduction(a, b):
    ao, bo = a['observations'], b['observations']
    at, bt = ao['tokens'], bo['tokens']
    same = (a['task'] == b['task'] and a['baseline_commit'] == b['baseline_commit']
            and a['python_version'] == b['python_version']
            and set(a['verification']['checks']) == set(b['verification']['checks'])
            and ao['provider'] is not None and ao['provider'] == bo['provider']
            and ao['model'] is not None and ao['model'] == bo['model']
            and ao['agent_mode'] is not None and ao['agent_mode'] == bo['agent_mode']
            and at.get('total_semantics') == bt.get('total_semantics')
            and at.get('total_semantics') not in (None, 'NOT_AVAILABLE'))
    if not same or at['source_type'] != 'provider_report' or bt['source_type'] != 'provider_report' or not at['evidence_ref'] or not bt['evidence_ref']:
        return None
    if not isinstance(at['total'], int) or at['total'] <= 0 or not isinstance(bt['total'], int) or bt['total'] < 0:
        return None
    return round((at['total'] - bt['total']) / at['total'] * 100, 2)


def compare():
    results = {}
    for run in ('A', 'B'):
        path = REPORTS / run / 'result.json'
        results[run] = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None
    a, b = results['A'], results['B']
    same_checks = bool(a and b and a['task'] == b['task']
                       and a['baseline_commit'] == b['baseline_commit']
                       and a['python_version'] == b['python_version']
                       and set(a['verification']['checks']) == set(b['verification']['checks']))
    verification_equivalence = ('NOT_ESTABLISHED' if not same_checks else
                                'PASS' if a['verification']['all_passed'] and b['verification']['all_passed']
                                else 'FAIL')
    reduction = token_reduction(a, b) if verification_equivalence == 'PASS' else None
    resource_comparison = 'PASS' if reduction is not None else 'INCONCLUSIVE'
    packages = bool(a and b and all((REPORTS / run / 'evidence.zip').is_file() for run in ('A', 'B')))
    transcripts = bool(a and b and all(results[run]['observations'].get('transcript_ref') for run in ('A', 'B')))
    evidence_completeness = ('PASS' if packages and transcripts else
                             'PARTIAL' if packages else 'NOT_ESTABLISHED')
    status = 'READY' if a and b else 'PARTIAL'
    a_paths = a.get('patch_files') if a else None
    b_paths = b.get('patch_files') if b else None
    path_comparison = ('are unavailable' if a_paths is None or b_paths is None
                       else 'match' if a_paths == b_paths else 'differ')
    output = {'schema_version': 1, 'status': status, 'runs': results, 'token_reduction_percent': reduction,
              'token_reduction_provenance': 'PROVIDER_REPORTS_AND_MATCHING_RUN_METADATA' if reduction is not None else 'NOT_AVAILABLE',
              'verification_equivalence': verification_equivalence,
              'solution_equivalence': 'NOT_ESTABLISHED',
              'resource_comparison': resource_comparison,
              'evidence_completeness': evidence_completeness,
              'engineering_decision': 'INCONCLUSIVE',
              'interpretation': 'Passing the same checks supports equivalent verification within tested scope, not semantic or efficiency equivalence. One A/B pair is exploratory.'}
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / 'comparison.json').write_text(json.dumps(output, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    lines = ['# AICA005 A/B engineering benchmark', '',
             'Status: **{}**. This describes report availability, not agent success.'.format(status), '',
             '## What happened?', '',
             '| Run | Script verification | Agent provenance | Patch files | Patch + / − |',
             '| --- | --- | --- | --- | ---: |']
    for run in ('A', 'B'):
        item = results[run]
        if item:
            obs = item['observations']
            patch = item.get('patch_statistics') or {}
            lines.append('| {} | {} | {} | {} | {} / {} |'.format(
                run, 'PASS' if item['verification']['all_passed'] else 'FAIL',
                obs['agent_execution_status'], ', '.join(item.get('patch_files') or []) or 'NONE',
                shown(patch.get('added_lines')), shown(patch.get('removed_lines'))))
        else:
            lines.append('| {} | NOT_AVAILABLE | NOT_OBSERVED | NOT_AVAILABLE | NOT_AVAILABLE |'.format(run))
    lines += ['', 'VERIFICATION_EQUIVALENCE: **{}** (same pinned task and checks; both passing is limited to tested behavior).'.format(verification_equivalence),
              'Patch paths {}. Review each `candidate.patch` for design and regression risks.'.format(path_comparison),
              'SOLUTION_EQUIVALENCE: **NOT_ESTABLISHED**; patch design and quality need human review.', '',
              '## What resources were consumed?', '',
              '| Run | Agent seconds | Input / cached / output / total tokens | Source | Tool calls | Verification attempts | Cost |',
              '| --- | ---: | --- | --- | ---: | ---: | --- |']
    for run in ('A', 'B'):
        item = results[run]
        if not item:
            lines.append('| {} | NOT_AVAILABLE | NOT_AVAILABLE | NOT_AVAILABLE | NOT_AVAILABLE | NOT_AVAILABLE | NOT_AVAILABLE |'.format(run))
            continue
        obs = item['observations']
        tokens = obs['tokens']
        cost = obs.get('cost') or {}
        attempts = obs.get('verification_attempts') or {}
        cost_display = ('NOT_AVAILABLE' if cost.get('amount') is None else
                        '{} {} (basis: {})'.format(cost['amount'], shown(cost.get('currency')),
                                                   shown(cost.get('pricing_basis'))))
        lines.append('| {} | {} | {} / {} / {} / {} | {} | {} | {} | {} |'.format(
            run, shown(obs['agent_seconds']), shown(tokens.get('input')),
            shown(tokens.get('cached_input')), shown(tokens.get('output')),
            shown(tokens.get('total')), tokens.get('source_type', 'NOT_AVAILABLE'),
            shown(obs['tool_calls']['count']), shown(attempts.get('count')), cost_display))
    lines += ['', 'RESOURCE_COMPARISON: **{}**. Token reduction: **{}**.'.format(
                  resource_comparison, 'NOT_AVAILABLE' if reduction is None else '{}%'.format(reduction)),
              'Exact provider totals require matching model, runtime, measurement definition, and passing checks. Cached input is displayed separately and never added twice.',
              'Rounded UI observations, tool calls, patch size, and elapsed time are not exact token totals.',
              'Available limits A / B: {} / {}; confirm they were comparable.'.format(
                  a['observations'].get('resource_limits_note', 'NOT_AVAILABLE') if a else 'NOT_AVAILABLE',
                  b['observations'].get('resource_limits_note', 'NOT_AVAILABLE') if b else 'NOT_AVAILABLE'),
              'Missing telemetry or differing outcomes prevent an efficiency conclusion.', '',
              '## What can we conclude?', '',
              '- Script verification equivalence: **{}**; agent execution provenance is separate.'.format(verification_equivalence),
              '- Evidence completeness: **{}**. Missing transcripts or usage records limit attribution and resource claims.'.format(evidence_completeness),
              '- Solution equivalence and equal patch quality: **NOT_ESTABLISHED**.', '',
              '## Harness Engineering & AI Governance', '',
              '- The same pinned Django baseline and script checks support reproducibility.',
              '- Verification logs and candidate patches are traceable in separate A/B evidence ZIPs.',
              '- The five-minute target is a policy, not an enforced timeout; a human reviews patches, evidence, and limits.', '',
              '## Engineering Decision', '',
              '**INCONCLUSIVE**. Review both patches and any comparable measurements before choosing BETTER, WORSE, or COMPARABLE.',
              'One A/B pair is exploratory and does not establish causality.', '']
    (REPORTS / 'comparison.md').write_text('\n'.join(lines), encoding='utf-8')
    print(REPORTS / 'comparison.md')
    print(REPORTS / 'comparison.json')


if __name__ == '__main__':
    try:
        if len(sys.argv) == 3 and sys.argv[1] == 'report':
            report(sys.argv[2])
        elif len(sys.argv) == 2 and sys.argv[1] == 'compare':
            compare()
        else:
            raise ValueError('Usage: results.py report A|B|BASELINE | compare')
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print('Evidence error: {}'.format(exc), file=sys.stderr)
        sys.exit(1)
