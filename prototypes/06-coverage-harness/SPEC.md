# SPEC — 06. Coverage Harness (orchestration for intellectual-space coverage)

> **Program spec.** This prototype is a *research program*, not a single build.
> It has a shared substrate (`harness/`) and a sequence of experiments, each in
> its own subdirectory with its own `SPEC.md` + `FINDINGS.md`. Read this file
> first; then the experiment SPEC you're building. Build order is fixed by the
> dependency graph below — the scoreboard (`scoreboard/`) comes first because
> nothing else is falsifiable without it.
>
> Working name "coverage-harness" = the organizing principle is **measured
> coverage of the corpus's intellectual space**; the experiments are
> orchestration designs that try to climb that score on local models.

## Thesis (program-level hypothesis)

On a **bounded-issue, fully-tagged, non-precedential** corpus, a *system* of
many small, narrowly-scoped, differently-grounded local-model passes can cover
the **intellectual space** of the corpus — the issues implicated by a matter and
the fact/reasoning analysis that makes past holdings useful — **as well as or
better than a single frontier-model pass, within an attorney-tolerable wall-clock
budget (hours, not a week).** "System over model," in the *many-adequate-with-
different-scopes-and-functions* sense, not merely the *many-adequate-eyes* sense.

**Falsified if:** once we can actually *measure* coverage (the scoreboard), no
local-model orchestration we try beats a fixed-RAG baseline by enough to justify
its wall-clock, **and/or** the gap to a single frontier pass stays wide on the
axis that matters (depth / fact-reasoning analysis, not breadth). A cheap,
deflating result is a success: e.g. "the taxonomy *is* the coverage; enumerate
it and skip the agent," or "orchestration buys breadth but depth is bounded by
the frontier model's raw reasoning."

This program finally runs **W9 stage 2** (can a *local* model orchestrate the
research loop — never tested) and operationalizes **W10/W11** under one scoreboard.

## Why it matters

Every attorney-facing idea in this repo (04 deep-research, 05 risk-memo, 03
scouting) is a different angle on one job: **give L&E attorneys strategic insight
they can act on in a live matter** (a contemplated layoff or an active dispute).
Two settled facts reframe the job:

1. **The value is insight, not citation.** OAH layoff decisions are not
   precedential — an attorney won't "cite this and win." The corpus is a
   *strategic-intelligence asset*: what recurs, what arguments land, what an ALJ
   is likely to do, what the other side will raise. So the product goal is
   **coverage of the intellectual space**, not retrieval of an on-point case.
2. **Grounding is a solved given, not the product.** Cite-resolution is cheap; a
   brittle LLM pass checks "does the holding support the proposition"; and the
   attorney cite-checks everything regardless (professional duty). So grounding
   stops being the trust story and becomes our **measurement instrument** (see
   the scoreboard's cite-resolution check).

The open worry is **coverage**, and this program exists to convert that worry
from an intuition into a measured quantity, then to find the orchestration that
maximizes it per wall-clock hour on **local models** (privacy: privileged matter
facts never leave the Strix Halo; cost: no API token budget, so effectively
unlimited passes — wall-clock is the only constraint).

## The two coverage problems (the spine of every experiment)

- **Breadth = issue-spotting recall.** Did we surface every issue the matter
  implicates? On a *bounded, fully-tagged* corpus, holding-level breadth is
  nearly free (every holding is issue-tagged — you don't *find* the skipping
  holdings, you *enumerate* all ~512 of them). So the real breadth risk is
  **spotting the issue at all** — including non-obvious **cross-issue
  interactions** (a skipping defense that's really a competency argument). 05's
  fixed `spot_issues()` rule-map is brittle exactly here.
- **Depth = fact/reasoning recovery.** Bare holdings (the gold summaries) are of
  limited use — they don't show *how the ALJ reasoned from the facts*. Useful
  analysis picks holdings apart by **facts + ALJ rationale** and compares them to
  the pending matter. This is the harder, more valuable axis — and it is
  **data-bounded**: reasoning exists only in the *structured decision records*
  (404 decisions, ~1,250 holdings across 1999–2025), not in the 35-year gold.
  Design rule that falls out: **for any holding that will carry analytical
  weight, read the full structured holding (`facts` + `reasoning`); never reason
  from a summary.** Depth scales with the production corpus build.

## Data inputs (the merged corpus)

Build a 3-era merged root by symlink (no copy; privacy preserved), reusing
`03-alj-scouting/make_merged_corpus.sh` (spike + production), then
`export CORPUS_ROOT=<merged>` so `corpuslib` runs unchanged. As of 2026-06-17:

| Source | Eras | Decisions | Holdings (w/ facts+reasoning) | Schema |
|--------|------|-----------|-------------------------------|--------|
| spike (`cert_layoff_lab`) | 2004, 2009 | 267 | 835 (≈all) | 0.2.0 |
| production (`cert_layoff_corpus`) | 1999–2001, 2018–2025 | 137 | ~419 (≈all) | 0.4.0 |
| **merged structured** | **1999–2025** | **404** | **~1,250** | mixed |
| gold summaries | 1979–2015 | — | 3,955 (summaries only, no reasoning) | — |

Accessors: `corpuslib.load_decisions()`, `load_gold_holdings()`,
`load_taxonomy()`, `load_case_index()`; F1 engine in `prototypes/01-search-mcp/`;
`corpuslib.deident.deidentify()`. Per-holding fields present in **both** schemas
and used here: `issue.category`, `issue.statement`, `ruling.prevailing_party`,
`facts[]` (`.summary`, `.quote`), `reasoning.summary`, `arguments[]`
(`.party`, `.summary`), `summary_style_holding`, `authorities[]`.

**Known data limitations — bake these into the harness, do not fight them:**
- **Schema tolerance (0.2.0 vs 0.4.0).** Read defensively. The one category that
  *moved*: gold + spike use `pks_allowed`/`pks_not_allowed`; production merged
  them to `pks_reduction`. The harness needs a **category-normalization map** so
  breadth recall compares like with like across sources. `identity.{district,alj}.raw`
  exists in both; `prevailing_party` unchanged; `canonical*` ids are null/partial
  in production (still surname-joining — conflation risk per the 03 lesson).
- **STATUS is stale** (says 93 prod decisions / 2018–25). The build is live and
  growing — **derive era/span/counts at runtime**, never hardcode.
- **Decision dates** are null on ~32 production records → temporal keys off the
  case-number-year prefix, not `decision_date`.
- **Depth is data-bounded** to 1999–2025 structured decisions; gold gives breadth
  only.

## Compute profile

`none` (scoreboard scaffolding, retrieval arms A/B, all metrics except the depth
judge — fully deterministic, **buildable now while the GPU is busy**) **+
local-LLM-heavy** (arms B/C/D synthesis, adversarial passes, the LLM depth-judge —
run when the GPU frees). Intended local models: the heterogeneous fleet
(`gemma4:31b`, `qwen3.6:27b`, `gpt-oss:120b`, down to small models for the
sweep), chosen per the lessons (`think=False` / `num_predict` for reasoning
models; `OLLAMA_NUM_PARALLEL=1` for big sequential runs).

**GPU-busy fallback** (subagent fan-out, cloud Claude on the subscription — never
`claude -p` from code): the **frontier reference arm** (the "one smart" ceiling)
and the **LLM depth-judge** can run as subagents anytime. *But the load-bearing
question is local feasibility* — a subagent arm validates the orchestration
*idea*, not that a local model can do it. **Every FINDINGS must name the backend
per result**, and the headline claims must be local-backend results.

## Shared infrastructure (`harness/`)

Built once, imported by every experiment (intra-prototype imports only; nothing
leaks to sibling prototypes).

- **`corpus.py`** — merged-corpus loader with schema-tolerant per-holding
  accessors + the category-normalization map + a robust era/year deriver. Wraps
  `corpuslib` so experiments never branch on schema version themselves.
- **`deid.py`** — the de-identification gate. `deidentify(text, rec)` on **every
  prose field** (`issue.statement`, `facts`, `reasoning`, `arguments`) before any
  model sees it or anything is written to a viewable/committed artifact, plus a
  belt-and-suspenders **name-scrub** for non-roster names (a retained junior
  teacher survives roster de-id — lesson 108). *First-build check: confirm
  `corpuslib.deident` covers the production 0.4.0 roster structure; it was built
  for 0.2.0.*
- **`matters.py`** — the **matter-from-held-out-decision generator** (see E0).
- **`metrics.py`** — breadth (issue-spotting recall/precision), depth
  (fact-reasoning recovery), cite-resolution (grounding instrument), and cost
  accounting (wall-clock + call-count + tokens). The scoreboard.
- **`blackboard.py`** — the runtime markdown scratchpad (per-matter dir:
  `question.md`, `notes/`, `findings.md`, `attacks/`, `verdict.md`).
  User-viewable (process visibility is itself a feature); gitignored. The
  coordination substrate for arm D and the judge-loop.

## Experiments (each a subdirectory)

> Each gets its own `SPEC.md` (build-ready) + `FINDINGS.md`. `scoreboard/` and
> `exp-bakeoff/` are specced in full now; `exp-divergence/`, `exp-depth/`,
> `exp-steering/`, `exp-judge-loop/` carry a focused stub SPEC to be promoted to
> full once E0/E1 land (don't gold-plate experiments whose design depends on
> earlier results).

### E0 — Scoreboard `scoreboard/` *(build first; mostly deterministic)*
The measurement instrument the whole program climbs. **Matter generator:** take a
held-out structured decision `D`, emit a **de-identified, facts-only matter**
(narrative fact pattern, names→roles, **no issue labels** — labeling issues would
make breadth trivially circular). **Answer keys, held out of retrieval:** breadth
= the set of `issue.category` values `D` actually adjudicated (normalized); depth
= each holding's `reasoning.summary` + operative `facts`. **Metrics:** breadth
recall/precision (+ a "plausible-but-not-in-D" bucket flagged, not auto-graded);
depth = does the arm's "why this holding bears" recover the ALJ's actual fact
distinction (LLM-judge rubric, with a cheap token-overlap proxy and a small
human-rated calibration set — LLM judges are brittle, cf. the 02 lesson);
grounding = cite-resolution rate; cost = wall-clock/calls/tokens. **Exclude `D`
(and trivially-near records) from retrieval.** Output: `scorecard.json` +
`leaderboard.md`.

### E1 — Coverage bake-off `exp-bakeoff/` *(flagship)*
Same held-out matter set, scored by E0, **four arms + a reference ceiling**:
- **A. Fixed RAG** — 05's `evidence.py` issue-spot + retrieve. The baseline to beat.
- **B. Taxonomy partition-and-sweep** — a generous (high-recall) cheap issue
  proposer picks candidate categories; *enumerate every holding* in them, shard
  across many small parallel local calls, each judging relevance to the matter.
  The "many adequate eyes" arm — coverage by enumeration, not retrieval.
- **C. Agentic adaptive search** — a local model drives `research_tool.py`
  (search/holding), adapting queries as insight accumulates (04's loop, local).
- **D. Sweep + divergence-adversarial recovery** — B, plus the E2 mechanisms
  (near-miss-tail + adjacent-doctrine adversaries) feeding missed issues/holdings
  back in.
- **Ref. Single frontier pass** (Opus subagent) — the "one smart" ceiling.
**Headline:** the *shape* — does many-adequate-diverse-scope beat fixed-RAG and
approach the ceiling, at what wall-clock cost. Resolves "agent vs non-agent"
**empirically** (e.g. if B≈C on breadth, the agent is theater). Run arms on local
models; ref on subagent.

### E2 — Context-divergence as a coverage mechanism `exp-divergence/` *(stub)*
Isolate it: ground the adversary in a **different region of the corpus** than the
researcher. Test slices — **near-miss tail** (holdings ranked just below the
primary cutoff → the adversary becomes a *coverage-recovery probe*: "what did
retrieval miss?") vs **random tail** (noise control) vs **adjacent-doctrine**
(competency-grounded adversary attacking a skipping conclusion → finds cross-issue
interactions). Metric: marginal issue/holding recall lift on E0 over a same-
grounding adversary. Hypothesis: divergence manufactures non-correlation via
*evidence placement* (cheaper/more steerable than model-weight diversity) and the
lift shows up as **coverage**, not just "more attacks."

### E3 — Depth pass: reasoning vs summary `exp-depth/` *(stub)*
Does reading full `facts`+`reasoning` for load-bearing holdings beat
summary-only? Metric: E0 depth score + a 05-style **discriminability** check (a
deeper, more matter-specific memo should be *more* discriminable to its own
matter vs a decoy). Tests the "bare holdings are brittle" hypothesis head-on and
quantifies the value of the structured-decision substrate over gold summaries.

### E4 — Local steering / in-context conditioning `exp-steering/` *(stub)*
Two levers, since "steering > raw model": (a) **background-issue packs** — a dense
corpus-derived "treatise chapter" per issue (e.g. skipping law), injected to
condition a per-issue agent ("immediate fine-tuning"); (b) **multi-shot
grounding** via strategic example selection. Hypothesis + the tradeoff to
measure: conditioning raises **depth** but **biases toward the dominant pattern
and suppresses novel-issue recall** — so pair every conditioned agent with a
divergence-grounded counterpart (E2) and quantify the bias. Secondary: does
model-family **heterogeneity** add error-catching beyond steering one model?

### E5 — Judge-loop with split metrics `exp-judge-loop/` *(stub)*
Iterative refine-until-threshold, but **split the objective sub-metric**
(recall/grounding from E0) from the **holistic rubric** score. Hypothesis (from
the W11 insight): the holistic/coverage score climbs while **grounding/recall
plateaus** — i.e. the loop buys polish and coverage, not correctness; and an
author==judge loop on one local model can reward-hack to "looks good to me." Cap
iterations; require monotone improvement on the *objective* metric or stop.

## Sequencing & dependencies

```
harness/ (corpus, deid, blackboard)
        │
        ▼
   E0 scoreboard ──────────────► (gate: nothing below is falsifiable without it)
        │
        ▼
   E1 bake-off  ──┬──► E2 divergence (decomposes arm D)
                  ├──► E3 depth pass (decomposes the depth axis)
                  ├──► E4 steering   (refines whichever arm wins)
                  └──► E5 judge-loop (wraps whichever arm wins)
```

Build E0 + `harness/` now (deterministic, GPU-free). Run E1 arms + the LLM
depth-judge when the GPU frees; the reference arm + depth-judge can ride on
subagents meanwhile to de-risk the *measurement* before the local grind.

## Directory structure

```
prototypes/06-coverage-harness/
  SPEC.md                 ← this program spec
  README.md               ← one-screen orientation (build later)
  setup_merged_corpus.sh  ← wrapper over 03's make_merged_corpus.sh
  harness/                ← corpus.py deid.py matters.py metrics.py blackboard.py
  scoreboard/             ← E0:  SPEC.md FINDINGS.md  build_evalset.py run_scoreboard.py  output/
  exp-bakeoff/            ← E1:  SPEC.md FINDINGS.md  arms/  bakeoff_workflow.js  output/
  exp-divergence/         ← E2:  SPEC.md ...
  exp-depth/              ← E3:  SPEC.md ...
  exp-steering/           ← E4:  SPEC.md ...
  exp-judge-loop/         ← E5:  SPEC.md ...
  FINDINGS.md             ← program-level rollup
```

Each experiment owns its `output/` (gitignored). If an arm needs exotic deps
(e.g. clustering), it gets its own venv; `harness/` stays importable from base
python + `corpuslib`.

## Success criteria (program)

- **E0 validated** when the metrics produce a *stable, sensible* scorecard on a
  held-out matter set: fixed-RAG scores reasonably, a deliberately-degraded arm
  scores low, depth-judge agrees with the human calibration set ≥ acceptably.
  (An unstable/un-discriminating scoreboard is the thing that would sink the
  program — find that out first and cheaply.)
- **E1 validated** if ≥1 local-model arm beats fixed-RAG on coverage by a margin
  that justifies its wall-clock, with the arm ranking + the local-vs-frontier gap
  reported with uncertainty. The interesting result is the *shape* and the
  *cheap deflations* (B≈C ⇒ skip the agent; depth gap stays wide ⇒ frontier-bound).
- **Each E2–E5** has its own falsifiable sub-claim above; "falsified-because-X"
  with X stated precisely is a success outcome per repo norm.

## Out of scope

The production app/UI and the latency-tiered surfaces (Tier 0/1/2) — this program
produces the *evidence* for which orchestration to ship, not the shipped thing.
The **Letta-style cross-matter accreting memory** is *designed but deferred*: when
built it stores **only de-identified, matter-agnostic corpus wisdom** (confirmed
splits, ALJ tendencies — "memory belongs to the corpus, not the user"), never
privileged matter facts; gated behind E0/E1 landing. Fine-tuning/distillation
(W12) is downstream. No non-layoff domains.

## Privacy notes

Load-bearing here, because the structured decisions carry **raw respondent names
in prose fields** (both schemas):
1. Corpus stays outside the repo (symlinked merged root); `output/` and blackboard
   dirs gitignored.
2. **De-id at read time, before any model call** — every prose field through
   `harness/deid.py`; plus the non-roster name-scrub gate before anything
   user-viewable or committed.
3. Synthesized **matters** are de-identified (names→roles) by construction.
4. Anything committed (sample matter, leaderboard, FINDINGS example) carries
   **District (ALJ) only** — never a respondent name, never an un-scrubbed
   verbatim dump. When in doubt, describe.

## Open questions / first-build verifications

- Confirm `corpuslib.deident` de-identifies production (0.4.0) rosters, not just
  spike (0.2.0). **Privacy-critical — verify before any 0.4.0 prose reaches a model.**
- Pin the **category-normalization map** (gold/spike `pks_allowed|pks_not_allowed`
  ↔ production `pks_reduction`; any other drift) before computing breadth recall.
- Calibrate the matter generator: does **facts-only** under-determine the issues
  `D` litigated (some issues raised but thinly factual)? Hand-check ~5; report the
  ceiling on achievable recall.
- Calibrate the **depth judge** against a small human-rated set; keep the cheap
  token-overlap proxy as a guard against judge drift.
- Re-derive corpus span/counts at build time (STATUS is stale; build is growing).
