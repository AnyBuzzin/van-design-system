"""Offline API traces and stop/no-retry tests, never live CAD evidence."""
import importlib
import json
import math
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from vandesign.modules.rounded_panel import build_rounded_panel, preview_rounded_panel, PANEL_ID
from vandesign.schemas.rounded_panel_spec import RoundedPanelSpec
from vandesign.verification.geometry_source import MeasuredBody


class RoundedRunnerTests(unittest.TestCase):
    def setUp(self):
        self.fake=NS(core=NS(Point3D=NS(create=lambda *v:v)), fusion=NS(
            Design=NS(cast=lambda d:d), DesignTypes=NS(ParametricDesignType=1),
            DimensionOrientations=NS(HorizontalDimensionOrientation='H',VerticalDimensionOrientation='V'),
            FeatureHealthStates=NS(HealthyFeatureHealthState=0),FeatureOperations=NS(NewBodyFeatureOperation=0)),
            doEvents=Mock())
        with patch.dict(sys.modules,{'adsk':self.fake,'adsk.core':self.fake.core,'adsk.fusion':self.fake.fusion}):
            self.m=importlib.import_module('vandesign.cad.fusion.rounded_panel')
            self.adapter=importlib.import_module('vandesign.cad.fusion.adapter')
        for module in (self.m,self.adapter):
            p=patch.object(module,'adsk',self.fake);p.start();self.addCleanup(p.stop)
        self.param=NS(expression='50 mm')
        self.design=NS(designType=1,rootComponent=NS(occurrences=NS(count=0),bRepBodies=NS(count=0),
                       sketches=NS(count=0)),userParameters=NS(count=0,itemByName=lambda n:self.param),
                       timeline=NS(count=0))
        self.doc=NS(isSaved=False,isModified=False,save=Mock(),close=Mock())
        self.app=NS(activeProduct=self.design,activeDocument=self.doc,activeViewport=NS(fit=Mock()))
        self.guard=Mock();self.assembly=build_rounded_panel(RoundedPanelSpec())

    def report(self,radius):
        env=self.assembly.parameters.resolve({'Panel_Radius':radius})
        box=self.assembly.panels[0].box.resolve(env);volume=(600*800-(1-math.pi/4)*radius**2)*18
        return dict(outcome='PASS',parameters_mm=env,preview=preview_rounded_panel(env),
                    bodies={PANEL_ID:dict(min=box.lo,max=box.hi,volume_mm3=volume)},
                    checks=[dict(check_id=PANEL_ID+'.volume',status='PASS',observed=volume,
                                 expected=volume,tolerance=volume*1e-6,unit='mm3',object_ids=[PANEL_ID])])

    def run_case(self, fail_at=None, state_failure=False):
        reports=[self.report(r) for r in (50,75,50,50)]
        if fail_at is not None:reports[fail_at]['outcome']='FAIL'
        with tempfile.TemporaryDirectory() as out, patch.object(self.m,'FusionAdapter') as adapter, \
                patch.object(self.m,'measure_rounded',side_effect=reports) as measure, \
                patch.object(self.m,'snapshot',side_effect=[{}, {'bad':1} if state_failure else {}, {}]):
            try:self.m.run_rounded_panel(self.app,out,self.guard)
            except RuntimeError:pass
            result=json.loads((Path(out)/'rounded_panel.json').read_text())
            with self.assertRaisesRegex(RuntimeError,'no retry'):
                self.m.run_rounded_panel(self.app,out,self.guard)
            self.doc.save.assert_not_called();self.doc.close.assert_not_called()
            return result,adapter,measure

    def test_sequence_refusal_and_no_document_lifecycle(self):
        result,adapter,measure=self.run_case()
        self.assertEqual(result['outcome'],'PASS');self.assertEqual(measure.call_count,4)
        self.assertEqual(result['refusal']['outcome'],'REFUSED');self.assertEqual(self.param.expression,'50 mm')
        adapter.return_value.compile.assert_called_once()

    def test_stop_on_failure_without_automatic_restore(self):
        result,_,measure=self.run_case(fail_at=1)
        self.assertEqual(result['outcome'],'FAIL');self.assertEqual(measure.call_count,2)
        self.assertEqual(self.param.expression,'75 mm');self.assertIsNone(result['refusal'])

    def test_state_failure_stops_before_refusal(self):
        result,_,measure=self.run_case(state_failure=True)
        self.assertEqual(result['outcome'],'FAIL');self.assertIsNone(result['refusal'])
        self.assertEqual(measure.call_count,3)

    def test_protected_or_nonempty_or_guard_failure_never_compiles(self):
        for obj,key,value in ((self.doc,'isSaved',True),(self.doc,'isModified',True),
                              (self.design,'designType',0),(self.design.rootComponent.occurrences,'count',1)):
            old=getattr(obj,key);setattr(obj,key,value)
            result,adapter,measure=self.run_case()
            self.assertEqual(result['outcome'],'FAIL');adapter.assert_not_called();measure.assert_not_called()
            setattr(obj,key,old)
        self.guard.side_effect=RuntimeError('protected document changed')
        _,adapter,_=self.run_case();adapter.assert_not_called()

    def test_arc_trace_binds_all_dimensions_and_reuses_endpoints(self):
        dimensions=[];lines=[];constraints=[]
        def dimension(*args):
            d=NS(parameter=NS(expression=None));dimensions.append((args,d));return d
        def line(a,b):
            obj=NS(startSketchPoint=a,endSketchPoint=b);lines.append(obj);return obj
        arc=NS(centerSketchPoint='centre',startSketchPoint='arc_start',endSketchPoint='arc_end')
        add_arc=Mock(return_value=arc)
        sketch=NS(originPoint='origin',profiles=NS(count=1),
            sketchCurves=NS(sketchArcs=NS(addByCenterStartSweep=add_arc),sketchLines=NS(addByTwoPoints=line)),
            sketchDimensions=NS(addDistanceDimension=dimension,addRadialDimension=dimension),
            geometricConstraints=NS(**{n:(lambda *args,n=n:constraints.append((n,args))) for n in
                ('addHorizontalPoints','addVerticalPoints','addHorizontal','addVertical')}))
        comp=NS(xYConstructionPlane='XY',sketches=NS(add=Mock(return_value=sketch)))
        values={'Panel_Width':60,'Panel_Length':80,'Panel_Radius':5}
        adapter=NS(_eval_cm=values.__getitem__)
        self.adapter.FusionAdapter._rounded_profile(adapter,comp,'panel',*values)
        add_arc.assert_called_once_with((55,75,0),(60,75,0),math.pi/2)
        self.assertEqual([d.parameter.expression for _,d in dimensions],
                         ['(Panel_Width - Panel_Radius)','(Panel_Length - Panel_Radius)','Panel_Radius'])
        self.assertEqual([(l.startSketchPoint,l.endSketchPoint) for l in lines],
                         [('origin',(60,0,0)),((60,0,0),'arc_start'),('arc_end',(0,80,0)),((0,80,0),'origin')])
        self.assertEqual([n for n,_ in constraints],['addHorizontalPoints','addVerticalPoints',
                                                     'addHorizontal','addHorizontal','addVertical','addVertical'])
        values['Panel_Radius']=60;comp.sketches.add.reset_mock()
        with self.assertRaises(ValueError):self.adapter.FusionAdapter._rounded_profile(adapter,comp,'panel',*values)
        comp.sketches.add.assert_not_called()

    def test_measure_missing_probes_wrong_volume_inventory_and_nonfinite_fail(self):
        env=self.assembly.parameters.resolve();box=self.assembly.panels[0].box.resolve(env)
        volume=(600*800-(1-math.pi/4)*50**2)*18
        def contains(pid,point):
            x,y,_=point
            return x<=550 or y<=750 or (x-550)**2+(y-750)**2<2500
        source=NS(parameter_value=env.get,body=Mock(return_value=MeasuredBody(box,volume)),
                  managed_ids=lambda:{PANEL_ID:1},point_in_material=contains,diagnostics=[])
        sketch=NS(profiles=NS(count=1),sketchCurves=NS(sketchLines=NS(count=4),sketchArcs=NS(count=1)),
                  isFullyConstrained=True,healthState=0)
        feature=NS(healthState=0,isSuppressed=False,operation=0)
        comp=NS(bRepBodies=NS(count=1,item=lambda i:NS(isSolid=True,isValid=True)),
                sketches=NS(count=1,item=lambda i:sketch),features=NS(count=1,extrudeFeatures=NS(count=1,item=lambda i:feature)))
        self.design.rootComponent.occurrences=NS(count=1,item=lambda i:NS(component=comp))
        self.design.timeline=NS(count=3,markerPosition=3)
        counts=dict(root_occurrences=1,all_components=2,timeline_items=3,user_parameters=3)
        with patch.object(self.m,'FusionAdapter') as adapter, patch.object(self.m,'_design_counts',return_value=counts):
            adapter.return_value.geometry_source.return_value=source
            def measure():return self.m.measure_rounded(self.design,self.assembly,self.guard,50)
            self.assertEqual(measure()['outcome'],'PASS')
            source.point_in_material=lambda *a:None
            result=measure();self.assertEqual(result['outcome'],'FAIL')
            self.assertTrue(any(c['status']=='UNKNOWN' for c in result['checks']))
            source.point_in_material=contains;source.body.return_value=MeasuredBody(box,box.volume)
            self.assertEqual(measure()['outcome'],'FAIL')
            source.body.return_value=MeasuredBody(box,volume);counts['all_components']=3
            self.assertEqual(measure()['outcome'],'FAIL')
            counts['all_components']=2;source.body.return_value=MeasuredBody(box,float('nan'))
            with self.assertRaisesRegex(RuntimeError,'finite BRep'):measure()
