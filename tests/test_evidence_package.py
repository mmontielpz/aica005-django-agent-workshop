"""Fixture-only packaging checks; no Copilot agent or Django tests run here."""
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import zipfile

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'results.py'
SPEC = importlib.util.spec_from_file_location('aica005_package_results', str(SCRIPT))
results = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(results)


class PackageFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temporary.name)
        self.saved = (results.ROOT, results.REPORTS, results.DJANGO)
        results.ROOT = self.root
        results.REPORTS = self.root / 'reports'
        results.DJANGO = self.root / 'workspace' / 'django'
        django = results.DJANGO
        (django / 'django' / 'forms').mkdir(parents=True)
        (django / 'tests').mkdir()
        (django / 'django' / 'forms' / 'widgets.py').write_text('baseline\n', encoding='utf-8')
        subprocess.check_call(['git', 'init', '-q', str(django)])
        subprocess.check_call(['git', '-C', str(django), 'config', 'user.name', 'Fixture'])
        subprocess.check_call(['git', '-C', str(django), 'config', 'user.email', 'fixture@example.invalid'])
        subprocess.check_call(['git', '-C', str(django), 'add', '.'])
        subprocess.check_call(['git', '-C', str(django), 'commit', '-qm', 'fixture baseline'])
        (django / 'django' / 'forms' / 'widgets.py').write_text('baseline\ncorrected\n', encoding='utf-8')
        (django / 'tests' / 'test_candidate.py').write_text('def test_candidate():\n    assert True\n', encoding='utf-8')
        venv = self.root / '.venv' / 'bin'
        venv.mkdir(parents=True)
        (venv / 'python').symlink_to(sys.executable)
        for run in ('A', 'B'):
            folder = results.REPORTS / run
            folder.mkdir(parents=True)
            (folder / 'status.tsv').write_text(
                'check\texit_code\tseconds\tcommand\n'
                'issue_regression\t0\t1\tfixture\n'
                'forms_media\t0\t1\tfixture\n'
                'admin_widgets\t0\t1\tfixture\n', encoding='utf-8')
            for name in results.CHECKS:
                (folder / (name + '.log')).write_text('fixture check: {}\n'.format(name), encoding='utf-8')

    def tearDown(self):
        results.ROOT, results.REPORTS, results.DJANGO = self.saved
        self.temporary.cleanup()

    def test_a_and_b_packages_contain_patch_and_fixed_verification_evidence(self):
        for run in ('A', 'B'):
            results.report(run)
            with zipfile.ZipFile(str(results.REPORTS / run / 'evidence.zip')) as archive:
                names = set(archive.namelist())
                self.assertEqual(names, {'candidate.patch', 'status.tsv', 'report.md', 'result.json',
                                         'issue_regression.log', 'forms_media.log', 'admin_widgets.log'})
                patch = archive.read('candidate.patch')
                self.assertIn(b'django/forms/widgets.py', patch)
                self.assertIn(b'tests/test_candidate.py', patch)
                self.assertIn(b'corrected', patch)
                self.assertNotIn('evidence.zip', names)
        results.compare()
        comparison = json.loads((results.REPORTS / 'comparison.json').read_text(encoding='utf-8'))
        self.assertEqual(comparison['status'], 'PARTIAL')
        self.assertEqual(comparison['outcome_equivalence'], 'UNKNOWN')
        self.assertIsNone(comparison['token_reduction_percent'])

    def test_repeated_report_is_idempotent_and_preserves_changed_package(self):
        results.report('A')
        folder = results.REPORTS / 'A'
        before = (folder / 'evidence.zip').read_bytes()
        results.report('A')
        self.assertEqual((folder / 'evidence.zip').read_bytes(), before)
        self.assertEqual(list(folder.glob('evidence-*.zip')), [])
        (folder / 'issue_regression.log').write_text('new fixture evidence\n', encoding='utf-8')
        results.report('A')
        backup = folder / 'evidence-{}.zip'.format(hashlib.sha256(before).hexdigest()[:12])
        self.assertEqual(backup.read_bytes(), before)
        with zipfile.ZipFile(str(folder / 'evidence.zip')) as archive:
            self.assertEqual(archive.read('issue_regression.log'), b'new fixture evidence\n')
            self.assertFalse(any(name.endswith('.zip') for name in archive.namelist()))

    def test_secret_pattern_blocks_replacement_and_symlink_escape(self):
        results.report('A')
        folder = results.REPORTS / 'A'
        before = (folder / 'evidence.zip').read_bytes()
        (folder / 'issue_regression.log').write_text('Authorization: Bearer fixture-secret\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Possible credential'):
            results.report('A')
        self.assertEqual((folder / 'evidence.zip').read_bytes(), before)
        outside = self.root / 'outside.txt'
        outside.write_text('outside', encoding='utf-8')
        (folder / 'escape.txt').symlink_to(outside)
        with self.assertRaises(ValueError):
            results.evidence_file(folder, 'escape.txt')

    def test_different_verified_outcomes_do_not_claim_token_reduction(self):
        for run in ('A', 'B'):
            folder = results.REPORTS / run
            (folder / 'transcript.txt').write_text('fixture transcript only', encoding='utf-8')
            (folder / 'observations.json').write_text(json.dumps({
                'run_id': run, 'agent_execution_status': 'COMPLETED',
                'transcript_ref': 'transcript.txt', 'provider': 'fixture-provider',
                'model': 'fixture-model', 'agent_mode': 'Agent',
                'tokens': {'source_type': 'NOT_AVAILABLE'},
            }), encoding='utf-8')
        (results.REPORTS / 'B' / 'status.tsv').write_text(
            'check\texit_code\tseconds\tcommand\n'
            'issue_regression\t1\t1\tfixture\n'
            'forms_media\t0\t1\tfixture\n'
            'admin_widgets\t0\t1\tfixture\n', encoding='utf-8')
        results.report('A')
        results.report('B')
        results.compare()
        comparison = json.loads((results.REPORTS / 'comparison.json').read_text(encoding='utf-8'))
        self.assertEqual(comparison['status'], 'READY')
        self.assertEqual(comparison['outcome_equivalence'], 'FAIL')
        self.assertIsNone(comparison['token_reduction_percent'])
        self.assertTrue(comparison['runs']['A']['verification']['all_passed'])
        self.assertFalse(comparison['runs']['B']['verification']['all_passed'])


if __name__ == '__main__':
    unittest.main()
