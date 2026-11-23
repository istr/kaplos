<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# AI Review and Retrospective Practices

This document holds the review-time practices of the Kaplos AI workflow: the
neutral context-free checkpoint, the post-change-set retrospective, and the
snapshot-hygiene discipline both depend on. They are kept out of
`AI-WORKFLOW.md` so that file stays the lean authoring contract; these are
consulted when a review or retrospective is commissioned, not at every
instruction-authoring anchor.

## Neutral checkpoints

Periodically commission a review from a fresh, context-free model session
that has only the repository snapshot and the stated decisions -- no project
memory, no prior framing, no investment in earlier choices.

A context-free reviewer is valuable precisely because it has not internalized
what the working sessions "meant". The gaps it catches are the
aspirational-vs-as-built kind that context-rich sessions normalize: a packet
format the documentation describes but the code does not emit, a decision that
still claims a stage the code has moved past, a figure in the README that no
committed table produces. A session that knows the intent reads past these; a
session that knows only the artifact does not.

The neutral review is a checklist to verify, not a verdict to apply. It should
disclaim its own authority -- a single read of a snapshot can be wrong about
the working tree -- and every finding is validated against the live tree
before any instruction is written. It produces candidates for confirmation,
not commands.

Before a publication (D4), the neutral review is mandatory: a context-free
session checks the disclosure text against the tagged tree -- every described
mechanism present in the code, every figure traceable to a committed table,
nothing confidential, no third-party audio.

## Retrospectives with the model

After a change set lands, run a structured retrospective: have a model re-read
the change set against the instruction or decision that motivated it and
report what is resolved, what remains, and what patterns emerged. Each
retrospective is a dated file in `docs/retrospectives/`, and each defect it
records carries a mechanism label from `AI-ORCHESTRATION.md`.

The value is threefold. It converts scattered history into an explicit,
checkable status ("of N findings, these are verified fixed, these are deferred,
this one is open"). It verifies fixes against the actual tree rather than
against the intent of the instructions that produced them. And it distills the
working method itself into reusable form.

A retrospective also surfaces residue that no single change owned: an option
that survived only in an experiment script, or a track that was deliberately
deferred and should be stated as deferred rather than left implicit. Open work
it finds is written into the roadmap store and referenced by id.

## Snapshot hygiene

A review is only as good as the snapshot it reads. The snapshot must contain
everything the review reasons about, and exclusions must be surgical: exclude
scratch output by path (`out/`), never all files of a type by glob, or the
documentation the review is meant to check disappears with the noise.

The same completeness applies to the searches run against the snapshot. Scope
a blast-radius search to the whole repository -- `kaplos/`, `harness/`,
`experiments/` and `tests/` alike -- because experiments and tests call the
codec exactly as a user does, and a change that searched only `kaplos/` misses
them.

## See also

- `AI-WORKFLOW.md` -- the core human-AI loop and the authoring contract.
- `AI-ORCHESTRATION.md` -- the model behind the loop and the mechanism labels.
- `docs/DECISIONS.md` -- the ratified decisions a review checks against.
