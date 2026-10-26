"""``python -m vdrunner`` - local orchestrator for the VanDesign Fusion runner.

Exit codes: 0 job PASS / command ok; 1 job FAIL, rejected, interrupted or
unknown; 2 invalid job or usage; 3 timeout; 4 runner not running / lost.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
from typing import Dict, Optional

from . import JOB_SCHEMA_ID, RUNNER_VERSION
from .evidence import package
from .policy import default_queue_root
from .queue import TERMINAL, DuplicateJob, JobQueue, read_json, utc_now
from .schema import JobSchemaError, validate_job

EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_TIMEOUT, EXIT_RUNNER = 0, 1, 2, 3, 4


def new_job_id(prefix: str = "vd") -> str:
    return "%s-%s-%s" % (prefix, time.strftime("%Y%m%dT%H%M%S"), secrets.token_hex(3))


def prepare(job: Dict, job_id: Optional[str] = None) -> Dict:
    job = dict(job)
    job.setdefault("schema", JOB_SCHEMA_ID)
    job["job_id"] = job_id or job.get("job_id") or new_job_id()
    job.setdefault("created_utc", utc_now())
    job.setdefault("args", {})
    return validate_job(job)


def wait_for(q: JobQueue, job_id: str, timeout_s: float, poll_s: float = 0.25, heartbeat_max_age_s: float = 15.0) -> Dict:
    """Block until the job reaches a terminal state, the runner disappears, or the timeout passes.

    On timeout a still-queued job is cancelled (so it can never run late);
    a running job cannot be cancelled and is reported as ``timeout_running``.

    A silent heartbeat only cancels a job that is still queued. Once the
    runner has claimed a job, heartbeat silence is not evidence of loss:
    Fusion can starve the watcher thread while its main thread is busy, and
    every live session since Issue #56 logged such false ``runner_lost``
    reports for jobs that then completed. A claimed job therefore ends as
    ``done`` or ``timeout_running``; a real crash is marked ``interrupted``
    at the runner's next start.
    """
    t0 = time.time()
    while True:
        st = q.read_state(job_id) or {}
        if st.get("status") in TERMINAL:
            return {"wait": "done", "state": st, "waited_s": round(time.time() - t0, 3)}
        rs = q.runner_status(heartbeat_max_age_s)
        if (st.get("status") == "queued" and not rs.get("alive")
                and time.time() - t0 > heartbeat_max_age_s and q.cancel(job_id)):
            return {"wait": "runner_not_running", "state": q.read_state(job_id), "runner": rs}
        if time.time() - t0 > timeout_s:
            if st.get("status") == "queued" and q.cancel(job_id):
                return {"wait": "timeout_cancelled", "state": q.read_state(job_id)}
            return {"wait": "timeout_running", "state": st}
        time.sleep(poll_s)


def _exit_for(w: Dict) -> int:
    if w["wait"] == "done":
        return EXIT_OK if (w["state"] or {}).get("status") == "completed" else EXIT_FAIL
    if w["wait"] in ("runner_not_running", "runner_lost"):
        return EXIT_RUNNER
    return EXIT_TIMEOUT


def _print(obj) -> None:
    print(json.dumps(obj, indent=2))


def _submit_and_maybe_wait(q: JobQueue, job: Dict, wait: bool, timeout: float) -> int:
    t0 = time.perf_counter()
    st = q.submit(job)
    submit_ms = round((time.perf_counter() - t0) * 1000, 2)
    out = {"job_id": job["job_id"], "status": st["status"], "submit_ms": submit_ms}
    if not wait:
        _print(out)
        return EXIT_OK
    w = wait_for(q, job["job_id"], timeout)
    out.update(wait=w["wait"], waited_s=w.get("waited_s"), state=w.get("state"))
    res_path = os.path.join(q.result_dir(job["job_id"]), "result.json")
    if os.path.exists(res_path):
        res = read_json(res_path)
        out["outcome"] = res.get("outcome")
        out["summary"] = res.get("summary")
    _print(out)
    return _exit_for(w)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="vdrunner", description="VanDesign Fusion runner orchestrator v" + RUNNER_VERSION)
    ap.add_argument("--queue", default=os.environ.get("VANDESIGN_RUNNER_QUEUE") or default_queue_root())
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit", help="validate and queue a job JSON file")
    s.add_argument("file"); s.add_argument("--job-id"); s.add_argument("--wait", action="store_true")
    s.add_argument("--timeout", type=float, default=600)
    s.add_argument("--target-id", help="override target.design_id"); s.add_argument("--target-name")
    for name in ("ping", "inspect"):
        p = sub.add_parser(name, help="submit a %s job and wait" % name)
        p.add_argument("--timeout", type=float, default=60)
    v = sub.add_parser("validate", help="validate a job file without queuing it"); v.add_argument("file")
    st = sub.add_parser("status", help="show a job state"); st.add_argument("job_id")
    w = sub.add_parser("wait", help="wait for a job"); w.add_argument("job_id"); w.add_argument("--timeout", type=float, default=600)
    r = sub.add_parser("result", help="print a job result.json"); r.add_argument("job_id")
    c = sub.add_parser("cancel", help="withdraw a queued job"); c.add_argument("job_id")
    sub.add_parser("list", help="list all job states")
    sub.add_parser("runner", help="runner heartbeat status")
    pk = sub.add_parser("package", help="zip original evidence for jobs"); pk.add_argument("job_ids", nargs="+"); pk.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    q = JobQueue(a.queue).ensure()

    try:
        if a.cmd == "submit":
            job = read_json(a.file)
            if a.target_id:
                job["target"] = {"design_id": a.target_id}
                if a.target_name:
                    job["target"]["document_name"] = a.target_name
            job = prepare(job, a.job_id)
            return _submit_and_maybe_wait(q, job, a.wait, a.timeout)
        if a.cmd in ("ping", "inspect"):
            job = prepare({"command": "ping" if a.cmd == "ping" else "inspect_design", "args": {}})
            return _submit_and_maybe_wait(q, job, True, a.timeout)
        if a.cmd == "validate":
            prepare(read_json(a.file), "validate-only")
            print("valid")
            return EXIT_OK
        if a.cmd == "status":
            _print(q.read_state(a.job_id) or {"job_id": a.job_id, "status": "unknown"})
            return EXIT_OK
        if a.cmd == "wait":
            w = wait_for(q, a.job_id, a.timeout)
            _print(w)
            return _exit_for(w)
        if a.cmd == "result":
            _print(read_json(os.path.join(q.result_dir(a.job_id), "result.json")))
            return EXIT_OK
        if a.cmd == "cancel":
            ok = q.cancel(a.job_id)
            _print({"job_id": a.job_id, "cancelled": ok})
            return EXIT_OK if ok else EXIT_FAIL
        if a.cmd == "list":
            for stt in q.list_states():
                print("%-40s %-12s %-8s %s" % (stt.get("job_id"), stt.get("status"), stt.get("outcome") or "", stt.get("command") or ""))
            return EXIT_OK
        if a.cmd == "runner":
            rs = q.runner_status()
            _print(rs)
            return EXIT_OK if rs.get("alive") else EXIT_RUNNER
        if a.cmd == "package":
            _print(package(q, a.job_ids, a.out))
            return EXIT_OK
    except (JobSchemaError, DuplicateJob) as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return EXIT_USAGE
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
