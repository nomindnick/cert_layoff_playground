# SPEC — E1. Coverage bake-off (the flagship)

> Build after E0. Read `../SPEC.md` + `../scoreboard/SPEC.md`. Arms run on **local
> models** (the load-bearing question); the reference arm rides a subagent.
> `local-LLM-heavy` → run when the GPU frees; scaffolding/arms A/B retrieval are
> deterministic and can be wired now.

## Hypothesis

On this bounded-issue corpus, a system of **many small, differently-scoped local
passes** covers the intellectual space (E0 breadth + depth) **as well as or better
than a single frontier pass, within hours of wall-clock**, and beats a fixed-RAG
baseline by enough to justify its cost. **Falsified if** no local arm beats fixed
RAG by a worthwhile margin per wall-clock hour, or the depth gap to the frontier
reference stays wide. Cheap deflations welcome: **B≈C ⇒ the agent is theater,
enumerate the taxonomy**; **depth-gap-stays-wide ⇒ depth is frontier-bound, ship
local for breadth + frontier/human for depth.**

## Why it matters

This is W9 stage 2 (can a *local* model orchestrate the loop — never tested) and
the empirical resolution of "agentic vs non-agentic" for our corpus. Its output
decides which orchestration the production app's Tier-1/Tier-2 surfaces are built
from, and whether local-primary is viable for the privileged active-dispute path.

## Data inputs

E0's held-out matter set + answer keys; the merged corpus via `harness/corpus.py`;
F1 engine (`01-search-mcp`) for retrieval; `04-deep-research/research_tool.py` for
the agentic arm; 05's `evidence.py` for the baseline.

## Approach — the arms

Each arm is an `arm_fn(matter) → {spotted_issues, per_issue:[{issue, analysis,
cited_holding_ids}], _cost}` graded by E0. **Design rule for every arm: read the
full structured holding (`facts`+`reasoning`) for any load-bearing holding; never
synthesize from a summary** (the depth fix).

- **A. Fixed RAG** *(baseline)* — 05 `evidence.py` issue-spot + retrieve + single
  grounded synth. Backend: one local model.
- **B. Taxonomy partition-and-sweep** — a cheap, **high-recall** issue proposer
  (small local model or keyword map) nominates candidate categories generously;
  for each, **enumerate every holding** (use the issue tag, not top-k) and shard
  across many small parallel local calls, each judging that holding's relevance +
  extracting its fact/reasoning bearing on the matter; merge. Coverage by
  enumeration. (Watch wall-clock: cap shard size, log what's swept — no silent
  truncation.)
- **C. Agentic adaptive** — a local model drives `research_tool.py`
  (search→holding), adapting queries as it learns; capped tool-call budget.
  **Primary local-feasibility probe**: does the model hold tool-call discipline,
  and does adaptivity raise recall over B?
- **D. Sweep + divergence-adversarial recovery** — B, then the E2 adversaries
  (near-miss-tail + adjacent-doctrine) propose missed issues/holdings; a triage
  pass (grounded — every proposed addition must cite a resolvable holding) folds
  the meritorious ones back in. Coordinated via `harness/blackboard.py`.
- **Ref. Single frontier pass** — one Opus subagent over the same matter (the
  "one smart" ceiling). Subagent backend; clearly labeled as idea-ceiling, not a
  local result.

## Deliverables

`exp-bakeoff/arms/{a_fixed,b_sweep,c_agentic,d_divergent}.py` (each exposing
`arm_fn`); `bakeoff_workflow.js` (orchestrates arms needing fan-out + the ref via
subagents, writes per-arm outputs the scoreboard ingests); `run_bakeoff.py`
(drives local arms, calls E0's `score`); `output/scorecard.json`,
`output/leaderboard.md`; `FINDINGS.md` with per-arm breadth/depth/grounding **and
wall-clock**, backend per arm, and the local-vs-frontier gap with uncertainty.

## Success criteria

Validated if ≥1 local arm beats A on coverage-per-wall-clock-hour with a margin
that survives the matter-set spread, and the arm ranking + local↔frontier gap are
reported with CIs. The *shape* + the cheap deflations are the finding regardless
of direction.

## Out of scope

Steering/conditioning (E4), the judge-loop wrapper (E5), and full isolation of the
divergence mechanism (E2) — D here just needs to *include* divergence; E2 dissects
why it works. No UI; no accreting memory.

## Privacy notes

All retrieval de-identified via `harness/deid.py`; blackboard files gitignored;
any committed leaderboard/example is District (ALJ) only. Local arms keep
(de-identified) matter facts on-box; the subagent ref arm receives only the
already-de-identified matter (it's a ceiling probe, not the privileged path).
