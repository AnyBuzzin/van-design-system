"""Convert box-panel assemblies (and their owned cuts) into PanelProfiles.

Each panel's thinnest box axis is its sheet thickness. The 2D view looks at the
machined face: local axes are right-handed about that face's outward normal,
so a part cut from the drawing is never a mirror image of the CAD part.
"""
from __future__ import annotations

import math

from ..core.geometry import Box
from .profile import (CLOSURE_TOL_MM, Arc, Pocket, PanelProfile, ProfileError,
                      ThroughCut, polygon_loop, rect_vertices, rounded_corner_outline)

_EPS = CLOSURE_TOL_MM


def _thickness_axis(box):
    size = box.size
    t = min(range(3), key=lambda i: size[i])
    if sum(1 for s in size if abs(s - size[t]) <= _EPS) != 1:
        raise ProfileError("Ambiguous sheet thickness for box size %r" % (size,))
    return t


def rectilinear_outline(width, height, notches):
    """Vertices (CCW) of a width x height rectangle minus edge-touching notches."""
    xs, ys = {0.0, float(width)}, {0.0, float(height)}
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


def panel_profile(panel, box, cuts, *, tool_diameter=None, relief=True, corner_radius=None):
    """Profile of one box panel minus ``cuts`` (world-frame Boxes it owns)."""
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
    features, reliefs = [], 0
    if corner_radius is not None:
        if notches or faces == {"bottom"} or t != 2:
            raise ProfileError("%s: rounded outline supports interior features only" % panel.stable_id)
        outline = rounded_corner_outline(w, h, corner_radius)
    elif notches:
        outline = polygon_loop(rectilinear_outline(w, h, notches), waste_inside=False, relief_radius=r)
        reliefs += _count_arcs(outline)
    else:
        outline = polygon_loop(rect_vertices(0.0, 0.0, w, h), waste_inside=False)

    for kind, face, depth, rect in classified:
        if kind == "through" and rect in notches:
            continue
        verts = rect_vertices(*rect)
        open_pts = [p for p in verts if _on_boundary(p, w, h)]
        loop = polygon_loop(verts, waste_inside=True, relief_radius=r, open_points=open_pts)
        reliefs += _count_arcs(loop)
        features.append(ThroughCut(loop) if kind == "through" else Pocket(loop, depth, face))
    if reliefs:
        notes.append("dog-bone relief for a %.3f mm tool added at %d inside corner(s); "
                     "not present in the CAD body" % (tool_diameter, reliefs))
    return PanelProfile(panel.stable_id, panel.display_name, panel.material_ref, thick,
                        outline, tuple(features), reliefs, tuple(notes))


def assembly_profiles(assembly, values=None, *, tool_diameter=None, relief=True, extra_cuts=()):
    """Profiles for every panel of ``assembly`` at the given base-parameter values.

    Owned cuts come from the assembly's DadoOperations plus ``extra_cuts``
    (``(target_panel_id, world Box)`` pairs) for modules whose cuts are not
    dado operations. A cut is assigned only to its named target panel.
    """
    env = assembly.parameters.resolve(values)
    boxes = {p.stable_id: p.box.resolve(env) for p in assembly.panels}
    owned = {pid: [] for pid in boxes}
    for op in assembly.operations:
        owned[op.target_panel_id].append(op.cut.resolve(env))
    for pid, cut in extra_cuts:
        if pid not in owned or type(cut) is not Box:
            raise ProfileError("Extra cut must name a known panel and a Box")
        owned[pid].append(cut)
    out = []
    for p in assembly.panels:
        if p.material_ref == "reference_only":
            continue  # envelope guides and keep-outs are never manufactured
        radius = p.corner_radius.eval(env) if p.corner_radius is not None else None
        out.append(panel_profile(p, boxes[p.stable_id], owned[p.stable_id],
                                 tool_diameter=tool_diameter, relief=relief, corner_radius=radius))
    return tuple(out)
