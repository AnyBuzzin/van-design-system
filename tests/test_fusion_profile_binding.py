"""Sketch binding intent only: no claim about the live Fusion solver."""
import importlib
import sys
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch



class ProfileBindingTests(unittest.TestCase):
    def setUp(self):
        self.fake = NS(core=NS(Point3D=NS(create=lambda *v: v)), fusion=NS(
            DimensionOrientations=NS(HorizontalDimensionOrientation="H",
                                     VerticalDimensionOrientation="V")))
        with patch.dict(sys.modules, {"adsk": self.fake, "adsk.core": self.fake.core,
                                      "adsk.fusion": self.fake.fusion}):
            self.mod = importlib.import_module("vandesign.cad.fusion.adapter")
        patcher = patch.object(self.mod, "adsk", self.fake)
        patcher.start(); self.addCleanup(patcher.stop)

    def profile(self, x, y, dynamic, values):
        points = [object() for _ in range(4)]
        lines = [NS(startSketchPoint=points[i], endSketchPoint=points[(i+1)%4])
                 for i in range(4)]
        self.constraints = Mock()
        self.dimensions = []
        def dimension(a, b, axis, text):
            d = NS(parameter=NS(expression=None))
            self.dimensions.append((a, b, axis, d))
            return d
        self.origin = object(); self.far = points[2]
        sketch = NS(originPoint=self.origin, geometricConstraints=self.constraints,
            sketchDimensions=NS(addDistanceDimension=dimension),
            sketchCurves=NS(sketchLines=NS(addTwoPointRectangle=lambda *a: NS(item=lambda i: lines[i]))))
        comp = NS(xYConstructionPlane=object(), sketches=NS(add=lambda p: sketch))
        adapter = object.__new__(self.mod.FusionAdapter)
        adapter._eval_cm = lambda e: values[e]
        adapter._rectangle_profile(comp, "test", x, y, "W", "D",
                                   x_dynamic=dynamic[0], y_dynamic=dynamic[1])
        return [d.parameter.expression for _, _, _, d in self.dimensions]

    def test_zero_dynamic_axes_bind_far_corner_not_fixed_axis(self):
        expressions = self.profile("X", "Y", (True, True), {"X":0,"Y":0,"W":20,"D":2})
        self.assertEqual(expressions, ["(X + W)", "(Y + D)", "W", "D"])
        for _, b, _, _ in self.dimensions[:2]: self.assertIs(b, self.far)
        self.constraints.addCoincident.assert_not_called()
        self.constraints.addHorizontalPoints.assert_not_called()
        self.constraints.addVerticalPoints.assert_not_called()

    def test_literal_zero_keeps_original_constraints(self):
        self.assertEqual(self.profile("0 mm", "0 mm", (False,False),
                                     {"0 mm":0,"W":20,"D":2}), ["W","D"])
        self.constraints.addCoincident.assert_called_once()
        self.profile("X", "0 mm", (True,False), {"X":150,"0 mm":0,"W":20,"D":2})
        self.constraints.addHorizontalPoints.assert_called_once()

    def test_nonzero_dynamic_origin_keeps_original_dimensions(self):
        self.assertEqual(self.profile("X", "Y", (True,True),
                                     {"X":150,"Y":10,"W":20,"D":2}), ["X","Y","W","D"])

    def test_both_composed_door_expressions_retain_y_dependency(self):
        from vandesign.composition import compose_layout
        from vandesign.layout_preview import make_layout
        assembly = compose_layout(make_layout([
            {'instance_id':'bed.001','translation_mm':[0,0,0]},
            {'instance_id':'cabinet.001','translation_mm':[1500,0,0]}]),
            editable_placement=True).assembly
        env = assembly.parameters.resolve()
        doors = [p for p in assembly.panels if p.stable_id.endswith(("door.001","door.002"))]
        self.assertEqual(len(doors), 2)
        for panel in doors:
            x,y,_ = panel.box.origin
            w,d,_ = panel.box.size
            values = {x.render():x.eval(env)/10, y.render():y.eval(env)/10,
                      "W":w.eval(env)/10, "D":d.eval(env)/10}
            expressions = self.profile(x.render(), y.render(), (bool(x.refs()),bool(y.refs())), values)
            self.assertEqual(expressions[1], "(%s + D)" % y.render())
            # Algebraic binding invariant, not simulated BRep correctness.
            for position in (0,100,0):
                changed = dict(env, Cab_Pos_Y=position)
                upper = y.eval(changed) + d.eval(changed)
                self.assertEqual(upper - d.eval(changed), position)

    def test_panel_and_dado_callers_forward_symbolic_dependencies(self):
        from vandesign.composition import compose_layout
        from vandesign.layout_preview import make_layout
        assembly = compose_layout(make_layout([
            {'instance_id':'bed.001','translation_mm':[0,0,0]},
            {'instance_id':'cabinet.001','translation_mm':[1500,0,0]}]),
            editable_placement=True).assembly
        self.fake.core.Matrix3D = NS(create=lambda: None)
        self.fake.fusion.FeatureOperations = NS(NewBodyFeatureOperation=0, CutFeatureOperation=1)
        adapter = object.__new__(self.mod.FusionAdapter)
        adapter.root = Mock()
        adapter._rectangle_profile = Mock()
        adapter._extrude = Mock()
        for panel in assembly.panels:
            adapter._make_panel(panel)
            self.assertEqual(adapter._rectangle_profile.call_args.kwargs,
                dict(x_dynamic=bool(panel.box.origin[0].refs()),
                     y_dynamic=bool(panel.box.origin[1].refs())))
        for op in assembly.operations:
            adapter._make_dado(op, Mock())
            self.assertEqual(adapter._rectangle_profile.call_args.kwargs,
                dict(x_dynamic=bool(op.cut.origin[0].refs()),
                     y_dynamic=bool(op.cut.origin[1].refs())))
