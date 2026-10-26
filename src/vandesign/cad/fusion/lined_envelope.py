"""Fixed B1 unsaved fixture; execution requires the existing owned Runner session."""
import json
from pathlib import Path
import adsk.core
import adsk.fusion

from .adapter import FusionAdapter
from .test_envelope import measure_test, snapshot
from ...core.geometry import Box
from ...modules.storage_box import storage_contacts
from ...modules.test_envelope import (build_lined_envelope, preview_lined_fit, furniture_rows,
                                     restored_lined_measurements)
from ...schemas.envelope_spec import EnvelopeSpec


def measure_lined(design, assembly, spec, guard, width):
    report = measure_test(design, assembly, guard, expected_panels=22,
                          expected_timeline=70, lined_spec=spec)
    env = report["parameters_mm"]
    expected = assembly.parameters.resolve({"Env_Bare_Width": width})
    checks = report["checks"]
    checks.append(dict(check_id="lined.parameters", status="PASS" if set(env)==set(expected)
                       and all(abs(env[k]-v)<0.001 for k, v in expected.items()) else "FAIL"))
    boxes = {k: Box(tuple(v["min"]), tuple(v["max"])) for k, v in report["bodies"].items()}
    for name, ok in storage_contacts(boxes).items():
        checks.append(dict(check_id="storage.contact."+name, status="PASS" if ok else "FAIL"))
    report["outcome"] = "PASS" if all(c["status"]=="PASS" for c in checks) else "FAIL"
    return report


def run_lined_envelope(app, output_dir, guard):
    path = Path(output_dir)/"lined_envelope.json"
    if path.exists():
        raise RuntimeError("Existing report; no retry")
    payload = dict(outcome="FAIL", stages=[], refusal=None)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        guard()
        design, doc = adsk.fusion.Design.cast(app.activeProduct), app.activeDocument
        if (doc.isSaved or doc.isModified or design.designType!=adsk.fusion.DesignTypes.ParametricDesignType
                or design.rootComponent.occurrences.count or design.rootComponent.bRepBodies.count
                or design.rootComponent.sketches.count or design.userParameters.count or design.timeline.count):
            raise RuntimeError("New empty unsaved parametric fixture required")
        spec = EnvelopeSpec()
        assembly = build_lined_envelope(spec)
        guard()
        FusionAdapter(design).compile(assembly)
        payload.update(specification=json.loads(spec.to_json()), spec_hash=assembly.spec_hash,
                       furniture_cut_list=furniture_rows(assembly))
        parameter = design.userParameters.itemByName("Env_Bare_Width")
        original = parameter.expression
        for width in (1784, 1794, 1784):
            if payload["stages"]:
                preview_lined_fit(assembly, spec, assembly.parameters.resolve({"Env_Bare_Width": width}))
                guard()
                parameter.expression = original if width==1784 else "1794 mm"
                adsk.doEvents()
            stage = measure_lined(design, assembly, spec, guard, width)
            payload["stages"].append(stage)
            if stage["outcome"]!="PASS":
                raise RuntimeError("B1 measurement failed; no automatic restoration")
            if len(payload["stages"])==1:
                payload["baseline_state"] = snapshot(design)
        payload["restored_state"] = snapshot(design)
        if (not restored_lined_measurements(payload["stages"][0], payload["stages"][-1])
                or payload["baseline_state"]!=payload["restored_state"]):
            raise RuntimeError("B1 restoration differs")
        before = payload["stages"][-1]
        boxes = {k: Box(tuple(v["min"]), tuple(v["max"])) for k, v in before["bodies"].items()}
        # Preview only: storage +500 X enters the right arch. Never write this move.
        for sid, b in list(boxes.items()):
            if sid.startswith("storage.001."):
                boxes[sid] = Box((b.lo[0]+500, *b.lo[1:]), (b.hi[0]+500, *b.hi[1:]))
        guard()
        try:
            preview_lined_fit(assembly, spec, before["parameters_mm"], boxes)
        except ValueError as exc:
            if "expanded keep-out" not in str(exc):
                raise RuntimeError("Unexpected refusal reason") from exc
            payload["refusal"] = dict(outcome="REFUSED", reason=str(exc), storage_delta_x_mm=500)
        else:
            raise RuntimeError("Unsafe move not refused")
        after = measure_lined(design, assembly, spec, guard, 1784)
        payload["after_refusal"] = after
        payload["final_state"] = snapshot(design)
        if (not restored_lined_measurements(before, after)
                or payload["restored_state"]!=payload["final_state"]):
            raise RuntimeError("Refusal changed geometry or state")
        guard()
        app.activeViewport.fit()
        payload["outcome"] = "PASS"
    except Exception as exc:
        payload["error"] = str(exc)
        raise
    finally:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)
