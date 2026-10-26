"""Export per-panel DXF files and a cut list for an existing module.

    python tools/export_dxf.py tab-slot-coupon --tool-diameter 6 --out dxf/coupon
    python tools/export_dxf.py cabinet --tool-diameter 6 --out dxf/cabinet

Output is manufacturing geometry for CAM/nesting software, not toolpaths.
Existing files are never overwritten.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from vandesign.manufacturing.catalog import MODULES, module_profiles  # noqa: E402
from vandesign.manufacturing.dxf import export_profiles, loop_areas, read_dxf  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("module", choices=MODULES)
    ap.add_argument("--tool-diameter", type=float, required=True, help="router bit diameter, mm")
    ap.add_argument("--no-relief", action="store_true", help="omit dog-bone relief (not for joinery)")
    ap.add_argument("--out", required=True, help="new or empty output directory")
    a = ap.parse_args(argv)
    profiles = module_profiles(a.module, tool_diameter=a.tool_diameter, relief=not a.no_relief)
    written = export_profiles(profiles, a.out)
    # Re-read every file independently and compare loop areas with the model.
    for p in profiles:
        with open(os.path.join(a.out, p.panel_id + ".dxf"), encoding="ascii") as fh:
            areas = loop_areas(read_dxf(fh.read()), "OUTLINE")
        if len(areas) != 1 or abs(areas[0] - p.outline.area) > 1e-3:
            raise SystemExit("DXF verification failed for %s" % p.panel_id)
    print(json.dumps({"module": a.module, "panels": len(profiles), "files": written,
                      "reliefs": sum(p.reliefs for p in profiles)}, indent=2))


if __name__ == "__main__":
    main()
