"""Immutable design records: Panel, DadoOperation, Constraint, AssemblyDefinition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Tuple

from ..core.expr import Expr
from ..core.geometry import BoxExpr, GeometryError, RoundedCornerOutline
from ..core.params import ParameterSet
from .ids import IdError, make_id


class StructureError(ValueError):
    """The assembly definition is inconsistent (raised BEFORE any CAD work)."""


class ConstraintViolation(ValueError):
    pass


@dataclass(frozen=True)
class Panel:
    stable_id: str
    display_name: str
    role: str
    material_ref: str
    box: BoxExpr
    grain_axis: Optional[str] = None  # not used yet
    # Excluded from Python hash to preserve existing rectangular Panel hashes;
    # equality still compares the shape. Unequal shapes may safely share a hash.
    corner_radius: Optional[Expr] = field(default=None, hash=False)


@dataclass(frozen=True)
class DadoOperation:
    """Open-front groove cut into ``target_panel_id`` to receive
    ``mating_panel_id``.  ``cut`` is the removed volume."""

    operation_id: str
    target_panel_id: str
    mating_panel_id: str
    side: str  # 'left' or 'right' (which side of the cabinet the groove is on)
    cut: BoxExpr
    groove_depth: Expr
    end_clearance: Expr
    slot_clearance: Expr
    open_at: str = "front"
    process: str = "cnc_pocket"
    # Module frame: quarter-turns about Z from the cabinet-local frame (X =
    # groove depth, Y = front-to-back, Z = up). Verification works in it.
    quarter_turns: int = 0


@dataclass(frozen=True)
class Constraint:
    constraint_id: str
    description: str
    lhs: Expr
    op: str  # '>' or '>='
    rhs: Expr

    def evaluate(self, env: Mapping[str, float]) -> Tuple[bool, float, float]:
        a, b = self.lhs.eval(env), self.rhs.eval(env)
        ok = a > b if self.op == ">" else a >= b
        return ok, a, b


@dataclass(frozen=True)
class AssemblyDefinition:
    assembly_id: str
    spec_hash: str
    parameters: ParameterSet
    panels: Tuple[Panel, ...]
    operations: Tuple[DadoOperation, ...]
    constraints: Tuple[Constraint, ...] = ()

    def panel(self, panel_id: str) -> Panel:
        for p in self.panels:
            if p.stable_id == panel_id:
                return p
        raise StructureError("no panel with id %r" % panel_id)

    def check_constraints(self, env: Mapping[str, float]) -> List[Tuple[Constraint, bool, float, float]]:
        out = []
        for c in self.constraints:
            ok, a, b = c.evaluate(env)
            out.append((c, ok, a, b))
        return out

    def validate_structure(self) -> None:
        """Structural checks using default parameter values."""
        try:
            for p in self.panels:
                make_id(*p.stable_id.split("."))
            for o in self.operations:
                make_id(*o.operation_id.split("."))
        except IdError as e:
            raise StructureError(str(e)) from None

        ids = [p.stable_id for p in self.panels]
        if len(set(ids)) != len(ids):
            raise StructureError("duplicate panel ids")
        op_ids = [o.operation_id for o in self.operations]
        if len(set(op_ids)) != len(op_ids):
            raise StructureError("duplicate operation ids")

        names = set(self.parameters.names())
        refs = set()
        for p in self.panels:
            refs |= p.box.refs()
            if p.corner_radius is not None:
                if not isinstance(p.corner_radius, Expr):
                    raise StructureError('Rounded radius must be a length expression')
                refs |= p.corner_radius.refs()
        for o in self.operations:
            refs |= o.cut.refs() | o.groove_depth.refs()
            refs |= o.end_clearance.refs() | o.slot_clearance.refs()
        for c in self.constraints:
            refs |= c.lhs.refs() | c.rhs.refs()
        if refs - names:
            raise StructureError("undefined parameters: %s" % ", ".join(sorted(refs - names)))

        idset = set(ids)
        for o in self.operations:
            if not o.target_panel_id:
                raise StructureError("%s: empty target (cuts must name their target body)" % o.operation_id)
            if o.target_panel_id not in idset:
                raise StructureError("%s: unknown target panel %r" % (o.operation_id, o.target_panel_id))
            if o.mating_panel_id not in idset:
                raise StructureError("%s: unknown mating panel %r" % (o.operation_id, o.mating_panel_id))
            if o.target_panel_id == o.mating_panel_id:
                raise StructureError("%s: target and mating panel are the same" % o.operation_id)

        env = self.parameters.resolve()
        try:
            boxes: Dict[str, object] = {p.stable_id: p.box.resolve(env) for p in self.panels}
            for p in self.panels:
                if p.corner_radius is None:
                    if p.role == 'rounded_panel':raise GeometryError('Rounded panel requires a radius')
                    continue
                b = boxes[p.stable_id]
                if (len(self.panels)!=1 or self.operations or p.role!='rounded_panel'
                        or b.lo!=(0,0,0) or any(e.refs() for e in p.box.origin)
                        or b.size[2]!=18 or p.box.size[2].refs()):
                    raise GeometryError('E1.1 requires standalone local XY panel, fixed 18 mm, no cuts')
                RoundedCornerOutline(b.size[0], b.size[1], p.corner_radius.eval(env))
            cuts = [(o, o.cut.resolve(env)) for o in self.operations]
        except GeometryError as e:
            raise StructureError("default geometry invalid: %s" % e) from None
        for o, cut in cuts:
            if not boxes[o.target_panel_id].contains_box(cut):
                raise StructureError("%s: cut lies outside its target panel" % o.operation_id)
        for i, (oa, ca) in enumerate(cuts):
            for ob, cb in cuts[i + 1:]:
                if oa.target_panel_id == ob.target_panel_id and ca.overlap_volume(cb) > 0:
                    raise StructureError("%s and %s overlap on the same panel" % (oa.operation_id, ob.operation_id))
