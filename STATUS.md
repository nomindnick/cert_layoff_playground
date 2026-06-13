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
| 03 | [alj-scouting (P2)](prototypes/03-alj-scouting/SPEC.md) | **validated** | none (+ local-LLM-light) | Per-ALJ scouting reports are real, not a horoscope: win-rate & issue-mix differ across ALJs beyond a permutation null (within-year p≈.0003). 59 usable ALJs; only 2 individual win-rate leans survive BH-FDR on 2yr data (group signal real, per-ALJ thin). Ship the deterministic cited render; LLM narrative stays 99% grounded / 100% discriminable when forced to obey significance labels. [FINDINGS](prototypes/03-alj-scouting/FINDINGS.md) |
| 04 | [deep-research (W9 s1)](prototypes/04-deep-research/SPEC.md) | **validated (stage 1)** | none | Claude + corpus-as-tool = a real deep-research harness. 4 hard longitudinal Qs; **~100% of cites grounded** on independent re-query, 3/4 judged non-obvious. Failure mode is subtle legal **over-generalization in prose**, not fake cites — caught by an adversarial verify pass. Stage 2 (can a *local* model orchestrate the loop) is the open question. [FINDINGS](prototypes/04-deep-research/FINDINGS.md) |

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
