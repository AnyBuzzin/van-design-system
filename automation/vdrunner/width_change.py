"""G4 first feature: plan a safe WIDTH change of an existing VanDesign cabinet.

Pure Python (no ``adsk``).  It uses the verified G3 code passed in as ``g3``
(``design_spec``, ``variants`` and ``expr`` modules) so the business rules are
never duplicated:

* the stored spec is parsed by the G3 loader;
* the expected live Fusion parameter expressions are rendered by the G3
  generator (``build_variant``) exactly as the adapter wrote them at build time;
* the new stored spec, its canonical text and hash come from the G3 loader.

``plan_width_change`` never touches Fusion.  It returns a preview (old/new
values, every affected parameter and panel/cut) and a list of refusal reasons;
an update may only proceed when that list is empty.
"""

from __future__ import annotations

import json
from typing import Dict, List, Mapping, Optional

TOL_MM = 1e-6


def _norm(expr) -> str:
    """Fusion re-spaces expressions ("( a - b )"); compare token text only."""
    return "".join(str(expr or "").split())


def expected_expressions(g3, assembly) -> Dict[str, str]:
    """Fusion expression text the G3 adapter writes for every parameter."""
    fmt = g3["expr"]._fmt
    out = {}
    for p in assembly.parameters.params:
        out[p.name] = ("%s mm" % fmt(p.value_mm)) if p.is_base else p.expr.render()
    return out


def _with_width(stored_text: str, new_width_mm: float) -> str:
    doc = json.loads(stored_text)
    if not isinstance(doc.get("parameters"), dict) or "width_mm" not in doc["parameters"]:
        raise ValueError("stored spec has no parameters.width_mm")
    doc["parameters"]["width_mm"] = float(new_width_mm)
    return json.dumps(doc)


def _boxes(assembly, env) -> Dict[str, Dict]:
    out = {}
    for p in assembly.panels:
        b = p.box.resolve(env)
        out[p.stable_id] = {"min": [round(v, 6) for v in b.lo], "max": [round(v, 6) for v in b.hi],
                            "size": [round(v, 6) for v in b.size]}
    for op in assembly.operations:
        b = op.cut.resolve(env)
        out[op.operation_id] = {"min": [round(v, 6) for v in b.lo], "max": [round(v, 6) for v in b.hi],
                                "size": [round(v, 6) for v in b.size]}
    return out


def plan_width_change(g3, stored_text: str, live_params: Mapping[str, Mapping], new_width_mm: float,
                      edit_bounds_mm: Optional[List[float]] = None) -> Dict:
    """live_params: {name: {"expression": str, "value_mm": float}} read from Fusion."""
    refusals: List[str] = []
    plan: Dict = {"new_width_mm": float(new_width_mm), "refusals": refusals}
    ds_mod, var_mod = g3["design_spec"], g3["variants"]

    # 1. the saved specification
    try:
        old = ds_mod.load_design_spec(stored_text)
    except Exception as e:
        refusals.append("stored specification cannot be loaded: %s" % e)
        return plan
    old_spec = old.resolved_params
    plan.update(variant="%s@%d" % (old.variant, old.profile_version), schema=old.original_schema,
                old_width_mm=old_spec.width_mm, old_design_spec_hash=old.design_spec_hash,
                hash_scheme=old.hash_scheme)
    old_asm = var_mod.build_variant(old_spec, old.profile)
    old_env = old_asm.parameters.resolve()
    want_expr = expected_expressions(g3, old_asm)

    # 2. unexpected modifications: every managed parameter must be exactly what the
    #    stored spec generates (expression text AND value); no missing parameters.
    drift = []
    for name, expr in want_expr.items():
        live = live_params.get(name)
        if live is None:
            drift.append("%s missing in the design" % name)
            continue
        if _norm(live.get("expression")) != _norm(expr):
            drift.append("%s expression %r != generated %r" % (name, live.get("expression"), expr))
        if live.get("value_mm") is None or abs(float(live["value_mm"]) - old_env[name]) > TOL_MM:
            drift.append("%s value %s != stored-spec value %s" % (name, live.get("value_mm"), old_env[name]))
    extra = sorted(n for n in live_params if n.startswith("Cab_") and n not in want_expr)
    if extra:
        drift.append("unexpected extra Cab_* parameters: %s" % extra)
    plan["drift"] = drift
    if drift:
        refusals.append("design differs from its stored specification (manual or unknown edits): %d difference(s)" % len(drift))

    # 3. the proposed change
    if abs(new_width_mm - old_spec.width_mm) <= TOL_MM:
        refusals.append("new width equals current width %.4g mm; nothing to do" % old_spec.width_mm)
    if edit_bounds_mm and not edit_bounds_mm[0] <= new_width_mm <= edit_bounds_mm[1]:
        refusals.append("new width %.4g mm outside allowed edit bounds %s" % (new_width_mm, edit_bounds_mm))
    try:
        new = ds_mod.load_design_spec(_with_width(old.canonical_stored_spec_json, new_width_mm))
    except Exception as e:
        refusals.append("new specification rejected by the G3 loader: %s" % e)
        return plan
    lim = var_mod.profile_limits(new.profile).get("Cab_Width")
    if lim and not lim[0] <= new_width_mm <= lim[1]:
        refusals.append("width %.4g mm outside %s profile range %s" % (new_width_mm, plan["variant"], list(lim)))
    new_asm = var_mod.build_variant(new.resolved_params, new.profile)
    new_env = new_asm.parameters.resolve()
    failed = [c.constraint_id for c, ok, _, _ in new_asm.check_constraints(new_env) if not ok]
    if failed:
        refusals.append("new cabinet violates constraints: %s" % failed)
    new_expr = expected_expressions(g3, new_asm)
    changed_expr = sorted(n for n in new_expr if new_expr[n] != want_expr.get(n))
    if changed_expr != ["Cab_Width"]:
        refusals.append("width change would alter parameter formulas %s; only Cab_Width may change" % changed_expr)
    if [p.stable_id for p in new_asm.panels] != [p.stable_id for p in old_asm.panels] or \
            [o.operation_id for o in new_asm.operations] != [o.operation_id for o in old_asm.operations]:
        refusals.append("width change would alter the component/cut structure; not a scalar update")

    ob, nb = _boxes(old_asm, old_env), _boxes(new_asm, new_env)
    plan.update(
        new_design_spec_hash=new.design_spec_hash,
        new_stored_text=new.canonical_stored_spec_json,
        new_expression=new_expr["Cab_Width"],
        parameter_changes={n: [round(old_env[n], 6), round(new_env[n], 6)] for n in new_env if abs(new_env[n] - old_env[n]) > TOL_MM},
        unchanged_parameters=sorted(n for n in new_env if abs(new_env[n] - old_env[n]) <= TOL_MM),
        geometry_changes={k: {"old": ob[k], "new": nb[k]} for k in nb if ob[k] != nb[k]},
        unchanged_geometry=sorted(k for k in nb if ob[k] == nb[k]),
        expected_after_mm={n: round(new_env[n], 6) for n in new_env},
        stable_ids=[p.stable_id for p in new_asm.panels],
    )
    return plan
