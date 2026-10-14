"""Fusion-side orchestration used by the thin script entrypoint."""

from __future__ import annotations

import datetime
import json
import os

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


def _write_report(script_dir, app, spec, assembly, report, mode):
    folder = os.path.join(script_dir, "reports")
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(folder, "report_%s.json" % stamp)
    payload = {
        "generator": GENERATOR_ID, "schema_version": SCHEMA_VERSION, "mode": mode,
        "fusion_version": app.version, "assembly_id": assembly.assembly_id,
        "spec_hash": assembly.spec_hash, "spec": spec.to_dict(),
        "exported_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "validation": report.to_dict(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def run_cabinet(app, ui, script_dir: str) -> None:
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        ui.messageBox("Open a Fusion design first.")
        return
    adapter = FusionAdapter(design)  # raises if design history is off

    if adapter.has_managed_assembly():
        stored = adapter.stored_spec_json()
        if not stored:
            ui.messageBox("Managed components found but no stored spec; cannot re-measure safely.")
            return
        spec = CabinetSpec.from_json(stored)
        assembly = build_cabinet(spec)
        mode = "measure"
        header = "EXISTING CABINET - MEASUREMENT (nothing was rebuilt)"
    else:
        spec = _load_spec(script_dir)
        assembly = build_cabinet(spec)
        adapter.compile(assembly)
        adapter.store_spec_json(spec.to_json())
        mode = "build"
        header = "V5 cabinet created."

    report = validate(assembly, adapter.geometry_source())
    app.log(report.text())
    try:
        path = _write_report(script_dir, app, spec, assembly, report, mode)
        footer = "\n\nReport saved: " + path
    except OSError as e:
        footer = "\n\n(Could not save JSON report: %s)" % e
    tail = ""
    if mode == "build":
        tail = ("\n\nNow edit parameters in Modify > Change Parameters and run this script "
                "again in the same design to re-measure.")
    ui.messageBox(header + "\n\n" + report.text() + footer + tail)
