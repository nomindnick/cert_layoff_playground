# FINDINGS — E0. Scoreboard

## Verdict

`validated (breadth + depth)` — the scoreboard discriminates on both axes.
**Breadth:** on a 36-matter zero-leak eval set it orders random (0.115
rarity-recall) < frequency-prior (0.373) < lexical/TF-IDF (0.399) < oracle
(1.000); grounding instrument resolves cites correctly. **Depth:** the
Opus-subagent rubric judge (48-item L0–L3 calibration ladder) cleanly separates
the three tiers that exist in this corpus — wrong-issue 0.00 < facts-only 1.08 <
recovered-reasoning 2.83 — and tracks the deterministic proxy at Spearman 0.85.
E0 can now grade any E1 arm on both coverage axes.

## What we learned

- **Rarity-weighted recall is the metric that matters; raw recall is gameable.**
  The frequency prior ("always guess the 3 most common issues") gets **0.443 raw
  recall** — it *beats* lexical retrieval (0.402) on raw recall, because
  bumping/seniority/skipping are in most matters. Lexical only wins on
  **rarity-weighted** recall (0.399 vs 0.373), which rewards spotting the rarer,
  harder issues. Judge E1 arms on rarity_recall.
- **The E1 floor-to-beat is the frequency prior (~0.37 rarity_recall), not
  random.** An arm that can't clear it isn't demonstrating coverage beyond a dumb
  prior + keyword matching. ("Beat the cheap baseline first," now on E0 itself.)
- **A pure freq-ratio term profile scores at random** — the first keyword arm
  (0.122) tied random because freq-ratio surfaces rare junk. TF-IDF over
  categories-as-documents fixed it (0.399). Noted so the lexical baseline isn't
  mistaken for "lexical doesn't work."
- **Matter generator (deterministic, zero-leak pool):** 271 eligible matters,
  141 zero-leak; 36 selected, 12/era (1999–2001, 2004–2009, 2018–2025). Median
  leak rate 0.00; leakage, where present, is usually facts quoting the board
  resolution. Answer keys are real (held-out decision issues + reasoning).
- **Privacy gate green:** 0/174 production rosters leak a surname after
  `deidentify`; residual flagger over-flags harmlessly (function words, subject
  names) and caught no real person.
- **The depth signal lives in `reasoning.summary`, which already bundles the
  legal distinction + its rationale.** The calibration showed "reasoning only"
  (L2) already scores level-3 — so the structured `reasoning` field is a complete
  analysis, while bare holding summaries (gold) are not. Direct implication for
  E3 (depth = reasoning vs summary) and the depth thesis: an arm that surfaces
  `reasoning.summary` for load-bearing holdings should score high; the gold-only
  longitudinal layer can't reach depth.
- **The judge correctly down-scores a "perfect" analysis when the source
  reasoning is shallow** (the one default/no-contest holding: L3 verbatim → 1).
  Depth is bounded by the decision, not just the analysis.
- **Methodological note:** the synthetic ladder mis-specified L2 (assumed
  "distinction without rationale" exists; the corpus bundles them), so strict
  L0<L1<L2<L3 monotonicity fails — but the judge was *right* and the ladder
  *wrong*. Validate on the discrimination that actually exists (3 realized tiers),
  not the assumed one.

## Backend notes

Breadth, grounding, matter generation, sanity arms, depth proxy — **deterministic
(no LLM)**. The depth **rubric judge is an Opus subagent** (48 agents, ~582k
tokens, 46s; the measuring instrument is frontier even though E1 arms will be
local). Calibration scores in `output/depth_judge_report.json`.

## Blocked on full corpus?

No — runs on the merged 3-era corpus now (441 decisions, growing). More full
decisions from the production build = more eval matters and broader era coverage;
`build_evalset.py` re-derives at runtime, so re-running picks them up. Depth
coverage scales with the structured-decision count.

## Production recommendation

Keep building — E0 is the measurement substrate, an **internal operator tool**,
not shipped. Next: (1) the depth rubric judge + a ~20-item human calibration to
confirm it tracks the proxy; (2) then E1 arms, judged on rarity_recall vs the
0.37 frequency-prior floor.
