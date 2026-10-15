"""Filesystem job queue shared by the orchestrator and the Fusion add-in.

Layout under the queue root::

    inbox/<job_id>.json        submitted, waiting for the runner
    claimed/<job_id>.json      taken by the runner (executing, or interrupted)
    cancelled/<job_id>.json    withdrawn by the orchestrator before it was claimed
    results/<job_id>/          result.json + original evidence files
    state/<job_id>.json        lifecycle state (single source of truth for status)
    ledger/<job_id>.submitted  O_EXCL marker: a job id can be submitted once, ever
    ledger/<job_id>.claimed    O_EXCL marker: a job id can be executed once, ever
    runner/heartbeat.json      written by the add-in while it is alive
    journal/                   restore journal for temporary parameter edits

Every JSON file is written atomically (temp file in the same directory, then
``os.replace``).  The ledger markers are never deleted by the tools, so a job id
cannot run twice even after restarts or manual queue clean-up of other folders.
An interrupted job is reported as ``interrupted`` and is never re-queued.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import tempfile
import time
from typing import Dict, List, Optional

from .schema import validate_job

STATUSES = ("queued", "running", "completed", "failed", "rejected", "cancelled", "interrupted")
TERMINAL = ("completed", "failed", "rejected", "cancelled", "interrupted")
_DIRS = ("inbox", "claimed", "cancelled", "results", "state", "ledger", "runner", "journal")


class QueueError(RuntimeError):
    pass


class DuplicateJob(QueueError):
    pass


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds")


_RETRIES, _RETRY_S = 50, 0.02   # Windows: a reader holding the file blocks os.replace briefly (WinError 32)


def _retry(fn, *args):
    for i in range(_RETRIES):
        try:
            return fn(*args)
        except PermissionError:
            if i == _RETRIES - 1:
                raise
            time.sleep(_RETRY_S)


def atomic_write_json(path: str, obj) -> None:
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, sort_keys=False)
            fh.flush()
            os.fsync(fh.fileno())
        _retry(os.replace, tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read_json_once(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_json(path: str):
    return _retry(_read_json_once, path)


def _create_exclusive(path: str, text: str) -> bool:
    """Create ``path`` only if it does not exist.  Returns False if it already existed."""
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return True


class JobQueue:
    def __init__(self, root: str):
        self.root = os.path.abspath(root)

    # ------------------------------------------------------------- paths
    def ensure(self) -> "JobQueue":
        for d in _DIRS:
            os.makedirs(os.path.join(self.root, d), exist_ok=True)
        return self

    def p(self, *parts) -> str:
        return os.path.join(self.root, *parts)

    def result_dir(self, job_id: str) -> str:
        return self.p("results", job_id)

    # ------------------------------------------------------------- state
    def write_state(self, job_id: str, status: str, **info) -> Dict:
        if status not in STATUSES:
            raise QueueError("unknown status %r" % status)
        prev = self.read_state(job_id) or {"job_id": job_id, "history": []}
        prev["status"] = status
        prev["updated_utc"] = utc_now()
        prev.setdefault("history", []).append({"status": status, "utc": prev["updated_utc"]})
        prev.update(info)
        atomic_write_json(self.p("state", job_id + ".json"), prev)
        return prev

    def read_state(self, job_id: str) -> Optional[Dict]:
        path = self.p("state", job_id + ".json")
        return read_json(path) if os.path.exists(path) else None

    # ------------------------------------------------------------- orchestrator side
    def submit(self, job: Dict) -> Dict:
        validate_job(job)
        self.ensure()
        jid = job["job_id"]
        if not _create_exclusive(self.p("ledger", jid + ".submitted"), utc_now()):
            raise DuplicateJob("job id %r was already submitted (ledger)" % jid)
        # State first, inbox second: once the file is in the inbox the runner may claim it
        # immediately, so the orchestrator must not write the state file after that point.
        st = self.write_state(jid, "queued", command=job["command"], submitted_utc=utc_now())
        atomic_write_json(self.p("inbox", jid + ".json"), job)
        return st

    def cancel(self, job_id: str) -> bool:
        """Withdraw a job that the runner has not claimed.  Returns False if it was already claimed."""
        src = self.p("inbox", job_id + ".json")
        try:
            os.replace(src, self.p("cancelled", job_id + ".json"))
        except FileNotFoundError:
            return False
        self.write_state(job_id, "cancelled", reason="cancelled by orchestrator before execution")
        return True

    # ------------------------------------------------------------- runner side
    def pending(self) -> List[str]:
        try:
            names = sorted(n for n in os.listdir(self.p("inbox")) if n.endswith(".json") and not n.startswith("."))
        except FileNotFoundError:
            return []
        return [n[:-5] for n in names]

    def claim(self, job_id: str) -> Dict:
        """Atomically take a job for execution.  Raises DuplicateJob if it was ever claimed."""
        if not _create_exclusive(self.p("ledger", job_id + ".claimed"), utc_now()):
            # Never execute twice.  Move any stray copy out of the inbox.
            try:
                os.replace(self.p("inbox", job_id + ".json"), self.p("cancelled", job_id + ".json"))
            except FileNotFoundError:
                pass
            raise DuplicateJob("job id %r was already claimed once; refusing to run it again" % job_id)
        dst = self.p("claimed", job_id + ".json")
        os.replace(self.p("inbox", job_id + ".json"), dst)
        job = read_json(dst)
        self.write_state(job_id, "running", started_utc=utc_now(), runner_pid=os.getpid())
        return job

    def finish(self, job_id: str, result: Dict) -> Dict:
        """Record a finished job.  ``result['outcome']`` decides completed (PASS) vs failed."""
        rdir = self.result_dir(job_id)
        os.makedirs(rdir, exist_ok=True)
        atomic_write_json(os.path.join(rdir, "result.json"), result)
        src = self.p("claimed", job_id + ".json")
        if os.path.exists(src):
            os.replace(src, os.path.join(rdir, "job.json"))
        status = "completed" if result.get("outcome") == "PASS" else "failed"
        return self.write_state(job_id, status, finished_utc=utc_now(), outcome=result.get("outcome"),
                                result_path=os.path.join(rdir, "result.json"))

    def reject(self, job_id: str, reason: str) -> Dict:
        rdir = self.result_dir(job_id)
        os.makedirs(rdir, exist_ok=True)
        for folder in ("claimed", "inbox"):
            src = self.p(folder, job_id + ".json")
            if os.path.exists(src):
                os.replace(src, os.path.join(rdir, "job.json"))
        atomic_write_json(os.path.join(rdir, "result.json"),
                          {"job_id": job_id, "outcome": "REJECTED", "error": reason, "finished_utc": utc_now()})
        return self.write_state(job_id, "rejected", reason=reason, outcome="REJECTED")

    def recover_interrupted(self) -> List[str]:
        """Called by the runner at start-up.  Any job left in claimed/ was interrupted.

        It is marked ``interrupted`` (outcome UNKNOWN) and is NOT re-run: a mutating
        command may have partially applied.  Returns the affected job ids.
        """
        hits = []
        try:
            names = os.listdir(self.p("claimed"))
        except FileNotFoundError:
            return hits
        for n in sorted(names):
            if not n.endswith(".json") or n.startswith("."):
                continue
            jid = n[:-5]
            st = self.read_state(jid) or {}
            if st.get("status") in TERMINAL and st.get("status") != "interrupted":
                continue
            rdir = self.result_dir(jid)
            os.makedirs(rdir, exist_ok=True)
            os.replace(self.p("claimed", n), os.path.join(rdir, "job.json"))
            atomic_write_json(os.path.join(rdir, "result.json"), {
                "job_id": jid, "outcome": "UNKNOWN", "finished_utc": utc_now(),
                "error": "runner stopped while this job was executing; the design state is UNCERTAIN. "
                         "Inspect the design and the restore journal before any further mutating job."})
            self.write_state(jid, "interrupted", outcome="UNKNOWN", recovered_utc=utc_now())
            hits.append(jid)
        return hits

    # ------------------------------------------------------------- heartbeat
    def heartbeat(self, info: Dict) -> None:
        info = dict(info, utc=utc_now(), epoch=time.time(), pid=os.getpid())
        atomic_write_json(self.p("runner", "heartbeat.json"), info)

    def runner_status(self, max_age_s: float = 10.0) -> Dict:
        path = self.p("runner", "heartbeat.json")
        if not os.path.exists(path):
            return {"alive": False, "reason": "no heartbeat file"}
        hb = read_json(path)
        age = time.time() - float(hb.get("epoch", 0))
        return dict(hb, alive=age <= max_age_s, age_s=round(age, 2))

    # ------------------------------------------------------------- listing
    def list_states(self) -> List[Dict]:
        out = []
        try:
            names = sorted(os.listdir(self.p("state")))
        except FileNotFoundError:
            return out
        for n in names:
            if n.endswith(".json") and not n.startswith("."):
                out.append(read_json(self.p("state", n)))
        return out
