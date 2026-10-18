import copy
import json
import unittest
from unittest.mock import patch

from vandesign.core.geometry import Box
from vandesign.layout_preview import make_layout
from vandesign.modules.bed_platform import build_bed_platform
from vandesign.modules.variants import build_variant
from vandesign.panel_preview import canonical_json, csv_text, make_preview
from vandesign.schemas.bed_platform_spec import BedPlatformSpec
from vandesign.schemas.design_spec import load_design_spec


def placements(bed=(0, 0, 0), cabinet=(1500, 0, 0)):
    return [{'instance_id': 'bed.001', 'translation_mm': list(bed)},
            {'instance_id': 'cabinet.001', 'translation_mm': list(cabinet)}]


class LayoutPreviewTests(unittest.TestCase):
    def test_separated_snapshot_and_actual_generator_envelopes(self):
        result = make_layout(placements())
        self.assertEqual(result['format'], 'vandesign.two-module-layout/1')
        self.assertEqual(result['collision']['status'], 'PASS')
        self.assertEqual(result['collision']['overlap_mm3'], 0)
        self.assertFalse(result['compile_ready_fusion_assembly'])
        self.assertTrue(all(v == 'UNKNOWN' for v in result['qualification'].values()))
        bed, cabinet = result['instances']
        self.assertEqual(bed['local_occupied_envelope']['hi_mm'], [1400, 1900, 700])
        # Nominal cabinet depth550 excludes the18mm front door offset.
        self.assertEqual(cabinet['local_occupied_envelope']['hi_mm'], [1200, 568, 850])
        self.assertEqual(cabinet['world_occupied_envelope']['lo_mm'], [1500, 0, 0])
        identities = [tuple(p['identity']) for i in result['instances'] for p in i['panels']]
        self.assertEqual(len(set(identities)), 11)
        self.assertEqual(identities, sorted(identities))
        self.assertEqual(json.loads(canonical_json(result)), result)

    def test_independent_xyz_motion_and_negative_offsets(self):
        base = make_layout(placements())
        for index in (0, 1):
            for axis in range(3):
                request = placements()
                request[index]['translation_mm'][axis] -= 23.5
                moved = make_layout(request)
                self.assertEqual(moved['instances'][1-index], base['instances'][1-index])
                for before, after in zip(base['instances'][index]['panels'], moved['instances'][index]['panels']):
                    self.assertEqual(before['local_box'], after['local_box'])
                    for side in ('lo_mm', 'hi_mm'):
                        expected = before['world_box'][side].copy()
                        expected[axis] -= 23.5
                        self.assertEqual(after['world_box'][side], expected)

    def test_overlap_including_empty_underbed_space_refused(self):
        with self.assertRaisesRegex(ValueError, 'REFUSED'):
            make_layout(placements(cabinet=(100, 100, 0)))
        # Default cabinet occupies no bed solid at this pose, but intersects the
        # reserved under-bed volume. No implicit floor/vehicle constraint exists.
        request = placements(cabinet=(100, 100, -200))
        bed = build_bed_platform(BedPlatformSpec())
        design = load_design_spec('{"schema_version":"0.2","module":"cabinet@1",'
                                  '"variant":"base","profile_version":1,"parameters":{}}')
        cab = build_variant(design.resolved_params, design.profile)
        for p in bed.panels:
            b = p.box.resolve(bed.parameters.resolve())
            for q in cab.panels:
                c = q.box.resolve(cab.parameters.resolve())
                shift = request[1]['translation_mm']
                c = Box(tuple(a+t for a,t in zip(c.lo, shift)), tuple(a+t for a,t in zip(c.hi, shift)))
                self.assertEqual(b.overlap_volume(c), 0)
        with self.assertRaisesRegex(ValueError, 'bed void included'):
            make_layout(request)

    def test_face_contact_and_existing_epsilon_policy(self):
        for xyz in ((1400, 0, 0), (0, 1900, 0), (0, 0, 700), (1400-0.5e-9, 0, 0)):
            self.assertEqual(make_layout(placements(cabinet=xyz))['collision']['status'], 'PASS')
        with self.assertRaisesRegex(ValueError, 'REFUSED'):
            make_layout(placements(cabinet=(1400-2e-9, 0, 0)))

    def test_invalid_records_refused(self):
        bad = [None, {}, [], placements()[:1], placements()+placements()[:1]]
        for field, value in [('instance_id', 'other'), ('instance_id', None),
                             ('instance_id', ['bed.001']), ('translation_mm', None),
                             ('translation_mm', [1, 2]), ('translation_mm', '123')]:
            req = placements(); req[0][field] = value; bad.append(req)
        req = placements(); req[1]['instance_id'] = 'bed.001'; bad.append(req)
        req = placements(); del req[0]['translation_mm']; bad.append(req)
        req = placements(); req[0]['rotation'] = 0; bad.append(req)
        for request in bad:
            with self.subTest(request=request), self.assertRaises(ValueError):
                make_layout(request)

    def test_nonnumeric_nonfinite_and_precision_loss_refused_before_build(self):
        for value in (None, True, '1', float('nan'), float('inf'), -float('inf'), 10**400):
            req = placements(); req[0]['translation_mm'][0] = value
            with self.subTest(value=repr(value)), patch('vandesign.layout_preview.build_bed_platform') as build:
                with self.assertRaises(ValueError):
                    make_layout(req)
                build.assert_not_called()
        with self.assertRaises(ValueError):
            make_layout(placements(bed=(1e308, 0, 0)))

    def test_unavailable_or_nonfinite_derived_geometry_never_passes(self):
        with patch('vandesign.layout_preview.Box.overlap_volume', return_value=float('nan')):
            with self.assertRaisesRegex(ValueError, 'intersection'):
                make_layout(placements())
        # Fault here is offline arithmetic only: no Fusion fixture or API involved.
        with patch('vandesign.layout_preview.Box.volume', new=property(lambda self: float('inf'))):
            with self.assertRaisesRegex(ValueError, 'geometry'):
                make_layout(placements())

    def test_deterministic_order_numeric_forms_and_input_immutability(self):
        req = placements(); original = copy.deepcopy(req)
        expected = canonical_json(make_layout(req))
        self.assertEqual(req, original)
        reordered = [dict(reversed(list(r.items()))) for r in reversed(req)]
        self.assertEqual(canonical_json(make_layout(reordered)), expected)
        req[0]['translation_mm'] = [-0.0, 0.0, 0.0]
        self.assertEqual(canonical_json(make_layout(req)), expected)
        for _ in range(3):
            self.assertEqual(canonical_json(make_layout(original)), expected)

    def test_standalone_spec_preview_parameters_and_cut_ownership_preserved(self):
        baseline = make_layout(placements())
        moved = make_layout(placements(bed=(-10, 5, 7), cabinet=(1600, 20, 9)))
        for first, second in zip(baseline['instances'], moved['instances']):
            for key in ('specification', 'assembly_spec_hash', 'parameters_mm', 'parameter_expressions', 'standalone_preview'):
                self.assertEqual(first[key], second[key])
            standalone = make_preview(first['specification']['canonical_json'])
            self.assertEqual(canonical_json(standalone), canonical_json(second['standalone_preview']))
            self.assertEqual(csv_text(standalone), csv_text(second['standalone_preview']))
            for op in second['operations']:
                self.assertEqual(op['target_identity'], [second['instance_id'], op['target_panel_id']])
                self.assertEqual(op['mating_identity'], [second['instance_id'], op['mating_panel_id']])
                self.assertEqual(op['world_cut']['lo_mm'], [v+t for v,t in zip(op['local_cut']['lo_mm'],second['translation_mm'])])
        cabinet = moved['instances'][1]
        self.assertEqual(len(cabinet['operations']), 2)
        self.assertEqual({op['target_panel_id'] for op in cabinet['operations']}, {'panel.left.001', 'panel.right.001'})
        for instance in moved['instances']:
            for row in instance['standalone_preview']['panels']:
                self.assertEqual(row['nominal_thickness_mm'], '6.000000' if row['role']=='back' else '18.000000')


if __name__ == '__main__':
    unittest.main()
