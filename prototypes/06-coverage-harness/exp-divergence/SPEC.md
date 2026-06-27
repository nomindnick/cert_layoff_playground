# SPEC — E2. Context-divergence as a coverage mechanism *(stub — promote after E1)*

> Read `../SPEC.md`. This isolates the mechanism arm D bundles. Full build-detail
> to be written once E1 shows D is worth dissecting. `local-LLM-heavy`.

## Hypothesis

Grounding an adversarial pass in a **different region of the corpus** than the
researcher manufactures non-correlation via *evidence placement* (cheaper and more
steerable than model-weight diversity), and its payoff shows up as **coverage**
(recovered issues/holdings), not merely "more attacks."

## Approach (sketch)

Hold the researcher fixed (E1's best arm). Vary the adversary's grounding:
- **near-miss tail** — holdings ranked just below the primary retrieval cutoff
  (the adversary as a *coverage-recovery probe*: "what did retrieval miss?");
- **random tail** — irrelevant holdings (noise control: expect non-sequitur attacks);
- **adjacent-doctrine** — ground on a *different* issue (competency → attack a
  skipping conclusion) to surface **cross-issue interactions**.
Every adversarial addition must cite a resolvable holding (grounded triage).
**Metric:** marginal issue/holding-recall lift on E0 over a same-grounding
adversary; near-miss and adjacent-doctrine should beat random-tail and beat
same-grounding.

## Falsified if

Divergent grounding adds no recall over a same-grounded adversary (the slice
doesn't matter), or random-tail does as well as near-miss (it's just "more
attacks," not coverage). Compute backend named per result.
