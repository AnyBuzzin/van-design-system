"""Deterministic nominal cabinet blanks; offline only, never a manufacturing BOM.

Run ``python -m vandesign.panel_preview spec.json NEW_DIRECTORY [--report FILE]``.
Report reuse checks historical consistency, not the current state of a live CAD file.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path

from . import GENERATOR_ID, __version__
from .modules.variants import build_variant
from .schemas.design_spec import load_design_spec

NOTICE = "ENGINEERING PREVIEW, NOT CERTIFIED CNC OUTPUT"
# blank axis 1, blank axis 2, thickness axis: cabinet coordinates, not grain.
ROLE_AXES = {"left": (1, 2, 0), "right": (1, 2, 0),
             "bottom": (0, 1, 2), "top": (0, 1, 2), "shelf": (0, 1, 2),
             "back": (0, 2, 1), "door": (0, 2, 1),
             "bed_deck": (0, 1, 2), "bed_support": (0, 2, 1)}
FIELDS = ("panel_id", "label", "role", "material_ref", "blank_axis_1",
          "blank_axis_2", "thickness_axis", "blank_1_mm", "blank_2_mm",
          "nominal_thickness_mm", "quantity", "notice")
PARAM_TOLERANCE_MM = 1e-6
BBOX_TOLERANCE_MM = 0.01


def canonical_json(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                      allow_nan=False) + "\n"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _dimension(value):
    if not _finite(value) or value <= 0:
        raise ValueError("blank dimensions must be finite and positive")
    # Fixed decimal strings give CSV/JSON exact parity, independent of float repr.
    text = format(value, ".6f")
    if float(text) <= 0:
        raise ValueError("dimension below preview precision")
    return text


def panel_rows(assembly):
    """Resolve existing panel boxes; refuse unknown roles instead of guessing axes."""
    assembly.validate_structure()
    env = assembly.parameters.resolve()
    if any(not ok for _, ok, _, _ in assembly.check_constraints(env)):
        raise ValueError("assembly constraints failed")
    rows = []
    for panel in sorted(assembly.panels, key=lambda p: p.stable_id):
        if panel.role not in ROLE_AXES:
            raise ValueError("unsupported panel role: " + panel.role)
        a, b, t = ROLE_AXES[panel.role]
        size = panel.box.resolve(env).size
        rows.append(dict(zip(FIELDS, (
            panel.stable_id, panel.display_name, panel.role, panel.material_ref,
            "XYZ"[a], "XYZ"[b], "XYZ"[t], _dimension(size[a]), _dimension(size[b]),
            _dimension(size[t]), 1, NOTICE))))
    return rows


def csv_text(preview):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(preview["panels"])
    return stream.getvalue()


def compare_report(design, assembly, report):
    """Conservative consistency check of the existing Fusion report format.

    FAIL means incompatible evidence, not necessarily defective CAD. An old stored
    spec hash does not identify a scalar-edited model: compare the actual snapshot.
    No cut-ownership or saved-document claims are inferred from a geometry report.
    """
    failures, unknowns = [], []
    result = {"status": "UNKNOWN", "failures": failures, "unknowns": unknowns,
              "scope": "historical report consistency only; not current Fusion state",
              "parameter_tolerance_mm": PARAM_TOLERANCE_MM,
              "bbox_tolerance_mm": BBOX_TOLERANCE_MM,
              "cut_ownership": "UNKNOWN", "saved_document": "UNKNOWN",
              "stored_spec_parameter_divergence": "UNKNOWN"}
    if report is None:
        unknowns.append("no measured report supplied")
        return result
    if not isinstance(report, dict):
        raise ValueError("report must be an object")
    identities = {"generator": GENERATOR_ID, "assembly_id": assembly.assembly_id,
                  "spec_hash": assembly.spec_hash, "design_spec_hash": design.design_spec_hash,
                  "hash_scheme": design.hash_scheme}
    for key, expected in identities.items():
        if key not in report:
            unknowns.append("missing " + key)
        elif report[key] != expected:
            failures.append("mismatched " + key)
    stored_text = report.get("design_spec_canonical_json")
    if stored_text is None:
        unknowns.append("missing stored specification")
    else:
        try:
            stored = load_design_spec(stored_text)
            if stored.design_spec_hash != design.design_spec_hash:
                failures.append("stored specification differs")
        except (ValueError, TypeError):
            failures.append("invalid stored specification")
    snapshot = report.get("parameters_read_from_fusion")
    expected_params = assembly.parameters.resolve()
    divergence = []
    if not isinstance(snapshot, dict):
        unknowns.append("missing actual parameter expressions and values")
    else:
        if set(snapshot) != set(expected_params):
            failures.append("parameter name set differs")
        for name, expected in expected_params.items():
            item = snapshot.get(name, {})
            if not isinstance(item, dict):
                failures.append("invalid parameter " + name)
                continue
            actual = item.get("value_mm")
            if not _finite(actual):
                unknowns.append("missing/nonfinite measured parameter " + name)
            elif abs(actual - expected) > PARAM_TOLERANCE_MM:
                divergence.append(name)
            if not isinstance(item.get("expression"), str) or not item["expression"].strip():
                unknowns.append("missing expression " + name)
        if divergence:
            failures.append("stored specification/actual parameter divergence: " + ", ".join(divergence))
        result["stored_spec_parameter_divergence"] = divergence
    validation = report.get("validation", {})
    checks = validation.get("checks", []) if isinstance(validation, dict) else []
    if not checks:
        unknowns.append("no validation checks")
    else:
        if any(not isinstance(c, dict) for c in checks):
            raise ValueError("invalid validation checks")
        if any(c.get("status") == "FAIL" for c in checks) or validation.get("verdict") == "FAIL":
            failures.append("original validation failed")
        if validation.get("verdict") != "PASS" or any(c.get("status") != "PASS" for c in checks):
            unknowns.append("validation is not entirely PASS")
        by_id = {c.get("check_id"): c for c in checks}
        if len(by_id) != len(checks):
            failures.append("duplicate validation check IDs")
        counts = {s: sum(c.get("status") == s for c in checks) for s in ("PASS", "FAIL", "UNKNOWN")}
        if validation.get("counts") != counts:
            failures.append("validation counts inconsistent")
        required = {"constraint." + c.constraint_id for c in assembly.constraints}
        required.update("param." + p.name for p in assembly.parameters.derived())
        required.update(p.stable_id + suffix for p in assembly.panels for suffix in (".bbox", ".volume"))
        required.update(o.operation_id + suffix for o in assembly.operations for suffix in (
            ".penetration", ".end_gap", ".gap_below", ".gap_above", ".mating_unmodified",
            ".probe.centre_empty", ".probe.front_open", ".probe.below_solid",
            ".probe.above_solid", ".probe.far_wall_solid", ".probe.rear_wall_solid"))
        required.update(("interference.joined", "entities.managed_ids"))
        if required - set(by_id):
            unknowns.append("missing validation checks: " + ", ".join(sorted(required - set(by_id))))
        # Existing Check semantics: equality within tolerance for measurements,
        # strict/non-strict inequalities for constraints. Probes are status-only.
        numeric = {"param." + p.name: ("mm", []) for p in assembly.parameters.derived()}
        numeric.update({p.stable_id + suffix: (unit, [p.stable_id])
                        for p in assembly.panels for suffix, unit in ((".bbox", "mm"), (".volume", "mm3"))})
        for operation in assembly.operations:
            for suffix in ("penetration", "end_gap", "gap_below", "gap_above", "mating_unmodified"):
                numeric[operation.operation_id + "." + suffix] = (
                    "mm3" if suffix == "mating_unmodified" else "mm",
                    [operation.target_panel_id, operation.mating_panel_id])
        joined = sorted({o.target_panel_id for o in assembly.operations} |
                        {o.mating_panel_id for o in assembly.operations})
        numeric.update({"interference.joined": ("pairs", joined), "entities.managed_ids": ("entities", [])})
        constraints = {"constraint." + c.constraint_id: c for c in assembly.constraints}
        numeric.update({cid: ("mm", []) for cid in constraints})
        for cid, (unit, ids) in numeric.items():
            if cid not in by_id:
                continue  # Missing required records are already UNKNOWN above.
            check = by_id[cid]
            if check.get("unit") != unit or check.get("object_ids") != ids:
                failures.append("numeric record unit/identity incompatible " + cid)
            observed, expected, tolerance = (check.get(k) for k in ("observed", "expected", "tolerance"))
            if not _finite(observed) or not _finite(expected):
                unknowns.append("missing/nonfinite numeric observation/expectation " + cid)
                continue
            if cid in constraints:
                if tolerance is not None:
                    failures.append("constraint tolerance incompatible " + cid)
                consistent = observed > expected if constraints[cid].op == ">" else observed >= expected
            else:
                if not _finite(tolerance):
                    unknowns.append("missing/nonfinite numeric tolerance " + cid)
                    continue
                if tolerance < 0:
                    failures.append("negative numeric tolerance " + cid)
                    continue
                consistent = abs(observed - expected) <= tolerance
            if not consistent:
                failures.append("numeric observation contradicts expectation " + cid)
        expected_ids = {p.stable_id for p in assembly.panels}
        actual_ids = {c.get("check_id", "")[:-5] for c in checks
                      if c.get("check_id", "").endswith(".bbox")}
        if actual_ids != expected_ids:
            failures.append("measured panel IDs differ")
        for pid in sorted(expected_ids):
            check = by_id.get(pid + ".bbox", {})
            value = check.get("observed")
            if not _finite(value):
                unknowns.append("missing bbox observation " + pid)
            elif (check.get("unit") != "mm" or check.get("expected") != 0 or
                  check.get("object_ids") != [pid] or value < 0 or value > BBOX_TOLERANCE_MM):
                failures.append("bbox observation incompatible " + pid)
    result["status"] = "FAIL" if failures else "UNKNOWN" if unknowns else "PASS"
    result["reported_document_name"] = report.get("document_name")
    result["reported_fusion_version"] = report.get("fusion_version")
    result["actual_parameter_snapshot"] = snapshot
    result["reported_counts"] = report.get("design_counts")
    return result


def _bed_preview(spec_text, report_bytes):
    from .schemas.bed_platform_spec import load_bed_spec, MODULE, SCHEMA, NOTICE as BED_NOTICE
    from .modules.bed_platform import build_bed_platform
    spec = load_bed_spec(spec_text)
    assembly = build_bed_platform(spec)
    if report_bytes is not None:
        raise ValueError("Bed measured-report integration is not qualified in V6.1; omit --report")
    return {
        "format": "vandesign.panel-preview/1", "notice": NOTICE, "unit": "mm",
        "qualification": BED_NOTICE,
        "dimension_semantics": "nominal rectangular blanks; no grain or measured stock claim",
        "generator": "vandesign.bed-platform@1", "package_version": __version__,
        "specification": {"module": MODULE, "design_schema_version": SCHEMA,
                          "canonical_json": spec.to_json(), "design_spec_hash": spec.spec_hash(),
                          "hash_scheme": "bed-platform-1-canonical-sha256"},
        "resolved_nominal_parameters_mm": assembly.parameters.resolve(),
        "panels": panel_rows(assembly), "grooves": [],
        "evidence": {"status": "UNKNOWN", "scope": "specification-only; no live bed qualification",
                     "report_sha256": None, "failures": [],
                     "unknowns": ["no qualified bed measurement report"],
                     "cut_ownership": "UNKNOWN", "saved_document": "UNKNOWN"},
    }


def make_preview(spec_text, report_bytes=None):
    # Dispatch only the explicit new module; cabinet loading/hashes stay unchanged.
    raw = json.loads(spec_text)
    if isinstance(raw, dict) and raw.get("module") == "bed-platform@1":
        return _bed_preview(spec_text, report_bytes)
    design = load_design_spec(spec_text)
    assembly = build_variant(design.resolved_params, design.profile)
    report = json.loads(report_bytes) if report_bytes is not None else None
    return {
        "format": "vandesign.panel-preview/1", "notice": NOTICE, "unit": "mm",
        "dimension_semantics": "nominal rectangular blanks; grooves listed separately; no grain or measured stock claim",
        "generator": GENERATOR_ID, "package_version": __version__,
        "specification": {**design.metadata(), "canonical_json": design.canonical_stored_spec_json},
        "resolved_nominal_parameters_mm": assembly.parameters.resolve(),
        "panels": panel_rows(assembly),
        "grooves": [{"operation_id": o.operation_id, "target_panel_id": o.target_panel_id,
                     "mating_panel_id": o.mating_panel_id} for o in sorted(assembly.operations, key=lambda o: o.operation_id)],
        "evidence": {"report_sha256": sha256(report_bytes) if report_bytes is not None else None,
                     **compare_report(design, assembly, report)},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("output", type=Path, help="new directory; existing output refused")
    parser.add_argument("--report", type=Path, help="existing Fusion measure/build report")
    args = parser.parse_args()
    preview = make_preview(args.spec.read_bytes(), args.report.read_bytes() if args.report else None)
    # Validate and serialize before creating any output. No overwrite or CAD access.
    encoded, csv_output = canonical_json(preview), csv_text(preview)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "panels.json").write_text(encoded, encoding="utf-8", newline="\n")
    (args.output / "panels.csv").write_text(csv_output, encoding="utf-8", newline="\n")
    print(NOTICE + "; historical evidence " + preview["evidence"]["status"])
    return 1 if preview["evidence"]["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
