# 06 coverage-harness — RUN PLAN (the grind)

Executable, beam-search experiment queue for the weekend grind. This is the
**operational** doc; design rationale lives in `EXPERIMENTS_BRAINSTORM.md`,
historical state in `NEXT_STEPS.md`, scoring in `exp-bakeoff/FINDINGS.md`.
Merged corpus: `export CORPUS_ROOT=/home/nick/Projects/cert_layoff_merged`.

## North star (settled)
Insight is the product (risk-memo / matter workbench, P1). 06 picks the LOCAL
analysis-engine architecture under privilege ("beat Opus" = match cloud-Opus on-box,
the ship/no-ship gate). **Outcome/exposure accuracy = anchored PROXY for trustworthy
insight**, not a prediction product; ALJ-fallibility caps it <100%, accept the fuzz.

---

## OPERATIONAL CORE — read before running anything

**Serialization (the load-bearing constraint).** Local generation is GPU-bound and
must be serial; Opus judge fan-out is cloud and MUST NOT run while the GPU is hot
(breaks local runs — see [[workflow-fanout-can-break-local-runs]]). The loop is:
```
for each config:  generate (GPU, serial, OLLAMA_NUM_PARALLEL=1 for big models)
                  → GPU idle → judge fan-out (Opus subagents) → score → checkpoint
```
Never start the next generation while judges are fanning out. Cluster 122b runs
(~2.5h/eval) overnight. **First action every session: `gpu_status()` / `ollama ps`.**

**Scoring funnel (protects the judge budget).**
- FREE / deterministic, run on EVERY config: breadth, grounding (cite-resolution),
  **cite-faithfulness** (new — build in Phase 0), cost.
- CHEAP Opus, run on every config: outcome-direction extractor → resp_acc vs real
  `prevailing_party`.
- EXPENSIVE Opus panel, run only on PROMOTED configs: usefulness (litigator+skeptic).
- **Cheap-screen gate:** a config advances to the usefulness panel only if it beats
  `CURRENT BEST` on **resp_acc AND grounding** (or ties resp_acc with higher grounding).
  Everything else dies cheap, logged, not judged.

**Beam search, not grid.** Fix each axis's winner, carry forward. Re-toggle a dropped
component only at a suspected interaction (noted per phase). Every scaffold must beat
the **raw-compute reference** (122b cb max-thinking) to justify its existence — the
bitter-lesson check, enforced as a baseline column, not a late experiment.

---

## Config-space axes
| Axis | Values (→ = ladder) |
|---|---|
| **BASE** | gemma4:31b (system base — sound) · qwen3.5:35b (bar: cb 86% direction) · qwen3.5:122b (local ceiling) · Opus (frontier ref) |
| **ARTIFACT** | raw-cases → rule-list → rule+comment → treatise-chapter (all from BALANCED retrieval, cites carried) |
| **DECOMPOSITION** | off (use existing extraction fields) · on (induced typed features, build-time) · faceted-retrieval |
| **TOPOLOGY** | single-pass → appellate-exchange · inquisitorial-judge · panel+aggregator · verify-cascade · 2-model-routing |
| **ANCHOR** | off · on (anchored to cb prior) |

**Beam state (update as we grind):**
> CURRENT BEST CONFIG: _(Phase 0 baseline TBD)_
> CURRENT BEST resp_acc / grounding / usefulness: _TBD_

---

## PHASES (0–1 detailed; 2–5 depend on winners — kept light per SPEC's no-gold-plating rule)

### Phase 0 — Build the ruler  *(do first; foundation)*
**Goal:** a trustworthy thick eval + re-baselined known points, incl. the raw-compute reference.
1. **2b — thicken the eval** (absorbs V1): `run_depth.py --n 36 --max-issues 6` (verify
   recoverable_map covers all 36). → ~24 resp-win + ~70 district-win, era-balanced. NO new
   matter selection (recon was wrong — skews era).
2. **Build cite-faithfulness judge** (absorbs G1): identity ≠ faithful use. New Opus judge:
   does each cited holding actually SUPPORT the proposition? Deterministic-ish wrapper like
   the others. Needed before treatise (Phase 1) — mandatory rail.
3. **Re-baseline on the thick set**, both bases + refs:
   closed-book · naive-RAG · balanced-RAG · v4 rule-presentation · **122b cb max-thinking
   (raw-compute ceiling)** · Opus cb · Opus-RAG. Score all (funnel).
**Carry-forward:** the best baseline becomes CURRENT BEST. Record qwen-cb resp_acc as **the bar**.
**STOP/ESCALATE if:** thick-set resp_acc REVERSES the n=7 direction finding (premises change) —
pause + ping. Also if 122b-raw-compute ≈ Opus and crushes all scaffolding — pause + ping (queue
may collapse, the good deflation).

### Phase 1 — Artifact ladder (R-series)  *(flagship; on gemma4:31b, balanced retrieval, anchor on, single-pass)*
Uses EXISTING extraction fields as the feature substrate (so R doesn't block on DC; DC tests
incremental enrichment later — this honors "DC conceptually upstream of R" without serializing them).
Ladder, cheap-screen each rung, promote winners:
- raw-cases (= baseline) → **rule-list (= v5: rule-presentation on gemma + grounding hybrid,
  S1)** → rule+comment (UCC/jury-instruction style) → **treatise-chapter (R3 crux)**.
- **R3 crux (falsifiable):** does treatise surface respondent-win CONDITIONS as doctrine
  (resp_acc ↑) or launder the 79%-district frequency into authoritative narrative (resp_acc ↓)?
  cite-faithfulness rail ON.
- Then on the winning rung only: **R1 distiller sweep** (12b → 31b → 120b → Opus build-time);
  **R2 volume/multi-pass** (5/10/20 rules, atomic 1→1 vs batched); **R4 static-vs-dynamic**
  (build-time matter-agnostic chapter vs per-matter distill — the product-shape bet, absorbs P1).
**Carry-forward:** best ARTIFACT (+ its distiller/volume/static-or-dynamic settings).
**STOP if:** no rung beats balanced-RAG baseline on the gate → richer artifacts don't pay; note + skip to Phase 3.

### Phase 2 — Decomposition increment (DC-series)  *(on the winning artifact)*
- **DC2** induce the typed decomposition schema per issue type (capable model proposes dims —
  don't hand-spec). **DC1** feed decomposed cases to the analyst / into the artifact builder
  (suspected interaction: decomposition → better induced rules → re-test even if DC1 standalone is flat).
- **DC4 faceted retrieval** (absorbs G2): retrieve analogues by operative dimension → surface
  exposure-relevant resp-win analogues text-sim buries.
- **DC3 bitter-lesson head-to-head:** winning-scaffold vs same-base max-thinking-multi-pass vs
  122b — at equal token budget. Does imposed structure beat raw compute? (Reference column from
  Phase 0 already gives the cheap read; this is the controlled version.)
**Carry-forward:** decomposition on/off + retrieval mode. **STOP if** decomposition flat at every interaction point → drop it, proceed.

### Phase 3 — Topology (SYS-series)  *(on winning artifact+component; anchor + RAG-only cites in all)*
single-pass (baseline) → **SYS1 appellate-exchange** (district last word) · **SYS2 inquisitorial-judge**
(best bet for soundness) · **SYS3 panel+aggregator** / self-consistency floor · **SYS4 verify-cascade**
(v1-done-right) · **SYS5 2-model routing** (qwen direction + gemma soundness, absorbs E1).
E2 (rules→adversarial) = winning artifact × winning advocacy topology, falls out for free.
think=OFF for judge/advocate roles. **Carry-forward:** best TOPOLOGY. **Expect modest gains** (cheap structural fixes already did the heavy lifting).

### Phase 4 — Base × system + ceiling  *(on the winning full config)*
Run winner on qwen3.5:35b (S2 contrast) and 122b (local ceiling). Establishes base×system interaction; does the system restore qwen's cb 86%?

### Phase 5 — Grand head-to-head + Pareto  *(finale)*
- **M1:** best-local-system vs naive-Opus-RAG (64%/29%) vs Opus-cb (76%/86%) vs **Opus-WITH-the-
  winning-system** (does the system lift Opus too? if yes, story = "system > model").
- **M2:** cost/latency/privacy Pareto over every logged config → the ship recommendation.

---

## Candidate → phase map (nothing lost)
V1→P0 · G1→P0 · S1/v5→P1 · D2→P1 · P1(static)→P1(R4) · G2→P2(DC4) · DC1-4→P2 · D1(base-rate)/D3(predict-then-ground)→cheap P1/P2 prompt variants · S2→P4 · S3→P3(SYS3 floor) · E1→P3(SYS5) · E2→P3(free) · M1/M2→P5 · **V2 DROPPED**.

## Live results log  *(fill as we grind: config | base | resp_acc | grounding | cite-faith | usefulness | wall-clock | verdict)*

### Phase 0 progress (started 2026-06-28)
- ✅ **Thick eval verified satisfiable.** evalset = 36 matters; usable = **34 matters / 77 issues**,
  era-balanced (1999-01: 10 · 2004-09: 12 · 2018-25: 12). Truth dist (via authoritative
  `truth_map()`): **20 respondent-win** (era 6/8/6) · 52 district · 3 none_ruled · 2 mixed →
  **72 gradeable, 20 exposure** (≈3× the prior n=7). Earlier "0 resp-win" was a field-lookup bug
  (prevailing_party lives on the holding via `hid`, not the depth key). No tripwire.
- ✅ **Cite-faithfulness rail built + smoke-validated** (GPU-free): `cite_faithfulness_{prep.py,
  judge.js,eval.py}`. Reuses `grounding.parse_cites/resolve`; emits 1 blinded item per
  (analysis, RESOLVED cite) with the real holding(s) as ground truth; judge → faithful/tangential/
  **unfaithful** (UNFAITH% = laundered confab, the rail). Smoke on gemma4-31b.think (rag, 84 cites)
  + adv3-qwen3.5-35b (judge, 101 cites) = 185 items, de-id intact.
- ⏸️ **Generation HELD:** GPU occupied by `qwen3.6:27b` (resident keep-alive, no driving job — not
  ours). Per serialization rule, holding 2b + re-baseline generation until GPU clears. (Judge
  fan-out also held — could break a local run if the 27b is in use.)

### Baseline scoreboard (Phase 0, thick set) — PENDING GPU
config | base | resp_acc | grounding | cite-faith | usefulness | verdict
--- | --- | --- | --- | --- | --- | ---
_(closed-book · naive-RAG · balanced-RAG · v4-rule-pres · 122b-cb-maxthink[raw-compute ref] · Opus-cb · Opus-RAG)_

## File / command map
- Generation: `run_depth.py` (local), `run_depth_opus.py` (Opus subagent), `run_adversarial.py`
  (`--anchor-tag`), `run_framing.py` (`--analyzer`); arms in `exp-bakeoff/arms/`.
- Judges (Workflow scripts): `w11_outcome_judge.js`, `w11_usefulness_judge.js`,
  `depth_recovery_judge.js`; + **cite_faithfulness_judge.js** (to build, P0).
- Scoring: `outcome_prep/eval.py`, `usefulness_prep/eval.py`, `grounding.py`/`grounding_eval.py`.
- New code needed: cite-faithfulness (P0); decomposition arm + schema-induction (P2);
  appellate/inquisitorial/panel/verify-cascade arms (P3). Build per-phase, don't pre-build.
