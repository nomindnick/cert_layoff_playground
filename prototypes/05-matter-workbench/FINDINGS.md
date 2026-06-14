# FINDINGS — 05. Matter workbench / risk-memo generator (P1, P4 folded in)

## Verdict

**Validated — as an evidence-marshalling first-draft tool with an attorney in the
loop, not an autonomous memo writer.** Given a structured matter, the system
produces an issue-by-issue risk memo that is **97.8% grounded** (independent
re-query), **matter-specific** (a blind judge matched all 3 memos to their own
matter, 3/3), and **useful** (3.67/5 from a deliberately harsh two-judge panel,
4.0 on the cleanest matter). The load-bearing finding — confirming and extending
W9 at the matter level — is that **the failure mode is not hallucination but legal
characterization**: cited holdings are ~100% real and correctly attributed, but
the synthesis occasionally mis-states a *rule* on top of a correct cite (e.g.
labeling a PKS attrition holding "ADA-based"), papering over genuine unsettled
splits. The independent verify pass caught the load-bearing error in **every**
memo, and the "What to verify" section the memos write themselves flags the
characterizations for review. So P1 works — as the interactive heart of the main
app — provided it is built as **deterministic evidence pack → grounded synthesis →
independent verification → attorney reviews the legal characterizations**, never
as a fire-and-forget generator.

## What we learned

Three synthetic matters (skipping/competency before ALJ Sarli; bumping/tie-break
before ALJ Lew; procedural/PKS with no ALJ assigned), each: evidence pack built
deterministically, memo synthesized, independently verified, judged by a 2-lens
usefulness panel, and run through a blind matter-match.

| Matter | claims | grounded | usefulness (overall) | note |
|---|---|---|---|---|
| crestview (bumping/tie-break, ALJ Lew) | 62 | **100%** | **4.0** (honesty 4.5) | every tally correct; surfaced real doctrinal splits |
| riverton (skipping, ALJ Sarli) | 50 | 98% | 3.5 | 1 false claim — the PKS/ADA mis-label |
| oakmesa (procedural, no ALJ) | 44 | 95.5% | 3.5 | 1 over-noticing overreach |
| **mean** | | **97.8%** | **3.67** | **discriminability 3/3** |

**The deterministic substrate (P4, folded in) is the strength.** Issue-spotting +
F1 retrieval produced genuinely on-point evidence packs: Oak Mesa's March-16
late-mailing pulled both sides of the real split (a late-receipt-is-jurisdictional
holding *and* a late-service-excused-no-prejudice holding) plus the over-noticing
answer (over-noticing on a bumping theory is proper); Crestview's plastics-bump
pulled the controlling no-split rule *and* a conflicting ROP-bump holding. This is
grounded by construction and is itself a shippable artifact (`cli.py` renders it
with zero LLM).

**The synthesis is good and honest, but makes an associate's mistakes.** The
memos correctly obeyed ALJ significance labels ("win-rate not distinguishable from
base → no lean to report"), distinguished "recorded prevailing party" from
"no recorded outcome" in their tallies, and flagged thin issues. But the harsh
"skeptical partner" judge found real analytical gaps a senior attorney would
catch: burying the single on-point *favorable* analog for a matter's worst
exposure (Riverton's online skip), under-developing a second skip, omitting an
unspotted facet (the Crestview tiebreak when `lottery_used=false`), and not
stating the cheapest fix ("amend the resolution before the board adopts it").
These are emphasis/judgment errors, not grounding errors — exactly what an
attorney-in-the-loop is for, and a clear prompt-improvement roadmap.

**The verification pass earned its place.** It was designed around the W9 lesson
and it paid off: in Riverton it caught a confident PKS/ADA rule inversion sitting
on a correct citation — precisely the failure mode — and noted the conflicting
attrition holdings the memo had papered over. Without that pass, the memo reads as
authoritative. **This validates the architecture, not just the idea.**

## Backend notes

- **Deterministic substrate (no LLM):** `evidence.py` over the F1 engine; issue-
  spotting is rule-based from the matter schema. Runs with no GPU.
- **Synthesis + verify + usefulness panel + discriminability: Claude subagent
  fan-out** (Workflow `matter-risk-memo`; 15 agents, ~650k tokens, ~13 min).
  Verifiers re-queried the corpus independently (`research_tool.py`); usefulness
  used a 2-lens panel (district litigator + skeptical partner) per **Nick's choice
  of subagent judges over personal review**. This validated the **idea**; the
  local-feasibility question is answered by the bakeoff below.
- **Privacy:** memos came back clean — the synth prompt's name-scrub held (only
  District (ALJ) cites + R-refs; the W9 non-roster-name risk did not materialize
  here, but the gate stays). Committed `sample_memo.md` re-scanned.

## Local-model synthesizer bakeoff (2026-06-14)

The open question — can a **local** model fill the synthesizer role, or does P1
need Opus 4.8? — tested head-to-head: same 3 matters, same deterministic evidence
packs, same fixed **Opus-4.8 eval harness** (grounding verify + invented-cite
check + 2-lens usefulness panel + blind matter-match). Only the synthesizer
varies. Local models ran on ollama at `OLLAMA_NUM_PARALLEL=1` with the **reasoning
channel ON** and a generous budget (the favorable condition for the big models).

| Synthesizer (3 matters) | grounded% | invented cites | usefulness /5 | honesty /5 | matter-match | gen/memo |
|---|---|---|---|---|---|---|
| **Opus 4.8** (baseline) | **95.7** | 0 | **4.0** | 4.83 | 3/3 | cloud |
| gemma4:31b | 86.0 | 0 | **2.83** | 4.0 | 3/3 | ~400s |
| qwen3.5:122b | 87.7 | 0 | 2.5 | 3.83 | 3/3 | ~310s |
| qwen3.5:35b | 80.7 | 0 | 2.33 | 3.33 | 3/3 | ~115s |
| gpt-oss:120b | 76.3 | **2** | 2.17 | 2.33 | 3/3 | ~120s |
| mistral-medium-3.5:128b | — | — | — | — | — | **failed to load** |

1. **More parameters did *not* buy better legal reasoning.** The **31b gemma was
   the best local model**; none of the 120b-class models beat it. The largest open
   model, **gpt-oss:120b, was the worst and the only one to fabricate holdings**
   (2 invented cites). qwen3.5:122b barely edged its own 35b sibling — within
   noise. At this task, architecture/training beats raw scale, and scale is no
   guarantee of grounding.
2. **No local model came close to Opus 4.8.** Opus led every axis — grounding
   (95.7% vs 76–88%), usefulness (4.0 vs 2.2–2.8), near-perfect honesty (4.83).
   The ranking held across all three matters (Opus per-matter overall
   [3.5, 4.5, 4] vs best-local gemma [3, 2.5, 3]); it isn't a one-matter fluke.
3. **Everyone passed the horoscope test.** All 15 memos, every arm, blind-matched
   to their own matter (3/3). Even weak local memos were *on the right matter* —
   the gap is grounding fidelity and analytical depth, not specificity.
4. **The local failure mode is mis-grounding + omission, not fabrication —
   except gpt-oss.** Most locals kept cites real (0 invented) but mis-stated
   outcomes/rules more than Opus and omitted the load-bearing analysis the matter
   was built to test (gemma never answered the senior-fluency-vs-BCLAD question).
   gpt-oss alone invented cites — disqualifying for an attorney tool.
5. **Operational reality: the dense 128b would not run.** mistral-medium-3.5:128b
   (the only *dense* 120-ish model) fit on GPU but its 80GB load blew past
   ollama's ~5-min `llama-server` start window ("context canceled") on every
   attempt — it needs a raised `OLLAMA_LOAD_TIMEOUT`. The **MoE** 120b models
   (gpt-oss, qwen3.5:122b) loaded and ran fast once `OLLAMA_NUM_PARALLEL=1` freed
   the full GPU (at the prior `=4`, a 4-slot KV reservation forced CPU offload).

**Implication for P1 — the honest, anticipated answer:** the production-quality
matter memo wants **Opus 4.8** (subscription/API). A local model can produce a
usable *first cut* — **gemma4:31b** is the pick of the local litter — but at
materially lower grounding/usefulness and with no guarantee against fabrication
(gpt-oss). For an attorney-facing tool where one hallucinated cite is
disqualifying, the local arm is a **draft-assist, not the engine**. Crucially,
the two backend-agnostic safety layers carry regardless of synthesizer: the
**deterministic evidence pack** (grounded by construction) and the **independent
verify pass** (which caught the local mis-groundings just as it caught Opus's).
*Caveat: one decoding config per model (reasoning-on); per-model prompt/temperature
tuning could move absolute numbers but is unlikely to close a ~1.2-point
usefulness / ~10-point grounding gap to Opus.*

## Blocked on full corpus?

P1 improves sharply with the production corpus and the code re-points via
`corpuslib`:
- **Thin-record honesty becomes density.** Many memo sections were flagged "thin"
  (a few holdings, one or two years). More years turn 3–1 tallies into real base
  rates and shrink the "no recorded prevailing party" gap (gold holdings lack
  structured outcomes; the production extraction adds them).
- **Active ALJs.** Conditioning on the *assigned* ALJ only helps once post-2017
  judges are in the structured set (P2's limit).
- **Argument inventory.** The "what respondents will argue" layer is strongest for
  issues dense in 2004/2009; full structured data makes every issue dense.

## Production recommendation

**Build it — as the interactive core of the main app, with the verification pass
and an attorney-review step as first-class, non-optional components.** The shape
the prototype validates: deterministic evidence pack (committable, grounded by
construction — ship the `cli.py` digest as the always-available substrate) → a
grounded synthesis that must cite the pack and obey significance labels → an
independent grounding/characterization verifier → the attorney resolves the
flagged legal characterizations. P3 (resolution linter) and P5 (report studio)
slot in as modes of this workbench, confirming the one-main-app thesis. Cheap
prompt wins already identified by the judges (lead with the on-point favorable
analog; address every spotted facet; always state the resolution-amendment fix)
would lift usefulness without new infrastructure. On the synthesizer engine, the
bakeoff settles it: **use Opus 4.8 for the production memo** (no local model came
within ~1.2 usefulness points or ~10 grounding points, and gpt-oss:120b
fabricated cites); offer a **local draft-assist (gemma4:31b)** for an offline/
cost-free first cut, never as the sole engine. The deterministic pack + verify
pass are backend-agnostic and stay mandatory either way. **Destination:
interactive heart of the main app** (the principled exception to "no query-time
inference," with everything but issue-spotting and synthesis kept deterministic).
