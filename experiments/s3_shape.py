# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Stage S3: encoder-only noise feedback. Sweep shaper settings at one rate."""
import sys
from kaplos import shaping as SH
from . import exp

SIGNALS = ['piano', 'recorder', 'glockenspiel', 'harpsichord', 'castanets', 'applause']
SHAPERS = {
    'flat': None,
    'lpc_.94_.5': SH.LPCShaper(16, 0.94, 0.5),
    'mask_g6': SH.MaskShaper(order=24, beta=1.0, range_db=40, gmax_db=6),
    'mask_g10': SH.MaskShaper(order=24, beta=1.0, range_db=40, gmax_db=10),
    'mask_g14': SH.MaskShaper(order=24, beta=1.0, range_db=40, gmax_db=14),
}

if __name__ == '__main__':
    kbps = int(sys.argv[1]) if len(sys.argv) > 1 else 384
    names = sys.argv[2:] or list(SHAPERS)
    for sig in SIGNALS:
        row = []
        for name in names:
            m = exp.run(sig, kbps, shaper=SHAPERS[name], check_decoder=False)
            row.append(f'{name} {m["nmr95"]:6.1f}')
        print(f'{sig:13s} {kbps}k ' + ' | '.join(row), flush=True)
