# FINDINGS — 02. Editorial-taste judge (W7)

## Verdict

**Partially validated, leaning weak — do not ship the LLM judge.** An LLM
editor (gemma4:31b, and gpt-class qwen3.5:122b) does **not** beat a cheap
logistic regression on mechanical features at reproducing the human editors'
selection, and adds no signal on top of it. More importantly, on the held-out
2004 volume *neither* selector clears chance by much: editorial "taste" as
recoverable from the holding records is partly real but substantially
**year/editor-specific**, not a stable learnable function. The useful product
takeaway is concrete: P5's curation layer should be a **transparent
feature-scored filter the attorney tunes**, not an LLM "is this interesting?"
gate — and it should not promise to match any particular era's volume.

## What we learned

**Pointwise selection on 2009 (dev, 633 candidates, 34% positive).** Numbers
are AUC (threshold-free ranking quality) and best-achievable F1:

| Selector | AUC | best F1 |
|---|---|---|
| Chance (base rate) | 0.500 | 0.34 |
| Heuristic rule | — | 0.477 |
| **Logistic regression** (8 features + category) | **0.667** | **0.541** |
| LLM judge, arm A (holding alone) | 0.614 | 0.526 |
| LLM judge, arm B (+ prior-volume context) | 0.601 | 0.516 |
| LLM judge, arm C (+ same-year duplicates) | 0.608 | 0.516 |
| Logistic **+ judge score as a feature** | 0.668–0.676 | 0.56 |

- **The 31B judge loses to logistic regression**, and adding the judge's
  score as a 9th feature moves logistic AUC by ≤0.01 — the LLM carries
  essentially no signal orthogonal to the mechanical features. Reading the
  holdings does not beat counting their structure.
- **Context arms did not help; prior-volume context (B) slightly hurt.**
  Feeding the judge what past editors catalogued on the same issue anchored
  it worse, not better. A clean negative result about retrieval-augmented
  judgment for this task: more corpus context ≠ better taste.
- **Scale does not rescue it.** qwen3.5:122b on a stratified 100-holding
  sample scored AUC 0.583 vs gemma4:31b's 0.597 on the *same* holdings —
  no improvement from ~4× the parameters.
- **Judges are poorly calibrated** — confidence is strongly bimodal (votes
  ~0.9 or ~0.1), so there's little graded signal to rank or threshold with.

**Held-out transfer (2004, 202 candidates, 40% positive) — the real test:**

| Selector | 2004 AUC | volume-assembly F1 (80-entry set) |
|---|---|---|
| Chance | 0.500 | 0.396 |
| Logistic (trained on 2009) | — | 0.41 |
| LLM judge, arm A | 0.563 | 0.412 |

- On a different era with different editors, **both selectors collapse to
  ~chance.** The 2009 signal (logistic F1 0.54) is substantially 2009-specific.
  This is the load-bearing finding: there is no stable, transferable "taste"
  function here, only weak per-year structure. (Caveat: 2004 is image-OCR era;
  some degradation is extraction noise, not pure taste drift — but the judge,
  which reads cleaned holdings, fell the same way.)

**Task B (assemble a volume at the human count).** 2009: judge selects a
215-entry volume overlapping the human one at 49%, logistic at 51%, chance
34%. The MMR dedup penalty (τ) barely moved overlap — duplication is already
priced into the `sim_same_year` feature, so an explicit dedup pass is
redundant given that feature.

**What the mechanical model reveals about real editorial behavior** (logistic
coefficients, the genuinely interesting by-product):
- **Similarity to other same-year holdings is the strongest *negative*
  predictor of inclusion** — direct, quantified evidence that "we already
  have this point" drives omission. The duplication theory of editorial
  selection is correct.
- `has_arguments` / `n_args` / `len_text` are positive — editors favor
  substantive, contested, developed holdings over terse ones.
- **`respondent_win` ≈ 0 weight** — contrary to the intuition baked into the
  judge prompt that teacher wins are inherently noteworthy. They aren't, in
  the aggregate.

**Label-noise caveat (unreviewed, per Nick's call):** negatives include
holdings the editors might have included but didn't catalog (the volumes are
editorial, not exhaustive), so all F1s are floors on true precision.
`output/disagreements_{2009,2004}.md` were generated for future use but not
reviewed; the verdict rests on metrics. This caveat cannot rescue the
transfer result, though — label noise is similar across years.

## Backend notes

- Primary judge **gemma4:31b** via `ollama` (batches at `-np 4`); ~2,000
  judgments at ~14s each. Scale check **qwen3.5:122b**.
- **Lesson — reasoning models need `think=False` for structured output.**
  qwen3.5:122b initially failed all 100 judgments (empty responses): it is a
  reasoning model that spent the entire token budget in the hidden thinking
  channel. `think=False` fixed it completely (and made it *faster* than
  gemma, ~5s/judgment — MoE). Now wired into `corpuslib.llm.generate(think=)`
  and auto-set for `qwen3` in `judge.py`. This is the "gpt-oss refuses
  structured output"-class toolbox fact the lessons ledger exists for.
- **Lesson — temp 0 + grammar-constrained gemma loops.** The first run hit
  repetition loops (timeouts, unterminated JSON, `confidence: 100`). temp 0.2
  + `num_predict` cap + a hotter retry + a `score` derived as
  `confidence if include else 1-confidence` (robust to the model's reading of
  "confidence") cleared it. The 50-judgment sanity gate caught all of this
  before the full run — keep that gate.

## Blocked on full corpus?

The transfer collapse is the thing to recheck at scale: with ~14 gold years
instead of 2, train on N-1 and test on the held-out year to see whether a
*multi-year-trained* selector generalizes where a single-year one didn't.
Plausible it improves (more editors averages out idiosyncrasy); plausible it
confirms taste is irreducibly editorial. Either is a real answer. Everything
re-points via `corpuslib`; rerun `features.py` → `baselines.py` → optionally
re-judge. Do **not** re-run the LLM judge at corpus scale on this evidence —
it doesn't earn its compute.

## Production recommendation

**Build differently — a build-time artifact generator, but the cheap version.**
P5 (report studio) should curate with a **transparent logistic/feature score
the attorney can threshold and see the reasons for**, not an LLM gate. Frame
regenerated volumes honestly: "ranked by estimated noteworthiness," not
"matches the 20xx editors." Keep the duplication feature (it's the real
signal); drop the dedup pass (redundant) and the respondent-win prior (no
signal). Revisit a learned selector only after the multi-year transfer test
above. The disagreement files remain available if the partner ever wants to
probe label quality.
