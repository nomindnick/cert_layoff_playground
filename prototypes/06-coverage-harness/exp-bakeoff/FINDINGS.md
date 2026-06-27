# FINDINGS — E1 (arm: local issue-spotter / breadth)

## Verdict

`validated` — **local models clear the issue-spotting floor decisively, and it's
a small-model job.** Scored on the E0 breadth metric (rarity_recall) over 36
zero-leak matters; floor = frequency prior 0.373.

| model | params | rarity_R | recall | precision | sec/matter | vs floor |
|-------|-------:|---------:|-------:|----------:|-----------:|----------|
| oracle | — | 1.000 | 1.000 | 1.000 | — | ceiling |
| **gemma4:31b** | 31b | **0.810** | 0.831 | 0.404 | 14.7 | 2.2× |
| **gemma4:12b** | 12b | **0.797** | 0.795 | 0.346 | 9.7 | 2.1× |
| **qwen3.6:27b** | 27b | **0.780** | 0.775 | 0.441 | 14.3 | 2.1× |
| qwen3.5:9b | 9b | 0.355 | 0.347 | 0.339 | 3.6 | <floor |
| qwen3.5:4b | 4b | 0.330 | 0.336 | 0.342 | 2.2 | <floor |
| freq-prior | — | 0.373 | 0.443 | 0.398 | 0 | floor |
| keyword | — | 0.399 | 0.402 | 0.333 | 0 | — |
| gpt-oss:20b/120b | — | — | — | — | — | ERR (see below) |

## What we learned

- **It's a capability threshold + family effect, not smooth scaling.**
  `gemma4:12b` (0.797) ≈ `gemma4:31b` (0.810) — scaling gemma 12b→31b adds almost
  nothing for issue-spotting. Yet `qwen3.5` at 4b/9b sits *below* the floor
  (0.33/0.36) while `qwen3.6:27b` is well above (0.78). So the capability appears
  sharply around a threshold and depends on model family, not a smooth size curve.
- **gemma4:12b is the efficiency sweet spot** — frontier-of-curve coverage at
  7.6 GB / 9.7 s, same score as the 19 GB / 14.7 s 31b. For this step, pay for the
  smallest capable model; bigger params don't move the metric. **Direct support
  for "system over model": a 12b model already saturates achievable issue-spotting
  recall.**
- **The shared blind spots are the RECALL CEILING, not a model gap.** Every
  working model — including the strongest (gemma4:31b) — systematically misses
  `tie_breaking`, `procedural_issues`, `bumping`, `pks_reduction`. Scaling within
  gemma (12b→31b) does NOT fix them. These issues are under-determined from a
  facts-only matter (tie-break needs spotting a shared seniority date; procedural
  is notice/timing rarely in the fact narrative). **The headroom above ~0.8 is a
  SYSTEM problem (retrieval/fact-surfacing/divergence to recover the missed
  issues), not a bigger-model problem** — exactly the question arms B/C/D test.
- **Precision (~0.34–0.44) is understated.** Over-spotting is dominated by
  `competency`/`credentials`/`seniority` — the *plausible-but-not-adjudicated*
  bucket (the facts genuinely touch them; they just didn't get a separate
  holding). True precision needs a plausibility reclassification (Opus judge over
  the over-spots) before reading the precision column literally. qwen3.6:27b has
  the best precision (0.441) among the strong models.
- **gpt-oss (20b + 120b) returned empty on all 36** — ollama structured-output
  (`format`) swallows the content into the harmony reasoning channel regardless of
  `think`. A known integration quirk, **not** a capability result; deferred (the
  ceiling question is already answered within the gemma family). To test gpt-oss
  later: free-text generation + manual JSON extraction, or read the reasoning
  channel, or a `reasoning_effort` option.

## Recall-ceiling calibration (Opus judge, 36 matters, 100 real + 144 decoy issues)

The 0.80 spotter score looked like a 0.20 miss; the ceiling calibration shows
most of that miss is **unrecoverable answer-key noise, not model failure** — and
that the over-spotting is mostly legitimate.

- **Ceiling = 0.78** (rarity-weighted 0.782): only 78% of answer-key issues have a
  genuine factual hook in the facts-only matter; **22% is under-determination**
  (the decision litigated the issue but the extracted facts don't carry its hook —
  lossy matter construction). Judge well-calibrated: real 0.78 vs decoy 0.31
  recoverable, **+0.47 separation**.
- **gemma4:12b fair recall = 0.902** (vs the recoverable-only key): it catches
  ~90% of what's recoverable. So **breadth-from-facts is ~90% solved by a 12b
  model**; only **~10% recoverable headroom** remains (plus the 22% that no
  facts-only arm can reach).
- **Precision was badly understated.** Plausible bucket = 0.31; the spotter's
  top over-spots are mostly legitimate — `competency` 0.75, `credentials` 0.46,
  `bumping` 0.44 of decoy occurrences have a real factual hook. Thorough
  over-spotting is a feature, not noise.
- **Under-determined categories** (their spotter-misses ARE the ceiling):
  `tie_breaking` 0.38, `procedural_issues` 0.58 recoverable.

**Implication / pivot:** breadth-from-facts is mostly solved by a cheap 12b model.
The ~10% recoverable tail + the 22% under-determination are the only breadth
headroom, and the latter needs **richer matter facts** (corpus extraction), not a
better arm or model. The bake-off's open game is **DEPTH** (per-issue fact+reasoning
analysis, scored by the E0 depth judge), where retrieval / sweep / divergence have
real leverage. Arms B/C/D get reframed as depth arms: spot (cheap 12b) → retrieve
analogous holdings *with reasoning* → analyze → depth-judge.

## Depth bake-off — does retrieval add depth? (gemma4:12b, RAG vs closed-book)

First foundational depth test: same model, same 25 matter-issues, same E0 depth
judge (0-3 vs the source ALJ's reasoning); only corpus retrieval varies. Paired.

| arm | mean depth (0-3) | dist | sec/issue |
|-----|-----------------:|------|----------:|
| closed-book | **1.52** | {0:1, 1:16, 2:2, 3:6} | 67 |
| RAG (k≈6)   | **1.44** | {0:3, 1:13, 2:4, 3:5} | 73 |

**Paired RAG − closed-book = −0.08** (RAG wins 7 / ties 12 / losses 6) → **no
effect.** Retrieval does not improve depth for gemma4:12b.

**Why — the bottleneck is REASONING, not evidence access.** Both arms sit at
~1.5/3, and the dominant failure mode in BOTH is **inverting the legal
distinction**: the model names the right operative facts but draws the *opposite*
conclusion — e.g. praising a random lottery as the proper tie-break when the ALJ
held a lottery FAILS §44955(b)'s needs-based requirement; arguing a contract's
missing status designation keeps an employee *temporary* when the ALJ held the
omission defaults them to *probationary*. It also fabricated case cites with the
evidence pack in hand. **This is W11 with depth evidence: retrieval is a coverage
amplifier; the depth deficit is a reasoning failure, which coverage can't fix.**

**Caveat — model-ceiling confound (the fork, NOT yet resolved):** one model, and
likely one too weak to USE the evidence (it inverts/confabulates regardless). The
disambiguator is to sweep the analyzer model — a model strong enough to read and
apply the holdings might score higher absolutely AND benefit from retrieval. If
even strong models show RAG≈closed-book, the corpus's value is grounding/
citability (not captured by this recovery metric), not supplying reasoning. **Next:
re-run RAG-vs-closed-book with gemma4:31b, a large local model, and an Opus
reference.** Until then this null is "12b can't convert retrieved law into correct
analysis," not "the corpus doesn't help."

### Model sweep — the ceiling resolves the fork

| model | think | closed-book | RAG | Δ(RAG−cb) | closed-book dist |
|-------|-------|-----------:|----:|----------:|------------------|
| gemma4:12b | OFF | 1.52 | 1.44 | −0.08 | {0:1, 1:16, 2:2, 3:6} |
| gemma4:12b | ON | 1.56 | 1.56 | +0.00 | {0:4, 1:9, 2:6, 3:6} |
| gemma4:31b | OFF | 1.88 | 1.84 | −0.04 | {0:3, 1:8, 2:3, 3:11} |
| gemma4:31b | ON | 1.92 | **2.00** | **+0.08** | {0:1, 1:11, 2:2, 3:11} |
| Opus (ref) | — | **2.36** | 2.48 | +0.12 | {1:7, 2:2, 3:16} |

**Reasoning helps a CAPABLE model use RETRIEVED evidence — not its own
knowledge.** think=ON lifts neither model's *closed-book* depth (12b +0.04, 31b
+0.04). But **31b's RAG arm jumps 1.84 → 2.00 (+0.16)**, and 31b-think is the
**first local config with a positive RAG delta (+0.08)** — reasoning + retrieval
compound once the model is strong enough to reason over the holdings (the 12b
can't: RAG-ON delta +0.00, still inverts). **gemma4:31b + reasoning + RAG = 2.00
is the best privacy-preserving depth** (closes ~57% of the 1.52→2.36 gap;
~6–7 min/issue). This is the base config the W11 verify-repair loop should build on.

**Depth scales with params (think=OFF): 12b 1.52 → 31b 1.88 → Opus 2.36** — unlike
breadth (12b≈31b), bigger genuinely helps depth (31b closes ~43% of the 12b→Opus
gap with reasoning off). So "frontier-bound" is too strong; "capability-bound, and
local scale climbs" is the better read.

**Reasoning (think=ON) did NOT lift the 12b mean (1.52→1.56) — it raised
VARIANCE.** The distribution shifted both ways: 1s→2s (recovers the distinction
more often) AND 1s→0s (more *confidently-wrong* — it reasons elaborately to a wrong
rule). Net flat, at ~3× the wall-clock. Evidence for the **reasoning∝baseline
knowledge** hypothesis from the failure side: a knowledge-poor model's scratchpad
is a coin-flip between surfacing a right rule and entrenching a wrong one. So
think=OFF was not the handicap I feared *for the 12b* — the prediction is that 31b
(more baseline) converts reasoning into net gains; that run is pending.

- **Depth is a MODEL-REASONING gap, not a corpus-access gap.** Opus closed-book
  (2.36/3, recovers the distinction in 16/25) vs gemma4:12b closed-book (1.52, fails
  in 16/25) — a huge gap with **no corpus involved**. Opus got the lottery
  distinction *right* (needs-based criteria; lottery only as residual) where 12b
  *inverted* it. Extends the 05 bakeoff ("no local model matches Opus for legal
  reasoning") to depth-recovery.
- **Retrieval adds little on the recovery metric at EITHER end** (12b −0.08, Opus
  +0.12, both within noise). 12b can't *use* the corpus (inverts regardless); Opus
  doesn't *need* it for common issues (already knows §44915/§44916 from training).
- **BUT the recovery metric is blind to the corpus's real product value —
  GROUNDING.** Opus closed-book "knows" the rule but cites it **from memory**
  (it invoked "Kavanaugh-line authority" — likely confabulated); the RAG arm cites
  **real, checkable corpus holdings** (Plumas (Smith) 2000, Pacific Grove
  (Rasmussen) 2002). The metric scores "did it get the distinction," not "are the
  cites real," so RAG's citability/currency/long-tail value is invisible here.
  **"Retrieval doesn't lift depth-recovery" ≠ "drop the corpus"** — its job is
  grounding + the rare/long-tail issues Opus's training is thin on (Opus's 4 RAG
  wins were exactly such cases, e.g. bumping cb=1→rag=3), not teaching Opus the
  common distinctions it already holds.
- **Caveats:** the Opus arm is judged by an Opus-family judge (possible
  self-preference; mitigated by reference-based grading + a gap to 12b far too
  large for self-preference to explain). n=25 pairs. The metric also slightly
  penalizes valid *divergent* framing (rewards recovering THIS ALJ's distinction).

**Strategic upshot:** depth is **frontier-bound**. Non-privileged use gets ~2.4/3
from Opus today; privileged (local-only) use gets ~1.5/3 from 12b, and the gap is a
*reasoning* gap retrieval cannot close — the W11/W12 problem, now quantified
(target: lift local 1.5 → 2.4). "System over model" WINS on breadth (a tiny model
saturates it) but the depth gap needs reasoning amplification
(orchestration/distillation), not coverage.

## Backend notes

All issue-spotter results are **local** (`ollama:<model>`, `think=False`,
`temperature=0.2`, `num_predict=2048`, structured `format`). `think=False` was
load-bearing — format mode did NOT suppress the reasoning channel for gemma4:31b
or qwen3.6:27b in this ollama version (gemma → JSON-then-thinking "Extra data";
qwen → empty). A free-text `basis` field caused gemma runaway / unterminated JSON
(lesson: 02-taste-judge) and was removed. Baselines (freq-prior/keyword/oracle)
and the metric are deterministic.

## Blocked on full corpus?

No — runs on the merged corpus now. More structured decisions = more eval matters;
re-run picks them up. The recall ceiling is worth measuring directly (how many
missed issues are genuinely unrecoverable from facts) to bound every arm — a small
Opus-judge calibration over the misses.

## Production recommendation

For the issue-spotting step of the main app: **use a small local model
(gemma4:12b), not a large one** — it saturates the metric at ~1/3 the params and
2/3 the wall-clock. This is a query-time/build-time feature of the main app. The
real coverage gains now live in the **system** (arms B/C/D: taxonomy-sweep,
agentic, divergence-adversarial) targeting the ceiling issues
(`tie_breaking`/`procedural`/`bumping`), not in model size. Next: build arm B/D and
test whether retrieval + divergence lifts recall past the bare issue-spotter's
~0.8, and run the recall-ceiling calibration to know how much headroom is real.

---

# W11 eval upgrade — the metrics that see what retrieval/orchestration do (2026-06-18)

The depth **recovery** metric ranks model capability but is blind to grounding,
correctness, and usefulness — exactly what retrieval + W11 change (it kept
reporting "RAG no effect"). So before W11 we built three reference-appropriate
metrics and ran them on the EXISTING think-run analyses (gemma4:12b, gemma4:31b,
Opus — same 25 matter-issues × {closed-book, RAG}), all via blinded Opus judge
panels (judges can't see arm/model). No new GPU.

## 1. Grounding (does the analysis cite REAL, in-evidence corpus holdings?)

`grounding.py` parses prose cites ("District (ALJ), year"), resolves them against
the corpus keyed on **(ALJ surname, year)** — the fields that survive de-id (the
scrubber over-fires on some district names) — and, for RAG, against the
deterministically-reconstructed retrieved set.

| arm | cite-anything | cites/item | resolve→real | within-evidence |
|-----|--------------:|-----------:|-------------:|----------------:|
| closed-book (12b/31b/Opus) | **0%** | 0.0 | — | — |
| RAG gemma4:12b | 28% | 1.04 | 100% | 100% |
| RAG gemma4:31b | 76% | 3.36 | 100% | 100% |
| RAG Opus        | 92% | 4.64 |  99% |  99% |

- **Closed-book grounds in NOTHING** — no model (incl. Opus) can cite these
  obscure, non-precedential OAH holdings from parametric memory. The recon's
  "Opus confabulates plausible cites" prediction was **wrong**: Opus correctly
  knows it doesn't know them, and cites none.
- **RAG flips that to 99–100% real, in-evidence cites** — this is where the
  corpus's value finally shows, made quantitative.
- Grounding exposes a **capability axis recovery missed**: cite-USE scales
  12b→31b→Opus (28→76→92%). The bigger model uses the evidence far more.

## 2. Domain-aware bottom-line outcome (the winner-inference confound, FIXED)

`w11_outcome_judge.js` asks ONE question — *does the district's action STAND?* —
with an explicit anti-inversion rules preamble (e.g. "probationary ⇒ district may
lay off ⇒ district"), and grades the extracted direction against the holding's
structured `prevailing_party`. The OLD confound lived in the judge's
winner-inference, NOT the truth; this pins the mapping so residual misses are real
MODEL errors. Verified on 1999020331 (the canonical confound case).

| model | arm | acc | **resp_acc** (exposure cases) | predicts d/r |
|-------|-----|----:|------------------------------:|-------------:|
| 12b  | closed-book | 68% | 57% | 16/9 |
| 12b  | RAG | 72% | **29%** | 21/4 |
| 31b  | closed-book | 60% | 43% | 16/9 |
| 31b  | RAG | 76% | 43% | 20/5 |
| Opus | closed-book | **76%** | **86%** | 14/11 |
| Opus | RAG | 64% | **29%** | 18/6 |
| *baseline* | always-district | 72% | 0% | — |

**The headline finding: naive RAG is net-negative on the bottom line for EVERY
model — worst for Opus.** Opus closed-book nails 86% of exposure cases from its
own doctrine; the 79%-district-skewed retrieved evidence drags it to 29% and drops
overall 76→64%. The district-bias is a **retrieval-skew problem, not a small-model
capability gap** — RAG grounds the cites but pattern-matches the majority class on
direction. (Caveat: resp_acc rests on n=7 respondent-win matter-issues — direction
consistent across all 3 models + mechanistically explained, but Step 2b's
expansion is what makes it robust.)

## 3. Usefulness panel (reference-free; litigator + skeptic lenses, 1–5)

`w11_usefulness_judge.js`, blind to arm.

| model | arm | issue_grasp | respondent_args | actionability | soundness | **overall** |
|-------|-----|------------:|----------------:|--------------:|----------:|------------:|
| 12b  | closed-book | 2.10 | 1.70 | 1.90 | 1.64 | 1.72 |
| 12b  | RAG | 2.04 | 1.54 | 1.86 | 1.46 | 1.68 |
| 31b  | closed-book | 2.54 | 1.78 | 2.16 | 1.80 | 1.90 |
| 31b  | RAG | 2.62 | 1.86 | 2.10 | 1.90 | 1.92 |
| Opus | closed-book | 3.96 | 2.64 | 2.98 | 3.14 | **3.10** |
| Opus | RAG | 3.92 | 2.78 | 3.12 | 2.94 | 3.02 |

- Clear capability ladder (1.7→1.9→**3.1**); the local→Opus gap is the W11 target.
- **Naive RAG is neutral-to-negative on usefulness at EVERY level** (even Opus:
  3.10→3.02, loses 11/25 pairs). The corpus's value is currently *unrealized* by
  naive retrieval.
- **`respondent_args` is the weakest dim at every level** (even Opus 2.64) —
  exposure-blindness is universal.

## 4. Failure-mode dissection (what W11 verify-repair must catch)

Mining the judges' `weak_or_wrong` flags (local analyses; ~90% scored soundness ≤2):

| failure mode | closed-book | RAG | RAG effect |
|--------------|------------:|----:|-----------|
| inversion (doctrine stated backwards) | 99 | 98 | unfixed |
| confabulated/mischaracterized authority | 150 | **204** | **worse** |
| wrong statute/test | 43 | **24** | RAG helps |
| ignores respondent/exposure | 30 | 30 | unfixed |
| conclusory/unsupported | 24 | 25 | unfixed |

RAG **helps** find the right framework (43→24) and grounds cite *identity*, but
leaves **inversions** untouched and **worsens authority confabulation** (more cites
= more chances to misstate a holding's *content*). Grounding a cite's identity ≠
faithful use of its content.

## Unified thesis + W11 design

**Naive RAG buys grounding (cite identity) but NOT usefulness, correctness, or
soundness — and actively HURTS exposure-case accuracy and authority-faithfulness,
at every capability level including Opus.** The bottleneck is the SYSTEM, not the
corpus or raw model reasoning. W11 verify-repair, in priority order (each maps to
an unfixed-by-RAG failure mode):
1. **Directional/inversion check** — verify each doctrine's direction against the
   retrieved holdings' real `prevailing_party` (the #1 mode; maps to exposure misses).
2. **Cite-faithfulness check** — verify a cited holding actually stands for what
   the analysis claims (its `reasoning.summary`/`prevailing_party`), not just that
   it resolves.
3. **Exposure injection** — balanced retrieval + a respondent's-counsel lens.

Falsifiable W11 win conditions: lift 31b usefulness 1.9→toward Opus 3.1, and —
the stark "system over model" result — make an orchestrated 31b BEAT *naive
Opus-RAG* on bottom-line/exposure accuracy (Opus-RAG is only 64%/29%).

## Tooling (all in exp-bakeoff/)
- `grounding.py` + `grounding_eval.py` (--tag) — pure Python, instant.
- `usefulness_prep.py` (blinded, multi-tag pooling) + `w11_usefulness_judge.js` + `usefulness_eval.py`.
- `outcome_prep.py` + `w11_outcome_judge.js` + `outcome_eval.py`.
- Results: `output/runs/{depth,useful,outcome}.<tag>.{input,key,scored,grounding,keymap,meta}.json`.

---

# Step 1 base-model selection — qwen3.5:35b vs gemma4:31b (2026-06-18)

Ran the full 4-metric profile on **qwen3.5:35b** (think=ON, same 25 matter-issues),
to test a second model family (only gemma4 had been depth-tested). Result is NOT a
clean winner — the two are **complementary**, which reframes W11.

| metric | gemma4:31b | qwen3.5:35b | Opus | read |
|--------|-----------:|------------:|-----:|------|
| recovery cb / RAG | 1.92 / **2.00** | 1.92 / 1.76 | 2.36 / 2.48 | gemma RAG *compounds*, qwen RAG *degrades* |
| grounding RAG (cite% / n) | **76% / 3.36** | 68% / 2.88 | 92% / 4.64 | gemma uses evidence more |
| outcome cb (acc / resp_acc) | 60% / 43% | **80% / 86%** | 76% / 86% | **qwen cb = Opus-level direction** |
| outcome RAG (acc / resp_acc) | 76% / 43% | 72% / 43% | 64% / 29% | naive RAG craters exposure for ALL |
| usefulness cb / RAG (overall) | 1.90 / 1.92 | 1.58 / **1.86** | 3.10 / 3.02 | qwen RAG **+0.28** (only positive local) |
| usefulness soundness cb | 1.80 | **1.12** | 3.14 | qwen cb confabulates heavily |
| wall-clock | ~390 s/matter | **~195 s/matter** | (cloud) | qwen ~2× faster |

**The two base models have opposite profiles:**
- **gemma4:31b** — *integrates evidence* well (grounding 76%, recovery RAG compounds
  +0.08) but weak *innate direction* (cb exposure 43%).
- **qwen3.5:35b** — *Opus-level closed-book direction* (cb 80%/86% — best local by far,
  matches Opus on exposure) but confabulation-prone (cb soundness 1.12) and uses
  retrieval worse (grounding 68%, recovery RAG −0.16). Its RAG *fixes confabulation*
  (usefulness +0.28) while *corrupting direction* (outcome exposure 86%→43%). 2× faster.

**Implication for W11:** qwen3.5:35b is arguably the BETTER base — it already has the
hard part (legal direction, the thing naive RAG destroys), so the system's job is to
PRESERVE it (directional verify) while adding grounding WITHOUT skew (balanced
retrieval) — exactly the W11 design. gemma would need the system to CREATE direction
(harder). Decision: **run the model-agnostic W11 harness on BOTH bases** — qwen3.5:35b
is the sharpest "system over model" test (cb 86% exposure → naive-RAG 43% → can the
system restore it?).

**122b ceiling probe (n=8 matter-issue subset, think=ON):** scale within the qwen
family substantially closes the gap to Opus AND fixes the 35b's RAG-degradation.

| metric (RAG arm) | qwen3.5:35b | gemma4:31b | **qwen3.5:122b** | Opus |
|------------------|------------:|-----------:|-----------------:|-----:|
| recovery cb / RAG | 1.92 / 1.76 | 1.92 / 2.00 | 2.12 / **2.38** | 2.36 / 2.48 |
| recovery RAG Δ | −0.16 | +0.08 | **+0.25** | +0.12 |
| grounding (cite% / n) | 68% / 2.88 | 76% / 3.36 | **88% / 4.1** | 92% / 4.64 |
| usefulness cb / RAG | 1.58 / 1.86 | 1.90 / 1.92 | 1.81 / **2.31** | 3.10 / 3.02 |
| usefulness RAG Δ | +0.28 | +0.02 | **+0.50** | −0.08 |

**The 122b is the only LOCAL model whose RAG compounds positively on BOTH recovery
(+0.25) and usefulness (+0.50)** — it USES retrieval like Opus does (the 35b degrades,
gemma is flat). On recovery (RAG 2.38) and grounding (88%) it approaches Opus; on
usefulness (RAG 2.31) it leads all locals but trails Opus (3.02). Caveats: n=8 subset
(noisy); OUTCOME could not be measured (only 2 respondent-win MIs in the subset →
resp_acc 1/2); still confabulates (cb soundness 1.31; invented a "Garcia" cite + a
hallucinated party name "Payne" — de-id held, the model only ever saw `[name]`, but it
fabricated a surname). SLOW: ~3 min/call (~49 min for 8 MIs → ~2.5 h for a full 25).

**Stall diagnosis CORRECTED:** the earlier 122b stall (GPU 3%, 0 matters) was NOT
think=ON / num_predict — it was the **three concurrent judge workflows (~200 agents)
disrupting the local run**. Re-run ISOLATED, the 122b generated at 98% GPU, clean (0
errors). Lesson: don't fan out big parallel workflows while a GPU job grinds under load
(>90%); GPU-free, hundreds of agents are fine. Also: 3 concurrent judge workflows hit a
server-side rate limit — run judge workflows ONE AT A TIME under GPU load.

**Base-model picture, now 3-way:** qwen3.5:35b = best closed-book DIRECTION (outcome
86% exposure), fast, but RAG degrades it; gemma4:31b = decent evidence-integration,
weak direction; qwen3.5:122b = best evidence-USE (RAG compounds like Opus, grounding
88%, near-Opus recovery) but slow (~2.5 h/eval) + outcome unmeasured + still confabulates.
For W11: 35b/31b are the fast iteration bases; 122b is the "local ceiling" config that
best exploits the balanced-retrieval the system will feed it.

---

# W11 build — Step 3 (2026-06-18). Base: qwen3.5:35b, current eval (n=7 exposure)

W11 = the orchestration layer that should convert naive RAG (grounds cites but
amplifies the district-win skew → craters exposure accuracy) into grounded,
correctly-directed analysis. Built on **balanced retrieval** (50/50 district/respondent).

## v1: balanced-RAG draft → corpus-grounded verify → repair. FALSIFIED (over-corrects).

| qwen3.5:35b | overall acc | resp_acc (exposure) | predicts d/r |
|-------------|------------:|--------------------:|-------------:|
| closed-book | 80% | 86% | 15/10 |
| naive UNBALANCED RAG | 72% | 43% | 19/5 |
| **W11 balanced draft** (rag arm) | 68% | **57%** | 15/9 |
| **W11 verify-repair** (w11 arm) | **24%** | 29% | **9/16** |

- **Balanced retrieval alone VALIDATED (mildly):** lifts exposure 43%→57% vs naive RAG
  (shifts predictions district→respondent 19/5→15/9), small overall cost (72%→68%).
- **The verify-repair loop OVER-CORRECTS — FALSIFIED:** it WRONGLY flipped **14 of 18
  district-truth cases** to respondent; overall acc collapses to 24%, predictions 9/16.
  Root cause = an **asymmetric verify** (one-directional "did you miss the respondent's
  case?" critic). With balanced evidence there is ALWAYS a respondent-win holding to
  cite, so the verify is a de-facto respondent advocate and the repair dutifully flips
  every draft. It replaced district-bias with a worse respondent-bias.
- **Infra lesson (load-bearing):** reasoning-heavy VERIFY/audit tasks return EMPTY under
  think=ON (CoT starvation — qwen3.5:35b verify think=ON → 0 chars/140s; think=OFF →
  5.8k chars/24s). Use think=OFF for verify/critique/judge steps (the reasoning IS the
  output) + a num_predict cap. (Draft analysis is fine think=ON.)
- Grounding: repair cut cite breadth (rag 68%/2.76 → w11 52%/2.08) but kept 100%
  resolved/in-evidence (no new confabulation). Recovery (partial, rate-limited 39/50):
  repair lowered recovery too (diverges from the ALJ's framing while over-arguing).

## v2: adversarial proceeding (symmetric BY CONSTRUCTION). IN PROGRESS.

Nick's redesign: simulate the OAH hearing — (1) DISTRICT counsel argues the District's
best good-faith case (grounded/quoting the RAG holdings), (2) RESPONDENT counsel argues
the employee's, (3) a neutral ALJ JUDGE reads facts + RAG pack + both briefs and writes
the decision, weighing both sides. Score the judge's opinion. This removes v1's
asymmetry structurally (both sides advocate; the judge balances). All local, think=OFF.
Arm 'judge'. `arms/adversarial.py` + `run_adversarial.py`.

### v2 RESULTS (adversarial, qwen3.5:35b, n=7 exposure) — best SYSTEM so far, but doesn't beat closed-book.

qwen3.5:35b OUTCOME + USEFULNESS ladder:

| config | out acc | resp_acc | useful overall | soundness | respondent_args |
|--------|--------:|---------:|---------------:|----------:|----------------:|
| closed-book | **80%** | **86%** | 1.58 | 1.12 | 1.72 |
| naive UNBAL RAG | 72% | 43% | **1.86** | 1.46 | 1.70 |
| balanced draft | 68% | 57% | — | — | — |
| v1 verify-repair | 24% | 29% | — | — | — |
| **v2 adversarial** | 60% | **71%** | 1.72 | 1.32 | **2.18** |

- **v2 fixes v1's overshoot** (preds 12/13 vs 9/16) and **restores exposure recall to 71%**
  (catches 5/7; naive RAG 43%), and **`respondent_args` 2.18 = highest of any qwen config**
  (the adversarial structure's intended win — both sides get argued).
- **BUT it doesn't beat qwen CLOSED-BOOK** on outcome (60% vs 80%; it leans respondent — the
  persuasive respondent brief pulls the judge) or usefulness (1.72 vs naive-RAG 1.86).
- **Soundness CRATERS to 1.32:** qwen's confabulation (its known cb weakness, soundness 1.12)
  is AMPLIFIED by the "cite heavily" advocacy framing — advocates invent fake *published-case*
  captions ("District v. Name (2009)"; several post-date a 1998 matter) the judge then relies on.
  GROUNDING METRIC BLIND SPOT: it only parses corpus "(ALJ), year" cites (28%/1.2, 100% real
  here), NOT the "X v. Y" published-case confabulation stream (~19 instances across 4/25 opinions).

**Diagnosis → v3 directions:** (1) constrain advocates to cite ONLY the provided RAG holdings
(kill the published-case confab); (2) anchor the JUDGE to the strong closed-book prior (or base
rate) so a persuasive brief can't flip a correct direction. **Deeper pattern (load-bearing):**
for a base with strong latent direction (qwen cb 86%), the corpus's value is GROUNDING, not
direction — v1/v2 that re-derive direction underperform the bare prior. The winning system likely
ANCHORS on closed-book + adds grounding/exposure as an overlay, not re-litigates from scratch.

### v3 RESULTS (RAG-only advocates + closed-book-anchored judge, qwen3.5:35b). Grounding WIN; soundness ceiling holds.

qwen3.5:35b FULL ladder (outcome | usefulness | grounding):

| config | out_acc | resp_acc | useful | soundness | resp_args | grounding cite% |
|--------|--------:|---------:|-------:|----------:|----------:|----------------:|
| closed-book | **80%** | **86%** | 1.58 | 1.12 | 1.72 | 0% |
| naive UNBAL RAG | 72% | 43% | **1.86** | 1.46 | 1.70 | 68% |
| v2 adversarial | 60% | 71% | 1.72 | 1.32 | **2.18** | 28% |
| **v3 anchored** | 72% | 57% | 1.72 | 1.24 | 2.14 | **96%** |
| Opus (cb / RAG) | 76/64 | 86/29 | 3.10 | 3.14 | 2.64 | 92% |

- The 2 fixes hit their targets: RAG-only advocates → **0 confabulated briefs + grounding 96%/4.04**
  (near-Opus); anchor → **overall acc 60%→72%** (preds 17/8, vs v2 12/13). Anchor TRADED exposure
  for overall: resp_acc 71%→57% (still > naive-RAG 43%, < closed-book 86%).
- **BUT soundness stayed ~1.24** — the judge stopped inventing fake CASES but now MISATTRIBUTES
  propositions to REAL in-corpus holdings (cites e.g. "(Sampogna), 2025" — a real 2018-25 holding
  the balanced retrieval surfaced — for a 1999 matter). Grounding scores it 100% RESOLVED; the
  usefulness judges catch it as unsound. **The cite-faithfulness blind spot, live.** (Residual: the
  JUDGE prompt lacks the advocates' RAG-only rule → 10 stray "X v. Y" captions across 25; easy v3.1 fix.)

**Honest verdict after v1/v2/v3:** the SYSTEM wins decisively on **grounding (0→96%)** and
**respondent-engagement (1.7→2.18)** — real product-relevant gains. But **no orchestration beats
qwen CLOSED-BOOK on outcome (80%/86%) or naive-RAG on overall usefulness (1.86).** The binding
constraint MIGRATED: coverage solved → direction is the base's strength → now **soundness /
trustworthiness is the ceiling, set by qwen's confabulation (~1.3 floor regardless of system).**
For a litigator-trustable product, soundness is the dealbreaker and qwen can't clear it. → two
complementary levers: **v4 rule-distillation** (attacks pattern-matching + confab at the root) and
**a sounder base** (gemma4:31b soundness 1.80 / 122b) on the same adversarial/anchored design.

### v4 RESULTS — rule-distillation / PRESENTATION diagnostic (qwen3.5:35b). HYPOTHESIS SUPPORTED.

Nick's hypothesis: models soft-nearest-neighbor VOTE on the retrieved cases' outcomes rather
than deriving + applying the rule → the lever is PRESENTATION. Distill (gemma4:12b) the
balanced RAG pack into RULE:/APPLICATION: doctrine, analyze (qwen3.5:35b) under 3 framings.

| framing | out_acc | resp_acc | pred d/r | grounding cite% |
|---------|--------:|---------:|---------:|----------------:|
| (a) raw cases | 72% | **43%** | 18/6 | 48% |
| (b) rules + example | 68% | **71%** | 14/9 | 4% |
| (c) rules-only | **72%** | **71%** | 15/10 | 0% |
| *closed-book ref* | 80% | 86% | 15/10 | 0% |

- **Reasoning from RULES ~doubles exposure accuracy (43%→71%)** — catches 5/7 respondent-win
  cases vs raw's 3/7 — and it shows in BOTH rule framings (not noise). Prediction distribution
  shifts raw 18/6 → (c) **15/10 = identical to closed-book** — rule-presentation pulls qwen off
  the nearest-neighbor vote back toward fact-driven direction. **Direct support for the
  pattern-matching hypothesis** (the matching mechanism is presentation, not just example mix).
- **Does the example help or PRESERVE the pull? → it slightly preserves it.** (c) rules-only beats
  (b) rules+example on overall acc (72% vs 68%) + truth-closer preds (15/10 vs 14/9). The worked
  APPLICATION outcome nudges qwen back toward matching; the pure rule gives cleanest direction.
  (n=7 exposure — consistent, not yet precise.)
- **Tradeoff = GROUNDING:** rule-framing nearly eliminates case cites (raw 48% → rulesex 4% →
  rulesonly 0%) — the analyzer reasons from abstracted rules, doesn't point at cases. → v5 HYBRID:
  reason from rules (direction) BUT retain the case cites (grounding). [usefulness/soundness pending]

**v4 usefulness/soundness by framing** (does rule-presentation lift the soundness ceiling? NO):

| framing | resp_args | soundness | useful overall |
|---------|----------:|----------:|---------------:|
| (a) raw cases | 1.86 | **1.46** | **1.76** |
| (b) rules + example | 1.62 | 1.40 | 1.70 |
| (c) rules-only | 1.74 | 1.30 | 1.58 |

**v4 VERDICT — two independent constraints, two independent fixes (the arc resolves):**
- **DIRECTION (pattern-matching pull) → FIXED by rule-presentation** (exposure 43%→71%). Confirmed.
- **SOUNDNESS (confabulation) → NOT a presentation artifact; it is qwen's BASE-MODEL floor.** qwen
  confabulates case cites whether handed cases OR rules (the framing prompt asks it to cite; rules-only,
  with no real cites to anchor, just invents them → WORST soundness 1.30). No system/presentation on
  qwen lifts this. Needs a SOUNDER BASE (gemma4:31b soundness 1.80, vs qwen 1.12).
- The two levers are ORTHOGONAL + COMPOSABLE → **v5 = rule-presentation on a sounder base (gemma4:31b)**
  = the configuration with a shot at clearing BOTH direction + soundness at once. Plus a v5 grounding
  fix: a HYBRID framing (reason from rules, but keep the real case cites) so direction doesn't cost
  grounding (rules-only = 0% cites). [And: for a true rules-only test, drop the "cite cases" instruction
  so it isn't forced to confabulate.]
