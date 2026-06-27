# Status

Session-boot dashboard. Read this before doing anything; update it before
ending any session that changes a prototype's state. One line per prototype;
detail lives in each prototype's FINDINGS.md.

States: `idea → spec → building → testing → validated | falsified | parked`

## Dashboard

| ID | Prototype | State | Compute | Verdict (one line) |
|----|-----------|-------|---------|--------------------|
| 01 | [search-mcp (F1)](prototypes/01-search-mcp/SPEC.md) | **validated** | embeddings | Hybrid search clears bar (2009 R@10 0.868/MRR 0.766; 2004 0.951/0.823); MCP server live via `.mcp.json`. [FINDINGS](prototypes/01-search-mcp/FINDINGS.md) |
| 02 | [taste-judge (W7)](prototypes/02-taste-judge/SPEC.md) | **partially validated (weak)** | local-LLM-heavy | LLM judge loses to cheap logistic regression & adds no signal; both ~chance on held-out 2004. Taste is mostly mechanical + year-specific. P5 → transparent feature filter, not LLM gate. [FINDINGS](prototypes/02-taste-judge/FINDINGS.md) |
| 03 | [alj-scouting (P2)](prototypes/03-alj-scouting/SPEC.md) | **validated** | none (+ local-LLM-light) | Per-ALJ scouting reports are real, not a horoscope: win-rate & issue-mix differ across ALJs beyond a permutation null (within-year p≈.0003). 59 usable ALJs; only 2 individual win-rate leans survive BH-FDR on 2yr data (group signal real, per-ALJ thin). Ship the deterministic cited render; LLM narrative stays 99% grounded / 100% discriminable when forced to obey significance labels. **Multi-era recheck** (merged 2004/09 + 2018–25, 360 decisions): group signal *strengthens* (Q=74, p=.0002), 3 ALJs now survive FDR, tendencies persist where measurable; ceiling is judicial rotation. [FINDINGS](prototypes/03-alj-scouting/FINDINGS.md) |
| 04 | [deep-research (W9 s1)](prototypes/04-deep-research/SPEC.md) | **validated (stage 1)** | none | Claude + corpus-as-tool = a real deep-research harness. 4 hard longitudinal Qs; **~100% of cites grounded** on independent re-query, 3/4 judged non-obvious. Failure mode is subtle legal **over-generalization in prose**, not fake cites — caught by an adversarial verify pass. Stage 2 (can a *local* model orchestrate the loop) is the open question. [FINDINGS](prototypes/04-deep-research/FINDINGS.md) |
| 05 | [matter-workbench (P1+P4)](prototypes/05-matter-workbench/SPEC.md) | **validated** | none (+ local-LLM-light) | Matter → issue-by-issue risk memo over a deterministic evidence pack. **97.8% grounded**, **3/3** matter-match discriminable, **3.67/5** useful (4.0 best) from a subagent judge panel. Failure mode is legal **mis-characterization on a correct cite** (not hallucination), caught by the verify pass + the memo's own "what to verify" section. Ship as pack → grounded synthesis → verify → attorney review. **Synthesizer bakeoff (6 models):** no local model nears Opus 4.8 (best local gemma4:31b 2.83/5 vs 4.0; grounding 86% vs 96%); param count ≠ legal reasoning (gpt-oss:120b *worst* + only one to fabricate cites). Opus for production, local = draft-assist. [sample](prototypes/05-matter-workbench/sample_memo.md) · [FINDINGS](prototypes/05-matter-workbench/FINDINGS.md) |
| 06 | [coverage-harness (W9s2/W10/W11)](prototypes/06-coverage-harness/SPEC.md) | **building** | none + local-LLM-heavy | **Program** (experiments as subdirs). Reframes 04+05 as one job — *cover the corpus's intellectual space* for a matter — and makes coverage **measurable**: breadth=issue-spotting, depth=fact/reasoning recovery, scored vs held-out real decisions. **E0 scoreboard VALIDATED (breadth + depth)** — a trusted instrument to grade arms. *Breadth* (deterministic; 36 zero-leak matters): discrimination PASS, random 0.12 < freq-prior 0.37 < lexical 0.40 < oracle 1.0; **rarity-weighted recall is the metric** (raw recall is gamed by the frequency prior, which *is* the floor E1 must beat — ~0.37). *Depth* (Opus-subagent rubric judge, 48-item L0–L3 ladder): TRUSTED — separates wrong-issue 0.00 < facts-only 1.08 < recovered-reasoning 2.83, Spearman 0.85 vs proxy. Privacy gate green (0/174 prod rosters leak). **E1 arm-1 (local issue-spotter): VALIDATED — local models clear the floor, and it's a small-model job.** gemma4:12b 0.80 ≈ gemma4:31b 0.81 rarity_recall (vs 0.37 floor; 2×); qwen3.6:27b 0.78; qwen3.5≤9b *below* floor; gpt-oss errs (harmony/format quirk). **Recall-ceiling calibration (Opus judge):** ceiling=0.78 (22% of the answer key is under-determined from facts), gemma4:12b fair-recall **0.90** → **breadth-from-facts is ~90% solved by a cheap 12b model** (~10% headroom); over-spotting mostly legit (plausible bucket 0.31 — precision was understated). **PIVOT: breadth solved cheap; open game is DEPTH.** **Depth bake-off (gemma4:12b, RAG vs closed-book):** NULL — retrieval no effect (paired Δ −0.08; both ~1.5/3 depth). Bottleneck is *reasoning* (12b inverts the distinction even with holdings in hand). **Model sweep resolves the fork:** Opus closed-book **2.36/3** vs 12b 1.52 → depth is a **model-reasoning gap, not corpus-access** (Opus nails the lottery distinction w/ no corpus; 12b inverts it). Retrieval ~no effect at either end (12b −0.08, Opus +0.12) — 12b can't *use* it, Opus already *knows* the common law. **But the recovery metric is blind to the corpus's real value (grounding):** Opus closed-book cites from memory (confabulates), RAG cites real holdings → "RAG doesn't lift recovery" ≠ "drop the corpus." **Depth is capability-bound** (scales w/ params, think=OFF: 12b 1.52 → 31b 1.88 → Opus 2.36 — unlike breadth where 12b≈31b). **Reasoning (think=ON):** alone doesn't lift closed-book (12b +0.04, 31b +0.04); but **reasoning + RAG COMPOUND at 31b** (RAG 1.84→2.00, first positive RAG-delta local) — reasoning helps a capable model *use retrieved evidence*, not its own knowledge (12b still inverts). **gemma4:31b + think + RAG = 2.00 = best privacy-preserving depth** (~57% of the 1.52→2.36 gap; ~6-7min/issue) = the W11 base config. Privilege tension narrowing (local 2.0 → frontier 2.4). **W11 reframe:** plausible path to/past Opus is the **corpus-grounded characterization-verify** (non-correlated oracle catching the inversions *every* model incl. Opus makes), not collective reasoning. **KEY: the recovery metric is the WRONG TARGET for W11** — it's blind to grounding/usefulness/exposure (what W11+retrieval improve), so it keeps reporting "RAG no effect" as an artifact; and the outcome metric is confounded (winner-inference). **→ upgrade the eval before W11 (not a teardown).** **EVAL UPGRADE (2a) DONE 2026-06-18 — 3 new metrics on existing think-runs (12b/31b/Opus × cb/RAG), blinded Opus panels:** **Grounding** — RAG cite-anything/resolve-real: 12b 28%/100%, 31b 76%/100%, Opus 92%/99%; **closed-book = 0% for ALL incl. Opus** (can't cite these obscure non-precedential holdings from memory — recon's "Opus confabulates cites" was WRONG). **Domain-aware outcome** (confound FIXED — anti-inversion rules + grade vs structured `prevailing_party`): **naive RAG net-NEGATIVE for every model** — Opus cb 76%/**86% resp_acc** → Opus RAG 64%/**29%**; district-bias is a RETRIEVAL-SKEW problem (79%-district evidence), not a small-model gap. **Usefulness** (litigator+skeptic 1–5): 12b 1.7 / 31b 1.9 / **Opus 3.1**; naive RAG neutral-to-negative even for Opus (3.10→3.02); `respondent_args` weakest dim everywhere (Opus 2.64 = exposure-blindness universal). **UNIFIED THESIS: naive RAG buys grounding but NOT usefulness/correctness/soundness, and HURTS exposure accuracy + cite-faithfulness at every level incl. Opus — bottleneck is the SYSTEM.** W11 verify-repair targets fall out of failure-mode data (inversions ~98 + exposure 30 unfixed by RAG; authority-confab WORSENED 150→204): (1) directional/inversion check vs holdings' real prevailing_party, (2) cite-faithfulness, (3) balanced-retrieval + respondent's-counsel lens. **Falsifiable W11 win: orchestrated 31b BEATS naive Opus-RAG (64%/29%) on exposure.** **STEP 1 base-model selection DONE (2026-06-18):** qwen3.5:35b full 4-metric profile vs gemma4:31b — **complementary, not a clean winner.** gemma4:31b integrates evidence (grounding 76%, recovery RAG +0.08) but weak innate direction (cb outcome 60%/43%). **qwen3.5:35b has Opus-LEVEL closed-book direction (cb 80%/86% exposure — best local by far)** but confabulation-prone (cb soundness 1.12), uses retrieval worse (grounding 68%, recovery RAG −0.16); its RAG *fixes confab* (usefulness +0.28, only positive local) while *corrupting direction* (exposure 86%→43%); 2× faster. → **run the model-agnostic W11 harness on BOTH bases** (qwen primary = sharpest system-over-model test: cb 86%→naive-RAG 43%→can the system restore it?). **122b ceiling DONE (n=8 subset):** scale closes the gap to Opus + fixes the 35b's RAG-degradation — recovery RAG 2.38/Δ+0.25, grounding 88%, usefulness RAG 2.31/Δ+0.50 (**only local that RAG-compounds on both like Opus**); but slow (~2.5h/eval), outcome unmeasured, still confabulates → 122b = "local ceiling" config, 35b/31b = fast iteration bases. (Earlier 122b stall was concurrent-workflow interference, NOT think/np — isolated it ran 98% GPU clean.) **REMAINING:** Step 2b = re-run **full 36-matter set** (all recoverable issues) → ~24 era-balanced resp-win MIs, no new selection (recon's "add unselected matters" was WRONG — skews era); Step 3 = W11. **W11 BUILT + 4 ITERATIONS RUN (qwen3.5:35b, 2026-06-18):** v1 verify-repair FALSIFIED (one-sided critic over-corrects 14/18 district→respondent); v2 adversarial (district-brief + respondent-brief + neutral judge) = best SYSTEM, restores exposure (resp_acc 71%) but doesn't beat closed-book + confabulates; v3 anchored+RAG-only-advocates → **grounding 0→96%** (near-Opus) but soundness floored; v4 **rule-distillation** (Nick's idea — distill cases→rules, reason from rules) → **DIRECTION FIXED** (exposure 43%→71%, confirms pattern-match hypothesis) but soundness is a BASE-MODEL floor not a presentation artifact. **CONCLUSION: two orthogonal constraints — DIRECTION fixed by rule-PRESENTATION; SOUNDNESS needs a sounder BASE; GROUNDING separable. → v5 = rule-presentation ON gemma4:31b (sound 1.80) + grounding hybrid.** No design yet beats qwen closed-book (80%/86%) on outcome; W11 wins on grounding+exposure-engagement. See [NEXT_STEPS.md](prototypes/06-coverage-harness/NEXT_STEPS.md). [E0](prototypes/06-coverage-harness/scoreboard/FINDINGS.md) · [E1](prototypes/06-coverage-harness/exp-bakeoff/FINDINGS.md) |

## Lessons

Cross-cutting learnings that should inform every future prototype. Add the
lesson, the prototype that surfaced it, and the date.

- **Ollama parallelism is config/version/architecture-dependent** — the lab
  found qwen-arch forced to `-np 1` on ollama 0.30.7, but parallel workers
  are currently configured on (Nick's later experiment). Don't assume either
  way: check the live config and `gpu_status()` before designing around
  parallelism, and re-test after ollama upgrades. *(cert_layoff_lab
  REFINEMENTS #2 + repo setup, 2026-06-12)*
- **Never call Claude from code** — `claude -p` shell calls bill at API
  rates; in-session Agent subagents use the subscription. Cloud fallback is
  therefore the subagent fan-out pattern (code writes batch inputs → main
  session spawns subagents → code merges/validates outputs), per
  cert_layoff_lab `annotate_summary.py`. *(repo setup, 2026-06-12)*
- **Silent truncation is the insidious LLM failure mode** — fixed context
  budgets fail invisibly on outlier-length inputs and the loss masquerades as
  quality problems. Size `num_ctx` dynamically and log loudly when a budget is
  exceeded. *(inherited from cert_layoff_lab REFINEMENTS #1)*
- **The gold holdings (1979–2015) are a first-class corpus**, not just eval
  scaffolding — 3,955 ALJ- and district-tagged holdings spanning 35 years,
  available before any production extraction runs. *(repo setup, 2026-06-12)*
- **arctic-l-v2 is the best open embedding model on both legal corpora
  tested** (FPPC benchmark and the layoff known-item eval); bge-large second.
  Use `Snowflake/snowflake-arctic-embed-l-v2.0` with `query: ` prefix on
  queries only. *(01-search-mcp, 2026-06-12)*
- **De-identify at index/artifact build time, not at render time** — names
  then can't leak from any downstream consumer. Boundary: the lab's
  `deidentify` covers roster (respondent) names only; non-roster employee
  names survive. *(01-search-mcp, 2026-06-12)*
- **Known-item evals built from token-similarity alignments are biased
  toward BM25** — judge semantic retrieval on paraphrase queries too before
  concluding embeddings don't help. *(01-search-mcp, 2026-06-12)*
- **Reasoning models (qwen3.5:*) need `think=False` for structured output** —
  otherwise they spend the whole token budget in the hidden thinking channel
  and return an empty response. Now in `corpuslib.llm.generate(think=)`.
  With thinking off, qwen3.5:122b (MoE) is also *faster* than gemma4:31b.
  *(02-taste-judge, 2026-06-13)*
- **temp 0 + grammar-constrained gemma4 → repetition loops** (timeouts,
  unterminated JSON, out-of-range numbers). Use temp ~0.2, a `num_predict`
  cap, and a hotter retry. *(02-taste-judge, 2026-06-13)*
- **Always run a small (~50-item) sanity gate before a multi-hour LLM grind**
  — it caught the two failures above and a wrong task framing for the cost of
  minutes. *(02-taste-judge, 2026-06-13)*
- **Beat the cheap baseline first.** A logistic regression on ~8 mechanical
  features matched/beat 31B and 122B LLM judges at reproducing editorial
  selection. For "is this X?" classification over structured records, run the
  deterministic baseline before assuming an LLM is needed. *(02-taste-judge,
  2026-06-13)*
- **Validate on a held-out slice, not just CV.** The taste signal that looked
  real on 2009 (the dev year) collapsed to ~chance on held-out 2004 — it was
  year/editor-specific. Single-year metrics overstated generality.
  *(02-taste-judge, 2026-06-13)*
- **Permutation test = the horoscope detector for per-entity profiles.** Before
  believing any per-ALJ / per-district "tendency," shuffle the entity labels
  across holdings and check the observed dispersion beats the null — and run a
  *within-stratum* variant (e.g. within-year) to rule out a confound (temporal
  drift). For ALJ scouting this cleanly separated real signal (p≈.0003) from
  noise. Corollary: **group-level signal can be real while few individuals
  survive multiple-comparison correction** — say both, don't overclaim
  individuals. *(03-alj-scouting, 2026-06-13)*
- **Deterministic-render-first, thin grounded LLM second.** The trustworthy P2
  product was the cited dossier render (zero inference); the LLM, *when forced to
  cite the dossier and obey its significance labels*, stayed 99% grounded and
  100% discriminable (adversarially verified). Opposite of W7's losing LLM-gate:
  the rule is **structured stats are the product, the LLM only presents them.**
  *(03-alj-scouting, 2026-06-13)*
- **Surname-only joins conflate entities.** Gold cites carry ALJ surnames only,
  so District(Johnson) silently merged Perry O. + Vallera J. (two judges). Detect
  collisions from richer records (decision raw full names, accent/whitespace
  folded) and sequester; flag that single-source surnames can't be
  disambiguated. *(03-alj-scouting, 2026-06-13)*
- **Workflow `args` arrive as a JSON *string*, not a parsed object** — destructure
  it and you get `undefined` fields with no error. Parse defensively at the top:
  `const A = typeof args === 'string' ? JSON.parse(args) : args`.
  *(03-alj-scouting, 2026-06-13)*
- **The corpus deep-research loop's failure mode is mis-characterization, not
  fabrication.** Agents driving the corpus got ~100% of *cites* right (every
  holding existed, correctly attributed) but occasionally **over-generalized a
  legal characterization on top of a correct cite** (e.g. framing the March-15
  rule as keying on employee receipt vs. district mailing). An **independent
  verify pass that re-queries the source** catches this cheaply; agents also
  self-rate conservatively (the judge upgraded 3/4 insights to non-obvious). Any
  attorney-facing generator = generate → re-query-verify each claim → leave legal
  characterization to a human. *(04-deep-research, 2026-06-13)*
- **Non-roster names survive into research/retrieval output.** `deidentify`
  covers roster respondents only, so a *retained junior teacher* named in a
  holding can leak into a snippet. Any deep-research / search output needs a
  **name-scrub gate** before an external surface. Extends the build-time-de-id
  boundary. *(04-deep-research, 2026-06-13)*
- **For attorney-facing generation, citation fidelity is the easy part; legal
  characterization is the hard part.** Confirmed at multi-issue scale (P1): memos
  were ~98% grounded with ~100% real, correctly-attributed cites, but the residual
  errors were confident **rule mis-statements on top of a correct citation** (a
  PKS attrition holding labeled "ADA-based"), which paper over genuine unsettled
  splits. The architecture that works: deterministic evidence pack → grounded
  synthesis → **independent verify-by-re-query** → human resolves the flagged
  characterizations. Extends the 04 lesson. *(05-matter-workbench, 2026-06-13)*
- **A 2-lens subagent judge panel is a usable stand-in for expert usefulness
  review.** An advocate-lens + skeptic-lens pair produced specific, attorney-grade
  critiques (buried the on-point favorable case; skipped a spotted facet; omitted
  the cheapest fix) — reproducible and unblocking for prototype-stage "is this
  actually useful?", with the human spot-checking rather than reading everything.
  *(05-matter-workbench, 2026-06-13)*
- **Parameter count is not a proxy for legal-reasoning quality, and no open local
  model matched Opus 4.8 for attorney-facing synthesis.** P1 synthesizer bakeoff
  (gemma4:31b, qwen3.5:35b/122b, gpt-oss:120b, Opus 4.8; mistral-128b failed to
  load), one fixed Opus-4.8 eval harness: the **31b gemma was the best local**,
  the 120b-class models did not beat it, and the *largest* (gpt-oss:120b) was the
  **worst and the only one to fabricate cites**. Best local hit ~70% of Opus's
  usefulness / 86% vs 96% grounding. Pick local models by measured grounding +
  usefulness, not size; for attorney-facing work use Opus, treat local as a
  draft-assist. *(05-matter-workbench, 2026-06-14)*
- **ollama ops for big-model local runs (v0.30.7, 96GB unified GPU):** (1) set
  `OLLAMA_NUM_PARALLEL=1` for sequential single-user work — a 4-slot reservation
  reserves `4×num_ctx` KV cache and CPU-offloads the 120b models; at `=1` MoE 120b
  models run on-GPU and *fast*. (2) These 2026 models (gemma4, qwen3.5/3.6,
  gpt-oss) are reasoning models: under grammar-`format` mode thinking is
  suppressed, but under free-prose generation they need either `think=False` or a
  big `num_predict` so the CoT doesn't starve the answer (gemma diagnosed: 400-tok
  budget → 40 chars). Output comes back as clean prose (CoT stripped) either way.
  (3) dense ~80GB models (mistral-medium-3.5:128b) exceed the default ~5-min
  `llama-server` load window → "context canceled"; needs a raised
  `OLLAMA_LOAD_TIMEOUT`. *(05-matter-workbench, 2026-06-14)*
- **The production corpus re-points cleanly — the `corpuslib` promise held with
  zero code changes.** First production extraction (`/home/nick/Projects/cert_layoff_corpus/output`,
  93 decisions 2018–25) loads via `CORPUS_ROOT=` alone; all four artifacts sit at
  the same relative paths (only `eval/` absent — used only by the falsified 02).
  Schema grew to v0.4.0 but the changes that touch our read paths are non-breaking:
  `identity.district/alj` gained `canonical*` but kept `.raw`; per-holding
  `prevailing_party` unchanged; `pks_allowed`+`pks_not_allowed` merged to
  `pks_reduction`. **Caveats:** no gold past 2015 (audit-only validation);
  `alj.canonical_id` is null this run (still surname-joining, conflation risk);
  `summary_style_holding` ~75% present; 32/93 undated (key temporal work on
  case-number year, not `decision_date`). **Bonus — richer schema unblocks parked
  ideas:** `board_action.artifacts` (skip/tiebreak/competency resolution language,
  structured) is a native **P3** substrate; `holdings[].notable` is native **W8**;
  `authorities[].role/proposition` enables the citation-graph concept. Compose
  multi-era corpora by symlinking decision dirs into one root (no copy, privacy
  preserved) — see `03-alj-scouting/make_merged_corpus.sh`. *(corpus integration,
  2026-06-16)*
- **Production (0.4.0) structured decisions carry RAW respondent names in prose
  fields** (`issue.statement`, `facts`, `reasoning.summary`, `arguments[].summary`);
  only `ruling.affected_respondents` is R-ref'd. So `deidentify(text, rec)` must run on
  every prose field at read time before any model call or commit — exactly as 04/05 do
  for the spike — and `corpuslib.deident` (built for 0.2.0 rosters) must be **verified
  against the 0.4.0 roster** before trusting it. Also: the production build has **grown
  to 137 decisions spanning 1999–2001 + 2018–2025** (835 spike holdings + ~419 prod,
  nearly all with `facts`+`reasoning`); the earlier "93 / 2018–25" is stale —
  **derive span/counts at runtime**, never hardcode. *(06-coverage-harness spec,
  2026-06-17)*
- **The depth signal lives in the structured `reasoning.summary` field, which
  already bundles the legal distinction AND its rationale** — so a holding's
  `reasoning` is a complete "level-3" analysis, while a bare holding *summary*
  (all the 35-yr gold has) is not. An attorney-facing arm that surfaces
  `reasoning.summary` for load-bearing holdings gets depth nearly for free; the
  gold-only longitudinal layer structurally cannot reach depth (it has no
  reasoning). Confirmed by the E0 depth-judge calibration. *(06-coverage-harness
  E0, 2026-06-17)*
- **For issue-spotting / coverage metrics, the floor to beat is the FREQUENCY
  PRIOR, not random** — guessing the ubiquitous issues (bumping/seniority/
  skipping) scored 0.44 raw recall. Use **rarity-weighted** recall (rewards
  spotting the rare, hard issues) as the headline; raw recall is gamed by the
  prior. And when validating an LLM judge against a synthetic quality ladder,
  test the discrimination that *actually exists* in the data — our ladder's
  "level 2" (distinction-without-rationale) doesn't occur because the corpus
  bundles them, so the judge correctly collapsed L2≈L3; the judge was right and
  the ladder wrong. *(06-coverage-harness E0, 2026-06-17)*
- **Issue-spotting over this corpus is a SMALL-model job — coverage saturates by
  ~12b and bigger doesn't help.** gemma4:12b (0.80 rarity_recall) ≈ gemma4:31b
  (0.81) at 1/3 the params and 2/3 the wall-clock; both ~2× the frequency-prior
  floor. But it's a threshold+family effect, not smooth scaling: qwen3.5 at 4b/9b
  is *below* floor while qwen3.6:27b is above. Pick the smallest *capable* model;
  the remaining coverage headroom (issues every size misses — tie_breaking/
  procedural/bumping) is a **system** problem (retrieval/divergence), not a
  bigger-model one. Supports "system over model." *(06-coverage-harness E1,
  2026-06-17)*
- **gpt-oss (20b/120b) returns EMPTY under ollama structured-output (`format`)** —
  its OpenAI-harmony reasoning channel swallows the content regardless of
  `think=False`; needs free-text generation + manual JSON extraction instead. And
  `think=False` is still required for gemma4/qwen under `format` in this ollama
  version — format mode does NOT auto-suppress thinking as an earlier lab note
  suggested (gemma → "Extra data" JSON-then-CoT; qwen → empty response).
  *(06-coverage-harness E1, 2026-06-17)*
- **Measure the recall CEILING before chasing recall.** An answer key built from
  real decisions can be *under-determined*: 22% of the issues a decision actually
  litigated have NO factual hook in the facts-only matter we derived from it. An
  Opus "is this issue recoverable from these facts?" pass — with DECOY non-issues
  as a negative control (real 0.78 vs decoy 0.31 recoverable = a valid judge) —
  separated real model headroom from answer-key noise, and showed gemma4:12b
  already catches **~90% of the recoverable** issues. So breadth-from-facts is a
  solved, cheap, small-model job; the heavy machinery (retrieval/sweep/divergence/
  bigger models) must justify itself on **DEPTH** (fact+reasoning analysis), not
  breadth. The same pass also de-biases precision: most "over-spots" (competency
  0.75, credentials 0.46) have a genuine factual hook — thorough spotting is a
  feature. *(06-coverage-harness E1 ceiling calibration, 2026-06-17)*
- **Retrieval is a coverage amplifier, not a reasoning amplifier — now confirmed
  on DEPTH.** gemma4:12b RAG-vs-closed-book over the corpus showed no depth gain
  (paired Δ −0.08, both ~1.5/3). The deficit is legal *characterization*: the
  model names the right operative facts but **inverts the operative distinction**
  (praises a lottery the ALJ struck down; calls a probationary-by-omission teacher
  "temporary") and fabricates cites — and it does this WITH the analogous holdings
  in front of it. Supplying more law can't fix a model that mis-reasons the rule.
  Open: whether a model strong enough to *use* the evidence benefits (model-ceiling
  confound → sweep the analyzer: 31b / large local / Opus). Extends W11 from
  synthesis to retrieval-grounded depth. *(06-coverage-harness E1 depth, 2026-06-17)*
- **Depth (legal characterization) is FRONTIER-BOUND, and the recovery metric is
  blind to where the corpus actually helps.** Depth-sweep ceiling: Opus closed-book
  2.36/3 vs gemma4:12b 1.52 — the depth gap is MODEL REASONING (Opus recovers the
  operative distinction with no corpus; 12b inverts it), and RAG adds ~nothing at
  either end (weak model can't use it; strong model already knows the common law).
  BUT Opus closed-book cites from MEMORY (confabulates "Kavanaugh-line authority")
  while RAG cites REAL checkable holdings — so "retrieval doesn't lift
  depth-recovery" ≠ "drop the corpus"; the corpus's value is grounding + long-tail,
  which needs a **cite-fidelity** metric (not recovery) to see. Quantifies the
  privilege tension: local depth ~1.5 vs frontier ~2.4 = the W11/W12 target. The
  "system over model" thesis wins on breadth, but depth needs reasoning
  amplification, not coverage. *(06-coverage-harness E1 depth ceiling, 2026-06-17)*
- **A correctness/outcome metric over this corpus is CONFOUNDED: the legal
  sub-question direction ≠ the holding's bottom-line `prevailing_party`.** An
  analysis can correctly recover the distinction ("R2 is probationary") — which
  reads employee-favorable — yet the holding's bottom line is district-favorable
  (probationary ⇒ she can still be laid off). So a naive "predicted direction vs
  prevailing_party" correctness metric measures something fuzzy; the Opus outcome
  judge itself flagged the divergence. Fix before trusting correctness numbers:
  ground the judge in the **bottom-line layoff outcome** ("does the district's
  action STAND?"), not the sub-argument, and expand the eval past n=7
  respondent-wins. The earlier "no model beats the always-district baseline /
  models are district-biased" correctness findings are **provisional** pending
  this fix. *(06-coverage-harness E1 correctness, 2026-06-17)*
- **Balanced retrieval fixes the evidence skew but is unproven on outcomes.** The
  RAG packs were ~79% district-win (similarity retrieval over a district-skewed
  corpus), mechanically feeding the model's district-bias; a 50/50 district/
  respondent pack (`retrieval.retrieve(balanced=True)`) fixes the skew and yields
  visibly richer "district wins when X, loses when Y" analysis. But on Opus it was
  inconclusive (recovery flat 2.32; correctness restored vanilla-RAG's degradation
  but didn't beat closed-book; n=7 + the confound above). Re-test on the
  district-biased LOCAL models + a fixed correctness metric + bigger eval.
  *(06-coverage-harness E1 balanced-RAG, 2026-06-17)*
- **A recovery metric ranks model CAPABILITY but is the wrong target to OPTIMIZE.**
  "Did the analysis reconstruct THIS ALJ's reasoning?" is calibrated and
  discriminates models (fine for base-model selection), but it is **blind to
  grounding, exposure-spotting, and usefulness** — exactly what retrieval and
  orchestration improve. Optimizing it makes RAG/W11 look like "no effect" (a
  metric artifact, not a finding). For any intervention whose value is
  grounding/coverage/usefulness (RAG, verify-repair, rules-packs), measure with a
  usefulness + grounding + outcome panel (cf. prototype 05), not recovery.
  *(06-coverage-harness E1 eval review, 2026-06-18)*
- **An outcome/correctness metric over this corpus fails in the WINNER-INFERENCE
  step, not the data.** Grading "predicted direction vs `prevailing_party`" (which
  IS per-holding/per-applicant, verified) breaks because mapping a prose legal
  conclusion to a winner needs domain knowledge: "employee classified
  **probationary**" sounds pro-employee but means she CAN be laid off ⇒ **district**
  wins (decision 1999020331 / R2; reasoning literally says "consequently she could
  be laid off"; `prevailing_party=district`). A lightweight outcome judge mis-maps
  these, so "wrong" predictions include the judge's own errors and the models look
  worse than they are. Fix: a domain-aware judge asking "does the district's ACTION
  STAND?", grounded in `prevailing_party` + per-applicant `respondent_dispositions`.
  *(06-coverage-harness E1 correctness, 2026-06-18)*
- **Naive RAG is grounding-positive but usefulness/correctness-NEGATIVE — at every
  capability level, including Opus.** Measured with the 3 new metrics: RAG flips
  cite-grounding 0%→76–92% (real, in-evidence) BUT is net-negative on the
  domain-aware bottom-line outcome for ALL models — it drags predictions toward the
  79%-district majority class, so it CRATERS accuracy on respondent-win "exposure"
  cases (Opus 86%→29%) and even drops Opus overall 76%→64%. Usefulness is flat-to-
  down too (even Opus 3.10→3.02). So the district-bias is a **retrieval-skew
  problem, not a small-model capability gap**, and the corpus's value is currently
  *unrealized* by naive retrieval — the lever is the SYSTEM (balanced retrieval +
  directional/cite-faithfulness verify-repair), not model size. The stark falsifiable
  W11 target: an orchestrated 31b that BEATS naive Opus-RAG on exposure accuracy.
  *(06-coverage-harness W11 eval upgrade, 2026-06-18)*
- **Grounding a cite's IDENTITY ≠ faithful use of its CONTENT.** RAG makes cites
  resolve to real holdings (grounding ✓) yet the usefulness judges flag MORE
  authority confabulation under RAG (150→204 mentions) — because more cites = more
  chances to misstate what a holding actually held. A grounding/cite-resolution
  metric is necessary but not sufficient; a separate cite-FAITHFULNESS check (does
  the holding stand for the claimed proposition, per its `reasoning.summary`/
  `prevailing_party`) is its own W11 verify step. *(06-coverage-harness W11 eval upgrade, 2026-06-18)*
- **To thicken an eval slice, exhaust the matters you already vetted before adding
  new ones.** The depth run only used 12 of 36 selected zero-leak matters with
  issues capped at 3, leaving most respondent-win matter-issues on the table in
  already-stratified matters. Re-running the FULL 36 (all recoverable issues) yields
  ~24 era-balanced (8/10/6) respondent-win MIs with zero new selection/leak/ceiling
  work — vs the recon's instinct to pull unselected matters, which would have skewed
  era (63/71 of the unselected resp-wins sit in one era). Check the cheap expansion
  of the existing pool first. *(06-coverage-harness Step 2b sizing, 2026-06-18)*
- **Model families differ in WHICH capability they hold — pick the base for a
  verify-repair system by what it must PRESERVE, not its average score.** Same-size
  locals split opposite ways on this task: gemma4:31b *integrates evidence* well
  (grounding 76%, recovery RAG-compounds) but has weak innate legal direction (cb
  exposure 43%); qwen3.5:35b has **Opus-level closed-book direction (cb exposure 86%)**
  but confabulates (cb soundness 1.12) and uses retrieval worse (grounding 68%,
  recovery RAG −0.16). Neither "wins" on a scalar. For a system whose job is balanced
  retrieval + directional verify, the better base is the one with the hard latent
  capability (direction) the system must protect from naive-RAG's skew — qwen — not
  the one the system would have to manufacture it in. So test the model-agnostic
  harness on BOTH; the sharpest system-over-model case is the model with the biggest
  latent-vs-naive gap (qwen cb 86% → naive-RAG 43%). *(06-coverage-harness Step 1 base selection, 2026-06-18)*
- **RAG examples act as outcome-VOTES, not rule-derivation (in-context pattern-matching).**
  Smoking gun: hold the matter facts FIXED and change only the retrieved-set MIX — qwen
  predictions move with it (unbalanced 79%-district → preds 19/5, resp_acc 43%; balanced
  50/50 → 15/9, resp_acc 57%). If the model derived a rule and applied it to the facts, the
  exemplar mix shouldn't swing the bottom line. **It behaves like a soft nearest-neighbor
  vote over the demonstrations — "which of these six does this most look like" — and even
  OPUS does it** (cb 86% exposure → RAG 29% when fed the skew). This re-explains the whole
  W11 arc (v1 over-corrected because balanced evidence always supplies a respondent-win
  exemplar to "match"; balanced retrieval only rebalanced the vote, didn't induce reasoning).
  **Implication:** the untried lever is PRESENTATION — distill the cases into RULES ("rule
  is X; applied to Y → Z (cite)") so the task becomes apply-the-rule, not match-the-neighbor
  (v4, NEXT_STEPS). *(06-coverage-harness W11 mechanism, 2026-06-18)*
- **Two ORTHOGONAL constraints, two independent fixes (the W11 arc, v1-v4).** Quality on this
  task decomposes into (1) DIRECTION (does the analysis reach the right outcome) and (2)
  SOUNDNESS/trust (does it avoid confabulating authority). They have DIFFERENT fixes and don't
  trade off: **DIRECTION is fixed by PRESENTATION** — reasoning from distilled RULES instead of
  raw cases breaks the nearest-neighbor pull (exposure acc 43%→71%, v4); **SOUNDNESS is a
  BASE-MODEL floor** — qwen confabulates cites whether given cases or rules (~1.3-1.5 regardless
  of v1/v2/v3/v4 system), so it needs a sounder base (gemma4:31b sound 1.80), NOT a better system.
  Grounding is a third, separable axis (RAG-only advocates → 96%; rules-only → 0%). Don't try to
  fix a base-model floor with orchestration, or a presentation problem with a bigger model — match
  the lever to the constraint. Convergent next test (v5): rule-presentation ON gemma4:31b +
  grounding hybrid. *(06-coverage-harness W11 v1-v4 synthesis, 2026-06-18)*
