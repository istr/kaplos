# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Kaplos kernels: integer predictor, quantiser with encoder-only noise feedback, Rice coding, bit I/O.

Per channel, sample by sample, with no algorithmic delay:
  prediction  p = (a1 * y[n-1]) / 32 + the sum of a cascade of backward-adaptive integer NLMS stages
              (the decoder runs the same integer arithmetic on the reconstructed samples)
  residual    t = x - p
  shaping     v = t + fb, fb = encoder-only noise feedback (float, never seen by the decoder)
  quantiser   q = round(v / D), D = step from a table, D = 1 means lossless
  output      y = clip(p + q * D)
  coding      zig-zag q, adaptive Rice code, parameter restarted every packet

Packet (one per 1 ms = 48 samples per channel, both channels, fixed byte budget):
  2 bits mode (0 Rice, 1 fixed-length escape), 1 bit stereo (0 L/R, 1 M/S), 1 bit key (the adaptive
  weights restart from zero), 8 bits step index, then per channel 5 bits (Rice k0 or escape width)
  and the 48 codes.
All integer state that the decoder needs is updated identically in encoder and decoder.
"""
import numpy as np
from numba import njit

PKT = 48
W_FRAC = 14
NMAX = 256
QMAX = 20          # Rice quotient limit before escape
RICE_N0 = 4
RICE_RESET = 32
HDR_BITS = 12      # mode 2 + stereo 1 + key 1 + step index 8
CH_BITS = 5


def _delta_table(n=192):
    """Step per index: 2^(i/8) (0.75 dB), but strictly increasing, so at the low end the
    integer steps run 1, 2, 3, ... until the exponential grows faster."""
    d = np.zeros(n, np.int64)
    for i in range(n):
        d[i] = max(int(np.floor(2.0 ** (i / 8.0) + 1e-9)), d[i - 1] + 1 if i else 1)
    return d


DELTA = _delta_table()


# ----------------------------------------------------------------------------- predictor

@njit(cache=True)
def _bitlen(v):
    n = 0
    while v > 0:
        v >>= 1
        n += 1
    return n


@njit(cache=True)
def predict(W, H, orders):
    S = orders.shape[0]
    preds = np.zeros(S, np.int64)
    for s in range(S):
        acc = 0
        for i in range(orders[s]):
            acc += W[s, i] * H[s, i]
        preds[s] = (acc + (1 << (W_FRAC - 1))) >> W_FRAC
    return preds


@njit(cache=True)
def update(W, H, E, orders, mus, leak, preds, r_final):
    """Back-compute the input of every stage from the reconstructed final residual,
    adapt each stage (power-of-two normalised LMS) and push its input into its history.
    Returns the reconstructed input of stage 1."""
    S = orders.shape[0]
    u_next = r_final
    for s in range(S - 1, -1, -1):
        N = orders[s]
        err = u_next
        u_in = u_next + preds[s]
        if err != 0:
            # NLMS normalised by the window power; the err^2 term limits weight jumps when an
            # unpredictable onset meets a quiet history (plain NLMS diverges there)
            sh = _bitlen(E[s] + ((err * err) << 3) + N * 16) - W_FRAC + mus[s]
            if sh > 0:
                rnd = 1 << (sh - 1)
                for i in range(N):
                    W[s, i] += (err * H[s, i] + rnd) >> sh
            else:
                for i in range(N):
                    W[s, i] += (err * H[s, i]) << (-sh)
        if leak > 0:
            for i in range(N):
                W[s, i] -= W[s, i] >> leak
        for i in range(N):
            if W[s, i] > (1 << 20):
                W[s, i] = 1 << 20
            elif W[s, i] < -(1 << 20):
                W[s, i] = -(1 << 20)
        leaving = H[s, N - 1]
        for i in range(N - 1, 0, -1):
            H[s, i] = H[s, i - 1]
        H[s, 0] = u_in
        E[s] += u_in * u_in - leaving * leaving   # exact power of the history window
        u_next = u_in
    return u_next


# ----------------------------------------------------------------------------- channel packet

@njit(cache=True)
def enc_packet_ch(x, W, H, E, misc, orders, mus, leak, a1, delta, nfb, nfc, nfe, nfr,
                  ymin, ymax, qlim, q_out, y_out):
    """Encode 48 samples of one channel. nfb/nfc: noise feedback numerator/denominator
    coefficients (without the leading 1); nfe/nfr: encoder-only histories of quantiser error
    and reconstruction error. qlim > 0 clamps q (fixed-length escape). Returns clip count."""
    nb = nfb.shape[0]
    nc = nfc.shape[0]
    clips = 0
    for n in range(PKT):
        preds = predict(W, H, orders)
        ylin = (a1 * misc[0] + 16) >> 5
        p = ylin + preds.sum()
        if p > ymax:
            p = ymax
        elif p < ymin:
            p = ymin
        t = x[n] - p
        fb = 0.0
        for i in range(nb):
            fb += nfb[i] * nfe[i]
        for i in range(nc):
            fb -= nfc[i] * nfr[i]
        v = t + fb
        q = np.int64(np.floor(v / delta + 0.5))
        if qlim > 0:
            if q > qlim - 1:
                q = qlim - 1
                clips += 1
            elif q < -qlim:
                q = -qlim
                clips += 1
        y = p + q * delta
        if y > ymax:
            y = ymax
        elif y < ymin:
            y = ymin
        r = float(y - x[n])
        eps = r - fb
        for i in range(nb - 1, 0, -1):
            nfe[i] = nfe[i - 1]
        if nb > 0:
            nfe[0] = eps
        for i in range(nc - 1, 0, -1):
            nfr[i] = nfr[i - 1]
        if nc > 0:
            nfr[0] = r
        update(W, H, E, orders, mus, leak, preds, y - p)
        misc[0] = y
        q_out[n] = q
        y_out[n] = y
    return clips


@njit(cache=True)
def dec_packet_ch(q, W, H, E, misc, orders, mus, leak, a1, delta, ymin, ymax, y_out):
    for n in range(PKT):
        preds = predict(W, H, orders)
        ylin = (a1 * misc[0] + 16) >> 5
        p = ylin + preds.sum()
        if p > ymax:
            p = ymax
        elif p < ymin:
            p = ymin
        y = p + q[n] * delta
        if y > ymax:
            y = ymax
        elif y < ymin:
            y = ymin
        update(W, H, E, orders, mus, leak, preds, y - p)
        misc[0] = y
        y_out[n] = y


# ----------------------------------------------------------------------------- Rice coding

@njit(cache=True)
def _zz(q):
    return 2 * q if q >= 0 else -2 * q - 1


@njit(cache=True)
def rice_cost(q, k0):
    A = RICE_N0 << k0
    N = RICE_N0
    bits = 0
    for n in range(q.shape[0]):
        u = _zz(q[n])
        k = 0
        while (N << k) < A:
            k += 1
        m = u >> k
        if m < QMAX:
            bits += m + 1 + k
        else:
            bits += QMAX + 5 + _bitlen(u)
        A += u
        N += 1
        if N >= RICE_RESET:
            A >>= 1
            N >>= 1
    return bits


@njit(cache=True)
def best_k0(q):
    s = 0
    for n in range(q.shape[0]):
        s += _zz(q[n])
    k_est = _bitlen(s // q.shape[0])
    best, bk = 1 << 60, 0
    for k in range(max(0, k_est - 2), min(31, k_est + 3)):
        c = rice_cost(q, k)
        if c < best:
            best, bk = c, k
    return bk, best


# ----------------------------------------------------------------------------- bit I/O

@njit(cache=True)
def put_bits(buf, pos, val, nbits):
    for i in range(nbits - 1, -1, -1):
        if (val >> i) & 1:
            buf[pos >> 3] |= np.uint8(0x80 >> (pos & 7))
        pos += 1
    return pos


@njit(cache=True)
def get_bits(buf, pos, nbits):
    v = 0
    for i in range(nbits):
        v = (v << 1) | ((buf[pos >> 3] >> (7 - (pos & 7))) & 1)
        pos += 1
    return v, pos


@njit(cache=True)
def put_rice(buf, pos, q, k0):
    A = RICE_N0 << k0
    N = RICE_N0
    for n in range(q.shape[0]):
        u = _zz(q[n])
        k = 0
        while (N << k) < A:
            k += 1
        m = u >> k
        if m < QMAX:
            for _ in range(m):
                pos = put_bits(buf, pos, 1, 1)
            pos = put_bits(buf, pos, 0, 1)
            pos = put_bits(buf, pos, u & ((1 << k) - 1), k)
        else:
            for _ in range(QMAX):
                pos = put_bits(buf, pos, 1, 1)
            L = _bitlen(u)
            pos = put_bits(buf, pos, L, 5)
            pos = put_bits(buf, pos, u, L)
        A += u
        N += 1
        if N >= RICE_RESET:
            A >>= 1
            N >>= 1
    return pos


@njit(cache=True)
def get_rice(buf, pos, k0, q):
    A = RICE_N0 << k0
    N = RICE_N0
    for n in range(q.shape[0]):
        k = 0
        while (N << k) < A:
            k += 1
        m = 0
        while m < QMAX:
            b, pos = get_bits(buf, pos, 1)
            if b == 0:
                break
            m += 1
        if m < QMAX:
            low, pos = get_bits(buf, pos, k)
            u = (m << k) | low
        else:
            L, pos = get_bits(buf, pos, 5)
            u, pos = get_bits(buf, pos, L)
        q[n] = (u >> 1) if (u & 1) == 0 else -((u + 1) >> 1)
        A += u
        N += 1
        if N >= RICE_RESET:
            A >>= 1
            N >>= 1
    return pos


# ----------------------------------------------------------------------------- channel state

class Predictor:
    """Configuration of the decoder-side predictor."""

    def __init__(self, stages=((32, 4), (4, 3)), a1=31, leak=0):
        self.orders = np.array([s[0] for s in stages], np.int64)
        self.mus = np.array([s[1] for s in stages], np.int64)
        self.a1 = a1
        self.leak = leak

    def new_state(self):
        S = len(self.orders)
        return [np.zeros((S, NMAX), np.int64), np.zeros((S, NMAX), np.int64),
                np.zeros(S, np.int64), np.zeros(4, np.int64)]


def copy_state(st):
    return [a.copy() for a in st]
