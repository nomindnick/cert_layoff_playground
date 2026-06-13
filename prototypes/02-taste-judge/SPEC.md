# SPEC — 02. Editorial-taste judge (W7)

> Written so a fresh Claude Code session told only "Prototype 02, go build
> it" can implement this unattended. Read the repo root `CLAUDE.md` and
> `STATUS.md` first. Prototype 01 (search) is validated and its lessons
> apply (arctic-l-v2 embeddings, de-identify before anything leaves the
> pipeline).

## Hypothesis

An LLM judge — especially one given corpus context — can reproduce the human
editors' selection of "noteworthy" holdings measurably better than mechanical
heuristics. Falsified if the judge can't beat the heuristic baseline, or if
neither beats chance (taste isn't recoverable from the holding records).
**A falsification is valuable either way:** "taste = cheap mechanical
features" means P5 ships the cheap version.

## Why it matters

The human volumes included ~260 holdings for 2009; extraction produced 633.
Regenerated volumes (P5) read like a dump without an editorial layer. This is
the rare taste problem WITH gold labels: the lab's eval alignments record
exactly which extracted holdings the human editors catalogued. If selection
is learnable, rung-2 report generation becomes credible; the disagreement
queue is also the partner-facing artifact that builds trust.

## Data inputs

All paths via `corpuslib.corpus_paths()`; alignments live in
`{corpus_root}/eval/alignment_{year}.json`.

**Candidates + labels** from each alignment's `system` list (one entry per
extracted holding: `{case_no, holding_idx, status, matched_gold_idxs,
category}`):

- label **include = 1** if `status` in `("matched", "category_divergent_match")`
- label **include = 0** if `status == "over_recovery"`
- Verified counts: 2009 = 633 candidates, 215 positive (34%); 2004 = 202
  candidates, 80 positive (40%). **2009 is dev** (threshold/prompt tuning),
  **2004 is held-out test** (run once, no tuning).

**Holding content** from the decision records (`corpuslib.load_decisions`),
same fields prototype 01 indexes: issue.statement/category/subtype,
summary_style_holding, ruling, arguments, facts, authorities,
reasoning.summary. **De-identify every holding text at load time** (see
Privacy) so respondent names never enter prompts, judgments, or artifacts.

**Prior-volume context**: `corpuslib.load_gold_holdings()` filtered to
`sort_year < {year}` — what earlier editors catalogued on similar issues
(the "settled vs novel" signal a 2009 editor carried in their head).

**Label honesty (carry into FINDINGS):** the negative class includes
correct-but-uncatalogued holdings the editors might have included had they
seen them (the volumes are editorial). Metrics are therefore a FLOOR on true
precision. The deliverable includes a ~30-item disagreement sample for
Nick's review to estimate how much of the "error" is actually label noise.
Also: pointwise labels conflate "routine" with "duplicative-of-a-selected
holding" — context arm C addresses this; say so when interpreting.

## Compute profile

`local-LLM-heavy` (volume of short calls, not long generations). Primary
judge: **gemma4:31b** (it batches on ollama, `-np 4`; qwen-arch does not —
see STATUS Lessons). ~2,500 total judgments (633 × 3 arms on 2009 + 202 × 1
on 2004 + sample reruns) of a short prompt → feasible in hours if batched
(use a small worker pool, 3–4 concurrent requests). Optional comparison:
qwen3.5:122b on a stratified 100-holding sample to test whether scale
changes taste quality. Check `corpuslib.llm.gpu_status()` before runs.
GPU-busy fallback: judgments are batch-shaped → subagent fan-out per
CLAUDE.md (validates the idea, not local feasibility; record backend).

## Approach

### Stage 0 — graduate shared code

`deident.py` now has a second consumer: **move it to `corpuslib/deident.py`**,
update prototype 01's imports (`build_index.py`, `mcp_server.py`), and keep
no copy here. Run 01's `cli.py` once after to confirm nothing broke (index
pickles are unaffected — content hash doesn't include code).

### Stage 1 — features + baselines (deterministic, CPU)

`features.py` computes per candidate, and caches to `output/features.json`:

- `sim_prior_gold`: max cosine (arctic-l-v2, doc-prefix conventions per
  prototype 01) vs all prior-year gold holdings — "how settled is this?"
- `sim_same_year`: max cosine vs other same-year candidates — duplication
  pressure
- mechanical: prevailing_party (respondent/mixed wins are rare → notable),
  category, n_authorities, cites_appellate_case (any authority of
  type=case), has_arguments, text length, remedies
- `baselines.py`: (a) chance at base rate; (b) logistic regression on the
  mechanical+similarity features (sklearn, 5-fold CV on 2009); (c) a
  rule-of-thumb baseline (respondent_prevailed OR cites_appellate_case OR
  sim_prior_gold < median). These are the bar the LLM must clear.

### Stage 2 — LLM judge (3 context arms on 2009)

`judge.py` — one JSON per (candidate, arm) under `output/judgments/`,
resumable/idempotent (skip existing), via `corpuslib.llm.generate` with a
JSON schema: `{include: bool, confidence: float 0-1, reasons: [enum:
novel_issue, unusual_facts, respondent_win, recurring_guidance,
clarifies_standard, routine_settled_law, duplicative, administrative,
fact_bound], rationale: str<=60w}`.

Prompt frame (same for all arms): "You are the editor of an annual volume
cataloguing noteworthy California teacher-layoff (Ed. Code §§44949/44955)
ALJ holdings for practitioners. Editors include holdings that are novel,
unsettled, instructive, or unusual; they omit routine applications of
settled law, administrative dispositions, and duplicates of already-known
points. Would you include this holding? <holding fields>"

- **Arm A — holding alone.**
- **Arm B — + prior-volume context:** top-5 `sim_prior_gold` neighbors with
  their years ("past volumes catalogued these on similar issues").
- **Arm C — + same-year context:** top-5 same-year candidate neighbors
  ("these similar holdings also exist this year"), targeting the
  duplicative class.

Pick the winning arm on 2009 (by F1 at the tuned threshold), then run ONLY
that arm on 2004, threshold frozen from 2009. Time-box: if an arm's first
50 judgments are degenerate (all-include or all-exclude), stop and fix the
prompt before burning the rest.

### Stage 3 — set assembly (Task B)

`assemble.py`: greedy selection by judge confidence with an MMR-style dedup
penalty (skip a candidate whose cosine vs an already-selected same-category
holding exceeds τ; tune τ on 2009). Produce the selected set at (a) the
human volume's count and (b) the threshold-implied count; score set-level
precision/recall/F1 vs the human-included set. This is the shape P5
actually consumes.

### Stage 4 — eval + disagreement queue

`eval_taste.py`: per-arm and per-baseline pointwise metrics on dev/test
(precision, recall, F1, plus precision-recall curve from confidence);
per-category breakdown; Task B set metrics. Writes
`output/disagreements_{year}.md`: ~30 stratified cases — judge-include/
human-omit and judge-omit/human-include — each with the holding (already
de-identified), the judge's rationale, and the matched/unmatched gold text.
The disagreement file is generated but **Nick has opted not to review it
for the verdict** — the verdict rests on metrics alone, with the label-noise
caveat disclosed as an open question in FINDINGS (the file remains available
if the question ever matters). FINDINGS quotes at most 3 examples.

## Deliverables

`features.py`, `baselines.py`, `judge.py`, `assemble.py`, `eval_taste.py`,
`output/` artifacts (gitignored), the corpuslib deident graduation,
`FINDINGS.md`, root `STATUS.md` + README gallery updates.

## Success criteria

- **Validated:** winning judge arm beats the logistic baseline on 2009 by
  ≥5 F1 points AND holds up on 2004 (no more than ~10-point F1 drop), with
  F1 meaningfully above chance (~0.40 at base rate). Judgment call near the
  line — argue from the failure cases, not the number alone.
- **Partially validated:** judge ≈ logistic baseline but both well above
  chance → taste is mechanically capturable; recommend the cheap version
  for P5.
- **Falsified:** nothing beats chance meaningfully.
- Report ALL numbers (every arm, every baseline, both years) — no
  cherry-picking the winning arm's dev score as the headline.

## Out of scope

Editorial commentary generation (W8). Report rendering (P5). Fine-tuning a
classifier on embeddings (a future iteration if the LLM judge disappoints).
Cross-year "memory" of what prior AI volumes selected. Re-judging with the
122b model beyond the 100-holding sample.

## Privacy notes

Judgments, features, and disagreement files contain holding text — all
de-identified at load time via `corpuslib.deident` (roster names → R-refs)
and kept under gitignored `output/`. Anything committed (FINDINGS examples)
cites District (ALJ) only. Local models only; no corpus text leaves the box
unless the subagent fan-out fallback is used (then it's already
de-identified).
