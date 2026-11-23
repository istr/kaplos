# SPDX-License-Identifier: BSD-2-Clause-Patent
"""The hard invariants on every synthetic test signal of the harness, through the real bitstream."""
import unittest
import numpy as np
from harness import gen_signals as G
from kaplos import packet
from kaplos import shaping


class SyntheticSignalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 24-bit integers, quantised as gen_signals.py writes them
        full = 1 << 23
        cls.signals = {name: np.clip(np.round(fn() * full), -full, full - 1).astype(np.int64)
                       for name, fn in G.SIGNALS.items()}

    def test_lossless_round_trip_is_bit_exact(self):
        for name, x in self.signals.items():
            with self.subTest(signal=name):
                pk, y, _ = packet.encode(x, bitdepth=24)
                self.assertTrue(np.array_equal(y, x))
                self.assertTrue(np.array_equal(packet.decode(pk, bitdepth=24), x))

    def test_capped_packets_have_the_budget_size_and_decode_to_the_reconstruction(self):
        shaper = shaping.LPCShaper(16, 0.96, 0.6, gmax_db=16)
        for name, x in self.signals.items():
            for kbps in (384, 576, 768):
                with self.subTest(signal=name, kbps=kbps):
                    budget = kbps // 8
                    pk, y, _ = packet.encode(x, bitdepth=24, budget=budget, shaper=shaper)
                    self.assertEqual({len(p) for p in pk}, {budget})
                    self.assertTrue(np.array_equal(packet.decode(pk, bitdepth=24), y))


if __name__ == '__main__':
    unittest.main()
