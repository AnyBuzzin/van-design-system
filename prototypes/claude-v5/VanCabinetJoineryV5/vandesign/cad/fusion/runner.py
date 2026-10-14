"""Fusion-side orchestration used by the thin script entrypoint."""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import traceback

import adsk.core
import adsk.fusion

from ... import GENERATOR_ID, SCHEMA_VERSION
from ...modules.variants import build_variant, profile_limits
from ...schemas.cabinet_spec import SpecError
from ...schemas.design_spec import MAX_SPEC_BYTES, default_design_spec, load_design_spec
from ...verification.validate import validate
from .adapter import FusionAdapter

SPEC_FILE = "cabinet_spec.json"


def _load_design_spec(script_dir: str):
    """Strictly load cabinet_spec.json beside the script, else the exact G2 default (schema 0.1)."""
    path = os.path.join(script_dir, SPEC_FILE)
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = f.read(MAX_SPEC_BYTES + 1)
        return load_design_spec(data)
    return default_design_spec()


def _raw_sha256(text):
    return None if text is None else hashlib.sha256(text.encode("utf-8")).hexdigest()


def _design_counts(design):
    """Read-only object counts, used to prove repeated measure runs create nothing."""
    counts = {}
    for key, getter in (
            ("user_parameters", lambda: design.userParameters.count),
            ("root_occurrences", lambda: design.rootComponent.occurrences.count),
            ("all_components", lambda: design.allComponents.count),
            ("timeline_items", lambda: design.timeline.count)):
        try:
            counts[key] = getter()
        except Exception:
            counts[key] = None
    return counts


def _fusion_parameters_mm(design):
    """Read actual live Fusion user parameters (lengths expressed in mm)."""
    values = {}
    params = design.userParameters
    for i in range(params.count):
        parameter = params.item(i)
        if parameter.name.startswith("Cab_"):
            values[parameter.name] = {
                "expression": parameter.expression,
                "value_mm": parameter.value * 10.0,  # Fusion stores length in cm.
            }
    return values


def _document_name(app):
    try:
        return app.activeDocument.name
    except Exception as exc:
        return 'unavailable (%s)' % exc


def _write_report(script_dir, app, design, spec, assembly, report, mode, design_spec=None, stored=None):
    folder = os.path.join(script_dir, "reports")
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    base = os.path.join(folder, "report_%s_%s" % (stamp, mode))
    document_name = _document_name(app)
    params = _fusion_parameters_mm(design)
    payload = {
        "generator": GENERATOR_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "fusion_version": app.version,
        "document_name": document_name,
        "parameters_read_from_fusion": params,
        "parameters_mm": {name: value["value_mm"] for name, value in params.items()},
        "assembly_id": assembly.assembly_id,
        "spec_hash": assembly.spec_hash,
        "spec": spec.to_dict(),
        "exported_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "validation": report.to_dict(),
    }
    if design_spec is not None:
        # Additive G3 fields.  Legacy meaning of schema_version/spec/spec_hash is unchanged:
        # they describe the legacy generator spec; the design_* fields describe the stored document.
        payload.update(design_spec.metadata())
        payload["design_spec_canonical_json"] = design_spec.canonical_stored_spec_json
        payload["profile_limits"] = {k: list(v) for k, v in profile_limits(design_spec.profile).items()}
        payload["design_counts"] = _design_counts(design)
        payload["stored_spec"] = dict(stored or {})
    report_lines = [
        "Document: %s" % document_name,
        "Fusion version: %s" % app.version,
        "Mode: %s" % mode,
    ]
    if design_spec is not None:
        report_lines.extend([
            "Variant: %s@%d" % (design_spec.variant, design_spec.profile_version),
            "Design schema: %s (migrated in memory: %s)" % (design_spec.original_schema, design_spec.migrated_in_memory),
            "Hash scheme: %s" % design_spec.hash_scheme,
            "design_spec_hash: %s" % design_spec.design_spec_hash,
            "assembly_legacy_spec_hash: %s" % design_spec.assembly_legacy_spec_hash,
            "Stored spec raw SHA-256 before: %s" % (stored or {}).get("raw_sha256_before"),
            "Stored spec raw SHA-256 after:  %s" % (stored or {}).get("raw_sha256_after"),
            "Stored spec unchanged: %s" % (stored or {}).get("unchanged"),
            "Design counts: %s" % json.dumps(payload.get("design_counts"), sort_keys=True),
        ])
    report_lines.extend([
        "",
        "Live Cab_* parameters read from Fusion:",
    ])
    for name in sorted(params):
        p = params[name]
        report_lines.append("  %s = %.4f mm [%s]" % (name, p["value_mm"], p["expression"]))
    report_lines.extend(["", report.text(), ""])
    txt_content = "\n".join(report_lines)
    json_path, txt_path = base + ".json", base + ".txt"
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    with open(txt_path, "w", encoding="utf-8") as handle:
        handle.write(txt_content)
    return json_path, txt_path


def run_cabinet(app, ui, script_dir: str) -> None:
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        ui.messageBox("Open a Fusion design first.")
        return
    adapter = FusionAdapter(design)  # raises if design history is off

    if adapter.has_managed_assembly():
        # MEASURE: read-only.  Nothing is stored, rewritten or rebuilt.
        stored = adapter.stored_spec_json()
        if not stored:
            ui.messageBox("Managed components found but no stored spec; cannot re-measure safely.\n"
                          "If an earlier build failed part-way, close this test design WITHOUT SAVING "
                          "and use a new empty design.")
            return
        try:
            design_spec = load_design_spec(stored)
        except SpecError as e:
            ui.messageBox("The spec stored in this design cannot be read; nothing was changed.\n\n%s" % e)
            return
        raw_before = _raw_sha256(stored)
        mode = "measure"
        header = "EXISTING CABINET - MEASUREMENT (nothing was rebuilt)"
        spec = design_spec.resolved_params
        assembly = build_variant(spec, design_spec.profile)
    else:
        try:
            design_spec = _load_design_spec(script_dir)  # strict; rejects BEFORE any CAD change
        except (SpecError, OSError) as e:
            ui.messageBox("The spec was rejected before anything was built:\n\n%s" % e)
            return
        spec = design_spec.resolved_params
        assembly = build_variant(spec, design_spec.profile)
        raw_before = None
        try:
            adapter.compile(assembly)
            adapter.store_spec_json(design_spec.canonical_stored_spec_json)
        except Exception:
            error = traceback.format_exc()
            app.log(error)
            ui.messageBox("Build failed part-way. Close this test design WITHOUT SAVING, "
                          "open a new empty design and run again. Send the error text:\n\n" + error)
            return
        mode = "build"
        header = "V5 cabinet created (%s@%d)." % (design_spec.variant, design_spec.profile_version)

    report = validate(assembly, adapter.geometry_source(),
                      profile_limits=profile_limits(design_spec.profile),
                      profile_variant=design_spec.variant)
    raw_after = _raw_sha256(adapter.stored_spec_json())
    stored_info = {
        "raw_sha256_before": raw_before,
        "raw_sha256_after": raw_after,
        "unchanged": (raw_before == raw_after) if mode == "measure" else None,
    }
    app.log(report.text())
    try:
        json_path, txt_path = _write_report(script_dir, app, design, spec, assembly, report, mode,
                                            design_spec=design_spec, stored=stored_info)
        footer = "\n\nReports saved:\n" + json_path + "\n" + txt_path
    except (OSError, ValueError, AttributeError) as e:
        footer = "\n\n(Report files unavailable: %s)" % e
    warning = ""
    if mode == "measure" and not stored_info["unchanged"]:
        warning = "\n\nWARNING: the stored spec attribute changed during measurement (it must not)."
    tail = ""
    if mode == "build":
        tail = ("\n\nNow edit parameters in Modify > Change Parameters and run this script "
                "again in the same design to re-measure.")
    ui.messageBox(header + "\n\n" + report.text() + warning + footer + tail)
