# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Experiment helper: run the codec on a generated test signal at a given rate and score it with the
harness."""
import numpy as np
from harness import analyze as A
from harness.baselines import SIG
from kaplos import packet


def load(sig):
    """Integer 24-bit samples of a generated test signal."""
    return np.fromfile(SIG / f'{sig}.s32', dtype='<i4').reshape(-1, 2).astype(np.int64)


def run(sig, kbps, shaper=None, check_decoder=True):
    x = load(sig)
    budget = round(kbps / 8)  # bytes per 1 ms packet
    pk, y, S = packet.encode(x, bitdepth=24, budget=budget, shaper=shaper, collect=True)
    if check_decoder:
        z = packet.decode(pk, bitdepth=24)
        assert np.array_equal(z, y), 'decoder output differs from encoder reconstruction'
    scale = 2.0 ** 23
    ref = x[:len(y)] / scale
    dec = y / scale
    m = A.metrics(ref, dec, delay=0)
    mode = np.array(S.mode)
    idx = np.array(S.idx)
    m.update({
        'kbps': kbps, 'bytes': budget,
        'lossless_pct': 100.0 * np.mean((idx == 0) & (mode == 0)),
        'escape_pct': 100.0 * np.mean(mode == 1),
        'trials': float(np.mean(S.trials)),
        'trials_max': int(np.max(S.trials)),
        'fill_pct': 100.0 * np.mean(np.array(S.bits)) / (budget * 8),
        'clips': S.clips, 'resets': S.resets,
        'bits_per_sample': float(np.mean(S.bits)) / (2 * packet.PKT),
    })
    return m
