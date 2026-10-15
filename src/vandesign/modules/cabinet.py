"""Base cabinet with sliding dado shelves: CabinetSpec -> AssemblyDefinition.

Pure Python - no CAD imports.  This is the single authoritative definition of
every derived quantity (shelf length, groove position, shelf heights ...).
Parameter names are the V4 names so existing Fusion designs keep their
meaning (see SPEC_TO_PARAM, the migration map).
"""

from __future__ import annotations

from typing import Dict

from ..components.ids import dado_id, panel_id
from ..components.model import AssemblyDefinition, Constraint, ConstraintViolation, DadoOperation, Panel
from ..core.expr import Mm, Param
from ..core.geometry import BoxExpr
from ..core.params import ParamDef, ParameterSet
from ..schemas.cabinet_spec import CabinetSpec

# Migration map: CabinetSpec field -> V4 Fusion user-parameter name.
SPEC_TO_PARAM: Dict[str, str] = {
    "width_mm": "Cab_Width",
    "height_mm": "Cab_Height",
    "depth_mm": "Cab_Depth",
    "ply_mm": "Cab_Ply",
    "back_mm": "Cab_Back",
    "gap_mm": "Cab_Gap",
    "dado_depth_mm": "Cab_Dado_Depth",
    "slot_clearance_mm": "Cab_Slot_Clearance",
    "end_clearance_mm": "Cab_End_Clearance",
}

_BASE_COMMENTS = {
    "Cab_Dado_Depth": "Groove penetrates each side panel",
    "Cab_Slot_Clearance": "Groove is this much taller than the shelf",
    "Cab_End_Clearance": "Gap at EACH shelf end, bottom of groove",
}
PARAM_COMMENT = "Van Cabinet Joinery V5"

W, H, D = Param("Cab_Width"), Param("Cab_Height"), Param("Cab_Depth")
T, B, G = Param("Cab_Ply"), Param("Cab_Back"), Param("Cab_Gap")
GD, SC, EC = Param("Cab_Dado_Depth"), Param("Cab_Slot_Clearance"), Param("Cab_End_Clearance")
INNER_D = Param("Cab_Inner_Depth")
SLOT_H = Param("Cab_Slot_Height")
ZERO = Mm(0)


def _parameters(spec: CabinetSpec) -> ParameterSet:
    n = spec.shelf_count
    defs = [
        ParamDef(SPEC_TO_PARAM[f], value_mm=float(getattr(spec, f)), comment=_BASE_COMMENTS.get(SPEC_TO_PARAM[f], PARAM_COMMENT))
        for f in SPEC_TO_PARAM
    ]
    comp = Param("Cab_Compartment")
    defs += [
        ParamDef("Cab_Inner_Depth", expr=D - B, comment="Side-panel depth minus back"),
        ParamDef("Cab_Slot_Height", expr=T + SC, comment="Groove height"),
        ParamDef("Cab_Shelf_X", expr=T - GD + EC, comment="Shelf left end X"),
        ParamDef("Cab_Shelf_Length", expr=W - 2 * T + 2 * GD - 2 * EC, comment="Shelf length incl. both groove insertions"),
        ParamDef("Cab_Compartment", expr=(H - (2 + n) * T) / (n + 1), comment="Equal clear compartment height"),
    ]
    for k in range(1, n + 1):
        defs.append(ParamDef("Cab_Shelf%d_Z" % k, expr=T + k * comp + (k - 1) * T, comment="Shelf %d underside Z" % k))
        defs.append(ParamDef("Cab_Slot%d_Z" % k, expr=Param("Cab_Shelf%d_Z" % k) - SC / 2, comment="Groove %d underside Z" % k))
    return ParameterSet(tuple(defs))


def _constraints(spec: CabinetSpec):
    n, doors = spec.shelf_count, spec.door_count
    return (
        Constraint("ply_positive", "Cab_Ply > 0", T, ">", ZERO),
        Constraint("dado_positive", "Cab_Dado_Depth > 0", GD, ">", ZERO),
        Constraint("dado_lt_ply", "groove must leave side-panel material (Cab_Ply > Cab_Dado_Depth)", T, ">", GD),
        Constraint("end_clearance_nonneg", "Cab_End_Clearance >= 0", EC, ">=", ZERO),
        Constraint("end_clearance_lt_dado", "shelf must enter the groove (Cab_Dado_Depth > Cab_End_Clearance)", GD, ">", EC),
        Constraint("slot_clearance_nonneg", "Cab_Slot_Clearance >= 0", SC, ">=", ZERO),
        Constraint("back_positive", "Cab_Back > 0", B, ">", ZERO),
        Constraint("back_lt_depth", "Cab_Depth > Cab_Back", D, ">", B),
        Constraint("gap_nonneg", "Cab_Gap >= 0", G, ">=", ZERO),
        Constraint("height_fits", "Cab_Height > (2 + shelves) * Cab_Ply", H, ">", (2 + n) * T),
        Constraint("width_fits", "Cab_Width > 2 * Cab_Ply", W, ">", 2 * T),
        Constraint("doors_fit", "Cab_Width > (doors + 1) * Cab_Gap", W, ">", (doors + 1) * G),
    )


def build_cabinet(spec: CabinetSpec) -> AssemblyDefinition:
    params = _parameters(spec)
    constraints = _constraints(spec)

    # Fail early (before any CAD) if the nominal spec violates a constraint.
    failed = [
        "%s: %s (%.4g vs %.4g)" % (c.constraint_id, c.description, a, b)
        for c, ok, a, b in AssemblyDefinition("tmp", "", params, (), (), constraints).check_constraints(params.resolve())
        if not ok
    ]
    if failed:
        raise ConstraintViolation("; ".join(failed))

    front = T  # body sits behind the front doors (door thickness = plywood)
    inner_w = W - 2 * T
    mat = spec.material_ref

    def panel(role, index, name, ox, oy, oz, sx, sy, sz):
        return Panel(panel_id(role, index), name, role, mat, BoxExpr((ox, oy, oz), (sx, sy, sz)))

    panels = [
        panel("left", 1, "01 Left Side", ZERO, front, ZERO, T, D, H),
        panel("right", 1, "02 Right Side", W - T, front, ZERO, T, D, H),
        panel("bottom", 1, "03 Bottom", T, front, ZERO, inner_w, INNER_D, T),
        panel("top", 1, "04 Top", T, front, H - T, inner_w, INNER_D, T),
        panel("back", 1, "05 Back", T, front + D - B, T, inner_w, B, H - 2 * T),
    ]
    ops = []
    for k in range(1, spec.shelf_count + 1):
        panels.append(panel("shelf", k, "06 Shelf %d" % k, Param("Cab_Shelf_X"), front,
                            Param("Cab_Shelf%d_Z" % k), Param("Cab_Shelf_Length"), INNER_D, T))
        slot_z = Param("Cab_Slot%d_Z" % k)
        for side, ox in (("left", T - GD), ("right", W - T)):
            ops.append(DadoOperation(
                operation_id=dado_id(k, side),
                target_panel_id=panel_id(side, 1),
                mating_panel_id=panel_id("shelf", k),
                side=side,
                cut=BoxExpr((ox, front, slot_z), (GD, INNER_D, SLOT_H)),
                groove_depth=GD, end_clearance=EC, slot_clearance=SC,
            ))

    nd = spec.door_count
    door_w = (W - (nd + 1) * G) / nd
    for i in range(nd):
        panels.append(panel("door", i + 1, "07 Door %d" % (i + 1),
                            (i + 1) * G + i * door_w, ZERO, G, door_w, T, H - 2 * G))

    asm = AssemblyDefinition(spec.cabinet_id, spec.spec_hash(), params, tuple(panels), tuple(ops), constraints)
    asm.validate_structure()
    return asm
