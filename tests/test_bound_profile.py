"""Offline API-contract checks, not a sketch solver or live CAD evidence."""
import math
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import test_profile_fixture as fixture
from test_width_bindings import module, spec
from vandesign.core.expr import Mm, Param
from vandesign.manufacturing.carcass import cabinet_tab_slot_width_bindings


class Point:
    def __init__(self, xyz):
        self.xyz = xyz
        self.geometry = NS(x=xyz[0], y=xyz[1], z=xyz[2])
        self.isFixed = False
        self.isFullyConstrained = True


class Sketch:
    def __init__(self):
        self.points, self.lines, self.arcs, self.dimensions, self.parallel = [], [], [], [], []
        self.sketchPoints = NS(add=self.point)
        self.sketchCurves = NS(sketchLines=NS(addByTwoPoints=self.line),
                              sketchArcs=NS(addByCenterStartSweep=self.arc))
        self.sketchDimensions = NS(addDistanceDimension=self.distance, addRadialDimension=self.radius)
        self.geometricConstraints = NS(addParallel=self.direction)
        self.profiles = NS(count=1)
        self.isFullyConstrained = True

    def point(self, xyz):
        p = Point(xyz); self.points.append(p); return p

    def line(self, a, b):
        line = NS(startSketchPoint=a if isinstance(a, Point) else self.point(a),
                  endSketchPoint=b if isinstance(b, Point) else self.point(b),
                  isFixed=False, isConstruction=False)
        self.lines.append(line)
        return line

    def arc(self, c, start, sweep):
        r = math.dist(c, start); angle = math.atan2(start[1]-c[1], start[0]-c[0])
        end = (c[0]+r*math.cos(angle+sweep), c[1]+r*math.sin(angle+sweep), 0)
        if sweep < 0:
            start, end = end, start  # Autodesk always returns a CCW arc.
        a = NS(centerSketchPoint=self.point(c), startSketchPoint=self.point(start),
               endSketchPoint=self.point(end), sweep=sweep, isFixed=False)
        self.arcs.append(a)
        return a

    def distance(self, anchor, p, orientation, text):
        d = NS(parameter=NS(expression=None), anchor=anchor, point=p, axis=orientation)
        self.dimensions.append(d)
        return d

    def radius(self, arc, text):
        d = NS(parameter=NS(expression=None)); arc.radial = d
        return d

    def direction(self, a, b):
        self.parallel.append((a, b))
        return object()


class BoundProfile(unittest.TestCase):
    def setUp(self):
        fixture.ProfileAPI.setUp(self)
        self.fake.fusion.DimensionOrientations = NS(HorizontalDimensionOrientation=0,
                                                     VerticalDimensionOrientation=1)
        self.asm, joinery = module(spec())
        self.bindings = cabinet_tab_slot_width_bindings(self.asm, joinery)
        self.env = self.asm.parameters.resolve()
        self.ends = tuple(self.asm.parameters.resolve({'Cab_Width': w}) for w in (1000, 1100))
        self.compiler = self.adapter.ProfileAdapter.__new__(self.adapter.ProfileAdapter)

    def compile(self, loop, offset=(Mm(-1500), -Param('Cab_Width')),
                sketch=None, ends=None):
        sketch = sketch or Sketch()
        comp = NS(sketches=NS(add=Mock(return_value=sketch)), xYConstructionPlane=object())
        result = self.compiler._bound_loop_sketch(comp, 'test', loop, offset, self.env,
                                                  self.ends if ends is None else ends, Mock())
        self.assertIs(result, sketch)
        return sketch

    @staticmethod
    def value(expression, env):
        # Only locally generated trusted Expr.render output, never user input.
        return eval(expression.replace(' mm', ''), {'__builtins__': {}}, env)

    def test_all_producer_loops_keep_native_expressions_and_shared_endpoints(self):
        changed = 0
        for b in self.bindings.values():
            for loop in [b.outline] + [f.loop for f in b.features]:
                sketch = self.compile(loop)
                self.assertEqual(len(sketch.arcs), sum(s[0] == 'arc' for s in loop.sources))
                material = [line for line in sketch.lines if not line.isConstruction]
                self.assertEqual(len(material), sum(s[0] == 'line' for s in loop.sources))
                for d in sketch.dimensions:
                    self.assertFalse(d.point.isFixed)
                    distance = self.value(d.parameter.expression, self.env)
                    self.assertAlmostEqual(distance / 10, d.point.xyz[d.axis]-d.anchor.xyz[d.axis])
                    values = [self.value(d.parameter.expression, e) for e in self.ends]
                    self.assertTrue(all(v > 0 for v in values))
                    changed += values[0] != values[1]
                # Re-evaluate every native coordinate at edit/intermediate/
                # restoration widths against producer provenance, not just a
                # check that an expression happens to mention the parameter.
                grouped = {}
                for d in sketch.dimensions:
                    grouped.setdefault(d.point, {})[d.axis] = d
                sources = [s[1] for s in loop.sources]
                sources += [s[2] for s in loop.sources if s[0] == 'line']
                for p, dims in grouped.items():
                    candidates = []
                    for i, delta in sources:
                        xy = (loop.vertices[i][0] + Mm(delta[0]-1500),
                              loop.vertices[i][1] + Mm(delta[1]) - Param('Cab_Width'))
                        if all(abs(xy[j].eval(self.env)-p.xyz[j]*10) < 1e-6 for j in range(2)):
                            candidates.append(xy)
                    self.assertTrue(candidates)
                    for width in (1000, 1050, 1100, 1000, 1100):
                        env = self.asm.parameters.resolve({'Cab_Width': width})
                        actual = [dims[j].anchor.xyz[j]*10 + self.value(dims[j].parameter.expression, env)
                                  for j in range(2)]
                        self.assertTrue(any(all(abs(xy[j].eval(env)-actual[j]) < 1e-6 for j in range(2))
                                            for xy in candidates))
                for arc in sketch.arcs:
                    self.assertFalse(arc.isFixed)
                    for p in (arc.startSketchPoint, arc.endSketchPoint):
                        self.assertFalse(p.isFixed)
                        self.assertEqual(sum(p is line.startSketchPoint or p is line.endSketchPoint
                                             for line in material), 1)
                    self.assertEqual(sum(ray.startSketchPoint is arc.centerSketchPoint
                                         for ray, ref in sketch.parallel), 2)
                self.assertTrue(all(not ray.isFixed and ref.isFixed for ray, ref in sketch.parallel))
                self.assertTrue(all(not line.isFixed for line in material))
        self.assertGreater(changed, 100)

    def test_negative_origins_and_all_signed_frame_axes_have_positive_dimensions(self):
        loop = self.bindings['panel.bottom.001'].outline
        axes = [tuple(sign if j == i else 0 for j in range(3)) for i in range(3) for sign in (-1, 1)]
        origin = (Mm(-2000), -Param('Cab_Width'), Mm(-500))
        for u in axes:
            for v in axes:
                if sum(a*b for a, b in zip(u, v)):
                    continue
                offset = tuple(sum((e*k for e, k in zip(origin, axis)), Mm(0)) for axis in (u, v))
                sketch = self.compile(loop, offset)
                for d in sketch.dimensions:
                    for width in (1000, 1050, 1100, 1000, 1100):
                        env = self.asm.parameters.resolve({'Cab_Width': width})
                        self.assertGreater(self.value(d.parameter.expression, env), 0)

    def test_failure_never_falls_back_to_fixed_profile_points(self):
        loop = self.bindings['panel.bottom.001'].outline
        for field, value in (('isFullyConstrained', False), ('isFullyConstrained', None),
                             ('profiles', NS(count=2))):
            s = Sketch(); setattr(s, field, value)
            with self.assertRaises(RuntimeError):
                self.compile(loop, sketch=s)
            self.assertTrue(all(not d.point.isFixed for d in s.dimensions))
        for method in ('addDistanceDimension', 'addRadialDimension'):
            s = Sketch(); setattr(s.sketchDimensions, method, Mock(return_value=None))
            with self.assertRaises(RuntimeError):
                self.compile(loop, sketch=s)
        s = Sketch(); s.geometricConstraints.addParallel = Mock(return_value=None)
        with self.assertRaises(RuntimeError):
            self.compile(loop, sketch=s)

    def test_clockwise_arc_api_normalisation_and_missing_readback(self):
        loop = self.bindings['panel.bottom.001'].outline
        self.assertTrue(any(s[0] == 'arc' and s[4] < 0 for s in loop.sources))
        sketch = self.compile(loop)
        material = [line for line in sketch.lines if not line.isConstruction]
        # Every material line retains the producer's direction despite Fusion's
        # reversed API endpoints on clockwise relief arcs.
        offset = (-1500, -1100)
        for line, seg in zip(material, (s for s in loop.resolve(self.env).segments
                                       if not hasattr(s, 'sweep'))):
            for point, expected in ((line.startSketchPoint, seg.start), (line.endSketchPoint, seg.end)):
                for i in range(2):
                    self.assertAlmostEqual(point.xyz[i]*10, expected[i]+offset[i])
        s = Sketch(); original = s.arc
        def wrong(*args):
            arc = original(*args)
            arc.startSketchPoint.geometry.x = float('nan')
            return arc
        s.sketchCurves.sketchArcs.addByCenterStartSweep = wrong
        with self.assertRaisesRegex(RuntimeError, 'readback'):
            self.compile(loop, sketch=s)
        with self.assertRaises(ValueError):
            self.compile(loop, ends=())


if __name__ == '__main__':
    unittest.main()
