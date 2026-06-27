# SPEC — E4. Local steering / in-context conditioning *(stub — promote after E1)*

> Read `../SPEC.md`. Tests "steer the model > pick a bigger model," and the bias
> cost of conditioning. `local-LLM-heavy`.

## Hypothesis

In-context conditioning ("immediate fine-tuning") raises a local per-issue agent's
**depth** toward frontier quality — but **biases it toward the dominant pattern
and suppresses novel-issue recall**, so it must be paired with a divergence
counterpart (E2). Steering (role + evidence placement) buys more than swapping
model size; model-family **heterogeneity** adds error-catching only where blind
spots are genuinely uncorrelated.

## Approach (sketch)

Levers over E1's best arm: (a) **background-issue packs** — a dense corpus-derived
"treatise chapter" per issue, injected to condition the agent; (b) **multi-shot
grounding** — strategic in-context holding examples. Measure E0 **depth** (should
rise) *and* **novel-issue recall** (should fall — quantify the bias). Secondary:
homogeneous vs heterogeneous (gemma/qwen/gpt-oss) panel on the same task — does
architecture diversity catch issues a single steered model misses?

## Falsified if

Conditioning raises depth without a measurable novelty cost (great — no tradeoff,
just use it), **or** it raises nothing over a well-prompted unconditioned agent
(steering ≠ fine-tuning here). Heterogeneity falsified if a homogeneous panel
matches it. Backend + exact models named per result.
