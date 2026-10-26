"""Offline control tests for the generic BuildArrangement entry; not Fusion evidence."""
import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from vandesign.arrangement_job import expected_evidence, plan_request
from test_arrangement_job import EDIT_OK, INTO_ARCH, request


class BuildArrangementRunner(unittest.TestCase):
    def setUp(self):
        self.fake = NS(core=NS(), fusion=NS(Design=NS(cast=lambda d: d),
                       DesignTypes=NS(ParametricDesignType=1)), doEvents=Mock())
        with patch.dict(sys.modules, {"adsk": self.fake, "adsk.core": self.fake.core, "adsk.fusion": self.fake.fusion}):
            self.m = importlib.import_module("vandesign.cad.fusion.arrangement_build")
        p = patch.object(self.m, "adsk", self.fake); p.start(); self.addCleanup(p.stop)
        self.params = {}
        def item(name):
            return self.params.setdefault(name, NS(expression="original(%s)" % name))
        self.design = NS(designType=1, rootComponent=NS(occurrences=NS(count=0), bRepBodies=NS(count=0),
                         sketches=NS(count=0)), timeline=NS(count=0),
                         userParameters=NS(count=0, itemByName=item))
        self.doc = NS(isSaved=False, isModified=False, save=Mock(), close=Mock())
        self.app = NS(activeProduct=self.design, activeDocument=self.doc, activeViewport=NS(fit=Mock()))
        self.guard = Mock()
        self.plan = plan_request(request([EDIT_OK, INTO_ARCH]))

    def report(self, values=None, volume_noise=0.0):
        asm = self.plan.arrangement.assembly
        env = asm.parameters.resolve(values)
        boxes = {p.stable_id: p.box.resolve(env) for p in asm.panels}
        bodies = {k: dict(min=list(b.lo), max=list(b.hi), volume_mm3=b.volume + volume_noise)
                  for k, b in boxes.items()}
        return dict(outcome="PASS", parameters_mm=env, counts={"timeline_items": 1}, bodies=bodies,
                    checks=[dict(check_id=k + ".volume", status="PASS", observed=bodies[k]["volume_mm3"],
                                 expected=b.volume, tolerance=1.0, unit="mm3", object_ids=[k])
                            for k, b in boxes.items()])

    def run_case(self, req, stages, states=None):
        states = states or [{"s": 0}] * 4
        with tempfile.TemporaryDirectory() as out, patch.object(self.m, "FusionAdapter") as adapter, \
                patch.object(self.m, "measure_arrangement", side_effect=stages) as measure, \
                patch.object(self.m, "snapshot", side_effect=states):
            try:
                self.m.run_arrangement(self.app, out, self.guard, req)
            except Exception:
                pass
            result = json.loads((Path(out) / "arrangement.json").read_text())
            dxf = sorted(p.name for p in (Path(out) / "dxf").glob("*")) if (Path(out) / "dxf").exists() else []
            with self.assertRaisesRegex(RuntimeError, "no retry"):
                self.m.run_arrangement(self.app, out, self.guard, req)
            self.doc.save.assert_not_called(); self.doc.close.assert_not_called()
            return result, adapter, measure, dxf

    def stages(self, **over):
        s = [self.report(), self.report({"K1_Cab_Width": 1000.0}), self.report(volume_noise=2.6e-8), self.report()]
        for i, rep in over.items():
            s[int(i[1:])] = rep
        return s

    def test_edit_restore_refusal_and_dxf_pack(self):
        r, adapter, measure, dxf = self.run_case(request([EDIT_OK, INTO_ARCH], tool_diameter_mm=6), self.stages())
        self.assertEqual(r["outcome"], "PASS", r.get("error"))
        self.assertEqual([e["outcome"] for e in r["edits"]], ["PASS", "PASS"])
        self.assertEqual(r["edits"][1]["preview"]["outcome"], "REFUSED")
        self.assertEqual([s["label"] for s in r["stages"]],
                         ["baseline", "edit_K1_Cab_Width", "restore_K1_Cab_Width", "after_refusal_K1_Pos_Y"])
        self.assertEqual(self.params["K1_Cab_Width"].expression, "original(K1_Cab_Width)")
        self.assertNotIn("K1_Pos_Y", self.params)                  # refused edit never touched
        self.assertEqual(measure.call_count, 4)
        adapter.return_value.compile.assert_called_once()
        furniture = [p for p in self.plan.arrangement.assembly.panels if p.material_ref != "reference_only"]
        self.assertEqual(len(dxf), len(furniture) + 1)
        self.assertEqual(r["inventory"]["root_occurrences"], len(self.plan.arrangement.assembly.panels))
        # The report the Fusion path writes is what Runner acceptance expects.
        expected = expected_evidence(plan_request(request([EDIT_OK, INTO_ARCH], tool_diameter_mm=6)))
        self.assertEqual([s["label"] for s in r["stages"]], [s["label"] for s in expected["stages"]])
        self.assertEqual((r["spec_hash"], r["instances"]), (expected["spec_hash"], expected["instances"]))
        for record in (r["planned_edits"], r["edits"]):
            self.assertEqual([{k: e[k] for k in ("parameter", "value_mm", "expect")} for e in record],
                             expected["edits"])

    def test_failed_edit_stops_without_automatic_restore(self):
        bad = self.report({"K1_Cab_Width": 1000.0}); bad["outcome"] = "FAIL"
        r, _, measure, dxf = self.run_case(request([EDIT_OK, INTO_ARCH], tool_diameter_mm=6), self.stages(s1=bad))
        self.assertEqual(r["outcome"], "FAIL")
        self.assertEqual(self.params["K1_Cab_Width"].expression, "1000.0 mm")   # left for investigation
        self.assertEqual(measure.call_count, 2)
        self.assertEqual(dxf, [])

    def test_real_restore_difference_fails(self):
        r, _, _, _ = self.run_case(request([EDIT_OK]), self.stages(s2=self.report(volume_noise=1e-3)))
        self.assertEqual(r["outcome"], "FAIL")
        self.assertIn("Restoration differs", r["error"])

    def test_refusal_that_changes_state_fails(self):
        r, _, _, _ = self.run_case(request([INTO_ARCH]), [self.report(), self.report()],
                                   states=[{"s": 0}, {"s": 1}])
        self.assertEqual(r["outcome"], "FAIL")
        self.assertIn("Refusal changed", r["error"])

    def test_dirty_document_or_bad_request_never_compiles(self):
        for obj, name, value in ((self.doc, "isSaved", True), (self.doc, "isModified", True),
                                 (self.design.rootComponent.sketches, "count", 1)):
            old = getattr(obj, name); setattr(obj, name, value)
            try:
                r, adapter, measure, _ = self.run_case(request(), self.stages())
            finally:
                setattr(obj, name, old)
            adapter.assert_not_called(); measure.assert_not_called()
            self.assertEqual(r["outcome"], "FAIL")
        r, adapter, measure, _ = self.run_case(request([dict(INTO_ARCH, expect="pass")]), self.stages())
        adapter.assert_not_called(); measure.assert_not_called()
        self.assertIn("preview gives REFUSED", r["error"])


if __name__ == "__main__":
    unittest.main()
