"""Independent E1.1 offline geometry checks; not Fusion qualification."""
from dataclasses import replace
import json
import math
from types import SimpleNamespace as NS
import unittest

from vandesign.cad.protocol import preflight
from vandesign.core.expr import Mm
from vandesign.core.geometry import RoundedCornerOutline, BoxExpr
from vandesign.modules.rounded_panel import build_rounded_panel, preview_rounded_panel, PANEL_ID
from vandesign.schemas.rounded_panel_spec import RoundedPanelSpec, load_rounded_panel_spec
from vandesign.verification.geometry_source import MeasuredBody
from vandesign.verification.validate import validate
from vandesign.panel_preview import panel_rows


class RoundedTests(unittest.TestCase):
    def test_closed_ccw_tangent_outline_and_independent_integral(self):
        for w, l, r in ((600,800,50),(700,800,50),(600,900,50),(600,800,75),(60,80,59)):
            o = RoundedCornerOutline(w,l,r)
            a,b,c,d,e = o.vertices
            self.assertEqual(o.lines, ((a,b),(b,c),(d,e),(e,a)))
            centre = o.arc['center']
            self.assertEqual(c, o.arc['start']); self.assertEqual(d, o.arc['end'])
            self.assertEqual(c, (w,l-r)); self.assertEqual(d, (w-r,l))
            self.assertEqual(o.arc['sweep_radians'], math.pi/2)
            # Radius vectors perpendicular to adjacent straight edges.
            for endpoint, tangent in ((c,(0,1)), (d,(-1,0))):
                rv = tuple(x-y for x,y in zip(endpoint,centre))
                self.assertAlmostEqual(math.hypot(*rv),r)
                self.assertEqual(sum(x*y for x,y in zip(rv,tangent)),0)
            # Green's theorem, independently integrating the boundary segments.
            integral = sum(x1*y2-y1*x2 for (x1,y1),(x2,y2) in o.lines)
            integral += centre[0]*r + centre[1]*r + r*r*math.pi/2
            self.assertAlmostEqual(o.area_mm2, integral/2)
            self.assertEqual((min(p[0] for p in o.vertices),min(p[1] for p in o.vertices)),(0,0))
            self.assertEqual((max(p[0] for p in o.vertices),max(p[1] for p in o.vertices)),(w,l))
            # Dense arc samples stay in the corner square and advance CCW.
            pts=[(centre[0]+r*math.cos(i*math.pi/200),centre[1]+r*math.sin(i*math.pi/200)) for i in range(101)]
            self.assertTrue(all(w-r-1e-9<=x<=w and l-r<=y<=l for x,y in pts))
            self.assertTrue(all(x1>=x2 and y1<=y2 for (x1,y1),(x2,y2) in zip(pts,pts[1:])))

    def test_dimensions_regenerate_identity_and_restore(self):
        spec=RoundedPanelSpec(); baseline=build_rounded_panel(spec)
        for field,value in (('width_mm',700),('length_mm',900),('radius_mm',75)):
            changed=replace(spec,**{field:value}); a=build_rounded_panel(changed)
            self.assertEqual(a.panels[0].stable_id,PANEL_ID)
            self.assertNotEqual(a.spec_hash,baseline.spec_hash)
            self.assertEqual(a.panels[0].box.resolve(a.parameters.resolve()).size,
                             (changed.width_mm,changed.length_mm,18))
            preview=preview_rounded_panel(a.parameters.resolve())
            expected=changed.width_mm*changed.length_mm-(1-math.pi/4)*changed.radius_mm**2
            self.assertAlmostEqual(preview['finished_volume_mm3'],expected*18)
            self.assertEqual(preview['enclosing_blank_mm'],[changed.width_mm,changed.length_mm,18])
        self.assertEqual(build_rounded_panel(spec),baseline)
        self.assertEqual(load_rounded_panel_spec(spec.to_json()),spec)
        self.assertEqual(RoundedPanelSpec(600.,800.,50.,18.).spec_hash(),spec.spec_hash())

    def test_strict_spec_and_preview_fail_closed(self):
        for field in ('width_mm','length_mm','radius_mm'):
            for value in (None,True,'50',0,-1,float('nan'),float('inf'),10001):
                with self.subTest(field=field,value=value), self.assertRaises(ValueError):
                    RoundedPanelSpec(**{field:value})
        for radius in (600,800,900):
            with self.assertRaises(ValueError): RoundedPanelSpec(radius_mm=radius)
        for thickness in (5,10,12,15,True,None,float('nan')):
            with self.assertRaises(ValueError): RoundedPanelSpec(thickness_mm=thickness)
        raw=json.loads(RoundedPanelSpec().to_json())
        for invalid in ({},[],dict(raw,extra=1),dict(raw,schema_version='0.1'),
                        dict(raw,parameters=dict(raw['parameters'],unknown=2))):
            with self.assertRaises(ValueError):load_rounded_panel_spec(json.dumps(invalid))
        with self.assertRaises(ValueError):load_rounded_panel_spec('{"a":1,"a":2}')
        with self.assertRaises(ValueError):preview_rounded_panel({'Panel_Radius':50})

    def test_shape_guards_and_rectangular_preview_refusal(self):
        a=build_rounded_panel(RoundedPanelSpec());p=a.panels[0]
        for panel in (replace(p,corner_radius=None),replace(p,corner_radius=3),replace(p,role='deck'),
                      replace(p,box=BoxExpr((Mm(1),Mm(0),Mm(0)),p.box.size)),
                      replace(p,box=BoxExpr(p.box.origin,(p.box.size[0],p.box.size[1],Mm(15))))):
            with self.assertRaises(ValueError):preflight(replace(a,panels=(panel,)))
        with self.assertRaises(ValueError):preflight(replace(a,panels=(p,replace(p,stable_id='other.001'))))
        with self.assertRaisesRegex(ValueError,'unsupported panel role'):panel_rows(a)

    def test_legacy_panel_hash_and_identity_unchanged(self):
        from vandesign.modules.cabinet import build_cabinet
        from vandesign.schemas.cabinet_spec import CabinetSpec
        a=build_cabinet(CabinetSpec())
        self.assertEqual(a.spec_hash,'a0a43e005535b33f069dd786dc847682734819a09bd0803650688bb5e4b0a750')
        for p in a.panels:
            self.assertIsNone(p.corner_radius)
            self.assertEqual(hash(p),hash((p.stable_id,p.display_name,p.role,p.material_ref,p.box,p.grain_axis)))

    def test_actual_volume_comparison_uses_contour_not_blank(self):
        a=build_rounded_panel(RoundedPanelSpec());env=a.parameters.resolve()
        box=a.panels[0].box.resolve(env)
        source=NS(parameter_value=env.get,managed_ids=lambda:{PANEL_ID:1},diagnostics=[])
        expected=(600*800-(1-math.pi/4)*50**2)*18
        for volume,outcome in ((expected,'PASS'),(box.volume,'FAIL'),(None,'UNKNOWN'),(float('nan'),'FAIL')):
            source.body=lambda pid:MeasuredBody(box,volume)
            rep=validate(a,source)
            self.assertEqual(rep.verdict,outcome)
        source.body=lambda pid:MeasuredBody(box,expected)
        env['Panel_Radius']=600
        self.assertEqual(validate(a,source).verdict,'FAIL')
