"""Deterministic snapshots of the verified G2 generator (used by C0 golden tests).

The golden fixtures are produced ONCE from the pre-G3 pinned source by
``tools/capture_g2_golden.py`` and are never regenerated to make a failing test
pass.  This module only *describes* what the current code produces; it contains
no geometry formulas of its own.
"""

import ast
import hashlib
import os

from core_path import HISTORICAL_SCRIPT_DIR, ROOT
import vandesign
from sim_geometry import SimGeometry

from vandesign.modules.cabinet import build_cabinet
from vandesign.schemas.cabinet_spec import CabinetSpec
from vandesign.verification.validate import validate

PKG = os.path.dirname(vandesign.__file__)

# Sources that must stay byte-identical (CRLF normalised to LF before hashing).
PROTECTED_FILES = [
    "VanCabinetJoineryV5.py",
    "VanCabinetJoineryV5.manifest",
    "vandesign/__init__.py",
    "vandesign/modules/cabinet.py",
    "vandesign/schemas/cabinet_spec.py",
    "vandesign/components/model.py",
    "vandesign/components/ids.py",
    "vandesign/core/__init__.py",
    "vandesign/core/expr.py",
    "vandesign/core/frames.py",
    "vandesign/core/geometry.py",
    "vandesign/core/params.py",
    "vandesign/core/units.py",
    "vandesign/cad/protocol.py",
]
PROTECTED_BASELINE_DIR = os.path.join(ROOT, "baseline")

# Fusion adapter geometry-creation methods that must stay byte-identical.
PROTECTED_ADAPTER_METHODS = [
    "compile", "_eval_cm", "_rectangle_profile", "_extrude", "_make_panel", "_make_dado",
]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def protected_manifest() -> dict:
    files = {}
    for rel in PROTECTED_FILES:
        with open(os.path.join(HISTORICAL_SCRIPT_DIR, rel), "rb") as fh:
            files[rel] = _sha(fh.read())
    baseline = {}
    for dirpath, dirnames, filenames in os.walk(PROTECTED_BASELINE_DIR):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for fname in sorted(filenames):
            if fname.endswith((".pyc", ".pyo")):
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, PROTECTED_BASELINE_DIR).replace(os.sep, "/")
            with open(full, "rb") as fh:
                baseline[rel] = _sha(fh.read())
    # Frozen source hashes protect the preserved adapter, not the evolving wheel.
    with open(os.path.join(HISTORICAL_SCRIPT_DIR, "vandesign", "cad", "fusion", "adapter.py"), "r", encoding="utf-8", newline="") as fh:
        src = fh.read().replace("\r\n", "\n")
    tree = ast.parse(src)
    methods = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "FusionAdapter":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in PROTECTED_ADAPTER_METHODS:
                    methods[item.name] = _sha(ast.get_source_segment(src, item).encode("utf-8"))
    return {"files": files, "baseline_files": baseline, "adapter_methods": methods}


def _boxexpr(b):
    return {"origin": [e.render() for e in b.origin], "size": [e.render() for e in b.size]}


def assembly_snapshot(asm) -> dict:
    return {
        "assembly_id": asm.assembly_id,
        "spec_hash": asm.spec_hash,
        "parameters": [
            {"name": p.name, "base": p.is_base,
             "value_mm": p.value_mm, "expr": p.expr.render() if p.expr is not None else None,
             "comment": p.comment}
            for p in asm.parameters.params],
        "panels": [
            {"id": p.stable_id, "display_name": p.display_name, "role": p.role,
             "material_ref": p.material_ref, "box": _boxexpr(p.box)}
            for p in asm.panels],
        "operations": [
            {"id": o.operation_id, "target": o.target_panel_id, "mating": o.mating_panel_id,
             "side": o.side, "cut": _boxexpr(o.cut), "groove_depth": o.groove_depth.render(),
             "end_clearance": o.end_clearance.render(), "slot_clearance": o.slot_clearance.render(),
             "open_at": o.open_at, "process": o.process}
            for o in asm.operations],
        "constraints": [
            {"id": c.constraint_id, "description": c.description,
             "lhs": c.lhs.render(), "op": c.op, "rhs": c.rhs.render()}
            for c in asm.constraints],
    }


def combo_snapshot(shelves: int, doors: int) -> dict:
    spec = CabinetSpec(shelf_count=shelves, door_count=doors)
    asm = build_cabinet(spec)
    rep = validate(asm, SimGeometry(asm))
    snap = assembly_snapshot(asm)
    snap["legacy_spec_json"] = spec.to_json()
    snap["legacy_spec_hash"] = spec.spec_hash()
    snap["sim_check_ids"] = [c.check_id for c in rep.checks]
    snap["sim_check_statuses"] = [c.status for c in rep.checks]
    return snap


def all_combo_snapshots() -> dict:
    return {"s%d_d%d" % (n, d): combo_snapshot(n, d) for n in range(5) for d in (1, 2)}
