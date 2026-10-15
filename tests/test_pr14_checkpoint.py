"""Safety tests for the one-shot Fusion checkpoint; no adsk or CAD mocks."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

path = Path(__file__).resolve().parents[1] / 'fusion/PR14CompatibilityCheckpoint/PR14CompatibilityCheckpoint.py'
spec = importlib.util.spec_from_file_location('checkpoint_under_test', path)
checkpoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkpoint)


class CheckpointSafetyTests(unittest.TestCase):
    def test_saved_document_refused_before_parameter_access(self):
        with self.assertRaisesRegex(RuntimeError, 'unsaved Untitled'):
            checkpoint.require_test_document(NS(name='Untitled', isSaved=True), NS())

    def test_non_test_document_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'unsaved Untitled'):
            checkpoint.require_test_document(NS(name='protected', isSaved=False), NS())

    def test_edit_failure_still_restores_exact_original_expression(self):
        parameter = NS(expression='1200 mm')
        calls = []
        record = {}
        def measure(stage):
            calls.append((stage, parameter.expression))
            if stage == 'edited':
                raise RuntimeError('measurement unavailable')
            return {'width_expression': parameter.expression}
        with self.assertRaisesRegex(RuntimeError, 'measurement unavailable'):
            checkpoint.edit_restore(parameter, measure, record)
        self.assertEqual(parameter.expression, '1200 mm')
        self.assertEqual(calls, [('edited', '1210 mm'), ('restored', '1200 mm')])
        self.assertTrue(record['original_expression_restored'])

    def test_brep_comparison_rejects_changed_geometry_or_missing_panel(self):
        baseline = {'panel': {'box': {'lo': (0,0,0), 'hi': (1200,18,850)}, 'volume_mm3': 18360000}}
        self.assertTrue(checkpoint.geometry_matches(baseline, baseline, .01, 1e-6))
        self.assertFalse(checkpoint.geometry_matches(baseline, {}, .01, 1e-6))
        changed = {'panel': {'box': {'lo': (0,0,0), 'hi': (1210,18,850)}, 'volume_mm3': 18513000}}
        self.assertFalse(checkpoint.geometry_matches(baseline, changed, .01, 1e-6))


if __name__ == '__main__':
    unittest.main()
