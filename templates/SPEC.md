# SPEC — {NN. Prototype name}

> Written so a fresh Claude Code session told only "Prototype {NN}, go build
> it" can implement this unattended. If a section would make that session
> stop and ask a question, the section isn't done.

## Hypothesis

What we believe and are trying to validate or falsify. One or two sentences,
falsifiable. (The builder needs to know what *falsified* looks like, not just
what *done* looks like.)

## Why it matters

One paragraph: which capability-ladder rung this serves, who'd use it, what
decision its outcome informs.

## Data inputs

Exactly which corpuslib accessors / fields this consumes. Note known data
limitations that bound the result (e.g., only 2 extracted years; gold
holdings are editorial, not exhaustive).

## Compute profile

`none / embeddings / local-LLM-light / local-LLM-heavy`. Name the intended
models. State the GPU-busy fallback: can the LLM steps run as subagent
fan-out (code writes batch inputs, main session spawns Agent subagents,
code merges — never `claude -p` from code), and what would that result mean
(idea validation only vs full validation)?

## Approach

Concrete enough to start coding: stages, key design decisions already made,
algorithms/prompts sketched. Flag the genuinely uncertain parts as
experiments-within-the-experiment.

## Deliverables

The artifacts that must exist when done (scripts, outputs, a demo, FINDINGS).

## Success criteria

How we'll judge validated vs falsified. Quantitative where possible; "Nick
eyeballs N samples" is acceptable where it's honest.

## Out of scope

What this prototype deliberately does NOT do, so an unattended session
doesn't gold-plate.

## Privacy notes

What this prototype renders/outputs and how de-identification is enforced
(District (ALJ) cites only in anything committed or screenshotted).
