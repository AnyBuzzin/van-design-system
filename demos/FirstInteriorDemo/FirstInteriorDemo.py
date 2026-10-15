"""Fusion script entrypoint; implementation and adsk imports live in adapter."""
import os
import sys
import traceback


def run(context):
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    here = os.path.dirname(os.path.abspath(__file__))
    package = here if os.path.isdir(os.path.join(here, 'vandesign')) else os.path.join(root, 'src')
    for name in list(sys.modules):
        if name == 'vandesign' or name.startswith('vandesign.'):
            del sys.modules[name]
    sys.path.insert(0, package)
    try:
        from vandesign.cad.fusion.interior_demo import run_demo, adsk
        app = adsk.core.Application.get()
        try:
            report = run_demo(app, os.path.join(here, 'reports'))
            app.userInterface.messageBox('Interior generated and verified. Report: ' + report)
        except Exception:
            app.userInterface.messageBox(traceback.format_exc())
    finally:
        sys.path.remove(package)


def stop(context):
    pass
