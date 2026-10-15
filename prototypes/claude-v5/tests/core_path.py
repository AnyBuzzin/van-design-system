"""Use the installed runtime; historical paths are only for evidence checks."""
import os
import vandesign

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORICAL_SCRIPT_DIR = os.path.join(ROOT, "VanCabinetJoineryV5")
SCRIPT_DIR = os.path.dirname(os.path.dirname(vandesign.__file__))
