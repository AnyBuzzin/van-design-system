"""One readback-tolerance policy for comparing repeated Fusion measurements.

Used to prove that a restore (or a refused change) left the model exactly as
it was. Fusion reports the same geometry with tiny floating-point differences
between reads; these limits admit that noise and nothing else. They are NOT
model tolerances (see ``core.units.MODEL_EPSILON_MM``) and NOT shop tolerances.

Observed readback noise on identical geometry:
  * body volume: 2.65e-8 mm^3 (Issue #56), 7.45e-9 mm^3 (Issue #61)
  * body bounds: 1.14e-13 mm (Issue #61)

Every other report field must match exactly, every check must PASS in both
reports, and the raw reports are never modified.
"""
from copy import deepcopy
import math

VOLUME_READBACK_MM3 = 1e-6
COORDINATE_READBACK_MM = 1e-9


def _finite(v):
    return type(v) in (int, float) and math.isfinite(v)


def same_except_volume_noise(before, after):
    """Identical reports except body volumes (and their volume checks' observed
    values) within VOLUME_READBACK_MM3. Bounds must match exactly."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    if before.get('outcome') != 'PASS' or after.get('outcome') != 'PASS':
        return False
    if {k: v for k, v in before.items() if k not in ('bodies', 'checks')} != {
            k: v for k, v in after.items() if k not in ('bodies', 'checks')}:
        return False
    bodies = before.get('bodies'); other = after.get('bodies')
    if not isinstance(bodies, dict) or not bodies or not isinstance(other, dict) or bodies.keys() != other.keys():
        return False
    for sid, body in bodies.items():
        restored = other[sid]
        if not isinstance(body, dict) or not isinstance(restored, dict):
            return False
        a, b = body.get('volume_mm3'), restored.get('volume_mm3')
        if not _finite(a) or not _finite(b) or min(a, b) <= 0 or abs(a - b) > VOLUME_READBACK_MM3:
            return False
        if {k: v for k, v in body.items() if k != 'volume_mm3'} != {k: v for k, v in restored.items() if k != 'volume_mm3'}:
            return False
    checks = before.get('checks'); others = after.get('checks')
    if not isinstance(checks, list) or not isinstance(others, list) or len(checks) != len(others):
        return False
    volume_ids = {sid + '.volume': sid for sid in bodies}
    seen = set()
    for a, b in zip(checks, others):
        if not isinstance(a, dict) or not isinstance(b, dict) or a.get('status') != 'PASS' or b.get('status') != 'PASS':
            return False
        cid = a.get('check_id')
        if cid in volume_ids:
            sid = volume_ids[cid]
            if cid in seen or a.get('unit') != 'mm3' or a.get('object_ids') != [sid]:
                return False
            seen.add(cid)
            for check, body in ((a, bodies[sid]), (b, other[sid])):
                obs, expected, tol = (check.get(k) for k in ('observed', 'expected', 'tolerance'))
                if (not all(_finite(v) for v in (obs, expected, tol)) or tol < 0
                        or obs != body['volume_mm3'] or abs(obs - expected) > tol):
                    return False
            if {k: v for k, v in a.items() if k != 'observed'} != {k: v for k, v in b.items() if k != 'observed'}:
                return False
        elif a != b:
            return False
    return seen == set(volume_ids)


def same_except_readback_noise(before, after):
    """As ``same_except_volume_noise`` but body bounds may also differ by up to
    COORDINATE_READBACK_MM. Bounds are validated first; only comparison copies
    are aligned."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    bodies, restored = before.get("bodies"), after.get("bodies")
    if (not isinstance(bodies, dict) or not bodies or not isinstance(restored, dict)
            or bodies.keys() != restored.keys()):
        return False
    aligned = deepcopy(after)
    for sid in bodies:
        a, b = bodies[sid], restored[sid]
        for body in (a, b):
            if not isinstance(body, dict):
                return False
            for side in ("min", "max"):
                values = body.get(side)
                if (not isinstance(values, (list, tuple)) or len(values) != 3
                        or any(not _finite(v) for v in values)):
                    return False
            if any(hi <= lo for lo, hi in zip(body["min"], body["max"])):
                return False
        for side in ("min", "max"):
            if type(a[side]) is not type(b[side]) or any(
                    abs(x - y) > COORDINATE_READBACK_MM for x, y in zip(a[side], b[side])):
                return False
            aligned["bodies"][sid][side] = deepcopy(a[side])
    return same_except_volume_noise(before, aligned)


def with_readback_noise(report, rng, *, coordinate_mm=1e-12, volume_mm3=1e-8):
    """Copy of a measurement report with Fusion-like readback noise injected
    into body bounds and volumes (and their volume checks). For offline tests:
    exact-equality comparisons that would fail live must fail here too."""
    noisy = deepcopy(report)
    for sid, body in noisy.get("bodies", {}).items():
        for side in ("min", "max"):
            body[side] = type(body[side])(v + rng.uniform(-coordinate_mm, coordinate_mm) for v in body[side])
        body["volume_mm3"] += rng.uniform(-volume_mm3, volume_mm3)
        for check in noisy.get("checks", []):
            if check.get("check_id") == sid + ".volume":
                check["observed"] = body["volume_mm3"]
    return noisy
