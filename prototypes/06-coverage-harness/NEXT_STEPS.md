# 06 coverage-harness — RESUME HERE (as of 2026-06-18, eval upgrade done)

Authoritative go-forward + state. Read this + `exp-bakeoff/FINDINGS.md` (the W11
eval-upgrade section) + the STATUS row before resuming. Merged corpus:
`export CORPUS_ROOT=/home/nick/Projects/cert_layoff_merged`.

## Where we are (one paragraph)

E0 scoreboard validated; E1 established breadth solved by a cheap 12b, depth
capability-bound. The depth **recovery** metric ranks capability but is blind to
what retrieval/W11 change. So we built **three reference-appropriate metrics**
(grounding, domain-aware outcome, reference-free usefulness) and ran them on the
existing think-runs (12b/31b/Opus × closed-book/RAG) via blinded Opus panels.
**Unified result: naive RAG buys grounding (real cites) but NOT usefulness,
correctness, or soundness — and HURTS exposure-case accuracy + authority-
faithfulness at EVERY level, including Opus.** The bottleneck is the SYSTEM, not
the corpus or raw reasoning. This is the empirical green light for W11.

## Step 2a RESULTS — DONE (2026-06-18). Numbers in FINDINGS; the load-bearing ones:

- **Grounding** (RAG cite-anything / resolve-to-real): 12b 28%/100%, 31b 76%/100%,
  Opus 92%/99%. Closed-book = 0% for ALL (incl. Opus — it can't cite these obscure
  non-precedential holdings from memory). RAG grounding is the corpus's value, made
  quantitative; cite-USE scales with capability.
- **Outcome** (domain-aware "does district action stand?", graded vs structured
  `prevailing_party`; confound FIXED): **naive RAG is net-negative for every model**.
  Opus closed-book 76% acc / **86% resp_acc** → Opus RAG 64% / **29%**. The
  79%-district-skewed evidence drags even Opus toward the majority class. District-
  bias = retrieval-skew problem, not a small-model gap. (resp_acc on n=7 resp-win
  matter-issues — direction robust, magnitude needs 2b.)
- **Usefulness** (litigator+skeptic, 1–5 overall): 12b 1.7, 31b 1.9, **Opus 3.1**.
  Naive RAG neutral-to-negative at every level (even Opus 3.10→3.02). `respondent_args`
  weakest dim everywhere (Opus 2.64) — exposure-blindness universal.
- **Failure modes** (unfixed by RAG): inversions (~98), exposure-blindness (30),
  conclusory (24). RAG *worsens* authority confabulation (150→204), *helps* right
  statute (43→24). Grounding cite IDENTITY ≠ faithful use of cite CONTENT.

## THE PLAN (execute in order)

### Step 1 — base-model selection — DONE (2026-06-18)
qwen3.5:35b ran the full 4-metric profile (see FINDINGS Step 1). **Result: the two
bases are COMPLEMENTARY, not a clean winner.** gemma4:31b integrates evidence well
(grounding 76%, recovery RAG +0.08) but weak innate direction (cb exposure 43%).
qwen3.5:35b has **Opus-level closed-book direction (cb 80%/86% exposure)** but
confabulation-prone (cb soundness 1.12) and uses retrieval worse (grounding 68%,
recovery RAG −0.16); RAG fixes its confab (usefulness +0.28) but corrupts direction
(exposure 86%→43%); 2× faster. **→ run the model-agnostic W11 harness on BOTH bases;
qwen3.5:35b is the sharpest "system over model" test (cb 86% → naive-RAG 43% → can
the system restore it?).** **122b ceiling DONE (n=8 subset, think=ON):** scale closes
the gap to Opus AND fixes the 35b's RAG-degradation — recovery RAG 2.38 (Δ+0.25),
grounding 88%, usefulness RAG 2.31 (Δ+0.50) = **only local that RAG-compounds on both
like Opus**; but slow (~2.5h/full eval), outcome unmeasured (subset had 2 resp-win MIs),
still confabulates (cb soundness 1.31). → 122b = the "local ceiling" W11 config; 35b/31b
= fast iteration bases. **The earlier 122b stall was workflow-interference, NOT think/np**
(isolated it ran 98% GPU clean) — see [[workflow-fanout-can-break-local-runs]]: don't
fan out big workflows while GPU >90% load; GPU-free is fine.

### Step 2 — eval upgrade — METRICS DONE (2a). Remaining: **2b expansion**
2a (grounding/outcome/usefulness) is built + run. 2b = thicken the respondent-win
("exposure") slice, which is the highest-value + currently only n=7.
- **SIMPLIFIED (corrected the recon):** the current depth run only used 12 of the
  36 selected zero-leak matters with issues capped at 3 — so most respondent-wins in
  ALREADY-VETTED, ALREADY-STRATIFIED matters were left on the table. Just re-run the
  **full 36-matter set, all recoverable issues, no cap** → **~24 respondent-win**
  (era-balanced 8/10/6) + ~70 district-win, ZERO new selection/leak/ceiling work,
  12/12/12 era stratification preserved. Hits the n→~25 target. Do NOT pull from the
  unselected pool (63/71 of its resp-wins sit in 2004-2009 → era skew, no benefit).
- Mechanics: `run_depth.py --n 36 --max-issues 6` (verify recoverable_map covers all
  36 via ceiling_scored). Run on the chosen base + Opus (subagent) + gemma4:31b ref.
  Then re-score all 4 metrics on the expanded set. Report `resp_acc` separately so
  the 72% majority class doesn't dominate the headline. (Default — proceed unless Nick
  wants 50/50 down-sampling or a bigger resp push via unselected 2004-2009 matters.)

### Step 3 — W11 (IN PROGRESS on qwen3.5:35b, current eval). See FINDINGS "W11 build".
Base finding so far: **balanced retrieval** (`retrieve(balanced=True)`) alone helps
exposure (resp_acc 43%→57%). All W11 designs build on it. Two designs tried:
- **v1 verify-repair (FALSIFIED):** draft → corpus-grounded verify → repair. The
  one-directional verify ("did you miss the respondent's case?") OVER-CORRECTS — flips
  14/18 district-truth cases to respondent, overall acc 24%. Asymmetric critic + balanced
  evidence = de-facto respondent advocate. `arms/w11.py` (kept for the record).
- **v2 adversarial proceeding (Nick's redesign, DONE):** symmetric BY CONSTRUCTION —
  DISTRICT brief + RESPONDENT brief (each advocates hard but ethically, grounded in RAG) →
  neutral ALJ JUDGE weighs both + record → decision (arm 'judge'). `arms/adversarial.py`.
  Result: BEST SYSTEM so far — fixes v1's overshoot (preds 12/13), restores exposure
  recall (resp_acc 71%), `respondent_args` 2.18 (highest). BUT doesn't beat qwen
  CLOSED-BOOK (out 60% vs 80%; leans respondent — persuasive briefs pull the judge) and
  soundness CRATERS to 1.32 (qwen confabulates fake "X v. Y" published cases under the
  "cite heavily" advocacy framing).
- **v3 (RUNNING) = Nick's 2 targeted fixes to v2:** (1) advocates may cite ONLY the
  provided RAG holdings + Ed.Code §§ (kills published-case confab — smoke confirmed 0 fake
  captions); (2) JUDGE anchored to qwen's validated CLOSED-BOOK prediction (the 80%/86%
  prior, reused from depth.qwen3.5-35b.think) + base rate, deviating only if facts+a
  closely-analogous holding compel (fixes the respondent-lean). `run_adversarial.py
  --anchor-tag qwen3.5-35b.think` → tag `adv3-…`, arm 'judge'. Judge one workflow at a time.
**Deeper pattern (load-bearing):** for a base with strong latent direction (qwen cb 86%),
the corpus's value is GROUNDING not direction — v1/v2 that re-derive direction underperform
the bare prior; v3 anchors on it. **Falsifiable win:** v3 keeps cb's ~80%/86% AND adds
grounding+exposure usefulness, beating naive-RAG (1.86) and naive Opus-RAG (64%/29%).

### Step 3 → v4 (QUEUED after v3, Nick's idea): rule-distillation / PRESENTATION transform
**Hypothesis (strongly data-supported — see STATUS lesson "RAG examples act as
outcome-votes"):** models treat retrieved cases as few-shot exemplars and soft
nearest-neighbor VOTE on the outcome distribution rather than deriving + applying the rule.
So the lever may be PRESENTATION, not example mix. v4 = a cheap **rule_distill pre-pass**
(gemma4:12b, fast) converting the balanced RAG pack into issue doctrine, format **"The rule
is X; applied to facts like Y, the result is Z (cite)"** (rule + worked illustration =
treatise/Restatement style — preserves fact-sensitivity). Feed RULES instead of raw cases;
plugs into ANY design (incl. adversarial: distill → advocates argue from rules → judge).
**3-framing diagnostic** (facts fixed): (a) raw cases [current pattern-match baseline],
(b) rules+example illustration, (c) rules-only (outcomes stripped). Open Q: does (b) help
(human intuition) or does the example PRESERVE the nearest-neighbor pull? Predict (c) best
direction/worst grounding; (b) sweet spot IF the example is subordinated to the rule
(illustration, not case-to-match). Caveats: distill call can confabulate the rule (ground
tightly in provided holdings + verify cites); captures the corpus's UNIQUE value (OAH
application nuance closed-book lacks — NOT generic law). Product implication: if it works, corpus
runtime role shrinks to BUILD-TIME rule-pack manufacture (cheaper, privacy-cleaner).
**BUILT + RUNNING (2026-06-18):** `arms/rule_distill.py` (gemma4:12b distiller, RULE:/
APPLICATION: format, rules_only strips APPLICATION lines) + `run_framing.py` (TWO-pass:
distill all on gemma, then analyze all 3 framings on qwen — avoids 23GB model thrash; arms
raw/rulesex/rulesonly). Smoke clean (distiller derives real operative rules + cites). Full
run `frame-qwen3.5-35b`. **v4 DONE (see FINDINGS v4 RESULTS):** rule-presentation FIXES
DIRECTION (exposure resp_acc raw 43% → rules 71%; preds raw 18/6 → rulesonly 15/10 =
closed-book's; (b) example slightly preserves the pull, (c) rules-only cleanest) — Nick's
pattern-match hypothesis CONFIRMED. But rule-presentation does NOT fix SOUNDNESS (raw 1.46 →
rulesonly 1.30) + KILLS grounding (cites 48%→0%): qwen confabulates cites whether given cases
OR rules → **the soundness/confab ceiling is the BASE MODEL's, not presentation.**

### → v5 (THE convergence — QUEUED): rule-presentation ON A SOUNDER BASE + grounding hybrid
Two ORTHOGONAL, COMPOSABLE constraints proven across v1-v4: **DIRECTION** (pattern-match pull)
→ fixed by rule-presentation; **SOUNDNESS** (confab) → base-model floor, needs a sounder base.
v5 = run the framing (or rules→adversarial) design on **gemma4:31b** (soundness 1.80 vs qwen
1.12) — shot at clearing BOTH bars at once; then 122b. Plus **grounding HYBRID**: present rules
FOR REASONING + keep the real case cites FOR GROUNDING (so direction doesn't cost grounding,
rules-only=0% cites); and for a clean rules-only test, DROP the "cite cases" instruction so it
isn't forced to confabulate. `run_framing.py --analyzer gemma4:31b`. Later: cite-faithfulness
check; static rule-packs; corpus-as-build-time-rule-factory product shape.

## Key methodological notes (don't relearn these)
- **De-id mangles district names** in saved analyses ([name]) but ALJ surname+year
  survive → grounding resolves on (alj, year). Cloud judges OK on public OAH data
  with scrub; PRODUCT stays fully local.
- **SCRUB GAP (harness TODO):** roster de-id anonymizes the named respondents
  (R1/R2…) but a COMPARATOR employee mentioned in passing (a non-roster surname
  appearing in one decision's prose) is NOT in the roster, and `scrub_external`'s best-effort pass misses a
  standalone surname → it can reach the cloud judge. Within eval policy (public OAH +
  best-effort, PRODUCT local), and never committed (FINDINGS uses District(ALJ)/R-anon
  only), but strengthen `harness.deid` to catch non-roster comparator names. Reinforces
  why product stays on-box.
- **think=OFF for verify/critique/JUDGE/advocate roles** — think=ON starves these
  reasoning-heavy tasks to EMPTY (CoT eats num_predict). Draft/analysis is fine think=ON.
- **GROUNDING METRIC BLIND SPOT:** parses only corpus "District (ALJ), year" cites, NOT
  "Name v. Name (year)" published-case confabulation (qwen invents these under advocacy).
  A high corpus-grounding score ≠ no confabulation; the usefulness soundness dim catches it.
- **Winner-inference confound is FIXED** in the outcome judge (explicit anti-inversion
  rules + grade vs structured prevailing_party). Residual misses are real model errors.
- **Blinding**: usefulness/outcome judges see opaque codes (U###/O###), never arm/model.
- **resp_acc is on n=7 resp-win matter-issues** until 2b — trust direction, not magnitude.
- Recovery metric: fine for capability ranking, WRONG as the product/W11 target.

## File map
- arms: `exp-bakeoff/arms/{issue_spotter,depth_analyzer,retrieval}.py`.
- drivers: `run_depth.py` (local), `run_depth_opus.py` (Opus subagent prep/merge).
- 2a metrics: `grounding.py`+`grounding_eval.py`; `usefulness_prep.py`+`w11_usefulness_judge.js`+`usefulness_eval.py`; `outcome_prep.py`+`w11_outcome_judge.js`+`outcome_eval.py`; `depth_recovery_judge.js`.
- results: `exp-bakeoff/output/runs/{depth,useful,outcome}.<tag>.{input,key,scored,grounding,keymap,meta}.json`.
