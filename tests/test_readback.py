"""Shared readback-tolerance policy: noise passes, real change fails, raw reports untouched."""
import copy
import random
import unittest

from vandesign.modules.storage_box import RESTORATION_VOLUME_EPSILON_MM3, restored_storage_measurements
from vandesign.modules.test_envelope import (B1_RESTORATION_COORDINATE_EPSILON_MM, build_lined_envelope,
                                             restored_lined_measurements)
from vandesign.schemas.envelope_spec import EnvelopeSpec
from vandesign.verification.readback import (COORDINATE_READBACK_MM, VOLUME_READBACK_MM3,
                                             same_except_readback_noise, same_except_volume_noise,
                                             with_readback_noise)


def report():
    asm = build_lined_envelope(EnvelopeSpec())
    env = asm.parameters.resolve()
    boxes = {p.stable_id: p.box.resolve(env) for p in asm.panels}
    return dict(outcome="PASS", parameters_mm=env, counts={"timeline_items": 70},
                bodies={k: dict(min=list(b.lo), max=list(b.hi), volume_mm3=b.volume) for k, b in boxes.items()},
                checks=[dict(check_id=k + ".volume", status="PASS", observed=b.volume, expected=b.volume,
                             tolerance=1.0, unit="mm3", object_ids=[k]) for k, b in boxes.items()]
                + [dict(check_id="furniture_interference", status="PASS", observed=0)])


class ReadbackPolicy(unittest.TestCase):
    def setUp(self):
        self.before = report()
        self.rng = random.Random(56061)

    def test_one_policy_behind_the_existing_names(self):
        self.assertIs(restored_storage_measurements, same_except_volume_noise)
        self.assertIs(restored_lined_measurements, same_except_readback_noise)
        self.assertEqual(RESTORATION_VOLUME_EPSILON_MM3, VOLUME_READBACK_MM3)
        self.assertEqual(B1_RESTORATION_COORDINATE_EPSILON_MM, COORDINATE_READBACK_MM)

    def test_injected_readback_noise_passes_and_exact_equality_would_not(self):
        for _ in range(100):
            noisy = with_readback_noise(self.before, self.rng)
            original = copy.deepcopy(noisy)
            self.assertNotEqual(noisy, self.before)              # naive comparison fails live
            self.assertTrue(same_except_readback_noise(self.before, noisy))
            self.assertEqual(noisy, original)                    # raw evidence untouched
            volume_only = with_readback_noise(self.before, self.rng, coordinate_mm=0)
            self.assertTrue(same_except_volume_noise(self.before, volume_only))
            self.assertFalse(same_except_volume_noise(self.before, noisy))  # bounds stay exact there

    def test_real_changes_fail_on_top_of_noise(self):
        sid = next(iter(self.before["bodies"]))
        for mutate in (
                lambda r: r["bodies"][sid]["min"].__setitem__(0, r["bodies"][sid]["min"][0] + 1e-6),
                lambda r: r["bodies"][sid].__setitem__("volume_mm3", r["bodies"][sid]["volume_mm3"] + 1e-4),
                lambda r: r["checks"][-1].__setitem__("observed", 1),
                lambda r: r["checks"][0].__setitem__("status", "FAIL"),
                lambda r: r["counts"].__setitem__("timeline_items", 71),
                lambda r: r["parameters_mm"].__setitem__("Env_Lining", 18.001),
                lambda r: r["bodies"].pop(sid),
                lambda r: r.__setitem__("outcome", "FAIL")):
            noisy = with_readback_noise(self.before, self.rng)
            mutate(noisy)
            self.assertFalse(same_except_readback_noise(self.before, noisy))


if __name__ == "__main__":
    unittest.main()
