"""Offline layout outputs for people: drawings, fit and material summaries.

Everything is derived from a planned arrangement (vandesign.arrangement_job)
and its manufacturing profiles. Drawings are SVG in millimetres: a top plan
(X across, Y forward), a front section (X across, Z up; shows sloped upper
walls) and a side elevation (Y forward, Z up). They show the finished lined
interior, wheel arches, keep-outs and every furniture panel. Not CAD
evidence; for review only.
"""
from __future__ import annotations

import math
from xml.sax.saxutils import escape

from .arrangement_job import plan_request
from .modules.test_envelope import ARCHES, REFERENCE

SHEET_MM = (2440.0, 1220.0)
SCALE = 10                    # drawings print at 1:10
_COLOURS = ("#4e79a7", "#f28e2b", "#59a14f", "#e15759", "#76b7b2", "#edc948", "#b07aa1", "#9c755f")
VIEWS = {"top": (0, 1), "front": (0, 2), "side": (1, 2)}
# Edge words per view: (low horizontal, high horizontal, low vertical, high vertical).
_EDGES = {"top": ("left", "right", "rear doors", "front (cab)"),
          "front": ("left", "right", "floor", "ceiling"),
          "side": ("rear doors", "front (cab)", "floor", "ceiling")}


def offline_plan(request):
    """Plan a design request offline (profile modules such as tab-slot cabinets allowed)."""
    return plan_request(request, allow_profile_modules=True)


def _boxes(plan, values=None):
    asm = plan.arrangement.assembly
    env = asm.parameters.resolve(values)
    return {p.stable_id: (p, p.box.resolve(env)) for p in asm.panels}


def _envelope_outline(env, view):
    w, length, _ = env.finished_size
    h = env.heights[0]
    if view == "top":
        return [(0, 0), (w, 0), (w, length), (0, length)]
    if view == "side":
        pts = [(0, 0), (length, 0)]
        for start, end, height in reversed(env.segments):
            pts += [(end, height), (start, height)]
        return pts
    # Front section at the main ceiling height, walking anticlockwise.
    pts = [(0, 0), (w, 0)]
    pts += ([(w, h)] if "right" not in env.upper_walls
            else [(w, env.upper_right_break_mm), (w - env.upper_right_inset_mm, h)])
    pts += ([(0, h)] if "left" not in env.upper_walls
            else [(env.upper_left_inset_mm, h), (0, env.upper_left_break_mm)])
    return pts


def layout_svg(plan, view="top", values=None):
    """SVG drawing of the planned arrangement in one view (mm, origin at the
    left rear corner of the finished floor)."""
    if view not in VIEWS:
        raise ValueError("view must be one of %s" % ", ".join(VIEWS))
    a, b = VIEWS[view]
    env = plan.envelope
    outline = _envelope_outline(env, view)
    width = max(p[0] for p in outline)
    height = max(p[1] for p in outline)
    margin = 280.0
    flip = lambda y: height - y  # noqa: E731  (SVG y grows downward)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="%g %g %g %g" width="%gmm" height="%gmm">'
           % (-margin, -margin, width + 2 * margin, height + 2 * margin, (width + 2 * margin) / SCALE,
              (height + 2 * margin) / SCALE),
           '<title>%s view - %s</title>' % (view, escape(env.provenance)),
           '<polygon points="%s" fill="#f4f1ea" stroke="#333" stroke-width="4"/>'
           % " ".join("%g,%g" % (x, flip(y)) for x, y in outline)]
    boxes = _boxes(plan, values)
    owners = plan.arrangement.owners
    instances = [i.instance_id for i in plan.arrangement.instances]
    for pid, (panel, box) in boxes.items():
        if not pid.startswith(REFERENCE):
            continue
        if pid in ARCHES or pid.startswith(REFERENCE + "keepout."):
            x0, x1, y0, y1 = box.lo[a], box.hi[a], box.lo[b], box.hi[b]
            out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="#bbb" fill-opacity="0.5" '
                       'stroke="#888" stroke-dasharray="20 10" stroke-width="3"><title>%s</title></rect>'
                       % (x0, flip(y1), x1 - x0, y1 - y0, escape(pid)))
    extents = {}
    for pid, (panel, box) in boxes.items():
        if pid.startswith(REFERENCE):
            continue
        owner = owners[pid]
        colour = _COLOURS[instances.index(owner) % len(_COLOURS)]
        x0, x1, y0, y1 = box.lo[a], box.hi[a], box.lo[b], box.hi[b]
        out.append('<rect x="%g" y="%g" width="%g" height="%g" fill="%s" fill-opacity="0.25" stroke="%s" '
                   'stroke-width="2"><title>%s</title></rect>' % (x0, flip(y1), x1 - x0, y1 - y0, colour, colour,
                                                                  escape(pid)))
        lo, hi = extents.get(owner, ((math.inf, math.inf), (-math.inf, -math.inf)))
        extents[owner] = ((min(lo[0], x0), min(lo[1], y0)), (max(hi[0], x1), max(hi[1], y1)))
    placed = []
    for owner, ((x0, y0), (x1, y1)) in extents.items():
        x, y = (x0 + x1) / 2, flip((y0 + y1) / 2)
        while any(abs(x - px) < 500 and abs(y - py) < 70 for px, py in placed):
            y += 75                                     # stacked furniture: keep labels readable
        placed.append((x, y))
        out.append('<text x="%g" y="%g" font-size="60" text-anchor="middle" font-family="sans-serif">%s</text>'
                   % (x, y, escape(owner)))
    lo_h, hi_h, lo_v, hi_v = _EDGES[view]
    for x, y, anchor, word in ((0, height + 40, "start", lo_h), (width, height + 40, "end", hi_h),
                               (-20, height, "end", lo_v), (-20, 40, "end", hi_v)):
        out.append('<text x="%g" y="%g" font-size="40" fill="#666" text-anchor="%s" font-family="sans-serif">'
                   '%s</text>' % (x, y, anchor, escape(word)))
    out.append('<text x="0" y="%g" font-size="70" font-family="sans-serif">%s view, 1:%d: %g x %g mm finished interior</text>'
               % (height + 110, view, SCALE, width, height))
    out.append("</svg>")
    return "\n".join(out)


def fit_summary(plan):
    """Smallest clearance per instance for each inset plane (mm beyond the tolerance)."""
    gaps = plan.arrangement.fit["clearance_to_inset_planes_mm"]
    out = {}
    for pid, g in gaps.items():
        owner = plan.arrangement.owners[pid]
        mine = out.setdefault(owner, {})
        for k, v in g.items():
            mine[k] = min(mine.get(k, math.inf), round(v, 3))
    return out


def material_summary(profiles, sheet_mm=SHEET_MM):
    """Panels grouped by material and thickness, with a sheet-count LOWER BOUND
    (blank area / sheet area; real nesting needs CAM or nesting software)."""
    groups = {}
    for p in profiles:
        (x0, y0), (x1, y1) = p.outline.bounds
        g = groups.setdefault((p.material_ref, round(p.thickness, 3)), dict(panels=0, net_m2=0.0, blank_m2=0.0))
        g["panels"] += 1
        g["net_m2"] += p.net_area_mm2 / 1e6
        g["blank_m2"] += (x1 - x0) * (y1 - y0) / 1e6
    sheet = sheet_mm[0] * sheet_mm[1] / 1e6
    return [dict(material=m, thickness_mm=t, panels=g["panels"], net_area_m2=round(g["net_m2"], 3),
                 blank_area_m2=round(g["blank_m2"], 3), sheets_lower_bound=math.ceil(g["blank_m2"] / sheet))
            for (m, t), g in sorted(groups.items())]
