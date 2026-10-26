"""Reusable CNC tab-and-slot joints between two flat panels (offline core).

A joint is applied in world space to axis-aligned panel blanks. The inserting
panel grows tabs of depth ``engagement`` through the receiving panel's
thickness; notches are cut between the tabs; slots with ``clearance`` (split
equally on both sides) are cut through the receiver. The profile pipeline
then adds dog-bone relief to every inside corner of both parts, including
the tab roots, so a round tool of the given diameter can cut them.

Sheet thicknesses are the MEASURED values: callers build blanks from them.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from ..core.geometry import Box
from .profile import Arc, Line, ProfileError, boundary_distance, CLOSURE_TOL_MM

NOMINAL_THICKNESSES_MM = (5, 10, 12, 15, 18)
_EPS = 1e-9
_AXES = {"x": 0, "y": 1, "z": 2}


def _number(v, name, lo=None, hi=None):
    if type(v) not in (int, float) or not math.isfinite(v):
        raise ProfileError("%s must be a finite number" % name)
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise ProfileError("%s must be within [%s, %s]" % (name, lo, hi))
    return float(v)


@dataclass(frozen=True)
class Sheet:
    """A plywood sheet: nominal thickness for ordering, measured for geometry."""
    name: str
    nominal_mm: float
    measured_mm: float

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ProfileError("Sheet needs a name")
        if self.nominal_mm not in NOMINAL_THICKNESSES_MM:
            raise ProfileError("Nominal thickness must be one of %s mm" % (NOMINAL_THICKNESSES_MM,))
        _number(self.measured_mm, "Measured thickness", self.nominal_mm - 1.0, self.nominal_mm + 1.0)
        if self.measured_mm <= 0:
            raise ProfileError("Measured thickness must be positive")

    @property
    def note(self):
        return "%s: measured %.2f mm (nominal %g mm)" % (self.name, self.measured_mm, self.nominal_mm)


@dataclass(frozen=True)
class TabSlot:
    """``inserter`` enters ``receiver`` moving along ``direction`` (e.g. '-z').

    ``tabs`` are (offset, width) pairs along the joint axis, measured from the
    inserter blank's low end on that axis.
    """
    inserter: str
    receiver: str
    direction: str
    tabs: tuple
    engagement_mm: float
    clearance_mm: float

    def __post_init__(self):
        if (not isinstance(self.direction, str) or len(self.direction) != 2
                or self.direction[0] not in "+-" or self.direction[1] not in _AXES):
            raise ProfileError("direction must be one of +x, -x, +y, -y, +z, -z")
        if self.inserter == self.receiver:
            raise ProfileError("A panel cannot join itself")
        _number(self.engagement_mm, "Engagement", 0.0)
        if self.engagement_mm <= 0:
            raise ProfileError("Engagement must be positive")
        _number(self.clearance_mm, "Clearance", 0.0, 5.0)
        tabs = tuple(tuple(t) for t in self.tabs)
        if not tabs or any(len(t) != 2 for t in tabs):
            raise ProfileError("At least one (offset, width) tab is required")
        for offset, width in tabs:
            _number(offset, "Tab offset", 0.0)
            _number(width, "Tab width")
            if width <= 0:
                raise ProfileError("Tab width must be positive")
        ordered = sorted(tabs)
        if any(a[0] + a[1] >= b[0] - _EPS for a, b in zip(ordered, ordered[1:])):
            raise ProfileError("Tabs must be separated by material")
        object.__setattr__(self, "tabs", tuple(ordered))


@dataclass(frozen=True)
class JointResult:
    joint: TabSlot
    inserter_box: Box          # blank extended by the tab depth
    cuts: tuple                # (panel id, world Box) through-cuts: notches and slots
    tabs: tuple                # world Boxes of the tabs
    slots: tuple               # world Boxes of the slots
    proof: dict


def _thin(box):
    s = box.size
    t = min(range(3), key=lambda i: s[i])
    if sum(1 for v in s if abs(v - s[t]) <= _EPS) != 1:
        raise ProfileError("Ambiguous sheet thickness for box size %r" % (s,))
    return t


def _box(ranges):
    return Box(tuple(r[0] for r in ranges), tuple(r[1] for r in ranges))


def apply_tab_slot(joint, inserter_box, receiver_box):
    """Tabs, notches and slots for one joint, with box-level proofs."""
    d = _AXES[joint.direction[1]]
    sign = -1 if joint.direction[0] == "-" else 1
    ti, tr = _thin(inserter_box), _thin(receiver_box)
    if tr != d or ti == d:
        raise ProfileError("The inserter must enter through the receiver's thickness")
    j = 3 - ti - d
    face = receiver_box.hi[d] if sign < 0 else receiver_box.lo[d]
    edge = inserter_box.lo[d] if sign < 0 else inserter_box.hi[d]
    if abs(face - edge) > CLOSURE_TOL_MM:
        raise ProfileError("The inserter edge must rest on the receiver face")
    e, c = joint.engagement_mm, joint.clearance_mm
    if e > receiver_box.size[d] + CLOSURE_TOL_MM:
        raise ProfileError("Engagement exceeds the receiver thickness")
    strip = (face - e, face) if sign < 0 else (face, face + e)
    lo_j, hi_j = inserter_box.lo[j], inserter_box.hi[j]
    if joint.tabs[-1][0] + joint.tabs[-1][1] > hi_j - lo_j + _EPS:
        raise ProfileError("Tabs extend beyond the inserter")
    ext = [list(r) for r in zip(inserter_box.lo, inserter_box.hi)]
    ext[d] = [min(ext[d][0], strip[0]), max(ext[d][1], strip[1])]
    thick = (inserter_box.lo[ti], inserter_box.hi[ti])
    tabs, slots, cuts = [], [], []
    cursor = lo_j
    for offset, width in joint.tabs:
        a, b = lo_j + offset, lo_j + offset + width
        if a > cursor + _EPS:
            cuts.append((joint.inserter, _box(_ranges(j, (cursor, a), ti, thick, d, strip))))
        tab = _box(_ranges(j, (a, b), ti, thick, d, strip))
        slot = _box(_ranges(j, (a - c / 2, b + c / 2), ti, (thick[0] - c / 2, thick[1] + c / 2),
                            d, (receiver_box.lo[d], receiver_box.hi[d])))
        if any(tab.lo[k] < receiver_box.lo[k] - _EPS or tab.hi[k] > receiver_box.hi[k] + _EPS for k in (j, ti)):
            raise ProfileError("Tab at offset %g lies outside the receiver" % offset)
        tabs.append(tab)
        slots.append(slot)
        cuts.append((joint.receiver, slot))
        cursor = b
    if hi_j > cursor + _EPS:
        cuts.append((joint.inserter, _box(_ranges(j, (cursor, hi_j), ti, thick, d, strip))))
    proof = _prove(joint, tabs, slots, receiver_box, j, ti, d)
    return JointResult(joint, _box(ext), tuple(cuts), tuple(tabs), tuple(slots), proof)


def _ranges(a1, r1, a2, r2, a3, r3):
    out = [None, None, None]
    out[a1], out[a2], out[a3] = r1, r2, r3
    return out


def _prove(joint, tabs, slots, receiver_box, j, ti, d):
    """Clearance on both faces, full-depth slots and no assembled material overlap."""
    c = joint.clearance_mm
    gaps = []
    for tab, slot in zip(tabs, slots):
        for k in (j, ti):
            gaps += [tab.lo[k] - slot.lo[k], slot.hi[k] - tab.hi[k]]
        if slot.lo[d] > receiver_box.lo[d] + _EPS or slot.hi[d] < receiver_box.hi[d] - _EPS:
            raise ProfileError("Slot does not pass through the receiver")
    if any(abs(g - c / 2) > 1e-9 for g in gaps):
        raise ProfileError("Clearance per face differs from clearance / 2")
    # Receiver material in the joint = receiver box minus slots; tabs lie inside slots.
    overlap = sum(receiver_box.overlap_volume(t) - slot.overlap_volume(t) for t, slot in zip(tabs, slots))
    if overlap > 1e-6:
        raise ProfileError("Assembled tabs overlap receiver material")
    return dict(clearance_per_face_mm=c / 2, tabs=len(tabs), assembled_overlap_mm3=overlap,
                engagement_mm=joint.engagement_mm)


def apply_joints(joints, boxes):
    """Apply joints in order. Returns (box overrides, extra cuts, results)."""
    boxes = dict(boxes)
    overrides, cuts, results = {}, [], []
    for joint in joints:
        if joint.inserter not in boxes or joint.receiver not in boxes:
            raise ProfileError("Joint names an unknown panel")
        result = apply_tab_slot(joint, boxes[joint.inserter], boxes[joint.receiver])
        boxes[joint.inserter] = overrides[joint.inserter] = result.inserter_box
        cuts.extend(result.cuts)
        results.append(result)
    return overrides, tuple(cuts), tuple(results)


def unrelieved_inside_corners(profile, tool_diameter):
    """Inside corners a round tool of ``tool_diameter`` cannot cut square.

    Every 90-degree corner whose waste side is the narrow wedge must carry a
    relief arc of at least the tool radius; corners on the outline boundary
    (open pocket edges) are exempt. Returns the offending corner points.
    """
    r = tool_diameter / 2
    bad = []
    loops = [(profile.outline, False)] + [(f.loop, True) for f in profile.features if hasattr(f, "loop")]
    for loop, waste_inside in loops:
        segs = loop.segments
        for a, b in zip(segs, segs[1:] + segs[:1]):
            if isinstance(a, Arc) and a.radius < r - 1e-9:
                bad.append(a.end)
            if not (isinstance(a, Line) and isinstance(b, Line)):
                continue
            d1 = (a.end[0] - a.start[0], a.end[1] - a.start[1])
            d2 = (b.end[0] - b.start[0], b.end[1] - b.start[1])
            turn = d1[0] * d2[1] - d1[1] * d2[0]
            narrow_waste = turn > 0 if waste_inside else turn < 0
            if narrow_waste and not (waste_inside and boundary_distance(a.end, profile.outline) <= CLOSURE_TOL_MM):
                bad.append(a.end)
    return bad
