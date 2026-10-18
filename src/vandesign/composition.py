"""Explicit fixed-pair V6.2 -> symbolic composition, offline only.

No adapter calls or persistence. Manifest JSON is immutable evidence, NOT a
cabinet spec and NOT suitable for the singular cabinet stored-spec attribute.
"""
from dataclasses import dataclass, replace
import hashlib
import math

from .cad.protocol import preflight
from .components.ids import make_id
from .components.model import AssemblyDefinition
from .core.expr import Expr, Mm, Param
from .core.geometry import Box, BoxExpr
from .core.params import ParamDef, ParameterSet
from .layout_preview import make_layout
from .modules.bed_platform import build_bed_platform
from .modules.variants import build_variant
from .panel_preview import canonical_json
from .schemas.bed_platform_spec import load_bed_spec
from .schemas.design_spec import load_design_spec

FORMAT = "vandesign.fixed-pair-composition/1"
ASSEMBLY_ID = "composition.bed_base.001"


@dataclass(frozen=True)
class Composition:
    assembly: AssemblyDefinition
    manifest_json: str


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _shift(box, xyz):
    return BoxExpr(tuple(origin + (offset if isinstance(offset, Expr) else Mm(offset))
                         for origin, offset in zip(box.origin, xyz)),
                   box.size)


def _check_box(box, expected):
    target = Box(tuple(expected['lo_mm']), tuple(expected['hi_mm']))
    _require(all(math.isfinite(v) for v in box.lo + box.hi + box.size + (box.volume,))
             and all(v > 0 for v in box.size), 'Invalid composed box')
    _require(box.max_deviation(target)[0] <= 1e-9
             and math.isclose(box.volume, expected['volume_mm3'], rel_tol=1e-12, abs_tol=1e-6),
             'Composed bounds/volume differ from validated layout')


def compose_layout(snapshot, *, editable_placement=False):
    """Fail closed on changed/incomplete V6.2 data; return no CAD side effects."""
    _require(type(editable_placement) is bool, 'editable_placement must be boolean')
    _require(isinstance(snapshot, dict), 'V6.2 snapshot must be an object')
    entries = snapshot.get('instances')
    _require(isinstance(entries, list) and len(entries) == 2, 'Fixed pair required')
    _require(all(isinstance(i, dict) and 'instance_id' in i and 'translation_mm' in i
                 for i in entries), 'Incomplete instance placement')
    layout = make_layout([{'instance_id': i['instance_id'], 'translation_mm': i['translation_mm']}
                          for i in entries])
    _require(canonical_json(snapshot) == canonical_json(layout),
             'Snapshot/source specification, hash or geometry mismatch')

    panels, operations, constraints, parameters, sources = [], [], [], [], []
    for entry in layout['instances']:
        instance = entry['instance_id']
        text = entry['specification']['canonical_json']
        if instance == 'bed.001':
            source = build_bed_platform(load_bed_spec(text))
        else:
            spec = load_design_spec(text)
            source = build_variant(spec.resolved_params, spec.profile)
        preflight(source)
        _require(source.spec_hash == entry['assembly_spec_hash']
                 and source.assembly_id == entry['assembly_id'], 'Source identity mismatch')
        env = source.parameters.resolve()
        _require(env == entry['parameters_mm'], 'Source parameters mismatch')
        parameters.extend(source.parameters.params)
        xyz = entry['translation_mm']
        offsets = xyz
        if editable_placement and instance == 'cabinet.001':
            parameters.extend((ParamDef('Cab_Pos_X', value_mm=xyz[0]),
                               ParamDef('Cab_Pos_Y', value_mm=xyz[1])))
            env.update(Cab_Pos_X=xyz[0], Cab_Pos_Y=xyz[1])
            offsets = (Param('Cab_Pos_X'), Param('Cab_Pos_Y'), xyz[2])
        expected_panels = {p['local_panel_id']: p for p in entry['panels']}
        _require({p.stable_id for p in source.panels} == set(expected_panels), 'Panel inventory mismatch')
        panel_map = {p.stable_id: make_id(instance, p.stable_id) for p in source.panels}
        panel_records, cut_records, constraint_records = [], [], []
        for panel in source.panels:
            expected = expected_panels[panel.stable_id]
            _check_box(panel.box.resolve(env), expected['local_box'])
            moved = replace(panel, stable_id=panel_map[panel.stable_id], box=_shift(panel.box, offsets))
            _check_box(moved.box.resolve(env), expected['world_box'])
            panels.append(moved)
            panel_records.append({'local_id': panel.stable_id, 'composed_id': moved.stable_id,
                                  'world_box': expected['world_box'],
                                  'origin_expressions': [e.render() for e in moved.box.origin],
                                  'size_expressions': [e.render() for e in moved.box.size]})
        expected_ops = {o['operation_id']: o for o in entry['operations']}
        _require({o.operation_id for o in source.operations} == set(expected_ops), 'Cut inventory mismatch')
        for op in source.operations:
            expected = expected_ops[op.operation_id]
            _require(instance == 'cabinet.001' and op.side in ('left', 'right')
                     and op.target_panel_id == 'panel.' + op.side + '.001'
                     and op.mating_panel_id == 'panel.shelf.001'
                     and op.target_panel_id == expected['target_panel_id']
                     and op.mating_panel_id == expected['mating_panel_id'], 'Invalid source cut ownership')
            _check_box(op.cut.resolve(env), expected['local_cut'])
            moved = replace(op, operation_id=make_id(instance, op.operation_id),
                            target_panel_id=panel_map[op.target_panel_id],
                            mating_panel_id=panel_map[op.mating_panel_id], cut=_shift(op.cut, offsets))
            _require(moved.target_panel_id == instance + '.' + op.target_panel_id
                     and moved.mating_panel_id == instance + '.' + op.mating_panel_id,
                     'Cross-instance/remapped cut ownership mismatch')
            _check_box(moved.cut.resolve(env), expected['world_cut'])
            operations.append(moved)
            cut_records.append({'local_id': op.operation_id, 'composed_id': moved.operation_id,
                                'local_target_id': op.target_panel_id, 'local_mating_id': op.mating_panel_id,
                                'target_id': moved.target_panel_id, 'mating_id': moved.mating_panel_id,
                                'world_cut': expected['world_cut'],
                                'origin_expressions': [e.render() for e in moved.cut.origin],
                                'size_expressions': [e.render() for e in moved.cut.size]})
        local_constraints = [c.constraint_id for c in source.constraints]
        _require(len(set(local_constraints)) == len(local_constraints), 'Duplicate source constraint IDs')
        for constraint in source.constraints:
            moved = replace(constraint, constraint_id=make_id(instance, constraint.constraint_id))
            constraints.append(moved)
            constraint_records.append({'local_id': constraint.constraint_id, 'composed_id': moved.constraint_id,
                                       'lhs': moved.lhs.render(), 'op': moved.op, 'rhs': moved.rhs.render()})
        sources.append({'instance_id': instance, 'translation_mm': xyz,
                        'specification': entry['specification'], 'assembly_spec_hash': source.spec_hash,
                        'panels': sorted(panel_records, key=lambda p: p['local_id']),
                        'operations': sorted(cut_records, key=lambda o: o['local_id']),
                        'constraints': sorted(constraint_records, key=lambda c: c['local_id'])})

    params = ParameterSet(tuple(parameters))  # Reject duplicates/invalid dependency order.
    _require(len(panels) == 11 and len(operations) == 2, 'Expected eleven panels and two dados')
    _require({o.target_panel_id for o in operations} ==
             {'cabinet.001.panel.left.001', 'cabinet.001.panel.right.001'}, 'Incorrect cabinet cut participants')
    ids = [p.stable_id for p in panels] + [o.operation_id for o in operations] + [c.constraint_id for c in constraints]
    _require(len(ids) == len(set(ids)), 'Ambiguous composed identities')
    manifest = {
        'format': FORMAT, 'assembly_id': ASSEMBLY_ID, 'unit': 'mm', 'sources': sources,
        'parameters': [{'name': p.name, 'value_mm': p.value_mm,
                        'expression': p.expr.render() if p.expr else None} for p in params.params],
        'inventory': {'panels': 11, 'cabinet_dados': 2},
        'layout_sha256': hashlib.sha256(canonical_json(layout).encode()).hexdigest(),
        'collision': layout['collision'], 'qualification': layout['qualification'],
        'metadata_scope': 'read-only offline provenance; not cabinet stored-spec or native Fusion attributes',
        'hash_scheme': 'fixed-pair-composition-1-canonical-sha256',
    }
    manifest_json = canonical_json(manifest)
    assembly = AssemblyDefinition(ASSEMBLY_ID, hashlib.sha256(manifest_json.encode()).hexdigest(),
                                  params, tuple(panels), tuple(operations), tuple(constraints))
    preflight(assembly)
    return Composition(assembly, manifest_json)


def preview_cabinet_placement(assembly, base_values, x_mm, y_mm):
    """Pure bounded preview. Occupied envelopes include the bed's empty underside.

    This is a guarded Runner move, not a watcher for raw Fusion parameter edits.
    No changes are applied here; rejected/missing inputs cannot authorise a move.
    """
    for value in (x_mm, y_mm):
        _require(type(value) in (int, float) and math.isfinite(value)
                 and abs(value) <= 10000, 'Placement must be finite millimetres within ±10000')
    names = {p.name for p in assembly.parameters.base()}
    _require({'Cab_Pos_X', 'Cab_Pos_Y'} <= names, 'Composition has no editable placement')
    _require(set(base_values) == names, 'Complete current base parameters required')
    _require(all(type(v) in (int, float) and math.isfinite(v) for v in base_values.values()),
             'Invalid current parameter observation')
    proposed = dict(base_values, Cab_Pos_X=x_mm, Cab_Pos_Y=y_mm)
    env = assembly.parameters.resolve(proposed)
    _require(all(ok for _, ok, _, _ in assembly.check_constraints(env)), 'Invalid proposed dimensions')
    envelopes = {}
    for instance in ('bed.001', 'cabinet.001'):
        boxes = [p.box.resolve(env) for p in assembly.panels if p.stable_id.startswith(instance+'.')]
        _require(bool(boxes), 'Missing occupied-envelope panels')
        _require(all(math.isfinite(v) for b in boxes for v in b.lo+b.hi), 'Invalid occupied bounds')
        envelopes[instance] = Box(tuple(min(b.lo[i] for b in boxes) for i in range(3)),
                                  tuple(max(b.hi[i] for b in boxes) for i in range(3)))
    overlap = envelopes['bed.001'].overlap_volume(envelopes['cabinet.001'])
    return dict(outcome='REFUSED' if overlap > 0 else 'PASS',
                reason='Occupied envelopes overlap' if overlap > 0 else 'Occupied envelopes clear',
                overlap_mm3=overlap, parameters_mm=env,
                envelopes_mm={k: dict(min=v.lo, max=v.hi) for k,v in envelopes.items()})
