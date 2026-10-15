"""Thin Fusion entrypoint.  No business logic lives here.

Install: copy the whole VanCabinetJoineryV5 folder into Fusion's Scripts
folder (Utilities > Scripts and Add-Ins > green + > Create new script shows the
location), or use 'Add existing script' and pick this folder.
"""

import os
import sys
import traceback

import adsk.core

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def _fresh_imports():
    """Fusion keeps imported modules alive between runs; drop ours so edits load."""
    for name in [n for n in sys.modules if n == "vandesign" or n.startswith("vandesign.")]:
        del sys.modules[name]


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        _fresh_imports()
        from vandesign.cad.fusion.runner import run_cabinet
        run_cabinet(app, ui, _HERE)
    except Exception:
        error = traceback.format_exc()
        app.log(error)
        ui.messageBox("VanCabinetJoinery V5 error:\n\n" + error)


def stop(context):
    pass
