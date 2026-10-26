"""Fusion adapter: AssemblyDefinition -> parametric Fusion model, and read-back.

Carries over the V4 construction that was validated in Fusion (dimension-driven
sketches, expression-based extrudes, one component per panel, per-cut
participantBodies) and adds: stable-ID attributes, pre-flight target
resolution BEFORE any cut exists, and BRep read-back for validation.

NOTE: written against the documented Fusion API; the parts that are new in V5
(attributes, pointContainment) have not yet been run in Fusion - see README.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import adsk.core
import adsk.fusion

from ... import GENERATOR_ID
from ...components.model import AssemblyDefinition, DadoOperation, Panel
from ...core.geometry import Box, Vec, RoundedCornerOutline
from ...core.expr import _fmt
from ...core.units import cm3_to_mm3, cm_to_mm
from ...verification.geometry_source import MeasuredBody
from ..protocol import CadError, CompileReport, preflight

ATTR_GROUP = "VanDesign"
ATTR_ID = "stable_id"
ATTR_RULE = "source_rule"
ATTR_GEN = "generator"
ATTR_SPEC = "spec_json"


class FusionAdapterError(CadError):
    pass


def _find_occurrences(root) -> Dict[str, List]:
    found: Dict[str, List] = {}
    for i in range(root.occurrences.count):
        occ = root.occurrences.item(i)
        attr = occ.component.attributes.itemByName(ATTR_GROUP, ATTR_ID)
        if attr:
            found.setdefault(attr.value, []).append(occ)
    return found


class FusionAdapter:
    def __init__(self, design: "adsk.fusion.Design"):
        if design.designType != adsk.fusion.DesignTypes.ParametricDesignType:
            raise FusionAdapterError("Design history (parametric mode) must be enabled.")
        self.design = design
        self.root = design.rootComponent

    # ------------------------------------------------------------------ state
    def has_managed_assembly(self) -> bool:
        return bool(_find_occurrences(self.root))

    def stored_spec_json(self) -> Optional[str]:
        attr = self.root.attributes.itemByName(ATTR_GROUP, ATTR_SPEC)
        return attr.value if attr else None

    def store_spec_json(self, text: str) -> None:
        self.root.attributes.add(ATTR_GROUP, ATTR_SPEC, text)

    # ---------------------------------------------------------------- compile
    def compile(self, assembly: AssemblyDefinition) -> CompileReport:
        preflight(assembly)  # structure + constraints, before anything is created
        if self.root.occurrences.count > 0:
            raise FusionAdapterError("Design is not empty; use a NEW, EMPTY design.")
        params = self.design.userParameters
        for p in assembly.parameters.params:
            if params.itemByName(p.name):
                raise FusionAdapterError("Parameter already exists: " + p.name)

        report = CompileReport()
        for p in assembly.parameters.params:
            expr = ("%s mm" % _fmt(p.value_mm)) if p.is_base else p.expr.render()
            up = params.add(p.name, adsk.core.ValueInput.createByString(expr), "mm", p.comment)
            up.isFavorite = True
            report.created_parameters.append(p.name)

        components: Dict[str, "adsk.fusion.Component"] = {}
        for panel in assembly.panels:
            components[panel.stable_id] = self._make_panel(panel)
            report.created_panels.append(panel.stable_id)

        # Resolve EVERY cut target to exactly one body before the first cut.
        targets = {}
        for op in assembly.operations:
            comp = components.get(op.target_panel_id)
            if comp is None or comp.bRepBodies.count != 1:
                raise FusionAdapterError(
                    "%s: target %r does not resolve to exactly one body; no cut was made."
                    % (op.operation_id, op.target_panel_id)
                )
            targets[op.operation_id] = comp
        for op in assembly.operations:
            self._make_dado(op, targets[op.operation_id])
            report.created_operations.append(op.operation_id)
        return report

    # --------------------------------------------------------- sketch/extrude
    def _eval_cm(self, expr: str) -> float:
        return self.design.unitsManager.evaluateExpression(expr, "mm")

    def _rectangle_profile(self, comp, name: str, x: str, y: str, width: str, depth: str,
                           *, x_dynamic=False, y_dynamic=False):
        px, py = self._eval_cm(x), self._eval_cm(y)
        pw, pd = self._eval_cm(width), self._eval_cm(depth)
        if min(pw, pd) <= 0:
            raise FusionAdapterError("Invalid profile for %s: %s x %s" % (name, width, depth))

        sketch = comp.sketches.add(comp.xYConstructionPlane)
        sketch.name = name + " - parametric profile"
        lines = sketch.sketchCurves.sketchLines.addTwoPointRectangle(
            adsk.core.Point3D.create(px, py, 0), adsk.core.Point3D.create(px + pw, py + pd, 0))
        cons = sketch.geometricConstraints
        for i in (0, 2):
            cons.addHorizontal(lines.item(i))
        for i in (1, 3):
            cons.addVertical(lines.item(i))

        bottom, right = lines.item(0), lines.item(1)
        corner, origin = bottom.startSketchPoint, sketch.originPoint
        dims = sketch.sketchDimensions
        H = adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation
        V = adsk.fusion.DimensionOrientations.VerticalDimensionOrientation

        fixed_x = abs(px) < 1e-7 and not x_dynamic
        fixed_y = abs(py) < 1e-7 and not y_dynamic
        # A zero-valued parameter is not a fixed axis. Bind the opposite corner
        # to origin + size so its driving dimension starts nonzero; the size
        # dimensions below preserve the requested lower-corner expression.
        far = right.endSketchPoint
        if fixed_x and fixed_y:
            cons.addCoincident(corner, origin)
        else:
            if fixed_x:
                cons.addVerticalPoints(origin, corner)
            else:
                zero = abs(px) < 1e-7
                d = dims.addDistanceDimension(origin, far if zero else corner, H,
                                              adsk.core.Point3D.create(px / 2, py - 2, 0))
                d.parameter.expression = "(%s + %s)" % (x, width) if zero else x
            if fixed_y:
                cons.addHorizontalPoints(origin, corner)
            else:
                zero = abs(py) < 1e-7
                d = dims.addDistanceDimension(origin, far if zero else corner, V,
                                              adsk.core.Point3D.create(px - 2, py / 2, 0))
                d.parameter.expression = "(%s + %s)" % (y, depth) if zero else y

        wd = dims.addDistanceDimension(bottom.startSketchPoint, bottom.endSketchPoint, H,
                                       adsk.core.Point3D.create(px + pw / 2, py - 2, 0))
        wd.parameter.expression = width
        dd = dims.addDistanceDimension(right.startSketchPoint, right.endSketchPoint, V,
                                       adsk.core.Point3D.create(px + pw + 2, py + pd / 2, 0))
        dd.parameter.expression = depth
        return sketch

    def _rounded_profile(self, comp, name, width, length, radius):
        w, l, r = (self._eval_cm(e) for e in (width, length, radius))
        RoundedCornerOutline(w * 10, l * 10, r * 10)
        point = adsk.core.Point3D.create
        sketch = comp.sketches.add(comp.xYConstructionPlane)
        sketch.name = name + " - parametric rounded profile"
        arc = sketch.sketchCurves.sketchArcs.addByCenterStartSweep(
            point(w-r, l-r, 0), point(w, l-r, 0), math.pi/2)
        if arc is None:
            raise FusionAdapterError("Rounded arc creation failed")
        cons, dims = sketch.geometricConstraints, sketch.sketchDimensions
        cons.addHorizontalPoints(arc.centerSketchPoint, arc.startSketchPoint)
        cons.addVerticalPoints(arc.centerSketchPoint, arc.endSketchPoint)
        H = adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation
        V = adsk.fusion.DimensionOrientations.VerticalDimensionOrientation
        for axis, expression, text in ((H, "(%s - %s)" % (width, radius), point(w/2, -2, 0)),
                                       (V, "(%s - %s)" % (length, radius), point(-2, l/2, 0))):
            dim = dims.addDistanceDimension(sketch.originPoint, arc.centerSketchPoint, axis, text)
            dim.parameter.expression = expression
        dims.addRadialDimension(arc, point(w+2, l+2, 0)).parameter.expression = radius
        lines = sketch.sketchCurves.sketchLines
        bottom = lines.addByTwoPoints(sketch.originPoint, point(w, 0, 0))
        right = lines.addByTwoPoints(bottom.endSketchPoint, arc.startSketchPoint)
        top = lines.addByTwoPoints(arc.endSketchPoint, point(0, l, 0))
        left = lines.addByTwoPoints(top.endSketchPoint, sketch.originPoint)
        for line in (bottom, top):
            cons.addHorizontal(line)
        for line in (right, left):
            cons.addVertical(line)
        if sketch.profiles.count != 1:
            raise FusionAdapterError("Rounded outline must produce exactly one closed profile")
        return sketch

    def _extrude(self, comp, sketch, name: str, z: str, height: str, operation, participants=None):
        features = comp.features.extrudeFeatures
        inp = features.createInput(sketch.profiles.item(0), operation)
        if operation == adsk.fusion.FeatureOperations.CutFeatureOperation:
            if not participants:
                raise FusionAdapterError("%s: a cut without explicit participant bodies is not allowed." % name)
            inp.participantBodies = participants
        inp.setOneSideExtent(
            adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByString(height)),
            adsk.fusion.ExtentDirections.PositiveExtentDirection)
        if z.strip() != "0 mm":
            inp.startExtent = adsk.fusion.OffsetStartDefinition.create(adsk.core.ValueInput.createByString(z))
        feature = features.add(inp)
        feature.name = name
        sketch.isVisible = False
        return feature

    def _make_panel(self, panel: Panel):
        occ = self.root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp = occ.component
        comp.name = panel.display_name
        ox, oy, oz = (e.render() for e in panel.box.origin)
        sx, sy, sz = (e.render() for e in panel.box.size)
        if panel.corner_radius is None:
            sketch = self._rectangle_profile(comp, panel.display_name, ox, oy, sx, sy,
                                             x_dynamic=bool(panel.box.origin[0].refs()),
                                             y_dynamic=bool(panel.box.origin[1].refs()))
        else:
            sketch = self._rounded_profile(comp, panel.display_name, sx, sy, panel.corner_radius.render())
        feat = self._extrude(comp, sketch, panel.display_name + " - solid", oz, sz,
                             adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        feat.bodies.item(0).name = panel.display_name
        comp.attributes.add(ATTR_GROUP, ATTR_ID, panel.stable_id)
        comp.attributes.add(ATTR_GROUP, ATTR_RULE, "module:%s role:%s" % (GENERATOR_ID, panel.role))
        comp.attributes.add(ATTR_GROUP, ATTR_GEN, GENERATOR_ID)
        return comp

    def _make_dado(self, op: DadoOperation, target_comp):
        ox, oy, oz = (e.render() for e in op.cut.origin)
        sx, sy, sz = (e.render() for e in op.cut.size)
        sketch = self._rectangle_profile(target_comp, op.operation_id, ox, oy, sx, sy,
                                         x_dynamic=bool(op.cut.origin[0].refs()),
                                         y_dynamic=bool(op.cut.origin[1].refs()))
        # Only the target panel's own body may be cut - never the mating shelf.
        return self._extrude(target_comp, sketch, op.operation_id, oz, sz,
                             adsk.fusion.FeatureOperations.CutFeatureOperation,
                             participants=[target_comp.bRepBodies.item(0)])

    # ------------------------------------------------------------- read-back
    def geometry_source(self) -> "FusionGeometrySource":
        return FusionGeometrySource(self.design)


class FusionGeometrySource:
    """Reads parameters, solids, containment and interference from Fusion."""

    def __init__(self, design: "adsk.fusion.Design"):
        self.design = design
        self.diagnostics: List[str] = []
        self._occ = _find_occurrences(design.rootComponent)
        for pid, occs in self._occ.items():
            if len(occs) > 1:
                self.diagnostics.append("duplicate occurrences carry stable id %s" % pid)

    def _single_body(self, panel_id: str):
        occs = self._occ.get(panel_id, [])
        if len(occs) != 1:
            self.diagnostics.append("%s: %d occurrences found (need exactly 1)" % (panel_id, len(occs)))
            return None
        occ = occs[0]
        if occ.bRepBodies.count != 1:
            self.diagnostics.append("%s: %d bodies found (need exactly 1)" % (panel_id, occ.bRepBodies.count))
            return None
        return occ.bRepBodies.item(0)  # assembly-context proxy

    def parameter_value(self, name: str) -> Optional[float]:
        p = self.design.userParameters.itemByName(name)
        return None if p is None else cm_to_mm(p.value)

    def body(self, panel_id: str) -> Optional[MeasuredBody]:
        b = self._single_body(panel_id)
        if b is None:
            return None
        bb = b.boundingBox
        lo = (cm_to_mm(bb.minPoint.x), cm_to_mm(bb.minPoint.y), cm_to_mm(bb.minPoint.z))
        hi = (cm_to_mm(bb.maxPoint.x), cm_to_mm(bb.maxPoint.y), cm_to_mm(bb.maxPoint.z))
        return MeasuredBody(Box(lo, hi), cm3_to_mm3(b.volume))

    def point_in_material(self, panel_id: str, point_mm: Vec) -> Optional[bool]:
        b = self._single_body(panel_id)
        if b is None:
            return None
        try:
            pt = adsk.core.Point3D.create(point_mm[0] / 10.0, point_mm[1] / 10.0, point_mm[2] / 10.0)
            result = b.pointContainment(pt)
            pc = adsk.fusion.PointContainment  # enum lives in adsk.fusion per Autodesk docs
            if result == pc.PointInsidePointContainment:
                return True
            if result == pc.PointOutsidePointContainment:
                return False
            return None  # on boundary / unknown
        except Exception as e:  # recorded, never silent; probe becomes UNKNOWN
            self.diagnostics.append("pointContainment failed for %s: %s" % (panel_id, e))
            return None

    def managed_ids(self) -> Optional[Dict[str, int]]:
        """Read-only census of managed stable ids across ALL root occurrences.

        Enumerates live (not the constructor snapshot) and counts every occurrence
        carrying a VanDesign stable_id attribute, so duplicates are visible as
        multiplicity > 1.  Never mutates the design.  None if enumeration fails.
        """
        try:
            root = self.design.rootComponent
            counts: Dict[str, int] = {}
            for i in range(root.occurrences.count):
                attr = root.occurrences.item(i).component.attributes.itemByName(ATTR_GROUP, ATTR_ID)
                if attr:
                    counts[attr.value] = counts.get(attr.value, 0) + 1
            return counts
        except Exception as e:
            self.diagnostics.append("managed id census failed: %s" % e)
            return None

    def interference_count(self, panel_ids: Sequence[str]) -> Optional[int]:
        try:
            coll = adsk.core.ObjectCollection.create()
            for pid in panel_ids:
                b = self._single_body(pid)
                if b is None:
                    return None
                coll.add(b)
            result = self.design.analyzeInterference(self.design.createInterferenceInput(coll))
            return result.count
        except Exception as e:
            self.diagnostics.append("interference analysis failed: %s" % e)
            return None
