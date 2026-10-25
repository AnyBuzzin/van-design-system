"""Runner configuration and safety policy (pure logic, unit-tested).

The configuration lives beside the installed add-in (``config.json``).  It names
the verified G3 generator and audit to reuse, the queue root, the protected
designs and the ONLY designs that mutating commands may touch.  Design identity
is the Fusion cloud ``DataFile.id`` (lineage id), never the document title.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional

DEFAULT_PARAMETER_BOUNDS_MM = {
    "Cab_Dado_Depth": [1.0, 20.0],
    "Cab_Ply": [6.0, 40.0],
    "Cab_Width": [200.0, 2500.0],
    "Cab_Height": [150.0, 2600.0],
    "Cab_Depth": [150.0, 900.0],
}
_REQUIRED = ("queue_root", "g3_script_dir", "audit_script")


class PolicyError(RuntimeError):
    """A job is not permitted by the runner safety policy."""


def load_config(path: str) -> Dict:
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    missing = [k for k in _REQUIRED if not cfg.get(k)]
    if missing:
        raise PolicyError("config %s missing %s" % (path, ", ".join(missing)))
    cfg.setdefault("allowed_design_ids", [])
    cfg.setdefault("protected_design_ids", [])
    cfg.setdefault("parameter_bounds_mm", DEFAULT_PARAMETER_BOUNDS_MM)
    for item in cfg["allowed_design_ids"]:
        if not isinstance(item, dict) or not item.get("design_id"):
            raise PolicyError("allowed_design_ids entries must be objects with design_id")
    return cfg


def check_target(cfg: Dict, job_target: Optional[Dict], active: Dict, mutating: bool) -> None:
    """Raise PolicyError unless the active document is the job's target and the job may run on it.

    active = {"design_id": str|None, "document_name": str, "is_saved": bool}
    """
    if job_target is None:
        return
    did = active.get("design_id")
    if not did:
        raise PolicyError("active document has no cloud identity (never saved); cannot verify target")
    if did != job_target["design_id"]:
        raise PolicyError("active design %r (%s) is not the job target %r" % (did, active.get("document_name"), job_target["design_id"]))
    want_name = job_target.get("document_name")
    if want_name and want_name != active.get("document_name"):
        raise PolicyError("document name %r does not match job target name %r" % (active.get("document_name"), want_name))
    protected = {p if isinstance(p, str) else p.get("design_id") for p in cfg.get("protected_design_ids", [])}
    if mutating:
        if did in protected:
            raise PolicyError("design %r is PROTECTED; mutating commands are refused" % did)
        allowed = {a["design_id"] for a in cfg.get("allowed_design_ids", [])}
        if did not in allowed:
            raise PolicyError("design %r is not on the disposable test-design allowlist" % did)


def check_parameter_edit(cfg: Dict, name: str, value_mm: float, current_expression: str) -> str:
    """Validate an edit.  Returns the new expression string (always explicit mm)."""
    bounds = cfg.get("parameter_bounds_mm", DEFAULT_PARAMETER_BOUNDS_MM)
    if name not in bounds:
        raise PolicyError("parameter %s is not editable (allowed: %s)" % (name, ", ".join(sorted(bounds))))
    lo, hi = bounds[name]
    if not lo <= value_mm <= hi:
        raise PolicyError("%s = %g mm outside allowed edit bounds %g-%g mm" % (name, value_mm, lo, hi))
    if not is_plain_mm_expression(current_expression):
        raise PolicyError("%s expression %r is a formula, not a plain mm value; refusing to overwrite it" % (name, current_expression))
    return format_mm(value_mm)


def format_mm(value_mm: float) -> str:
    return ("%.6f" % value_mm).rstrip("0").rstrip(".") + " mm"


def is_plain_mm_expression(expr: str) -> bool:
    parts = (expr or "").strip().split()
    if len(parts) != 2 or parts[1] != "mm":
        return False
    try:
        float(parts[0])
    except ValueError:
        return False
    return True


def default_queue_root() -> str:
    return os.path.join(os.path.expanduser("~"), "Documents", "VanDesign-Runner", "queue")
