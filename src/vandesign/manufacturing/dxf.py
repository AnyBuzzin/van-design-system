"""Minimal DXF (R12, millimetres) writer and reader for PanelProfiles.

One file per panel, drawn as seen from its machined ("top") face, with
layers that downstream CAM/nesting maps to operations:

    OUTLINE                 cut outside the line, full depth
    THROUGH                 cut inside the line, full depth
    POCKET_TOP_<d>MM        pocket to depth d from the top face (d: 6_00 = 6.00)
    POCKET_BOTTOM_<d>MM     pocket from the bottom face (flip; drawn see-through)
    DRILL_THROUGH / DRILL_<FACE>_<d>MM
    LABEL                   panel id text only; never cut

Only LINE, ARC, CIRCLE and TEXT entities are written: the subset every common
CAM and nesting tool reads. The reader exists to verify written files
independently of the writer's in-memory geometry.
"""
from __future__ import annotations

import csv
import io
import math
import os

from .profile import Arc, Hole, Line, Pocket, ThroughCut

OUTLINE, THROUGH, LABEL = "OUTLINE", "THROUGH", "LABEL"
_COLOURS = {OUTLINE: 7, THROUGH: 1, LABEL: 8}


def _depth_tag(depth):
    return ("%.2f" % depth).replace(".", "_") + "MM"


def pocket_layer(face, depth):
    return "POCKET_%s_%s" % (face.upper(), _depth_tag(depth))


def drill_layer(hole):
    return "DRILL_THROUGH" if hole.depth is None else "DRILL_%s_%s" % (hole.face.upper(), _depth_tag(hole.depth))


def _num(v):
    s = "%.6f" % v
    return "0.000000" if s == "-0.000000" else s


def _entities(profile):
    out = [(OUTLINE, profile.outline)]
    for f in profile.features:
        if isinstance(f, ThroughCut):
            out.append((THROUGH, f.loop))
        elif isinstance(f, Pocket):
            out.append((pocket_layer(f.face, f.depth), f.loop))
        elif isinstance(f, Hole):
            out.append((drill_layer(f), f))
    return out


def dxf_text(profile):
    """DXF text for one PanelProfile."""
    items = _entities(profile)
    layers = sorted({layer for layer, _ in items} | {LABEL})
    (x0, y0), (x1, y1) = profile.outline.bounds
    w = []

    def g(code, value):
        w.append("%d\n%s\n" % (code, value))

    g(0, "SECTION"); g(2, "HEADER")
    g(9, "$ACADVER"); g(1, "AC1009")
    g(9, "$INSUNITS"); g(70, 4)
    g(9, "$EXTMIN"); g(10, _num(x0)); g(20, _num(y0))
    g(9, "$EXTMAX"); g(10, _num(x1)); g(20, _num(y1))
    g(0, "ENDSEC")
    g(0, "SECTION"); g(2, "TABLES")
    g(0, "TABLE"); g(2, "LTYPE"); g(70, 1)
    g(0, "LTYPE"); g(2, "CONTINUOUS"); g(70, 0); g(3, "Solid line"); g(72, 65); g(73, 0); g(40, "0.0")
    g(0, "ENDTAB")
    g(0, "TABLE"); g(2, "LAYER"); g(70, len(layers))
    for name in layers:
        colour = _COLOURS.get(name, 5 if name.startswith("POCKET") else 3)
        g(0, "LAYER"); g(2, name); g(70, 0); g(62, colour); g(6, "CONTINUOUS")
    g(0, "ENDTAB")
    g(0, "ENDSEC")
    g(0, "SECTION"); g(2, "ENTITIES")
    for layer, item in items:
        if isinstance(item, Hole):
            g(0, "CIRCLE"); g(8, layer); g(10, _num(item.center[0])); g(20, _num(item.center[1]))
            g(30, "0.0"); g(40, _num(item.diameter / 2))
            continue
        for seg in item.segments:
            if isinstance(seg, Line):
                g(0, "LINE"); g(8, layer)
                g(10, _num(seg.start[0])); g(20, _num(seg.start[1])); g(30, "0.0")
                g(11, _num(seg.end[0])); g(21, _num(seg.end[1])); g(31, "0.0")
            else:
                a1 = seg.start_angle if seg.sweep > 0 else seg.start_angle + seg.sweep
                a2 = a1 + abs(seg.sweep)
                g(0, "ARC"); g(8, layer)
                g(10, _num(seg.center[0])); g(20, _num(seg.center[1])); g(30, "0.0")
                g(40, _num(seg.radius))
                g(50, _num(math.degrees(a1) % 360)); g(51, _num(math.degrees(a2) % 360))
    height = max(3.0, min(10.0, 0.05 * min(x1 - x0, y1 - y0)))
    g(0, "TEXT"); g(8, LABEL); g(10, _num(x0 + height)); g(20, _num(y0 + height)); g(30, "0.0")
    g(40, _num(height)); g(1, profile.panel_id)
    g(0, "ENDSEC")
    g(0, "EOF")
    return "".join(w)


def read_dxf(text):
    """Entities of a DXF written by ``dxf_text``: list of dicts with 'type'/'layer'."""
    lines = text.splitlines()
    if len(lines) % 2:
        raise ValueError("Malformed DXF: odd number of lines")
    pairs = [(int(lines[i].strip()), lines[i + 1].strip()) for i in range(0, len(lines), 2)]
    entities, current, in_entities = [], None, False
    for code, value in pairs:
        if code == 2 and value == "ENTITIES":
            in_entities = True
            continue
        if not in_entities:
            continue
        if code == 0:
            if current is not None:
                entities.append(current)
            current = None if value in ("ENDSEC", "EOF") else {"type": value}
            if value == "ENDSEC":
                in_entities = False
            continue
        if current is not None:
            current[code] = value
    out = []
    for e in entities:
        f = {k: (float(v) if k in (10, 20, 11, 21, 40, 50, 51) else v) for k, v in e.items()}
        f["layer"] = f.pop(8)
        out.append(f)
    return out


def _arc_points(e):
    cx, cy, r = e[10], e[20], e[40]
    a1, a2 = math.radians(e[50]), math.radians(e[51])
    sweep = (a2 - a1) % (2 * math.pi) or 2 * math.pi
    return (cx + r * math.cos(a1), cy + r * math.sin(a1)), (cx + r * math.cos(a1 + sweep),
                                                            cy + r * math.sin(a1 + sweep)), sweep


def loop_areas(entities, layer, tol=1e-4):
    """Chain LINE/ARC entities on ``layer`` into closed loops; return their areas."""
    segs = []
    for e in entities:
        if e["layer"] != layer:
            continue
        if e["type"] == "LINE":
            segs.append(((e[10], e[20]), (e[11], e[21]), None))
        elif e["type"] == "ARC":
            p1, p2, sweep = _arc_points(e)
            segs.append((p1, p2, (e[10], e[20], e[40], math.radians(e[50]), sweep)))
    areas = []
    while segs:
        first = segs.pop(0)
        chain, (start, end) = [(first, False)], first[:2]
        while math.dist(end, start) > tol:
            for k, s in enumerate(segs):
                if math.dist(s[0], end) <= tol:
                    chain.append((s, False)); end = s[1]; segs.pop(k); break
                if math.dist(s[1], end) <= tol:
                    chain.append((s, True)); end = s[0]; segs.pop(k); break
            else:
                raise ValueError("Open contour on layer %s near %r" % (layer, end))
        total = 0.0
        for (p1, p2, arc), reverse in chain:
            if arc is None:
                a, b = (p2, p1) if reverse else (p1, p2)
                total += 0.5 * (a[0] * b[1] - b[0] * a[1])
            else:
                cx, cy, r, a1, sweep = arc
                a2 = a1 + sweep
                term = 0.5 * (r * (cx * (math.sin(a2) - math.sin(a1)) - cy * (math.cos(a2) - math.cos(a1)))
                              + r * r * sweep)
                total += -term if reverse else term
        areas.append(abs(total))
    return sorted(areas)


def cutlist_csv(profiles, files=None):
    fields = ("panel_id", "display_name", "material_ref", "thickness_mm", "blank_x_mm", "blank_y_mm",
              "net_area_mm2", "volume_mm3", "through_cuts", "pockets", "holes", "machined_faces",
              "reliefs", "dxf_file", "notes")
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(fields)
    for p in profiles:
        (x0, y0), (x1, y1) = p.outline.bounds
        writer.writerow((p.panel_id, p.display_name, p.material_ref, "%.3f" % p.thickness,
                         "%.3f" % (x1 - x0), "%.3f" % (y1 - y0), "%.3f" % p.net_area_mm2,
                         "%.3f" % p.volume_mm3,
                         sum(isinstance(f, ThroughCut) for f in p.features),
                         sum(isinstance(f, Pocket) for f in p.features),
                         sum(isinstance(f, Hole) for f in p.features),
                         "+".join(p.faces_machined) or "none", p.reliefs,
                         (files or {}).get(p.panel_id, ""), " | ".join(p.notes)))
    return buf.getvalue()


def export_profiles(profiles, out_dir):
    """Write one DXF per panel plus cutlist.csv; refuse to overwrite anything."""
    ids = [p.panel_id for p in profiles]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate panel ids")
    os.makedirs(out_dir, exist_ok=True)
    files = {pid: pid.replace("/", "_") + ".dxf" for pid in ids}
    targets = [os.path.join(out_dir, f) for f in files.values()] + [os.path.join(out_dir, "cutlist.csv")]
    existing = [t for t in targets if os.path.exists(t)]
    if existing:
        raise FileExistsError("Refusing to overwrite: %s" % ", ".join(existing))
    for p in profiles:
        with open(os.path.join(out_dir, files[p.panel_id]), "x", encoding="ascii", newline="\n") as fh:
            fh.write(dxf_text(p))
    with open(os.path.join(out_dir, "cutlist.csv"), "x", encoding="utf-8", newline="\n") as fh:
        fh.write(cutlist_csv(profiles, files))
    return targets
