"""Offline control-flow tests; these do not establish Fusion geometry PASS."""
import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch


class StorageRunnerTests(unittest.TestCase):
    def setUp(self):
        self.fake=NS(core=NS(),fusion=NS(Design=NS(cast=lambda d:d),DesignTypes=NS(ParametricDesignType=1)),doEvents=Mock())
        with patch.dict(sys.modules,{'adsk':self.fake,'adsk.core':self.fake.core,'adsk.fusion':self.fake.fusion}):
            self.m=importlib.import_module('vandesign.cad.fusion.storage_box')
        p=patch.object(self.m,'adsk',self.fake);p.start();self.addCleanup(p.stop)
        self.width=NS(expression='600 mm')
        self.design=NS(designType=1,rootComponent=NS(occurrences=NS(count=0),bRepBodies=NS(count=0)),
            userParameters=NS(count=0,itemByName=lambda n:self.width),timeline=NS(count=0))
        self.doc=NS(isSaved=False,isModified=False,save=Mock(),close=Mock())
        self.app=NS(activeProduct=self.design,activeDocument=self.doc,activeViewport=NS(fit=Mock()))
        self.guard=Mock();self.a=self.m.build_storage_scene()

    def report(self,width):
        env=self.a.parameters.resolve({'Storage_Width':width})
        return dict(outcome='PASS',checks=[dict(check_id='existing',status='PASS')],parameters_mm=env,
            counts={'timeline_items':67},bodies={p.stable_id:dict(min=p.box.resolve(env).lo,
                max=p.box.resolve(env).hi,volume_mm3=p.box.resolve(env).volume) for p in self.a.panels})

    def run_sequence(self,reports=None,states=None):
        with tempfile.TemporaryDirectory() as out,patch.object(self.m,'FusionAdapter') as adapter, \
             patch.object(self.m,'measure_storage',side_effect=reports or [self.report(w) for w in (600,700,600,600)]), \
             patch.object(self.m,'snapshot',side_effect=states or [{'timeline':67}]*4):
            try: self.m.run_storage_box(self.app,out,self.guard)
            except RuntimeError: pass
            return json.loads((Path(out)/'storage_box.json').read_text()),adapter

    def test_sequence_restore_refusal_and_no_document_operations(self):
        r,adapter=self.run_sequence()
        self.assertEqual(r['outcome'],'PASS');self.assertEqual(r['refusal']['outcome'],'REFUSED')
        self.assertEqual([s['parameters_mm']['Storage_Width'] for s in r['stages']],[600,700,600])
        self.assertEqual(r['before'],r['after']);self.assertEqual(self.width.expression,'600 mm')
        adapter.return_value.compile.assert_called_once()
        self.doc.save.assert_not_called();self.doc.close.assert_not_called()

    def test_dirty_saved_nonempty_and_nonparametric_refused(self):
        for target,key,value in ((self.doc,'isSaved',True),(self.doc,'isModified',True),
            (self.design,'designType',0),(self.design.timeline,'count',1)):
            old=getattr(target,key);setattr(target,key,value)
            r,adapter=self.run_sequence();self.assertEqual(r['outcome'],'FAIL');adapter.assert_not_called()
            setattr(target,key,old)

    def test_failure_stops_without_automatic_restore(self):
        r,adapter=self.run_sequence([self.report(600),dict(self.report(700),outcome='FAIL')])
        self.assertEqual(len(r['stages']),2);self.assertIsNone(r['refusal'])
        self.assertEqual(r['outcome'],'FAIL');self.assertEqual(self.width.expression,'700 mm')
        self.doc.close.assert_not_called();adapter.return_value.compile.assert_called_once()

    def test_changed_state_or_refusal_measurement_never_pass(self):
        r,_=self.run_sequence(states=[{'timeline':67},{'timeline':68}])
        self.assertEqual(r['outcome'],'FAIL');self.assertIsNone(r['refusal'])
        reports=[self.report(w) for w in (600,700,600,600)];reports[-1]['unexpected']=True
        r,_=self.run_sequence(reports);self.assertEqual(r['outcome'],'FAIL')

    def test_protected_guard_failure_prevents_geometry(self):
        self.guard.side_effect=RuntimeError('protected document changed')
        r,adapter=self.run_sequence();adapter.assert_not_called();self.assertEqual(r['outcome'],'FAIL')

    def test_measurements_use_observed_boxes_and_requested_width(self):
        for width in (600,700):
            with patch.object(self.m,'measure_test',return_value=self.report(width)):
                r=self.m.measure_storage(self.design,self.a,self.guard,width)
            self.assertEqual(r['outcome'],'PASS')
            self.assertEqual(sum(c['check_id'].startswith('storage.contact.') for c in r['checks']),8)
        measured=self.report(700)
        with patch.object(self.m,'measure_test',return_value=measured):
            r=self.m.measure_storage(self.design,self.a,self.guard,600)
        self.assertEqual(r['outcome'],'FAIL')
        measured=self.report(600);p=measured['bodies']['storage.001.storage.front.001']
        p['min']=(p['min'][0],p['min'][1],p['min'][2]+1)
        with patch.object(self.m,'measure_test',return_value=measured):
            r=self.m.measure_storage(self.design,self.a,self.guard,600)
        self.assertEqual(r['outcome'],'FAIL')
