"""Turn one layout request into drawings, a fit report and a DXF cutting pack.

    python tools/design_layout.py examples/crafter_interior.json --out design/crafter

Writes into a new or empty directory:
    top.svg, front.svg, side.svg   drawings of the finished interior and furniture
    dxf/                           one DXF per panel + cutlist.csv (joints included)
    summary.json                   fit clearances, materials, joints, assumptions

Offline only: nothing is sent to Fusion. Manufacturing geometry, not
toolpaths; sheet counts are lower bounds before nesting. Existing files are
never overwritten.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from vandesign.layout_report import (VIEWS, fit_summary, layout_svg, material_summary,  # noqa: E402
                                     offline_plan)
from vandesign.manufacturing.dxf import export_profiles, loop_areas, read_dxf  # noqa: E402
from vandesign.manufacturing.placement import arrangement_profiles  # noqa: E402


def design(request, out_dir, tool_diameter):
    if os.path.exists(out_dir) and os.listdir(out_dir):
        raise SystemExit("Output directory must be new or empty: %s" % out_dir)
    plan = offline_plan(request)
    profiles, joints = arrangement_profiles(plan.arrangement, tool_diameter=tool_diameter)
    os.makedirs(out_dir, exist_ok=True)
    files = export_profiles(profiles, os.path.join(out_dir, "dxf"))
    for p in profiles:  # re-read every DXF independently
        with open(os.path.join(out_dir, "dxf", p.panel_id + ".dxf"), encoding="ascii") as fh:
            areas = loop_areas(read_dxf(fh.read()), "OUTLINE")
        if len(areas) != 1 or abs(areas[0] - p.outline.area) > 1e-3:
            raise SystemExit("DXF verification failed for %s" % p.panel_id)
    for view in VIEWS:
        with open(os.path.join(out_dir, view + ".svg"), "x", encoding="utf-8") as fh:
            fh.write(layout_svg(plan, view))
    summary = dict(
        spec_hash=plan.arrangement.assembly.spec_hash,
        envelope=dict(finished_mm=plan.envelope.finished_size, provenance=plan.envelope.provenance,
                      upper_walls=list(plan.envelope.upper_walls)),
        instances=[dict(instance_id=i.instance_id, module=i.module, position_mm=list(i.position_mm),
                        quarter_turns=i.quarter_turns) for i in plan.arrangement.instances],
        fit=dict(outcome=plan.arrangement.fit["outcome"], tolerance_mm=plan.envelope.tolerance_mm,
                 clearance_beyond_tolerance_mm=fit_summary(plan)),
        materials=material_summary(profiles),
        joints={iid: [dict(inserter=r.joint.inserter, receiver=r.joint.receiver, tabs=len(r.tabs),
                           clearance_per_face_mm=r.proof["clearance_per_face_mm"]) for r in results]
                for iid, results in joints.items()},
        panels=len(profiles), reliefs=sum(p.reliefs for p in profiles),
        files=sorted([os.path.relpath(f, out_dir).replace(os.sep, "/") for f in files]
                     + [v + ".svg" for v in VIEWS]),
        limits=["Offline design output; not verified in Fusion or cut.",
                "Vehicle values marked ASSUMED or PUBLISHED are not measurements.",
                "DXF is manufacturing geometry, not toolpaths; sheet counts are lower bounds before nesting.",
                "No load, anchoring or vehicle-fit qualification."])
    with open(os.path.join(out_dir, "summary.json"), "x", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("request", help="layout request JSON (arrangement, envelope, edits)")
    ap.add_argument("--out", required=True, help="new or empty output directory")
    ap.add_argument("--tool-diameter", type=float, default=None,
                    help="router bit diameter, mm (default: the request's tool_diameter_mm)")
    a = ap.parse_args(argv)
    with open(a.request, encoding="utf-8") as fh:
        request = json.load(fh)
    tool = a.tool_diameter if a.tool_diameter is not None else request.get("tool_diameter_mm")
    if tool is None:
        raise SystemExit("A tool diameter is required (--tool-diameter or tool_diameter_mm)")
    s = design(request, a.out, tool)
    print(json.dumps(dict(fit=s["fit"]["outcome"], panels=s["panels"], reliefs=s["reliefs"],
                          materials=s["materials"], out=a.out), indent=2))


if __name__ == "__main__":
    main()
