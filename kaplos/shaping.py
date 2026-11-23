# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Encoder-only noise shaping filters.

A shaper returns (b, c) for the noise feedback loop: the reconstruction error becomes
r = (B(z) / C(z)) * e with B = 1 + sum b_i z^-i, C = 1 + sum c_i z^-i and e the (white)
quantiser error. Both filters are minimum phase, so the shaped noise keeps the geometric-mean
level of e (Gerzon and Craven) and the step size alone sets the rate.

LPCShaper   classic speech-coding weighting: B/C = A(z/g2) / A(z/g1) from an LPC of the signal.
MaskShaper  all-pole fit to a masking threshold (the Johnston-style model of the NMR heuristic in
            harness/analyze.py), with depth control: exponent beta and a maximum range in dB.
"""
import numpy as np
from . import codec as C


def levinson(r, order):
    a = np.zeros(order + 1)
    a[0] = 1.0
    err = r[0]
    for i in range(1, order + 1):
        acc = r[i] + np.dot(a[1:i], r[i - 1:0:-1])
        k = -acc / err
        a[1:i] = a[1:i] + k * a[i - 1:0:-1]
        a[i] = k
        err *= (1 - k * k)
        if err <= 0:
            break
    return a


def _window_signal(x, k, ch, ms, win):
    end = (k + 1) * C.PKT
    start = max(0, end - win)
    seg = x[start:end].astype(np.float64)
    if ms:
        s = seg[:, 0] - seg[:, 1]
        m = seg[:, 1] + s / 2
        sig = m if ch == 0 else s
    else:
        sig = seg[:, ch]
    if len(sig) < win:
        sig = np.concatenate([np.zeros(win - len(sig)), sig])
    return sig


class LPCShaper:
    def __init__(self, order=16, g1=0.94, g2=0.5, win=256, gmax_db=None):
        self.order, self.g1, self.g2, self.win = order, g1, g2, win
        self.w = np.hanning(win)
        self.gmax = None if gmax_db is None else 10 ** (gmax_db / 10)

    def __call__(self, x, k, ch, ms):
        s = _window_signal(x, k, ch, ms, self.win) * self.w
        r = np.correlate(s, s, 'full')[self.win - 1:self.win + self.order]
        if r[0] <= 0:
            return np.zeros(0), np.zeros(0)
        r[0] *= 1.0001
        r[1:] *= np.exp(-0.5 * (2 * np.pi * 60 / 48000 * np.arange(1, self.order + 1)) ** 2)
        a = levinson(r, self.order)
        i = np.arange(1, self.order + 1)
        g1, g2 = self.g1, self.g2
        for _ in range(20):
            b = a[1:] * g2 ** i
            c = a[1:] * g1 ** i
            if self.gmax is None:
                break
            # noise power gain of the monic minimum-phase shaping filter B/C
            H2 = np.abs(np.fft.rfft(np.r_[1.0, b], 512)) ** 2 / np.abs(np.fft.rfft(np.r_[1.0, c], 512)) ** 2
            if np.mean(H2) <= self.gmax:
                break
            g1 *= 0.97
            g2 *= 0.97
        return b, c


class MaskShaper:
    """Noise PSD follows the masking threshold of the current window (512 samples ending at
    the packet end), compressed by beta and limited to range_db below its maximum."""
    FS = 48000

    def __init__(self, bitdepth=24, order=24, beta=1.0, range_db=40.0, win=512, spl_fs=100.0,
                 gmax_db=10.0, hf_hz=16000.0):
        self.order, self.beta, self.range_db, self.win = order, beta, range_db, win
        self.gmax_db = gmax_db
        self.hf_hz = hf_hz
        self.scale = 2.0 ** (bitdepth - 1)
        n = win
        f = np.fft.rfftfreq(n, 1 / self.FS)
        z = 13 * np.arctan(0.00076 * f) + 3.5 * np.arctan((f / 7500.0) ** 2)
        band = np.floor(z / 0.5).astype(int)
        nb = band.max() + 1
        zc = (np.arange(nb) + 0.5) * 0.5
        dz = zc[:, None] - zc[None, :]
        sf = 10 ** ((15.81 + 7.5 * (dz + 0.474) - 17.5 * np.sqrt(1 + (dz + 0.474) ** 2)) / 10)
        ff = np.maximum(f, 20.0) / 1000.0
        ath = 3.64 * ff ** -0.8 - 6.5 * np.exp(-0.6 * (ff - 3.3) ** 2) + 1e-3 * ff ** 4
        ath_band = np.array([ath[band == b].min() if (band == b).any() else 200.0 for b in range(nb)])
        self.ath_lin = 10 ** ((ath_band - spl_fs) / 10)
        self.band, self.nb, self.zc, self.sf, self.sf_gain = band, nb, zc, sf, sf.sum(axis=1)
        self.bandmat = np.zeros((nb, len(f)))
        self.bandmat[band, np.arange(len(f))] = 1.0
        self.nbins = self.bandmat.sum(axis=1)
        self.w = np.hanning(n)
        self.norm = 4.0 / (n * np.sum(self.w ** 2))
        self.f = f
        self.sel = f < 20000

    def threshold_psd(self, s):
        X = np.abs(np.fft.rfft(s * self.w)) ** 2 * self.norm + 1e-30
        Ps = self.bandmat @ X
        Xs = X[self.sel]
        sfm_db = 10 * (np.mean(np.log10(Xs)) - np.log10(np.mean(Xs)))
        alpha = np.clip(sfm_db / -60.0, 0, 1)
        offset_db = alpha * (14.5 + self.zc) + (1 - alpha) * 5.5
        spread = (self.sf @ Ps) / self.sf_gain
        mask = np.maximum(spread * 10 ** (-offset_db / 10), self.ath_lin)
        D = (mask / np.maximum(self.nbins, 1))[self.band]          # allowed noise per bin
        D[~self.sel] = D[self.sel][-1]                              # above 20 kHz: continue the top band
        return D

    def __call__(self, x, k, ch, ms):
        s = _window_signal(x, k, ch, ms, self.win) / self.scale
        D = self.threshold_psd(s)
        L = np.log(D)
        # the threshold in quiet explodes above ~16 kHz; continue the 16 kHz level instead of
        # letting the shaper dump its noise budget there
        i16 = np.searchsorted(self.f, self.hf_hz)
        L[i16:] = np.minimum(L[i16:], L[i16])
        L = L - L.max()
        L = np.maximum(L, -self.range_db / 10 * np.log(10))
        # noise power gain of the shaped noise over white noise at equal step size
        # (arithmetic over geometric mean of the PSD); cap it by lowering the exponent
        beta = self.beta
        for _ in range(12):
            Lb = beta * L
            g_db = 10 / np.log(10) * (np.log(np.mean(np.exp(Lb))) - np.mean(Lb))
            if g_db <= self.gmax_db:
                break
            beta *= 0.8
        P = np.exp(beta * L)
        r = np.fft.irfft(P)[:self.order + 1]
        r[0] *= 1.0001
        a = levinson(r, self.order)
        return np.zeros(0), a[1:]
