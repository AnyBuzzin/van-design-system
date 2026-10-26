"""Ideal geometry derived from the model itself (offline oracle, never CAD evidence).

Implements the GeometrySource protocol from the assembly definition: each body
is its blank box minus the volume of its own cuts. Used to derive which checks
``validate`` produces for a model, and in offline tests.
"""
from __future__ import annotations

from .geometry_source import MeasuredBody


class ModelGeometrySource:
    def __init__(self, assembly, values=None):
        self.diagnostics = []
        self.env = assembly.parameters.resolve(values)
        self.boxes = {p.stable_id: p.box.resolve(self.env) for p in assembly.panels}
        self.cuts = {}
        for op in assembly.operations:
            self.cuts.setdefault(op.target_panel_id, []).append(op.cut.resolve(self.env))

    def parameter_value(self, name):
        return self.env.get(name)

    def body(self, panel_id):
        box = self.boxes.get(panel_id)
        if box is None:
            return None
        return MeasuredBody(box, box.volume - sum(box.overlap_volume(c) for c in self.cuts.get(panel_id, ())))

    def point_in_material(self, panel_id, p):
        inside = lambda b: all(b.lo[i] < p[i] < b.hi[i] for i in range(3))  # noqa: E731
        return inside(self.boxes[panel_id]) and not any(inside(c) for c in self.cuts.get(panel_id, ()))

    def interference_count(self, panel_ids):
        return 0

    def managed_ids(self):
        return {pid: 1 for pid in self.boxes}
