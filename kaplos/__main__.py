# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Kaplos command line: WAV in, WAV out (encode, then decode the real bitstream).

    python3 -m kaplos in.wav out.wav --kbps 384 [--shaper lpc|flat] [--bits 16|24] [--stats]

Input must be 48 kHz stereo. The output has the same length and is sample-aligned with the
input (the codec adds no algorithmic delay), so it can go straight into an A/B/X test.
--kbps 0 runs the lossless variable-rate mode. The first run compiles the kernels.
"""
import argparse
import sys
import numpy as np
import soundfile as sf
from . import codec as C
from . import packet
from . import shaping as SH


def read_wav(path):
    info = sf.info(path)
    x, fs = sf.read(path, dtype='int32', always_2d=True)
    bits = 24 if info.subtype in ('PCM_24', 'PCM_32', 'FLOAT', 'DOUBLE') else 16
    return (x.astype(np.int64) >> (32 - bits)), fs, bits


def write_wav(path, y, fs, bits):
    sf.write(path, (y << (32 - bits)).astype(np.int32), fs, subtype=f'PCM_{bits}')


def main():
    ap = argparse.ArgumentParser(prog='python3 -m kaplos', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inp')
    ap.add_argument('out')
    ap.add_argument('--kbps', type=int, default=384, help='stereo bitrate, multiple of 8 (0 = lossless)')
    ap.add_argument('--shaper', choices=['lpc', 'flat'], default='lpc')
    ap.add_argument('--bits', type=int, choices=[16, 24], help='override the detected bit depth')
    ap.add_argument('--stats', action='store_true')
    a = ap.parse_args()
    x, fs, bits = read_wav(a.inp)
    bits = a.bits or bits
    if fs != 48000 or x.shape[1] != 2:
        sys.exit('need 48 kHz stereo input')
    if a.kbps % 8:
        sys.exit('--kbps must be a multiple of 8 (whole bytes per 1 ms packet)')
    if 0 < a.kbps < 8 * packet.MIN_BUDGET:
        sys.exit(f'--kbps must be 0 or at least {8 * packet.MIN_BUDGET}')
    n = len(x)
    pad = (-n) % C.PKT
    xp = np.concatenate([x, np.zeros((pad, 2), np.int64)]) if pad else x
    budget = None if a.kbps == 0 else a.kbps // 8
    shaper = SH.LPCShaper(16, 0.96, 0.6, gmax_db=16) if a.shaper == 'lpc' else None
    pk, y_enc, S = packet.encode(xp, bitdepth=bits, budget=budget, shaper=shaper, collect=True)
    y = packet.decode(pk, bitdepth=bits)
    assert np.array_equal(y, y_enc), 'decoder mismatch'
    if budget is not None:
        assert all(len(p) == budget for p in pk)
    write_wav(a.out, y[:n], fs, bits)
    if a.stats:
        idx, mode = np.array(S.idx), np.array(S.mode)
        e = (y[:n] - x).astype(float)
        snr = 10 * np.log10(np.sum(x.astype(float) ** 2) / max(np.sum(e ** 2), 1e-30))
        rate = 'lossless VBR' if budget is None else f'{a.kbps} kbit/s ({budget} bytes per 1 ms packet)'
        print(f'{a.inp}: {bits}-bit, {rate}, {len(pk)} packets\n'
              f'  lossless packets {100 * np.mean((idx == 0) & (mode == 0)):.1f} %, '
              f'escape {100 * np.mean(mode == 1):.2f} %, key packets {S.resets}, '
              f'mean step index {idx.mean():.1f}, SNR {snr:.1f} dB, '
              f'mean bits per sample {np.mean(S.bits) / (2 * C.PKT):.2f}', file=sys.stderr)


if __name__ == '__main__':
    main()
