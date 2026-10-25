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
unexpected result stops the job. Dedicated demo lifecycle operations use
runner-created session references and fresh geometry verification before saving.
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
from .schema import BATCH_COMMAND, DEMO_COMMANDS, is_mutating, steps_of, validate_job
from .width_change import plan_width_change
from .shelf_change import JOURNAL_KEY, equivalent, plan_shelf_count_change


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
            if job["command"] in DEMO_COMMANDS:
                summary = self.b.demo_command(job["command"], job["args"], evidence_dir, job["job_id"])
                status = "PASS" if summary.get("outcome") == "PASS" else "FAIL"
                result["steps"].append(self._step(job["command"], {}, status, 0, summary=summary))
                result["outcome"] = status
                return self._done(result, t_job)
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
                if st["command"] in ("update_width", "update_shelf_count") and rec["status"] == "PASS":
                    baseline = rec["post_measure"]["summary"]   # the updated cabinet is the new reference
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
            if cmd == "preview_width_change":
                plan = self._plan(args)
                plan.pop("_state", None)
                status = "PASS" if not plan["refusals"] else "FAIL"
                return self._step(cmd, args, status, (time.perf_counter() - t0) * 1000, preview=self._public(plan),
                                  checks=["OK safe to update"] if status == "PASS" else ["REFUSED " + r for r in plan["refusals"]])
            if cmd == "update_width":
                return self._update_width(cmd, args, out_dir, label, journal, job_id, t0)
            if cmd in ("preview_shelf_count_change", "update_shelf_count"):
                if journal is None or journal.load()["entries"]:
                    raise PolicyError("shelf change requires a target and an entirely clear restore journal")
                before = self.b.shelf_state()
                plan = plan_shelf_count_change(self.b.g3_modules(), before, args["new_shelf_count"])
                if plan["refusals"] or cmd == "preview_shelf_count_change":
                    return self._step(cmd, args, "FAIL" if plan["refusals"] else "PASS",
                                      (time.perf_counter()-t0)*1000, preview=self._public(plan),
                                      refused=bool(plan["refusals"]), checks=plan["refusals"])
                return self._update_shelves(cmd, args, out_dir, label, journal, job_id, t0, before, plan)
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

    # ------------------------------------------------------------------ G4: bounded shelf reconstruction
    def _shelf_verify(self, out_dir, label, count, expected_hash, expected_params, expected_counts):
        m = self._measure("measure", {}, out_dir, label, None, time.perf_counter(),
                          expect={"design_spec_hash": expected_hash, "params_mm": expected_params,
                                  "counts": expected_counts})
        audit = self.b.audit(out_dir, label)
        audit_ok, notes = evaluate_audit(audit, {"features_passed": 2*count})
        exact_ops = {"dado.shelf%d.%s" % (n,side): "PASS" for n in range(1,count+1) for side in ("left","right")}
        state = self.b.shelf_state()
        ok = (m["status"] == "PASS" and audit_ok and audit.get("operations") == exact_ops
              and equivalent(m["summary"].get("params_mm"), expected_params))
        return {"verified": ok, "measure": m, "audit": audit, "audit_checks": notes, "state": state}

    @staticmethod
    def _same_document(before, after):
        keys = ("design_id", "document_name", "is_saved", "version_number")
        return (bool(before.get("design_id")) and before.get("is_saved") is True
                and type(before.get("version_number")) is int
                and all(before.get(k) == after.get(k) for k in keys))

    def _update_shelves(self, cmd, args, out_dir, label, journal, job_id, t0, before, plan):
        g3 = self.b.g3_modules()
        old = g3["design_spec"].load_design_spec(before["stored_text"])
        asm = g3["variants"].build_variant(old.resolved_params, old.profile)
        old_params = asm.parameters.resolve()
        old_counts = {"user_parameters": len(old_params), "root_occurrences": len(asm.panels),
                      "all_components": len(asm.panels)+1,
                      "timeline_items": 3*len(asm.panels)+2*len(asm.operations)}
        pre = self._shelf_verify(os.path.join(out_dir,"pre"), label+" pre", plan["old_shelf_count"],
                                 old.design_spec_hash, old_params, old_counts)
        rec = {"preview": self._public(plan), "pre_verification": pre}
        if (not pre["verified"] or not equivalent(before["inventory"], pre["state"]["inventory"])
                or not self._same_document(before["identity"], self.b.identity())):
            return self._step(cmd,args,"FAIL",(time.perf_counter()-t0)*1000, refused=True,
                              checks=["REFUSED baseline or document identity verification"], **rec)
        operation = self.b.begin_shelf_regeneration(plan["new_stored_text"])
        journal.begin_structural(JOURNAL_KEY, before, plan["new_stored_text"], job_id)
        try:
            if not self._same_document(before["identity"], self.b.identity()):
                raise StepFailed("document identity changed before mutation")
            operation.apply(plan["new_stored_text"])
            post = self._shelf_verify(os.path.join(out_dir,"post"), label+" post", plan["new_shelf_count"],
                                     plan["new_design_spec_hash"], plan["expected_after_mm"], plan["expected_counts"])
            rec["post_verification"] = post
            rec["post_measure"] = post["measure"]
            if (not post["verified"] or post["state"]["stored_text"] != plan["new_stored_text"]
                    or not self._same_document(before["identity"], self.b.identity())):
                raise StepFailed("post-reconstruction verification failed")
            journal.clear(JOURNAL_KEY)
            return self._step(cmd,args,"PASS",(time.perf_counter()-t0)*1000, **rec)
        except Exception as exc:
            rec["error"] = "%s: %s" % (type(exc).__name__, exc)
            recovery = {"verified": False}
            try:
                # Never reconstruct against a different active document or saved identity.
                if not self._same_document(before["identity"], self.b.identity()):
                    raise StepFailed("document changed; automatic recovery stopped")
                if operation.started:
                    operation.restore(before["stored_text"])
                recovery = self._shelf_verify(os.path.join(out_dir,"recovery"), label+" recovery", plan["old_shelf_count"],
                                              old.design_spec_hash, old_params, old_counts)
                recovery["verified"] = (recovery["verified"]
                    and recovery["state"]["stored_text"] == before["stored_text"]
                    and equivalent(before["inventory"], recovery["state"]["inventory"])
                    and self._same_document(before["identity"], self.b.identity()))
            except Exception as restore_exc:
                recovery["error"] = "%s: %s" % (type(restore_exc).__name__, restore_exc)
                recovery["verified"] = False
            if recovery["verified"]:
                journal.clear(JOURNAL_KEY)
            else:
                journal.mark(JOURNAL_KEY, "restore_unverified", error=rec["error"], recovery=recovery)
            rec["recovery"] = recovery
            return self._step(cmd,args,"FAIL",(time.perf_counter()-t0)*1000, **rec)

    # ------------------------------------------------------------------ G4: safe width update
    def _plan(self, args) -> Dict:
        if args["unit"] != "mm":
            raise PolicyError("unsupported unit")
        st = self.b.cabinet_state()
        bounds = self.cfg.get("parameter_bounds_mm", {}).get("Cab_Width")
        plan = plan_width_change(self.b.g3_modules(), st["stored_text"], st["live_params"], float(args["new_width"]), bounds)
        plan["_state"] = st
        return plan

    @staticmethod
    def _public(plan: Dict) -> Dict:
        return {k: v for k, v in plan.items() if not k.startswith("_") and k != "new_stored_text"}

    def _update_width(self, cmd, args, out_dir, label, journal, job_id, t0) -> Dict:
        if journal is None:
            raise PolicyError("update_width requires a target design")
        plan = self._plan(args)
        before = plan.pop("_state")
        rec = {"preview": self._public(plan)}
        if plan["refusals"]:
            return self._step(cmd, args, "FAIL", (time.perf_counter() - t0) * 1000, refused=True,
                              checks=["REFUSED " + r for r in plan["refusals"]], **rec)
        pre = self._measure("measure", {}, os.path.join(out_dir, "pre"), label + " pre", None, time.perf_counter())
        rec["pre_measure"] = pre
        if pre["status"] != "PASS":
            return self._step(cmd, args, "FAIL", (time.perf_counter() - t0) * 1000, refused=True,
                              checks=["REFUSED existing cabinet does not validate before the update"] + pre.get("checks", []), **rec)
        orig = self.b.get_parameter("Cab_Width")
        journal.begin_edit("Cab_Width", orig["expression"], orig["value_mm"], plan["new_expression"], job_id)
        journal.mark("Cab_Width", "pending", kind="update_width", original_stored_text=before["stored_text"],
                     new_design_spec_hash=plan["new_design_spec_hash"])
        problems: List[str] = []
        t_apply = time.perf_counter()
        try:
            got = self.b.set_parameter_expression("Cab_Width", plan["new_expression"])
            journal.mark("Cab_Width", "applied", applied_value_mm=got)
            stored_back = self.b.store_spec_text(plan["new_stored_text"])
            rec["apply_ms"] = round((time.perf_counter() - t_apply) * 1000, 1)
            if abs(got - plan["new_width_mm"]) > 1e-6:
                problems.append("Cab_Width read back %s, expected %s" % (got, plan["new_width_mm"]))
            if stored_back != plan["new_stored_text"]:
                problems.append("stored specification read-back differs from the new canonical spec")
            exp = dict(args.get("expect") or {})
            exp.setdefault("design_spec_hash", plan["new_design_spec_hash"])
            exp.setdefault("counts", pre["summary"]["design_counts"])
            exp.setdefault("params_mm", {"Cab_Width": plan["expected_after_mm"]["Cab_Width"],
                                         "Cab_Shelf_Length": plan["expected_after_mm"]["Cab_Shelf_Length"]})
            post = self._measure("measure", {}, os.path.join(out_dir, "post"), label + " post", None,
                                 time.perf_counter(), expect=exp)
            rec["post_measure"] = post
            if post["status"] != "PASS":
                problems.append("post-update validation failed")
            after = self.b.cabinet_state()
            rec["identity_check"] = ident = _compare_identity(before, after)
            problems += ident["problems"]
            live_bad = [n for n, v in plan["expected_after_mm"].items()
                        if abs(after["live_params"].get(n, {}).get("value_mm", float("nan")) - v) > 1e-6]
            if live_bad:
                problems.append("live parameters differ from the updated spec: %s" % live_bad)
        except Exception as e:  # any API failure => roll back
            problems.append("%s: %s" % (type(e).__name__, e))
            rec["traceback"] = traceback.format_exc()
        if not problems:
            journal.clear("Cab_Width")   # permanent, verified change: spec and geometry agree again
            s = rec["post_measure"]["summary"]
            return self._step(cmd, args, "PASS", (time.perf_counter() - t0) * 1000, checks=[
                "OK width %s -> %s mm; spec hash %s -> %s; validation %s/%s; component ids and timeline unchanged" % (
                    plan["old_width_mm"], plan["new_width_mm"], plan["old_design_spec_hash"][:12],
                    plan["new_design_spec_hash"][:12], s["counts"]["PASS"], s["total"])], **rec)
        rec["rollback"] = self._rollback_width(orig, before["stored_text"], plan["old_design_spec_hash"],
                                               pre["summary"]["design_counts"], out_dir, label, journal)
        return self._step(cmd, args, "FAIL", (time.perf_counter() - t0) * 1000, checks=["FAIL " + p for p in problems], **rec)

    def _rollback_width(self, orig, stored_text, old_hash, pre_counts, out_dir, label, journal) -> Dict:
        out = {}
        try:
            out["value_read_back_mm"] = self.b.set_parameter_expression("Cab_Width", orig["expression"])
            out["stored_restored"] = self.b.store_spec_text(stored_text) == stored_text
            m = self._measure("measure", {}, os.path.join(out_dir, "rollback"), label + " rollback", None, time.perf_counter(),
                              expect={"design_spec_hash": old_hash, "params_mm": {"Cab_Width": orig["value_mm"]},
                                      "counts": pre_counts})
            out["verification"] = m
            ok = out["stored_restored"] and m["status"] == "PASS"
        except Exception as e:
            out["error"] = "%s: %s" % (type(e).__name__, e)
            ok = False
        if ok:
            journal.clear("Cab_Width")
        else:
            journal.mark("Cab_Width", "restore_unverified")
        out["verified"] = ok
        return out


def _compare_identity(before: Dict, after: Dict) -> Dict:
    """Same managed components (stable id, entity token, component name, body count) and timeline length."""
    problems = []
    if before["occurrences"] != after["occurrences"]:
        problems.append("managed component identities changed")
    if before["timeline_count"] != after["timeline_count"]:
        problems.append("timeline length changed %s -> %s (features added/removed)" % (
            before["timeline_count"], after["timeline_count"]))
    ids = [o["stable_id"] for o in after["occurrences"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate stable ids after update")
    return {"problems": problems, "occurrences_before": before["occurrences"], "occurrences_after": after["occurrences"],
            "timeline_before": before["timeline_count"], "timeline_after": after["timeline_count"]}
