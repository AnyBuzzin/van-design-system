"""Convert box-panel assemblies (and their owned cuts) into PanelProfiles.

Each panel's thinnest box axis is its sheet thickness. The 2D view looks at the
machined face: local axes are right-handed about that face's outward normal,
so a part cut from the drawing is never a mirror image of the CAD part.
"""
from __future__ import annotations

from contextlib import contextmanager
import math

from ..core.expr import Mm
from ..core.geometry import Box, GeometryError
from .profile import (CLOSURE_TOL_MM, Arc, Pocket, PanelFrame, PanelProfile, ProfileError,
                      ThroughCut, polygon_loop_with_sources, rect_vertices, rounded_corner_outline)

_EPS = CLOSURE_TOL_MM
_decisions = None


def _number(x):
    return type(x) in (int, float) or isinstance(x, Tracked)


def expr_of(x):
    """The Expr behind a coordinate: its provenance, or a constant."""
    return x.expr if isinstance(x, Tracked) else Mm(float(x))


class Tracked(float):
    """A millimetre value that keeps the Expr it was built from (#95 bindings).

    It is the same float, so the profile code runs unchanged and its numbers
    are bit-identical; the Expr follows +, - and scaling by plain numbers.
    Products of two coordinates (proof volumes) drop to plain floats. While
    ``recording_decisions`` is active every comparison is logged as an Expr
    pair, so a caller can prove each value-based decision holds over a range.
    """

    def __new__(cls, value, expr):
        obj = float.__new__(cls, value)
        obj.expr = expr
        return obj

    def __add__(self, o):
        return Tracked(float.__add__(self, o), self.expr + expr_of(o)) if _number(o) else NotImplemented

    def __radd__(self, o):
        return Tracked(float.__radd__(self, o), expr_of(o) + self.expr) if _number(o) else NotImplemented

    def __sub__(self, o):
        return Tracked(float.__sub__(self, o), self.expr - expr_of(o)) if _number(o) else NotImplemented

    def __rsub__(self, o):
        return Tracked(float.__rsub__(self, o), expr_of(o) - self.expr) if _number(o) else NotImplemented

    def __neg__(self):
        return Tracked(float.__neg__(self), -self.expr)

    def __pos__(self):
        return self

    def __abs__(self):
        return self if self >= 0 else -self

    def __mul__(self, o):
        if isinstance(o, Tracked) or not _number(o):
            return float.__mul__(self, o)
        return Tracked(float.__mul__(self, o), self.expr * o)

    def __rmul__(self, o):
        return Tracked(float.__rmul__(self, o), self.expr * o) if _number(o) else NotImplemented

    def __truediv__(self, o):
        if isinstance(o, Tracked) or not _number(o):
            return float.__truediv__(self, o)
        return Tracked(float.__truediv__(self, o), self.expr / o)

    def _log(self, o):
        if _decisions is not None and _number(o):
            _decisions.append((self.expr, expr_of(o)))

    def __lt__(self, o):
        self._log(o)
        return float.__lt__(self, o)

    def __le__(self, o):
        self._log(o)
        return float.__le__(self, o)

    def __gt__(self, o):
        self._log(o)
        return float.__gt__(self, o)

    def __ge__(self, o):
        self._log(o)
        return float.__ge__(self, o)

    def __eq__(self, o):
        self._log(o)
        return float.__eq__(self, o)

    def __ne__(self, o):
        self._log(o)
        return float.__ne__(self, o)

    __hash__ = float.__hash__


@contextmanager
def recording_decisions():
    """Log every Tracked comparison made inside the block as (Expr, Expr)."""
    global _decisions
    previous, _decisions = _decisions, []
    try:
        yield _decisions
    finally:
        _decisions = previous


def tracked_box(box_expr, env):
    """``BoxExpr.resolve`` with Tracked coordinates (the same numbers)."""
    lo = tuple(Tracked(e.eval(env), e) for e in box_expr.origin)
    size = tuple(Tracked(e.eval(env), e) for e in box_expr.size)
    if any(s <= 0 for s in size):
        raise GeometryError("non-positive box size %r" % (size,))
    return Box(lo, tuple(a + b for a, b in zip(lo, size)))


def _resolve(box_expr, env):
    return box_expr.resolve(env)


def _thickness_axis(box):
    size = box.size
    t = min(range(3), key=lambda i: size[i])
    if sum(1 for s in size if abs(s - size[t]) <= _EPS) != 1:
        raise ProfileError("Ambiguous sheet thickness for box size %r" % (size,))
    return t


def rectilinear_outline(width, height, notches):
    """Vertices (CCW) of a width x height rectangle minus edge-touching notches."""
    # Tracked sizes stay Tracked (they are floats); other numbers are normalised.
    width = width if isinstance(width, float) else float(width)
    height = height if isinstance(height, float) else float(height)
    xs, ys = {0.0, width}, {0.0, height}
    clipped = []
    for x0, y0, x1, y1 in notches:
        x0, y0, x1, y1 = max(x0, 0.0), max(y0, 0.0), min(x1, width), min(y1, height)
        if x1 - x0 <= _EPS or y1 - y0 <= _EPS:
            continue
        clipped.append((x0, y0, x1, y1))
        xs.update((x0, x1))
        ys.update((y0, y1))
    xs, ys = sorted(xs), sorted(ys)

    def material(i, j):
        if not (0 <= i < len(xs) - 1 and 0 <= j < len(ys) - 1):
            return False
        cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
        return not any(x0 < cx < x1 and y0 < cy < y1 for x0, y0, x1, y1 in clipped)

    edges = {}
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            if not material(i, j):
                continue
            a, b, c, d = (xs[i], ys[j]), (xs[i + 1], ys[j]), (xs[i + 1], ys[j + 1]), (xs[i], ys[j + 1])
            for (p, q), (di, dj) in (((a, b), (0, -1)), ((b, c), (1, 0)),
                                     ((c, d), (0, 1)), ((d, a), (-1, 0))):
                if not material(i + di, j + dj):
                    if p in edges:
                        raise ProfileError("Notches pinch the outline at %r" % (p,))
                    edges[p] = q
    if not edges:
        raise ProfileError("Notches remove the whole panel")
    start = min(edges)
    loop, p = [start], edges[start]
    while p != start:
        loop.append(p)
        p = edges[p]
        if len(loop) > len(edges):
            raise ProfileError("Outline tracing failed")
    if len(loop) != len(edges):
        raise ProfileError("Notches split the panel into separate pieces")
    # Drop collinear vertices.
    out = []
    for k, v in enumerate(loop):
        prev, nxt = loop[k - 1], loop[(k + 1) % len(loop)]
        if not ((prev[0] == v[0] == nxt[0]) or (prev[1] == v[1] == nxt[1])):
            out.append(v)
    return tuple(out)


def _on_boundary(p, w, h):
    return (abs(p[0]) <= _EPS or abs(p[1]) <= _EPS
            or abs(p[0] - w) <= _EPS or abs(p[1] - h) <= _EPS)


def _touches_boundary(rect, w, h):
    x0, y0, x1, y1 = rect
    return x0 <= _EPS or y0 <= _EPS or x1 >= w - _EPS or y1 >= h - _EPS


def _count_arcs(loop):
    return sum(1 for s in loop.segments if isinstance(s, Arc))


def _loop(verts, loops, **kw):
    """polygon_loop on plain numbers; ``loops`` (a list, or None) receives
    the vertices as given (Tracked when the boxes are) and the sources."""
    loop, sources = polygon_loop_with_sources(
        [(float(a), float(b)) for a, b in verts],
        **dict(kw, open_points=[(float(a), float(b)) for a, b in kw.get("open_points", ())]))
    if loops is not None:
        loops.append((tuple(verts), sources))
    return loop


def panel_profile(panel, box, cuts, *, tool_diameter=None, relief=True, corner_radius=None):
    """Profile of one box panel minus ``cuts`` (world-frame Boxes it owns)."""
    return _panel_profile(panel, box, cuts, tool_diameter, relief, corner_radius, None)


def _panel_profile(panel, box, cuts, tool_diameter, relief, corner_radius, capture):
    """``capture`` (a dict, or None) receives the outline and feature loops
    (outline first), each feature's (kind, face, depth), the frame origin and
    the thickness, as computed from the given boxes."""
    if relief and (type(tool_diameter) not in (int, float) or not math.isfinite(tool_diameter)
                   or tool_diameter <= 0):
        raise ProfileError("A positive tool diameter is required for dog-bone relief")
    r = tool_diameter / 2 if relief else None
    t = _thickness_axis(box)
    u, v = (t + 1) % 3, (t + 2) % 3
    thick = box.size[t]

    classified = []
    for cut in cuts:
        part = box.intersection(cut)
        if part is None:
            raise ProfileError("%s: owned cut does not intersect the panel" % panel.stable_id)
        lo_t, hi_t = part.lo[t] - box.lo[t], part.hi[t] - box.lo[t]
        if lo_t <= _EPS and hi_t >= thick - _EPS:
            kind, face, depth = "through", None, None
        elif hi_t >= thick - _EPS:
            kind, face, depth = "pocket", "top", thick - lo_t
        elif lo_t <= _EPS:
            kind, face, depth = "pocket", "bottom", hi_t
        else:
            raise ProfileError("%s: internal void cannot be machined" % panel.stable_id)
        rect = (part.lo[u] - box.lo[u], part.lo[v] - box.lo[v],
                part.hi[u] - box.lo[u], part.hi[v] - box.lo[v])
        classified.append((kind, face, depth, rect))

    w, h = box.size[u], box.size[v]
    faces = {face for kind, face, _, _ in classified if kind == "pocket"}
    if faces == {"bottom"}:
        # View from the machined face instead: swapping axes is that reflection.
        w, h = h, w
        classified = [(k, "top" if f else None, d, (r_[1], r_[0], r_[3], r_[2]))
                      for k, f, d, r_ in classified]
    notes = []
    if faces == {"top", "bottom"}:
        notes.append("machined on both faces: flip required; bottom features drawn as seen through the top face")

    notches = [rect for kind, _, _, rect in classified
               if kind == "through" and _touches_boundary(rect, w, h)]
    features, reliefs, kinds = [], 0, []
    loops = [] if capture is not None else None
    if corner_radius is not None:
        if notches or faces == {"bottom"} or t != 2:
            raise ProfileError("%s: rounded outline supports interior features only" % panel.stable_id)
        outline = rounded_corner_outline(w, h, corner_radius)
        if loops is not None:
            loops.append(None)              # no vertex provenance for a rounded outline
    elif notches:
        outline = _loop(rectilinear_outline(w, h, notches), loops, waste_inside=False, relief_radius=r)
        reliefs += _count_arcs(outline)
    else:
        outline = _loop(rect_vertices(0.0, 0.0, w, h), loops, waste_inside=False)

    for kind, face, depth, rect in classified:
        if kind == "through" and rect in notches:
            continue
        verts = rect_vertices(*rect)
        open_pts = [p for p in verts if _on_boundary(p, w, h)]
        loop = _loop(verts, loops, waste_inside=True, relief_radius=r, open_points=open_pts)
        reliefs += _count_arcs(loop)
        features.append(ThroughCut(loop) if kind == "through" else Pocket(loop, float(depth), face))
        kinds.append((kind, face, depth))
    if reliefs:
        notes.append("dog-bone relief for a %.3f mm tool added at %d inside corner(s); "
                     "not present in the CAD body" % (tool_diameter, reliefs))
    e = [tuple(1.0 if i == k else 0.0 for i in range(3)) for k in range(3)]
    if faces == {"bottom"}:
        # Viewed from the old bottom face: a runs along v, b along u, c downwards.
        origin = tuple(box.hi[k] if k == t else box.lo[k] for k in range(3))
        frame = PanelFrame(tuple(map(float, origin)), e[v], e[u], tuple(-x for x in e[t]))
    else:
        origin = box.lo
        frame = PanelFrame(tuple(map(float, origin)), e[u], e[v], e[t])
    if capture is not None:
        capture.update(loops=loops, features=kinds, origin=origin, thickness=thick)
    return PanelProfile(panel.stable_id, panel.display_name, panel.material_ref, float(thick),
                        outline, tuple(features), reliefs, tuple(notes), frame)


def assembly_profiles(assembly, values=None, *, tool_diameter=None, relief=True, extra_cuts=(),
                      box_overrides=None):
    """Profiles for every panel of ``assembly`` at the given base-parameter values.

    Owned cuts come from the assembly's DadoOperations plus ``extra_cuts``
    (``(target_panel_id, world Box)`` pairs) for modules whose cuts are not
    dado operations. A cut is assigned only to its named target panel.
    ``box_overrides`` (panel id -> world Box) replaces a panel blank, e.g. a
    panel extended by joint tabs.
    """
    return _assembly_profiles(assembly, values, tool_diameter, relief, extra_cuts, box_overrides, _resolve, None)


def _assembly_profiles(assembly, values, tool_diameter, relief, extra_cuts, box_overrides, resolve, captures,
                       cut_overrides=None):
    """``resolve`` turns a BoxExpr into a Box (plain, or ``tracked_box``);
    ``captures`` (a dict, or None) receives each panel's capture by id;
    ``cut_overrides`` (operation id -> world Box) replaces a dado's cut, e.g.
    a stopped dado."""
    env = assembly.parameters.resolve(values)
    boxes = {p.stable_id: resolve(p.box, env) for p in assembly.panels}
    for pid, box in (box_overrides or {}).items():
        if pid not in boxes or type(box) is not Box:
            raise ProfileError("Box override must name a known panel and a Box")
        boxes[pid] = box
    cut_overrides = dict(cut_overrides or {})
    owned = {pid: [] for pid in boxes}
    for op in assembly.operations:
        cut = cut_overrides.pop(op.operation_id, None)
        if cut is not None and type(cut) is not Box:
            raise ProfileError("Cut override must be a Box")
        owned[op.target_panel_id].append(resolve(op.cut, env) if cut is None else cut)
    if cut_overrides:
        raise ProfileError("Cut override names an unknown operation: %s" % ", ".join(sorted(cut_overrides)))
    for pid, cut in extra_cuts:
        if pid not in owned or type(cut) is not Box:
            raise ProfileError("Extra cut must name a known panel and a Box")
        owned[pid].append(cut)
    out = []
    for p in assembly.panels:
        if p.material_ref == "reference_only":
            continue  # envelope guides and keep-outs are never manufactured
        radius = p.corner_radius.eval(env) if p.corner_radius is not None else None
        capture = None if captures is None else captures.setdefault(p.stable_id, {})
        out.append(_panel_profile(p, boxes[p.stable_id], owned[p.stable_id], tool_diameter, relief, radius,
                                  capture))
    return tuple(out)
