import copy
from dataclasses import replace
import unittest
from vandesign.modules.test_envelope import (build_test_envelope,preview_fit,preview_invalid_arch,
    furniture_rows,ARCHES,CABINET_SPEC,NOTICE)
from vandesign.core.geometry import Box
from vandesign.layout_preview import make_layout
from vandesign.composition import compose_layout

class TestEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.a=build_test_envelope(); self.env=self.a.parameters.resolve()
        self.boxes={p.stable_id:p.box.resolve(self.env) for p in self.a.panels}

    def test_nominal_layout_dimensions_clearances_and_determinism(self):
        self.assertEqual(self.a,build_test_envelope())
        self.assertEqual(len(self.a.panels),16)
        self.assertEqual(self.boxes[ARCHES[0]],Box((0,600,0),(196,1400,300)))
        self.assertEqual(self.boxes[ARCHES[1]],Box((1588,600,0),(1784,1400,300)))
        self.assertEqual(self.boxes['bed.001.bed.deck.001'],Box((192,50,682),(1592,1950,700)))
        result=preview_fit(self.a,self.env)
        self.assertEqual((result['deck_to_arch_mm'],result['nominal_right_strip_mm']),(382,634))
        self.assertEqual({o.target_panel_id for o in self.a.operations},
                         {'cabinet.001.panel.left.001','cabinet.001.panel.right.001'})

    def test_guides_outside_clear_space_and_not_in_cut_list(self):
        rows=furniture_rows(self.a)
        self.assertEqual(len(rows),11)
        self.assertFalse(any(r['panel_id'].startswith('reference.') for r in rows))
        self.assertEqual(self.boxes['reference.floor'].hi[2],0)
        self.assertEqual(self.boxes['reference.right'].lo[0],1784)
        self.assertEqual(self.boxes['reference.front'].lo[1],3044)
        self.assertTrue(all(NOTICE in p.display_name for p in self.a.panels if p.stable_id.startswith('reference.')))

    def test_invalid_bed_placement_refused_without_change(self):
        before=copy.deepcopy((self.a,self.env,self.boxes))
        refusal=preview_invalid_arch(self.a,self.env)
        self.assertEqual(refusal['outcome'],'REFUSED')
        self.assertIn('Bed panel intrudes',refusal['reason'])
        self.assertEqual((self.a,self.env,self.boxes),before)

    def test_arches_fit_void_but_cannot_touch_bed_material(self):
        for sid in ('bed.001.bed.deck.001','bed.001.bed.front.001','bed.001.bed.rear.001'):
            boxes=dict(self.boxes); boxes[sid]=Box((192,650,0),(1592,668,682))
            with self.subTest(panel=sid),self.assertRaisesRegex(ValueError,'Bed panel intrudes'):
                preview_fit(self.a,self.env,boxes)

    def test_cabinet_void_reserved_and_outside_rejected(self):
        boxes=dict(self.boxes)
        for sid,b in list(boxes.items()):
            if sid.startswith('cabinet.001.'):
                boxes[sid]=Box((b.lo[0],b.lo[1]-1500,b.lo[2]),(b.hi[0],b.hi[1]-1500,b.hi[2]))
        with self.assertRaisesRegex(ValueError,'Cabinet occupies'):
            preview_fit(self.a,self.env,boxes)
        boxes=dict(self.boxes); boxes['bed.001.bed.deck.001']=Box((-1,50,682),(1399,1950,700))
        with self.assertRaisesRegex(ValueError,'Outside'):
            preview_fit(self.a,self.env,boxes)

    def test_missing_nonfinite_and_extra_measurements_rejected(self):
        for bad in (None,float('nan'),float('inf'),True):
            with self.subTest(value=bad),self.assertRaises(ValueError):
                preview_fit(self.a,dict(self.env,Test_Width=bad))
        boxes=dict(self.boxes);boxes.pop(ARCHES[0])
        with self.assertRaises(ValueError): preview_fit(self.a,self.env,boxes)
        with self.assertRaises(ValueError): preview_fit(self.a,{})

    def test_existing_defaults_and_explicit_spec_identity(self):
        placements=[dict(instance_id='bed.001',translation_mm=[0,0,0]),
                    dict(instance_id='cabinet.001',translation_mm=[1500,0,0])]
        default=make_layout(placements)
        self.assertEqual(default['instances'][1]['parameters_mm']['Cab_Width'],1200)
        changed=make_layout(placements,cabinet_spec_json=CABINET_SPEC)
        self.assertEqual(changed['instances'][1]['parameters_mm']['Cab_Width'],1100)
        with self.assertRaises(ValueError): compose_layout(changed)
        compiled=compose_layout(changed,cabinet_spec_json=CABINET_SPEC).assembly
        self.assertEqual(compiled.parameters.resolve()['Cab_Width'],1100)
        self.assertEqual(len(compiled.panels),11)

    def test_optional_left_sill_absent_but_reference_bbox_checks_still_strict(self):
        from types import SimpleNamespace as NS
        from vandesign.verification.geometry_source import MeasuredBody
        from vandesign.verification.validate import validate
        ids={p.stable_id for p in self.a.panels if p.stable_id.startswith('reference.')}
        self.assertEqual(ids, {'reference.floor','reference.right','reference.front',*ARCHES})
        self.assertNotIn('reference.left',self.boxes)
        original=self.boxes['reference.right']
        shifted=Box(tuple(v+20 if i==0 else v for i,v in enumerate(original.lo)),
                    tuple(v+20 if i==0 else v for i,v in enumerate(original.hi)))
        source=NS(parameter_value=lambda n:self.env[n],
                  body=lambda sid:MeasuredBody(shifted,original.volume) if sid=='reference.right' else None,
                  point_in_material=lambda *args:None,interference_count=lambda ids:None,
                  managed_ids=lambda:{p.stable_id:1 for p in self.a.panels},diagnostics=[])
        report=validate(self.a,source)
        check=next(c for c in report.checks if c.check_id=='reference.right.bbox')
        self.assertEqual(check.status,'FAIL')
        self.assertEqual(check.observed,20)
        self.assertEqual(check.tolerance,0.01)
