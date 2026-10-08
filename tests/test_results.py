"""Synthetic unit fixtures for the evidence calculation, not experiment runs."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'results.py'
SPEC = importlib.util.spec_from_file_location('aica005_results', str(SCRIPT))
results = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(results)


def sample(total, model='same-model', source='provider_report'):
    return {
        'task': 'django__django-11019', 'baseline_commit': results.BASE,
        'python_version': 'Python 3.7.17',
        'verification': {'checks': {'issue_regression': {}, 'forms_media': {}, 'admin_widgets': {}}},
        'observations': {'provider': 'example-provider', 'model': model, 'agent_mode': 'Agent',
                         'tokens': {'total': total, 'source_type': source,
                                    'total_semantics': 'input_plus_output', 'evidence_ref': 'provider.txt'}},
    }


class EvidenceTests(unittest.TestCase):
    def test_reduction_requires_comparable_provider_totals(self):
        self.assertEqual(results.token_reduction(sample(1000), sample(750)), 25.0)
        self.assertIsNone(results.token_reduction(sample(1000), sample(750, model='other-model')))
        self.assertIsNone(results.token_reduction(sample(1000), sample(750, source='NOT_AVAILABLE')))
        self.assertIsNone(results.token_reduction(sample(1000, source='provider_ui_rounded'),
                                                   sample(750, source='provider_ui_rounded')))
        self.assertIsNone(results.token_reduction(sample(0), sample(750)))
        cached = sample(1000)
        cached['observations']['tokens'].update(cached_input=500, total_semantics='cached_included_in_input')
        other = sample(750)
        other['observations']['tokens'].update(cached_input=250, total_semantics='cached_included_in_input')
        self.assertEqual(results.token_reduction(cached, other), 25.0)
        self.assertIsNone(results.token_reduction(cached, sample(750)))

    def test_setup_and_agent_durations_are_separate_utc_intervals(self):
        self.assertEqual(results.duration('2026-10-08T12:00:00Z', '2026-10-08T12:00:30Z'), 30.0)
        self.assertIsNone(results.duration(None, None))
        with self.assertRaises(ValueError):
            results.duration('2026-10-08T12:00:30Z', '2026-10-08T12:00:00Z')

    def test_tokens_without_provider_evidence_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            run_dir = pathlib.Path(folder)
            (run_dir / 'observations.json').write_text(json.dumps({
                'run_id': 'A', 'agent_execution_status': 'COMPLETED', 'transcript_ref': 'transcript.txt',
                'tokens': {'total': 1000, 'source_type': 'NOT_AVAILABLE', 'evidence_ref': None},
            }), encoding='utf-8')
            (run_dir / 'transcript.txt').write_text('Test fixture only', encoding='utf-8')
            with self.assertRaises(ValueError):
                results.observations('A', run_dir)

    def test_cached_input_is_not_double_counted(self):
        with tempfile.TemporaryDirectory() as folder:
            run_dir = pathlib.Path(folder)
            (run_dir / 'provider.txt').write_text('fixture provider record', encoding='utf-8')
            (run_dir / 'transcript.txt').write_text('fixture transcript', encoding='utf-8')
            values = {
                'run_id': 'A', 'agent_execution_status': 'COMPLETED',
                'transcript_ref': 'transcript.txt',
                'tokens': {'input': 800, 'cached_input': 500, 'output': 200, 'total': 1000,
                           'source_type': 'provider_report', 'total_semantics': 'cached_included_in_input',
                           'evidence_ref': 'provider.txt'},
            }
            path = run_dir / 'observations.json'
            path.write_text(json.dumps(values), encoding='utf-8')
            observed = results.observations('A', run_dir)
            self.assertEqual(observed['tokens']['total'], 1000)
            values['tokens']['total'] = 1500
            path.write_text(json.dumps(values), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Token parts'):
                results.observations('A', run_dir)
            values['tokens']['total_semantics'] = 'cached_separate'
            path.write_text(json.dumps(values), encoding='utf-8')
            self.assertEqual(results.observations('A', run_dir)['tokens']['total'], 1500)


if __name__ == '__main__':
    unittest.main()
