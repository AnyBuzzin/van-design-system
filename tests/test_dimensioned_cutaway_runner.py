"""Offline safety/control tests; not actual Fusion visual qualification."""
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock,patch
import test_dimensioned_cutaway

class VisualRunnerTests(unittest.TestCase):
    def setUp(self):
        self.fake=NS(core=NS(),fusion=NS(Design=NS(cast=lambda d:d),DesignTypes=NS(ParametricDesignType=1)))
        with patch.dict(sys.modules,{'adsk':self.fake,'adsk.core':self.fake.core,'adsk.fusion':self.fake.fusion}):
            self.m=importlib.import_module('vandesign.cad.fusion.dimensioned_cutaway')
        p=patch.object(self.m,'adsk',self.fake);p.start();self.addCleanup(p.stop)
        self.design=NS(designType=1,rootComponent=NS(occurrences=NS(count=0),bRepBodies=NS(count=0),sketches=NS(count=0)),
                       userParameters=NS(count=0),timeline=NS(count=0))
        self.doc=NS(isSaved=False,isModified=False,save=Mock(),close=Mock())
        self.app=NS(activeProduct=self.design,activeDocument=self.doc)
        self.guard=Mock()
        fixture=test_dimensioned_cutaway.CutawayTests();fixture.setUp();self.report=fixture.report

    def run_case(self,fail=None,overlap=0):
        with tempfile.TemporaryDirectory() as out,patch.object(self.m,'FusionAdapter') as adapter, \
             patch.object(self.m,'measure_storage',return_value=self.report), \
             patch.object(self.m,'annotate',side_effect=fail,return_value={'labels':[]}) as annotation, \
             patch.object(self.m,'captures',return_value={'cutaway':'image','plan':'image'}) as capture:
            adapter.return_value.geometry_source.return_value.interference_count.return_value=overlap
            try:self.m.run_dimensioned_cutaway(self.app,out,self.guard)
            except (RuntimeError,ValueError):pass
            result=json.loads((Path(out)/'dimensioned_cutaway.json').read_text())
            with self.assertRaisesRegex(RuntimeError,'no retry'):
                self.m.run_dimensioned_cutaway(self.app,out,self.guard)
            return result,adapter,annotation,capture

    def test_success_measures_once_before_and_after_annotations_without_edits(self):
        r,a,_,c=self.run_case();self.assertEqual(r['outcome'],'PASS')
        a.return_value.compile.assert_called_once();c.assert_called_once()
        self.assertIn('UNKNOWN',r['visual_review'])
        self.doc.save.assert_not_called();self.doc.close.assert_not_called()

    def test_annotation_or_reference_failure_preserves_evidence_without_capture(self):
        for failure,overlap in ((RuntimeError('annotation unavailable'),0),(None,None),(None,1)):
            r,_,_,c=self.run_case(failure,overlap);self.assertEqual(r['outcome'],'FAIL');c.assert_not_called()

    def test_saved_dirty_nonempty_or_guard_refuses_before_compile(self):
        for obj,key,value in ((self.doc,'isSaved',True),(self.doc,'isModified',True),
                              (self.design.timeline,'count',1),(self.design,'designType',0)):
            old=getattr(obj,key);setattr(obj,key,value)
            r,a,_,_=self.run_case();self.assertEqual(r['outcome'],'FAIL');a.assert_not_called()
            setattr(obj,key,old)
        self.guard.side_effect=RuntimeError('protected document changed')
        r,a,_,_=self.run_case();a.assert_not_called();self.assertEqual(r['outcome'],'FAIL')

    def test_annotation_readback_and_roof_scale_fail_closed(self):
        self.fake.core=NS(Point3D=NS(create=lambda x,y,z:NS(x=x,y=y,z=z)),
            ValueInput=NS(createByString=lambda s:s),
            HorizontalAlignments=NS(LeftHorizontalAlignment=0),VerticalAlignments=NS(TopVerticalAlignment=0))
        def line(a,b):
            return NS(startSketchPoint=NS(worldGeometry=NS(x=a.x,y=a.y,z=202.5)),
                      endSketchPoint=NS(worldGeometry=NS(x=b.x,y=b.y,z=202.5)))
        roof=NS(isVisible=True,sketchCurves=NS(sketchLines=NS(addByTwoPoints=Mock(side_effect=line))))
        text_input=NS(setAsMultiLine=Mock(return_value=True))
        sketch=NS(isVisible=True,sketchTexts=NS(createInput3=Mock(return_value=text_input),
                   add=Mock(return_value=NS(text='Measured 382 mm'))))
        root=NS(xYConstructionPlane='XY',constructionPlanes=NS(
            createInput=lambda:NS(setByOffset=lambda *a:True),add=lambda i:NS(isLightBulbOn=True)),
            sketches=NS(add=Mock(side_effect=[roof,sketch])))
        result=self.m.annotate(NS(rootComponent=root),self.report['parameters_mm'],['Measured 382 mm'],self.guard)
        self.assertEqual(result['labels'],['Measured 382 mm'])
        self.assertEqual(len(result['roof_segments_mm']),4)
        sketch.sketchTexts.createInput3.assert_called_once_with("'Measured 382 mm'",'28 mm')
        root.sketches.add.side_effect=[roof,sketch]
        sketch.sketchTexts.add.return_value.text='wrong'
        with self.assertRaisesRegex(RuntimeError,'readback'):
            self.m.annotate(NS(rootComponent=root),self.report['parameters_mm'],['Measured 382 mm'],self.guard)

    def test_capture_requires_two_real_output_files_and_stops_on_failure(self):
        self.fake.core=NS(Point3D=NS(create=lambda *v:v),Vector3D=NS(create=lambda *v:v),
                          CameraTypes=NS(OrthographicCameraType=1))
        with tempfile.TemporaryDirectory() as out:
            def save(path,w,h):Path(path).write_bytes(b'fake image');return True
            viewport=NS(camera=NS(),refresh=Mock(return_value=True),saveAsImageFile=Mock(side_effect=save))
            paths=self.m.captures(NS(activeViewport=viewport),Path(out),self.report['parameters_mm'],self.guard)
            self.assertEqual(set(paths),{'cutaway','plan'});self.assertEqual(viewport.saveAsImageFile.call_count,2)
            viewport.refresh.return_value=False
            with self.assertRaisesRegex(RuntimeError,'refresh'):
                self.m.captures(NS(activeViewport=viewport),Path(out),self.report['parameters_mm'],self.guard)
