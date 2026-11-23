# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Kaplos packet encoder and decoder.

encode(x, ...) -> list of packets (bytes), decoded signal as seen by the encoder, statistics
decode(packets, ...) -> decoded signal

x is an int64 array (samples, 2) at the given bit depth. Every packet carries 48 samples per
channel. With budget=None the coder runs lossless at a variable packet size; with a byte budget
every packet has exactly that size and the rate control chooses the step per packet.
"""
import numpy as np
from . import codec as C

PKT = C.PKT
# smallest budget the escape mode can fill: header, two channel fields, one bit per sample
MIN_BUDGET = (C.HDR_BITS + 2 * (C.CH_BITS + PKT) + 7) // 8


class Stats:
    def __init__(self):
        self.bits = []
        self.idx = []
        self.mode = []
        self.trials = []
        self.clips = 0
        self.resets = 0


def _stereo_fwd(l, r):
    s = l - r
    m = r + (s >> 1)
    return m, s


def _stereo_inv(m, s):
    r = m - (s >> 1)
    return r + s, r


def _idx_for(delta, idx_max):
    return int(min(idx_max, np.searchsorted(C.DELTA, delta)))


def encode(x, bitdepth=24, pred=None, budget=None, shaper=None, stereo='lr', idx_max=191,
           collect=False):
    if budget is not None and budget < MIN_BUDGET:
        raise ValueError(f'budget of {budget} bytes is below the minimum of {MIN_BUDGET} bytes per packet')
    pred = pred or C.Predictor()
    n_pk = len(x) // PKT
    ymin, ymax = -(1 << (bitdepth - 1)), (1 << (bitdepth - 1)) - 1
    st = [pred.new_state(), pred.new_state()]
    nf_len = 32
    nfe = [np.zeros(nf_len), np.zeros(nf_len)]
    nfr = [np.zeros(nf_len), np.zeros(nf_len)]
    zero = np.zeros(0)
    y = np.zeros((n_pk * PKT, 2), np.int64)
    packets = []
    S = Stats()
    idx_prev = 0
    bits_prev = 0
    q = [np.zeros(PKT, np.int64), np.zeros(PKT, np.int64)]
    yo = [np.zeros(PKT, np.int64), np.zeros(PKT, np.int64)]
    budget_bits = None if budget is None else budget * 8

    for k in range(n_pk):
        seg = x[k * PKT:(k + 1) * PKT]
        ms = 1 if stereo == 'ms' else 0
        if ms:
            m_, s_ = _stereo_fwd(seg[:, 0], seg[:, 1])
            chans = [m_, s_]
            lim = [(ymin, ymax), (2 * ymin, 2 * ymax + 1)]
        else:
            chans = [seg[:, 0].copy(), seg[:, 1].copy()]
            lim = [(ymin, ymax), (ymin, ymax)]
        # encoder-only noise shaping filters for this packet
        if shaper is not None and budget is not None:
            filt = [shaper(x, k, c, ms) for c in range(2)]
        else:
            filt = [(zero, zero), (zero, zero)]

        def attempt(idx, qlim=0, use_nf=True, reset=False):
            sts = [C.copy_state(st[c]) for c in range(2)]
            if reset:
                for c in range(2):
                    sts[c][0][:] = 0          # key packet: adaptive weights restart from zero
            use_nf = use_nf and C.DELTA[idx] >= 2      # step 1 is lossless: no shaping
            nes = [nfe[c].copy() for c in range(2)]
            nrs = [nfr[c].copy() for c in range(2)]
            if not use_nf:
                for c in range(2):
                    nes[c][:] = 0
                    nrs[c][:] = 0
            clips = 0
            for c in range(2):
                b, a = filt[c] if use_nf else (zero, zero)
                W, H, E, misc = sts[c]
                clips += C.enc_packet_ch(chans[c], W, H, E, misc, pred.orders, pred.mus, pred.leak,
                                         pred.a1, C.DELTA[idx], b, a, nes[c][:len(b)] if len(b) else zero,
                                         nrs[c][:len(a)] if len(a) else zero,
                                         lim[c][0], lim[c][1], qlim, q[c], yo[c])
            return sts, nes, nrs, clips

        trials = 0
        mode = 0
        key = 0
        if budget is None:
            idx = 0
            sts, nes, nrs, clips = attempt(0)
            ks = [C.best_k0(q[c]) for c in range(2)]
            bits = C.HDR_BITS + sum(C.CH_BITS + kb[1] for kb in ks)
            trials = 1
        else:
            # start from the step that would have filled ~97 % of the last packet
            # (about 12 bits per step index for 96 samples)
            target = 0.97 * budget_bits
            # bits per sample change by log2 of the step ratio; map through the step table
            # (linear at the low end, 0.75 dB steps above)
            idx0 = _idx_for(C.DELTA[idx_prev] * 2.0 ** ((bits_prev - target) / (2 * PKT)), idx_max)

            def search(idx, reset):
                """Smallest step index that fits: climb with estimated jumps, then bisect back
                down if a jump overshot (escape-heavy Rice costs exaggerate the overshoot)."""
                tr, lo, best = 0, -1, None
                for _ in range(10):
                    tr += 1
                    res = attempt(idx, reset=reset)
                    ks_ = [C.best_k0(q[c]) for c in range(2)]
                    b_ = C.HDR_BITS + sum(C.CH_BITS + kb[1] for kb in ks_)
                    if b_ <= budget_bits:
                        best = (idx, res, ks_, b_, [q[0].copy(), q[1].copy()], [yo[0].copy(), yo[1].copy()])
                        break
                    lo = idx
                    if idx >= idx_max:
                        break
                    jump = C.DELTA[idx] * 2.0 ** ((b_ - 0.97 * budget_bits) / (2 * PKT))
                    idx = max(idx + 1, _idx_for(jump, idx_max))
                    idx = min(idx_max, idx)
                if best is None:
                    return (False, idx, res, ks_, b_, tr, [q[0].copy(), q[1].copy()],
                            [yo[0].copy(), yo[1].copy()])
                hi = best[0]
                while lo >= 0 and hi - lo > 1:
                    mid = (lo + hi) // 2
                    tr += 1
                    res = attempt(mid, reset=reset)
                    ks_ = [C.best_k0(q[c]) for c in range(2)]
                    b_ = C.HDR_BITS + sum(C.CH_BITS + kb[1] for kb in ks_)
                    if b_ <= budget_bits:
                        hi = mid
                        best = (mid, res, ks_, b_, [q[0].copy(), q[1].copy()], [yo[0].copy(), yo[1].copy()])
                    else:
                        lo = mid
                i_, res, ks_, b_, qq_, yy_ = best
                return True, i_, res, ks_, b_, tr, qq_, yy_

            ok, idx, res, ks, bits, trials, qq, yy = search(idx0, False)
            if idx > 0 and (not ok or idx > idx_prev + 6):
                alt = search(idx0, True)
                trials += alt[5]
                if alt[0] and (not ok or alt[1] < idx):
                    ok, idx, res, ks, bits, _, qq, yy = alt
                    key = 1
                    S.resets += 1
            sts, nes, nrs, clips = res
            q[0][:], q[1][:] = qq
            yo[0][:], yo[1][:] = yy
            if not ok:
                mode = 1
                width = (budget_bits - C.HDR_BITS - 2 * C.CH_BITS) // (2 * PKT)
                qlim = 1 << (width - 1)
                for it in range(8):
                    trials += 1
                    sts, nes, nrs, clips = attempt(idx, qlim, use_nf=False)
                    if clips == 0 or idx >= idx_max or it == 7:
                        break
                    idx = min(idx_max, idx + 4)
                nes = [np.zeros(nf_len), np.zeros(nf_len)]
                nrs = [np.zeros(nf_len), np.zeros(nf_len)]
                bits = C.HDR_BITS + 2 * (C.CH_BITS + PKT * width)
                S.clips += clips
        # commit
        st = sts
        nfe, nfr = nes, nrs
        idx_prev = idx
        bits_prev = bits
        nbytes = budget if budget is not None else (bits + 7) // 8
        buf = np.zeros(nbytes + 8, np.uint8)
        pos = C.put_bits(buf, 0, mode, 2)
        pos = C.put_bits(buf, pos, ms, 1)
        pos = C.put_bits(buf, pos, key, 1)
        pos = C.put_bits(buf, pos, idx, 8)
        for c in range(2):
            if mode == 0:
                pos = C.put_bits(buf, pos, ks[c][0], 5)
                pos = C.put_rice(buf, pos, q[c], ks[c][0])
            else:
                pos = C.put_bits(buf, pos, width, 5)
                for n in range(PKT):
                    pos = C.put_bits(buf, pos, int(q[c][n]) & ((1 << width) - 1), width)
        assert pos == bits, (pos, bits)
        assert budget is None or pos <= budget * 8
        packets.append(bytes(buf[:nbytes]))
        if ms:
            l_, r_ = _stereo_inv(yo[0], yo[1])
        else:
            l_, r_ = yo[0], yo[1]
        y[k * PKT:(k + 1) * PKT, 0] = l_
        y[k * PKT:(k + 1) * PKT, 1] = r_
        if collect:
            S.bits.append(bits)
            S.idx.append(idx)
            S.mode.append(mode)
            S.trials.append(trials)
    return packets, y, S


def decode(packets, bitdepth=24, pred=None):
    """Decode packets produced by encode() with the same bit depth and predictor."""
    pred = pred or C.Predictor()
    ymin, ymax = -(1 << (bitdepth - 1)), (1 << (bitdepth - 1)) - 1
    st = [pred.new_state(), pred.new_state()]
    y = np.zeros((len(packets) * PKT, 2), np.int64)
    q = [np.zeros(PKT, np.int64), np.zeros(PKT, np.int64)]
    yo = [np.zeros(PKT, np.int64), np.zeros(PKT, np.int64)]
    for k, pk in enumerate(packets):
        buf = np.frombuffer(pk + b'\0' * 8, np.uint8)
        mode, pos = C.get_bits(buf, 0, 2)
        ms, pos = C.get_bits(buf, pos, 1)
        key, pos = C.get_bits(buf, pos, 1)
        if key:
            for c in range(2):
                st[c][0][:] = 0
        idx, pos = C.get_bits(buf, pos, 8)
        for c in range(2):
            v, pos = C.get_bits(buf, pos, 5)
            if mode == 0:
                pos = C.get_rice(buf, pos, v, q[c])
            else:
                for n in range(PKT):
                    u, pos = C.get_bits(buf, pos, v)
                    q[c][n] = u - (1 << v) if u >= (1 << (v - 1)) else u
        lim = [(ymin, ymax), (2 * ymin, 2 * ymax + 1)] if ms else [(ymin, ymax), (ymin, ymax)]
        for c in range(2):
            W, H, E, misc = st[c]
            C.dec_packet_ch(q[c], W, H, E, misc, pred.orders, pred.mus, pred.leak, pred.a1,
                            C.DELTA[idx], lim[c][0], lim[c][1], yo[c])
        if ms:
            l_, r_ = _stereo_inv(yo[0], yo[1])
        else:
            l_, r_ = yo[0], yo[1]
        y[k * PKT:(k + 1) * PKT, 0] = l_
        y[k * PKT:(k + 1) * PKT, 1] = r_
    return y
