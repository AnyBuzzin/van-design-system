"""ADR-0003 carcass top for a worktop: hidden fixing holes and an optional sink opening.

The worktop is screwed from inside the cabinet, up through clearance holes in
the carcass top panel (two rows, front and back) into pilot holes in the
worktop's underside, so no fixing shows. Under a sink the top panel becomes a
frame: a through opening leaves rails ``sink_rail_mm`` wide, and the fixing
rows sit in the front and back rails. Positions are relative to the top panel,
so they follow width edits. Every value is editable; screws are not qualified.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
import math

from ..core.geometry import Box
from .profile import ProfileError

TOP = "panel.top.001"


@dataclass(frozen=True)
class CarcassTop:
    fixing_hole_mm: float = 5.0        # clearance hole, through the carcass top
    fixings_per_row: int = 3           # front and back rows
    fixing_inset_mm: float = 40.0      # from the top panel's edges
    sink_rail_mm: float | None = None  # None: solid top; else the rail width around a sink opening
    pilot_hole_mm: float = 3.0         # matching pilot in the worktop underside
    pilot_depth_mm: float = 10.0

    def __post_init__(self):
        for f in fields(self):
            v = getattr(self, f.name)
            if f.name == "fixings_per_row":
                if type(v) is not int or not 2 <= v <= 8:
                    raise ProfileError("fixings_per_row must be 2-8")
            elif not (v is None and f.name == "sink_rail_mm") and (
                    type(v) not in (int, float) or not math.isfinite(v) or v <= 0):
                raise ProfileError("%s must be a positive number" % f.name)
        if self.sink_rail_mm is not None and self.fixing_inset_mm >= self.sink_rail_mm:
            raise ProfileError("fixing_inset_mm must lie inside the sink rails")

    @classmethod
    def from_json(cls, data):
        allowed = {f.name for f in fields(cls)}
        if not isinstance(data, dict) or not set(data) <= allowed:
            raise ProfileError("top takes only: " + ", ".join(sorted(allowed)))
        return cls(**data)


def sink_opening(boxes, top):
    """(panel id, through-cut Box) leaving rails round the carcass top, or ()."""
    if top.sink_rail_mm is None:
        return ()
    b, r = boxes[TOP], top.sink_rail_mm
    if min(b.size[0], b.size[1]) <= 2 * r + 100:
        raise ProfileError("Carcass top too small for a %g mm rail frame" % r)
    return ((TOP, Box((b.lo[0] + r, b.lo[1] + r, b.lo[2]), (b.hi[0] - r, b.hi[1] - r, b.hi[2]))),)


def fixing_holes(boxes, top):
    """{TOP: [(module-frame centre on the top face, +z, diameter, None = through)]}."""
    b, n, i = boxes[TOP], top.fixings_per_row, top.fixing_inset_mm
    span = b.size[0] - 2 * i
    out = []
    for y in (b.lo[1] + i, b.hi[1] - i):
        for k in range(n):
            out.append(((b.lo[0] + i + k * span / (n - 1), y, b.hi[2]), (0, 0, 1), top.fixing_hole_mm, None))
    return {TOP: out}
