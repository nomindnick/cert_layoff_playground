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
  of subagent judges over personal review**. This validates the **idea**; a local
  re-run (gemma4:31b / qwen3.5:122b) is the remaining step to claim local
  feasibility for an offline build.
- **Privacy:** memos came back clean — the synth prompt's name-scrub held (only
  District (ALJ) cites + R-refs; the W9 non-roster-name risk did not materialize
  here, but the gate stays). Committed `sample_memo.md` re-scanned.

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
would lift usefulness without new infrastructure. Run the local-model spot-test
next to decide interactive-local vs. fan-out. **Destination: interactive heart of
the main app** (the principled exception to "no query-time inference," with
everything but issue-spotting and synthesis kept deterministic).
