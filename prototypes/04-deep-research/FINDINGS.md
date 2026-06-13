# FINDINGS — 04. Corpus deep-research harness, stage 1 (W9)

## Verdict

**Validated (stage 1) — the corpus-as-tool deep-research loop works, with one
load-bearing operational caveat.** A reasoning agent (Claude, in-session and as
fanned-out subagents) driving the F1 corpus through a single CLI tool produced
**grounded, non-obvious** answers to hard, multi-step longitudinal questions. On
independent adversarial re-query, **every cited holding across all four questions
checked out — the harness does not hallucinate citations.** Its actual failure
mode is subtler and important: it can **over-generalize a legal characterization
in prose even when the cites are sound** (Q3 framed the March-15 rule as keying on
employee *receipt* when the corpus keys on district *mailing/service*). That is
exactly what the adversarial-verify pass is for, and it caught it. Conclusion: the
agentic layer earns its keep over plain search, **and** any product built on it
(P1, W4, W10) must pair generation with an independent grounding/verification
pass and leave legal characterization to a human. Stage 2 — whether a **local**
model can drive the same loop as code — remains the open feasibility question.

## What we learned

Four hard questions (1 run live in-session, 3 via Workflow fan-out with an
independent verifier per memo). 36 corpus tool-calls total across the fanned
three; ~6–13 per question.

| Question | claims | grounded (independent re-query) | self-rating | verifier verdict |
|---|---|---|---|---|
| Q1 — evolution of special-skills skipping (1980s→2010s), **live** | — | self-checked, all cites read in-session | — | grounded, non-obvious |
| Q2 — what respondent arguments beat a §44955(d)(1) skip | 16 | **100%** | known_but_now_evidenced | **grounded_nonobvious** |
| Q3 — recurring procedural defects: fatal vs. curable | 30 | **100%** | known_but_now_evidenced | partly_overreach |
| Q4 — lottery/tie-breaker doctrine: upheld vs. struck | 18 | **100%** | known_but_now_evidenced | **grounded_nonobvious** |

**Grounding is excellent; the agents are even modest.** Independent verifiers
re-pulled the load-bearing holdings and confirmed they exist, are cited to the
right case/ALJ/year, and say what the memo claims — "often with the quoted ALJ
reasoning verbatim." The agents self-rated every answer the conservative
"known_but_now_evidenced"; the independent judge **upgraded 3 of 4 to genuinely
non-obvious.** Real examples of the non-obvious synthesis:
- **Q2:** the *durable* respondent win is not "I'm as qualified as the junior" —
  it's attacking the district's **predicate showing** (a generalized need not
  tied to a specific course; a qualification the junior won't actually use), e.g.
  Travis (Sarli) 2006, Acton-Agua Dulce (Reyes) 2004, Sylvan Union (Brandt) 2009.
- **Q4:** lottery is lawful only as a genuine **last resort**, with three
  distinct failure modes (used too early, not actually random, no current-needs
  determination); and the apparent "split" is **intra-ALJ sequencing**, not a
  disagreement on legality — the verifier independently found a corroborating
  case and *no* contradicting one.
- **Q1 (live):** the substantive skip standard has been stable since *Alexander*
  (1983); what changed is formalization into a recited multi-prong test and the
  migration of district losses to **resolution drafting + proving the negative**
  (see `sample_memo.md`).

**The one real flaw is the signal, not noise.** Q3's overreach — calling the
March-15 defect a failure of employee *receipt* rather than district *mailing* —
is a subtle but real legal mischaracterization sitting on top of correct
citations. This is the precise risk profile an attorney-facing tool must design
around: **not invented cases, but confident mis-framing of a correctly-retrieved
holding.** The cheap fix worked here (an independent verifier re-querying the
corpus flagged it); the durable fix is to keep a human on legal characterization.

## Backend notes

- **Retrieval/substrate:** F1 engine (arctic-l-v2 hybrid), unchanged. Exposed via
  a new `research_tool.py` (search / holding / decision / facets, de-identified
  reads) because the **`layoff-corpus` MCP server was not connected in this
  session** — the `.mcp.json` server needs approval to load. Driving the identical
  engine through the CLI wrapper is equivalent for the insight question; wiring
  the MCP live is a trivial follow-up.
- **Reasoning: Claude** (in-session for Q1; subagent fan-out for Q2–Q4 + an
  independent adversarial verifier each; 6 agents, ~270k tokens, ~10 min). This
  validates **the idea** — Claude + corpus = a real research harness. It does
  **not** validate local feasibility; that is stage 2.
- **Privacy boundary surfaced (Lesson):** a retrieved holding summary contained a
  **non-roster** individual's name (a *retained* junior teacher, not a roster
  respondent), which `deidentify` does not cover. Deep-research output therefore
  needs a **name-scrub gate** before any external surface; the research prompt
  forbade reproducing names and committed memos are scrubbed.

## Blocked on full corpus?

Stage 1's conclusion (the loop yields grounded insight) won't change with scale —
it will get *richer*: more years close the gaps this run papered over (Q1
explicitly sampled era endpoints; Q2/Q3 win-rate counts are 2-year-thin). The
genuinely corpus-blocked piece is **stage 2**: whether qwen3.5:122b (or similar)
can orchestrate plan→search→read→synthesize as code with this grounding
discipline — worth testing **before** the production build occupies the GPU.

## Production recommendation

**Build the loop into P1, with the verify pass as a first-class component, not an
afterthought.** Stage 1 shows the retrieve→read→synthesize pattern produces
attorney-valuable, grounded answers; it also shows the failure mode is subtle
legal over-generalization, so the architecture must be **generate → independently
re-query to verify each claim → surface ungrounded/overreaching claims to the
human.** Concretely for P1: cite-grounded drafting + an automated grounding check
+ explicit "verify this characterization" flags on legal conclusions. Run **stage
2 (local orchestration) next** to learn whether this can be a local build-time
generator or must lean on subagent fan-out. Destination: **internal harness /
capability layer** feeding P1 and the wild-tier miners (W4, W10).
