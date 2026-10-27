"""READ-ONLY Fusion diagnostic for Issue #95 (proposed; NOT run; needs owner approval).

Run once as a Fusion script (Utilities > Scripts and Add-Ins) or as a reviewed
read-only Runner command. It reads the failed native-profile sketches that the
three failed live builds left in their open, unsaved fixtures and writes one
JSON report. It never activates, edits, saves, closes or discards a document,
sets no property and calls no creation, merge or delete method. Any read error
is recorded and the script carries on.

What it settles (see hypotheses.py):
  * was the semicircle arc's own centre already constrained at creation (O1)?
  * did addByCenterStartSweep reuse the given SketchPoint, copy it with a
    coincident constraint, or copy it unlinked (O2)?
  * did merge() redirect the arc, keep the arc's own point, or remove the driven
    point and its two coordinate dimensions (O3)?
  * does == on two reads of one property compare equal (wrapper equality)?
"""
import json
import os
import traceback

import adsk.core
import adsk.fusion

SKETCH = "k.panel.left.001 - native profile"
OUT = os.path.join(os.path.expanduser("~"), "Documents", "VanDesign-Runner", "diagnostics",
                   "issue95_arc_centre_inspection.json")


def _safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:                           # record, never stop or recover
        return {"error": "%s: %s" % (type(exc).__name__, exc)} if default is None else default


def _mm(p):
    g = p.geometry
    return [round(g.x * 10, 6), round(g.y * 10, 6), round(g.z * 10, 6)]


def _index(item, items):
    """Index of ``item`` in a read-only list by ==, else None."""
    for i, other in enumerate(items):
        if _safe(lambda: other == item, False):
            return i
    return None


def _entity(e, points, curves):
    kind = _safe(lambda: e.objectType, "?")
    if "SketchPoint" in str(kind):
        return {"point": _index(e, points), "at_mm": _safe(lambda: _mm(e))}
    return {"curve": _index(e, curves), "type": kind}


def inspect(sketch):
    points = [sketch.sketchPoints.item(i) for i in range(sketch.sketchPoints.count)]
    curves = [sketch.sketchCurves.item(i) for i in range(sketch.sketchCurves.count)]
    out = {"isFullyConstrained": _safe(lambda: sketch.isFullyConstrained), "points": [], "arcs": [],
           "constraints": [], "dimensions": []}
    for i, p in enumerate(points):
        out["points"].append({
            "index": i, "at_mm": _safe(lambda: _mm(p)), "isFixed": _safe(lambda: p.isFixed),
            "isFullyConstrained": _safe(lambda: p.isFullyConstrained),
            "isReference": _safe(lambda: p.isReference),
            "connected": _safe(lambda: [_entity(p.connectedEntities.item(k), points, curves)
                                        for k in range(p.connectedEntities.count)])})
    arcs = sketch.sketchCurves.sketchArcs
    for i in range(arcs.count):
        a = arcs.item(i)
        g = _safe(lambda: a.geometry)
        out["arcs"].append({
            "curve": _index(a, curves), "radius_mm": _safe(lambda: a.radius * 10),
            "sweep_rad": _safe(lambda: g.endAngle - g.startAngle),
            "isFullyConstrained": _safe(lambda: a.isFullyConstrained),
            "centre_point_by_eq": _safe(lambda: _index(a.centerSketchPoint, points)),
            "centre_at_mm": _safe(lambda: _mm(a.centerSketchPoint)),
            "centre_isFixed": _safe(lambda: a.centerSketchPoint.isFixed),
            "centre_isFullyConstrained": _safe(lambda: a.centerSketchPoint.isFullyConstrained),
            # Wrapper-equality test: two separate reads of the same property.
            "centre_eq_itself": _safe(lambda: a.centerSketchPoint == a.centerSketchPoint),
            "start_point_by_eq": _safe(lambda: _index(a.startSketchPoint, points)),
            "end_point_by_eq": _safe(lambda: _index(a.endSketchPoint, points)),
            "centre_constraints": _safe(lambda: [a.centerSketchPoint.geometricConstraints.item(k).objectType
                                                 for k in range(a.centerSketchPoint.geometricConstraints.count)]),
            "centre_dimensions": _safe(lambda: [a.centerSketchPoint.sketchDimensions.item(k).objectType
                                                for k in range(a.centerSketchPoint.sketchDimensions.count)])})
    for i in range(sketch.geometricConstraints.count):
        c = sketch.geometricConstraints.item(i)
        row = {"type": _safe(lambda: c.objectType)}
        for name in ("point", "entity", "lineOne", "lineTwo"):
            if hasattr(c, name):
                row[name] = _safe(lambda: _entity(getattr(c, name), points, curves))
        out["constraints"].append(row)
    for i in range(sketch.sketchDimensions.count):
        d = sketch.sketchDimensions.item(i)
        row = {"type": _safe(lambda: d.objectType), "isDriving": _safe(lambda: d.isDriving),
               "expression": _safe(lambda: d.parameter.expression), "value_mm": _safe(lambda: d.parameter.value * 10)}
        for name in ("entityOne", "entityTwo", "entity"):
            if hasattr(d, name):
                row[name] = _safe(lambda: _entity(getattr(d, name), points, curves))
        out["dimensions"].append(row)
    return out


def run(context):
    report = {"sketch_name": SKETCH, "documents": []}
    try:
        app = adsk.core.Application.get()
        docs = app.documents
        for di in range(docs.count):
            doc = docs.item(di)
            design = _safe(lambda: adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType")))
            if not design or isinstance(design, dict):
                continue
            found = []
            for ci in range(design.allComponents.count):
                comp = design.allComponents.item(ci)
                for si in range(comp.sketches.count):
                    sketch = comp.sketches.item(si)
                    if _safe(lambda: sketch.name) == SKETCH:
                        found.append(inspect(sketch))
            if found:
                # Document order and name only: no cloud, project or folder identifiers.
                report["documents"].append({"open_index": di, "name": _safe(lambda: doc.name),
                                            "isSaved": _safe(lambda: doc.isSaved), "sketches": found})
    except Exception:
        report["error"] = traceback.format_exc()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
