"""Offline control tests; these are not Fusion geometry evidence."""
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from vandesign.modules.test_envelope import build_lined_envelope
from vandesign.schemas.envelope_spec import EnvelopeSpec


class LinedRunnerTests(unittest.TestCase):
    def setUp(self):
        self.fake = NS(core=NS(), fusion=NS(Design=NS(cast=lambda d:d),
                       DesignTypes=NS(ParametricDesignType=1)), doEvents=Mock())
        with patch.dict(sys.modules, {"adsk":self.fake, "adsk.core":self.fake.core, "adsk.fusion":self.fake.fusion}):
            self.m = importlib.import_module("vandesign.cad.fusion.lined_envelope")
        p = patch.object(self.m, "adsk", self.fake); p.start(); self.addCleanup(p.stop)
        self.parameter = NS(expression="1784 mm")
        self.design = NS(designType=1, rootComponent=NS(occurrences=NS(count=0),
                         bRepBodies=NS(count=0), sketches=NS(count=0)), timeline=NS(count=0),
                         userParameters=NS(count=0, itemByName=lambda n:self.parameter))
        self.doc = NS(isSaved=False, isModified=False, save=Mock(), close=Mock())
        self.app = NS(activeProduct=self.design, activeDocument=self.doc, activeViewport=NS(fit=Mock()))
        self.guard = Mock()
        self.assembly = build_lined_envelope(EnvelopeSpec())

    def report(self, width):
        env = self.assembly.parameters.resolve({"Env_Bare_Width":width})
        boxes = {p.stable_id:p.box.resolve(env) for p in self.assembly.panels}
        return dict(outcome="PASS", parameters_mm=env,
                    bodies={k:dict(min=b.lo, max=b.hi, volume_mm3=b.volume) for k,b in boxes.items()},
                    checks=[dict(check_id=k+".volume",status="PASS",observed=b.volume,
                                 expected=b.volume,tolerance=1e-6,unit="mm3",object_ids=[k])
                            for k,b in boxes.items()])

    def run_case(self, fail_at=None, changed_state=False):
        stages = [self.report(w) for w in (1784,1794,1784,1784)]
        if fail_at is not None: stages[fail_at]["outcome"]="FAIL"
        states = [{}, {"unexpected":1} if changed_state else {}, {}]
        with tempfile.TemporaryDirectory() as out, patch.object(self.m,"FusionAdapter") as adapter, \
                patch.object(self.m,"measure_lined",side_effect=stages) as measure, \
                patch.object(self.m,"snapshot",side_effect=states):
            try: self.m.run_lined_envelope(self.app,out,self.guard)
            except RuntimeError: pass
            result = json.loads((Path(out)/"lined_envelope.json").read_text())
            with self.assertRaisesRegex(RuntimeError,"no retry"):
                self.m.run_lined_envelope(self.app,out,self.guard)
            self.doc.save.assert_not_called();self.doc.close.assert_not_called()
            return result, adapter, measure

    def test_fixed_edit_restore_refusal_and_no_document_lifecycle(self):
        r, a, m = self.run_case()
        self.assertEqual(r["outcome"],"PASS")
        self.assertEqual(r["refusal"]["outcome"],"REFUSED")
        self.assertEqual(self.parameter.expression,"1784 mm")
        self.assertEqual(m.call_count,4)
        a.return_value.compile.assert_called_once()
        self.assertEqual(len(r["furniture_cut_list"]),16)

    def test_failed_edit_stops_without_automatic_restore(self):
        r, _, m = self.run_case(fail_at=1)
        self.assertEqual(r["outcome"],"FAIL")
        self.assertEqual(len(r["stages"]),2)
        self.assertEqual(self.parameter.expression,"1794 mm")
        self.assertIsNone(r["refusal"])
        self.assertEqual(m.call_count,2)

    def test_state_failure_stops_before_refusal(self):
        r, _, _ = self.run_case(changed_state=True)
        self.assertEqual(r["outcome"],"FAIL")
        self.assertIsNone(r["refusal"])

    def test_saved_dirty_nonempty_or_guard_failure_never_compiles(self):
        for obj, name, value in ((self.doc,"isSaved",True),(self.doc,"isModified",True),
                                 (self.design,"designType",0),
                                 (self.design.rootComponent.sketches,"count",1)):
            old = getattr(obj,name);setattr(obj,name,value)
            r, a, m = self.run_case()
            self.assertEqual(r["outcome"],"FAIL");a.assert_not_called();m.assert_not_called()
            setattr(obj,name,old)
        self.guard.side_effect=RuntimeError("protected document changed")
        r, a, _ = self.run_case();a.assert_not_called()
        self.assertEqual(r["outcome"],"FAIL")

    def test_measure_checks_parameters_and_storage_contacts(self):
        with patch.object(self.m,"measure_test",return_value=self.report(1784)) as measure:
            r=self.m.measure_lined(self.design,self.assembly,EnvelopeSpec(),self.guard,1784)
            self.assertEqual(r["outcome"],"PASS")
            self.assertEqual(len([c for c in r["checks"] if c["check_id"].startswith("storage.contact")]),8)
            self.assertIsInstance(measure.call_args.kwargs["lined_spec"],EnvelopeSpec)
        with patch.object(self.m,"measure_test",return_value=self.report(1794)):
            r=self.m.measure_lined(self.design,self.assembly,EnvelopeSpec(),self.guard,1784)
            self.assertEqual(r["outcome"],"FAIL")
