# SPDX-License-Identifier: BSD-2-Clause-Patent
"""The codec configuration (default predictor, LPC shaping) on every test signal, with the decoder
checked against the encoder reconstruction."""
import sys
from harness import gen_signals as G
from kaplos import shaping as SH
from . import exp

if __name__ == '__main__':
    rates = [int(r) for r in sys.argv[1:]] or [384, 576, 768]
    shaper = SH.LPCShaper(16, 0.96, 0.6, gmax_db=16)
    for sig in G.SIGNALS:
        for kbps in rates:
            m = exp.run(sig, kbps, shaper=shaper)
            print(f"{sig:13s} {kbps:5d}k NMR95 {m['nmr95']:6.1f} NMRmax {m['nmr_max']:6.1f} "
                  f"SNR {m['snr']:6.1f} lossless {m['lossless_pct']:5.1f}% escape {m['escape_pct']:.2f}% "
                  f"keys {m['resets']:4d} trials {m['trials']:.2f} max {m['trials_max']}", flush=True)
