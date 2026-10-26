"""Plan a generic arrangement build: everything is validated before any CAD write.

A request is plain JSON (one Runner job argument):

    {"arrangement": {"schema_version": "vandesign.arrangement/1", "instances": [...]},
     "envelope":    {"schema_version": "vandesign.lined-envelope/1", "parameters": {...}},
     "edits":       [{"parameter": "K1_Cab_Width", "value_mm": 1000, "expect": "pass"},
                     {"parameter": "K1_Pos_Y", "value_mm": 2100, "expect": "refused"}],
     "tool_diameter_mm": 6}            # optional: also write the DXF pack

Each edit is previewed here against the full model (constraints, cross-instance
collisions, envelope fit). A job whose previews disagree with its expectations
is refused before Fusion is touched. Edits are applied one at a time from the
baseline and restored before the next.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math

from .arrangement import ArrangementError, build_arrangement, collisions, load_arrangement
from .core.expr import ExprError
from .core.params import ParameterError
from .schemas.envelope_spec import load_envelope_spec

MAX_EDITS = 6
_REQUEST_KEYS = {"arrangement", "envelope", "edits"}
_EDIT_KEYS = {"parameter", "value_mm", "expect"}


@dataclass(frozen=True)
class Edit:
    parameter: str
    value_mm: float
    expect: str               # "pass" or "refused"
    preview: dict             # offline outcome and reason


@dataclass(frozen=True)
class Plan:
    arrangement: object       # arrangement.Arrangement
    envelope: object          # schemas.envelope_spec.EnvelopeSpec
    edits: tuple
    tool_diameter_mm: float | None


def preview_values(arrangement, envelope, values):
    """Offline verdict for base-parameter ``values``: PASS or REFUSED with reason."""
    from .modules.test_envelope import preview_lined_fit
    asm = arrangement.assembly
    try:
        env = asm.parameters.resolve(values)
        failed = [c.constraint_id for c, ok, _, _ in asm.check_constraints(env) if not ok]
        if failed:
            return dict(outcome="REFUSED", reason="constraint violations: " + ", ".join(failed))
        boxes = {p.stable_id: p.box.resolve(env) for p in asm.panels}
        hits = collisions(asm, env, arrangement.owners)
        if hits:
            return dict(outcome="REFUSED", reason="instances share material: %s / %s" % hits[0])
        preview_lined_fit(asm, envelope, env, boxes)
    except (ValueError, ParameterError, ExprError) as exc:
        return dict(outcome="REFUSED", reason=str(exc))
    return dict(outcome="PASS", reason="constraints, collisions and envelope fit pass")


def plan_request(request):
    """Validate a request fully and return a Plan, or raise ArrangementError."""
    if not isinstance(request, dict) or not (_REQUEST_KEYS <= set(request) <= _REQUEST_KEYS | {"tool_diameter_mm"}):
        raise ArrangementError("Request needs arrangement, envelope, edits and optional tool_diameter_mm")
    try:
        text = json.dumps(request, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ArrangementError("Request must be finite JSON") from exc
    if len(text) > 262144:
        raise ArrangementError("Request larger than 256 KiB")
    instances = load_arrangement(json.dumps(request["arrangement"]))
    try:
        envelope = load_envelope_spec(json.dumps(request["envelope"]))
    except ValueError as exc:
        raise ArrangementError("Invalid envelope: %s" % exc) from None
    arrangement = build_arrangement(instances, envelope)  # refuses collisions and misfit
    tool = request.get("tool_diameter_mm")
    if tool is not None and (type(tool) not in (int, float) or not math.isfinite(tool) or not 0 < tool <= 50):
        raise ArrangementError("tool_diameter_mm must be a finite number in (0, 50]")
    raw = request["edits"]
    if not isinstance(raw, list) or len(raw) > MAX_EDITS:
        raise ArrangementError("edits must be a list of at most %d" % MAX_EDITS)
    base = {p.name: p.value_mm for p in arrangement.assembly.parameters.base()}
    edits = []
    for item in raw:
        if not isinstance(item, dict) or set(item) != _EDIT_KEYS:
            raise ArrangementError("Each edit needs exactly parameter, value_mm, expect")
        name, value, expect = item["parameter"], item["value_mm"], item["expect"]
        if name not in base:
            raise ArrangementError("Edit parameter %r is not an editable base parameter" % (name,))
        if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 100000:
            raise ArrangementError("Edit value_mm must be a finite number")
        if value == base[name]:
            raise ArrangementError("Edit of %s does not change it" % name)
        if expect not in ("pass", "refused"):
            raise ArrangementError("Edit expect must be 'pass' or 'refused'")
        preview = preview_values(arrangement, envelope, dict(base, **{name: float(value)}))
        if (preview["outcome"] == "PASS") != (expect == "pass"):
            raise ArrangementError("Edit %s=%s expected %s but preview gives %s (%s)"
                                   % (name, value, expect, preview["outcome"], preview["reason"]))
        edits.append(Edit(name, float(value), expect, preview))
    return Plan(arrangement, envelope, tuple(edits), None if tool is None else float(tool))
