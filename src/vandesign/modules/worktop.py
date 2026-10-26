"""One-piece L-shaped worktop (ADR-0003 kitchen): box model and editable parameters.

Module frame: the two back edges are x = 0 and y = 0 (against the walls).
Leg A runs along X (length WT_A_Length, depth WT_A_Depth); leg B runs along
Y (length WT_B_Length, depth WT_B_Depth); thickness is along Z. The box model
is the exact union of two boxes (panel.worktop.001 = leg A, panel.worktop.002
= the rest of leg B), so collision and envelope fit are exact. It is cut as
ONE profile (manufacturing.worktop). An optional sink cut-out lies inside one
leg with at least WT_Sink_Margin of worktop all round. Geometry only: no
load, heat or water qualification; the sink model is not chosen yet.
"""
from __future__ import annotations

import hashlib
import json
import math

from ..cad.protocol import preflight
from ..components.model import AssemblyDefinition, Constraint, Panel
from ..core.expr import Mm, Param
from ..core.geometry import BoxExpr
from ..core.params import ParamDef, ParameterSet

SCHEMA = "vandesign.worktop-l/1"
NOTICE = "Worktop: nominal geometry, unqualified"
_PARAMS = {  # spec key -> parameter
    "leg_a_length_mm": "WT_A_Length", "leg_a_depth_mm": "WT_A_Depth",
    "leg_b_length_mm": "WT_B_Length", "leg_b_depth_mm": "WT_B_Depth",
    "thickness_mm": "WT_Thickness", "front_corner_radius_mm": "WT_Front_Radius",
    "inside_corner_radius_mm": "WT_Inside_Radius"}
_SINK = {"leg": None, "centre_x_mm": "WT_Sink_X", "centre_y_mm": "WT_Sink_Y", "width_mm": "WT_Sink_Width",
         "length_mm": "WT_Sink_Length", "corner_radius_mm": "WT_Sink_Radius", "margin_mm": "WT_Sink_Margin"}


class WorktopSpecError(ValueError):
    pass


def _number(v, key):
    if type(v) not in (int, float) or not math.isfinite(v) or v < 0 or v > 10000:
        raise WorktopSpecError("%s must be a finite number in [0, 10000]" % key)
    return float(v)


def load_worktop_spec(text):
    """Strict JSON: {"schema_version", "material_ref", "parameters", "sink" (object or null)}."""
    raw = json.loads(text)
    if (not isinstance(raw, dict) or set(raw) != {"schema_version", "material_ref", "parameters", "sink"}
            or raw["schema_version"] != SCHEMA or not isinstance(raw["material_ref"], str)
            or not raw["material_ref"].strip() or not isinstance(raw["parameters"], dict)
            or set(raw["parameters"]) != set(_PARAMS)):
        raise WorktopSpecError("worktop spec needs schema_version %s, material_ref, parameters (%s) and sink"
                               % (SCHEMA, ", ".join(sorted(_PARAMS))))
    params = {_PARAMS[k]: _number(v, k) for k, v in raw["parameters"].items()}
    sink = raw["sink"]
    if sink is not None:
        if not isinstance(sink, dict) or set(sink) != set(_SINK) or sink["leg"] not in ("a", "b"):
            raise WorktopSpecError("sink needs leg ('a' or 'b') and " + ", ".join(sorted(k for k in _SINK if k != "leg")))
        params.update({p: _number(sink[k], k) for k, p in _SINK.items() if p})
    return dict(params=params, sink_leg=None if sink is None else sink["leg"], material_ref=raw["material_ref"],
                spec_hash=hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()).hexdigest())


def build_worktop(text):
    spec = load_worktop_spec(text)
    parameters = ParameterSet(tuple(ParamDef(n, value_mm=v, comment=NOTICE) for n, v in spec["params"].items()))
    la, da, lb, db, t, rf, ri = (Param(p) for p in _PARAMS.values())
    z = Mm(0)
    panels = (
        Panel("panel.worktop.001", "Worktop (leg A)", "worktop", spec["material_ref"], BoxExpr((z, z, z), (la, da, t))),
        Panel("panel.worktop.002", "Worktop (leg B)", "worktop", spec["material_ref"],
              BoxExpr((z, da, z), (db, lb - da, t))))
    c = [Constraint("worktop.leg_a", "leg A longer than leg B is deep", la, ">", db + ri + rf),
         Constraint("worktop.leg_b", "leg B longer than leg A is deep", lb, ">", da + ri + rf),
         Constraint("worktop.thickness", "positive thickness", t, ">", Mm(0)),
         Constraint("worktop.front_radius", "front corners fit their legs", da, ">", 2 * rf),
         Constraint("worktop.front_radius_b", "front corners fit their legs", db, ">", 2 * rf),
         Constraint("worktop.inside_radius", "a radiused inside corner", ri, ">", Mm(0))]
    if spec["sink_leg"] is not None:
        x, y, w, l, rs, m = (Param(p) for p in list(_SINK.values())[1:])
        # The sink lies inside one leg's rectangle (each includes the corner block).
        lo_x, hi_x = Mm(0), (la if spec["sink_leg"] == "a" else db)
        lo_y, hi_y = Mm(0), (da if spec["sink_leg"] == "a" else lb)
        c += [Constraint("worktop.sink_left", "sink margin to the worktop edge", x - w / 2, ">=", lo_x + m),
              Constraint("worktop.sink_right", "sink margin to the worktop edge", hi_x - m, ">=", x + w / 2),
              Constraint("worktop.sink_back", "sink margin to the worktop edge", y - l / 2, ">=", lo_y + m),
              Constraint("worktop.sink_front", "sink margin to the worktop edge", hi_y - m, ">=", y + l / 2),
              Constraint("worktop.sink_radius", "sink corners fit the cut-out", w, ">", 2 * rs),
              Constraint("worktop.sink_radius_l", "sink corners fit the cut-out", l, ">", 2 * rs),
              Constraint("worktop.sink_rounded", "radiused sink corners", rs, ">", Mm(0))]
    assembly = AssemblyDefinition("worktop.l.001", spec["spec_hash"], parameters, panels, (), tuple(c))
    preflight(assembly)
    return assembly


def sink_leg(text):
    return load_worktop_spec(text)["sink_leg"]
