"""VanDesign - CAD-neutral engineering core with a thin Fusion adapter.

Layering rule: nothing outside ``vandesign.cad.fusion`` may import ``adsk``.
"""

__version__ = "0.5.0"
SCHEMA_VERSION = "0.1"
GENERATOR_ID = "vandesign.cabinet@" + __version__
