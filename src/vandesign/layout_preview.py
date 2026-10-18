"""Fixed bed/base-cabinet nominal layout; never a compile-ready Fusion assembly.

make_layout accepts exactly two instance_id/translation_mm records. Invalid
inputs or occupied-envelope overlap raise ValueError; no partial PASS is emitted.
Serialize the result with panel_preview.canonical_json. No files or CAD touched.
"""
import math

from .cad.protocol import preflight
from .core.geometry import Box
from .modules.bed_platform import build_bed_platform
from .modules.variants import build_variant
from .panel_preview import make_preview
from .schemas.bed_platform_spec import BedPlatformSpec
from .schemas.design_spec import load_design_spec

FORMAT = "vandesign.two-module-layout/1"
INSTANCE_IDS = ("bed.001", "cabinet.001")
CONTACT_EPSILON_MM = 1e-9  # Existing Box.intersection boundary, not clearance.


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("translation must contain finite millimetre numbers")
    try:
        value = float(value)
    except OverflowError:
        raise ValueError("translation exceeds finite numeric range") from None
    if not math.isfinite(value):
        raise ValueError("translation must contain finite millimetre numbers")
    return 0.0 if value == 0 else value  # Canonicalize negative zero.


def _placements(records):
    if not isinstance(records, (list, tuple)) or len(records) != 2:
        raise ValueError("exactly one bed.001 and one cabinet.001 placement required")
    result = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != {"instance_id", "translation_mm"}:
            raise ValueError("placement requires only instance_id and translation_mm")
        identity = record["instance_id"]
        if not isinstance(identity, str) or identity not in INSTANCE_IDS or identity in result:
            raise ValueError("unknown or duplicate instance identity")
        xyz = record["translation_mm"]
        if not isinstance(xyz, (list, tuple)) or len(xyz) != 3:
            raise ValueError("translation_mm must be an XYZ triple")
        result[identity] = tuple(_number(v) for v in xyz)
    return result


def _box(box):
    values = box.lo + box.hi + box.size + (box.volume,)
    if not all(math.isfinite(v) for v in values) or any(v <= 0 for v in box.size):
        raise ValueError("nonfinite or nonpositive resolved box geometry")
    if box.volume <= 0:
        raise ValueError("nonpositive resolved volume")
    return {"lo_mm": list(box.lo), "hi_mm": list(box.hi), "volume_mm3": box.volume}


def _translate(box, xyz):
    _box(box)
    moved = Box(tuple(v + t for v, t in zip(box.lo, xyz)),
                tuple(v + t for v, t in zip(box.hi, xyz)))
    _box(moved)
    if any(abs(a - b) > CONTACT_EPSILON_MM for a, b in zip(box.size, moved.size)):
        raise ValueError("translation loses panel dimensions at numeric precision")
    return moved


def make_layout(placements, *, cabinet_spec_json=None):
    """Return independent module snapshots; refuse unsafe nominal placements."""
    translations = _placements(placements)
    bed = BedPlatformSpec()
    cabinet = load_design_spec(cabinet_spec_json if cabinet_spec_json is not None else
        '{"schema_version":"0.2","module":"cabinet@1",'
        '"variant":"base","profile_version":1,"parameters":{}}')
    if cabinet_spec_json is not None:
        cabinet = load_design_spec(cabinet.canonical_stored_spec_json)
    if cabinet.variant != "base":
        raise ValueError("Fixed layout requires a base cabinet")
    modules = (
        ("bed.001", bed.to_json(), build_bed_platform(bed)),
        ("cabinet.001", cabinet.canonical_stored_spec_json,
         build_variant(cabinet.resolved_params, cabinet.profile)),
    )
    instances, envelopes = [], []
    for identity, spec_text, assembly in modules:
        preflight(assembly)
        env = assembly.parameters.resolve()
        xyz = translations[identity]
        local = {p.stable_id: p.box.resolve(env) for p in assembly.panels}
        panels = [{"identity": [identity, sid], "local_panel_id": sid,
                   "local_box": _box(box), "world_box": _box(_translate(box, xyz))}
                  for sid, box in sorted(local.items())]
        envelope = Box(tuple(min(b.lo[i] for b in local.values()) for i in range(3)),
                       tuple(max(b.hi[i] for b in local.values()) for i in range(3)))
        world_envelope = _translate(envelope, xyz)
        envelopes.append(world_envelope)
        operations = []
        for op in sorted(assembly.operations, key=lambda o: o.operation_id):
            cut = op.cut.resolve(env)
            operations.append({
                "identity": [identity, op.operation_id],
                "operation_id": op.operation_id,
                "target_panel_id": op.target_panel_id,
                "mating_panel_id": op.mating_panel_id,
                "target_identity": [identity, op.target_panel_id],
                "mating_identity": [identity, op.mating_panel_id],
                "local_cut": _box(cut), "world_cut": _box(_translate(cut, xyz)),
            })
        preview = make_preview(spec_text)
        instances.append({
            "instance_id": identity, "translation_mm": list(xyz),
            "assembly_id": assembly.assembly_id,
            "assembly_spec_hash": assembly.spec_hash,
            "specification": preview["specification"],
            "parameters_mm": env,
            "parameter_expressions": {p.name: p.expr.render() if not p.is_base else None
                                      for p in assembly.parameters.params},
            "panels": panels, "operations": operations,
            "local_occupied_envelope": _box(envelope),
            "world_occupied_envelope": _box(world_envelope),
            "standalone_preview": preview,
        })
    overlap = envelopes[0].overlap_volume(envelopes[1])
    if not math.isfinite(overlap) or overlap < 0:
        raise ValueError("nonfinite or invalid occupied-envelope intersection")
    if overlap > 0:
        raise ValueError("REFUSED: bed/cabinet occupied envelopes overlap (bed void included)")
    return {
        "format": FORMAT, "unit": "mm", "instances": instances,
        "compile_ready_fusion_assembly": False,
        "collision": {"status": "PASS", "overlap_mm3": overlap,
                      "scope": "nominal whole occupied envelopes, including bed underside",
                      "contact_epsilon_mm": CONTACT_EPSILON_MM},
        "qualification": {"live_layout_geometry": "UNKNOWN", "access_clearance": "UNKNOWN",
                          "door_motion": "UNKNOWN", "fastening": "UNKNOWN",
                          "vehicle_fit": "UNKNOWN", "structural_load": "UNKNOWN",
                          "manufacturing": "UNKNOWN"},
    }
