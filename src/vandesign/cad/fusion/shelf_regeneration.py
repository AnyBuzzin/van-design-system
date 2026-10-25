"""Narrow, opt-in owned reconstruction. No save/close, global Undo or crash replay.

Only a fresh compile can issue a receipt. Every unavailable API observation
raises, so lack of evidence cannot authorize deletion. See the G4 contract.
"""
import json
import math
import adsk.core
import adsk.fusion

from .adapter import ATTR_GROUP, ATTR_ID, ATTR_GEN, ATTR_RULE, FusionAdapter, FusionAdapterError
from ... import GENERATOR_ID

RECEIPT = "g4_fresh_fixture_v1"


class ShelfFixtureAdapter(FusionAdapter):
    """Explicit fresh-fixture opt-in; the accepted G3 adapter is unchanged.

    The small panel wrapper differs only by immediate occurrence capture.
    Expressions, sketch construction, extrudes and cuts still use G3 methods.
    Its equivalence to the original panel method is checked offline.
    """
    def compile(self, assembly):
        require_empty(self.design)
        report = super().compile(assembly)
        record_receipt(self, assembly)
        return report

    def _make_panel(self, panel):
        occ = self.root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        if hasattr(self, "_structural_created"):
            self._structural_created.append(occ)
        comp = occ.component
        comp.name = panel.display_name
        ox, oy, oz = (e.render() for e in panel.box.origin)
        sx, sy, sz = (e.render() for e in panel.box.size)
        sketch = self._rectangle_profile(comp, panel.display_name, ox, oy, sx, sy,
                                         x_dynamic=bool(panel.box.origin[0].refs()),
                                         y_dynamic=bool(panel.box.origin[1].refs()))
        feat = self._extrude(comp, sketch, panel.display_name + " - solid", oz, sz,
                             adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        feat.bodies.item(0).name = panel.display_name
        comp.attributes.add(ATTR_GROUP, ATTR_ID, panel.stable_id)
        comp.attributes.add(ATTR_GROUP, ATTR_RULE, "module:%s role:%s" % (GENERATOR_ID, panel.role))
        comp.attributes.add(ATTR_GROUP, ATTR_GEN, GENERATOR_ID)
        return comp


def items(collection):
    return [collection.item(i) for i in range(collection.count)]


def require(condition, message):
    if not condition:
        raise FusionAdapterError(message)


def finite(value):
    require(math.isfinite(value), "non-finite measurement")
    return value


def point(p):
    return [finite(p.x), finite(p.y), finite(p.z)]


def auxiliaries(comp):
    # Origin planes/axes are not in the user-created collections.
    return {n: getattr(comp, n).count for n in (
        "occurrences", "meshBodies", "constructionPlanes", "constructionAxes",
        "constructionPoints", "joints", "asBuiltJoints", "rigidGroups")}


def require_empty(design):
    root = design.rootComponent
    require(not any(auxiliaries(root).values()) and root.bRepBodies.count == 0
            and root.sketches.count == 0 and root.features.count == 0
            and design.allComponents.count == 1 and design.timeline.count == 0
            and design.userParameters.count == 0, "structural fixture requires an entirely empty design")


def snapshot(adapter, assembly):
    """Measured inventory + token handles; does not move the timeline."""
    design, root = adapter.design, adapter.root
    expected = {p.stable_id: p for p in assembly.panels}
    cuts = {o.operation_id: o.target_panel_id for o in assembly.operations}
    require(design.timeline.markerPosition == design.timeline.count, "timeline is rolled back")
    require(design.timeline.count == 3 * len(expected) + 2 * len(cuts), "unexpected timeline entities")
    require(root.occurrences.count == len(expected) and design.allComponents.count == len(expected)+1,
            "missing, duplicate or orphan components")
    root_aux = auxiliaries(root)
    root_aux.pop("occurrences")
    require(not any(root_aux.values()) and root.bRepBodies.count == 0 and root.sketches.count == 0
            and root.features.count == 0, "unmanaged root entities")
    live = {p.name: {"expression": p.expression, "unit": p.unit, "value_mm": finite(p.value * 10)}
            for p in items(design.userParameters)}
    require(set(live) == {p.name for p in assembly.parameters.params}, "unexpected user parameters")
    panels, tokens = {}, {}
    for occ in items(root.occurrences):
        comp = occ.component
        attr = comp.attributes.itemByName(ATTR_GROUP, ATTR_ID)
        pid = attr.value if attr else None
        require(pid in expected and pid not in panels, "missing/duplicate/unmanaged stable ID")
        panel = expected[pid]
        require(not occ.isReferencedComponent and not any(auxiliaries(comp).values()), "linked/nested/unmanaged entities")
        for key, value in ((ATTR_GEN, GENERATOR_ID),
                           (ATTR_RULE, "module:%s role:%s" % (GENERATOR_ID, panel.role))):
            a = comp.attributes.itemByName(ATTR_GROUP, key)
            require(a is not None and a.value == value, "generator/role drift")
        feature_names = [panel.display_name + " - solid"] + sorted(k for k,v in cuts.items() if v == pid)
        feats = items(comp.features.extrudeFeatures)
        sketches = items(comp.sketches)
        require(all(int(f.healthState) == 0 and not f.isSuppressed for f in feats), "unhealthy/suppressed feature")
        require(comp.bRepBodies.count == 1 and comp.features.count == len(feature_names)
                and sorted(f.name for f in feats) == sorted(feature_names)
                and sorted(s.name for s in sketches) == sorted(n.replace(" - solid", "") + " - parametric profile"
                                                             for n in feature_names), "unexpected bodies/features/sketches")
        b = comp.bRepBodies.item(0)
        require(b.isSolid, "body is not solid")
        sketch_data = {}
        for s in sketches:
            require(s.sketchCurves.count == 4 and s.sketchCurves.sketchLines.count == 4,
                    "non-generator sketch geometry")
            sketch_data[s.name] = {
                "lines": [[point(l.startSketchPoint.geometry), point(l.endSketchPoint.geometry)]
                          for l in items(s.sketchCurves.sketchLines)],
                "points": s.sketchPoints.count, "constraints": [c.objectType for c in items(s.geometricConstraints)],
                "dimensions": [[d.objectType, d.parameter.expression, finite(d.parameter.value)]
                               for d in items(s.sketchDimensions)], "profiles": s.profiles.count}
        panels[pid] = {
            "name": comp.name, "body_name": b.name, "transform": [finite(v) for v in occ.transform2.asArray()],
            "bounds_cm": [point(b.boundingBox.minPoint), point(b.boundingBox.maxPoint)],
            "volume_cm3": finite(b.volume), "topology": [b.faces.count, b.edges.count, b.vertices.count],
            "features": [[f.name, int(f.operation), int(f.healthState), bool(f.isSuppressed)] for f in feats],
            "sketches": sketch_data,
            # Internal auto-numbered parameter names need not survive reconstruction.
            "model_parameters": sorted([[p.expression, p.unit, finite(p.value)] for p in items(comp.modelParameters)])}
        for key, entity in [(pid, occ), (pid+"/body", b)] + [(pid+"/"+f.name, f) for f in feats] + [(pid+"/"+s.name, s) for s in sketches]:
            tokens[key] = entity.entityToken
    require(set(panels) == set(expected), "incomplete panel inventory")
    return {"live_params": live, "panels": panels, "cuts": cuts,
            "timeline": design.timeline.count}, tokens


def same(a, b):
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(same(x,y) for x,y in zip(a,b))
    if type(a) in (int, float):
        return type(b) in (int,float) and math.isfinite(a) and math.isfinite(b) and abs(a-b) <= 1e-7
    return a is not None and a == b


def record_receipt(adapter, assembly):
    state, tokens = snapshot(adapter, assembly)
    adapter.root.attributes.add(ATTR_GROUP, RECEIPT, json.dumps({"state": state, "tokens": tokens}, allow_nan=False))


def verified_state(adapter, assembly):
    receipt = adapter.root.attributes.itemByName(ATTR_GROUP, RECEIPT)
    require(receipt is not None, "no fresh-fixture ownership receipt; existing designs cannot be adopted")
    saved = json.loads(receipt.value)
    state, tokens = snapshot(adapter, assembly)
    require(same(saved["state"], state), "live structure differs from fresh-fixture receipt")
    require(saved["tokens"].keys() == tokens.keys(), "entity census differs")
    for key, token in saved["tokens"].items():
        # Resolve both tokens now; never compare a historical token string to a current one.
        old = adapter.design.findEntityByToken(token)
        current = adapter.design.findEntityByToken(tokens[key])
        require(len(old) == 1 and len(current) == 1 and old[0] == current[0], "owned entity replaced: " + key)
    return state


class Reconstruction:
    """Synchronous operation handle, retaining only explicitly captured entities."""
    def __init__(self, adapter, old_assembly, new_assembly):
        verified_state(adapter, old_assembly)
        self.adapter = adapter
        self.started = False
        self.old, self.new = old_assembly, new_assembly
        self.owned = items(adapter.root.occurrences)
        adapter._structural_created = self.owned
        self.param_names = {p.name for a in (old_assembly,new_assembly) for p in a.parameters.params}

    def _empty_owned(self):
        a = self.adapter
        live = items(a.root.occurrences)
        require(all(any(o == known for known in self.owned if known.isValid) for o in live),
                "unexpected occurrence: cleanup stopped")
        for occ in reversed(self.owned):
            if occ.isValid:
                require(occ.deleteMe(), "owned occurrence deletion failed")
        self.owned[:] = []
        remaining = items(a.design.userParameters)
        require(all(p.name in self.param_names for p in remaining), "unexpected parameter: cleanup stopped")
        while remaining:
            progress = False
            for p in remaining:
                if p.isValid and p.isDeletable:
                    require(p.deleteMe(), "owned parameter deletion failed")
                    progress = True
            remaining = items(a.design.userParameters)
            require(progress or not remaining, "owned parameters still referenced; cleanup stopped")
        require_empty(a.design)

    def rebuild(self, assembly, stored_text):
        self._empty_owned()
        self.adapter.compile(assembly)
        self.adapter.store_spec_json(stored_text)
        require(self.adapter.stored_spec_json() == stored_text, "stored spec write verification failed")

    def apply(self, stored_text):
        verified_state(self.adapter, self.old)  # final read-only guard, immediately before deletion
        self.started = True
        self.rebuild(self.new, stored_text)

    def restore(self, stored_text):
        self.rebuild(self.old, stored_text)
