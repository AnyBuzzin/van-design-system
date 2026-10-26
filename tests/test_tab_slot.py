"""Independent offline coupon geometry and evidence checks; no live CAD claims."""
from dataclasses import replace
import json
import math
from types import SimpleNamespace as NS
import unittest

from vandesign.core.tab_slot import TabSlotGeometry, RECEIVER, UPRIGHT
from vandesign.modules.tab_slot import build_tab_slot, preview_tab_slot, NAMES, CUT_IDS, OWNERS
from vandesign.schemas.tab_slot_spec import TabSlotSpec, load_tab_slot_spec
from vandesign.verification.geometry_source import MeasuredBody
from vandesign.verification.tab_slot import measure_coupon_geometry
from vandesign.panel_preview import panel_rows


class IdealCouponSource:
    """Analytic stand-in for negative offline evidence tests only."""
    def __init__(self,coupon):
        self.env=coupon.blanks.parameters.resolve();self.g=coupon.geometry()
        self.faces={}
        for axis,name in ((0,'x'),(1,'y')):
            for side,attr in (('low','lo'),('high','hi')):
                self.faces['tab_'+name+'_'+side]=getattr(self.g.tab,attr)[axis]
                self.faces['slot_'+name+'_'+side]=getattr(self.g.slot,attr)[axis]
        self.faces.update(receiver_top=18,tab_bottom=18-self.g.engagement,shoulder_left=18,shoulder_right=18)
    def parameter_value(self,n):return self.env[n]
    def managed_ids(self):return {RECEIVER:1,UPRIGHT:1}
    def body(self,pid):return MeasuredBody(self.g.bounds[pid],self.g.volumes[pid])
    def interference_count(self,ids):return 0
    def point_in_material(self,pid,p):return self.g.contains(pid,p)
    def coupon_faces(self,g):return self.faces.copy()


class CouponTests(unittest.TestCase):
    def test_default_geometry_clearance_contacts_and_union_volume(self):
        c=build_tab_slot(TabSlotSpec());g=c.geometry();env=c.blanks.parameters.resolve()
        self.assertEqual(g.slot.lo,(69.75,50.75,0));self.assertEqual(g.slot.hi,(130.25,69.25,18))
        self.assertEqual(g.tab.lo,(70,51,0));self.assertEqual(g.tab.hi,(130,69,18))
        self.assertEqual(g.volumes[UPRIGHT],235440)
        self.assertAlmostEqual(g.volumes[RECEIVER],411483.6239802369)
        self.assertEqual(g.centres[0],(69.75+3/math.sqrt(2),50.75+3/math.sqrt(2)))
        self.assertEqual(OWNERS,(UPRIGHT,UPRIGHT,RECEIVER,RECEIVER,RECEIVER,RECEIVER,RECEIVER))
        self.assertEqual(len(set(CUT_IDS)),7)
        self.assertAlmostEqual(sum(g.cut_volumes),432000+120*118*18-sum(g.volumes.values()))
        for actual,expected in zip(c.shoulders,g.shoulders):self.assertEqual(actual.resolve(env),expected)
        self.assertEqual(c.slot.resolve(env),g.slot)
        self.assertEqual(tuple(tuple(e.eval(env) for e in centre) for centre in c.centres),g.centres)
        self.assertEqual(c.radius.eval(env),3)
        for x in g.contact_x:
            self.assertTrue(g.contains(RECEIVER,(x,60,17.99)))
            self.assertTrue(g.contains(UPRIGHT,(x,60,18.01)))
        # Only the tab enters receiver Z; it is entirely inside the removed slot.
        self.assertTrue(g.slot.contains_box(g.tab,eps=0))
        self.assertEqual(g.bounds[RECEIVER].hi[2],18)
        self.assertEqual(g.tab.hi[2],18)
        with self.assertRaisesRegex(ValueError,'unsupported panel role'):panel_rows(c.blanks)

    def test_relief_union_independent_segment_quadrature(self):
        for diameter in (2,6,8):
            g=TabSlotGeometry(60,18,.5,diameter);r=diameter/2;a=r/math.sqrt(2);steps=20000
            dx=(r-a)/steps
            segment=sum(2*math.sqrt(r*r-(a+(i+.5)*dx)**2)*dx for i in range(steps))
            # Four circles, two exterior caps each; zero area outside both edges.
            self.assertAlmostEqual(8*segment,4*g.relief_extra_area,delta=2e-6)
            for (cx,cy),corner in zip(g.centres,((g.slot.lo[0],g.slot.lo[1]),(g.slot.hi[0],g.slot.lo[1]),
                                                (g.slot.hi[0],g.slot.hi[1]),(g.slot.lo[0],g.slot.hi[1]))):
                self.assertAlmostEqual(math.dist((cx,cy),corner),r)
            self.assertLess(4*g.relief_extra_area,4*math.pi*r*r)

    def test_independent_changes_regeneration_and_refusal(self):
        spec=TabSlotSpec();baseline=build_tab_slot(spec)
        for field,value in (('tab_width_mm',70),('engagement_mm',12),('clearance_mm',1),('tool_diameter_mm',8)):
            s=replace(spec,**{field:value});c=build_tab_slot(s);g=c.geometry();env=c.blanks.parameters.resolve()
            self.assertNotEqual(s.spec_hash(),spec.spec_hash());self.assertEqual([p.stable_id for p in c.blanks.panels],[RECEIVER,UPRIGHT])
            self.assertEqual(c.slot.resolve(env),g.slot)
            self.assertEqual(tuple(tuple(e.eval(env) for e in centre) for centre in c.centres),g.centres)
            self.assertEqual(tuple(b.resolve(env) for b in c.shoulders),g.shoulders)
            self.assertEqual(preview_tab_slot(env)['clearance_per_face_mm'],s.clearance_mm/2)
            self.assertEqual(measure_coupon_geometry(c,IdealCouponSource(c))['outcome'],'PASS')
            self.assertTrue(g.slot.contains_box(g.tab,eps=0))
        self.assertEqual(build_tab_slot(spec),baseline)
        self.assertEqual(load_tab_slot_spec(spec.to_json()),spec)
        self.assertEqual(TabSlotSpec(60.,18.,.5,6.,18.).spec_hash(),spec.spec_hash())
        for field,value in (('tab_width_mm',120),('tab_width_mm',0),('engagement_mm',19),('engagement_mm',0),
                            ('clearance_mm',-1),('clearance_mm',90),('tool_diameter_mm',12),('tool_diameter_mm',0),('thickness_mm',15)):
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):replace(spec,**{field:value})
        self.assertEqual(TabSlotSpec(clearance_mm=0).clearance_mm,0)

    def test_strict_version_and_numeric_types(self):
        for field in ('tab_width_mm','engagement_mm','clearance_mm','tool_diameter_mm','thickness_mm'):
            for value in (True,None,'6',float('nan'),float('inf')):
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):TabSlotSpec(**{field:value})
        raw=json.loads(TabSlotSpec().to_json())
        for obj in ([],{},dict(raw,extra=1),dict(raw,schema_version='0.1'),dict(raw,parameters={})):
            with self.assertRaises(ValueError):load_tab_slot_spec(json.dumps(obj))
        with self.assertRaises(ValueError):load_tab_slot_spec('{"a":1,"a":2}')
        with self.assertRaises(ValueError):preview_tab_slot(dict(zip(NAMES,(60,18,.5,12))))
        with self.assertRaises(ValueError):preview_tab_slot({'Joint_Tool_Diameter':6})

    def test_measured_evidence_not_arithmetic_pass(self):
        c=build_tab_slot(TabSlotSpec());s=IdealCouponSource(c)
        r=measure_coupon_geometry(c,s);self.assertEqual(r['outcome'],'PASS')
        self.assertEqual(r['measured_fit_mm']['clearance_x_low'],.25)
        s.faces['slot_x_low']+=.1
        self.assertEqual(measure_coupon_geometry(c,s)['outcome'],'FAIL')
        s=IdealCouponSource(c);s.point_in_material=lambda *a:None
        self.assertEqual(measure_coupon_geometry(c,s)['outcome'],'UNKNOWN')
        s=IdealCouponSource(c);s.point_in_material=lambda *a:True
        self.assertEqual(measure_coupon_geometry(c,s)['outcome'],'FAIL')
        s=IdealCouponSource(c);s.body=lambda pid:MeasuredBody(s.g.bounds[pid],s.g.bounds[pid].volume)
        self.assertEqual(measure_coupon_geometry(c,s)['outcome'],'FAIL')
        s=IdealCouponSource(c);s.interference_count=lambda ids:1
        self.assertEqual(measure_coupon_geometry(c,s)['outcome'],'FAIL')
        s=IdealCouponSource(c);s.body=lambda pid:MeasuredBody(s.g.bounds[pid],float('nan'))
        with self.assertRaises(ValueError):measure_coupon_geometry(c,s)
