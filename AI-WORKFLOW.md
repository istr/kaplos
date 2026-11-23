<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Working With AI: Collaboration Practices

Kaplos is built in an AI-heavy workflow: an operator works with a
general-purpose language model to do analysis and author instruction files;
a separate coding agent executes those instructions against the repository.
This file is the *imperative* half of that loop -- the rules the operator and
the analysis model obey at every anchor. Its neighbors: `AGENTS.md` gives
imperative rules to the *coding agent*, `docs/DECISIONS.md` records the
ratified decisions, and `AI-ORCHESTRATION.md` explains the orchestrate-only
model these rules implement and records where each one came from.

## Where a rule lives

One placement rule governs the three workflow documents, and is stated only
here:

> If the executor or the author must obey it at every anchor, it lives in
> `AGENTS.md` (executor imperatives) or `AI-WORKFLOW.md` (loop imperatives)
> -- terse, imperative, one line of rationale, stable section anchors. If it
> explains, narrates, generalizes, or records history, it lives in
> `AI-ORCHESTRATION.md`.

Both imperative files are read whole at every anchor, so both stay short. A
rule that grows a backstory sheds the backstory to the concept paper and
keeps a pointer; it does not grow in place.

## Roles in the loop

Three roles, with a strict direction of authority:

- **Operator.** Owns scope and ratified decisions. Approves every bitstream,
  arithmetic, measurement-definition or structural decision before any
  instruction is written. Ratified decisions (the `D`-numbered list in
  `docs/DECISIONS.md`) are permanent: annotated, never silently rewritten.
- **Analysis model.** Reads the repository, produces analysis, authors
  instruction files and patches prepared outside the tree. Proposes
  decisions; does not ratify them. Grounds by reading, not running (below).
  Never writes to the repository.
- **Coding agent.** Executes instruction files and applies patches. Does not
  infer or expand scope, and stops and asks when an instruction does not
  match the tree.

Analysis flows up to the operator for ratification; instructions flow down to
the agent for execution. Neither model decides scope on its own.

Roadmap item *creation* is the analysis model's lane: it runs the
roadmap-items skill outside the tree to write the new `proposed` item and
delivers it as a git-am patch alongside the motivating instruction. Every
other roadmap-store mutation -- a `done` retire, a rank, rescale,
restructure, reorder, or `_order.md` edit -- is the executor's lane,
committed in the run that occasions it. The operator performs the
`proposed -> ratified` flip between the two.

## The analysis model grounds by reading, not by running

The analysis model is deliberately tooling-minimal: git-native read access to
the pinned tree, text search, and the planning script. It has no build, test,
or measurement toolchain, and does not acquire one.

A *static* question is settled by reading the pinned source -- whether a
before-snippet appears exactly once, which bits a header field occupies,
what a function does to an input. The analysis model answers these itself;
they are the substance of grounding.

A *dynamic* question needs the toolchain to run -- whether a predictor change
alters the bits per sample, whether every packet still fits its budget,
whether the gate passes, any quality figure. The analysis model does not run
these, and never presents a guess about one as if it had measured it. Each
load-bearing dynamic question takes exactly one of two paths:

- **Predict and gate** when a careful reader can determine the outcome from
  the pinned source. The instruction states the expected outcome and makes the
  agent's own test or measurement the proof.
- **Delegate the measurement** when the outcome cannot be read from the
  source. The agent runs the operation in a throwaway worktree and reports the
  result; the byte-exact steps that depend on it are authored only afterward.
  The measurement is scratch and is never committed.

The discriminator is whether the byte-exact *content* depends on the measured
value (delegate) or only the *gating* does (predict). Confidence is not the
test. Why: `AI-ORCHESTRATION.md#grounding-predict-and-gate-or-delegate-the-measurement`.

## Quality figures are measurements

Every quality or rate figure -- NMR, SNR, bits per sample, lossless share,
escape share, cycle counts -- that appears in a decision, a roadmap item, the
README or a publication comes from an executor report or a committed results
table, and names its source. The analysis model never states one it did not
receive that way. A heuristic ranks; the operator's blind listening test
decides. Why: `AI-ORCHESTRATION.md#the-metric-is-not-the-listening-test`.

## The instruction file is a contract

Work reaches the coding agent as a numbered instruction file, not a
conversational request. Each file follows the same shape:

- **Goal** -- one paragraph stating the end state.
- **Out of scope / do NOT touch** -- an explicit boundary list.
- **Confirmation gate** -- the decisions that must be ratified first, plus the
  commit hash the before-snippets and patches were taken from.
- **Anti-initiative clause** -- what the agent must not do even if it looks
  helpful.
- **Files and edits** -- exact before/after snippets or a named patch series,
  not deltas or templates.
- **Quality gates** -- the commands that must pass, written so the result is
  checkable rather than asserted.
- **Acceptance criteria** and a **commit message**.
- **Execution profile** -- recommended model class and reasoning depth, with a
  one-line rationale.

Two rules the shape does not state on its own:

- A before-snippet is taken from the pinned tree itself, never from a working
  copy or an upload that predates the pin.
- An acceptance check is scoped to what was *removed*, not to a token. A
  criterion satisfiable only by touching retained code is a defect in the
  criterion -- surfaced by the agent, not satisfied by it.

Instruction files are ephemeral working papers, not tracked history. They move
one change from analysis to execution and are discarded once it lands; their
numbering carries no meaning. Nothing downstream may depend on an instruction
file's name or number. Why:
`AI-ORCHESTRATION.md#why-the-instruction-file-is-a-contract`.

## Authoring clauses every instruction obeys

1. **Acceptance observes the invariant.** When an instruction's goal states an
   invariant -- every packet fits, every decode is bit-exact -- its acceptance
   observes it over every packet of every test signal, never a sample of them
   and never a percentile. A sample certifies the sample; only the full
   observation certifies the invariant.
2. **Sibling closure.** An instruction that changes one member of a family --
   one rate point, one stereo mode, one predictor stage, one header field --
   enumerates every sibling of the same family, each either in scope or named
   as a deferral with its follow-up item id.
3. **Domain before narrowing.** Before an instruction narrows a value's range
   or width -- a header field, a table, a clamp -- the author verifies the full
   domain of values every writer can produce. A value outside the target range
   blocks the change until it is removed or the design is widened by ratified
   decision.
4. **Deferrals carry owners.** Every deferral a gate can see -- a skipped
   case, a known-failing signal, an accepted-until-revisited note -- carries
   the roadmap item id that owns it. A deferral without an owner is a defect of
   the change introducing it.
5. **Gate values are measured, not derived.** Every count an instruction's
   gate asserts is the output of a command, never a number reasoned out from
   reading. A claim that something occurs once or never names the search
   behind it.
6. **Dictated Markdown sits in a fence.** Every block of Markdown an
   instruction dictates -- a before-snippet, an after-snippet, a whole new file
   -- sits inside a fence, with its extraction markers inside the fence too, so
   that the dictated bytes are unambiguous.
7. **Gates run on the dev container's tools.** Every gate command runs as
   written with the tool set D6 defines. An invariant the pre-commit gate
   already checks is gated by that gate, not restated.
8. **A gate on generated output regenerates it first.** Signals, decoded audio
   and tables under `out/` are never trusted across commits: a gate that reads
   them removes `out/` and regenerates what it needs at the commit it checks.

## The execution profile is part of the contract

The analysis model records a recommendation in every instruction file: model
class, reasoning depth (none / brief / deep), and one line of why. The mapping
follows risk, not size. Mechanical work -- byte-exact application,
documentation, patch application behind a green gate -- takes the smallest
capable model and no deep reasoning. Code changes verified by hermetic tests
sit in the middle. The strongest model with deep reasoning is reserved for
work whose acceptance needs measurement interpretation, debugging against
hardware, or changes to the decoder arithmetic.

The profile is advisory to the operator, not a control: gates, before-snippets,
and stop-and-report apply identically under every profile.

## Decisions are ratified before instructions exist

Bitstream, arithmetic, measurement-definition and structural decisions are
resolved with the operator and recorded as `D`-numbered decisions in
`docs/DECISIONS.md` before any instruction that depends on them is authored.
An instruction never carries an unratified decision. The decision is made by
the operator, not discovered by the agent mid-edit.

## Planning state lives in the roadmap item store, never in the chat

The analysis model tracks planning state through exactly one mechanism: the
checked-in `roadmap/` item store -- one markdown file per work item, managed
through the `roadmap-items` skill. There is no second place. The moment a
planning effort needs structure -- arcs, a status flip, a findings checklist,
a landed-vs-open ledger, a cross-arc execution order -- that structure is an
item (or a re-rank, or an `_order.md` edit) in the store, not prose in the
conversation. Planning that lives only in a transcript, a handover, or an
upload is not tracked.

The store holds only drift-invariant state: each item carries a `goal`, an
`acceptance_intent`, and `links`, never byte-exact snippets, file-and-edit
lists, or gate commands -- those are authored ephemerally at execution time
and discarded after they land. An item moves `proposed -> ratified -> done`;
`proposed` is all the analysis model writes, the flip is the operator's call,
and a `done` item moves to `roadmap/completed/`. Handovers and retrospectives
may point at items by id but do not own the tracking. Decisions in
`docs/DECISIONS.md` are the exception: permanent, append-only, outside the
store, never edited through it. Why:
`AI-ORCHESTRATION.md#planning-state-and-the-compaction-cost`.

## Code comments never leak the workflow's transient vocabulary

The planning store, instruction files, and chat transcript are *scaffolding*:
they produce a ratified change and fall away. A comment authored during this
loop must not reach back into the scaffolding -- no roadmap item id or arc
name, no instruction reference, no historical note, no chat-only category.
The discipline lives in the instruction's acceptance criteria, not the
executor's judgement. The one durable cross-reference a comment may carry is a
decision number from `docs/DECISIONS.md`. Why:
`AI-ORCHESTRATION.md#transient-vocabulary-in-durable-code`.

## Anti-initiative is structural, not advisory

General-purpose models bias toward doing more than asked: tuning a constant
silently, adding a helper before confirming the need, deleting a mode instead
of fixing it. The countermeasure is structure, not a reminder: every
instruction carries an explicit out-of-scope list and an anti-initiative
clause, and substantive steps end in stop-and-report gates. In documentation
work: annotate, do not rewrite, because ratified text is permanent.

Anti-initiative without an exit is lossy: the improvement the agent correctly
declined to make must land somewhere. It lands in the mandatory **Follow-up
candidates** section of the completion report (`AGENTS.md`), and the author
turns those candidates into roadmap items. Why:
`AI-ORCHESTRATION.md#the-follow-up-channel`.

## Deviations from the dictated commit message

When the instruction file includes an exact commit message, the executor
appends a **Deviations** paragraph to that dictated body whenever the
completion report's Observations section documents any deviation from the
before-snippets, gate findings, or anti-initiative clauses -- one brief line
per deviation. Git log and the report then carry the same facts.

## Commit attribution names the model, nothing else

Every commit produced with an AI model -- executed from an instruction file,
or prepared as a patch outside the tree -- MUST end with one
`Co-Authored-By:` trailer per model, naming the model
(`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`). It MUST NOT
disclose any other detail of the AI interaction: no session links or ids
(e.g. a `Claude-Session:` trailer), no prompts, transcripts, or tool
metadata. A dictated commit message carries the model trailer only, and the
operator checks a patch's trailers before applying it, because `git am`
keeps every one. Why: the history is public and permanent.

## Cluster by risk, not by finding order

When a review produces many findings, group them by risk before sequencing.
Documentation-only patches bundle into a single change -- they share one
review concern. Substantive changes -- bitstream, decoder arithmetic,
measurement definitions -- stay separate and cautious, one concern per
change.

## Removal is the default resolution

When a finding can be resolved by implementing dead surface or by removing it,
removal is the default. Unused modes, unreferenced options and documented but
unwired capabilities invite someone to rely on a thing that does nothing.

## Review and retrospective practices

The neutral context-free checkpoint, the post-change-set retrospective, and
the snapshot-hygiene discipline they depend on are review-time practices and
live in `docs/AI-REVIEW-AND-RETROSPECTIVES.md`. One lesson is load-bearing at
authoring time and is kept here: scope a blast-radius search to the whole
repository -- `kaplos/`, `harness/`, `experiments/` and `tests/` alike --
because the experiments and tests call the codec exactly as a user does.

## Inspect the whole file, never a ritual window

An existence or absence claim rests on a whole-file search (`grep -n` over the
whole file) or a full read, never on a slice. Both sides of the loop obey this:
a line window (`sed -n 'A,Bp'`, `head`, `tail`) is a guess about where the
answer lives, and a truncated slice looks exactly like a complete one.

A window is legitimate only after a search has located the target, to read
context the search cannot give cleanly -- prefer `grep -n -C3 PATTERN file`.
Why: `AI-ORCHESTRATION.md#the-ritual-window`.
