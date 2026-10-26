"""Strict validation of runner jobs (schema ``vandesign.runner.job/1``).

Stdlib only.  Unknown keys, unknown commands, wrong types and out-of-bounds
values are rejected - nothing is coerced.  The machine-readable JSON Schema in
``automation/schema/vdrunner-job-v1.schema.json`` documents the same contract;
this module is the enforcement point used by both the orchestrator (before a
job is queued) and the Fusion add-in (before a job is executed).
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, List

from . import JOB_SCHEMA_ID

READ_ONLY_COMMANDS = ("ping", "inspect_design", "measure", "audit_cuts", "preview_width_change", "preview_shelf_count_change")
DEMO_COMMANDS = ("create_demo_design", "run_approved_demo", "save_demo_design", "capture_demo_viewport", "verify_demo_persistence", "close_demo_design")
MUTATING_COMMANDS = ("set_parameter", "restore_parameter", "update_width", "update_shelf_count") + DEMO_COMMANDS[:3] + ("close_demo_design",)
BATCH_COMMAND = "run_test_batch"
ALL_COMMANDS = READ_ONLY_COMMANDS + MUTATING_COMMANDS + ("capture_demo_viewport", "verify_demo_persistence", BATCH_COMMAND)
STEP_COMMANDS = ("inspect_design", "measure", "set_parameter", "restore_parameter", "audit_cuts",
                 "preview_width_change", "update_width", "preview_shelf_count_change", "update_shelf_count")

JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,79}$")
PARAM_NAME_RE = re.compile(r"^Cab_[A-Za-z0-9_]{1,40}$")
CHECK_ID_RE = re.compile(r"^[a-z0-9_.]{3,120}$")
SUPPORTED_UNITS = ("mm",)
MAX_STEPS = 60
MAX_TIMEOUT_S = 3600


class JobSchemaError(ValueError):
    """A job document does not satisfy the runner job schema."""


def _fail(path: str, msg: str) -> None:
    raise JobSchemaError("%s: %s" % (path or "job", msg))


def _keys(obj: Dict, path: str, required: tuple, optional: tuple = ()) -> None:
    if not isinstance(obj, dict):
        _fail(path, "must be an object")
    missing = [k for k in required if k not in obj]
    if missing:
        _fail(path, "missing required key(s) %s" % ", ".join(missing))
    extra = sorted(set(obj) - set(required) - set(optional))
    if extra:
        _fail(path, "unknown key(s) %s" % ", ".join(extra))


def _number(v: Any, path: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        _fail(path, "must be a finite number")
    return float(v)


def _int(v: Any, path: str, lo: int, hi: int) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        _fail(path, "must be an integer %d-%d" % (lo, hi))
    return v


def _str(v: Any, path: str, max_len: int = 200) -> str:
    if not isinstance(v, str) or not v or len(v) > max_len:
        _fail(path, "must be a non-empty string (max %d chars)" % max_len)
    return v


def _param_name(v: Any, path: str) -> str:
    if not isinstance(v, str) or not PARAM_NAME_RE.match(v):
        _fail(path, "must be a Cab_* parameter name")
    return v


def validate_expect(exp: Any, path: str) -> None:
    _keys(exp, path, (), ("verdict", "pass_count", "total", "fail_ids", "params_mm", "tol_mm",
                          "counts", "design_spec_hash", "features_passed", "stable_counts"))
    if "verdict" in exp and exp["verdict"] not in ("PASS", "FAIL"):
        _fail(path + ".verdict", "must be PASS or FAIL")
    for k in ("pass_count", "total", "features_passed"):
        if k in exp:
            _int(exp[k], path + "." + k, 0, 10000)
    if "fail_ids" in exp:
        if not isinstance(exp["fail_ids"], list) or len(exp["fail_ids"]) > 50:
            _fail(path + ".fail_ids", "must be a list (max 50)")
        for i, c in enumerate(exp["fail_ids"]):
            if not isinstance(c, str) or not CHECK_ID_RE.match(c):
                _fail("%s.fail_ids[%d]" % (path, i), "must be a check id")
    if "params_mm" in exp:
        if not isinstance(exp["params_mm"], dict) or not exp["params_mm"] or len(exp["params_mm"]) > 60:
            _fail(path + ".params_mm", "must be a non-empty object")
        for k, val in exp["params_mm"].items():
            _param_name(k, path + ".params_mm key")
            _number(val, "%s.params_mm.%s" % (path, k))
    if "tol_mm" in exp:
        t = _number(exp["tol_mm"], path + ".tol_mm")
        if not 0 < t <= 1.0:
            _fail(path + ".tol_mm", "must be > 0 and <= 1.0")
    if "counts" in exp:
        _keys(exp["counts"], path + ".counts", (), ("user_parameters", "root_occurrences", "all_components", "timeline_items"))
        for k, val in exp["counts"].items():
            _int(val, "%s.counts.%s" % (path, k), 0, 100000)
    if "design_spec_hash" in exp and (not isinstance(exp["design_spec_hash"], str)
                                      or not re.fullmatch(r"[0-9a-f]{64}", exp["design_spec_hash"])):
        _fail(path + ".design_spec_hash", "must be a sha256 hex digest")
    if "stable_counts" in exp and not isinstance(exp["stable_counts"], bool):
        _fail(path + ".stable_counts", "must be a boolean")


MAX_REQUEST_BYTES = 262144


def _arrangement_request(req: Any, path: str) -> None:
    """Structural check only; the full plan is validated inside Fusion before any write."""
    if isinstance(req, dict) and 'fixture' in req:
        _keys(req, path, ('fixture',))
        if req['fixture'] != 'profile-panels/1':
            _fail(path, 'unknown profile fixture')
        return
    _keys(req, path, ("arrangement", "envelope", "edits"), ("tool_diameter_mm",))
    if not isinstance(req["arrangement"], dict) or not isinstance(req["envelope"], dict):
        _fail(path, "arrangement and envelope must be objects")
    if not isinstance(req["edits"], list) or len(req["edits"]) > 6:
        _fail(path + ".edits", "must be a list of at most 6 edits")
    if "tool_diameter_mm" in req:
        _number(req["tool_diameter_mm"], path + ".tool_diameter_mm")
    try:
        size = len(json.dumps(req, allow_nan=False))
    except (TypeError, ValueError):
        _fail(path, "must be finite JSON")
    if size > MAX_REQUEST_BYTES:
        _fail(path, "larger than %d bytes" % MAX_REQUEST_BYTES)


def validate_args(command: str, args: Any, path: str) -> None:
    if command == "ping":
        _keys(args, path, ())
    elif command in DEMO_COMMANDS:
        required = {"create_demo_design": (), "run_approved_demo": ("demo_id", "entry_point"),
                    "save_demo_design": ("demo_id", "name", "project_id", "folder_id"),
                    "close_demo_design": ("demo_id",), "capture_demo_viewport": ("demo_id",), "verify_demo_persistence": ("design_id",)}[command]
        if command=='run_approved_demo' and isinstance(args,dict) and args.get('entry_point')=='PhaseACombinedPersistence':
            required=('demo_id','entry_point','name','project_id','folder_id')
        if command=='run_approved_demo' and isinstance(args,dict) and args.get('entry_point')=='BuildArrangement':
            required=('demo_id','entry_point','request')
        _keys(args, path, required, ('layout_mm','vehicle_mm') if command=='run_approved_demo' and args.get('entry_point')=='FirstInteriorDemo' else ())
        for key in required:
            if key != 'request':
                _str(args[key], path + "." + key, 300)
        if 'request' in args:
            _arrangement_request(args['request'], path + '.request')
        if "demo_id" in args and not JOB_ID_RE.fullmatch(args["demo_id"]):
            _fail(path + ".demo_id", "must be the create job id")
        if command == "run_approved_demo" and args["entry_point"] not in ("FirstInteriorDemo", "BedCabinetComposition", "TestTransitEnvelope", "TestStorageBox", "DimensionedCutaway", "PhaseABaseCheckpoint", "PhaseACombinedPersistence", "LinedInteriorEnvelope", "RoundedPanel", "TabSlotCoupon", "BuildArrangement"):
            _fail(path + ".entry_point", "unapproved entry point")
        if args.get('entry_point') in ('BedCabinetComposition', 'TestTransitEnvelope', 'TestStorageBox', 'DimensionedCutaway', 'PhaseABaseCheckpoint', 'LinedInteriorEnvelope', 'RoundedPanel', 'TabSlotCoupon') and set(args) != {'demo_id', 'entry_point'}:
            _fail(path, 'composition uses fixed reviewed inputs')
        if 'layout_mm' in args:
            _keys(args['layout_mm'], path+'.layout_mm', (), ('Bed_Width', 'Bed_Length', 'Bed_Height', 'Kitchen_X', 'Kitchen_Y'))
            for key, value in args['layout_mm'].items():
                _number(value, path+'.layout_mm.'+key)
        if 'vehicle_mm' in args:
            _keys(args['vehicle_mm'], path+'.vehicle_mm', (), ('Van_Width','Van_Length','Van_Height',
                  'Arch_Width','Arch_Length','Arch_Height','Arch_Left_Y','Arch_Right_Y','Min_Aisle'))
            for key,value in args['vehicle_mm'].items():
                _number(value, path+'.vehicle_mm.'+key)
        if command == "save_demo_design":
            name = args["name"]
            if name != name.strip() or len(name) > 120 or any(ord(c) < 32 or c in '/\\:*?"<>|' for c in name):
                _fail(path + ".name", "invalid document name")
    elif command == "inspect_design":
        _keys(args, path, (), ("label",))
    elif command == "measure":
        _keys(args, path, (), ("expect", "label"))
    elif command == "audit_cuts":
        _keys(args, path, (), ("expect", "label"))
    elif command == "set_parameter":
        _keys(args, path, ("name", "value", "unit"), ("label",))
        _param_name(args["name"], path + ".name")
        v = _number(args["value"], path + ".value")
        if v <= 0:
            _fail(path + ".value", "must be > 0")
        if args["unit"] not in SUPPORTED_UNITS:
            _fail(path + ".unit", "unsupported unit %r (supported: %s)" % (args["unit"], ", ".join(SUPPORTED_UNITS)))
    elif command in ("preview_width_change", "update_width"):
        # G4: width change of an existing managed cabinet, driven by its stored spec
        _keys(args, path, ("new_width", "unit"), ("expect", "label"))
        if _number(args["new_width"], path + ".new_width") <= 0:
            _fail(path + ".new_width", "must be > 0")
        if args["unit"] not in SUPPORTED_UNITS:
            _fail(path + ".unit", "unsupported unit %r" % (args["unit"],))
    elif command in ("preview_shelf_count_change", "update_shelf_count"):
        _keys(args, path, ("new_shelf_count",), ("label",))
        _int(args["new_shelf_count"], path + ".new_shelf_count", 1, 2)
    elif command == "restore_parameter":
        _keys(args, path, ("name",), ("expect", "label"))
        _param_name(args["name"], path + ".name")
    elif command == BATCH_COMMAND:
        _keys(args, path, ("steps",), ("stable_counts", "label"))
        steps = args["steps"]
        if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
            _fail(path + ".steps", "must be a list of 1-%d steps" % MAX_STEPS)
        if "stable_counts" in args and not isinstance(args["stable_counts"], bool):
            _fail(path + ".stable_counts", "must be a boolean")
        for i, st in enumerate(steps):
            sp = "%s.steps[%d]" % (path, i)
            _keys(st, sp, ("command",), ("args",))
            if st["command"] not in STEP_COMMANDS:
                _fail(sp + ".command", "not allowed in a batch: %r" % (st["command"],))
            validate_args(st["command"], st.get("args", {}), sp + ".args")
    else:
        _fail("command", "unknown command %r" % (command,))
    if isinstance(args, dict):
        if "expect" in args:
            validate_expect(args["expect"], path + ".expect")
        if "label" in args:
            _str(args["label"], path + ".label", 120)


def validate_job(job: Any) -> Dict:
    """Validate a complete job document.  Returns it unchanged or raises JobSchemaError."""
    _keys(job, "job", ("schema", "job_id", "command", "args"), ("target", "timeout_s", "created_utc", "note"))
    if job["schema"] != JOB_SCHEMA_ID:
        _fail("schema", "must be %r" % JOB_SCHEMA_ID)
    if not isinstance(job["job_id"], str) or not JOB_ID_RE.match(job["job_id"]):
        _fail("job_id", "must match %s" % JOB_ID_RE.pattern)
    cmd = job["command"]
    if cmd not in ALL_COMMANDS:
        _fail("command", "unknown command %r" % (cmd,))
    validate_args(cmd, job["args"], "args")
    if "timeout_s" in job:
        _int(job["timeout_s"], "timeout_s", 5, MAX_TIMEOUT_S)
    for k in ("created_utc", "note"):
        if k in job:
            _str(job[k], k, 500)
    needs_target = cmd not in ("ping", "inspect_design") + DEMO_COMMANDS
    if cmd in DEMO_COMMANDS and "target" in job:
        _fail("target", "demo commands use runner-created session identity, not cloud targets")
    if "target" in job:
        _keys(job["target"], "target", ("design_id",), ("document_name",))
        _str(job["target"]["design_id"], "target.design_id", 300)
        if "document_name" in job["target"]:
            _str(job["target"]["document_name"], "target.document_name", 200)
    elif needs_target:
        _fail("target", "required for command %r (document identity check)" % cmd)
    return job


def is_mutating(job: Dict) -> bool:
    if job["command"] in MUTATING_COMMANDS:
        return True
    if job["command"] == BATCH_COMMAND:
        return any(s["command"] in MUTATING_COMMANDS for s in job["args"]["steps"])
    return False


def steps_of(job: Dict) -> List[Dict]:
    """Normalise a job into an ordered list of {command, args} steps."""
    if job["command"] == BATCH_COMMAND:
        return [{"command": s["command"], "args": s.get("args", {})} for s in job["args"]["steps"]]
    return [{"command": job["command"], "args": job["args"]}]
