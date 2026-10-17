"""Bounded base@1 shelf-count planning; generator-derived, CAD neutral."""
import json
import math

from .width_change import _boxes, _norm, expected_expressions

JOURNAL_KEY = "structural_shelf_count"


def plan_shelf_count_change(g3, state, new_shelf_count):
    refusals = []
    plan = {"new_shelf_count": new_shelf_count, "refusals": refusals}
    if type(new_shelf_count) is not int or new_shelf_count not in (1, 2):
        refusals.append("new_shelf_count must be integer 1 or 2")
        return plan
    try:
        old = g3["design_spec"].load_design_spec(state["stored_text"])
        spec = old.resolved_params
        default = g3["variants"].profile_defaults_spec(g3["variants"].get_profile("base", 1))
        actual, wanted = spec.to_dict()["parameters"], default.to_dict()["parameters"]
        actual.pop("shelf_count"); wanted.pop("shelf_count")
        if (old.original_schema, old.variant, old.profile_version) != ("0.2", "base", 1):
            refusals.append("only schema0.2 base@1 is supported")
        if actual != wanted or spec.shelf_count not in (1, 2):
            refusals.append("only the default base fixture with 1 or 2 shelves is supported")
        if spec.shelf_count == new_shelf_count:
            refusals.append("no-op shelf count")
        old_asm = g3["variants"].build_variant(spec, old.profile)
        old_expr = expected_expressions(g3, old_asm)
        old_env = old_asm.parameters.resolve()
        live = state["live_params"]
        if set(live) != set(old_expr):
            refusals.append("missing or extra user parameters")
        for name, expression in old_expr.items():
            p = live.get(name, {})
            value = p.get("value_mm")
            if (p.get("unit") != "mm" or _norm(p.get("expression")) != _norm(expression)
                    or type(value) not in (int, float) or not math.isfinite(value)
                    or abs(value - old_env[name]) > 1e-6):
                refusals.append("parameter drift: " + name)
        if state.get("ownership_verified") is not True:
            refusals.append("ownership receipt missing or live structure diverged")
        refusals.extend(state.get("ownership_errors", []))
        raw = json.loads(old.canonical_stored_spec_json)
        raw["parameters"]["shelf_count"] = new_shelf_count
        new = g3["design_spec"].load_design_spec(json.dumps(raw))
        new_asm = g3["variants"].build_variant(new.resolved_params, new.profile)
        new_expr = expected_expressions(g3, new_asm)
        new_env = new_asm.parameters.resolve()
        ob, nb = _boxes(old_asm, old_env), _boxes(new_asm, new_env)
        plan.update(old_shelf_count=spec.shelf_count,
                    old_design_spec_hash=old.design_spec_hash, new_design_spec_hash=new.design_spec_hash,
                    new_stored_text=new.canonical_stored_spec_json,
                    parameter_expressions={n: {"old": old_expr.get(n), "new": new_expr.get(n)}
                                           for n in sorted(set(old_expr) | set(new_expr))
                                           if old_expr.get(n) != new_expr.get(n)},
                    geometry_changes={n: {"old": ob.get(n), "new": nb.get(n)}
                                      for n in sorted(set(ob) | set(nb)) if ob.get(n) != nb.get(n)},
                    expected_after_mm=new_env,
                    panel_ids=[p.stable_id for p in new_asm.panels],
                    cut_targets={o.operation_id: o.target_panel_id for o in new_asm.operations},
                    expected_counts={"user_parameters": len(new_expr), "root_occurrences": len(new_asm.panels),
                                     "all_components": len(new_asm.panels) + 1,
                                     "timeline_items": 3 * len(new_asm.panels) + 2 * len(new_asm.operations)})
    except Exception as exc:
        refusals.append("cannot establish safe shelf change: %s" % exc)
    return plan


def equivalent(a, b, tolerance=1e-6):
    """Finite measured evidence comparison; unavailable values never compare equal."""
    if a is None or b is None:
        return False
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(equivalent(a[k], b[k], tolerance) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(equivalent(x, y, tolerance) for x, y in zip(a, b))
    if type(a) in (int, float):
        return type(b) in (int, float) and math.isfinite(a) and math.isfinite(b) and abs(a-b) <= tolerance
    return a == b
