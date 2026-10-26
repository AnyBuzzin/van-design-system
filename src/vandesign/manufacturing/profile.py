"""Closed 2D loops of lines and arcs, CNC relief, and flat panel profiles.

Panel-local frame: X/Y in the sheet plane, millimetres, origin at the lower-left
corner of the enclosing blank. Material outlines run counter-clockwise
(material on the left); cut loops also run counter-clockwise (waste inside).
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Tuple

# Geometry built here is exact up to trigonometric round-off; loops must close
# within this distance. It is a construction check, not a shop tolerance.
CLOSURE_TOL_MM = 1e-6

Point = Tuple[float, float]


class ProfileError(ValueError):
    """Manufacturing geometry is invalid or not representable."""


def _finite_point(p) -> Point:
    if (not isinstance(p, (tuple, list)) or len(p) != 2
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in p)):
        raise ProfileError("Finite 2D point required, got %r" % (p,))
    return (float(p[0]), float(p[1]))


@dataclass(frozen=True)
class Line:
    start: Point
    end: Point

    def __post_init__(self):
        object.__setattr__(self, "start", _finite_point(self.start))
        object.__setattr__(self, "end", _finite_point(self.end))
        if math.dist(self.start, self.end) <= CLOSURE_TOL_MM:
            raise ProfileError("Zero-length line at %r" % (self.start,))

    def area_term(self) -> float:
        (x1, y1), (x2, y2) = self.start, self.end
        return 0.5 * (x1 * y2 - x2 * y1)

    def sample(self):
        return (self.start, self.end)


@dataclass(frozen=True)
class Arc:
    """Circular arc: centre, radius, start angle and signed sweep (radians)."""
    center: Point
    radius: float
    start_angle: float
    sweep: float

    def __post_init__(self):
        object.__setattr__(self, "center", _finite_point(self.center))
        for v in (self.radius, self.start_angle, self.sweep):
            if type(v) not in (int, float) or not math.isfinite(v):
                raise ProfileError("Finite arc values required")
        if self.radius <= 0 or not 0 < abs(self.sweep) < 2 * math.pi:
            raise ProfileError("Arc needs positive radius and 0 < |sweep| < 2*pi")

    def _point(self, angle) -> Point:
        cx, cy = self.center
        return (cx + self.radius * math.cos(angle), cy + self.radius * math.sin(angle))

    @property
    def start(self) -> Point:
        return self._point(self.start_angle)

    @property
    def end(self) -> Point:
        return self._point(self.start_angle + self.sweep)

    def area_term(self) -> float:
        # Green's theorem: 0.5 * integral(x dy - y dx) along the arc.
        (cx, cy), r = self.center, self.radius
        a1, a2 = self.start_angle, self.start_angle + self.sweep
        return 0.5 * (r * (cx * (math.sin(a2) - math.sin(a1)) - cy * (math.cos(a2) - math.cos(a1)))
                      + r * r * self.sweep)

    def sample(self, step=math.pi / 36):
        n = max(2, int(math.ceil(abs(self.sweep) / step)) + 1)
        return tuple(self._point(self.start_angle + self.sweep * i / (n - 1)) for i in range(n))


@dataclass(frozen=True)
class Loop:
    """Closed, counter-clockwise sequence of line/arc segments."""
    segments: tuple

    def __post_init__(self):
        segs = tuple(self.segments)
        if len(segs) < 2 or any(type(s) not in (Line, Arc) for s in segs):
            raise ProfileError("Loop needs at least two Line/Arc segments")
        for a, b in zip(segs, segs[1:] + segs[:1]):
            if math.dist(a.end, b.start) > CLOSURE_TOL_MM:
                raise ProfileError("Loop is not closed between %r and %r" % (a.end, b.start))
        object.__setattr__(self, "segments", segs)
        if self.area <= CLOSURE_TOL_MM:
            raise ProfileError("Loop must be counter-clockwise with positive area")

    @property
    def area(self) -> float:
        return sum(s.area_term() for s in self.segments)

    def points(self):
        out = []
        for s in self.segments:
            out.extend(s.sample()[:-1])
        return tuple(out)

    @property
    def bounds(self):
        pts = self.points()
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return (min(xs), min(ys)), (max(xs), max(ys))


def _turn(d1, d2):
    return d1[0] * d2[1] - d1[1] * d2[0]


# --------------------------------------------------------------- containment
_SAMPLE_STEP = math.radians(2)
_RAY_ANGLES = (0.3721, 1.1093, 2.0517, 2.7183, 4.0411, 5.3337)


def _arc_param(seg, q):
    """Fraction (0..1) along ``seg`` of a point ``q`` on its circle, or None."""
    theta = math.atan2(q[1] - seg.center[1], q[0] - seg.center[0])
    rel = ((theta - seg.start_angle) * math.copysign(1, seg.sweep)) % (2 * math.pi)
    return rel / abs(seg.sweep) if rel <= abs(seg.sweep) + 1e-12 else None


def _distance(p, seg):
    if isinstance(seg, Line):
        (ax, ay), (bx, by) = seg.start, seg.end
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)
    d = math.dist(p, seg.center)
    if d > 0 and _arc_param(seg, (seg.center[0] + (p[0] - seg.center[0]) * seg.radius / d,
                                  seg.center[1] + (p[1] - seg.center[1]) * seg.radius / d)) is not None:
        return abs(d - seg.radius)
    return min(math.dist(p, seg.start), math.dist(p, seg.end))


def boundary_distance(p, loop):
    return min(_distance(p, s) for s in loop.segments)


def _crossings(p, loop, angle):
    """Ray crossings from p, or None when the ray grazes a vertex or tangent."""
    d = (math.cos(angle), math.sin(angle))
    count = 0
    for seg in loop.segments:
        if isinstance(seg, Line):
            (ax, ay), (bx, by) = seg.start, seg.end
            ex, ey = bx - ax, by - ay
            den = d[0] * ey - d[1] * ex
            if abs(den) < 1e-15:
                continue
            wx, wy = ax - p[0], ay - p[1]
            t = (wx * ey - wy * ex) / den
            s = (wx * d[1] - wy * d[0]) / den
            if t > 1e-12 and -1e-9 <= s <= 1 + 1e-9:
                if s < 1e-9 or s > 1 - 1e-9:
                    return None
                count += 1
        else:
            fx, fy = p[0] - seg.center[0], p[1] - seg.center[1]
            b = d[0] * fx + d[1] * fy
            disc = b * b - (fx * fx + fy * fy - seg.radius ** 2)
            if disc < -1e-12:
                continue
            if abs(disc) <= 1e-12:
                return None
            for t in (-b - math.sqrt(disc), -b + math.sqrt(disc)):
                if t <= 1e-12:
                    continue
                f = _arc_param(seg, (p[0] + t * d[0], p[1] + t * d[1]))
                if f is None:
                    continue
                if f < 1e-9 or f > 1 - 1e-9:
                    return None
                count += 1
    return count


def contains_point(loop, p):
    """Exact: True inside, False outside (points on the boundary are not resolved)."""
    for angle in _RAY_ANGLES:
        n = _crossings(p, loop, angle)
        if n is not None:
            return n % 2 == 1
    raise ProfileError("Could not classify point %r" % (p,))


def _samples(loop):
    out = []
    for s in loop.segments:
        out.extend(s.sample(_SAMPLE_STEP) if isinstance(s, Arc) else s.sample())
    return out


def _circle_samples(center, radius):
    n = int(2 * math.pi / _SAMPLE_STEP)
    return [(center[0] + radius * math.cos(2 * math.pi * i / n),
             center[1] + radius * math.sin(2 * math.pi * i / n)) for i in range(n)]


def check_contained(outline, boundary_points, inner_loop=None, *, may_touch):
    """Feature boundary inside the outline material; the outline never inside the feature.

    ``may_touch`` allows boundary contact (open pockets); through-cuts and
    holes must stay clear of the outline, since an edge-touching through-cut
    is a notch and belongs in the outline itself.
    """
    for q in boundary_points:
        gap = boundary_distance(q, outline)
        if gap <= CLOSURE_TOL_MM:
            if not may_touch:
                return "touches the outline (model it as a notch in the outline)"
            continue
        if not contains_point(outline, q):
            return "lies outside the outline material"
    if inner_loop is not None:
        for q in _samples(outline):
            if boundary_distance(q, inner_loop) > CLOSURE_TOL_MM and contains_point(inner_loop, q):
                return "contains part of the outline"
    return None


def polygon_loop(vertices, *, waste_inside, relief_radius=None, open_points=()):
    """Counter-clockwise loop through axis-aligned ``vertices``.

    With ``relief_radius`` every 90-degree corner where the waste side is the
    narrow 90-degree wedge gets dog-bone relief: an arc of the tool radius whose
    centre lies on the waste bisector, at distance r from the corner, so a round
    tool reaches the sharp corner a mating part needs. Corners listed in
    ``open_points`` (e.g. on an open pocket edge) are left unrelieved.
    """
    pts = [_finite_point(v) for v in vertices]
    if len(pts) < 4:
        raise ProfileError("Polygon needs at least four vertices")
    n = len(pts)
    signed = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    if signed <= 0:
        raise ProfileError("Polygon vertices must be counter-clockwise")
    r = relief_radius
    if r is not None and (type(r) not in (int, float) or not math.isfinite(r) or r <= 0):
        raise ProfileError("Relief radius must be finite and positive")
    open_set = [_finite_point(p) for p in open_points]

    corners = []  # (vertex, incoming unit, outgoing unit, relieved)
    for i in range(n):
        prev, v, nxt = pts[i - 1], pts[i], pts[(i + 1) % n]
        d1 = (v[0] - prev[0], v[1] - prev[1])
        d2 = (nxt[0] - v[0], nxt[1] - v[1])
        if (d1[0] and d1[1]) or (d2[0] and d2[1]) or d1 == (0, 0) or d2 == (0, 0):
            raise ProfileError("Relief polygons must be axis-aligned without repeated vertices")
        u1 = (math.copysign(1, d1[0]) if d1[0] else 0.0, math.copysign(1, d1[1]) if d1[1] else 0.0)
        u2 = (math.copysign(1, d2[0]) if d2[0] else 0.0, math.copysign(1, d2[1]) if d2[1] else 0.0)
        turn = _turn(u1, u2)
        if turn == 0:
            raise ProfileError("Collinear vertex at %r" % (v,))
        # Waste is inside a cut loop (left of travel) and outside an outline.
        narrow_waste = (turn > 0) if waste_inside else (turn < 0)
        is_open = any(math.dist(v, p) <= CLOSURE_TOL_MM for p in open_set)
        corners.append((v, u1, u2, bool(r) and narrow_waste and not is_open))

    if r is None:
        return Loop(tuple(Line(pts[i], pts[(i + 1) % n]) for i in range(n)))

    reach = r * math.sqrt(2)  # where the relief circle crosses each edge
    entry, exit_ = [], []
    for v, u1, u2, relieved in corners:
        if relieved:
            entry.append((v[0] - reach * u1[0], v[1] - reach * u1[1]))
            exit_.append((v[0] + reach * u2[0], v[1] + reach * u2[1]))
        else:
            entry.append(v)
            exit_.append(v)
    segments = []
    for i, (v, u1, u2, relieved) in enumerate(corners):
        if relieved:
            bis = ((u2[0] - u1[0]) / math.sqrt(2), (u2[1] - u1[1]) / math.sqrt(2))
            c = (v[0] + r * bis[0], v[1] + r * bis[1])
            a_in = math.atan2(entry[i][1] - c[1], entry[i][0] - c[0])
            # Half-turn through the corner: counter-clockwise inside a cut loop,
            # clockwise for an outline, so the arc always bulges into material.
            segments.append(Arc(c, r, a_in, math.pi if waste_inside else -math.pi))
        j = (i + 1) % n
        if math.dist(exit_[i], entry[j]) <= CLOSURE_TOL_MM:
            raise ProfileError("Edge too short for dog-bone relief near %r" % (v,))
        if _dot((entry[j][0] - exit_[i][0], entry[j][1] - exit_[i][1]), u2) <= 0:
            raise ProfileError("Dog-bone relief circles overlap near %r" % (v,))
        segments.append(Line(exit_[i], entry[j]))
    return Loop(tuple(segments))


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def rect_vertices(x0, y0, x1, y1):
    if not (x1 > x0 and y1 > y0):
        raise ProfileError("Rectangle needs positive size")
    return ((x0, y0), (x1, y0), (x1, y1), (x0, y1))


def rounded_corner_outline(width, length, radius):
    """E1.1 family: rectangle with one upper-right quarter-circle corner."""
    if not 0 < radius < min(width, length):
        raise ProfileError("Require 0 < radius < min(width, length)")
    w, l, r = float(width), float(length), float(radius)
    return Loop((Line((0, 0), (w, 0)), Line((w, 0), (w, l - r)),
                 Arc((w - r, l - r), r, 0.0, math.pi / 2),
                 Line((w - r, l), (0, l)), Line((0, l), (0, 0))))


@dataclass(frozen=True)
class ThroughCut:
    loop: Loop


@dataclass(frozen=True)
class Pocket:
    loop: Loop
    depth: float
    face: str  # 'top' (+thickness face) or 'bottom'

    def __post_init__(self):
        if self.face not in ("top", "bottom"):
            raise ProfileError("Pocket face must be 'top' or 'bottom'")
        if type(self.depth) not in (int, float) or not math.isfinite(self.depth) or self.depth <= 0:
            raise ProfileError("Pocket depth must be finite and positive")


@dataclass(frozen=True)
class Hole:
    center: Point
    diameter: float
    depth: float | None = None  # None = through
    face: str = "top"

    def __post_init__(self):
        object.__setattr__(self, "center", _finite_point(self.center))
        if type(self.diameter) not in (int, float) or not math.isfinite(self.diameter) or self.diameter <= 0:
            raise ProfileError("Hole diameter must be finite and positive")
        if self.depth is not None and (type(self.depth) not in (int, float)
                                       or not math.isfinite(self.depth) or self.depth <= 0):
            raise ProfileError("Hole depth must be finite and positive")
        if self.face not in ("top", "bottom"):
            raise ProfileError("Hole face must be 'top' or 'bottom'")


@dataclass(frozen=True)
class PanelProfile:
    panel_id: str
    display_name: str
    material_ref: str
    thickness: float
    outline: Loop
    features: tuple = ()
    reliefs: int = 0      # dog-bone arcs added for manufacture
    notes: tuple = ()     # e.g. why this differs from the CAD body

    def __post_init__(self):
        t = self.thickness
        if type(t) not in (int, float) or not math.isfinite(t) or t <= 0:
            raise ProfileError("%s: thickness must be finite and positive" % self.panel_id)
        for f in self.features:
            if type(f) not in (ThroughCut, Pocket, Hole):
                raise ProfileError("%s: unknown feature %r" % (self.panel_id, f))
            if isinstance(f, Hole):
                r = f.diameter / 2
                circle = Loop((Arc(f.center, r, 0.0, math.pi), Arc(f.center, r, math.pi, math.pi)))
                problem = check_contained(self.outline, _circle_samples(f.center, r), circle,
                                          may_touch=False)
            else:
                problem = check_contained(self.outline, _samples(f.loop), f.loop,
                                          may_touch=isinstance(f, Pocket))
            if problem:
                raise ProfileError("%s: %s %s" % (self.panel_id, type(f).__name__, problem))
            depth = f.depth if isinstance(f, Pocket) else (f.depth if isinstance(f, Hole) else None)
            if depth is not None and depth >= t:
                raise ProfileError("%s: blind depth must be less than the thickness" % self.panel_id)
        object.__setattr__(self, "features", tuple(self.features))
        object.__setattr__(self, "notes", tuple(self.notes))

    @property
    def net_area_mm2(self):
        through = sum(f.loop.area for f in self.features if isinstance(f, ThroughCut))
        through += sum(math.pi * (f.diameter / 2) ** 2 for f in self.features
                       if isinstance(f, Hole) and f.depth is None)
        return self.outline.area - through

    @property
    def volume_mm3(self):
        """Finished volume, assuming features do not overlap each other."""
        blind = sum(f.loop.area * f.depth for f in self.features if isinstance(f, Pocket))
        blind += sum(math.pi * (f.diameter / 2) ** 2 * f.depth for f in self.features
                     if isinstance(f, Hole) and f.depth is not None)
        return self.net_area_mm2 * self.thickness - blind

    @property
    def faces_machined(self):
        return tuple(sorted({f.face for f in self.features if isinstance(f, (Pocket, Hole))
                             and not (isinstance(f, Hole) and f.depth is None)}))
