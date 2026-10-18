import copy
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import unittest
from unittest.mock import patch

from vandesign.cad.protocol import preflight
from vandesign.composition import compose_layout, preview_cabinet_placement
from vandesign.components.ids import make_id
from vandesign.core.params import ParameterSet
from vandesign.layout_preview import make_layout
from vandesign.modules.bed_platform import build_bed_platform
from vandesign.modules.variants import build_variant
from vandesign.panel_preview import canonical_json, csv_text, make_preview
from vandesign.schemas.bed_platform_spec import BedPlatformSpec
from vandesign.schemas.design_spec import load_design_spec


def layout(bed=(0, 0, 0), cabinet=(1500, 0, 0)):
    return make_layout([{'instance_id': 'bed.001', 'translation_mm': list(bed)},
                        {'instance_id': 'cabinet.001', 'translation_mm': list(cabinet)}])


def sources(snapshot):
    spec = load_design_spec(snapshot['instances'][1]['specification']['canonical_json'])
    return (build_bed_platform(BedPlatformSpec()), build_variant(spec.resolved_params, spec.profile))


class CompositionTests(unittest.TestCase):
    def test_opt_in_placement_preserves_sources_and_translates_panels_and_cuts(self):
        fixed = compose_layout(layout())
        editable = compose_layout(layout(), editable_placement=True)
        a = editable.assembly
        self.assertNotEqual(a.spec_hash, fixed.assembly.spec_hash)
        self.assertEqual(a, compose_layout(layout(), editable_placement=True).assembly)
        self.assertEqual(a.parameters.names(), fixed.assembly.parameters.names()+('Cab_Pos_X', 'Cab_Pos_Y'))
        initial = a.parameters.resolve()
        moved = a.parameters.resolve({'Cab_Pos_X':1600, 'Cab_Pos_Y':100})
        for panel, old in zip(a.panels, fixed.assembly.panels):
            self.assertEqual(panel.stable_id, old.stable_id)
            self.assertEqual(panel.box.resolve(initial), old.box.resolve(initial))
            delta = (100,100,0) if panel.stable_id.startswith('cabinet.001.') else (0,0,0)
            self.assertEqual(panel.box.resolve(moved).lo,
                             tuple(v+d for v,d in zip(panel.box.resolve(initial).lo,delta)))
            self.assertAlmostEqual(panel.box.resolve(moved).volume, panel.box.resolve(initial).volume)
        for cut in a.operations:
            self.assertEqual(cut.cut.resolve(moved).lo,
                             tuple(v+d for v,d in zip(cut.cut.resolve(initial).lo,(100,100,0))))
        self.assertEqual(a.parameters.resolve(), initial)

    def test_placement_preview_refuses_overlap_missing_nonfinite_and_reserves_bed_void(self):
        a = compose_layout(layout(), editable_placement=True).assembly
        base = {p.name:p.value_mm for p in a.parameters.base()}
        saved = copy.deepcopy(base)
        for xy in ((1600,100),(1500,0),(0,2000),(1400,0)):
            self.assertEqual(preview_cabinet_placement(a,base,*xy)['outcome'],'PASS')
        self.assertEqual(preview_cabinet_placement(a,base,100,100)['outcome'],'REFUSED')
        # Cabinet can fit below a raised deck without touching bed panels;
        # its placement is still refused by the conservative full bed envelope.
        raised = dict(base, Bed_Height=1100, Bed_Width=1600, Bed_Length=2200,
                      Cab_Width=600, Cab_Height=600, Cab_Depth=300)
        self.assertEqual(preview_cabinet_placement(a,raised,100,100)['outcome'],'REFUSED')
        for x in (True,None,'1600',float('nan'),float('inf'),10001):
            with self.subTest(x=x), self.assertRaises(ValueError): preview_cabinet_placement(a,base,x,0)
        missing=dict(base);missing.pop('Cab_Pos_Y')
        with self.assertRaises(ValueError): preview_cabinet_placement(a,missing,1600,100)
        self.assertEqual(base,saved)

    def test_eleven_panels_two_owned_cuts_preflight_and_distinct_hash(self):
        snapshot = layout()
        result = compose_layout(snapshot)
        a = result.assembly
        preflight(a)
        self.assertEqual((len(a.panels), len(a.operations)), (11, 2))
        self.assertEqual({o.target_panel_id for o in a.operations},
                         {'cabinet.001.panel.left.001', 'cabinet.001.panel.right.001'})
        self.assertEqual({o.mating_panel_id for o in a.operations}, {'cabinet.001.panel.shelf.001'})
        ids = [p.stable_id for p in a.panels]+[o.operation_id for o in a.operations]+[c.constraint_id for c in a.constraints]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(a.spec_hash, hashlib.sha256(result.manifest_json.encode()).hexdigest())
        self.assertNotIn(a.spec_hash, [s.spec_hash for s in sources(snapshot)])
        self.assertEqual(json.loads(result.manifest_json)['qualification']['live_layout_geometry'], 'UNKNOWN')
        with self.assertRaises(FrozenInstanceError):
            result.manifest_json = '{}'
        with self.assertRaises(FrozenInstanceError):
            result.assembly.spec_hash = 'changed'

    def test_independent_symbolic_translations_and_formula_preservation(self):
        for bed_xyz, cab_xyz in [((0, 0, 0), (1500, 0, 0)), ((-17.5, 22, 5), (1600, -37, 101)),
                                 ((0, 0, -50), (0, 2000, 70))]:
            snapshot = layout(bed_xyz, cab_xyz)
            a = compose_layout(snapshot).assembly
            original = sources(snapshot)
            self.assertEqual(a.parameters.params, original[0].parameters.params+original[1].parameters.params)
            env = a.parameters.resolve()
            for entry, source in zip(snapshot['instances'], original):
                local_env = source.parameters.resolve()
                for panel in source.panels:
                    moved = a.panel(entry['instance_id']+'.'+panel.stable_id)
                    self.assertEqual(moved.box.size, panel.box.size)
                    self.assertEqual(moved.box.refs(), panel.box.refs())
                    for origin, local, offset in zip(moved.box.origin, panel.box.origin, entry['translation_mm']):
                        self.assertAlmostEqual(origin.eval(env), local.eval(local_env)+offset)
                        self.assertIn(' mm', origin.render())
                    self.assertAlmostEqual(moved.box.resolve(env).volume, panel.box.resolve(local_env).volume, places=5)
                for op in source.operations:
                    moved = next(o for o in a.operations if o.operation_id==entry['instance_id']+'.'+op.operation_id)
                    self.assertEqual(moved.cut.size, op.cut.size)
                    self.assertEqual(moved.groove_depth, op.groove_depth)
                    self.assertEqual(moved.slot_clearance, op.slot_clearance)
                    self.assertEqual(moved.end_clearance, op.end_clearance)
                    self.assertEqual((moved.side, moved.open_at, moved.process), (op.side, op.open_at, op.process))
                for c in source.constraints:
                    moved = next(v for v in a.constraints if v.constraint_id==entry['instance_id']+'.'+c.constraint_id)
                    self.assertEqual((moved.lhs,moved.op,moved.rhs), (c.lhs,c.op,c.rhs))
            # Expressions stay parameter-driven (not a qualification of later edits).
            changed = a.parameters.resolve({'Bed_Width': 1500, 'Cab_Width': 1250})
            self.assertEqual(a.panel('bed.001.bed.deck.001').box.resolve(changed).size[0], 1500)
            self.assertAlmostEqual(a.panel('cabinet.001.panel.right.001').box.resolve(changed).lo[0], cab_xyz[0]+1232)

    def test_determinism_manifest_mapping_and_input_preservation(self):
        snapshot = layout(); before = copy.deepcopy(snapshot)
        first = compose_layout(snapshot)
        self.assertEqual(first, compose_layout(snapshot))
        self.assertEqual(snapshot, before)
        manifest = json.loads(first.manifest_json)
        for entry, source in zip(snapshot['instances'], manifest['sources']):
            self.assertEqual(source['specification'], entry['specification'])
            for p in source['panels']:
                self.assertEqual(p['composed_id'], source['instance_id']+'.'+p['local_id'])
                expected = next(v for v in entry['panels'] if v['local_panel_id']==p['local_id'])
                self.assertEqual(p['world_box'], expected['world_box'])
            preview = make_preview(entry['specification']['canonical_json'])
            self.assertEqual(canonical_json(preview), canonical_json(entry['standalone_preview']))
            self.assertEqual(csv_text(preview), csv_text(entry['standalone_preview']))
        self.assertNotEqual(first.assembly.spec_hash, compose_layout(layout(cabinet=(1600,0,0))).assembly.spec_hash)

    def test_tampered_snapshot_spec_hash_bounds_parameters_ownership_refused(self):
        mutations = [
            lambda s: s.update(format='wrong'),
            lambda s: s.update(compile_ready_fusion_assembly=True),
            lambda s: s['instances'][0]['specification'].update(design_spec_hash='wrong'),
            lambda s: s['instances'][0]['specification'].update(canonical_json='{}'),
            lambda s: s['instances'][1].update(assembly_spec_hash='wrong'),
            lambda s: s['instances'][0]['parameters_mm'].update(Bed_Width=1500),
            lambda s: s['instances'][0]['panels'][0]['world_box'].update(volume_mm3=1),
            lambda s: s['instances'][1]['operations'][0].update(mating_panel_id='bed.deck.001'),
            lambda s: s['instances'][1].update(instance_id='bed.001'),
            lambda s: s['instances'][0]['panels'].append(s['instances'][0]['panels'][0]),
            lambda s: s['instances'][0].pop('specification'),
        ]
        for change in mutations:
            snapshot = layout(); change(snapshot)
            with self.subTest(change=change), self.assertRaises(ValueError):
                compose_layout(snapshot)
        for snapshot in (None, {}, {'instances':[{}]}, {'instances':[{},{}]}):
            with self.assertRaises(ValueError):
                compose_layout(snapshot)

    def test_revalidate_collision_contact_and_bad_placements(self):
        for xyz in ([100,100,0], [100,100,-200], [float('nan'),0,0], [float('inf'),0,0],
                    [True,0,0], [1e308,0,0], ['1500',0,0]):
            snapshot = layout(); snapshot['instances'][1]['translation_mm'] = xyz
            with self.subTest(xyz=xyz), self.assertRaises(ValueError):
                compose_layout(snapshot)
        compose_layout(layout(cabinet=(1400,0,0)))
        compose_layout(layout(cabinet=(1400-0.5e-9,0,0)))
        snapshot = layout(); snapshot['instances'][1]['translation_mm'] = [1400-2e-9,0,0]
        with self.assertRaises(ValueError):
            compose_layout(snapshot)

    def test_duplicate_source_ids_parameters_constraints_and_dependency_order_refused(self):
        snapshot = layout(); bed = sources(snapshot)[0]
        # Malformed ordered parameter sets simulate corrupt source evidence.
        def bad_params(params):
            p = object.__new__(ParameterSet)
            object.__setattr__(p, 'params', tuple(params))
            return p
        altered = [replace(bed, panels=bed.panels+(bed.panels[0],)),
                   replace(bed, constraints=bed.constraints+(bed.constraints[0],)),
                   replace(bed, parameters=bad_params(bed.parameters.params+(bed.parameters.params[0],))),
                   replace(bed, parameters=bad_params(reversed(bed.parameters.params))),
                   replace(bed, spec_hash='wrong')]
        for assembly in altered:
            with patch('vandesign.composition.build_bed_platform', return_value=assembly):
                with self.assertRaises(ValueError):
                    compose_layout(snapshot)

    def test_wrong_source_and_remapped_cut_ownership_refused(self):
        snapshot = layout(); cab = sources(snapshot)[1]
        wrong = replace(cab.operations[0], mating_panel_id='panel.top.001')
        with patch('vandesign.composition.build_variant', return_value=replace(cab,operations=(wrong,)+cab.operations[1:])):
            with self.assertRaises(ValueError):
                compose_layout(snapshot)
        def cross_instance(*parts):
            if parts == ('cabinet.001','panel.left.001'):
                return 'bed.001.bed.front.001'
            return make_id(*parts)
        with patch('vandesign.composition.make_id', side_effect=cross_instance):
            with self.assertRaisesRegex(ValueError, 'ownership mismatch'):
                compose_layout(snapshot)


if __name__ == '__main__':
    unittest.main()
