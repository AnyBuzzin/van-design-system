import os
import time
import unittest

from _helpers import TmpDirCase, job
from vdrunner.cli import prepare, wait_for
from vdrunner.queue import DuplicateJob, JobQueue, atomic_write_json, read_json


class QueueTests(TmpDirCase):
    def q(self):
        return JobQueue(os.path.join(self.tmp, "queue")).ensure()

    def test_atomic_write_leaves_no_temp_files(self):
        p = os.path.join(self.tmp, "x", "a.json")
        atomic_write_json(p, {"a": 1})
        atomic_write_json(p, {"a": 2})
        self.assertEqual(read_json(p), {"a": 2})
        self.assertEqual(os.listdir(os.path.dirname(p)), ["a.json"])

    def test_lifecycle_submit_claim_finish(self):
        q = self.q()
        st = q.submit(job("ping", target=None))
        self.assertEqual(st["status"], "queued")
        self.assertEqual(q.pending(), ["job-001"])
        j = q.claim("job-001")
        self.assertEqual(j["command"], "ping")
        self.assertEqual(q.read_state("job-001")["status"], "running")
        self.assertEqual(q.pending(), [])
        q.finish("job-001", {"job_id": "job-001", "outcome": "PASS"})
        st = q.read_state("job-001")
        self.assertEqual((st["status"], st["outcome"]), ("completed", "PASS"))
        self.assertTrue(os.path.exists(os.path.join(q.result_dir("job-001"), "job.json")))
        self.assertEqual([h["status"] for h in st["history"]], ["queued", "running", "completed"])

    def test_failed_outcome_is_not_completed(self):
        q = self.q()
        q.submit(job("ping", target=None)); q.claim("job-001")
        self.assertEqual(q.finish("job-001", {"outcome": "FAIL"})["status"], "failed")

    def test_duplicate_submission_rejected_even_after_cleanup(self):
        q = self.q()
        q.submit(job("ping", target=None))
        with self.assertRaises(DuplicateJob):
            q.submit(job("ping", target=None))
        q.claim("job-001"); q.finish("job-001", {"outcome": "PASS"})
        # someone deletes the state + results: the ledger still blocks re-use of the id
        import shutil
        shutil.rmtree(q.p("state")); shutil.rmtree(q.p("results")); q.ensure()
        with self.assertRaises(DuplicateJob):
            q.submit(job("ping", target=None))

    def test_duplicate_execution_blocked_after_restart(self):
        q = self.q()
        q.submit(job("ping", target=None))
        q.claim("job-001")
        # a stray copy re-appears in the inbox (e.g. restored from backup)
        atomic_write_json(q.p("inbox", "job-001.json"), job("ping", target=None))
        q2 = JobQueue(q.root)  # "restarted" runner
        with self.assertRaises(DuplicateJob):
            q2.claim("job-001")
        self.assertEqual(q2.pending(), [])
        self.assertTrue(os.path.exists(q2.p("cancelled", "job-001.json")))

    def test_interrupted_job_is_marked_unknown_and_never_requeued(self):
        q = self.q()
        q.submit(job("set_parameter", {"name": "Cab_Dado_Depth", "value": 10, "unit": "mm"}))
        q.claim("job-001")                      # runner crashes here
        hits = JobQueue(q.root).recover_interrupted()
        self.assertEqual(hits, ["job-001"])
        st = q.read_state("job-001")
        self.assertEqual((st["status"], st["outcome"]), ("interrupted", "UNKNOWN"))
        self.assertEqual(q.pending(), [])
        self.assertIn("UNCERTAIN", read_json(os.path.join(q.result_dir("job-001"), "result.json"))["error"])
        self.assertEqual(JobQueue(q.root).recover_interrupted(), [])   # idempotent

    def test_cancel_only_before_claim(self):
        q = self.q()
        q.submit(job("ping", target=None, job_id="job-a"))
        self.assertTrue(q.cancel("job-a"))
        self.assertEqual(q.read_state("job-a")["status"], "cancelled")
        q.submit(job("ping", target=None, job_id="job-b"))
        q.claim("job-b")
        self.assertFalse(q.cancel("job-b"))

    def test_reject(self):
        q = self.q()
        q.submit(job("ping", target=None)); q.claim("job-001")
        self.assertEqual(q.reject("job-001", "bad")["status"], "rejected")

    def test_heartbeat_age(self):
        q = self.q()
        self.assertFalse(q.runner_status()["alive"])
        q.heartbeat({"runner_version": "t"})
        self.assertTrue(q.runner_status(5)["alive"])
        hb = read_json(q.p("runner", "heartbeat.json")); hb["epoch"] -= 100
        atomic_write_json(q.p("runner", "heartbeat.json"), hb)
        self.assertFalse(q.runner_status(5)["alive"])

    def test_wait_timeout_cancels_queued_job_so_it_never_runs_late(self):
        q = self.q()
        q.heartbeat({})                                   # runner looks alive but never claims
        j = prepare({"command": "ping", "args": {}})
        q.submit(j)
        w = wait_for(q, j["job_id"], timeout_s=0.3, poll_s=0.05, heartbeat_max_age_s=60)
        self.assertEqual(w["wait"], "timeout_cancelled")
        self.assertEqual(q.pending(), [])

    def test_wait_detects_missing_runner(self):
        q = self.q()
        j = prepare({"command": "ping", "args": {}})
        q.submit(j)
        w = wait_for(q, j["job_id"], timeout_s=5, poll_s=0.05, heartbeat_max_age_s=0.1)
        self.assertEqual(w["wait"], "runner_not_running")
        self.assertEqual(q.read_state(j["job_id"])["status"], "cancelled")

    def test_wait_reports_running_job_on_timeout(self):
        q = self.q()
        q.heartbeat({})
        j = prepare({"command": "ping", "args": {}})
        q.submit(j); q.claim(j["job_id"])
        w = wait_for(q, j["job_id"], timeout_s=0.2, poll_s=0.05, heartbeat_max_age_s=60)
        self.assertEqual(w["wait"], "timeout_running")

    def test_prepare_assigns_unique_ids(self):
        ids = {prepare({"command": "ping", "args": {}})["job_id"] for _ in range(50)}
        self.assertEqual(len(ids), 50)

    def test_state_written_before_job_reaches_inbox(self):
        """Regression (real Fusion, 2026-10-15): the runner claimed a job while the CLI was still
        writing its 'queued' state -> WinError 32.  The state must exist before the inbox file."""
        q = self.q()
        seen = {}
        import vdrunner.queue as qm
        real = qm.atomic_write_json

        def spy(path, obj):
            if os.path.dirname(path) == q.p("inbox"):
                seen["state_at_inbox_write"] = q.read_state("job-001")
            return real(path, obj)
        qm.atomic_write_json = spy
        try:
            q.submit(job("ping", target=None))
        finally:
            qm.atomic_write_json = real
        self.assertEqual(seen["state_at_inbox_write"]["status"], "queued")

    def test_replace_retries_transient_sharing_violation(self):
        import vdrunner.queue as qm
        calls = {"n": 0}
        real = os.replace

        def flaky(a, b):
            calls["n"] += 1
            if calls["n"] < 3:
                raise PermissionError(32, "being used by another process")
            return real(a, b)
        qm.os.replace = flaky
        try:
            atomic_write_json(os.path.join(self.tmp, "r.json"), {"ok": 1})
        finally:
            qm.os.replace = real
        self.assertEqual(read_json(os.path.join(self.tmp, "r.json")), {"ok": 1})
        self.assertEqual(calls["n"], 3)


if __name__ == "__main__":
    unittest.main()
