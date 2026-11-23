// SPDX-License-Identifier: BSD-2-Clause-Patent
/* occ - Opus Custom codec test harness (encode + decode through libopus' Opus Custom API).
 *
 * Usage: occ <rate> <channels> <frame_size> <bytes_per_packet> <complexity> <in.s32> <out.s32>
 *
 * Build, from the repository root, against libopus built with custom modes:
 *   gcc -O2 -I/usr/local/include/opus -o out/occ harness/occ.c /usr/local/lib/libopus.a -lm
 *
 * I/O is raw interleaved signed 32-bit little-endian holding 24-bit samples
 * (range -2^23 .. 2^23-1), so the same harness works for float and fixed-point builds.
 * The output is NOT delay-compensated: the decoder look-ahead is left in so it can be measured.
 * Encoding and decoding run as two separate passes (run_encode, run_decode) so each can be
 * timed and profiled on its own.
 */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "opus_custom.h"

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &ts);
    return ts.tv_sec + 1e-9 * ts.tv_nsec;
}

__attribute__((noinline))
int run_encode(OpusCustomEncoder *enc, const opus_int32 *pcm, int frames, int frame_size,
               int channels, int bytes, unsigned char *packets) {
    int i;
    for (i = 0; i < frames; i++) {
        int len = opus_custom_encode24(enc, pcm + (size_t)i * frame_size * channels, frame_size,
                                       packets + (size_t)i * bytes, bytes);
        if (len != bytes) {
            fprintf(stderr, "encode frame %d returned %d (expected %d)\n", i, len, bytes);
            return -1;
        }
    }
    return 0;
}

__attribute__((noinline))
int run_decode(OpusCustomDecoder *dec, const unsigned char *packets, int frames, int frame_size,
               int channels, int bytes, opus_int32 *out) {
    int i;
    for (i = 0; i < frames; i++) {
        int ret = opus_custom_decode24(dec, packets + (size_t)i * bytes, bytes,
                                       out + (size_t)i * frame_size * channels, frame_size);
        if (ret != frame_size) {
            fprintf(stderr, "decode frame %d returned %d\n", i, ret);
            return -1;
        }
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 8) {
        fprintf(stderr, "Usage: %s <rate> <channels> <frame_size> <bytes_per_packet> <complexity> "
                        "<in.s32> <out.s32>\n", argv[0]);
        return 2;
    }
    int rate = atoi(argv[1]), channels = atoi(argv[2]), frame_size = atoi(argv[3]);
    int bytes = atoi(argv[4]), complexity = atoi(argv[5]);
    int err = 0;

    OpusCustomMode *mode = opus_custom_mode_create(rate, frame_size, &err);
    if (!mode || err != OPUS_OK) {
        fprintf(stderr, "mode_create(%d, %d) failed: %s\n", rate, frame_size, opus_strerror(err));
        return 1;
    }
    OpusCustomEncoder *enc = opus_custom_encoder_create(mode, channels, &err);
    if (err != OPUS_OK) { fprintf(stderr, "encoder_create failed: %s\n", opus_strerror(err)); return 1; }
    OpusCustomDecoder *dec = opus_custom_decoder_create(mode, channels, &err);
    if (err != OPUS_OK) { fprintf(stderr, "decoder_create failed: %s\n", opus_strerror(err)); return 1; }

    if (opus_custom_encoder_ctl(enc, OPUS_SET_COMPLEXITY(complexity)) != OPUS_OK) {
        fprintf(stderr, "set complexity failed\n");
        return 1;
    }
    if (opus_custom_encoder_ctl(enc, OPUS_SET_VBR(0)) != OPUS_OK) {
        fprintf(stderr, "set CBR failed\n");
        return 1;
    }
    if (opus_custom_encoder_ctl(enc, OPUS_SET_LSB_DEPTH(24)) != OPUS_OK) {
        fprintf(stderr, "set lsb depth failed\n");
        return 1;
    }

    opus_int32 lookahead = -1;
    opus_custom_decoder_ctl(dec, OPUS_GET_LOOKAHEAD(&lookahead));

    FILE *fin = fopen(argv[6], "rb");
    if (!fin) { perror("input"); return 1; }
    fseek(fin, 0, SEEK_END);
    long size = ftell(fin);
    fseek(fin, 0, SEEK_SET);
    int frames = (int)(size / (4L * channels * frame_size));
    size_t samples = (size_t)frames * frame_size * channels;
    opus_int32 *pcm = malloc(samples * 4);
    opus_int32 *out = calloc(samples, 4);
    unsigned char *packets = malloc((size_t)frames * bytes);
    if (fread(pcm, 4, samples, fin) != samples) { fprintf(stderr, "short read\n"); return 1; }
    fclose(fin);

    double t0 = now();
    if (run_encode(enc, pcm, frames, frame_size, channels, bytes, packets)) return 1;
    double t1 = now();
    if (run_decode(dec, packets, frames, frame_size, channels, bytes, out)) return 1;
    double t2 = now();

    FILE *fout = fopen(argv[7], "wb");
    if (!fout) { perror("output"); return 1; }
    fwrite(out, 4, samples, fout);
    fclose(fout);

    double seconds = (double)frames * frame_size / rate;
    printf("rate=%d ch=%d frame=%d (%.3f ms) bytes=%d (%.1f kbit/s) complexity=%d lookahead=%d (%.3f ms) "
           "frames=%d audio=%.2fs enc=%.4fs dec=%.4fs enc_us_per_frame=%.2f dec_us_per_frame=%.2f\n",
           rate, channels, frame_size, 1000.0 * frame_size / rate, bytes,
           bytes * 8.0 * rate / frame_size / 1000.0, complexity, (int)lookahead,
           1000.0 * lookahead / rate, frames, seconds, t1 - t0, t2 - t1,
           1e6 * (t1 - t0) / frames, 1e6 * (t2 - t1) / frames);

    opus_custom_encoder_destroy(enc);
    opus_custom_decoder_destroy(dec);
    opus_custom_mode_destroy(mode);
    free(pcm); free(out); free(packets);
    return 0;
}
