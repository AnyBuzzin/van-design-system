"""B1 axis-aligned reference space; geometry only, never a vehicle-fit claim."""
from dataclasses import asdict, dataclass
import json
import math
import re

SCHEMA = "vandesign.lined-envelope/1"
SCHEMA2 = "vandesign.lined-envelope/2"    # adds optional angled upper walls (B2)
UPPER_FIELDS = ("upper_left_break_mm", "upper_left_inset_mm", "upper_right_break_mm", "upper_right_inset_mm")
NOTICE = "PUBLISHED-NOMINAL Transit L2H3; lining, margin and arches ASSUMED; UNMEASURED"


def number(value):
    return type(value) in (int, float) and abs(value) <= 100000 and math.isfinite(value)


def vector(value):
    return isinstance(value, (tuple, list)) and len(value) == 3 and all(number(v) for v in value)


@dataclass(frozen=True)
class KeepOut:
    """Finished-frame box. For a door, size includes the full clearance depth."""
    name: str
    kind: str
    origin_mm: tuple
    size_mm: tuple

    def __post_init__(self):
        if (not isinstance(self.name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", self.name)
                or self.kind not in ("obstruction", "door")
                or not vector(self.origin_mm) or not vector(self.size_mm)
                or min(self.origin_mm) < 0 or min(self.size_mm) <= 0):
            raise ValueError("Invalid keep-out name, kind or finite box")
        object.__setattr__(self, "origin_mm", tuple(self.origin_mm))
        object.__setattr__(self, "size_mm", tuple(self.size_mm))


@dataclass(frozen=True)
class MountingPoint:
    position_mm: tuple
    normal: tuple
    kind: str
    capacity: str = "unqualified"

    def __post_init__(self):
        if (not vector(self.position_mm) or not vector(self.normal)
                or sum(v*v for v in self.normal) == 0
                or not isinstance(self.kind, str) or not self.kind.strip()
                or self.capacity != "unqualified"):
            raise ValueError("Finite mounting point, nonzero normal and unqualified capacity required")
        object.__setattr__(self, "position_mm", tuple(self.position_mm))
        object.__setattr__(self, "normal", tuple(self.normal))


@dataclass(frozen=True)
class EnvelopeSpec:
    """Uniform allowance on six bare faces; finished floor is always Z=0.

    Ceiling split is Y in the finished frame; second height is bare height.
    Wheel arches use bare datums; exposed dimensions subtract floor/side lining.
    Other keep-outs/mounts use finished datums and must be retargeted explicitly.
    """
    bare_width_mm: float = 1784
    bare_length_mm: float = 3044
    bare_height_mm: float = 2025
    lining_mm: float = 18
    tolerance_mm: float = 5
    bare_between_arches_mm: float = 1392
    arch_length_mm: float = 800
    arch_height_mm: float = 300
    arch_y_mm: float = 600
    ceiling_split_mm: float | None = None
    second_bare_height_mm: float | None = None
    keepouts: tuple = ()
    mounting_points: tuple = ()
    provenance: str = NOTICE
    # B2 angled upper walls (finished frame, optional per side): the lining
    # leans inward from the break height, reaching ``inset`` horizontally at
    # the main finished ceiling height. Absent on both sides = schema /1.
    upper_left_break_mm: float | None = None
    upper_left_inset_mm: float | None = None
    upper_right_break_mm: float | None = None
    upper_right_inset_mm: float | None = None

    def __post_init__(self):
        values = asdict(self)
        for key in ("keepouts", "mounting_points", "provenance",
                    "ceiling_split_mm", "second_bare_height_mm") + UPPER_FIELDS:
            values.pop(key)
        if any(not number(v) for v in values.values()):
            raise ValueError("Complete finite envelope dimensions required")
        if (min(self.bare_width_mm, self.bare_length_mm, self.bare_height_mm,
                self.bare_between_arches_mm, self.arch_length_mm, self.arch_height_mm) <= 0
                or min(self.lining_mm, self.tolerance_mm, self.arch_y_mm) < 0):
            raise ValueError("Invalid envelope dimensions")
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError("Explicit provenance required; measured fit is not implied")
        if (self.ceiling_split_mm is None) != (self.second_bare_height_mm is None):
            raise ValueError("Ceiling split and second height must be supplied together")
        w, l, h = self.finished_size
        if min(w, l, h) <= 2*self.tolerance_mm:
            raise ValueError("Lining/margin consumes usable space")
        if self.ceiling_split_mm is not None:
            if (not number(self.ceiling_split_mm) or not number(self.second_bare_height_mm)
                    or not self.tolerance_mm < self.ceiling_split_mm < l-self.tolerance_mm
                    or self.second_bare_height_mm == self.bare_height_mm
                    or self.second_bare_height_mm-2*self.lining_mm <= 2*self.tolerance_mm):
                raise ValueError("Invalid ceiling segments")
        aw = (self.bare_width_mm-self.bare_between_arches_mm)/2-self.lining_mm
        ah = self.arch_height_mm-self.lining_mm
        ay = self.arch_y_mm-self.lining_mm
        if (aw <= 0 or ah <= 0 or ay < 0 or ay+self.arch_length_mm > l
                or self.bare_between_arches_mm >= w):
            raise ValueError("Invalid exposed arch geometry after lining")
        if not isinstance(self.keepouts, (tuple, list)) or any(type(k) is not KeepOut for k in self.keepouts):
            raise ValueError("Explicit keep-out records required")
        if len({k.name for k in self.keepouts}) != len(self.keepouts):
            raise ValueError("Duplicate keep-out names")
        if not isinstance(self.mounting_points, (tuple, list)) or any(
                type(m) is not MountingPoint for m in self.mounting_points):
            raise ValueError("Explicit mounting records required")
        insets = []
        for side in ("left", "right"):
            brk, inset = getattr(self, "upper_%s_break_mm" % side), getattr(self, "upper_%s_inset_mm" % side)
            if (brk is None) != (inset is None):
                raise ValueError("Upper %s wall needs both break and inset" % side)
            if brk is None:
                continue
            if not number(brk) or not number(inset) or not 0 < brk < self.heights[0] or inset < 0:
                raise ValueError("Upper %s wall: 0 < break < finished height and inset >= 0" % side)
            insets.append(inset)
        if sum(insets) >= w - 2*self.tolerance_mm:
            raise ValueError("Upper wall insets consume the ceiling width")
        # Reference obstacles must fit the actual, un-inset space too. Both
        # arches are checked: the upper walls need not be symmetric.
        arches = [((0, ay, 0), (aw, self.arch_length_mm, ah)),
                  ((w - aw, ay, 0), (aw, self.arch_length_mm, ah))]
        for origin, size in arches + [(k.origin_mm, k.size_mm) for k in self.keepouts]:
            if (any(o+s > d for o, s, d in zip(origin, size, (w, l, max(self.heights))))
                    or any(origin[2]+size[2] > height for start, end, height in self.segments
                           if origin[1] < end and origin[1]+size[1] > start)
                    or any(self.upper_wall_distance(side, x, z) < 0 for side in self.upper_walls
                           for x in (origin[0], origin[0]+size[0]) for z in (origin[2], origin[2]+size[2]))):
                raise ValueError("Obstruction outside finished envelope")
        for m in self.mounting_points:
            x, y, z = m.position_mm
            if (min(x, y, z) < 0 or x > w or y > l
                    or any(z > height for start, end, height in self.segments if start <= y <= end)):
                raise ValueError("Mounting point outside finished envelope")
        object.__setattr__(self, "keepouts", tuple(self.keepouts))
        object.__setattr__(self, "mounting_points", tuple(self.mounting_points))

    @property
    def finished_size(self):
        return tuple(v-2*self.lining_mm for v in
                     (self.bare_width_mm, self.bare_length_mm, self.bare_height_mm))

    @property
    def heights(self):
        return (self.finished_size[2],) if self.second_bare_height_mm is None else (
            self.finished_size[2], self.second_bare_height_mm-2*self.lining_mm)

    @property
    def segments(self):
        length = self.finished_size[1]
        if self.ceiling_split_mm is None:
            return ((0, length, self.heights[0]),)
        return ((0, self.ceiling_split_mm, self.heights[0]),
                (self.ceiling_split_mm, length, self.heights[1]))

    @property
    def upper_walls(self):
        return tuple(side for side in ("left", "right")
                     if getattr(self, "upper_%s_break_mm" % side) is not None)

    def upper_wall_distance(self, side, x, z):
        """Signed distance (mm) of finished-frame point (x, z) from a sloped
        upper wall plane; positive inside the van. The plane passes through
        the wall at the break height and is ``inset`` from it at the main
        finished ceiling height; it is unbounded, so below the break it lies
        outside the vertical lower wall and constrains nothing extra."""
        brk = getattr(self, "upper_%s_break_mm" % side)
        inset = getattr(self, "upper_%s_inset_mm" % side)
        rise = self.heights[0] - brk
        across = x if side == "left" else self.finished_size[0] - x
        return (across * rise - (z - brk) * inset) / math.hypot(rise, inset)

    def to_json(self):
        params = asdict(self)
        if not self.upper_walls:
            # Byte-identical to schema /1: existing specs keep their hashes.
            for key in UPPER_FIELDS:
                params.pop(key)
        return json.dumps(dict(schema_version=SCHEMA2 if self.upper_walls else SCHEMA, parameters=params),
                          sort_keys=True, separators=(",", ":"), allow_nan=False)


def load_envelope_spec(text):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError("Duplicate envelope key: "+k)
            result[k] = v
        return result
    if not isinstance(text, (str, bytes)) or len(text) > 65536:
        raise ValueError("Envelope JSON required, at most 64 KiB")
    raw = json.loads(text, object_pairs_hook=unique)
    if (not isinstance(raw, dict) or set(raw) != {"schema_version", "parameters"}
            or raw["schema_version"] not in (SCHEMA, SCHEMA2) or not isinstance(raw["parameters"], dict)):
        raise ValueError("Invalid envelope schema")
    fields = raw["parameters"]
    known = set(EnvelopeSpec.__dataclass_fields__)
    if set(fields) != (known if raw["schema_version"] == SCHEMA2 else known - set(UPPER_FIELDS)):
        raise ValueError("Complete known envelope fields required")
    if raw["schema_version"] == SCHEMA2 and all(fields[k] is None for k in UPPER_FIELDS):
        raise ValueError("Schema /2 requires at least one upper wall; use /1")
    try:
        fields["keepouts"] = tuple(KeepOut(**k) for k in fields["keepouts"])
        fields["mounting_points"] = tuple(MountingPoint(**m) for m in fields["mounting_points"])
        return EnvelopeSpec(**fields)
    except (TypeError, KeyError) as exc:
        raise ValueError("Invalid envelope records") from exc
