# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Reference codecs for comparison: 16-bit PCM, IMA ADPCM, aptX, aptX HD (via ffmpeg) and Opus Custom
(the occ helper program, built as described in harness/occ.c). Decoded outputs are cached in out/."""
import subprocess
import sys
from pathlib import Path
import numpy as np
from . import analyze as A
from . import gen_signals as G

ROOT = Path(__file__).resolve().parent.parent
SIG, OUT = ROOT / 'out' / 'sig', ROOT / 'out'
OUT.mkdir(exist_ok=True)


def _ff(args):
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + [str(a) for a in args],
                   check=True)


def ref(sig):
    return A.load_s32_24(SIG / f'{sig}.s32')


def pcm16(sig, seed=1):
    x = ref(sig)
    rng = np.random.default_rng(seed)
    d = (rng.random(x.shape) - rng.random(x.shape)) / 32768
    return np.round((x + d) * 32768) / 32768, 768.0 * 2, 0


def adpcm(sig):
    x = ref(sig)
    s24, wav, dec = OUT / f'{sig}.s24', OUT / f'{sig}_adpcm.wav', OUT / f'{sig}_adpcm.s24'
    if not dec.exists():
        A.save_s24(s24, x)
        _ff(['-f', 's24le', '-ar', '48000', '-ac', '2', '-i', s24, '-c:a', 'adpcm_ima_wav', wav])
        _ff(['-i', wav, '-f', 's24le', dec])
    kbps = wav.stat().st_size * 8 / (len(x) / 48000) / 1000
    return A.load_s24(dec), kbps, None


def aptx(sig, hd=False):
    codec = 'aptx_hd' if hd else 'aptx'
    x = ref(sig)
    s24, enc, dec = OUT / f'{sig}.s24', OUT / f'{sig}.{codec}', OUT / f'{sig}_{codec}.s24'
    if not dec.exists():
        A.save_s24(s24, x)
        _ff(['-f', 's24le', '-ar', '48000', '-ac', '2', '-i', s24, '-c:a', codec, '-f', codec, enc])
        _ff(['-f', codec, '-sample_rate', '48000', '-i', enc, '-f', 's24le', dec])
    kbps = enc.stat().st_size * 8 / (len(x) / 48000) / 1000
    return A.load_s24(dec), kbps, None


def opus_custom(sig, frame, kbps, complexity=10):
    binary = OUT / 'occ'
    if not binary.exists():
        raise FileNotFoundError(f'{binary} is missing: build it as described in harness/occ.c')
    nbytes = round(kbps * 1000 * frame / 48000 / 8)
    out = OUT / f'{sig}_occ{frame}_{kbps}.s32'
    if not out.exists():
        subprocess.run([binary, '48000', '2', str(frame), str(nbytes), str(complexity), SIG / f'{sig}.s32',
                        out], check=True, capture_output=True)
    return A.load_s32_24(out), nbytes * 8 * 48000 / frame / 1000, None


BASELINES = {
    'pcm16': pcm16,
    'adpcm4_384': adpcm,
    'aptx_384': lambda s: aptx(s, False),
    'aptxhd_576': lambda s: aptx(s, True),
    'occ1ms_384': lambda s: opus_custom(s, 48, 384),
    'occ2ms_384': lambda s: opus_custom(s, 96, 384),
    'occ1ms_576': lambda s: opus_custom(s, 48, 576),
    'occ2ms_576': lambda s: opus_custom(s, 96, 576),
}

if __name__ == '__main__':
    names = sys.argv[1:] or list(BASELINES)
    for sig in G.SIGNALS:
        r = ref(sig)
        row = []
        for name in names:
            dec, kbps, delay = BASELINES[name](sig)
            m = A.metrics(r, dec, delay=delay)
            row.append(f'{name} {m["nmr95"]:6.1f}')
        print(f'{sig:13s} ' + ' | '.join(row), flush=True)
