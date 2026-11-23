# SPDX-License-Identifier: BSD-2-Clause-Patent
"""The hard invariants, tested through the real bitstream."""
import unittest
import numpy as np
from kaplos import packet
from kaplos import shaping

FS = 48000


def tones(packets, bits, seed=1):
    """Two-channel tones with a little noise, at the given bit depth."""
    n = packets * packet.PKT
    t = np.arange(n) / FS
    rng = np.random.default_rng(seed)
    left = 0.3 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.sin(2 * np.pi * 3150 * t)
    right = 0.25 * np.sin(2 * np.pi * 660 * t + 0.5)
    x = np.stack([left, right], axis=1) + 0.01 * rng.standard_normal((n, 2))
    full = 1 << (bits - 1)
    return np.clip(np.round(x * (full - 1)), -full, full - 1).astype(np.int64)


def noise(packets, bits, seed=2):
    """Full-scale white noise, which no capped packet can code losslessly."""
    full = 1 << (bits - 1)
    return np.random.default_rng(seed).integers(-full, full, size=(packets * packet.PKT, 2))


def lpc():
    return shaping.LPCShaper(16, 0.96, 0.6, gmax_db=16)


class LosslessTest(unittest.TestCase):
    def test_round_trip_is_bit_exact(self):
        for bits in (16, 24):
            for stereo in ('lr', 'ms'):
                with self.subTest(bits=bits, stereo=stereo):
                    x = tones(100, bits)
                    pk, y, _ = packet.encode(x, bitdepth=bits, stereo=stereo)
                    self.assertTrue(np.array_equal(y, x))
                    self.assertTrue(np.array_equal(packet.decode(pk, bitdepth=bits), x))


class CappedTest(unittest.TestCase):
    def test_every_packet_has_the_budget_size(self):
        x = tones(200, 24)
        for kbps in (384, 576):
            for name, shaper in (('flat', None), ('lpc', lpc())):
                with self.subTest(kbps=kbps, shaper=name):
                    budget = kbps // 8
                    pk, y, _ = packet.encode(x, bitdepth=24, budget=budget, shaper=shaper)
                    self.assertEqual({len(p) for p in pk}, {budget})
                    self.assertTrue(np.array_equal(packet.decode(pk, bitdepth=24), y))

    def test_escape_mode_keeps_the_size_and_the_decoder_match(self):
        x = noise(50, 24)
        budget = packet.MIN_BUDGET
        pk, y, S = packet.encode(x, bitdepth=24, budget=budget, collect=True)
        self.assertIn(1, S.mode)
        self.assertEqual({len(p) for p in pk}, {budget})
        self.assertTrue(np.array_equal(packet.decode(pk, bitdepth=24), y))

    def test_budget_below_the_escape_minimum_is_rejected(self):
        with self.assertRaises(ValueError):
            packet.encode(tones(10, 24), bitdepth=24, budget=packet.MIN_BUDGET - 1)

    def test_no_look_ahead_beyond_the_current_packet(self):
        # coding a prefix of the input must give exactly the leading packets of the full run
        x = tones(200, 24)
        full, _, _ = packet.encode(x, bitdepth=24, budget=48, shaper=lpc())
        head, _, _ = packet.encode(x[:120 * packet.PKT], bitdepth=24, budget=48, shaper=lpc())
        self.assertEqual(head, full[:120])


if __name__ == '__main__':
    unittest.main()
