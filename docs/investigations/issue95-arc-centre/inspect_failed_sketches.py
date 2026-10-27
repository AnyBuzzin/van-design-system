"""READ-ONLY Fusion diagnostic for Issue #95 (proposed; NOT run; needs owner approval).

Run once as a Fusion script (Utilities > Scripts and Add-Ins). It reads the
failed native-profile sketches that the three failed live builds left in
their open, unsaved fixtures and writes one NEW JSON report (exclusive
creation; an existing file is never overwritten). It never activates, edits,
saves, closes or discards a document, sets no property and calls no
creation, merge or delete method.

Every API read is recorded as either a value or an explicit error record.
An equality comparison or index that could not be evaluated is "UNKNOWN",
never a mismatch. The report states how many sketches were expected and
found, and whether collection was complete, partial or errored.

What it can show is the CURRENT post-failure state of each sketch: points,
connectivity, constraints, dimensions, the arc centre's constraint state and
whether == holds between two reads of the same property. It cannot prove the
state at arc creation or replay what merge() did; any such reading is an
inference, labelled as one.
"""
import datetime
import hashlib
import json
import os
import traceback
import uuid

import adsk.core
import adsk.fusion

SKETCH = "k.panel.left.001 - native profile"
EXPECTED_SKETCHES = 3                  # one per failed build: 89b7a5a, 8b98209, 6d4e87a
OUT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "VanDesign-Runner", "diagnostics")
UNKNOWN = "UNKNOWN"


class Read:
    """Collects every read error so completeness is reported, not assumed."""

    def __init__(self):
        self.errors = 0

    def __call__(self, fn):
        try:
            return {"value": fn()}
        except Exception as exc:
            self.errors += 1
            return {"error": "%s: %s" % (type(exc).__name__, exc)}


def _value(record):
    return record.get("value") if "value" in record else None


def _index(read, item, items):
    """{"index": i} on an == match, {"index": None} when every comparison ran
    and none matched, {"index": UNKNOWN, ...} when any comparison failed."""
    failures = []
    for i, other in enumerate(items):
        r = read(lambda: other == item)
        if "error" in r:
            failures.append({"candidate": i, "error": r["error"]})
        elif r["value"] is True:
            return {"index": i}
    return {"index": UNKNOWN, "comparison_errors": failures} if failures else {"index": None}


def _mm(p):
    g = p.geometry
    return [round(g.x * 10, 6), round(g.y * 10, 6), round(g.z * 10, 6)]


def _entity(read, e, points, curves):
    kind = read(lambda: e.objectType)
    if "SketchPoint" in str(_value(kind)):
        return {"kind": kind, "point": _index(read, e, points), "at_mm": read(lambda: _mm(e))}
    return {"kind": kind, "curve": _index(read, e, curves)}


def _reference(read, obj, name, points, curves):
    """The entity behind property ``name`` when the class has it; a failed read
    is recorded (hasattr would call the API and could hide or raise errors)."""
    if name not in dir(type(obj)):
        return {}
    target = read(lambda: getattr(obj, name))
    return {name: target if "error" in target else _entity(read, target["value"], points, curves)}


def _items(read, collection_fn):
    count = read(lambda: collection_fn().count)
    if "error" in count:
        return count, []
    return count, [collection_fn().item(i) for i in range(count["value"])]


def inspect(read, sketch):
    _, points = _items(read, lambda: sketch.sketchPoints)
    _, curves = _items(read, lambda: sketch.sketchCurves)
    out = {"isFullyConstrained": read(lambda: sketch.isFullyConstrained), "points": [], "arcs": [],
           "constraints": [], "dimensions": []}
    for i, p in enumerate(points):
        connected = read(lambda: [_entity(read, p.connectedEntities.item(k), points, curves)
                                  for k in range(p.connectedEntities.count)])
        out["points"].append({"index": i, "at_mm": read(lambda: _mm(p)), "isFixed": read(lambda: p.isFixed),
                              "isFullyConstrained": read(lambda: p.isFullyConstrained),
                              "isReference": read(lambda: p.isReference), "connected": connected})
    _, arcs = _items(read, lambda: sketch.sketchCurves.sketchArcs)
    for a in arcs:
        centre = lambda: a.centerSketchPoint  # noqa: E731  (a fresh read each call)
        geometry = read(lambda: a.geometry)
        out["arcs"].append({
            "curve": _index(read, a, curves), "radius_mm": read(lambda: a.radius * 10),
            "sweep_rad": read(lambda: geometry["value"].endAngle - geometry["value"].startAngle),
            "isFullyConstrained": read(lambda: a.isFullyConstrained),
            "centre_point": _index(read, centre(), points), "centre_at_mm": read(lambda: _mm(centre())),
            "centre_isFixed": read(lambda: centre().isFixed),
            "centre_isFullyConstrained": read(lambda: centre().isFullyConstrained),
            # Two separate reads of one property: tests wrapper equality directly.
            "centre_eq_second_read": read(lambda: centre() == centre()),
            "start_point": _index(read, a.startSketchPoint, points),
            "end_point": _index(read, a.endSketchPoint, points),
            "centre_constraints": read(lambda: [centre().geometricConstraints.item(k).objectType
                                                for k in range(centre().geometricConstraints.count)]),
            "centre_dimensions": read(lambda: [centre().sketchDimensions.item(k).objectType
                                               for k in range(centre().sketchDimensions.count)])})
    _, constraints = _items(read, lambda: sketch.geometricConstraints)
    for c in constraints:
        row = {"type": read(lambda: c.objectType)}
        for name in ("point", "entity", "lineOne", "lineTwo"):
            row.update(_reference(read, c, name, points, curves))
        out["constraints"].append(row)
    _, dimensions = _items(read, lambda: sketch.sketchDimensions)
    for d in dimensions:
        row = {"type": read(lambda: d.objectType), "isDriving": read(lambda: d.isDriving),
               "expression": read(lambda: d.parameter.expression), "value_mm": read(lambda: d.parameter.value * 10)}
        for name in ("entityOne", "entityTwo", "entity"):
            row.update(_reference(read, d, name, points, curves))
        out["dimensions"].append(row)
    return out


def run(context):
    read = Read()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(OUT_DIR, "issue95_arc_centre_%s_%s.json" % (stamp, uuid.uuid4().hex[:8]))
    def source_sha256():
        with open(__file__, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    report = {"sketch_name": SKETCH, "source_sha256": read(source_sha256), "started_utc": stamp,
              "fusion_version": read(lambda: adsk.core.Application.get().version),
              "documents": [], "document_errors": [], "status": "error"}
    try:
        app = adsk.core.Application.get()
        count = read(lambda: app.documents.count)
        report["open_documents"] = count
        for di in range(_value(count) or 0):
            doc = app.documents.item(di)
            design = read(lambda: adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType")))
            if "error" in design or design["value"] is None:
                report["document_errors"].append({"open_index": di, "design": design})
                continue
            found = []
            _, comps = _items(read, lambda: design["value"].allComponents)
            for comp in comps:
                _, sketches = _items(read, lambda: comp.sketches)
                for sketch in sketches:
                    if _value(read(lambda: sketch.name)) == SKETCH:
                        found.append(inspect(read, sketch))
            if found:
                # Document order and name only: no cloud, project or folder identifiers.
                report["documents"].append({"open_index": di, "name": read(lambda: doc.name),
                                            "isSaved": read(lambda: doc.isSaved), "sketches": found})
        observed = sum(len(d["sketches"]) for d in report["documents"])
        report["expected_sketches"], report["observed_sketches"] = EXPECTED_SKETCHES, observed
        report["read_errors"] = read.errors
        report["status"] = ("complete" if observed == EXPECTED_SKETCHES and read.errors == 0
                            and not report["document_errors"] else "partial")
    except Exception:
        report["error"] = traceback.format_exc()
        report["read_errors"] = read.errors
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(path, "x", encoding="utf-8") as fh:          # exclusive: never overwrite evidence
        json.dump(report, fh, indent=2)
