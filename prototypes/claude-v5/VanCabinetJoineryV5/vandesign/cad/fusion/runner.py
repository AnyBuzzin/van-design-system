"""Fusion-side orchestration used by the thin script entrypoint."""

from __future__ import annotations

import datetime
import json
import os
import traceback

import adsk.core
import adsk.fusion

from ... import GENERATOR_ID, SCHEMA_VERSION
from ...modules.cabinet import build_cabinet
from ...schemas.cabinet_spec import CabinetSpec
from ...verification.validate import validate
from .adapter import FusionAdapter

SPEC_FILE = "cabinet_spec.json"


def _load_spec(script_dir: str) -> CabinetSpec:
    path = os.path.join(script_dir, SPEC_FILE)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return CabinetSpec.from_json(f.read())
    return CabinetSpec()


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


def _write_report(script_dir, app, design, spec, assembly, report, mode):
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
    report_lines = [
        "Document: %s" % document_name,
        "Fusion version: %s" % app.version,
        "Mode: %s" % mode,
        "",
        "Live Cab_* parameters read from Fusion:",
    ]
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
        stored = adapter.stored_spec_json()
        if not stored:
            ui.messageBox("Managed components found but no stored spec; cannot re-measure safely.\n"
                          "If an earlier build failed part-way, close this test design WITHOUT SAVING "
                          "and use a new empty design.")
            return
        spec = CabinetSpec.from_json(stored)
        assembly = build_cabinet(spec)
        mode = "measure"
        header = "EXISTING CABINET - MEASUREMENT (nothing was rebuilt)"
    else:
        spec = _load_spec(script_dir)
        assembly = build_cabinet(spec)
        try:
            adapter.compile(assembly)
            adapter.store_spec_json(spec.to_json())
        except Exception:
            error = traceback.format_exc()
            app.log(error)
            ui.messageBox("Build failed part-way. Close this test design WITHOUT SAVING, "
                          "open a new empty design and run again. Send the error text:\n\n" + error)
            return
        mode = "build"
        header = "V5 cabinet created."

    report = validate(assembly, adapter.geometry_source())
    app.log(report.text())
    try:
        json_path, txt_path = _write_report(script_dir, app, design, spec, assembly, report, mode)
        footer = "\n\nReports saved:\n" + json_path + "\n" + txt_path
    except (OSError, ValueError, AttributeError) as e:
        footer = "\n\n(Report files unavailable: %s)" % e
    tail = ""
    if mode == "build":
        tail = ("\n\nNow edit parameters in Modify > Change Parameters and run this script "
                "again in the same design to re-measure.")
    ui.messageBox(header + "\n\n" + report.text() + footer + tail)
