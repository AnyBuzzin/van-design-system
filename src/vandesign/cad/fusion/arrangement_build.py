"""Generic owned-session build and verification of any arrangement (M1, #78).

One entry point for every furniture arrangement: no per-feature check counts.
Expected inventory is derived from the model (each panel adds an occurrence,
sketch and extrude; each cut a sketch and extrude). Cut ownership is read
without moving the timeline. Same guards as every other entry: a fresh empty
unsaved parametric document owned by this session, refusal before any write,
stop on failure, no retry and no automatic restoration.
"""
import json
from pathlib import Path

import adsk.core
import adsk.fusion

from .adapter import FusionAdapter
from .test_envelope import measure_test, snapshot
from ...arrangement import collisions
from ...arrangement_job import plan_request, preview_values
from ...core.geometry import Box
from ...modules.test_envelope import restored_lined_measurements

REPORT = "arrangement.json"


def expected_inventory(assembly):
    panels, cuts = len(assembly.panels), len(assembly.operations)
    return dict(panels=panels, timeline=3 * panels + 2 * cuts)


def measure_arrangement(design, plan, guard):
    asm = plan.arrangement.assembly
    inventory = expected_inventory(asm)
    report = measure_test(design, asm, guard, expected_panels=inventory["panels"],
                          expected_timeline=inventory["timeline"], read_only_ownership=True,
                          lined_spec=plan.envelope)
    boxes = {k: Box(tuple(v["min"]), tuple(v["max"])) for k, v in report["bodies"].items()}
    hits = collisions(asm, report["parameters_mm"], plan.arrangement.owners, boxes)
    report["checks"].append(dict(check_id="instances.no_shared_material",
                                 status="PASS" if not hits else "FAIL", observed=[list(h) for h in hits]))
    report["outcome"] = "PASS" if all(c["status"] == "PASS" for c in report["checks"]) else "FAIL"
    return report


def _export_dxf(plan, output_dir):
    from ...manufacturing.assembly import assembly_profiles
    from ...manufacturing.dxf import export_profiles
    profiles = assembly_profiles(plan.arrangement.assembly, tool_diameter=plan.tool_diameter_mm)
    files = export_profiles(profiles, str(Path(output_dir) / "dxf"))
    return dict(tool_diameter_mm=plan.tool_diameter_mm, panels=len(profiles),
                reliefs=sum(p.reliefs for p in profiles), files=[Path(f).name for f in files])


def run_arrangement(app, output_dir, guard, request):
    path = Path(output_dir) / REPORT
    if path.exists():
        raise RuntimeError("Existing report; no retry")
    payload = dict(outcome="FAIL", stages=[], edits=[])
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        guard()
        design, doc = adsk.fusion.Design.cast(app.activeProduct), app.activeDocument
        if (doc.isSaved or doc.isModified or design.designType != adsk.fusion.DesignTypes.ParametricDesignType
                or design.rootComponent.occurrences.count or design.rootComponent.bRepBodies.count
                or design.rootComponent.sketches.count or design.userParameters.count or design.timeline.count):
            raise RuntimeError("New empty unsaved parametric fixture required")
        plan = plan_request(request)          # every refusal happens before CAD writes
        asm = plan.arrangement.assembly
        payload.update(spec_hash=asm.spec_hash, instances=[i.instance_id for i in plan.arrangement.instances],
                       inventory=expected_inventory(asm), fit=plan.arrangement.fit,
                       planned_edits=[dict(parameter=e.parameter, value_mm=e.value_mm, expect=e.expect,
                                           preview=e.preview) for e in plan.edits])
        guard()
        FusionAdapter(design).compile(asm)
        baseline = measure_arrangement(design, plan, guard)
        payload["stages"].append(dict(label="baseline", **baseline))
        if baseline["outcome"] != "PASS":
            raise RuntimeError("Baseline verification failed")
        payload["baseline_state"] = snapshot(design)
        base_values = {p.name: p.value_mm for p in asm.parameters.base()}
        last = baseline
        for edit in plan.edits:
            record = dict(parameter=edit.parameter, value_mm=edit.value_mm, expect=edit.expect, outcome="FAIL")
            payload["edits"].append(record)
            # Re-preview against the values Fusion currently reports, never only the plan.
            current = {n: last["parameters_mm"][n] for n in base_values}
            preview = preview_values(plan.arrangement, plan.envelope, dict(current, **{edit.parameter: edit.value_mm}))
            record["preview"] = preview
            if edit.expect == "refused":
                if preview["outcome"] != "REFUSED":
                    raise RuntimeError("Expected refusal was not refused; nothing written")
                after = measure_arrangement(design, plan, guard)
                payload["stages"].append(dict(label="after_refusal_" + edit.parameter, **after))
                if not restored_lined_measurements(last, after) or snapshot(design) != payload["baseline_state"]:
                    raise RuntimeError("Refusal changed geometry or state")
                record["outcome"] = "PASS"
                continue
            if preview["outcome"] != "PASS":
                raise RuntimeError("Edit preview refused at current values; nothing written")
            guard()
            parameter = design.userParameters.itemByName(edit.parameter)
            original = parameter.expression
            parameter.expression = "%r mm" % edit.value_mm
            adsk.doEvents()
            edited = measure_arrangement(design, plan, guard)
            payload["stages"].append(dict(label="edit_" + edit.parameter, **edited))
            if edited["outcome"] != "PASS" or abs(edited["parameters_mm"][edit.parameter] - edit.value_mm) > 1e-6:
                raise RuntimeError("Edited model failed verification; no automatic restoration")
            guard()
            parameter.expression = original
            adsk.doEvents()
            restored = measure_arrangement(design, plan, guard)
            payload["stages"].append(dict(label="restore_" + edit.parameter, **restored))
            if (restored["outcome"] != "PASS" or not restored_lined_measurements(baseline, restored)
                    or snapshot(design) != payload["baseline_state"]):
                raise RuntimeError("Restoration differs from baseline")
            record["outcome"] = "PASS"
            last = restored
        payload["final_state"] = snapshot(design)
        if plan.tool_diameter_mm is not None:
            payload["dxf"] = _export_dxf(plan, output_dir)
        guard()
        app.activeViewport.fit()
        payload["outcome"] = "PASS"
    except Exception as exc:
        payload["error"] = str(exc)
        raise
    finally:
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return str(path)
