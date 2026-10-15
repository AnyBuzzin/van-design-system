"""Fusion script entrypoint; implementation and adsk imports live in adapter."""
import os
import sys
import traceback


def run(context):
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    package = os.path.join(root, 'prototypes', 'claude-v5', 'VanCabinetJoineryV5')
    for name in list(sys.modules):
        if name == 'vandesign' or name.startswith('vandesign.'):
            del sys.modules[name]
    sys.path.insert(0, package)
    try:
        from vandesign.cad.fusion.interior_demo import run_demo, adsk
        app = adsk.core.Application.get()
        try:
            report = run_demo(app, os.path.join(root, 'demos', 'evidence'))
            app.userInterface.messageBox('Interior generated and verified. Report: ' + report)
        except Exception:
            app.userInterface.messageBox(traceback.format_exc())
    finally:
        sys.path.remove(package)


def stop(context):
    pass
