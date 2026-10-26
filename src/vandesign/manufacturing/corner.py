"""ADR-0003 blind corner: where two carcasses of an L meet, joined invisibly.

The cabinet that runs into the corner gets a fixed BLIND panel (in place of
its corner door, inside the inset opening) wide enough that the other
cabinet butts against it with room for its doors. The butting cabinet gets
clearance holes through that side panel; the blind panel gets matching pilot
holes in its front face; screws go from inside the butting cabinet, so no
fixing shows. Both patterns are measured from the same references: along the
wall from the corner wall (the blind cabinet's outer face on its blind side,
the butting cabinet's back face) and up from the cabinet bottom. The
arrangement refuses any hole without its partner. Screws are not qualified.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
import math

from .profile import ProfileError

SIDES = {"left": "panel.left.001", "right": "panel.right.001"}


def _pattern(obj):
    if obj.side not in SIDES:
        raise ProfileError("side must be 'left' or 'right'")
    for name in ("offsets_mm", "heights_mm"):
        v = getattr(obj, name)
        if (not isinstance(v, (tuple, list)) or not 1 <= len(v) <= 6
                or any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in v)):
            raise ProfileError("%s needs 1-6 positive numbers" % name)
        object.__setattr__(obj, name, tuple(float(x) for x in v))
    for f in fields(obj):
        v = getattr(obj, f.name)
        if f.name not in ("side", "offsets_mm", "heights_mm") and (
                type(v) not in (int, float) or not math.isfinite(v) or v <= 0):
            raise ProfileError("%s must be a positive number" % f.name)


def _from_json(cls, data, name):
    allowed = {f.name for f in fields(cls)}
    if not isinstance(data, dict) or not set(data) <= allowed or "side" not in data:
        raise ProfileError("%s takes side and only: %s" % (name, ", ".join(sorted(allowed))))
    return cls(**data)


@dataclass(frozen=True)
class Blind:
    """Fixed blind panel on ``side``, reaching ``width_mm`` in from that outer face."""
    side: str
    width_mm: float
    offsets_mm: tuple = (150.0, 400.0)   # pilots along the cabinet from the blind-side outer face
    heights_mm: tuple = (200.0, 600.0)   # and up from the cabinet bottom
    pilot_mm: float = 3.0
    pilot_depth_mm: float = 10.0

    def __post_init__(self):
        _pattern(self)

    @classmethod
    def from_json(cls, data):
        return _from_json(cls, data, "blind")


@dataclass(frozen=True)
class CornerFixings:
    """Clearance holes through the ``side`` panel of the cabinet that butts a blind panel."""
    side: str
    offsets_mm: tuple = (150.0, 400.0)   # from the cabinet's back face
    heights_mm: tuple = (200.0, 600.0)   # up from the cabinet bottom
    hole_mm: float = 5.0

    def __post_init__(self):
        _pattern(self)

    @classmethod
    def from_json(cls, data):
        return _from_json(cls, data, "corner_fixings")


def blind_pilots(boxes, blind, panel_id):
    """{blind panel id: [(module-frame centre on its front face, -y, diameter, depth)]}."""
    b = boxes[panel_id]
    ref = boxes["panel.left.001"].lo[0] if blind.side == "left" else boxes["panel.right.001"].hi[0]
    sign = 1 if blind.side == "left" else -1
    z0 = boxes["panel.bottom.001"].lo[2]
    out = []
    for o in blind.offsets_mm:
        x = ref + sign * o
        for h in blind.heights_mm:
            z = z0 + h
            if not (b.lo[0] + blind.pilot_mm <= x <= b.hi[0] - blind.pilot_mm
                    and b.lo[2] + blind.pilot_mm <= z <= b.hi[2] - blind.pilot_mm):
                raise ProfileError("Blind-panel pilot at %g mm along, %g mm up misses the blind panel" % (o, h))
            out.append(((x, b.lo[1], z), (0, -1, 0), blind.pilot_mm, blind.pilot_depth_mm))
    return {panel_id: out}


def corner_holes(boxes, fixings):
    """{side panel id: [(module-frame centre on its outer face, outward normal, diameter, None = through)]}."""
    pid = SIDES[fixings.side]
    s = boxes[pid]
    x, normal = (s.lo[0], (-1, 0, 0)) if fixings.side == "left" else (s.hi[0], (1, 0, 0))
    z0 = boxes["panel.bottom.001"].lo[2]
    out = [((x, s.hi[1] - o, z0 + h), normal, fixings.hole_mm, None)
           for o in fixings.offsets_mm for h in fixings.heights_mm]
    for (_, y, z), _, d, _ in out:
        if not (s.lo[1] + d <= y <= s.hi[1] - d and s.lo[2] + d <= z <= s.hi[2] - d):
            raise ProfileError("Corner fixing hole misses the %s side panel" % fixings.side)
    return {pid: out}
