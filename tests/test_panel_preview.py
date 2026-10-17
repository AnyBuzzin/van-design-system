import copy
import csv
from dataclasses import replace
import io
import json
from pathlib import Path
import unittest

from vandesign.modules.cabinet import build_cabinet
from vandesign.panel_preview import canonical_json, csv_text, make_preview, panel_rows
from vandesign.schemas.cabinet_spec import CabinetSpec

ROOT = Path(__file__).resolve().parents[1]
G4 = ROOT / 'docs/integration/g4-shelf-count/live-20261017'


def measured_case(stage='to-two'):
    directory = G4 / ('jobs/g4-live-20261017-' + stage)
    report_file = next((directory / 'evidence/00_update_shelf_count/post/reports').glob('*.json'))
    raw = report_file.read_bytes()
    report = json.loads(raw)
    return report['design_spec_canonical_json'], raw, json.loads((directory / 'result.json').read_bytes())


class PanelPreviewTests(unittest.TestCase):
    def test_spec_only_unknown_and_deterministic_parity(self):
        spec = CabinetSpec().to_json()
        a = make_preview(spec)
        self.assertEqual(canonical_json(a), canonical_json(make_preview(spec)))
        self.assertEqual(a['evidence']['status'], 'UNKNOWN')
        rows = list(csv.DictReader(io.StringIO(csv_text(a))))
        self.assertEqual(rows, [{k: str(v) for k, v in row.items()} for row in a['panels']])
        self.assertEqual([r['panel_id'] for r in rows], sorted(r['panel_id'] for r in rows))
        self.assertTrue(all(r['quantity'] == '1' for r in rows))

    def test_role_axes_and_back_thickness(self):
        rows = {p['role']: p for p in panel_rows(build_cabinet(CabinetSpec()))}
        self.assertEqual(rows['back']['nominal_thickness_mm'], '6.000000')
        self.assertEqual(rows['left']['nominal_thickness_mm'], '18.000000')
        self.assertEqual(rows['shelf']['blank_1_mm'], '1175.400000')
        self.assertEqual(rows['back']['blank_axis_2'], 'Z')
        # Thickness is by role even when it is not the smallest dimension.
        asm = build_cabinet(CabinetSpec(width_mm=40, door_count=1))
        back = next(r for r in panel_rows(asm) if r['role'] == 'back')
        self.assertEqual(back['blank_1_mm'], '4.000000')
        self.assertEqual(back['nominal_thickness_mm'], '6.000000')

    def test_unknown_role_and_invalid_spec_refused(self):
        asm = build_cabinet(CabinetSpec())
        with self.assertRaises(ValueError):
            panel_rows(replace(asm, panels=(replace(asm.panels[0], role='unknown'),) + asm.panels[1:]))
        for text in ['{}', '{"schema_version":"0.2","parameters":{"width_mm":NaN}}']:
            with self.assertRaises(ValueError):
                make_preview(text)

    def test_accepted_g4_measured_blanks_and_grooves(self):
        for stage, panel_count, cut_count in [('to-two', 9, 4), ('to-one', 8, 2)]:
            with self.subTest(stage=stage):
                spec, raw, job = measured_case(stage)
                preview = make_preview(spec, raw)
                self.assertEqual(preview['evidence']['status'], 'PASS', preview['evidence'])
                self.assertEqual(len(preview['panels']), panel_count)
                self.assertEqual(len(preview['grooves']), cut_count)
                state = job['steps'][0]['post_verification']['state']
                bodies = state['inventory']['panels']
                for row in preview['panels']:
                    bounds = bodies[row['panel_id']]['bounds_cm']
                    measured = [(b-a)*10 for a,b in zip(*bounds)]
                    for axis_key, value_key in [('blank_axis_1','blank_1_mm'), ('blank_axis_2','blank_2_mm'), ('thickness_axis','nominal_thickness_mm')]:
                        self.assertAlmostEqual(measured['XYZ'.index(row[axis_key])], float(row[value_key]), delta=0.01)
                self.assertEqual(preview['evidence']['cut_ownership'], 'UNKNOWN')
                self.assertEqual(preview['evidence']['saved_document'], 'UNKNOWN')

    def test_stale_parameters_not_hidden_by_matching_hash(self):
        spec, raw, _ = measured_case()
        report = json.loads(raw)
        report['parameters_read_from_fusion']['Cab_Width']['value_mm'] += 10
        p = make_preview(spec, json.dumps(report).encode())
        self.assertEqual(p['evidence']['status'], 'FAIL')
        self.assertEqual(p['evidence']['stored_spec_parameter_divergence'], ['Cab_Width'])

    def test_mismatched_and_missing_evidence(self):
        spec, raw, _ = measured_case()
        baseline = json.loads(raw)
        mutations = [
            ('FAIL', lambda r: r.update(design_spec_hash='stale')),
            ('FAIL', lambda r: r['validation']['checks'][0].update(status='FAIL')),
            ('UNKNOWN', lambda r: r.pop('parameters_read_from_fusion')),
            ('UNKNOWN', lambda r: r['validation']['checks'][0].update(status='UNKNOWN')),
            ('UNKNOWN', lambda r: r['parameters_read_from_fusion']['Cab_Width'].update(value_mm=None)),
            ('FAIL', lambda r: r['validation']['checks'].append(r['validation']['checks'][0])),
            ('FAIL', lambda r: r['validation']['checks'].append({'check_id':'panel.orphan.001.bbox','status':'PASS'})),
        ]
        for expected, mutate in mutations:
            report = copy.deepcopy(baseline)
            mutate(report)
            self.assertEqual(make_preview(spec, json.dumps(report).encode())['evidence']['status'], expected)

    def test_reused_overhead_scalar_edit_is_explicit_divergence(self):
        directory = ROOT / 'docs/integration/g3-remaining-verification/runner/g3-overhead-remaining-20261017-001/evidence'
        raw = next((directory / '02_measure/reports').glob('*.json')).read_bytes()
        report = json.loads(raw)
        p = make_preview(report['design_spec_canonical_json'], raw)
        self.assertEqual(p['evidence']['status'], 'FAIL')
        self.assertIn('Cab_Depth', p['evidence']['stored_spec_parameter_divergence'])


if __name__ == '__main__':
    unittest.main()
