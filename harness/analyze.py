# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Objective comparison helpers: delay estimation, SNR and a rough noise-to-mask ratio (NMR).

The NMR is a heuristic in the style of Johnston's 1988 perceptual entropy model:
half-Bark bands, Schroeder spreading function, tonality from the spectral flatness measure,
Terhardt's threshold in quiet with a full-scale sine mapped to 100 dB SPL. No temporal
masking is modelled. It ranks codecs on the same signal; it does not predict audibility.
"""
import numpy as np

FS = 48000
NFFT = 2048
HOP = 1024
SPL_FULL_SCALE = 100.0


def load_s32_24(path, channels=2):
    return np.fromfile(path, dtype='<i4').reshape(-1, channels).astype(np.float64) / 2 ** 23


def load_s24(path, channels=2):
    raw = np.fromfile(path, dtype=np.uint8)
    raw = raw[: len(raw) // (3 * channels) * 3 * channels].reshape(-1, 3)
    v = raw[:, 0].astype(np.int32) | (raw[:, 1].astype(np.int32) << 8) | (raw[:, 2].astype(np.int32) << 16)
    v = np.where(v >= 1 << 23, v - (1 << 24), v)
    return v.reshape(-1, channels).astype(np.float64) / 2 ** 23


def save_s24(path, x):
    q = np.clip(np.round(x * 2 ** 23), -2 ** 23, 2 ** 23 - 1).astype(np.int32).reshape(-1)
    out = np.empty((len(q), 3), dtype=np.uint8)
    out[:, 0] = q & 0xFF
    out[:, 1] = (q >> 8) & 0xFF
    out[:, 2] = (q >> 16) & 0xFF
    out.tofile(path)


def estimate_delay(ref, dec, max_lag=4096):
    """Lag (in samples) of dec relative to ref that maximises the cross-correlation (channel 0)."""
    n = min(len(ref), len(dec))
    a = ref[:n, 0]
    b = dec[:n, 0]
    size = 1 << int(np.ceil(np.log2(2 * n)))
    fa = np.fft.rfft(a, size)
    fb = np.fft.rfft(b, size)
    cc = np.fft.irfft(fb * np.conj(fa), size)
    lags = np.arange(0, max_lag)
    return int(lags[np.argmax(cc[:max_lag])])


def align(ref, dec, delay):
    n = min(len(ref), len(dec) - delay)
    return ref[:n], dec[delay:delay + n]


def snr_db(ref, dec):
    err = dec - ref
    return 10 * np.log10(np.sum(ref ** 2) / max(np.sum(err ** 2), 1e-30))


def _bark(f):
    return 13 * np.arctan(0.00076 * f) + 3.5 * np.arctan((f / 7500.0) ** 2)


def _ath_spl(f):
    f = np.maximum(f, 20.0) / 1000.0
    return 3.64 * f ** -0.8 - 6.5 * np.exp(-0.6 * (f - 3.3) ** 2) + 1e-3 * f ** 4


_freqs = np.fft.rfftfreq(NFFT, 1 / FS)
_z = _bark(_freqs)
_band = np.floor(_z / 0.5).astype(int)
_nb = _band.max() + 1
_zc = (np.arange(_nb) + 0.5) * 0.5
_dz = _zc[:, None] - _zc[None, :]  # maskee - masker
_sf = 10 ** ((15.81 + 7.5 * (_dz + 0.474) - 17.5 * np.sqrt(1 + (_dz + 0.474) ** 2)) / 10)
_sf_gain = _sf.sum(axis=1)
_ath_band = np.full(_nb, np.inf)
for _b in range(_nb):
    sel = _band == _b
    if sel.any():
        _ath_band[_b] = np.min(_ath_spl(_freqs[sel]))
_ath_lin = 10 ** ((_ath_band - SPL_FULL_SCALE) / 10)
_fc = np.array([_freqs[_band == b].mean() if (_band == b).any() else np.nan for b in range(_nb)])
_use = _fc < 20000
_win = np.hanning(NFFT)
_norm = 4.0 / (NFFT * np.sum(_win ** 2))
_bandmat = np.zeros((_nb, len(_freqs)))
_bandmat[_band, np.arange(len(_freqs))] = 1.0


def nmr_frames(ref, dec):
    """Per-frame worst-band NMR in dB, pooled over channels."""
    out = []
    for ch in range(ref.shape[1]):
        x = ref[:, ch]
        e = dec[:, ch] - ref[:, ch]
        nfr = (len(x) - NFFT) // HOP
        idx = np.arange(NFFT)[None, :] + HOP * np.arange(nfr)[:, None]
        X = np.abs(np.fft.rfft(x[idx] * _win, axis=1)) ** 2 * _norm
        E = np.abs(np.fft.rfft(e[idx] * _win, axis=1)) ** 2 * _norm
        Ps = X @ _bandmat.T
        Pn = E @ _bandmat.T
        sel = _freqs < 20000
        Xs = X[:, sel] + 1e-30
        sfm_db = 10 * (np.mean(np.log10(Xs), axis=1) - np.log10(np.mean(Xs, axis=1)))
        alpha = np.clip(sfm_db / -60.0, 0, 1)[:, None]
        offset_db = alpha * (14.5 + _zc[None, :]) + (1 - alpha) * 5.5
        spread = (Ps @ _sf.T) / _sf_gain[None, :]
        mask = np.maximum(spread * 10 ** (-offset_db / 10), _ath_lin[None, :])
        nmr = 10 * np.log10((Pn + 1e-30) / mask)
        out.append(np.max(nmr[:, _use], axis=1))
    return np.concatenate(out)


def metrics(ref, dec, delay=None):
    if delay is None:
        delay = estimate_delay(ref, dec)
    r, d = align(ref, dec, delay)
    # ignore the first and last 50 ms (codec start-up and tail)
    cut = int(0.05 * FS)
    r, d = r[cut:-cut], d[cut:-cut]
    nm = nmr_frames(r, d)
    return {
        'delay': delay,
        'snr': snr_db(r, d),
        'nmr95': float(np.percentile(nm, 95)),
        'nmr_max': float(np.max(nm)),
        'nmr_mean': float(np.mean(nm)),
    }
