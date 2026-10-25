"""VanDesign automation runner - pure-Python core (no ``adsk`` imports).

Shared by the local orchestrator CLI and the Fusion add-in:
job schema validation, the filesystem job queue, expectation evaluation
and evidence packaging.  Everything that touches Fusion lives in the
add-in (``automation/VanDesignRunner``).
"""

RUNNER_VERSION = "0.4.0"
JOB_SCHEMA_ID = "vandesign.runner.job/1"
RESULT_SCHEMA_ID = "vandesign.runner.result/1"
