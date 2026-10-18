"""Offline workflow failures; not live Fusion solver evidence."""
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch

class EnvelopeRunnerTests(unittest.TestCase):
    def setUp(self):
        fake=NS(core=NS(),fusion=NS(Design=NS(cast=lambda d:d)))
        with patch.dict(sys.modules,{'adsk':fake,'adsk.core':fake.core,'adsk.fusion':fake.fusion}):
            self.m=importlib.import_module('vandesign.cad.fusion.test_envelope')
        patcher=patch.object(self.m,'adsk',fake);patcher.start();self.addCleanup(patcher.stop)
        self.design=NS(rootComponent=NS(occurrences=NS(count=0),bRepBodies=NS(count=0)),
                       userParameters=NS(count=0),timeline=NS(count=0))
        self.doc=NS(isSaved=False,isModified=False)
        self.app=NS(activeDocument=self.doc,activeProduct=self.design,activeViewport=NS(fit=Mock()))
        self.guard=Mock()
        self.report={'outcome':'PASS','parameters_mm':self.m.build_test_envelope().parameters.resolve()}

    def run_with(self, reports, states=None):
        with tempfile.TemporaryDirectory() as out, patch.object(self.m,'FusionAdapter') as adapter, \
             patch.object(self.m,'measure_test',side_effect=reports), \
             patch.object(self.m,'snapshot',side_effect=states or [{'timeline':52},{'timeline':52}]):
            try:
                self.m.run_test_envelope(self.app,out,self.guard)
            except RuntimeError:
                pass
            payload=json.loads((Path(out)/'test_envelope.json').read_text())
            return payload,adapter

    def test_success_has_refusal_and_unchanged_snapshots(self):
        payload,adapter=self.run_with([self.report,self.report])
        self.assertEqual(payload['outcome'],'PASS')
        self.assertEqual(payload['refusal']['outcome'],'REFUSED')
        self.assertEqual(payload['before'],payload['after'])
        self.assertEqual(len(payload['furniture_cut_list']),11)
        adapter.return_value.compile.assert_called_once()

    def test_existing_saved_or_dirty_document_never_compiled(self):
        for key in ('isSaved','isModified'):
            setattr(self.doc,key,True)
            payload,adapter=self.run_with([])
            self.assertEqual(payload['outcome'],'FAIL')
            adapter.assert_not_called()
            setattr(self.doc,key,False)

    def test_failed_measurement_preserved_and_no_retry_or_refusal(self):
        failed=dict(self.report,outcome='FAIL')
        payload,adapter=self.run_with([failed])
        self.assertEqual(payload['before'],failed)
        self.assertIsNone(payload['refusal'])
        self.assertEqual(payload['outcome'],'FAIL')
        adapter.return_value.compile.assert_called_once()

    def test_refusal_state_or_geometry_change_stops(self):
        payload,_=self.run_with([self.report,self.report],[{'timeline':52},{'timeline':53}])
        self.assertEqual(payload['outcome'],'FAIL')
        changed=dict(self.report,unexpected='measurement changed')
        payload,_=self.run_with([self.report,changed])
        self.assertEqual(payload['outcome'],'FAIL')

    def test_guard_failure_stops_before_compile(self):
        self.guard.side_effect=RuntimeError('protected inventory changed')
        payload,adapter=self.run_with([])
        adapter.assert_not_called()
        self.assertIn('protected inventory',payload['error'])

    def test_read_only_root_name_reaches_measurement_and_refusal(self):
        class Root:
            occurrences = NS(count=0)
            bRepBodies = NS(count=0)
            @property
            def name(self):
                return 'Untitled'
            @name.setter
            def name(self, value):
                raise RuntimeError('root component name cannot be changed')
        self.design.rootComponent = Root()
        payload, adapter = self.run_with([self.report, self.report])
        self.assertEqual(payload['outcome'], 'PASS')
        self.assertEqual(payload['before'], self.report)
        self.assertEqual(payload['after'], self.report)
        self.assertEqual(payload['refusal']['outcome'], 'REFUSED')
        self.assertEqual(self.design.rootComponent.name, 'Untitled')
        self.assertEqual(payload['notice'], self.m.NOTICE)
        assembly = adapter.return_value.compile.call_args.args[0]
        references = [p for p in assembly.panels if p.stable_id.startswith('reference.')]
        self.assertEqual(len(references), 5)
        self.assertTrue(all(self.m.NOTICE in p.display_name for p in references))
        self.assertTrue(all(self.m.NOTICE in p.comment for p in assembly.parameters.params
                            if p.name.startswith('Test_')))
