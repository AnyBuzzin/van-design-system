"""Offline contracts only: fake API success is not live CAD qualification."""
from copy import deepcopy
from dataclasses import replace
import importlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from vandesign.core.geometry import Box
from vandesign.manufacturing.profile import (Arc, Hole, Pocket, ThroughCut, contains_point)
from vandesign.manufacturing.dxf import export_profiles, read_dxf, loop_areas, pocket_layer
from vandesign.modules.profile_fixture import (FIXTURE,PARAMETER,PARAMETERS,resolve_profiles,validate_panels,
    feature_loop,feature_depth,feature_start,feature_id,request_valid,inventory,spec_hash)
from vandesign.verification.geometry_source import MeasuredBody
from vandesign.verification.profile_panel import probes,measure_profiles,expected_evidence


class IdealSource:
    def __init__(self,t=18,noise=0):
        self.panels={p.profile.panel_id:p for p in resolve_profiles({PARAMETER:t})};self.t=t;self.noise=noise
    def parameter_value(self,name):return self.t+self.noise
    def managed_ids(self):return dict.fromkeys(self.panels,1)
    def interference_count(self,ids):return 0
    def body(self,pid):
        p=self.panels[pid];b=p.box
        return MeasuredBody(Box(tuple(v+self.noise for v in b.lo),tuple(v+self.noise for v in b.hi)),p.profile.volume_mm3+self.noise)
    def point_in_material(self,pid,point):
        panel=self.panels[pid];p=panel.profile;x,y,z=(a-b for a,b in zip(point,panel.origin))
        if not 0<z<p.thickness or contains_point(p.outline,(x,y)) is not True:return False
        for f in p.features:
            start=feature_start(f).eval({PARAMETER:p.thickness});depth=feature_depth(f).eval({PARAMETER:p.thickness})
            if start<z<start+depth and contains_point(feature_loop(f),(x,y)) is True:return False
        return True


class Items:
    def __init__(self,values=()):self.values=list(values)
    @property
    def count(self):return len(self.values)
    def item(self,i):return self.values[i]


class Profiles(unittest.TestCase):
    def test_geometry_regeneration_and_thickness(self):
        a,b=resolve_profiles(),resolve_profiles({PARAMETER:20})
        self.assertEqual(a,resolve_profiles());self.assertEqual(spec_hash(),spec_hash())
        for x,y in zip(a,b):
            self.assertEqual(x.profile.outline,y.profile.outline);self.assertEqual(x.profile.features,y.profile.features)
            self.assertAlmostEqual(y.profile.volume_mm3-x.profile.volume_mm3,2*x.profile.net_area_mm2)
        for t in (None,True,float('nan'),float('inf'),0,5,6,31):
            with self.subTest(t=t),self.assertRaises((TypeError,ValueError)):
                resolve_profiles({PARAMETER:t})
        request_valid({'fixture':FIXTURE})
        for req in ({'fixture':'bad'},{'fixture':FIXTURE,'code':'x'},{'fixture':FIXTURE,'thickness':20}):
            with self.assertRaises(ValueError):request_valid(req)

    def test_overlap_depth_and_identity_refuse_before_cad(self):
        a,b=resolve_profiles()
        for panels in ((a,a),(a,replace(b,origin=(0,0,0))),
                       (a,replace(b,profile=replace(b.profile,features=b.profile.features+(b.profile.features[0],))))):
            with self.assertRaises(ValueError):validate_panels(panels)
        with self.assertRaises(ValueError):replace(b.profile,features=(Pocket(feature_loop(b.profile.features[0]),18,'top'),))

    def test_noisy_measurements_missing_probes_and_wrong_geometry(self):
        for t in (18,20):
            s=IdealSource(t,1e-10);r=measure_profiles(s,{PARAMETER:t});self.assertEqual(r['outcome'],'PASS')
            self.assertEqual(len([c for c in r['checks'] if 'point_mm' in c]),sum(len(probes(p)) for p in s.panels.values()))
        for field,replacement in [('parameter_value',lambda n:None),('managed_ids',lambda:None),
                                  ('interference_count',lambda ids:1),('point_in_material',lambda *args:None),
                                  ('body',lambda pid:MeasuredBody(IdealSource().panels[pid].box,123))]:
            s=IdealSource();setattr(s,field,replacement);self.assertEqual(measure_profiles(s,{PARAMETER:18})['outcome'],'FAIL')

    def test_dxf_same_profiles_all_feature_loops(self):
        for t in (18,20):
            with tempfile.TemporaryDirectory() as d:
                panels=resolve_profiles({PARAMETER:t});export_profiles([p.profile for p in panels],d)
                for panel in panels:
                    p=panel.profile;ents=read_dxf((Path(d)/(p.panel_id+'.dxf')).read_text())
                    self.assertAlmostEqual(loop_areas(ents,'OUTLINE')[0],p.outline.area,delta=1e-3)
                    for f in p.features:
                        if isinstance(f,Hole):
                            circle=next(e for e in ents if e['type']=='CIRCLE')
                            self.assertEqual((circle[10],circle[20],circle[40]),(*f.center,f.diameter/2))
                        else:
                            layer='THROUGH' if isinstance(f,ThroughCut) else pocket_layer(f.face,f.depth)
                            self.assertAlmostEqual(loop_areas(ents,layer)[0],f.loop.area,delta=1e-3)


class ProfileAPI(unittest.TestCase):
    def setUp(self):
        self.fake=NS(core=NS(Point3D=NS(create=lambda *p:p),Matrix3D=NS(create=lambda:None),
                            ValueInput=NS(createByString=lambda s:s)),fusion=NS(
            Design=NS(cast=lambda d:d),DesignTypes=NS(ParametricDesignType=1),
            FeatureOperations=NS(NewBodyFeatureOperation=0,CutFeatureOperation=1),
            FeatureHealthStates=NS(HealthyFeatureHealthState=0)),doEvents=Mock())
        with patch.dict(sys.modules,{'adsk':self.fake,'adsk.core':self.fake.core,'adsk.fusion':self.fake.fusion}):
            self.adapter=importlib.import_module('vandesign.cad.fusion.profile_panel')
            self.run=importlib.import_module('vandesign.cad.fusion.profile_build')
        for m in (self.adapter,self.run):
            p=patch.object(m,'adsk',self.fake);p.start();self.addCleanup(p.stop)

    def test_loop_api_units_fixed_curves_signed_arcs_and_failures(self):
        curves=[];lines=[];arcs=[]
        def add(target,*args):
            target.append(args);c=NS(isFixed=False);curves.append(c);return c
        sketch=NS(profiles=Items([1]),sketchCurves=NS(sketchLines=NS(addByTwoPoints=lambda *a:add(lines,*a)),
                    sketchArcs=NS(addByCenterStartSweep=lambda *a:add(arcs,*a))))
        comp=NS(xYConstructionPlane='XY',sketches=NS(add=lambda plane:sketch))
        panel=resolve_profiles()[0]
        self.adapter.ProfileAdapter._loop_sketch(None,comp,'outline',panel.profile.outline,(100,200,0))
        self.assertEqual(lines[0],((10,20,0),(70,20,0)))
        self.assertAlmostEqual(arcs[0][2],math.pi/2);self.assertTrue(all(c.isFixed for c in curves))
        sketch.profiles=Items()
        with self.assertRaisesRegex(RuntimeError,'one closed'):
            self.adapter.ProfileAdapter._loop_sketch(None,comp,'outline',panel.profile.outline,(0,0,0))

    def test_compile_explicit_targets_depth_bindings_and_mate_failure(self):
        for bad in (False,True):
            panels=resolve_profiles();components=[];calls=[]
            def new_component():
                values={}
                attrs=NS(add=lambda g,k,v:values.update({k:v}),itemByName=lambda g,k:NS(value=values[k]) if k in values else None)
                c=NS(attributes=attrs,bRepBodies=Items());components.append(c);return NS(component=c)
            a=self.adapter.ProfileAdapter.__new__(self.adapter.ProfileAdapter)
            a.root=NS(occurrences=NS(count=0,addNewComponent=lambda m:new_component()),bRepBodies=Items(),sketches=Items())
            a.design=NS(userParameters=NS(count=0,add=Mock()),timeline=NS(count=0));a._loop_sketch=Mock(return_value='sketch')
            def extrude(c,sketch,name,z,depth,op,participants=None):
                calls.append((name,z,depth,op,participants));p=panels[components.index(c)].profile
                if op==0:
                    c.bRepBodies.values=[NS(volume=p.outline.area*p.thickness/1000,parentComponent=c,isValid=True,isSolid=True)]
                else:
                    self.assertEqual(participants,[c.bRepBodies.item(0)])
                    index=next(i for i in range(len(p.features)) if feature_id(p,i)==name);f=p.features[index]
                    c.bRepBodies.item(0).volume-=feature_loop(f).area*feature_depth(f).eval({PARAMETER:18})/1000
                    if bad:components[0].bRepBodies.item(0).volume-=1
                return NS(bodies=c.bRepBodies,attributes=NS(add=Mock()))
            a._extrude=Mock(side_effect=extrude);records=[]
            with patch.object(self.adapter,'affected_body_check',return_value={'status':'PASS'}):
                if bad:
                    with self.assertRaisesRegex(RuntimeError,'unexpected material'):a.compile_profiles(panels,Mock(),records)
                    self.assertEqual(len(records),1);self.assertEqual(records[0]['outcome'],'FAIL')
                else:
                    a.compile_profiles(panels,Mock(),records);self.assertEqual(len(records),3)
                    self.assertTrue(all(r['outcome']=='PASS' for r in records))
                    self.assertEqual(calls[2][2],PARAMETER)
                    self.assertIn(PARAMETER,calls[3][1]);self.assertEqual(calls[3][2],'6 mm')
                    self.assertEqual(calls[4][1],'(0 mm + 0 mm)')
            a._extrude.reset_mock()
            with self.assertRaises(ValueError):a.compile_profiles((panels[0],panels[0]),Mock(),[])
            a._extrude.assert_not_called()

    def report(self,t):
        r=measure_profiles(IdealSource(t,1e-10),{PARAMETER:t});r['counts']=inventory(resolve_profiles({PARAMETER:t}))
        for cid in expected_evidence()['required_checks']:
            if cid not in {c['check_id'] for c in r['checks']}:r['checks'].append(dict(check_id=cid,status='PASS'))
        return r

    def test_measured_feature_ids_health_and_actual_owner_fail_closed(self):
        panels=resolve_profiles();occurrences=[];cuts=[]
        for panel in panels:
            p=panel.profile;comp=NS(attributes=NS(itemByName=lambda g,k,pid=p.panel_id:NS(value=pid)))
            body=NS(isValid=True,isSolid=True,parentComponent=comp);comp.bRepBodies=Items([body])
            features=[NS(operation=0,healthState=0,isSuppressed=False)]
            for i in range(len(p.features)):
                cid=feature_id(p,i)
                f=NS(operation=1,healthState=0,isSuppressed=False,bodies=Items([body]),parentComponent=comp,
                     attributes=NS(itemByName=lambda g,k,cid=cid:NS(value=cid)))
                features.append(f);cuts.append(f)
            comp.features=NS(count=len(features),extrudeFeatures=Items(features))
            comp.sketches=Items([NS(profiles=Items([1]),healthState=0,isFullyConstrained=True) for _ in features])
            occurrences.append(NS(component=comp))
        counts=inventory(panels)
        class ReadOnlyTimeline:
            count=counts['timeline_items']
            @property
            def markerPosition(self):return self.count
            @markerPosition.setter
            def markerPosition(self,v):raise AssertionError('No timeline writes permitted')
        design=NS(rootComponent=NS(occurrences=Items(occurrences),bRepBodies=Items(),sketches=Items()),
                  timeline=ReadOnlyTimeline())
        with patch.object(self.adapter,'FusionGeometrySource',return_value=IdealSource()), \
             patch.object(self.adapter,'_design_counts',return_value=counts):
            r=self.adapter.measure_profile_design(design,panels,Mock(),18)
            self.assertEqual(r['outcome'],'PASS')
            cuts[0].bodies=occurrences[0].component.bRepBodies
            self.assertEqual(self.adapter.measure_profile_design(design,panels,Mock(),18)['outcome'],'FAIL')
            cuts[0].bodies=occurrences[1].component.bRepBodies
            cuts[1].attributes=cuts[0].attributes
            with self.assertRaisesRegex(RuntimeError,'Duplicate'):
                self.adapter.measure_profile_design(design,panels,Mock(),18)

    def test_lifecycle_stops_on_failure_without_restore_or_document_operations(self):
        for bad in (False,True):
            parameter=NS(expression='18 mm');doc=NS(isSaved=False,isModified=False,save=Mock(),close=Mock())
            design=NS(designType=1,userParameters=NS(itemByName=lambda n:parameter))
            app=NS(activeDocument=doc,activeProduct=design,activeViewport=NS(fit=Mock()))
            reports=[self.report(t) for t in (18,20,18,18)]
            if bad:reports[1]['outcome']='FAIL'
            with tempfile.TemporaryDirectory() as d,patch.object(self.run,'ProfileAdapter'), \
                 patch.object(self.run,'measure_profile_design',side_effect=reports) as measure,patch.object(self.run,'snapshot',return_value={'same':True}):
                if bad:
                    with self.assertRaisesRegex(RuntimeError,'no automatic'):self.run.run_profile_fixture(app,d,Mock(),{'fixture':FIXTURE})
                else:self.run.run_profile_fixture(app,d,Mock(),{'fixture':FIXTURE})
                result=json.loads((Path(d)/'arrangement.json').read_text())
                self.assertEqual(result['outcome'],'FAIL' if bad else 'PASS')
                self.assertEqual(measure.call_count,2 if bad else 4)
                self.assertEqual(parameter.expression,'20 mm' if bad else '18 mm')
                with self.assertRaisesRegex(RuntimeError,'no retry'):self.run.run_profile_fixture(app,d,Mock(),{'fixture':FIXTURE})
            doc.save.assert_not_called();doc.close.assert_not_called()
