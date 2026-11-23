<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# AI Orchestration: The Orchestrate-Only Development Model

Kaplos is written under an orchestrate-only model. One human operator ratifies
every decision and writes no production code. A general-purpose language model
reads the pinned tree, produces analysis, and authors byte-exact instruction
files and patches prepared outside the tree. A separate coding agent applies
them, runs the gates and the measurements, and commits. Nothing else touches
the repository.

This document explains that model and records why each of its rules exists.
The rules themselves live where they are obeyed: `AGENTS.md` holds the
executor imperatives, `AI-WORKFLOW.md` holds the loop imperatives and the
placement rule that decides which file a new rule enters. Nothing here is a
rule. If a sentence in this file reads like an instruction, the instruction is
stated elsewhere and this file is explaining it.

## The orchestrate-only model

Three roles, one direction of authority. Analysis flows up to the operator for
ratification; instructions flow down to the agent for execution. Neither model
decides scope, and the two models never talk to each other -- the ratifying
commit is the only channel between them.

The strict separation is not an efficiency measure. It exists because the two
failure modes of a general-purpose model are opposite in character, and each
role's constraints suppress one of them:

- An **author** with a toolchain starts running things, then reports the
  results of a run it half-understood as if they were reasoning. Removing the
  toolchain forces the author to state what it believes and why, in a form the
  executor's gates can falsify.
- An **executor** with design latitude starts improving. It retunes a constant
  it was not asked to touch, adds a helper before confirming the need, deletes
  a mode it should have fixed. Removing the latitude -- a byte-exact
  before-snippet, an out-of-scope list, a stop-and-report gate -- turns "the
  tree drifted" from a silent corruption into a caught error.

The operator is the only role that can hold both, and holds neither: the
operator ratifies and does not write.

## Role economics: state access and cost, not capability

The two model roles are frequently the same model class. The axis that
separates them is not how capable they are; it is **what state they can reach
and what a mistake costs there**.

The author reaches a pinned, read-only tree and its own context. Its mistakes
are cheap and legible: a wrong before-snippet fails to match and the run stops.
Its expensive failure is invisible -- a confident claim about something it
could not observe. So the author's discipline is epistemic: separate the static
question (readable from source) from the dynamic one (needs the toolchain), and
never present a guess about the second as a measurement.

The executor reaches a writable tree, the toolchain, the measurement harness,
and the commit. Its mistakes are expensive and, unchecked, silent. So the
executor's discipline is procedural: apply exactly what was written, run the
full gate, and report -- including what it noticed and declined to do.

Capability parity across the two roles is what makes the split informative
rather than merely bureaucratic. When the same model class produces different
results in the two harnesses, the difference is attributable to state access
and cost, not to intelligence.

## Why the instruction file is a contract

Work reaches the coding agent as a numbered instruction file with exact
before/after snippets or a named patch series, not as a conversational
request. The agent handles "replace this exact text with that exact text" far
more reliably than "make this kind of change." Pinning the before-snippets to
a named commit hash turns a codec's own discipline -- bit-exact agreement
between encoder and decoder -- inward onto the process: a snippet that does
not match triggers a stop-and-report instead of an improvised edit.

Two corollaries follow.

First, a before-snippet must come from the pinned tree, not from a working copy
or an upload that predates the pin. A snippet that differs only in whitespace
fails to match for a reason unrelated to drift, and noise of that kind trains
the agent to read stop-and-report as a false alarm -- precisely the reflex the
mechanism depends on not having.

Second, an acceptance check must be scoped to what was *removed*, not to a
token. When a deleted path and a retained path share a term, a blanket "this
grep returns nothing" cannot pass without cutting code meant to stay. A
criterion satisfiable only by damaging retained code is a defect in the
criterion, and the agent is instructed to say so rather than satisfy it.

Instruction files are ephemeral working papers. They move one change from
analysis to execution and are discarded once it lands; their numbering carries
no meaning. This is the exact opposite of a ratified decision -- permanent,
strictly numbered, never rewritten -- and the contrast is deliberate: the
durable record is the decision, never the mechanics of applying it.

**The execution profile** rides in the same file: model class, reasoning depth,
one line of why, chosen by risk rather than size. It is advisory to the
operator's launch choice and never modifies the contract. Its value is that an
under-profiled session grinding against its gates is visible and named at the
moment it happens, instead of being diagnosed afterward from a wreck.

## Grounding: predict-and-gate, or delegate the measurement

The author has no build, test, or measurement toolchain. That absence is a
design choice, not a limitation to be routed around: narrowing what the author
can do narrows what an over-eager author can quietly get wrong.

It also forces every load-bearing dynamic question onto one of two named paths.
When a careful reader can determine the outcome from the pinned source, the
instruction **predicts and gates**: it states the expected outcome and makes
the agent's own test or measurement the proof, so a deviation stops the run
instead of shipping. When the outcome cannot be read from the source -- a
bit rate, a quality figure, a cycle count -- the measurement is **delegated**:
the agent runs the operation in a throwaway worktree, reports the result,
commits nothing, and the byte-exact steps that depend on the value are authored
only afterward.

The discriminator is whether the byte-exact *content* depends on the measured
value, or only the *gating* does. Confidence is explicitly not the test. A
guess dressed as a prediction still ships unverified, and an instruction
resting on a measurement its author could not take is either a fabrication or
an unverified guess. Both are worse than a named hand-off.

## The metric is not the listening test

A codec project produces numbers that look like facts: a noise-to-mask ratio,
a signal-to-noise ratio, a bit rate, a lossless share. The NMR heuristic in
`harness/` ranks codecs on one signal; it does not predict audibility, and a
summary statistic over frames can hide exactly the event a listener hears.

The prototype stage showed both halves of this. A rate-control defect let a
few packets at the attacks of a single test item fall back to a step size more
than a thousand times too coarse. The 95th-percentile figure for that item
stayed perfect, because the defective packets were far fewer than five percent
of the frames. The worst frame stood 47 dB above the masking threshold, but
that maximum was read as an inherent limit of attacks rather than as a defect;
the operator's blind listening test identified it as audible clicks, and
tracing the encoder's rate-control decisions for those packets found the
cause. The retrospective of that stage lives in `docs/retrospectives/`.

Two consequences shape the rules. Acceptance of an invariant observes every
packet of every signal, never a percentile -- a percentile is a gate narrower
than the goal (M1 below). And a quality figure is a measurement with a named
source, never a number the author reasons out, because a metric an encoder was
tuned against cannot also certify the result: the operator's blind listening
test decides.

## The follow-up channel

Anti-initiative is the executor's cardinal discipline, and without an exit it
is lossy. An instruction says: report a correct-but-out-of-scope improvement as
a follow-up candidate, never implement it in passing. The executor complies.
If the candidates go only into a completion report, the report goes into a
transcript, and the transcript is compacted, nothing remembers them.

The fix is structural on both ends. The executor's completion report ends
with two mandatory sections, **Observations** and **Follow-up candidates**, and
a missing section is a gate failure. The author's side answers with sibling
closure: an instruction that changes one member of a family -- one rate point,
one stereo mode, one header field -- enumerates every sibling, each either in
scope or named as a deferral carrying the roadmap item id that owns it.

## The blame reflex

A failing gate provokes a trained reflex: ask whether this change was at fault,
and stop at the first plausible external cause. The environment. A prior
commit. An unexpected file. Each of those is a verdict about responsibility,
and none of them is a diagnosis. The defect stays in the tree.

The countermeasure states that blame is irrelevant and worth zero reasoning,
names the three forbidden stopping points explicitly, and fixes the diagnostic
order: re-read the spec, then the existing code, then your own change. The
order matters because it grounds the diagnosis in declared intent and the
existing contract before it reaches the edit that is easiest to suspect.

The rule that no gate may be shrunk to make it pass -- no test selector, no
skip, no loosened tolerance -- belongs to the same reflex. A gate that is green
because its scope was cut has been disabled, not passed, and the disabling is
almost always reported as a success.

## The ritual window

Both sides of the loop share one failure: inspecting a file through an
arbitrary line window -- `sed -n 'A,Bp'`, `head`, `tail` -- as the way to find
out what the file contains, rather than to read a region already located.

The window is a guess about where the answer lives, committed before the
answer's location is known. When the guess is wrong, the output does not
announce its incompleteness: a truncated slice of a list looks exactly like a
complete list, so a wrong window becomes a confident "it is not there." On a
small file the window saves no meaningful context and buys an unbounded,
invisible correctness risk. A whole-file search costs the same and cannot be
wrong in that way.

## Planning state and the compaction cost

Planning that lives only in a transcript, a handover, or an upload is not
tracked. It is one compaction away from loss: a long session's summary blurs
which steps landed and which are open, and the next session has to reconstruct
that state from a transcript.

Planning state therefore lives in exactly one place, the checked-in `roadmap/`
item store: one markdown file per item, diffable, reviewable, queryable from
the tree. The store holds only drift-invariant state -- a goal, an acceptance
intent, links. Byte-exact snippets and gate commands are deliberately
excluded, because a stored item carrying a stale snippet is worse than no item:
it trains a false-alarm stop-and-report the first time the tree moves.

Retrospectives and handovers may summarize and point at items by id, but they
do not own the tracking. When one of them starts enumerating open work under
its own labels, that is the signal of a missing or stale item.

## Transient vocabulary in durable code

The planning store, the instruction files, and the chat transcript are
scaffolding: they produce a ratified change and fall away. The code that lands
is durable and has to stand alone -- in this project more than most, because
the repository itself is a publication.

So a comment authored inside this loop must not reach back into the
scaffolding: no roadmap item id, no arc name, no instruction reference, no
historical narrative, no chat-only category. The trap is structural rather than
careless -- the author who has the context is exactly the one who cannot tell
that the comment is unmoored. The discipline therefore lives in the
instruction's acceptance criteria, where a grep can enforce it, and not in the
executor's judgement. The one durable cross-reference a comment may carry is a
decision number.

## The mechanism taxonomy

Defects are not uniform debt. Each way of executing a change leaves a
characteristic residue, and the residue is more informative than the count.
Every defect gets a mechanism label; the primary output of a retrospective is
the mechanism fix -- a gate, a channel, an owner -- with the code fix
secondary.

- **M1 gate narrower than goal.** The goal states an invariant over all
  packets or all signals; the gate observes a sample, a percentile, or one
  syntactic position.
- **M2 anti-initiative without a follow-up channel.** Scope discipline works
  as designed and leaves half-finished seams, because the mandated follow-up
  candidates never became items.
- **M3 deferral without an owner.** Skipped cases, known-failing signals and
  accepted-until-revisited notes with no item id attached.
- **M4 fresh code regresses where no gate observes.** New code whose behavior
  no test or measurement covers.
- **M5 toolchain limitation mislabeled as debt.** A tool limitation is worked
  around at every call site instead of at its source, and the workaround is
  filed as debt.
- **M6 never-scoped area.** Files outside every change's scope simply keep
  their old shape.

M1 is answered by the invariant-observation clause, M2 by the follow-up channel
and sibling closure, M3 by the deferral-owner clause, M5 by fixing the cause at
the tool. M4 and M6 are answered by standing gates rather than by authoring
rules.

## The diff is the product

An audit run twice on the same pinned tree -- once through the analysis lane
(read-only, single context) and once through the executor lane (full
toolchain, measurements) -- produces two reports whose overlap is the boring
part. The information is in the single-side and disputed sets: findings one
harness could see and the other structurally could not, and findings the two
lanes disagree about. Treated as the product, that difference is what yields
mechanism labels; neither report contains them.

Full dual runs are expensive and are reserved for invariants over the whole
codec and for high-stakes analyses, such as the figures a publication rests
on.

## Origin and evidence base

The model and its rules were adopted from the strike project by the same
author (`https://github.com/istr/strike`), where each rule was learned from a
dated failure recorded in that project's retrospectives. They are restated and
adapted here so that this repository stands on its own.

- `docs/retrospectives/` -- this project's dated retrospectives, one per
  change set, audit, or incident.
- `docs/AI-REVIEW-AND-RETROSPECTIVES.md` -- the review-time practices that
  produce those documents.
- `AI-WORKFLOW.md` -- the loop imperatives, and the placement rule that decides
  whether a new lesson becomes a rule there, a rule in `AGENTS.md`, or a
  section here.
- `AGENTS.md` -- the executor imperatives, including the completion report.
- `docs/DECISIONS.md` -- the ratified decisions.
- `roadmap/` -- the item store; open work identified by any retrospective is
  written there and referenced by id.
