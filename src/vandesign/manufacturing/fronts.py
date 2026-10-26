"""ADR-0003 inset doors: placement inside the carcass opening and hidden hardware bores.

Doors sit between the sides, bottom and top, flush with their front edges,
with an equal ``gap_mm`` all round and between doors. Shelves are set back
behind the doors' back faces by ``setback_mm`` (room for a push latch).
Hardware is cut geometry only: 35 mm concealed hinge cups in each door's back
face, hinge-plate pilot holes in the side's inner face and push-latch pilot
holes in the bottom panel behind each door's free edge. Product positions
follow common 37 mm-system practice; the hardware is NOT chosen yet, so every
value is editable data and nothing here qualifies a product or a load.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
import math

from ..core.geometry import Box
from .joints import MIN_SKIN_MM
from .profile import Hole, ProfileError


def _positive(obj):
    for f in fields(obj):
        v = getattr(obj, f.name)
        if isinstance(v, (Hinge, Latch)):
            continue
        if type(v) not in (int, float) or not math.isfinite(v) or v <= 0:
            raise ProfileError("%s must be a positive number" % f.name)


def _strict(cls, data, name):
    if data is None:
        return cls()
    allowed = {f.name for f in fields(cls)}
    if not isinstance(data, dict) or not set(data) <= allowed:
        raise ProfileError("%s takes only: %s" % (name, ", ".join(sorted(allowed))))
    return cls(**data)


@dataclass(frozen=True)
class Hinge:
    cup_diameter_mm: float = 35.0
    cup_depth_mm: float = 12.5
    cup_edge_mm: float = 22.5        # cup centre from the door's hinge edge
    end_offset_mm: float = 100.0     # first and last cup centre from the door's ends
    plate_setback_mm: float = 37.0   # plate holes behind the door's back face
    plate_pitch_mm: float = 32.0     # the plate's two holes, centred on the cup height
    plate_hole_mm: float = 5.0
    plate_hole_depth_mm: float = 10.0

    def __post_init__(self):
        _positive(self)


@dataclass(frozen=True)
class Latch:
    """Pilot holes for a surface-mounted push-to-open latch on the bottom panel."""
    hole_mm: float = 3.0
    depth_mm: float = 8.0
    setback_mm: float = 12.0         # behind the door's back face
    edge_inset_mm: float = 40.0      # from the door's free (non-hinge) edge
    pitch_mm: float = 24.0           # second hole, further from the free edge

    def __post_init__(self):
        _positive(self)


@dataclass(frozen=True)
class InsetFronts:
    gap_mm: float = 2.5
    setback_mm: float = 2.0
    hinge: Hinge = Hinge()
    latch: Latch = Latch()

    def __post_init__(self):
        _positive(self)
        if type(self.hinge) is not Hinge or type(self.latch) is not Latch:
            raise ProfileError("fronts need Hinge and Latch records")

    @classmethod
    def from_json(cls, data):
        """``{"style": "inset", ...}``; omitted values take the defaults above."""
        if not isinstance(data, dict) or data.get("style") != "inset" or not set(data) <= {
                "style", "gap_mm", "setback_mm", "hinge", "latch"}:
            raise ProfileError('fronts need style "inset" and only gap_mm, setback_mm, hinge, latch')
        rest = {k: v for k, v in data.items() if k in ("gap_mm", "setback_mm")}
        return cls(hinge=_strict(Hinge, data.get("hinge"), "hinge"),
                   latch=_strict(Latch, data.get("latch"), "latch"), **rest)


def door_ids(boxes):
    return sorted(pid for pid in boxes if pid.startswith("panel.door."))


def hinge_count(height):
    return 2 if height <= 900 else 3 if height <= 1600 else 4


def inset_boxes(boxes, fronts):
    """Door and set-back shelf boxes (module frame) for inset fronts."""
    left, right = boxes["panel.left.001"], boxes["panel.right.001"]
    bottom, top = boxes["panel.bottom.001"], boxes["panel.top.001"]
    doors = door_ids(boxes)
    if not doors:
        raise ProfileError("Inset fronts need at least one door")
    g, n = fronts.gap_mm, len(doors)
    thick = boxes[doors[0]].size[1]
    front = left.lo[1]
    x0, x1, z0, z1 = left.hi[0] + g, right.lo[0] - g, bottom.hi[2] + g, top.lo[2] - g
    width = (x1 - x0 - (n - 1) * g) / n
    if width < 2 * fronts.hinge.cup_edge_mm or z1 - z0 < 2 * fronts.hinge.end_offset_mm:
        raise ProfileError("Inset doors are too small for their hinges")
    over = {}
    for i, pid in enumerate(doors):
        a = x0 + i * (width + g)
        over[pid] = Box((a, front, z0), (a + width, front + thick, z1))
    behind = front + thick + fronts.setback_mm
    for pid, b in boxes.items():
        if pid.startswith("panel.shelf.") and b.lo[1] < behind:
            over[pid] = Box((b.lo[0], behind, b.lo[2]), b.hi)
    return over


def hardware(boxes, fronts):
    """{panel id: [(module-frame centre, outward face normal, diameter, depth)]}.

    Door i hinges on the left for the left half of the doors, on the right
    otherwise; its latch sits behind the opposite (free) edge."""
    doors = door_ids(boxes)
    h, l = fronts.hinge, fronts.latch
    left, right, bottom = boxes["panel.left.001"], boxes["panel.right.001"], boxes["panel.bottom.001"]
    out = {}
    for i, pid in enumerate(doors):
        d = boxes[pid]
        on_left = i < len(doors) / 2
        sign = 1 if on_left else -1                      # from the hinge edge towards the free edge
        edge, free = (d.lo[0], d.hi[0]) if on_left else (d.hi[0], d.lo[0])
        height = d.size[2]
        m = hinge_count(height)
        span = height - 2 * h.end_offset_mm
        for k in range(m):
            z = d.lo[2] + h.end_offset_mm + k * span / (m - 1)
            out.setdefault(pid, []).append(((edge + sign * h.cup_edge_mm, d.hi[1], z), (0, 1, 0),
                                            h.cup_diameter_mm, h.cup_depth_mm))
            side, x, normal = (("panel.left.001", left.hi[0], (1, 0, 0)) if on_left
                               else ("panel.right.001", right.lo[0], (-1, 0, 0)))
            for dz in (-h.plate_pitch_mm / 2, h.plate_pitch_mm / 2):
                out.setdefault(side, []).append(((x, d.hi[1] + h.plate_setback_mm, z + dz), normal,
                                                 h.plate_hole_mm, h.plate_hole_depth_mm))
        y = d.hi[1] + l.setback_mm
        for dx in (l.edge_inset_mm, l.edge_inset_mm + l.pitch_mm):
            out.setdefault("panel.bottom.001", []).append(((free - sign * dx, y, bottom.hi[2]), (0, 0, 1),
                                                          l.hole_mm, l.depth_mm))
    return out


def _local(p, origin, frame):
    d = [p[i] - origin[i] for i in range(3)]
    return tuple(sum(d[i] * axis[i] for i in range(3) if axis[i]) for axis in (frame.u, frame.v, frame.w))


def add_hardware(profiles, boxes, fronts, captures):
    """Profiles with the hardware bores added as Holes (after their cut
    features); ``captures`` gets each hole's local centre as computed (Tracked
    in a width-binding run) for its binding."""
    holes = hardware(boxes, fronts)
    out = []
    for p in profiles:
        found = holes.get(p.panel_id, ())
        if not found:
            out.append(p)
            continue
        cap = captures[p.panel_id]
        cap["holes"] = []
        new = []
        for centre, normal, diameter, depth in found:
            if p.thickness - depth < MIN_SKIN_MM - 1e-9:
                raise ProfileError("%s: a %g mm deep bore leaves less than %g mm" % (p.panel_id, depth, MIN_SKIN_MM))
            w = p.frame.w
            face = "top" if w == tuple(float(x) for x in normal) else (
                "bottom" if w == tuple(-float(x) for x in normal) else None)
            if face is None:
                raise ProfileError("%s: hardware bore is not on a panel face" % p.panel_id)
            a, b, c = _local(centre, cap["origin"], p.frame)
            if abs(c - (p.thickness if face == "top" else 0.0)) > 1e-6:
                raise ProfileError("%s: hardware bore does not start on the panel face" % p.panel_id)
            new.append(Hole((float(a), float(b)), float(diameter), float(depth), face))
            cap["holes"].append((a, b, diameter, depth, face))
        out.append(replace(p, features=p.features + tuple(new)))
    return tuple(out)
