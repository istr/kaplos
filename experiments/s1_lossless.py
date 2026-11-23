# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Stage S1: lossless core. Bits per sample of the predictor variants in 48-sample packets
(Rice parameter restarted every packet) against FLAC -8, for 24-bit and 16-bit versions of the
test signals. Also checks bit-exact decoding through the real bitstream."""
import subprocess
import sys
import time
import numpy as np
from harness import analyze as A
from harness import gen_signals as G
from harness.baselines import SIG, OUT
from kaplos import codec as C
from kaplos import packet


def load_int(sig, bits):
    x = np.fromfile(SIG / f'{sig}.s32', dtype='<i4').reshape(-1, 2).astype(np.int64)
    if bits == 24:
        return x
    rng = np.random.default_rng(7)
    d = rng.random(x.shape) - rng.random(x.shape)
    return np.clip(np.round(x / 256.0 + d), -32768, 32767).astype(np.int64)


def flac_bps(x, bits, frame_size=None):
    raw = OUT / 'flac_in.raw'
    if bits == 16:
        x.astype('<i2').tofile(raw)
        fmt = 's16le'
    else:
        A.save_s24(raw, x / 2 ** 23)
        fmt = 's24le'
    out = OUT / 'flac_out.flac'
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', fmt, '-ar', '48000', '-ac', '2',
           '-i', raw, '-c:a', 'flac', '-compression_level', '8']
    if frame_size:
        cmd += ['-frame_size', str(frame_size)]
    if bits == 24:
        cmd += ['-sample_fmt', 's32']
    subprocess.run(cmd + [out], check=True)
    return out.stat().st_size * 8 / x.size


PREDICTORS = {
    'fixed1': C.Predictor(stages=((1, 30),), a1=32),
    'nlms8': C.Predictor(stages=((8, 4),)),
    'nlms16': C.Predictor(stages=((16, 4),)),
    'nlms32': C.Predictor(stages=((32, 4),)),
    'nlms32_mu5': C.Predictor(stages=((32, 5),)),
    'nlms32+4': C.Predictor(stages=((32, 4), (4, 3))),
    'nlms256+16': C.Predictor(stages=((256, 5), (16, 4))),
}

if __name__ == '__main__':
    names = sys.argv[1:] or list(PREDICTORS)
    for bits in (16, 24):
        print(f'== {bits}-bit: mean bits per sample (packet 99.9 percentile) ==')
        print(f'{"signal":13s} {"flac-8":>7s} {"flac48":>7s} ' + ' '.join(f'{n:>15s}' for n in names))
        for sig in G.SIGNALS:
            x = load_int(sig, bits)
            row = [f'{flac_bps(x, bits):7.2f}', f'{flac_bps(x, bits, 48):7.2f}']
            for name in names:
                P = PREDICTORS[name]
                pk, y, S = packet.encode(x, bitdepth=bits, pred=P, budget=None, collect=True)
                assert np.array_equal(y, x[:len(y)]), 'encoder reconstruction not lossless'
                b = np.array(S.bits) / (2 * C.PKT)
                row.append(f'{b.mean():6.2f} ({np.percentile(b, 99.9):5.2f})')
            print(f'{sig:13s} ' + ' '.join(f'{c:>7s}' if i < 2 else f'{c:>15s}' for i, c in enumerate(row)),
                  flush=True)
    # bit-exact check through the real bitstream
    P = PREDICTORS['nlms32']
    x = load_int('piano', 24)
    t0 = time.time()
    pk, y, S = packet.encode(x, bitdepth=24, pred=P, budget=None)
    t1 = time.time()
    z = packet.decode(pk, bitdepth=24, pred=P)
    t2 = time.time()
    print('bitstream decode bit-exact:', np.array_equal(z, x[:len(z)]),
          f'(encode {t1 - t0:.1f} s, decode {t2 - t1:.1f} s for 8 s of audio)')
