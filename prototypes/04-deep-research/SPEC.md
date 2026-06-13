# SPEC — 04. Corpus deep-research harness, stage 1 (W9)

> Stage 1 of W9: the cheap, near-free experiment that rides on F1. Stage 2 (can a
> *local* model orchestrate the same loop as code) is deferred — see FINDINGS.

## Hypothesis

A reasoning agent (a Claude session, or a Claude subagent) with the F1 corpus
exposed as a queryable tool functions as a genuine **deep-research harness**: on a
hard, multi-step longitudinal question it will plan → search → read → synthesize
and produce a **grounded, non-obvious** answer that an attorney would value —
not just a single-fact lookup or a plausible-but-ungrounded essay.

**Falsified if** the outputs are (a) **ungrounded** — claims don't trace to real
holdings, cites are wrong/invented; or (b) **shallow** — they merely restate what
one search already returns, or recite what any layoff lawyer already knows; or
(c) the loop adds nothing — synthesis quality is no better than the raw search
hits. A frankly **mixed** result (grounded but mostly "known, now evidenced") is
an honest and useful outcome and tells us where the agentic layer pays off.

## Why it matters

This loop is the backbone of several heavier ideas — W4 (hypothesis miner), W7
novelty checks, W10 (split hunter), and **P1's research step**. If the cheap
in-session version already yields grounded insight, P1 is de-risked and stage 2
(local orchestration) is worth building. If it's shallow or ungrounded, we learn
that before investing. Destination: **internal harness / capability test** that
feeds the build-time generators and P1.

## Data inputs

The F1 substrate, unchanged: `holdings` (267 structured 2004/2009 decisions, with
arguments-by-party + outcomes), `gold_holdings` (3,900+ editorial summaries
1979–2015), `decisions` (full text, BM25). Queried through a single CLI wrapper,
`research_tool.py` (search / holding / decision / facets), which de-identifies
roster names on full reads. Limits that bound the answers: structured outcomes
are 2 years only; gold is editorial, not exhaustive.

## Compute profile

`none` for stage 1 (retrieval is embeddings already built in F1; the reasoning is
the agent itself). **No new local-LLM cost.** Stage-1 grounding is validated by
**Claude subagent fan-out** (one harness instance per question + an independent
adversarial verifier per memo) and by one question run live in-session. A
subagent result here validates the *idea* (Claude + corpus = research harness);
**stage 2** is the separate question of whether a *local* model (qwen3.5:122b)
can drive the same loop as code — explicitly out of scope for stage 1.

## Approach

1. Pose 4 hard questions a partner would actually ask, each requiring multi-step
   retrieval across collections/eras (doctrine evolution; argument efficacy;
   procedural exposure; tie-breaker doctrine).
2. Run the loop: **1 question live in-session** (the authentic "session is the
   harness" trace → `sample_memo.md`), **3 via Workflow fan-out**
   (`deepresearch_workflow.js`), each agent driving `research_tool.py`.
3. **Adversarially verify** each fanned memo with a second agent that
   independently re-queries the corpus and checks every load-bearing claim's
   grounding + rates the headline insight (grounded-nonobvious / grounded-known /
   overreach / shallow).
4. Judge honestly: grounding rate, and the insight mix.

## Deliverables

`research_tool.py` (reusable corpus CLI), `deepresearch_workflow.js`,
`sample_memo.md` (the live trace, committed, de-identified), `FINDINGS.md`,
STATUS/README/IDEAS updates. Per-question memos + verifier verdicts in `output/`
(gitignored).

## Success criteria

- **Grounding ≥ ~90%** of load-bearing claims trace to a real holding on
  independent re-query. Below that ⇒ the harness hallucinates; fix retrieval
  discipline before relying on it.
- **Insight**: at least some answers rated *grounded & non-obvious* (not all
  "shallow/obvious"). If everything is shallow, the agentic layer isn't earning
  its keep over plain search.

## Out of scope

- Stage 2 (local-model orchestration as code) — the real feasibility question,
  deferred.
- Wiring the MCP server live in-session (the `layoff-corpus` server in `.mcp.json`
  wasn't connected this session; the identical engine was driven via the CLI
  wrapper — equivalent for the insight question).
- Productionizing any memo; these are capability probes, not shippable artifacts.

## Privacy notes

Cite **District (ALJ)** only. Known boundary (surfaced here): `deidentify` covers
**roster** respondent names; a **non-roster** individual named in a holding
(e.g. a *retained* junior teacher) can survive into a snippet. The research
prompt forbids reproducing personal names, and any committed memo is
name-scrubbed. This is itself a finding: deep-research outputs need a name-scrub
gate before any external surface.
