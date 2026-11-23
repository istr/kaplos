<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Kaplos

Kaplos ("capped lossless") is an audio codec for fixed-size 1 ms packets: 48 samples per channel
at 48 kHz, every packet exactly the configured size, no algorithmic delay beyond collecting the
packet, and lossless whenever the packet budget allows. Its target is microcontroller-class
hardware.

This repository holds the reference implementation in Python (numpy and numba), the measurement
harness, and the experiments behind every published figure. The docstring of `kaplos/codec.py`
summarizes the predictor, the quantiser, the noise feedback, the Rice coding and the packet
layout.

## Layout

- `kaplos/` -- the codec: predictor, quantiser, Rice coding, packet encoder and decoder,
  encoder-only noise shaping, the command-line tool.
- `harness/` -- the NMR heuristic, the synthetic test signals, the baseline codecs, and the Opus
  Custom helper program.
- `experiments/` -- one script per experiment stage; each prints the table it measures.
- `tests/` -- the unit tests.
- `docs/` -- the ratified decisions and the review practices.
- `roadmap/` and `.claude/skills/roadmap-items/` -- the planning store and the skill that manages
  it.
- `.devcontainer/` -- the pinned dev container that runs every gate and measurement.
- `LICENSES/` -- the licence texts besides `LICENSE`.

Generated signals, decoded audio and measurement output go to `out/`, which is never committed.

## Usage

The dev container provides Python 3.13 with numpy, numba and soundfile, ffmpeg, and libopus 1.6.1
with custom modes. Run every command from the repository root. The first run compiles the numba
kernels.

The tests:

```sh
python3 -m unittest discover -s tests -v
```

The command line takes a 48 kHz stereo WAV file and writes the decoded WAV file, sample-aligned
with the input for blind listening tests. The rate is in kbit/s and a multiple of 8; `--kbps 0`
codes lossless at a variable rate.

```sh
python3 -m kaplos in.wav out.wav --kbps 384 --stats
```

The measurements: generate the test signals, build the Opus Custom helper, then run the baselines
and the experiments.

```sh
python3 -m harness.gen_signals out/sig
gcc -O2 -I/usr/local/include/opus -o out/occ harness/occ.c /usr/local/lib/libopus.a -lm
python3 -m harness.baselines
python3 -m experiments.s1_lossless
python3 -m experiments.s2_rate 384 576 768
python3 -m experiments.s3_shape 384
python3 -m experiments.s3_lpc 384
python3 -m experiments.final_table 384 576 768
```

## Licences

- Code: BSD-2-Clause-Patent (`LICENSE`).
- Text and documentation: CC BY 4.0 (`LICENSES/CC-BY-4.0.txt`).
- Synthetic test signals: CC0 1.0 (`LICENSES/CC0-1.0.txt`).

Every source file names its licence in an SPDX header. The repository contains no third-party
audio.

## AI assistance

Kaplos is developed with AI assistance. `AI-WORKFLOW.md`, `AGENTS.md` and `AI-ORCHESTRATION.md`
describe the workflow.

Author: Ingo Struck, ORCID iD 0009-0006-9579-1301.
