"""Unit policy.

Every length in the domain model is a float in MILLIMETRES.  Conversion to
Fusion's internal centimetres happens only inside ``vandesign.cad.fusion``.
"""

MM_PER_CM = 10.0
MM3_PER_CM3 = 1000.0

# Model-consistency epsilon: how closely measured CAD geometry must agree with
# the nominal calculation.  This is a software check, NOT a shop tolerance.
MODEL_EPSILON_MM = 0.01
VOLUME_REL_TOL = 1e-6


def cm_to_mm(value_cm: float) -> float:
    return value_cm * MM_PER_CM


def mm_to_cm(value_mm: float) -> float:
    return value_mm / MM_PER_CM


def cm3_to_mm3(value_cm3: float) -> float:
    return value_cm3 * MM3_PER_CM3
