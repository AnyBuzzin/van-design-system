"""Install / configure the VanDesign Runner Fusion add-in.

    python automation/tools/install_runner.py install --g3-dir <G3 VanCabinetJoineryV5 folder> \
        --audit-script <...VanDesignCutAuditG3.py> [--queue-root DIR] [--addins-dir DIR] [--upgrade]
    python automation/tools/install_runner.py allow  <design_id> --name <document name> [--note TEXT]
    python automation/tools/install_runner.py protect <design_id> --name <document name>
    python automation/tools/install_runner.py show

The add-in is installed as its OWN folder ``<AddIns>/VanDesignRunner`` and never
touches the G2/G3 script folders it reads from.  ``install`` refuses to replace
an existing installation unless ``--upgrade`` (code is replaced, config.json kept).
"""

import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUTOMATION = os.path.dirname(HERE)
sys.path.insert(0, AUTOMATION)

from vdrunner import RUNNER_VERSION  # noqa: E402
from vdrunner.policy import DEFAULT_PARAMETER_BOUNDS_MM, default_queue_root  # noqa: E402
from vdrunner.queue import atomic_write_json  # noqa: E402

DEFAULT_ADDINS = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                              "Autodesk", "Autodesk Fusion 360", "API", "AddIns")


def _target(addins_dir):
    return os.path.join(addins_dir, "VanDesignRunner")


def _cfg_path(addins_dir):
    return os.path.join(_target(addins_dir), "config.json")


def install(a):
    g3 = os.path.abspath(a.g3_dir)
    if not os.path.isfile(os.path.join(g3, "VanCabinetJoineryV5.py")) or not os.path.isdir(os.path.join(g3, "vandesign")):
        sys.exit("G3 folder %s does not contain VanCabinetJoineryV5.py + vandesign/" % g3)
    audit = os.path.abspath(a.audit_script)
    if not os.path.isfile(audit):
        sys.exit("audit script not found: %s" % audit)
    dst = _target(a.addins_dir)
    cfg_file = _cfg_path(a.addins_dir)
    old_cfg = None
    if os.path.exists(dst):
        if not a.upgrade:
            sys.exit("%s already exists; use --upgrade to replace the code (config.json is kept)" % dst)
        if os.path.exists(cfg_file):
            old_cfg = json.load(open(cfg_file, encoding="utf-8"))
        for name in ("VanDesignRunner.py", "VanDesignRunner.manifest", "fusion_backend.py"):
            p = os.path.join(dst, name)
            if os.path.exists(p):
                os.remove(p)
        shutil.rmtree(os.path.join(dst, "vdrunner"), ignore_errors=True)
    os.makedirs(dst, exist_ok=True)
    src = os.path.join(AUTOMATION, "VanDesignRunner")
    for name in ("VanDesignRunner.py", "VanDesignRunner.manifest", "fusion_backend.py"):
        shutil.copy2(os.path.join(src, name), os.path.join(dst, name))
    shutil.copytree(os.path.join(AUTOMATION, "vdrunner"), os.path.join(dst, "vdrunner"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    cfg = old_cfg or {"allowed_design_ids": [], "protected_design_ids": [],
                      "parameter_bounds_mm": DEFAULT_PARAMETER_BOUNDS_MM}
    cfg.update(queue_root=os.path.abspath(a.queue_root), g3_script_dir=g3, audit_script=audit,
               runner_version=RUNNER_VERSION)
    atomic_write_json(cfg_file, cfg)
    print(json.dumps({"installed": dst, "runner_version": RUNNER_VERSION, "config": cfg}, indent=2))


def _edit_list(a, key):
    cfg_file = _cfg_path(a.addins_dir)
    cfg = json.load(open(cfg_file, encoding="utf-8"))
    other = "protected_design_ids" if key == "allowed_design_ids" else "allowed_design_ids"
    if any((x if isinstance(x, str) else x.get("design_id")) == a.design_id for x in cfg.get(other, [])):
        sys.exit("design %s is already in %s; refusing to put it in both lists" % (a.design_id, other))
    items = [x for x in cfg.get(key, []) if (x if isinstance(x, str) else x.get("design_id")) != a.design_id]
    items.append({"design_id": a.design_id, "document_name": a.name, "note": a.note or ""})
    cfg[key] = items
    atomic_write_json(cfg_file, cfg)
    print(json.dumps({key: items}, indent=2))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--addins-dir", default=DEFAULT_ADDINS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("install")
    i.add_argument("--g3-dir", required=True); i.add_argument("--audit-script", required=True)
    i.add_argument("--queue-root", default=default_queue_root()); i.add_argument("--upgrade", action="store_true")
    for name in ("allow", "protect"):
        p = sub.add_parser(name)
        p.add_argument("design_id"); p.add_argument("--name", required=True); p.add_argument("--note")
    sub.add_parser("show")
    a = ap.parse_args(argv)
    if a.cmd == "install":
        install(a)
    elif a.cmd == "allow":
        _edit_list(a, "allowed_design_ids")
    elif a.cmd == "protect":
        _edit_list(a, "protected_design_ids")
    else:
        print(open(_cfg_path(a.addins_dir), encoding="utf-8").read())


if __name__ == "__main__":
    main()
