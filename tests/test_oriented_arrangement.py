"""Bounded #95 offline integration; simulated readback is not Fusion evidence."""
from copy import deepcopy
from dataclasses import replace
import importlib
import json
import math
import sys
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import test_profile_fixture as fixture
from test_arrangement_job import request, instance
from test_width_bindings import spec
from vandesign.arrangement_job import plan_request, preview_values, expected_evidence, expected_inventory
from vandesign.core.expr import Mm
from vandesign.manufacturing.profile import contains_world_point, world_box
from vandesign.verification.geometry_source import MeasuredBody
from vandesign.verification.profile_panel import measure_oriented, oriented_targets
from vandesign.verification.readback import same_except_readback_noise, with_readback_noise


def native_request(turn=1):
    r = request([{'parameter':'K_Cab_Width','value_mm':1000,'expect':'pass'},
                 {'parameter':'K_Cab_Width','value_mm':999,'expect':'refused'},
                 {'parameter':'K_Cab_Height','value_mm':800,'expect':'refused'}], tool_diameter_mm=6)
    r['arrangement']['instances'] = [instance('k','cabinet_tab_slot','K',spec(),(100,2800,5),turn)]
    return r


class Source:
    def __init__(self, plan, width=1100):
        self.env, profiles, self.targets = oriented_targets(plan, {'K_Cab_Width':width})
        self.profiles = {p.panel_id:p for p in profiles}
    def parameter_value(self, name): return self.env[name]
    def managed_ids(self): return dict.fromkeys(self.targets,1)
    def body(self, pid): return MeasuredBody(*self.targets[pid])
    def point_in_material(self, pid, point): return contains_world_point(self.profiles[pid],point)
    def interference_count(self, ids): return 0


class OrientedPlan(unittest.TestCase):
    def test_shipped_request_is_the_bounded_contract(self):
        path=Path(__file__).parents[1]/'automation/jobs/requests/arrangement_request_tab_slot.json'
        self.assertEqual(json.loads(path.read_text(encoding='utf-8')),native_request())

    def test_width_only_request_and_profile_evidence_for_all_quarter_turns(self):
        for turn in range(4):
            plan = plan_request(native_request(turn))
            e = expected_evidence(plan)
            self.assertEqual(len(e['stages']),5)
            self.assertEqual(len(e['construction_cuts']),2)
            self.assertEqual(e['inventory']['timeline_items'],3*len(e['body_ids'])+2*len(e['construction_cuts']))
            self.assertTrue(e['stages'][0]['point_checks'])
            for width in (1100,1000,1050,1100):
                self.assertEqual(measure_oriented(Source(plan,width),plan)['outcome'],'PASS')
            baseline, edit = e['stages'][:2]
            self.assertNotEqual(baseline['volumes'],edit['volumes'])
            self.assertEqual(baseline['boxes'],e['stages'][2]['boxes'])
            self.assertEqual(json.loads(json.dumps(e)),e)

    def test_unsafe_scope_frozen_provenance_and_wrong_tool_refuse(self):
        for field,value in [('tool_diameter_mm',8),('tool_diameter_mm',None)]:
            r=native_request();r[field]=value
            with self.assertRaises(ValueError):plan_request(r)
        r=native_request();r['arrangement']['instances']*=2
        with self.assertRaises(ValueError):plan_request(r)
        for param,value in [('width_mm',1050),('width_mm',1200)]:
            r=native_request();r['arrangement']['instances'][0]['spec']['cabinet']['parameters'][param]=value
            with self.assertRaises(ValueError):plan_request(r)
        plan=plan_request(native_request())
        base={p.name:p.value_mm for p in plan.arrangement.assembly.parameters.base()}
        for name,value in [('K_Cab_Height',800),('K_Pos_X',110),('K_Cab_Width',999),('K_Cab_Width',1101)]:
            self.assertEqual(preview_values(plan.arrangement,plan.envelope,dict(base,**{name:value}),
                                            plan.profile_bindings)['outcome'],'REFUSED')
        b=plan.profile_bindings['k.panel.bottom.001']
        frozen=replace(b,outline=replace(b.outline,vertices=tuple(tuple(Mm(e.eval(plan.arrangement.assembly.parameters.resolve()))
                                                    for e in xy) for xy in b.outline.vertices)))
        bindings=dict(plan.profile_bindings,**{b.panel_id:frozen})
        self.assertEqual(preview_values(plan.arrangement,plan.envelope,dict(base,K_Cab_Width=1000),bindings)['outcome'],'REFUSED')
        r=native_request();r['edits']=[dict(parameter='K_Cab_Width',value_mm=1100+1e-10,expect='pass')]
        with self.assertRaises(ValueError):plan_request(r)

    def test_missing_or_false_measurements_never_pass(self):
        plan=plan_request(native_request())
        for method,value in [('body',None),('parameter_value',None),('parameter_value',float('nan')),
                             ('managed_ids',{}),('point_in_material',None),('point_in_material',True),
                             ('interference_count',1)]:
            source=Source(plan);setattr(source,method,lambda *args,v=value:v)
            self.assertEqual(measure_oriented(source,plan)['outcome'],'FAIL',(method,value))
        source=Source(plan,1000)
        frozen=Source(plan,1100)
        source.body=frozen.body
        self.assertEqual(measure_oriented(source,plan)['outcome'],'FAIL')
        source=Source(plan);source.env['K_Cab_Shelf_Length']+=1
        self.assertEqual(measure_oriented(source,plan)['outcome'],'FAIL')
        source=Source(plan);source.env['K_Cab_Width']+=1e-12
        self.assertEqual(measure_oriented(source,plan)['outcome'],'PASS')


class XYZ:
    def __init__(self,x,y,z,point=False):self.x,self.y,self.z,self.point=x,y,z,point
    def transformBy(self,matrix):
        v=(self.x,self.y,self.z)
        self.x,self.y,self.z=tuple(sum(v[j]*matrix[j][i] for j in range(3)) for i in range(3))
        return True


class OrientedAPI(unittest.TestCase):
    def setUp(self):
        fixture.ProfileAPI.setUp(self)
        p=patch.dict(sys.modules,{'adsk':self.fake,'adsk.core':self.fake.core,'adsk.fusion':self.fake.fusion,
                                 'vandesign.cad.fusion.profile_panel':self.adapter})
        p.start();self.addCleanup(p.stop)
        self.plan=plan_request(native_request())
        with patch.dict(sys.modules,{'adsk':self.fake,'adsk.core':self.fake.core,'adsk.fusion':self.fake.fusion}):
            self.build=importlib.import_module('vandesign.cad.fusion.arrangement_build')
        p=patch.object(self.build,'adsk',self.fake);p.start();self.addCleanup(p.stop)
        self.fake.core.Point3D.create=lambda *p:XYZ(*p,point=True)
        self.fake.core.Vector3D=NS(create=lambda *p:XYZ(*p))

    def design(self,source):
        Items=fixture.Items
        occs=[];cuts=[]
        for pid in source.targets:
            profile=source.profiles.get(pid)
            comp=NS(attributes=NS(itemByName=lambda g,k,pid=pid:NS(value=pid)))
            body=NS(isValid=True,isSolid=True,parentComponent=comp)
            comp.bRepBodies=Items([body])
            features=[NS(operation=0,healthState=0,isSuppressed=False)]
            for i in range(len(profile.features) if profile else 0):
                cid=pid+'.cut.%03d'%(i+1)
                f=NS(operation=1,healthState=0,isSuppressed=False,bodies=Items([body]),parentComponent=comp,
                     attributes=NS(itemByName=lambda g,k,cid=cid:NS(value=cid)))
                cuts.append(f);features.append(f)
            comp.features=NS(count=len(features),extrudeFeatures=Items(features))
            comp.sketches=Items([NS(healthState=0,profiles=Items([1]),isFullyConstrained=True) for f in features])
            frame=profile.frame if profile else NS(u=(1,0,0),v=(0,1,0),w=(0,0,1))
            occs.append(NS(component=comp,transform2=(frame.u,frame.v,frame.w)))
        counts=expected_evidence(self.plan)['inventory']
        design=NS(rootComponent=NS(occurrences=Items(occs),bRepBodies=Items(),sketches=Items()),
                  timeline=NS(count=counts['timeline_items'],markerPosition=counts['timeline_items']))
        return design,cuts,counts

    def measured(self,width=1100,mutate=None):
        source=Source(self.plan,width);design,cuts,counts=self.design(source)
        if mutate:mutate(design,cuts)
        with patch.object(self.adapter,'FusionGeometrySource',return_value=source), \
             patch.object(self.adapter,'_design_counts',return_value=counts):
            return self.adapter.measure_oriented_design(design,self.plan,Mock())

    def test_frame_health_fully_constrained_ownership_and_restoration(self):
        import random
        base=self.measured();self.assertEqual(base['outcome'],'PASS')
        self.assertEqual(self.measured(1000)['outcome'],'PASS')
        restored=self.measured()
        self.assertTrue(same_except_readback_noise(base,restored))
        self.assertTrue(same_except_readback_noise(base,with_readback_noise(restored,random.Random(95))))
        for mutate in (lambda d,c:setattr(c[0],'isSuppressed',True),
                       lambda d,c:setattr(c[0],'bodies',c[1].bodies),
                       lambda d,c:setattr(d.rootComponent.occurrences.item(0).component.sketches.item(0),'isFullyConstrained',False),
                       lambda d,c:setattr(d.rootComponent.occurrences.item(0),'transform2',((1,0,0),(0,1,0),(0,0,1)))):
            self.assertEqual(self.measured(mutate=mutate)['outcome'],'FAIL')

    def test_native_cut_participants_mate_volume_failure_and_prewrite_refusal(self):
        Items=fixture.Items
        for damage in (False,True):
            a=self.adapter.ProfileAdapter.__new__(self.adapter.ProfileAdapter)
            a.root=NS(occurrences=Items(),bRepBodies=Items(),sketches=Items())
            a.design=NS(userParameters=Items(),timeline=Items())
            source=Source(self.plan);comps={};records=[]
            def compile_boxes(asm):
                self.assertFalse(asm.operations)
                for pid,(box,volume) in source.targets.items():
                    p=source.profiles.get(pid)
                    c=NS(bRepBodies=Items([NS(volume=(p.outline.area*p.thickness if p else volume)/1000)]))
                    comps[pid]=c
            def cut(comp,sketch,cid,start,depth,operation,participants):
                self.assertEqual(participants,[comp.bRepBodies.item(0)])
                owner=next(pid for pid,c in comps.items() if c is comp)
                profile=source.profiles[owner];f=profile.features[int(cid.rsplit('.',1)[1])-1]
                removed=f.loop.area*f.depth
                comp.bRepBodies.item(0).volume-=removed/1000
                if damage:comps['k.panel.shelf.001'].bRepBodies.item(0).volume-=1
                return NS(attributes=NS(add=Mock()))
            a._bound_loop_sketch=Mock(return_value='sketch');a._extrude=Mock(side_effect=cut)
            with patch.object(self.adapter.FusionAdapter,'compile',side_effect=compile_boxes), \
                 patch.object(self.adapter,'_find_occurrences',side_effect=lambda root:{pid:[NS(component=c)] for pid,c in comps.items()}), \
                 patch.object(self.adapter,'affected_body_check',side_effect=lambda cut,op:dict(status='PASS',affected_bodies=[op.target_panel_id],feature_parent=op.target_panel_id)):
                if damage:
                    with self.assertRaisesRegex(RuntimeError,'unexpected material'):a.compile_oriented(self.plan,Mock(),records)
                    self.assertEqual(records[-1]['outcome'],'FAIL')
                    self.assertEqual(len(records),1)
                else:
                    a.compile_oriented(self.plan,Mock(),records)
                    self.assertEqual(len(records),len(expected_evidence(self.plan)['construction_cuts']))
                    self.assertTrue(all(r['outcome']=='PASS' for r in records))
            self.assertIsNone(a._native)
        with patch.object(self.adapter.FusionAdapter,'compile') as write:
            with self.assertRaises(ValueError):a.compile_oriented(replace(self.plan,profile_bindings={}),Mock(),[])
            b=self.plan.profile_bindings['k.panel.bottom.001']
            env=self.plan.arrangement.assembly.parameters.resolve()
            frozen=replace(b,outline=replace(b.outline,vertices=tuple(tuple(Mm(e.eval(env)) for e in xy)
                                                                      for xy in b.outline.vertices)))
            bad=replace(self.plan,profile_bindings=dict(self.plan.profile_bindings,**{b.panel_id:frozen}))
            with self.assertRaisesRegex(ValueError,'interval preflight'):
                a.compile_oriented(bad,Mock(),[])
            write.assert_not_called()

    def test_dispatch_edit_restore_refusals_and_failure_never_auto_restore(self):
        for failure in (False,True):
            parameter=NS(expression='1100 mm')
            design=NS(designType=1,rootComponent=NS(occurrences=fixture.Items(),bRepBodies=fixture.Items(),sketches=fixture.Items()),
                      userParameters=NS(count=0,itemByName=lambda name:parameter),timeline=NS(count=0))
            doc=NS(isSaved=False,isModified=False,save=Mock(),close=Mock())
            app=NS(activeDocument=doc,activeProduct=design,activeViewport=NS(fit=Mock()))
            calls=[]
            def measure(d,p,g):
                width=float(parameter.expression.split()[0]);calls.append(width)
                r=self.measured(width)
                if failure and width==1000:r['outcome']='FAIL'
                return r
            with tempfile.TemporaryDirectory() as out, \
                 patch.object(self.adapter.ProfileAdapter,'compile_oriented') as compile_native, \
                 patch.object(self.build,'measure_arrangement',side_effect=measure), \
                 patch.object(self.build,'snapshot',side_effect=lambda d:dict(expression=parameter.expression)), \
                 patch.object(self.build.FusionAdapter,'compile') as old_compile:
                if failure:
                    with self.assertRaisesRegex(RuntimeError,'no automatic restoration'):
                        self.build.run_arrangement(app,out,Mock(),native_request())
                    self.assertEqual(parameter.expression,'1000.0 mm')
                    self.assertEqual(calls,[1100,1000])
                else:
                    self.build.run_arrangement(app,out,Mock(),native_request())
                    self.assertEqual(calls,[1100,1000,1100,1100,1100])
                    self.assertEqual(parameter.expression,'1100 mm')
                    report=json.loads((Path(out)/'arrangement.json').read_text(encoding='utf-8'))
                    self.assertEqual(report['outcome'],'PASS')
                    self.assertEqual(report['dxf']['panels'],8)
                    from vandesign.manufacturing.dxf import read_dxf,loop_areas,pocket_layer
                    for p in Source(self.plan).profiles.values():
                        entities=read_dxf((Path(out)/'dxf'/(p.panel_id+'.dxf')).read_text(encoding='utf-8'))
                        self.assertAlmostEqual(loop_areas(entities,'OUTLINE')[0],p.outline.area,delta=1e-3)
                        for f in p.features:
                            self.assertAlmostEqual(loop_areas(entities,pocket_layer(f.face,f.depth))[0],f.loop.area,delta=1e-3)
                old_compile.assert_not_called();compile_native.assert_called_once()
                with self.assertRaisesRegex(RuntimeError,'no retry'):
                    self.build.run_arrangement(app,out,Mock(),native_request())
                doc.save.assert_not_called();doc.close.assert_not_called()

    def test_panel_native_origin_and_extrusion_follow_width_without_rebuild(self):
        for turn in range(4):
            plan=plan_request(native_request(turn));env,profiles,_=oriented_targets(plan)
            ends=tuple(plan.arrangement.assembly.parameters.resolve({'K_Cab_Width':w}) for w in (1000,1100))
            prepared={}
            for p in profiles:
                b=plan.profile_bindings[p.panel_id]
                offset=tuple(sum((e*k for e,k in zip(b.frame_origin,axis)),Mm(0)) for axis in b.frame_axes)
                prepared[p.panel_id]=(p,b,offset)
            a=self.adapter.ProfileAdapter.__new__(self.adapter.ProfileAdapter)
            a._native=(prepared,env,ends,Mock())
            comp=NS();a._oriented_component=Mock(return_value=comp);a._bound_loop_sketch=Mock(return_value='sketch')
            a._extrude=Mock(return_value=NS(bodies=fixture.Items([NS()])))
            for p,b,offset in prepared.values():
                self.assertIs(a._make_panel(plan.arrangement.assembly.panel(p.panel_id)),comp)
                args=a._extrude.call_args.args
                self.assertEqual((args[3],args[4]),(offset[2].render(),b.thickness.render()))
                self.assertEqual(a._bound_loop_sketch.call_args.args[2:4],(b.outline,offset[:2]))
                for env_at in ends:
                    local=tuple(e.eval(env_at) for e in offset)
                    actual=tuple(sum(local[j]*b.frame_axes[j][i] for j in range(3)) for i in range(3))
                    self.assertEqual(actual,tuple(e.eval(env_at) for e in b.frame_origin))


if __name__ == '__main__':unittest.main()
