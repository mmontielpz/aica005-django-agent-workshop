#!/usr/bin/env python3
"""Turn executed checks and participant evidence into reviewable A/B results."""
import csv
import datetime
import hashlib
import json
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
    for ref in (obs['transcript_ref'], obs['tokens']['evidence_ref'], obs['tool_calls']['evidence_ref']):
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
    token_counts = {name: count(tokens.get(name), 'tokens.{}'.format(name)) for name in ('input', 'output', 'total')}
    if any(value is not None for value in token_counts.values()):
        if status == 'NOT_OBSERVED' or tokens.get('source_type') != 'provider_report':
            raise ValueError('Token values require an observed run and provider report')
        evidence_file(run_dir, tokens.get('evidence_ref'))
        if all(token_counts[name] is not None for name in ('input', 'output', 'total')) and token_counts['input'] + token_counts['output'] != token_counts['total']:
            raise ValueError('Input plus output tokens must equal total tokens')
    tools = raw.get('tool_calls') or {}
    tool_count = count(tools.get('count'), 'tool_calls.count')
    if tool_count is not None:
        evidence_file(run_dir, tools.get('evidence_ref'))
    return {
        'provider': raw.get('provider'), 'model': raw.get('model'), 'agent_mode': raw.get('agent_mode'),
        'resource_limits_note': limits_note,
        'agent_execution_status': status, 'agent_outcome': raw.get('agent_outcome', 'NOT_AVAILABLE'),
        'transcript_ref': transcript, 'setup_start_utc': raw.get('setup_start_utc'),
        'setup_end_utc': raw.get('setup_end_utc'),
        'setup_seconds': duration(raw.get('setup_start_utc'), raw.get('setup_end_utc')),
        'agent_start_utc': raw.get('agent_start_utc'), 'agent_end_utc': raw.get('agent_end_utc'),
        'agent_seconds': duration(raw.get('agent_start_utc'), raw.get('agent_end_utc')),
        'tokens': dict(token_counts, source_type=tokens.get('source_type', 'NOT_AVAILABLE'), evidence_ref=tokens.get('evidence_ref')),
        'tool_calls': {'count': tool_count, 'evidence_ref': tools.get('evidence_ref')},
        'provenance': 'PARTICIPANT_SUPPLIED' if raw else 'NOT_AVAILABLE',
    }


def shown(value):
    return 'NOT_AVAILABLE' if value is None else str(value)


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
        'observations': obs,
    }
    (run_dir / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    lines = ['# AICA005 run {} evidence'.format(run), '',
             '- Task: `django__django-11019`', '- Baseline: `{}`'.format(BASE),
             '- Current Django HEAD: `{}`'.format(result['current_commit']),
             '- Verification: {}'.format('PASS' if result['verification']['all_passed'] else 'FAIL'),
             '- Changed files: {} (git status at report time)'.format(result['changed_files']),
             '- Candidate patch: `candidate.patch` (tracked and untracked Django changes)',
             '- Agent execution: {} ({})'.format(obs['agent_execution_status'], obs['provenance']),
             '- Provider / model / mode: {} / {} / {}'.format(shown(obs['provider']), shown(obs['model']), shown(obs['agent_mode'])),
             '- Available resource limits: {}'.format(obs['resource_limits_note']),
             '- Setup seconds: {}; agent seconds: {}'.format(shown(obs['setup_seconds']), shown(obs['agent_seconds'])),
             '- Input / output / total tokens: {} / {} / {} (source: {})'.format(shown(obs['tokens']['input']), shown(obs['tokens']['output']), shown(obs['tokens']['total']), obs['tokens']['source_type']),
             '- Tool calls: {} (participant evidence)'.format(shown(obs['tool_calls']['count'])),
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
            and ao['agent_mode'] is not None and ao['agent_mode'] == bo['agent_mode'])
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
    observed = bool(a and b and all(results[run]['observations']['agent_execution_status'] != 'NOT_OBSERVED' for run in ('A', 'B')))
    equivalent = bool(observed and a['verification']['all_passed'] and b['verification']['all_passed'])
    reduction = token_reduction(a, b) if equivalent else None
    outcome_equivalence = 'PASS' if equivalent else 'FAIL' if observed else 'UNKNOWN'
    status = 'READY' if observed else 'PARTIAL'
    output = {'schema_version': 1, 'status': status, 'runs': results, 'token_reduction_percent': reduction,
              'token_reduction_provenance': 'PROVIDER_REPORTS_AND_MATCHING_RUN_METADATA' if reduction is not None else 'NOT_AVAILABLE',
              'outcome_equivalence': outcome_equivalence,
              'interpretation': 'One A/B comparison is exploratory, not statistically conclusive. Different or failed outcomes do not support an efficiency conclusion.'}
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / 'comparison.json').write_text(json.dumps(output, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    lines = ['# AICA005 A/B comparison', '', 'Status: **{}**'.format(status), '',
             '| Run | Agent | Verification | Changed files | Agent seconds | Total tokens |',
             '| --- | --- | --- | ---: | ---: | ---: |']
    for run in ('A', 'B'):
        item = results[run]
        if item:
            obs = item['observations']
            lines.append('| {} | {} | {} | {} | {} | {} |'.format(run, obs['agent_execution_status'], 'PASS' if item['verification']['all_passed'] else 'FAIL', item['changed_files'], shown(obs['agent_seconds']), shown(obs['tokens']['total'])))
        else:
            lines.append('| {} | NOT_OBSERVED | NOT_AVAILABLE | NOT_AVAILABLE | NOT_AVAILABLE | NOT_AVAILABLE |'.format(run))
    lines += ['', 'Equivalent verified outcomes: **{}**'.format(outcome_equivalence),
              'Token reduction: **{}**'.format('NOT_AVAILABLE' if reduction is None else '{}%'.format(reduction)),
              'Available limits A / B: {} / {}; confirm that the same account limits applied.'.format(
                  a['observations'].get('resource_limits_note', 'NOT_AVAILABLE') if a else 'NOT_AVAILABLE',
                  b['observations'].get('resource_limits_note', 'NOT_AVAILABLE') if b else 'NOT_AVAILABLE'),
              'Formula: (Tokens A − Tokens B) / Tokens A × 100; used only with equivalent verified outcomes and attached comparable provider records.',
              'Tool calls and elapsed time are separate observables, not token estimates.',
              'A single comparison is exploratory. Judge resource use alongside verification and patch quality.', '']
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
