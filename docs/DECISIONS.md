<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Ratified decisions

Each decision is proposed by the analysis lane and ratified by the operator
before any instruction that depends on it is written (`AI-WORKFLOW.md`). The
list is permanent and append-only: a decision is never rewritten or
renumbered. A later decision supersedes an earlier one by naming it, and the
earlier entry is annotated with a pointer to its successor.

## D1 -- Name

Ratified 2026-11-23.

The codec is named Kaplos ("capped lossless"). The repository is
`https://github.com/istr/kaplos`.

## D2 -- Licences

Ratified 2026-11-23; the first commit added `LICENSE`.

- Code: BSD-2-Clause-Patent (`LICENSE`).
- Text and documentation: CC BY 4.0 (`LICENSES/CC-BY-4.0.txt`).
- Synthetic test signals: CC0 1.0 (`LICENSES/CC0-1.0.txt`).

## D3 -- No third-party audio

Ratified 2026-11-23.

The repository contains no third-party audio: no excerpt of a commercial
recording or test CD, and no file encoded from one.

## D4 -- Publication channels and order

Ratified 2026-11-23.

The work is published as a defensive publication (prior art).

1. Tag `v0.1.0` of the repository (stages S0 to S3) and archive it on Zenodo.
   The Zenodo DOI and its timestamp are the first dated public disclosure.
2. The same day, a technical disclosure of the Kaplos codec on Technical
   Disclosure Commons, citing the DOI.
3. A separate Technical Disclosure Commons entry describes the system concept
   (a two-device wireless duplex audio system for video conferencing), with no
   product name and no repository.
4. An arXiv preprint, primary category eess.AS, once endorsed.
5. Later stages (S4, S5) appear as new arXiv versions, new Zenodo versions and
   new Technical Disclosure Commons entries. Published Technical Disclosure
   Commons entries are never edited.
6. Research Disclosure is not used for now; it is revisited only if a concrete
   threat appears.
7. Content rules: enabling detail including the variants; no material
   received under a non-disclosure agreement and no third-party audio (D3);
   text under CC BY 4.0 (D2); AI assistance acknowledged in every disclosure;
   author Ingo Struck with ORCID iD 0009-0006-9579-1301.

## D5 -- Repository layout

Ratified 2026-11-23.

- Root: `LICENSE`, `README.md`, `AGENTS.md`, `AI-WORKFLOW.md`,
  `AI-ORCHESTRATION.md`.
- `docs/`: `DECISIONS.md`, `AI-REVIEW-AND-RETROSPECTIVES.md`,
  `retrospectives/`.
- `LICENSES/`: `CC-BY-4.0.txt`, `CC0-1.0.txt`.
- `roadmap/` and `.claude/skills/roadmap-items/`: the planning store and the
  skill that manages it.
- `kaplos/` (codec), `harness/` (metric, signals, baselines), `experiments/`
  (stage scripts), `tests/` (`unittest`, no new dependency).
- Every source file carries an SPDX header.

## D6 -- Toolchain

Ratified 2026-11-23.

- The executor runs in a dev container defined in `.devcontainer/`. The base
  image and every dependency are pinned by digest or hash.
- Python 3.13 with numpy, numba and soundfile.
- ffmpeg from Debian, and libopus 1.6.1 with custom modes built from a pinned
  tag, both only for the baseline comparisons.
- Digests and hashes are delegated measurements: the Containerfile is authored
  only after the executor has reported them.

## D7 -- Results tables

Ratified 2026-11-23.

- The results tables live in `docs/RESULTS.md`, a Markdown file under
  `docs/`. D5 stays unchanged.
