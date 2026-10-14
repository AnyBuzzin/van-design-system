import os
import unittest

from _helpers import DESIGN, OTHER, PROTECTED, FakeBackend, TmpDirCase, cfg, job
from vdrunner.executor import Executor
from vdrunner.journal import RestoreJournal

DEMO_STEPS = [
    {"command": "measure", "args": {"label": "baseline", "expect": {"pass_count": 59, "params_mm": {"Cab_Shelf_Length": 1175.4}}}},
    {"command": "set_parameter", "args": {"name": "Cab_Dado_Depth", "value": 10, "unit": "mm"}},
    {"command": "measure", "args": {"label": "dado10", "expect": {"pass_count": 59, "params_mm": {"Cab_Shelf_Length": 1183.4}}}},
    {"command": "restore_parameter", "args": {"name": "Cab_Dado_Depth", "expect": {"pass_count": 59, "params_mm": {"Cab_Shelf_Length": 1175.4}}}},
    {"command": "audit_cuts", "args": {"expect": {"features_passed": 2}}},
]


class ExecutorTests(TmpDirCase):
    def ex(self, backend=None):
        self.b = backend or FakeBackend()
        self.jdir = os.path.join(self.tmp, "journal")
        return Executor(self.b, cfg(), self.jdir)

    def run_job(self, j, backend=None):
        return self.ex(backend).run(j, os.path.join(self.tmp, "ev"))

    def test_demo_batch_passes_and_restores(self):
        r = self.run_job(job("run_test_batch", {"steps": DEMO_STEPS}))
        self.assertEqual(r["outcome"], "PASS", r)
        self.assertEqual([s["status"] for s in r["steps"]], ["PASS"] * 5)
        self.assertEqual(self.b.params["Cab_Dado_Depth"], "6 mm")
        self.assertEqual(self.b.set_calls, [("Cab_Dado_Depth", "10 mm"), ("Cab_Dado_Depth", "6 mm")])
        self.assertEqual(RestoreJournal(self.jdir, DESIGN).load()["entries"], {})
        self.assertNotIn("open_edits", r)

    def test_command_completion_is_not_success(self):
        b = FakeBackend(); b.fail_ids = ["dado.shelf1.left.penetration"]
        r = self.run_job(job("measure", {}), b)
        self.assertEqual(r["outcome"], "FAIL")
        self.assertEqual(r["steps"][0]["status"], "FAIL")

    def test_unknown_check_is_never_pass(self):
        b = FakeBackend(); b.unknown_ids = ["interference.joined"]
        self.assertEqual(self.run_job(job("measure", {}), b)["outcome"], "FAIL")

    def test_expected_negative_fail_passes_only_for_exact_ids(self):
        b = FakeBackend(); b.fail_ids = ["profile.tall.height_range"]
        good = {"verdict": "FAIL", "fail_ids": ["profile.tall.height_range"]}
        self.assertEqual(self.run_job(job("measure", {"expect": good}, job_id="job-j1"), b)["outcome"], "PASS")
        b.fail_ids = ["profile.tall.height_range", "panel.left.001.volume"]
        self.assertEqual(self.run_job(job("measure", {"expect": good}, job_id="job-j2"), b)["outcome"], "FAIL")

    def test_stops_on_first_failure_and_reports_open_edit(self):
        b = FakeBackend()
        steps = list(DEMO_STEPS)
        steps[2] = {"command": "measure", "args": {"expect": {"params_mm": {"Cab_Shelf_Length": 9999}}}}
        r = self.run_job(job("run_test_batch", {"steps": steps}), b)
        self.assertEqual(r["outcome"], "FAIL")
        self.assertEqual(len(r["steps"]), 3)                  # stopped, did not continue
        self.assertIn("Cab_Dado_Depth", r["open_edits"])     # temporary edit still applied, reported
        self.assertEqual(b.params["Cab_Dado_Depth"], "10 mm")

    def test_mutation_refused_on_protected_unlisted_or_wrong_design(self):
        for ident, target in ((PROTECTED, PROTECTED), (OTHER, OTHER), (OTHER, DESIGN)):
            b = FakeBackend(design_id=ident)
            r = self.run_job(job("set_parameter", {"name": "Cab_Dado_Depth", "value": 10, "unit": "mm"}, target=target), b)
            self.assertEqual(r["outcome"], "REFUSED", (ident, target))
            self.assertEqual(b.set_calls, [])

    def test_read_only_allowed_on_protected_design_but_identity_still_checked(self):
        b = FakeBackend(design_id=PROTECTED)
        self.assertEqual(self.run_job(job("measure", {}, target=PROTECTED), b)["outcome"], "PASS")
        self.assertEqual(self.run_job(job("measure", {}, target=DESIGN, job_id="job-j2"), FakeBackend(design_id=PROTECTED))["outcome"], "REFUSED")

    def test_unsaved_document_cannot_be_targeted(self):
        b = FakeBackend(design_id=None)
        self.assertEqual(self.run_job(job("measure", {}), b)["outcome"], "REFUSED")

    def test_identity_rechecked_between_steps(self):
        b = FakeBackend(); b.switch_identity_after_measure = OTHER
        r = self.run_job(job("run_test_batch", {"steps": DEMO_STEPS}), b)
        self.assertEqual(r["outcome"], "REFUSED")
        self.assertEqual(b.set_calls, [])

    def test_parameter_bounds_and_formula_protection(self):
        r = self.run_job(job("set_parameter", {"name": "Cab_Dado_Depth", "value": 25, "unit": "mm"}))
        self.assertEqual(r["outcome"], "FAIL"); self.assertEqual(self.b.set_calls, [])
        r = self.run_job(job("set_parameter", {"name": "Cab_Shelf_Length", "value": 100, "unit": "mm"}, job_id="job-j2"))
        self.assertEqual(r["outcome"], "FAIL"); self.assertEqual(self.b.set_calls, [])

    def test_no_stacked_edits_and_restore_needs_journal(self):
        ex = self.ex()
        ev = os.path.join(self.tmp, "ev")
        self.assertEqual(ex.run(job("set_parameter", {"name": "Cab_Dado_Depth", "value": 10, "unit": "mm"}, job_id="job-a"), ev)["outcome"], "PASS")
        r = ex.run(job("set_parameter", {"name": "Cab_Dado_Depth", "value": 12, "unit": "mm"}, job_id="job-b"), ev)
        self.assertEqual(r["outcome"], "FAIL")
        self.assertEqual(self.b.params["Cab_Dado_Depth"], "10 mm")
        r = ex.run(job("restore_parameter", {"name": "Cab_Ply"}, job_id="job-c"), ev)
        self.assertEqual(r["outcome"], "FAIL")
        r = ex.run(job("restore_parameter", {"name": "Cab_Dado_Depth"}, job_id="job-d"), ev)
        self.assertEqual(r["outcome"], "PASS")
        self.assertEqual(self.b.params["Cab_Dado_Depth"], "6 mm")

    def test_failed_restore_verification_keeps_uncertain_journal_and_blocks_mutation(self):
        ex = self.ex()
        ev = os.path.join(self.tmp, "ev")
        ex.run(job("set_parameter", {"name": "Cab_Dado_Depth", "value": 10, "unit": "mm"}, job_id="job-a"), ev)
        self.b.fail_ids = ["panel.left.001.volume"]           # geometry wrong after restore
        r = ex.run(job("restore_parameter", {"name": "Cab_Dado_Depth"}, job_id="job-b"), ev)
        self.assertEqual(r["outcome"], "FAIL")
        self.assertEqual(RestoreJournal(self.jdir, DESIGN).entry("Cab_Dado_Depth")["state"], "restore_unverified")
        self.b.fail_ids = []
        r = ex.run(job("set_parameter", {"name": "Cab_Ply", "value": 15, "unit": "mm"}, job_id="job-c"), ev)
        self.assertEqual(r["outcome"], "REFUSED")              # uncertain journal blocks further edits

    def test_crash_during_set_leaves_pending_journal(self):
        b = FakeBackend(); b.raise_on = "set"
        r = self.run_job(job("set_parameter", {"name": "Cab_Dado_Depth", "value": 10, "unit": "mm"}), b)
        self.assertEqual(r["outcome"], "FAIL")
        self.assertEqual(RestoreJournal(self.jdir, DESIGN).entry("Cab_Dado_Depth")["state"], "pending")

    def test_backend_exception_is_failure_with_traceback(self):
        b = FakeBackend(); b.raise_on = "measure"
        r = self.run_job(job("measure", {}), b)
        self.assertEqual(r["outcome"], "FAIL")
        self.assertEqual(r["steps"][0]["status"], "ERROR")
        self.assertIn("simulated Fusion API error", r["steps"][0]["error"])

    def test_stored_spec_change_fails_measurement(self):
        b = FakeBackend(); b.stored_unchanged = False
        self.assertEqual(self.run_job(job("measure", {}), b)["outcome"], "FAIL")

    def test_batch_counts_must_stay_stable(self):
        class Drift(FakeBackend):
            def measure(self, out_dir, label):
                s = super().measure(out_dir, label)
                if self.measure_calls > 1:
                    s["design_counts"]["timeline_items"] += 1   # a duplicate feature appeared
                return s
        r = self.run_job(job("run_test_batch", {"steps": DEMO_STEPS}), Drift())
        self.assertEqual(r["outcome"], "FAIL")
        self.assertEqual(len(r["steps"]), 3)

    def test_audit_without_timeline_restore_fails(self):
        b = FakeBackend(); b.audit_restored = False
        self.assertEqual(self.run_job(job("audit_cuts", {}), b)["outcome"], "FAIL")

    def test_ping(self):
        r = self.run_job(job("ping", target=None))
        self.assertEqual(r["outcome"], "PASS")


if __name__ == "__main__":
    unittest.main()
