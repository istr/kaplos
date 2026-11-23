# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Stage S3: sweep of the LPC shaper (bandwidth expansion g1/g2, noise power gain cap) at one rate."""
import sys
from kaplos import shaping as SH
from . import exp

SIGNALS = ['piano', 'recorder', 'glockenspiel', 'harpsichord', 'castanets', 'applause']
SHAPERS = {
    'flat': None,
    '.94/.5': SH.LPCShaper(16, 0.94, 0.5),
    '.94/.5 g10': SH.LPCShaper(16, 0.94, 0.5, gmax_db=10),
    '.94/.5 g16': SH.LPCShaper(16, 0.94, 0.5, gmax_db=16),
    '.96/.6 g16': SH.LPCShaper(16, 0.96, 0.6, gmax_db=16),
    '.92/.3 g16': SH.LPCShaper(16, 0.92, 0.3, gmax_db=16),
}

if __name__ == '__main__':
    kbps = int(sys.argv[1]) if len(sys.argv) > 1 else 384
    for sig in SIGNALS:
        row = []
        for name, shaper in SHAPERS.items():
            m = exp.run(sig, kbps, shaper=shaper, check_decoder=False)
            row.append(f'{name} {m["nmr95"]:6.1f}')
        print(f'{sig:13s} {kbps}k ' + ' | '.join(row), flush=True)
