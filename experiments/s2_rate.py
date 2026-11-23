# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Stage S2: hard per-packet byte cap, flat (unshaped) quantisation noise."""
import sys
from harness import gen_signals as G
from . import exp

if __name__ == '__main__':
    rates = [int(r) for r in sys.argv[1:]] or [384, 576, 768]
    for sig in G.SIGNALS:
        for kbps in rates:
            m = exp.run(sig, kbps)
            print(f"{sig:13s} {kbps:5d}k  NMR95 {m['nmr95']:6.1f}  SNR {m['snr']:6.1f}  "
                  f"lossless {m['lossless_pct']:5.1f}%  escape {m['escape_pct']:4.1f}%  "
                  f"clips {m['clips']:4d}  resets {m['resets']:4d}  trials {m['trials']:.2f}  "
                  f"fill {m['fill_pct']:5.1f}%", flush=True)
