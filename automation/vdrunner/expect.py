"""Evaluate a step's ``expect`` block against the evidence it produced.

Command completion is never success: a step passes only when its own evidence
meets every stated expectation.  A measurement step with no ``expect`` block
still requires verdict PASS with zero FAIL/UNKNOWN.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

DEFAULT_TOL_MM = 1e-6


def evaluate_measure(summary: Dict, expect: Optional[Dict], baseline: Optional[Dict] = None) -> Tuple[bool, List[str]]:
    """summary = {verdict, counts{PASS,FAIL,UNKNOWN}, total, fail_ids, unknown_ids, params_mm,
    design_counts, design_spec_hash, stored_unchanged}."""
    exp = dict(expect or {})
    notes: List[str] = []
    ok = True

    def bad(msg):
        nonlocal ok
        ok = False
        notes.append("FAIL " + msg)

    want_verdict = exp.get("verdict", "PASS")
    if summary.get("verdict") != want_verdict:
        bad("verdict %s, expected %s" % (summary.get("verdict"), want_verdict))
    if summary.get("unknown_ids"):
        bad("UNKNOWN checks present: %s" % summary["unknown_ids"])
    want_fail = sorted(exp.get("fail_ids", []))
    if sorted(summary.get("fail_ids", [])) != want_fail:
        bad("FAIL ids %s, expected %s" % (sorted(summary.get("fail_ids", [])), want_fail))
    for k in ("pass_count", "total"):
        if k in exp:
            got = summary["counts"]["PASS"] if k == "pass_count" else summary.get("total")
            if got != exp[k]:
                bad("%s %s, expected %s" % (k, got, exp[k]))
    tol = exp.get("tol_mm", DEFAULT_TOL_MM)
    for name, val in (exp.get("params_mm") or {}).items():
        got = (summary.get("params_mm") or {}).get(name)
        if got is None or abs(got - val) > tol:
            bad("%s = %s, expected %s (tol %g)" % (name, got, val, tol))
    if "counts" in exp:
        for k, v in exp["counts"].items():
            if (summary.get("design_counts") or {}).get(k) != v:
                bad("design count %s = %s, expected %s" % (k, (summary.get("design_counts") or {}).get(k), v))
    if "design_spec_hash" in exp and summary.get("design_spec_hash") != exp["design_spec_hash"]:
        bad("design_spec_hash %s, expected %s" % (summary.get("design_spec_hash"), exp["design_spec_hash"]))
    if summary.get("stored_unchanged") is not True:
        bad("stored spec changed or unverifiable during measurement")
    if baseline is not None:
        if summary.get("design_counts") != baseline.get("design_counts"):
            bad("design counts %s differ from batch baseline %s" % (summary.get("design_counts"), baseline.get("design_counts")))
        if summary.get("design_spec_hash") != baseline.get("design_spec_hash"):
            bad("design_spec_hash differs from batch baseline")
    if ok:
        notes.append("OK all expectations met (%s %d/%d)" % (summary.get("verdict"), summary["counts"]["PASS"], summary.get("total", 0)))
    return ok, notes


def evaluate_audit(summary: Dict, expect: Optional[Dict]) -> Tuple[bool, List[str]]:
    """summary = {overall, features_passed, features_total, timeline_restored, counts_equal}."""
    exp = dict(expect or {})
    notes: List[str] = []
    ok = True

    def bad(msg):
        nonlocal ok
        ok = False
        notes.append("FAIL " + msg)

    if summary.get("overall") != "PASS":
        bad("audit overall %s" % summary.get("overall"))
    if summary.get("timeline_restored") is not True:
        bad("timeline marker NOT restored")
    if summary.get("counts_equal") is not True:
        bad("design counts changed during audit")
    if summary.get("features_passed") != summary.get("features_total"):
        bad("features passed %s/%s" % (summary.get("features_passed"), summary.get("features_total")))
    if "features_passed" in exp and summary.get("features_passed") != exp["features_passed"]:
        bad("features passed %s, expected %s" % (summary.get("features_passed"), exp["features_passed"]))
    if ok:
        notes.append("OK audit %s/%s, timeline restored, counts unchanged" % (summary.get("features_passed"), summary.get("features_total")))
    return ok, notes
