"""Puts the Fusion script folder on sys.path so tests can import ``vandesign``."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.join(ROOT, "VanCabinetJoineryV5")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
