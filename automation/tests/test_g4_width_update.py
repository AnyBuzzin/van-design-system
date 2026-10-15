"""G4 first feature: safe width update of an existing cabinet (offline, real G3 code)."""

import importlib
import json
import os
import sys
import unittest

from _helpers import AUTOMATION, DESIGN, OTHER, TmpDirCase, cfg, job
from vdrunner.executor import Executor
from vdrunner.journal import RestoreJournal
from vdrunner.width_change import expected_expressions, plan_width_change

REPO = os.path.dirname(AUTOMATION)
G3_DIR = os.path.join(REPO, "prototypes", "claude-v5", "VanCabinetJoineryV5")
BASE_SPEC = os.path.join(REPO, "prototypes", "claude-v5", "specs", "base.json")


def g3_modules():
    if G3_DIR not in sys.path:
        sys.path.insert(0, G3_DIR)
    return {k: importlib.import_module(m) for k, m in (
        ("design_spec", "vandesign.schemas.design_spec"), ("variants", "vandesign.modules.variants"),
        ("expr", "vandesign.core.expr"))}


class FakeCabinet:
    """A base@1 cabinet held in memory, driven by the real G3 generator."""

    def __init__(self, design_id=DESIGN):
        self.g3 = g3_modules()
        ds = self.g3["design_spec"].load_design_spec(open(BASE_SPEC, "rb").read())
        self.stored = ds.canonical_stored_spec_json
        self.asm = self.g3["variants"].build_variant(ds.resolved_params, ds.profile)
        # Fusion re-spaces formulas; mimic that so the planner must normalise
        self.exprs = {n: e.replace("(", "( ").replace(")", " )") for n, e in expected_expressions(self.g3, self.asm).items()}
        self.ident = {"design_id": design_id, "document_name": "v5-g4-width-demo", "is_saved": True,
                      "is_modified": False, "fusion_version": "fake"}
        self.occurrences = [{"stable_id": p.stable_id, "entity_token": "tok-" + p.stable_id, "component": p.display_name,
                             "bodies": 1} for p in self.asm.panels]
        self.timeline = 28
        self.fault = None
        self.set_calls = []
        self.spec_writes = []

    # --- helpers
    def _base(self):
        return {p.name: float(self.exprs[p.name].split()[0]) for p in self.asm.parameters.base()}

    def _env(self):
        return self.asm.parameters.resolve(self._base())

    # --- backend contract
    def identity(self):
        return dict(self.ident)

    def g3_modules(self):
        return self.g3

    def cabinet_state(self):
        env = self._env()
        live = {n: {"expression": self.exprs[n], "value_mm": env[n]} for n in self.exprs}
        return {"stored_text": self.stored, "live_params": live, "occurrences": [dict(o) for o in self.occurrences],
                "timeline_count": self.timeline, "timeline_marker": self.timeline}

    def get_parameter(self, name):
        return {"expression": self.exprs[name], "value_mm": self._env()[name]}

    def set_parameter_expression(self, name, expr):
        self.set_calls.append((name, expr))
        self.exprs[name] = expr
        if self.fault == "duplicate_feature":
            self.timeline += 1
        return self._env()[name]

    def store_spec_text(self, text):
        self.spec_writes.append(text)
        self.stored = text
        return text + (" " if self.fault == "spec_readback" and len(self.spec_writes) == 1 else "")

    def measure(self, out_dir, label):
        env = self._env()
        bad = self.fault == "geometry" and abs(env["Cab_Width"] - 1100) < 1e-9
        return {"verdict": "FAIL" if bad else "PASS", "counts": {"PASS": 58 if bad else 59, "FAIL": 1 if bad else 0, "UNKNOWN": 0},
                "total": 59, "fail_ids": ["panel.shelf.001.volume"] if bad else [], "unknown_ids": [],
                "params_mm": dict(env), "design_counts": {"user_parameters": 16, "root_occurrences": 8, "all_components": 9,
                                                          "timeline_items": self.timeline},
                "design_spec_hash": self.g3["design_spec"].load_design_spec(self.stored).design_spec_hash,
                "stored_unchanged": True}

    def inspect(self):
        return self.cabinet_state()

    def audit(self, out_dir, label):
        return {"overall": "PASS", "features_passed": 2, "features_total": 2, "timeline_restored": True, "counts_equal": True}


UPDATE = {"new_width": 1100, "unit": "mm"}


class WidthPlannerTests(unittest.TestCase):
    def test_preview_1200_to_1100(self):
        c = FakeCabinet()
        p = plan_width_change(c.g3, c.stored, c.cabinet_state()["live_params"], 1100)
        self.assertEqual(p["refusals"], [])
        self.assertEqual(p["parameter_changes"], {"Cab_Width": [1200.0, 1100.0], "Cab_Shelf_Length": [1175.4, 1075.4]})
        self.assertEqual(sorted(p["geometry_changes"]), ["dado.shelf1.right", "panel.back.001", "panel.bottom.001",
                                                         "panel.door.001", "panel.door.002", "panel.right.001",
                                                         "panel.shelf.001", "panel.top.001"])
        self.assertEqual(p["unchanged_geometry"], ["dado.shelf1.left", "panel.left.001"])
        self.assertEqual(p["geometry_changes"]["panel.door.001"]["new"]["size"][0], 545.5)
        self.assertEqual(json.loads(p["new_stored_text"])["parameters"]["width_mm"], 1100.0)
        self.assertNotEqual(p["new_design_spec_hash"], p["old_design_spec_hash"])

    def test_refusals(self):
        c = FakeCabinet()
        live = c.cabinet_state()["live_params"]
        self.assertTrue(plan_width_change(c.g3, c.stored, live, 1200)["refusals"])          # no-op
        self.assertTrue(plan_width_change(c.g3, c.stored, live, 30)["refusals"])            # not buildable
        live["Cab_Dado_Depth"] = {"expression": "10 mm", "value_mm": 10.0}                  # manual edit
        self.assertIn("differs from its stored specification", plan_width_change(c.g3, c.stored, live, 1100)["refusals"][0])
        self.assertTrue(plan_width_change(c.g3, "{not json", c.cabinet_state()["live_params"], 1100)["refusals"])


class WidthUpdateTests(TmpDirCase):
    def run_job(self, j, cab, journal="journal"):
        self.jdir = os.path.join(self.tmp, journal)
        return Executor(cab, cfg(), self.jdir).run(j, os.path.join(self.tmp, "ev"))

    def test_update_succeeds_and_updates_spec_hash(self):
        c = FakeCabinet()
        old_hash = c.measure("", "")["design_spec_hash"]
        r = self.run_job(job("update_width", UPDATE), c)
        self.assertEqual(r["outcome"], "PASS", json.dumps(r, default=str)[:2000])
        s = r["steps"][0]
        self.assertEqual(c.set_calls, [("Cab_Width", "1100 mm")])
        new_hash = c.measure("", "")["design_spec_hash"]
        self.assertNotEqual(new_hash, old_hash)
        self.assertEqual(s["preview"]["new_design_spec_hash"], new_hash)
        self.assertEqual(s["post_measure"]["summary"]["params_mm"]["Cab_Shelf_Length"], 1075.4)
        self.assertEqual(s["identity_check"]["problems"], [])
        self.assertEqual(RestoreJournal(self.jdir, DESIGN).load()["entries"], {})

    def test_preview_never_mutates(self):
        c = FakeCabinet()
        r = self.run_job(job("preview_width_change", UPDATE), c)
        self.assertEqual(r["outcome"], "PASS")
        self.assertEqual((c.set_calls, c.spec_writes), ([], []))

    def test_unsafe_changes_refused_without_touching_design(self):
        c = FakeCabinet()
        c.exprs["Cab_Ply"] = "15 mm"                       # unexpected manual modification
        r = self.run_job(job("update_width", UPDATE), c)
        self.assertEqual(r["outcome"], "FAIL")
        self.assertTrue(r["steps"][0]["refused"])
        self.assertEqual((c.set_calls, c.spec_writes), ([], []))
        c2 = FakeCabinet()
        r = self.run_job(job("update_width", {"new_width": 30, "unit": "mm"}, job_id="job-narrow"), c2)
        self.assertEqual(r["outcome"], "FAIL")
        self.assertEqual((c2.set_calls, c2.spec_writes), ([], []))

    def test_not_allowlisted_refused(self):
        c = FakeCabinet(design_id=OTHER)
        r = self.run_job(job("update_width", UPDATE, target=OTHER), c)
        self.assertEqual(r["outcome"], "REFUSED")
        self.assertEqual(c.set_calls, [])

    def test_failed_validation_rolls_back_width_and_spec(self):
        for fault in ("geometry", "duplicate_feature", "spec_readback"):
            c = FakeCabinet()
            c.fault = fault
            original_spec = c.stored
            r = self.run_job(job("update_width", UPDATE, job_id="job-" + fault.replace("_", "-")), c, journal="j-" + fault)
            self.assertEqual(r["outcome"], "FAIL", fault)
            rb = r["steps"][0]["rollback"]
            self.assertEqual(c.exprs["Cab_Width"], "1200 mm", fault)
            self.assertEqual(c.stored, original_spec, fault)
            if fault == "duplicate_feature":      # extra timeline item stays -> rollback cannot be verified
                self.assertFalse(rb["verified"])
                self.assertEqual(RestoreJournal(self.jdir, DESIGN).entry("Cab_Width")["state"], "restore_unverified")
            else:
                self.assertTrue(rb["verified"], fault)
                self.assertEqual(RestoreJournal(self.jdir, DESIGN).load()["entries"], {})

    def test_batch_with_update_uses_new_baseline(self):
        c = FakeCabinet()
        steps = [{"command": "measure", "args": {"expect": {"params_mm": {"Cab_Shelf_Length": 1175.4}}}},
                 {"command": "preview_width_change", "args": UPDATE},
                 {"command": "update_width", "args": UPDATE},
                 {"command": "measure", "args": {"expect": {"params_mm": {"Cab_Shelf_Length": 1075.4}}}},
                 {"command": "audit_cuts", "args": {"expect": {"features_passed": 2}}}]
        r = self.run_job(job("run_test_batch", {"steps": steps}), c)
        self.assertEqual(r["outcome"], "PASS", [(s["command"], s["status"], s.get("checks")) for s in r["steps"]])


if __name__ == "__main__":
    unittest.main()
