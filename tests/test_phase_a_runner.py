"""Phase A offline sequencing, not live qualification."""
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock,patch


class PhaseARunnerTests(unittest.TestCase):
    def setUp(self):
        fake=NS(core=NS(),fusion=NS(Design=NS(cast=lambda d:d),DesignTypes=NS(ParametricDesignType=1)),doEvents=Mock())
        with patch.dict(sys.modules,{'adsk':fake,'adsk.core':fake.core,'adsk.fusion':fake.fusion}):
            self.m=importlib.import_module('vandesign.cad.fusion.phase_a')
        p=patch.object(self.m,'adsk',fake);p.start();self.addCleanup(p.stop)
        self.param=NS(expression='1200 mm')
        self.design=NS(designType=1,rootComponent=NS(occurrences=NS(count=0),bRepBodies=NS(count=0)),
            userParameters=NS(count=0,itemByName=lambda n:self.param),timeline=NS(count=0))
        self.app=NS(activeProduct=self.design,activeDocument=NS(isSaved=False,isModified=False))
        self.guard=Mock()

    def stage(self,width):
        a=self.m.build_variant(self.m.profile_defaults_spec(self.m.get_profile('base',1)))
        env=a.parameters.resolve({'Cab_Width':width})
        return dict(outcome='PASS',parameters_mm=env,bodies={'panel':{'volume_mm3':100,'min':[0,0,0],'max':[1,1,1]}},
            checks=[dict(check_id='panel.volume',status='PASS',observed=100,expected=100,tolerance=1e-6,unit='mm3',object_ids=['panel'])])

    def test_base_original_edit_restore_and_failed_edit_no_cleanup(self):
        for fail in (False,True):
            stages=[self.stage(w) for w in (1200,1210,1200)]
            if fail:stages[1]['outcome']='FAIL'
            with tempfile.TemporaryDirectory() as out,patch.object(self.m,'FusionAdapter') as adapter, \
                 patch.object(self.m,'phase_a_measure',side_effect=stages),patch.object(self.m,'snapshot',return_value={'timeline':28}):
                if fail:
                    with self.assertRaises(RuntimeError):self.m.run_phase_a(self.app,out,self.guard)
                    self.assertEqual(self.param.expression,'1210 mm')
                else:
                    r=self.m.run_phase_a(self.app,out,self.guard)
                    self.assertEqual(r['outcome'],'PASS');self.assertEqual(self.param.expression,'1200 mm')
                raw=json.loads((Path(out)/'phase_a.json').read_text())
                self.assertEqual(len(raw['stages']),2 if fail else 3)
                adapter.return_value.compile.assert_called_once()

    def test_saved_design_or_protected_guard_failure_never_compiles(self):
        for saved in (False,True):
            self.app.activeDocument.isSaved=saved
            self.guard.side_effect=None if saved else RuntimeError('protected inventory')
            with tempfile.TemporaryDirectory() as out,patch.object(self.m,'FusionAdapter') as adapter:
                with self.assertRaises(RuntimeError):self.m.run_phase_a(self.app,out,self.guard)
                adapter.assert_not_called()
