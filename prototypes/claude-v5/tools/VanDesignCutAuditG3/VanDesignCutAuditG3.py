"""VanDesign G3 - read-only cut participant audit for ALL dado.* features.

NEW SCRIPT.  It is NOT derived from the original G2 "VanDesignCutAudit" script
(that source was never committed to the repository); it reproduces that audit's
documented behaviour and output style and extends it to every dado feature.
It has not been run in Fusion by its author: treat its first run as part of the
G3 test, and compare it with the G2 evidence file (cut_audit_20261014_174320_047406.txt).

What it does (nothing is created, deleted or edited):
  * reads the spec stored in the design and derives the INTENDED dado list:
    dado.shelf<k>.left -> panel.left.001, dado.shelf<k>.right -> panel.right.001
  * finds every extrude feature named dado.* (must match the intended list exactly)
  * for each: owner component stable id, operation is Cut, and the
    participantBodies list has EXACTLY ONE body, owned by the intended side panel
    (never a shelf)
  * temporarily rolls the timeline marker before each feature (required by the
    participantBodies property) and RESTORES the original marker in `finally`.
    If restoring fails the overall result is FAIL and the user is warned.
Any missing/duplicate feature, ambiguous participants or failed API call is
FAIL or UNKNOWN, never PASS.
"""

import datetime
import json
import os
import re
import traceback

ATTR_GROUP = "VanDesign"
ATTR_ID = "stable_id"
ATTR_SPEC = "spec_json"
PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"
_DADO_RE = re.compile(r"^dado\.shelf(\d+)\.(left|right)$")


# ----------------------------------------------------------------- pure logic
def expected_operations(stored_spec_text):
    """{operation_id: expected target stable id} from the stored spec (schema 0.1 or 0.2)."""
    doc = json.loads(stored_spec_text)
    n = doc["parameters"]["shelf_count"]
    if isinstance(n, bool) or not isinstance(n, int) or not 0 <= n <= 4:
        raise ValueError("stored shelf_count invalid: %r" % (n,))
    ops = {}
    for k in range(1, n + 1):
        ops["dado.shelf%d.left" % k] = "panel.left.001"
        ops["dado.shelf%d.right" % k] = "panel.right.001"
    return ops


def judge(expected, observed, extra_names):
    """Pure verdicts.

    expected: {op_id: target_id}
    observed: {op_id: [obs, ...]} where obs is
        {"owner_id": str|None, "is_cut": bool, "participants": [ {"stable_id","name"} ] | None,
         "error": str|None}
    extra_names: dado.* feature names present but not expected.
    """
    results = []
    for op_id in sorted(expected):
        target = expected[op_id]
        obs = observed.get(op_id, [])
        lines, status = [], PASS
        if len(obs) == 0:
            status, lines = FAIL, ["feature not found"]
        elif len(obs) > 1:
            status, lines = FAIL, ["%d features carry this name (need exactly 1)" % len(obs)]
        else:
            o = obs[0]
            if o.get("error"):
                status, lines = UNKNOWN, ["could not inspect: %s" % o["error"]]
            else:
                lines.append("Feature owner stable id: %s (expected %s)" % (o["owner_id"], target))
                lines.append("Operation Cut: %s" % o["is_cut"])
                parts = o["participants"]
                lines.append("Participant count: %s" % ("unavailable" if parts is None else len(parts)))
                for p in parts or []:
                    lines.append("  Body: %r; stable id: %r" % (p.get("name"), p.get("stable_id")))
                if parts is None:
                    status = UNKNOWN
                else:
                    if o["owner_id"] != target:
                        status = FAIL
                    if not o["is_cut"]:
                        status = FAIL
                    if len(parts) != 1 or parts[0].get("stable_id") != target:
                        status = FAIL
                    if any(str(p.get("stable_id") or "").startswith("panel.shelf") for p in parts):
                        status = FAIL
        results.append({"operation_id": op_id, "expected_target": target, "status": status, "details": lines})
    for name in sorted(extra_names):
        results.append({"operation_id": name, "expected_target": None, "status": FAIL,
                        "details": ["unexpected dado feature not in the stored spec"]})
    return results


def overall(results, timeline_restored, expected_count):
    if not timeline_restored:
        return FAIL
    if expected_count == 0 and not results:
        return UNKNOWN  # nothing was audited: not a pass
    sts = [r["status"] for r in results]
    if FAIL in sts:
        return FAIL
    if UNKNOWN in sts:
        return UNKNOWN
    return PASS


# ----------------------------------------------------------- Fusion read-back
def _stable_id(component):
    attr = component.attributes.itemByName(ATTR_GROUP, ATTR_ID)
    return attr.value if attr else None


def _all_components(design):
    comps = [design.rootComponent]
    for i in range(design.rootComponent.occurrences.count):
        comps.append(design.rootComponent.occurrences.item(i).component)
    return comps


def collect(design, cut_operation, expected):
    """Read-only. Returns (observed, extra_names).  Moves/restores the timeline marker."""
    observed, extra = {}, []
    seen_components = set()
    for comp in _all_components(design):
        key = comp.entityToken if hasattr(comp, "entityToken") else id(comp)
        if key in seen_components:
            continue
        seen_components.add(key)
        feats = comp.features.extrudeFeatures
        for i in range(feats.count):
            f = feats.item(i)
            if not _DADO_RE.match(f.name):
                continue
            if f.name not in expected:
                extra.append(f.name)
                continue
            obs = {"owner_id": None, "is_cut": None, "participants": None, "error": None}
            try:
                obs["owner_id"] = _stable_id(f.parentComponent)
                obs["is_cut"] = (f.operation == cut_operation)
                f.timelineObject.rollTo(True)  # marker to immediately BEFORE the feature
                bodies = f.participantBodies
                parts = []
                for b in (bodies or []):
                    parts.append({"name": b.name, "stable_id": _stable_id(b.parentComponent)})
                obs["participants"] = parts
            except Exception as e:  # recorded; becomes UNKNOWN
                obs["error"] = "%s: %s" % (type(e).__name__, e)
            observed.setdefault(f.name, []).append(obs)
    return observed, extra


def run_audit(design, cut_operation):
    """Full audit.  Returns dict with results, timeline info, overall."""
    root = design.rootComponent
    stored_attr = root.attributes.itemByName(ATTR_GROUP, ATTR_SPEC)
    if not stored_attr:
        return {"overall": UNKNOWN, "error": "no stored spec in this design", "results": [],
                "timeline_restored": True, "counts_before": None, "counts_after": None}
    expected = expected_operations(stored_attr.value)
    tl = design.timeline
    start_marker, start_count = tl.markerPosition, tl.count
    counts_before = _counts(design)
    restored, restore_error = False, None
    observed, extra, collect_error = {}, [], None
    try:
        observed, extra = collect(design, cut_operation, expected)
    except Exception:
        collect_error = traceback.format_exc()
    finally:
        try:
            tl.markerPosition = start_marker
            restored = (tl.markerPosition == start_marker)
            if start_marker == start_count:
                tl.moveToEnd()
                restored = (tl.markerPosition == start_count)
        except Exception as e:
            restore_error = "%s: %s" % (type(e).__name__, e)
            restored = False
    results = judge(expected, observed, extra)
    counts_after = _counts(design)
    ov = overall(results, restored, len(expected))
    if collect_error and ov == PASS:
        ov = UNKNOWN
    if counts_before != counts_after:
        ov = FAIL
    return {"overall": ov, "results": results, "timeline_restored": restored,
            "restore_error": restore_error, "collect_error": collect_error,
            "start_marker": start_marker, "start_count": start_count,
            "counts_before": counts_before, "counts_after": counts_after,
            "expected_operations": expected}


def _counts(design):
    out = {}
    for key, getter in (("timeline_items", lambda: design.timeline.count),
                        ("user_parameters", lambda: design.userParameters.count),
                        ("root_occurrences", lambda: design.rootComponent.occurrences.count)):
        try:
            out[key] = getter()
        except Exception:
            out[key] = None
    return out


def render_text(doc_name, audit):
    lines = ["VanDesign G3 cut participant audit", "Document: %s" % doc_name,
             "Read-only: no geometry, parameters or features changed",
             "NOTE: The history marker is temporarily repositioned during inspection.", ""]
    for r in audit["results"]:
        lines.append("--- %s ---" % r["operation_id"])
        lines.extend(r["details"])
        lines.append("RESULT: %s" % r["status"])
        lines.append("")
    if audit.get("error"):
        lines.append("ERROR: %s" % audit["error"])
    if audit.get("collect_error"):
        lines.append("COLLECT ERROR:\n%s" % audit["collect_error"])
    lines.append("Timeline moved back to original position: %s" % audit["timeline_restored"])
    if audit.get("restore_error"):
        lines.append("RESTORE ERROR: %s  -- DO NOT EDIT THIS DESIGN; close WITHOUT saving and reopen." % audit["restore_error"])
    lines.append("Counts before: %s" % json.dumps(audit["counts_before"], sort_keys=True))
    lines.append("Counts after:  %s" % json.dumps(audit["counts_after"], sort_keys=True))
    n = len(audit["results"])
    p = len([r for r in audit["results"] if r["status"] == PASS])
    lines.append("Features passed: %d/%d" % (p, n))
    lines.append("")
    lines.append("OVERALL: %s" % audit["overall"])
    return "\n".join(lines)


# ------------------------------------------------------------------ entry point
def run(context):
    import adsk.core
    import adsk.fusion
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox("Open a Fusion design first.")
            return
        audit = run_audit(design, adsk.fusion.FeatureOperations.CutFeatureOperation)
        try:
            doc_name = app.activeDocument.name
        except Exception:
            doc_name = "unavailable"
        text = render_text(doc_name, audit)
        folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
        os.makedirs(folder, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        base = os.path.join(folder, "cut_audit_g3_%s" % stamp)
        with open(base + ".txt", "w", encoding="utf-8") as fh:
            fh.write(text)
        with open(base + ".json", "w", encoding="utf-8") as fh:
            json.dump({"document_name": doc_name, "fusion_version": app.version, **audit}, fh, indent=2)
        ui.messageBox(text + "\n\nSaved:\n" + base + ".txt\n" + base + ".json")
    except Exception:
        ui.messageBox("Audit failed:\n" + traceback.format_exc())
