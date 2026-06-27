# SPEC — E5. Judge-loop with split metrics *(stub — promote after E1)*

> Read `../SPEC.md`. Tests iterative refine-until-threshold against the W11 lesson
> that orchestration buys coverage, not correctness. `local-LLM-heavy`.

## Hypothesis

An LLM-judge refinement loop lifts **coverage/polish** but **plateaus on the
objective sub-metric** (E0 recall + grounding). The holistic rubric score climbs
while recall/grounding flattens — so the loop buys breadth and presentation, not
correctness — and an author==judge loop on one local model can reward-hack to
"looks good to me" without converging on what matters.

## Approach (sketch)

Wrap E1's best arm in a loop: synthesize → judge (rubric: untested assumptions,
unaddressed counter-authority, missing issues) → if below threshold, fan out to
address → repeat. **Split the score:** track the **objective** metric
(E0 issue-recall + cite-resolution) *separately* from the **holistic** rubric.
Plot both vs iteration. Cap iterations; require monotone improvement on the
objective metric or stop (anti-reward-hacking, anti-non-termination). Compare
same-model judge vs a different-family judge (non-correlation).

## Falsified if

The objective metric climbs with iterations alongside the holistic one (the loop
*does* buy correctness — then it's worth the wall-clock), or the loop fails to
terminate / oscillates (judge instability). Either way, report iterations-to-plateau
and wall-clock. Backend named per result.
