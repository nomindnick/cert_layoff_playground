# Ideas ledger

Everything we might build, from concrete prototype candidates to half-formed
concepts. Promoting an idea = assigning it a `prototypes/NN-slug/` directory
and writing its SPEC. Nothing here is committed-to; "no bad ideas" space.

Compute profiles: `none / embeddings / local-LLM-light / local-LLM-heavy`.
Heavy ones should run **before** the production corpus build occupies the GPU.

## Product shape (working thesis, 2026-06-12)

Most ideas converge on **one main attorney-facing app** over the corpus, not
a fleet of apps. The substrate (corpus + retrieval + structured query) is a
platform; ideas are views over it. The durability rule (static app over a
frozen corpus, no inference at query time) sorts every idea into one of four
destinations:

1. **Query-time feature** of the main app — cheap, deterministic,
   retrieval-only (search, P4 tables, P5 slices).
2. **Build-time artifact generator** — where most LLM-heavy ideas belong:
   batch jobs whose frozen outputs the app serves (W7 curated volumes, P2
   profiles, W10 splits memo, W2 atlas, the corpus-memory layer).
3. **Internal operator tool** — never shipped to attorneys (corpus QA,
   eval scaffolding).
4. **Standalone experiment** — the simulator, mostly alone here; its
   credible production form is batch simulation as a build-time insight
   generator, not an interactive toy.

This does NOT change the repo approach — prototypes still test ideas in
isolation, with no integration/UI tax. The thesis just means each FINDINGS
should name its destination, and the production app gets assembled once,
later, from validated pieces.

## Foundation

- **F1. Hybrid search + corpus MCP server** *(embeddings)* — **[built →
  prototype 01, validated]** FPPC-pattern
  BM25 + embedding retrieval over holdings and decisions, faceted by
  issue/ALJ/district/outcome/year. Twist: expose as an MCP server so Claude
  sessions (and local models) can use the corpus as a tool — the substrate
  for rung-3/4 prototypes, not just a search box.

## Practice tools (rung 3)

- **P1. Matter workbench / risk memo generator** *(local-LLM-light)* —
  attorney describes a live layoff (district, proposed skips, tiebreak
  approach) → retrieve similar holdings → issue-by-issue risk memo with
  verifiable cites, including what respondents will argue (we have
  structured arguments-by-party data).
- **P2. ALJ scouting reports** *(local-LLM-light)* — **[built → prototype 03,
  validated]** per-ALJ dossiers: issue-by-issue tendencies, persuasive
  arguments, procedural strictness. Gold holdings are ALJ-tagged across 35
  years, so this is buildable now with real longitudinal depth. *Result:
  tendencies are real (not a horoscope) by permutation test; 59 usable ALJs;
  ship the deterministic cited render. The editors' own 535 ALJ-attributed
  observations are the trustworthy core.*
- **P3. Resolution linter** *(local-LLM-light)* — feed a draft board
  resolution / skip criteria / tiebreak criteria; check against every way
  similar artifacts were attacked in the corpus; flag exposure with cites.
  Preventive — the thing management-side clients actually pay for.
- **P4. Argument win-rate explorer** *(embeddings)* — per issue: the
  inventory of arguments made, by whom, success rate, and the ALJ's stated
  reasoning. "What survives a (d)(1) skip challenge" as a queryable table.
- **P5. Report studio** *(embeddings)* — parameterized summary reports:
  any year, year range, issue-across-years, ALJ, or district slice, rendered
  in the human volumes' format. The easy half of report generation —
  deterministic assembly over the same substrate as F1 (the lab's
  `render_summary.py` generalized from per-year to arbitrary slices).
  Pairs with W7 for the editorial layer.

## Wild tier

- **W1. Adversarial hearing simulator** *(local-LLM-heavy)* — local models
  as respondent's counsel (armed with the corpus of winning respondent
  arguments), district counsel, and ALJ (optionally conditioned on a P2
  profile). Stress-test a layoff plan before the board adopts it.
- **W2. The 35-year atlas** *(none)* — interactive visualization of issue
  drift 1979–2015 from the gold holdings: layoff waves vs budget crises,
  rise/fall of issue categories. Zero inference required; high
  show-the-partner value.
- **W3. Doctrine-space map** *(embeddings)* — embed all ~4,200 holdings,
  project to 2D, color by issue/outcome/era. Sparse regions and odd
  neighbors are the Move-37 candidate surface, made visible.
- **W4. Move-37 hypothesis miner** *(local-LLM-heavy)* — enumerate issue ×
  argument × fact-pattern combinations, find unattested/under-tested ones,
  have a 122B model reason about plausible-theory vs known-loser. Output: a
  candidate-novel-theories memo for expert review.
- **W5. Predictability experiment** *(local-LLM-heavy)* — strip rulings from
  holdings, predict prevailing party, measure calibration per issue. The
  per-issue spread is the finding: which issues are coin flips vs
  effectively determined.
- **W6. Doctrine drift detector** *(local-LLM-heavy)* — same issue,
  different decades: has the de facto standard moved while the statute stood
  still? Diff reasoning chains across eras with a big model.
- **W7. Editorial-taste judge** *(local-LLM-light; subagent-fan-out
  friendly)* — **[built → prototype 02, partially validated (weak)]** can an
  LLM reproduce the human editors' selection of
  noteworthy holdings? Rare luxury: taste has gold labels here — the
  2009/2004 eval alignments mark which system holdings the human volume
  included (~600 candidates → ~260 selections in 2009). Decompose before
  judging: duplication = embedding similarity vs already-selected set
  (MMR-style greedy selection); novelty = corpus-relative frequency (a
  query, not an intuition — likely a small agentic search loop per holding,
  see W9); residual "is this substantively interesting" = the LLM call.
  Metric: precision/recall vs human selection. Feeds P5.
- **W8. Editorial-commentary detector** *(local-LLM-heavy)* — the volumes'
  editorial remarks ("the ALJ appears to conflate competency with special
  training," implicit domino theory, unpointed-criteria subjectivity) as
  typed-observation detection, NOT open-ended legal judgment: mine a
  typology + few-shot examples from 35 years of gold commentary, detect
  instances per type using the structured authorities/reasoning fields,
  eval against which decisions the humans actually commented on. Output is
  candidate observations for expert review, never auto-published. Highest
  difficulty; falsifying it cheaply is a fine outcome.
- **W9. Corpus deep-research harness** *(local-LLM-heavy; stage 1 is
  cheap)* — the agentic plan→search→read→synthesize loop over the corpus.
  Stage 1 (near-free, rides on F1): Claude Code session + corpus MCP server
  IS a deep-research harness — ask hard longitudinal questions, judge
  whether the pattern yields insight worth having. Stage 2 (the real
  feasibility question): the same loop as code on local models — can
  qwen3.5:122b orchestrate? Backbone for W4, W7 novelty checks, and P1's
  research step.
- **W10. ALJ-split hunter** *(local-LLM-heavy)* — agent sweeps for pairs of
  holdings in tension: same issue, similar facts, opposite outcomes,
  different ALJs. "The circuit splits of OAH" — an artifact that has never
  existed; the human volumes caught splits only incidentally. Inherently
  agentic (candidate pair → verify the tension is real → characterize).
  Natural W9 application.

## Concepts (not yet shaped into prototypes)

- Citation-graph analytics: which authorities (Bledsoe, Duax, Alexander…) do
  the work; doctrine propagation through ALJ decisions; authority half-life.
- Corpus-grounded Q&A chatbot ("PKS bot") — probably falls out of F1 + a
  system prompt; may not need its own prototype.
- Cross-backend capability matrix: which local models can do which jobs
  (structured output, long-context reasoning, citation fidelity) — emerges
  from FINDINGS across prototypes rather than its own build.
- **Corpus memory / practice-wisdom layer**: memory belongs to the corpus,
  not the user. Research runs, curation passes, and split-hunts accrete
  distilled observations ("ALJ X consistently strict on notice defects
  post-2010") into a durable notebook future runs consult — the system gets
  smarter about the corpus over time, Letta-style but with no accounts or
  hosting. First instantiation should ride on W9, not be its own build.
- Matter-context personalization (attorney's multi-session inquiries on one
  matter): **parked** — requires user accounts, makes deployment
  exponentially harder, usage frequency unknown. Revisit only if rung-3
  tools show real adoption.
- Corpus QA agent: the deep-research pattern pointed inward — an agent
  prowling extraction records, cross-checking against full_text, flagging
  anomalies for human review. Would pay for itself during the production
  corpus build.
