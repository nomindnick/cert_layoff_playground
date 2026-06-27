# SPEC — E0. Scoreboard (the measurement instrument)

> Build this first. Read `../SPEC.md` (program spec) for context, the merged-corpus
> facts, and the privacy rules. Mostly deterministic → **buildable now, GPU-busy.**
> The only LLM step is the depth-judge, which can ride on a subagent.

## Hypothesis

We can **measure coverage of the corpus's intellectual space** with a stable,
discriminating scorecard, using the corpus's own structured decisions as the
answer key — such that better orchestration scores measurably higher and a
degraded arm scores lower. **Falsified if** the metrics are too noisy/circular to
rank arms (e.g. facts-only matters under-determine issues so badly that recall is
a coin flip, or the depth-judge can't beat its own token-overlap proxy). If the
scoreboard can't discriminate, the whole program is unfalsifiable — find that out
here, cheaply, before building any arm.

## Why it matters

Coverage is currently an intuition. This repo's method is to turn intuitions into
measurements (permutation tests, held-out validation, beat-the-baseline). The
scoreboard is that conversion for coverage; every later experiment is scored by
it. No scoreboard ⇒ "the fancy system covered more" is hand-waving.

## Data inputs

Merged corpus (`harness/corpus.py`): 404 structured decisions (1999–2025,
schemas 0.2.0 + 0.4.0), per-holding `issue.category`, `issue.statement`,
`facts[]`, `reasoning.summary`, `arguments[]`, `ruling.prevailing_party`. Gold
(3,955) is **not** an answer-key source here (no reasoning) but is in-corpus for
arms to retrieve. Category-normalization map from `harness/corpus.py`.

## Approach

**1. Matter generator (`build_evalset.py`) — `harness/matters.py`.**
For each held-out decision `D`:
- Collect `D`'s holdings; **de-identify every prose field** (`harness/deid.py`)
  before use.
- Emit a **facts-only matter**: a narrative fact pattern assembled from
  `facts[].summary` across holdings (+ district context from `identity.district.raw`,
  de-identified to District form, names→roles like "a senior teacher" / "a junior
  teacher"). **No issue labels, no holdings, no outcomes** in the matter — only the
  raw factual situation an attorney would have *before* the decision. (Optionally
  reframe to a pre-decision posture, but do not inject issue cues.)
- **Answer keys (held out):**
  - *breadth* = `set(normalize(h.issue.category) for h in D.holdings)`.
  - *depth* = per holding: `{reasoning.summary, operative facts}` — what a good
    analysis of that issue *should* recover.
- Record `D`'s id so retrieval can **exclude `D`** (and same-district+same-year
  near-duplicates) — no self-retrieval.
- Sample a held-out set spanning eras/issues (e.g. 30–50 matters); stratify so
  rare issues appear. Persist `output/evalset/{matter_id}.json`
  (`matter`, `answer_key`, `exclude_ids`).

**2. Metrics (`harness/metrics.py`, driven by `run_scoreboard.py`).**
An *arm* is anything that, given a matter, returns `{spotted_issues:[cat],
per_issue:[{issue, analysis, cited_holding_ids:[...]}]}`. The scoreboard grades
that, arm-agnostic:
- **Breadth:** recall = |spotted ∩ key| / |key|; precision = |spotted ∩ key| /
  |spotted|; spurious-but-plausible issues bucketed and **flagged, not penalized**
  (auto-grading "plausible" is unreliable — leave to human/LLM review). Normalize
  categories both sides.
- **Depth:** for each correctly-spotted issue, did the arm's `analysis` recover
  the ALJ's operative fact distinction (the held-out `reasoning`/`facts`)? Two
  scorers run together: (a) cheap **token/entity-overlap proxy** vs the operative
  facts; (b) **LLM-judge rubric** (0–3: restates bare holding / names the right
  facts / recovers the actual distinction-and-rationale). Report both; trust the
  judge only where it tracks the proxy + the human calibration set.
- **Grounding (instrument, not trust):** cite-resolution rate — every
  `cited_holding_id` must resolve to a real merged-corpus holding; unresolved →
  flagged and the claim dropped from scoring. Plus optional brittle
  "does-cited-holding-support-analysis" LLM check.
- **Cost:** wall-clock seconds, model-call count, total tokens per (matter, arm)
  — the denominator for *coverage per wall-clock hour*.

**3. Calibration (experiments-within-the-experiment).**
- Hand-check ~5 generated matters: does facts-only under-determine the litigated
  issues? Report the **recall ceiling** (some issues may be unrecoverable from
  facts alone — that bounds every arm and must be stated, not hidden).
- Human-rate ~20 depth judgments; keep the judge only if it correlates; else fall
  back to the proxy + spot-checks.
- Sanity arms: a **random-issue arm** (floor) and **fixed-RAG** (05) must bracket
  the score sensibly, or the scoreboard isn't discriminating.

## Deliverables

`harness/{corpus.py, deid.py, matters.py, metrics.py}`; `setup_merged_corpus.sh`;
`scoreboard/build_evalset.py`, `scoreboard/run_scoreboard.py`;
`output/evalset/*.json`; a `score(arm_fn) → scorecard.json` entry point E1 calls;
`output/leaderboard.md`; `FINDINGS.md` (incl. the recall-ceiling + judge-calibration
numbers and which backend judged).

## Success criteria

Validated when: (a) the matter generator produces de-identified, issue-label-free
matters with a stated recall ceiling; (b) fixed-RAG and the random floor bracket
the scale (discrimination exists); (c) the depth-judge meets the calibration bar
or is replaced by the proxy. Then E1 can run.

## Out of scope

The arms themselves (E1). Generating *synthetic* matters from scratch — we derive
matters from real held-out decisions so the answer key is real. UI.

## Privacy notes

Matters are de-identified by construction (names→roles); every prose field passes
`harness/deid.py` + the non-roster scrub. Any matter or judgment committed as a
FINDINGS example carries District (ALJ) only. `output/` gitignored.
