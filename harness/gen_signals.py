# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Generate synthetic critical test signals (48 kHz, stereo, 24-bit in s32le raw).

These are stand-ins for real critical material. They stress the known weak spots of
low-delay codecs (tonal content, dense harmonics, sharp transients, low-level passages),
but they are not music and do not replace a listening test.
"""
import sys
from pathlib import Path
import numpy as np

FS = 48000
DUR = 8.0
rng = np.random.default_rng(20261122)


def t_axis(dur=DUR):
    return np.arange(int(dur * FS)) / FS


def stereoize(mono, delay_samples=7, mix=0.25):
    """Cheap decorrelation: the right channel gets a small delayed cross-mix."""
    d = np.concatenate([np.zeros(delay_samples), mono[:-delay_samples]])
    left = mono + mix * 0.3 * d
    right = (1 - mix) * mono + mix * d
    return np.stack([left, right], axis=1)


def normalize(x, peak_dbfs=-6.0):
    return x * (10 ** (peak_dbfs / 20) / np.max(np.abs(x)))


def piano():
    """Decaying inharmonic partials with a short hammer noise, notes ringing into each other."""
    t = t_axis()
    x = np.zeros_like(t)
    notes = [(0.2, 220.0), (1.0, 277.18), (1.8, 329.63), (2.6, 440.0), (3.4, 110.0),
             (4.6, 659.25), (5.2, 880.0), (5.8, 1318.5), (6.4, 174.61)]
    for start, f0 in notes:
        n0 = int(start * FS)
        tt = t[: len(t) - n0]
        note = np.zeros_like(tt)
        B = 0.0004
        for k in range(1, 40):
            fk = f0 * k * np.sqrt(1 + B * k * k)
            if fk > 18000:
                break
            amp = 1.0 / k ** 1.3
            decay = 1.2 + 0.9 * k
            note += amp * np.exp(-decay * tt) * np.sin(2 * np.pi * fk * tt + rng.uniform(0, 2 * np.pi))
        hammer = rng.standard_normal(len(tt)) * np.exp(-tt * 400) * 0.15
        x[n0:] += note * (1 - np.exp(-tt * 2000)) + hammer
    return normalize(stereoize(x))


def recorder():
    """High, nearly pure tone with weak harmonics, vibrato and faint breath noise."""
    t = t_axis()
    x = np.zeros_like(t)
    seq = [1568.0, 1760.0, 1975.5, 2093.0, 2349.3, 2637.0, 2093.0, 1760.0]
    seg = len(t) // len(seq)
    for i, f0 in enumerate(seq):
        tt = t[:seg]
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * tt)
        ph = 2 * np.pi * np.cumsum(f0 * vib) / FS
        tone = np.sin(ph) + 0.05 * np.sin(2 * ph) + 0.02 * np.sin(3 * ph)
        env = np.minimum(1, tt / 0.03) * np.minimum(1, (tt[-1] - tt) / 0.05)
        x[i * seg:(i + 1) * seg] = tone * env
    breath = rng.standard_normal(len(t)) * 10 ** (-52 / 20)
    return normalize(stereoize(x + breath))


def glockenspiel():
    """Struck high sinusoidal partials with sharp attacks."""
    t = t_axis()
    x = np.zeros_like(t)
    for i in range(16):
        n0 = int((0.2 + i * 0.47) * FS)
        f0 = [2093.0, 2637.0, 3136.0, 3520.0, 4186.0, 5274.0][i % 6]
        tt = t[: len(t) - n0]
        note = (np.sin(2 * np.pi * f0 * tt) + 0.5 * np.sin(2 * np.pi * f0 * 2.76 * tt)
                + 0.25 * np.sin(2 * np.pi * f0 * 5.4 * tt) * (f0 * 5.4 < 20000))
        x[n0:] += note * np.exp(-tt * 3.0) * (tt >= 0)
    return normalize(stereoize(x))


def castanets():
    """Isolated broadband clicks with silence in between (pre-echo test)."""
    t = t_axis()
    x = np.zeros_like(t)
    pos = 0.3
    while pos < DUR - 0.2:
        n0 = int(pos * FS)
        tt = t[: int(0.05 * FS)]
        click = rng.standard_normal(len(tt)) * np.exp(-tt * 250)
        click += np.sin(2 * np.pi * 2400 * tt) * np.exp(-tt * 180)
        x[n0:n0 + len(tt)] += click
        pos += rng.uniform(0.12, 0.45)
    return normalize(stereoize(x))


def harpsichord():
    """Dense harmonic series (plucked, bright): needs fine frequency resolution."""
    t = t_axis()
    x = np.zeros_like(t)
    seq = [110.0, 146.83, 164.81, 196.0, 220.0, 261.63, 293.66, 329.63, 392.0, 440.0,
           130.81, 174.61, 98.0, 246.94, 349.23, 523.25]
    for i, f0 in enumerate(seq):
        n0 = int((0.1 + i * 0.48) * FS)
        tt = t[: len(t) - n0]
        note = np.zeros_like(tt)
        k = 1
        while f0 * k < 16000:
            note += (1.0 / k ** 0.8) * np.exp(-(1.5 + 0.12 * k) * tt) * np.sin(
                2 * np.pi * f0 * k * tt + rng.uniform(0, 2 * np.pi))
            k += 1
        x[n0:] += note
    return normalize(stereoize(x))


def applause():
    """Dense random noise bursts."""
    t = t_axis()
    x = np.zeros_like(t)
    n_claps = int(DUR * 220)
    tt = t[: int(0.012 * FS)]
    for _ in range(n_claps):
        n0 = rng.integers(0, len(t) - len(tt))
        burst = rng.standard_normal(len(tt)) * np.exp(-tt * rng.uniform(300, 900))
        x[n0:n0 + len(tt)] += burst * rng.uniform(0.2, 1.0)
    left = x
    y = np.zeros_like(t)
    for _ in range(n_claps):
        n0 = rng.integers(0, len(t) - len(tt))
        burst = rng.standard_normal(len(tt)) * np.exp(-tt * rng.uniform(300, 900))
        y[n0:n0 + len(tt)] += burst * rng.uniform(0.2, 1.0)
    st = np.stack([left + 0.4 * y, y + 0.4 * left], axis=1)
    return normalize(st)


def quiet_tone():
    """1 kHz sine at -60 dBFS with fade: low-level behaviour and idle noise."""
    t = t_axis()
    x = np.sin(2 * np.pi * 1000 * t) * 10 ** (-60 / 20)
    x[: FS // 2] = 0
    x[-FS // 2:] = 0
    return np.stack([x, x], axis=1)


SIGNALS = {
    'piano': piano, 'recorder': recorder, 'glockenspiel': glockenspiel, 'castanets': castanets,
    'harpsichord': harpsichord, 'applause': applause, 'quiet_tone': quiet_tone,
}

if __name__ == '__main__':
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in SIGNALS.items():
        x = fn()
        # truncate to a multiple of 480 samples so all frame sizes under test divide evenly
        n = (len(x) // 1920) * 1920
        x = x[:n]
        q = np.clip(np.round(x * 2 ** 23), -2 ** 23, 2 ** 23 - 1).astype('<i4')
        q.tofile(out / f'{name}.s32')
        print(f'{name:13s} {n / FS:.2f}s peak {20 * np.log10(np.max(np.abs(x)) + 1e-12):6.1f} dBFS '
              f'rms {20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12):6.1f} dBFS')
