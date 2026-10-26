"""Offline fake API contracts; actual CAD qualification remains NOT RUN."""
from dataclasses import replace
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock,patch

from test_tab_slot import IdealCouponSource
from vandesign.core.tab_slot import RECEIVER,UPRIGHT
from vandesign.modules.tab_slot import build_tab_slot,CUT_IDS,OWNERS
from vandesign.schemas.tab_slot_spec import TabSlotSpec
from vandesign.verification.tab_slot import measure_coupon_geometry


class Items:
    def __init__(self,values=()):self.values=list(values)
    @property
    def count(self):return len(self.values)
    def item(self,i):return self.values[i]


class CouponRunnerTests(unittest.TestCase):
    def setUp(self):
        self.fake=NS(core=NS(Point3D=NS(create=lambda *v:v),Plane=NS(cast=lambda x:x)),
            fusion=NS(Design=NS(cast=lambda d:d),DesignTypes=NS(ParametricDesignType=1),
                      DimensionOrientations=NS(HorizontalDimensionOrientation='H',VerticalDimensionOrientation='V'),
                      FeatureOperations=NS(CutFeatureOperation=1,NewBodyFeatureOperation=0),
                      FeatureHealthStates=NS(HealthyFeatureHealthState=0)),doEvents=Mock())
        with patch.dict(sys.modules,{'adsk':self.fake,'adsk.core':self.fake.core,'adsk.fusion':self.fake.fusion}):
            self.m=importlib.import_module('vandesign.cad.fusion.tab_slot')
        p=patch.object(self.m,'adsk',self.fake);p.start();self.addCleanup(p.stop)
        self.coupon=build_tab_slot(TabSlotSpec());self.guard=Mock();self.param=NS(expression='6 mm')
        self.design=NS(designType=1,rootComponent=NS(occurrences=Items(),bRepBodies=Items(),sketches=Items()),
                       userParameters=NS(count=0,itemByName=lambda n:self.param),timeline=NS(count=0))
        self.doc=NS(isSaved=False,isModified=False,save=Mock(),close=Mock())
        self.app=NS(activeDocument=self.doc,activeProduct=self.design,activeViewport=NS(fit=Mock()))

    def report(self,d):
        c=build_tab_slot(TabSlotSpec(tool_diameter_mm=d))
        return measure_coupon_geometry(c,IdealCouponSource(c))

    def run_case(self,failed_stage=None,changed_state=False):
        reports=[self.report(d) for d in (6,8,6,6)]
        if failed_stage is not None:reports[failed_stage]['outcome']='FAIL'
        with tempfile.TemporaryDirectory() as out,patch.object(self.m,'CouponAdapter') as adapter, \
                patch.object(self.m,'measure_coupon',side_effect=reports) as measure, \
                patch.object(self.m,'snapshot',side_effect=[{}, {'changed':1} if changed_state else {}, {}]):
            try:self.m.run_tab_slot(self.app,out,self.guard)
            except RuntimeError:pass
            result=json.loads((Path(out)/'tab_slot.json').read_text())
            with self.assertRaisesRegex(RuntimeError,'no retry'):self.m.run_tab_slot(self.app,out,self.guard)
            self.doc.save.assert_not_called();self.doc.close.assert_not_called()
            return result,adapter,measure

    def test_tool_edit_restoration_refusal_without_lifecycle(self):
        r,a,m=self.run_case();self.assertEqual(r['outcome'],'PASS');self.assertEqual(m.call_count,4)
        self.assertEqual(r['refusal']['outcome'],'REFUSED');self.assertEqual(self.param.expression,'6 mm')
        a.return_value.compile_coupon.assert_called_once()

    def test_fail_stops_without_restore_and_preserves_report(self):
        r,_,m=self.run_case(failed_stage=1)
        self.assertEqual(r['outcome'],'FAIL');self.assertEqual(m.call_count,2)
        self.assertEqual(self.param.expression,'8 mm');self.assertIsNone(r['refusal'])
        self.param.expression='6 mm'
        r,_,m=self.run_case(changed_state=True)
        self.assertEqual(r['outcome'],'FAIL');self.assertEqual(m.call_count,3);self.assertIsNone(r['refusal'])

    def test_saved_dirty_nonempty_and_guard_failure_do_not_compile(self):
        for obj,key,value in ((self.doc,'isSaved',True),(self.doc,'isModified',True),(self.design,'designType',0),
                              (self.design.userParameters,'count',1)):
            old=getattr(obj,key);setattr(obj,key,value)
            r,a,m=self.run_case();self.assertEqual(r['outcome'],'FAIL');a.assert_not_called();m.assert_not_called()
            setattr(obj,key,old)
        self.guard.side_effect=RuntimeError('Protected document changed')
        r,a,_=self.run_case();a.assert_not_called();self.assertEqual(r['outcome'],'FAIL')

    def test_circle_profile_trace_uses_parameter_expressions(self):
        dimensions=[]
        def dimension(*args):
            d=NS(parameter=NS(expression=None));dimensions.append(d);return d
        circle=NS(centerSketchPoint='centre');create=Mock(return_value=circle)
        sketch=NS(originPoint='origin',profiles=NS(count=1),sketchCurves=NS(sketchCircles=NS(addByCenterRadius=create)),
                  sketchDimensions=NS(addDistanceDimension=dimension,addRadialDimension=dimension))
        comp=NS(xYConstructionPlane='XY',sketches=NS(add=Mock(return_value=sketch)))
        a=NS(_eval_cm={'X':7,'Y':5,'R':.3}.__getitem__)
        self.m.CouponAdapter._circle_profile(a,comp,'relief','X','Y','R')
        create.assert_called_once_with((7,5,0),.3)
        self.assertEqual([d.parameter.expression for d in dimensions],['X','Y','R'])
        create.return_value=None
        with self.assertRaisesRegex(RuntimeError,'Circle creation'):self.m.CouponAdapter._circle_profile(a,comp,'relief','X','Y','R')

    def components(self):
        result={}
        env=self.coupon.blanks.parameters.resolve()
        for panel in self.coupon.blanks.panels:
            attrs=NS(itemByName=lambda group,name,pid=panel.stable_id:NS(value=pid))
            comp=NS(attributes=attrs)
            comp.bRepBodies=Items([NS(volume=panel.box.resolve(env).volume/1000,parentComponent=comp,isSolid=True,isValid=True)])
            result[panel.stable_id]=comp
        return result

    def test_seven_cut_targets_actual_removed_caps_and_mate_guard(self):
        for bad_mate in (False,True):
            comps=self.components();a=self.m.CouponAdapter.__new__(self.m.CouponAdapter)
            a.root=NS(occurrences=Items([NS(component=c) for c in comps.values()]))
            a._rectangle_profile=Mock(return_value='rectangle');a._circle_profile=Mock(return_value='circle')
            def extrude(comp,sketch,cid,z,depth,operation,participants):
                i=CUT_IDS.index(cid);self.assertIs(comp,comps[OWNERS[i]])
                self.assertEqual(participants,[comp.bRepBodies.item(0)]);self.assertEqual(operation,1)
                comp.bRepBodies.item(0).volume-=self.coupon.geometry().cut_volumes[i]/1000
                if bad_mate:comps[RECEIVER].bRepBodies.item(0).volume-=.1
            a._extrude=Mock(side_effect=extrude);records=[]
            with patch.object(self.m.FusionAdapter,'compile'):
                if bad_mate:
                    with self.assertRaisesRegex(RuntimeError,'mate change'):a.compile_coupon(self.coupon,self.guard,records)
                    self.assertEqual(len(records),1);self.assertEqual(records[0]['outcome'],'FAIL')
                else:
                    a.compile_coupon(self.coupon,self.guard,records)
                    self.assertEqual(len(records),7);self.assertTrue(all(r['outcome']=='PASS' for r in records))
                    self.assertEqual(a._circle_profile.call_count,4);self.assertEqual(a._rectangle_profile.call_count,3)
                    for pid,c in comps.items():self.assertAlmostEqual(c.bRepBodies.item(0).volume*1000,self.coupon.geometry().volumes[pid])

    def test_ambiguous_or_missing_owner_never_cuts_and_forged_plan_never_compiles(self):
        a=self.m.CouponAdapter.__new__(self.m.CouponAdapter);a._extrude=Mock()
        comps=self.components();a.root=NS(occurrences=Items([NS(component=comps[RECEIVER])]))
        with patch.object(self.m.FusionAdapter,'compile') as compile:
            with self.assertRaisesRegex(RuntimeError,'Ambiguous'):a.compile_coupon(self.coupon,self.guard)
            a._extrude.assert_not_called();compile.reset_mock()
            with self.assertRaisesRegex(ValueError,'canonical'):a.compile_coupon(replace(self.coupon,centres=()),self.guard)
            compile.assert_not_called()

    def test_face_readback_missing_or_ambiguous_fails(self):
        g=self.coupon.geometry()
        def face(axis,value,lo,hi):
            n=[0,0,0];n[axis]=1
            return NS(geometry=NS(normal=NS(**dict(zip('xyz',n)))),
                      boundingBox=NS(minPoint=NS(**dict(zip('xyz',[v/10 for v in lo]))),
                                     maxPoint=NS(**dict(zip('xyz',[v/10 for v in hi])))))
        male=[face(0,70,(70,51,0),(70,69,18)),face(0,130,(130,51,0),(130,69,18)),
              face(1,51,(40,51,0),(160,51,118)),face(1,69,(40,69,0),(160,69,118)),
              face(2,0,(70,51,0),(130,69,0)),face(2,18,(40,51,18),(70,69,18)),
              face(2,18,(130,51,18),(160,69,18))]
        recv=[face(0,69.75,(69.75,55,0),(69.75,65,18)),face(0,130.25,(130.25,55,0),(130.25,65,18)),
              face(1,50.75,(75,50.75,0),(125,50.75,18)),face(1,69.25,(75,69.25,0),(125,69.25,18)),
              face(2,18,(0,0,18),(200,120,18))]
        source=self.m.CouponSource.__new__(self.m.CouponSource)
        source._single_body=lambda pid:NS(faces=Items(recv if pid==RECEIVER else male))
        actual=source.coupon_faces(g);self.assertEqual(actual,IdealCouponSource(self.coupon).faces)
        male.append(male[0])
        with self.assertRaisesRegex(RuntimeError,'ambiguous'):source.coupon_faces(g)
        male.pop();recv.pop()
        with self.assertRaisesRegex(RuntimeError,'Missing'):source.coupon_faces(g)

    def test_measured_cut_ownership_and_first_failure_stopping(self):
        comps=self.components();cut_features=[]
        self.design.timeline=NS(count=20,markerPosition=20)
        self.design.allComponents=NS(count=3);self.design.userParameters.count=4
        self.design.rootComponent.occurrences=Items([NS(component=c) for c in comps.values()])
        for pid,comp in comps.items():
            features=[NS(name='base',operation=0,healthState=0,isSuppressed=False)]
            for cid,owner in zip(CUT_IDS,OWNERS):
                if owner!=pid:continue
                feature=NS(name=cid,operation=1,healthState=0,isSuppressed=False,parentComponent=comp,
                           participantBodies=[comp.bRepBodies.item(0)],timelineObject=NS(rollTo=Mock(return_value=True)))
                features.append(feature);cut_features.append(feature)
            comp.features=NS(count=len(features),extrudeFeatures=Items(features))
            comp.sketches=Items([NS(isFullyConstrained=True,profiles=NS(count=1),healthState=0) for f in features])
        source=IdealCouponSource(self.coupon)
        with patch.object(self.m,'CouponSource',return_value=source):
            r=self.m.measure_coupon(self.design,self.coupon,self.guard,6)
            self.assertEqual(r['outcome'],'PASS')
            self.assertEqual(len([c for c in r['checks'] if c['check_id'].endswith('.ownership')]),7)
            for f in cut_features:f.timelineObject.rollTo.reset_mock()
            first=next(f for f in cut_features if f.name==CUT_IDS[0])
            first.participantBodies=[comps[RECEIVER].bRepBodies.item(0)]
            r=self.m.measure_coupon(self.design,self.coupon,self.guard,6)
            self.assertEqual(r['outcome'],'FAIL');self.assertEqual(self.design.timeline.markerPosition,20)
            self.assertEqual(sum(f.timelineObject.rollTo.call_count for f in cut_features),1)
            for f in cut_features:f.timelineObject.rollTo.reset_mock()
            source.interference_count=lambda ids:1
            r=self.m.measure_coupon(self.design,self.coupon,self.guard,6)
            self.assertEqual(r['outcome'],'FAIL')
            self.assertEqual(sum(f.timelineObject.rollTo.call_count for f in cut_features),0)

    def test_partial_cut_evidence_survives_construction_failure(self):
        def failure(coupon,guard,records):
            records.append(dict(cut_id=CUT_IDS[0],outcome='FAIL',removed_mm3=1))
            raise RuntimeError('bad cut')
        with tempfile.TemporaryDirectory() as out,patch.object(self.m,'CouponAdapter') as adapter:
            adapter.return_value.compile_coupon.side_effect=failure
            with self.assertRaisesRegex(RuntimeError,'bad cut'):self.m.run_tab_slot(self.app,out,self.guard)
            r=json.loads((Path(out)/'tab_slot.json').read_text())
            self.assertEqual(r['outcome'],'FAIL');self.assertEqual(r['construction_cuts'][0]['removed_mm3'],1)
            self.assertEqual(r['stages'],[]);self.doc.close.assert_not_called();self.doc.save.assert_not_called()
