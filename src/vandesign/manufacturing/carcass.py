"""Tab-and-slot cabinet carcass: joinery spec and module-local profiles.

Bottom and top tab flush through both sides (engagement = measured side
thickness); shelves keep their dados; doors and back are unchanged. Profiles
are computed in the cabinet's own frame: a part's cut shape does not change
when the cabinet is moved or rotated, only its frame does.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math

from .assembly import assembly_profiles
from .joints import Sheet, TabSlot, apply_joints
from .profile import ProfileError

_JOINERY_KEYS = {"sheet", "clearance_mm", "tabs_per_edge", "tab_width_mm", "tool_diameter_mm"}
_SHEET_KEYS = {"name", "nominal_mm", "measured_mm"}
SIDES = (("panel.left.001", "-x"), ("panel.right.001", "+x"))
TABBED = ("panel.bottom.001", "panel.top.001")


@dataclass(frozen=True)
class TabSlotJoinery:
    sheet: Sheet
    tool_diameter_mm: float
    clearance_mm: float = 0.2
    tabs_per_edge: int = 2
    tab_width_mm: float | None = None

    def __post_init__(self):
        if type(self.sheet) is not Sheet:
            raise ProfileError("Joinery needs a Sheet")
        for name in ("tool_diameter_mm", "clearance_mm"):
            v = getattr(self, name)
            if type(v) not in (int, float) or not math.isfinite(v):
                raise ProfileError("%s must be a finite number" % name)
        if not 0 < self.tool_diameter_mm <= 25:
            raise ProfileError("tool_diameter_mm must be in (0, 25]")
        if not 0 <= self.clearance_mm <= 2:
            raise ProfileError("clearance_mm must be in [0, 2]")
        if type(self.tabs_per_edge) is not int or not 1 <= self.tabs_per_edge <= 6:
            raise ProfileError("tabs_per_edge must be 1-6")
        w = self.tab_width_mm
        if w is not None and (type(w) not in (int, float) or not math.isfinite(w) or w <= 0):
            raise ProfileError("tab_width_mm must be positive")

    @classmethod
    def from_json(cls, data):
        """Strict: exact keys (tab_width_mm may be null)."""
        if not isinstance(data, dict) or set(data) != _JOINERY_KEYS:
            raise ProfileError("joinery needs exactly: " + ", ".join(sorted(_JOINERY_KEYS)))
        sheet = data["sheet"]
        if not isinstance(sheet, dict) or set(sheet) != _SHEET_KEYS:
            raise ProfileError("sheet needs exactly: " + ", ".join(sorted(_SHEET_KEYS)))
        return cls(Sheet(sheet["name"], sheet["nominal_mm"], sheet["measured_mm"]), data["tool_diameter_mm"],
                   data["clearance_mm"], data["tabs_per_edge"], data["tab_width_mm"])


def cabinet_joints(boxes, joinery):
    """Four TabSlot joints for a cabinet's resolved panel boxes (module frame)."""
    depth = boxes["panel.bottom.001"].size[1]
    n = joinery.tabs_per_edge
    width = float(joinery.tab_width_mm if joinery.tab_width_mm is not None else min(120.0, depth / (2 * n)))
    tabs = tuple(((k + 0.5) * depth / n - width / 2, width) for k in range(n))
    t = joinery.sheet.measured_mm
    return [TabSlot(panel, side, direction, tabs, t, joinery.clearance_mm)
            for panel in TABBED for side, direction in SIDES]


def cabinet_tab_slot_profiles(assembly, joinery, values=None):
    """Module-frame profiles of a cabinet assembly with tab-and-slot carcass joints.

    The cabinet's Cab_Ply must equal the sheet's measured thickness.
    Returns (profiles, joint results).
    """
    env = assembly.parameters.resolve(values)
    if abs(env["Cab_Ply"] - joinery.sheet.measured_mm) > 1e-9:
        raise ProfileError("Cab_Ply %.3f mm must equal the measured sheet thickness %.3f mm"
                           % (env["Cab_Ply"], joinery.sheet.measured_mm))
    failed = [c.constraint_id for c, ok, _, _ in assembly.check_constraints(env) if not ok]
    if failed:
        raise ProfileError("Cabinet constraints fail: " + ", ".join(failed))
    boxes = {p.stable_id: p.box.resolve(env) for p in assembly.panels}
    overrides, cuts, results = apply_joints(cabinet_joints(boxes, joinery), boxes)
    profiles = assembly_profiles(assembly, values, tool_diameter=joinery.tool_diameter_mm,
                                 extra_cuts=cuts, box_overrides=overrides)
    t = joinery.sheet.measured_mm
    out = tuple(replace(p, notes=p.notes + (joinery.sheet.note,)) if abs(p.thickness - t) <= 1e-9 else p
                for p in profiles)
    return out, results
