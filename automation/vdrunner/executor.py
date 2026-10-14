"""Command execution, sequencing and safety - independent of Fusion.

The executor talks to Fusion only through a *backend* object (the real one is
``FusionBackend`` in the add-in; tests use a fake).  Backend contract::

    identity() -> {"design_id": str|None, "document_name": str, "is_saved": bool,
                   "is_modified": bool, "fusion_version": str}
    inspect() -> dict                                  # read-only snapshot
    measure(out_dir, label) -> summary dict            # see expect.evaluate_measure
    get_parameter(name) -> {"expression": str, "value_mm": float} | None
    set_parameter_expression(name, expr) -> float      # value_mm read back after regenerate
    audit(out_dir, label) -> summary dict              # see expect.evaluate_audit

Rules enforced here: target identity is re-checked before EVERY step; mutating
work requires an allowlisted, unprotected design and a clean restore journal;
every edit is journalled before it is applied; a restore is accepted only when
the original value reads back AND the follow-up measurement passes; the first
unexpected result stops the job.  Nothing is ever saved by the runner.
"""

from __future__ import annotations

import os
import time
import traceback
from typing import Dict, List, Optional

from . import RESULT_SCHEMA_ID, RUNNER_VERSION
from .expect import evaluate_audit, evaluate_measure
from .journal import JournalError, RestoreJournal
from .policy import PolicyError, check_parameter_edit, check_target
from .queue import utc_now
from .schema import BATCH_COMMAND, is_mutating, steps_of, validate_job


class StepFailed(RuntimeError):
    pass


class Executor:
    def __init__(self, backend, cfg: Dict, journal_dir: str):
        self.b = backend
        self.cfg = cfg
        self.journal_dir = journal_dir

    # ------------------------------------------------------------------
    def run(self, job: Dict, evidence_dir: str) -> Dict:
        validate_job(job)
        t_job = time.perf_counter()
        result = {"schema": RESULT_SCHEMA_ID, "runner_version": RUNNER_VERSION, "job_id": job["job_id"],
                  "command": job["command"], "target": job.get("target"), "started_utc": utc_now(),
                  "steps": [], "outcome": "UNKNOWN", "notes": []}
        mutating = is_mutating(job)
        journal: Optional[RestoreJournal] = None
        try:
            ident = self.b.identity()
            result["identity_at_start"] = ident
            if job["command"] == "ping":
                result["steps"].append(self._step("ping", {}, "PASS", 0.0, ident=ident))
                result["outcome"] = "PASS"
                return self._done(result, t_job)
            check_target(self.cfg, job.get("target"), ident, mutating)
            if job.get("target"):
                journal = RestoreJournal(self.journal_dir, job["target"]["design_id"])
                if mutating:
                    bad = journal.uncertain()
                    if bad:
                        raise PolicyError("restore journal has UNCERTAIN entries %s; resolve before mutating" % sorted(bad))
            stable = job["command"] == BATCH_COMMAND and job["args"].get("stable_counts", True)
            baseline = None
            for i, st in enumerate(steps_of(job)):
                if i:
                    check_target(self.cfg, job.get("target"), self.b.identity(), mutating)
                rec = self._run_step(i, st, evidence_dir, journal, baseline if stable else None, job["job_id"])
                result["steps"].append(rec)
                if st["command"] == "measure" and rec["status"] == "PASS" and baseline is None:
                    baseline = rec["summary"]
                if rec["status"] != "PASS":
                    result["notes"].append("stopped at step %d (%s): %s" % (i, st["command"], rec.get("error") or "; ".join(rec.get("checks", []))))
                    break
            all_pass = result["steps"] and all(s["status"] == "PASS" for s in result["steps"])
            planned = len(steps_of(job))
            result["outcome"] = "PASS" if all_pass and len(result["steps"]) == planned else "FAIL"
        except PolicyError as e:
            result["outcome"] = "REFUSED"
            result["error"] = str(e)
        except Exception as e:  # unexpected backend / API error: never PASS
            result["outcome"] = "FAIL"
            result["error"] = "%s: %s" % (type(e).__name__, e)
            result["traceback"] = traceback.format_exc()
        if journal is not None:
            pending = journal.load()["entries"]
            if pending:
                result["open_edits"] = pending
                result["notes"].append("temporary edits still applied (not restored): %s" % sorted(pending))
        return self._done(result, t_job)

    # ------------------------------------------------------------------
    def _done(self, result: Dict, t0: float) -> Dict:
        result["finished_utc"] = utc_now()
        result["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        result["summary"] = {"steps": len(result["steps"]),
                             "passed": sum(1 for s in result["steps"] if s["status"] == "PASS"),
                             "outcome": result["outcome"]}
        return result

    @staticmethod
    def _step(command, args, status, ms, **extra) -> Dict:
        d = {"command": command, "label": (args or {}).get("label"), "status": status, "elapsed_ms": round(ms, 1)}
        d.update(extra)
        return d

    def _run_step(self, i: int, st: Dict, evidence_dir: str, journal, baseline, job_id: str) -> Dict:
        cmd, args = st["command"], st.get("args", {})
        label = args.get("label") or "%02d_%s" % (i, cmd)
        out_dir = os.path.join(evidence_dir, "%02d_%s" % (i, cmd))
        t0 = time.perf_counter()
        try:
            if cmd == "inspect_design":
                snap = self.b.inspect()
                return self._step(cmd, args, "PASS", (time.perf_counter() - t0) * 1000, inspection=snap)
            if cmd == "measure":
                return self._measure(cmd, args, out_dir, label, baseline, t0)
            if cmd == "audit_cuts":
                summ = self.b.audit(out_dir, label)
                ok, notes = evaluate_audit(summ, args.get("expect"))
                return self._step(cmd, args, "PASS" if ok else "FAIL", (time.perf_counter() - t0) * 1000, summary=summ, checks=notes)
            if cmd == "set_parameter":
                return self._set(cmd, args, journal, job_id, t0)
            if cmd == "restore_parameter":
                return self._restore(cmd, args, out_dir, label, journal, baseline, t0)
            raise StepFailed("unsupported step %s" % cmd)
        except (PolicyError, JournalError, StepFailed) as e:
            return self._step(cmd, args, "FAIL", (time.perf_counter() - t0) * 1000, error=str(e))
        except Exception as e:
            return self._step(cmd, args, "ERROR", (time.perf_counter() - t0) * 1000,
                              error="%s: %s" % (type(e).__name__, e), traceback=traceback.format_exc())

    def _measure(self, cmd, args, out_dir, label, baseline, t0, expect=None) -> Dict:
        summ = self.b.measure(out_dir, label)
        ok, notes = evaluate_measure(summ, expect if expect is not None else args.get("expect"), baseline)
        return self._step(cmd, args, "PASS" if ok else "FAIL", (time.perf_counter() - t0) * 1000, summary=summ, checks=notes)

    def _set(self, cmd, args, journal, job_id, t0) -> Dict:
        if journal is None:
            raise PolicyError("set_parameter requires a target design")
        name, value = args["name"], float(args["value"])
        cur = self.b.get_parameter(name)
        if cur is None:
            raise StepFailed("parameter %s not found in the design" % name)
        new_expr = check_parameter_edit(self.cfg, name, value, cur["expression"])
        journal.begin_edit(name, cur["expression"], cur["value_mm"], new_expr, job_id)
        t_edit = time.perf_counter()
        got = self.b.set_parameter_expression(name, new_expr)
        edit_ms = (time.perf_counter() - t_edit) * 1000
        journal.mark(name, "applied", applied_value_mm=got)
        status = "PASS" if abs(got - value) <= 1e-6 else "FAIL"
        return self._step(cmd, args, status, (time.perf_counter() - t0) * 1000, parameter=name,
                          original_expression=cur["expression"], original_value_mm=cur["value_mm"],
                          new_expression=new_expr, value_read_back_mm=got, edit_and_regenerate_ms=round(edit_ms, 1),
                          checks=["%s read back %s mm (requested %s)" % (name, got, value)])

    def _restore(self, cmd, args, out_dir, label, journal, baseline, t0) -> Dict:
        if journal is None:
            raise PolicyError("restore_parameter requires a target design")
        name = args["name"]
        e = journal.entry(name)
        if e is None:
            raise StepFailed("no recorded edit for %s in the restore journal" % name)
        if e.get("state") != "applied":
            raise StepFailed("journal entry for %s is %s; not safe to restore automatically" % (name, e.get("state")))
        t_edit = time.perf_counter()
        got = self.b.set_parameter_expression(name, e["original_expression"])
        edit_ms = (time.perf_counter() - t_edit) * 1000
        cur = self.b.get_parameter(name)
        value_ok = abs(got - e["original_value_mm"]) <= 1e-6 and cur and cur["expression"] == e["original_expression"]
        m = self._measure("measure", args, out_dir, label, baseline, time.perf_counter())
        if value_ok and m["status"] == "PASS":
            journal.clear(name)
            status = "PASS"
        else:
            journal.mark(name, "restore_unverified", read_back_mm=got)
            status = "FAIL"
        return self._step(cmd, args, status, (time.perf_counter() - t0) * 1000, parameter=name,
                          restored_expression=e["original_expression"], value_read_back_mm=got,
                          edit_and_regenerate_ms=round(edit_ms, 1), verification=m,
                          checks=["value restored: %s" % bool(value_ok)] + m.get("checks", []))
