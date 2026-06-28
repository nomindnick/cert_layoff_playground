# 06 coverage-harness — weekend experiment brainstorm (WORKING, unpruned)

Status: brainstorm in progress (started 2026-06-27). Not a queue yet — threads
get dumped here, pruned/ordered later into the actual run order.

## Settled frame (don't relitigate)
- **North star: insight is the product.** The main app is the risk-memo / matter
  workbench (P1 / proto 05); 06 decides the *architecture* of its analysis engine,
  to run LOCALLY (privilege → on-box; "beat Opus" = match cloud-Opus quality on-box,
  the ship/no-ship gate).
- **Outcome/exposure accuracy is the anchored PROXY for trustworthy insight**, NOT a
  prediction product. If the system can't reach the "right" result most of the time
  we can't trust its analysis.
- **ALJ-fallibility caps the outcome metric <100%** (ALJs sometimes err; editors too
  polite to give a clean "ALJ got it wrong" signal — NOT worth mining). Accept the fuzz;
  read outcome as a directional floor vs the ~79% always-district baseline, relative
  across arms.
- **Scoring = 5 metrics.** Anchored: breadth (deterministic), outcome/resp_acc
  (Opus extracts direction → code grades vs real `prevailing_party`), grounding
  (deterministic cite-resolution). Opus-panel: depth-recovery (DEMOTED — capability
  ranking, blind to grounding/exposure), usefulness (litigator+skeptic, 1-5, blinded).
- V2 (Nick as human outcome judge) DROPPED — anchored metric needs no human cal.

## Measurement principle for ALL artifact experiments
Score the artifact by its **downstream effect on the analyst** (existing scoreboard),
holding the analyst model CONSTANT. Intrinsic quality = secondary: blinded Opus
pairwise + objective cite-faithfulness + Nick face-validity read (face validity is
fine for a lawyer even if not a cert-layoff expert; different from outcome-judging).
Agreement of downstream+intrinsic = strong; divergence (pretty but no lift) = a finding.

## Run economics (free GPU does NOT mean free experiments)
Generation = free (local GPU, serial). The SCARCE budget is (a) judge tokens (Opus
usefulness + outcome-direction panels — cloud fan-out, can't run while GPU hot) and
(b) interpretation attention. So:
- **Beam search, not full factorial.** Fix the winner of each axis, carry it forward;
  toggle a component again only at a SUSPECTED INTERACTION, not everywhere.
- **Cheap-screen → expensive-confirm funnel.** Run generation + deterministic metrics
  (breadth, grounding, cite-faithfulness) + the cheap outcome-direction extractor on
  EVERY variation; promote only configs that beat current-best on resp_acc+grounding to
  the full usefulness panel. Most variations die cheap and never cost a judge token.
- The bitter lesson (DC3) is enforced CONTINUOUSLY by keeping a raw-compute reference
  column (122b cb max-thinking) in the baselines — every scaffold must beat it to justify itself.

---

## Thread 1 — Doctrinal artifact: rule statements → treatise (Nick, 2026-06-27)

Architecture principle: separate 3 roles, possibly 3 different models —
  (1) atomic EXTRACTION — small/focused, **1 case → 1 grounded rule + holding id**, cite-checked
      (atomic controls confab + keeps cite attribution clean; batching blurs + invites outcome-votes)
  (2) doctrinal SYNTHESIS — large model; atomic rules[+holdings] → rule+comment / treatise
  (3) ANALYSIS — the base under test, fed the artifact.
Carry holding ids through synthesis → analyst can cite real holdings while reasoning from
prose (fixes v4 rules-only grounding 48%→0%).

- **R1 distiller sweep** — fix format+analyst, vary distiller: gemma4:12b(current) → 31b →
  qwen3.5:35b → 120b-class → Opus(build-time ceiling). Metric: cite-faithfulness(obj) +
  blinded Opus pairwise + downstream lift. FALSIFIED if 12b ≈ 120b downstream (distiller
  quality doesn't propagate → cheap one wins; good deflation).
- **R2 volume / multi-pass** — analyst sees 5 vs 10 vs 20 rules via focused passes
  (≤5 cases/pass); atomic(1→1) vs batched(5→synth). Metric: downstream + context-pollution
  check (breadth/soundness vs volume — the "pollutes context" worry made measurable).
- **R3 FORMAT LADDER [flagship]** — (a) raw cases → (b) rule list → (c) rule+comment
  (UCC/jury-instruction style) → (d) full treatise chapter (RAG→treatise). Built from
  BALANCED retrieval; carry holding cites. CRUX (falsifiable): does treatise surface
  respondent-win CONDITIONS as first-class doctrine (resp_acc ↑) or launder the
  79%-district frequency into authoritative narrative (resp_acc ↓)? resp_acc is the tell.
- **R4 static vs dynamic** — build-time matter-AGNOSTIC per-issue treatise chapter (big
  model, manufactured once) vs per-matter dynamic distill. Product-shape bet
  (corpus → build-time treatise factory) + cost/privacy win. Preserve fact-sensitivity via
  worked illustrations/comments in the chapter.

Risks to bake in:
- **Laundering of confab** — richer prose makes a confabulated rule look authoritative →
  cite-faithfulness is a MANDATORY rail on R3/R4, not optional.
- **Laundering of skew** — treatise from skewed retrieval bakes district-lean as doctrine →
  build from balanced retrieval; resp_acc is the tell (this is R3's crux).
- Build-time treatise is matter-agnostic → preserve fact-sensitivity via worked illustrations.

## Thread 2 — Different systems / topologies (Nick, 2026-06-28)

Mostly richer versions of the advocacy system; read as TARGETED FIXES to v2's known
failure modes (v2 = best exposure resp_acc 71% BUT manufactures respondent-lean
out 60% vs cb 80%, + craters soundness 1.32 via confab). Keep v3's cheap wins in all:
judge ANCHORED to cb prior + advocates cite ONLY RAG holdings. think=OFF for judge/advocate.

- **SYS1 appellate/sequential exchange** — opening → response → reply → judgment (responsive,
  not independent simultaneous briefs). Fixes "two ships passing": reply must rebut → exposes
  weak args. LEVER: who gets last word = directional thumb. OAH = accusation: district opens,
  respondent opposes, district replies → DISTRICT last word → counters v2's respondent-lean.
- **SYS2 inquisitorial judge** — judge reads briefs → poses questions → advocates answer →
  judge writes opinion. Best bet for SOUNDNESS: active interrogation tests briefs vs the record
  (= cite-faithfulness pressure), instead of passively weighing rhetoric (the "pull"). Mirrors a
  hot-bench ALJ.
- **SYS3 analyst panel + aggregator** [non-advocacy] — N independent analysts (vary base/
  decomposition/framing) → aggregator reconciles. SPEC's "many adequate eyes" (arm B); cheapest
  with free GPU. Self-consistency (sample-N-vote) = its near-free floor.
- **SYS4 decomposed verify-cascade** [non-advocacy] — what v1 should have been: a SEQUENCE of
  narrow, symmetric, grounded single-purpose checks (direction-vs-prevalence, cite-faithfulness,
  addressed-respondent's-best-arg, rule-stated-right) → repair. Each checks ONE thing vs record →
  none can swing the verdict like v1's one-sided critic did.
- **SYS5 two-model routing** (absorbs earlier E1) — qwen supplies direction prior, gemma does the
  grounded/sound analysis. Operationalizes the complementarity finding.

HONEST CAVEAT (from our own history): high-leverage fixes so far were CHEAP structural changes
(anchor, RAG-only cites, balanced retrieval), NOT elaborate procedure. Predict modest gains from
richer topology; test cheap; don't out-engineer the structural knobs before they're maxed.

(E2 rules→adversarial emerges for free = winning ARTIFACT × winning advocacy TOPOLOGY.)

---
**→ Consolidated executable plan: see `RUN_PLAN.md` (the grind artifact).**

## Thread 3 — Case decomposition / typed feature extraction (Nick, 2026-06-27)

Idea, named: turn each retrieved case from a text-blob into a TYPED FEATURE
decomposition (affected teacher's credential/seniority/status; comparator's quals in
skip/bump contest; district posture; notice defects; procedural posture; disposition
per issue). Analyst reasons dimension-by-dimension vs the matter, not whole-case
surface similarity. Origin: bitter lesson (spend tokens to "really understand" each
case first) + the embeddings/multi-dimensional-representation intuition.

HONEST SPLIT (Nick's own "reasoning is thin" obs is load-bearing):
- decompose what IS there (parties/facts/defects/disposition) = safe EXTRACTION, grounded.
- expand thin reasoning WITHIN one case = CONFABULATION (the failure mode we fight). The
  defensible "expand" is INDUCTIVE ACROSS cases, grounded in dispositions = the treatise
  (Thread 1). So "expand reasoning" → treatise done right / confab done naive. Keep separate.

REFRAME — decomposition is the FOUNDATION UNDER rules/treatise (sets build order):
  decompose into features → induce rules over features → treatise → analyst reasons
  feature-by-feature. Attacks our 2 worst problems at root: DIRECTION (feature reasoning
  breaks the outcome-vote pull) + SOUNDNESS (grounding in extracted features curbs confab).
  Falsifiable: should most move resp_acc + soundness; if neither, drop it (tokens for nothing).
  => BUILD ORDER: DC (decomposition) is upstream of R (rules/treatise).

- **DC1 decompose-then-analyze [core]** — build-time enrich each corpus case into a typed
  decomposition; feed analyst the decomposed retrieved cases vs raw text (baseline). Measure
  downstream; hypothesis resp_acc + soundness ↑.
- **DC2 schema induction vs hand-spec** — model-induced decomposition schema per issue type
  (capable model reads corpus, proposes salient dims) vs Nick's hand-written list. Induced is
  more bitter-lesson-aligned AND solves the "dims I don't know" gap. Also just produces the schema.
- **DC3 structured decomposition vs "just think harder" [bitter-lesson fork; load-bearing
  for the whole program]** — at EQUAL token budget: typed decomposition pre-pass vs unstructured
  extended-thinking/multi-pass "deeply understand case+matter" pre-pass (+ vs bigger local model).
  Does imposed structure beat raw compute? If a 122b w/ max thinking matches all the scaffolding
  for free = the deflationary (good) result: run biggest local model, skip orchestration.
- **DC4 faceted/structured retrieval** — retrieve analogues by operative DIMENSION (credential-
  nexus, notice-defect type) not surface text → surfaces exposure-relevant respondent-win
  analogues that text-sim buries → balanced retrieval + resp_acc ↑. (Absorbs earlier G2.)

Placement: build-time — decompose each corpus case ONCE, store, retrieve enriched form.
Matter-relative salience (which dims matter for THIS dispute) = cheap runtime step.
Start from existing extraction fields (facts/arguments/authorities/dispositions); ENRICH, don't re-extract.

---

## Claude's earlier candidate list (unendorsed; for merge/prune)
D1 base-rate naming · D2 format ablation [⊂ R3] · D3 predict-then-ground ·
S1 v5 (rule-presentation on gemma4:31b + grounding hybrid) · S2 base sweep ·
S3 self-consistency · G1 cite-faithfulness [now a mandatory rail] · G2 retrieval re-rank ·
E1 two-model routing (qwen direction + gemma soundness/grounding) · E2 rules→adversarial ·
P1 static rule-pack [⊂ R4] · V1 Step-2b eval thickening (resp-win n=7→~24) ·
M1 grand head-to-head (incl. does-the-system-help-Opus) · M2 cost/latency/privacy Pareto.
