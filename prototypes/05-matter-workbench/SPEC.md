# SPEC — 05. Matter workbench / risk-memo generator (P1, with P4 folded in)

> The flagship rung-3 tool and the core workflow of the eventual main app. Builds
> directly on F1 (retrieval), P2 (per-ALJ tendencies), and the W9 stage-1 lesson
> that the generate loop must be paired with an independent verification pass.

## Hypothesis

Given a **structured description of a live layoff matter** (district, basis for
the reduction, proposed skips/tiebreaks, assigned ALJ if known), the system can
produce an **issue-by-issue risk memo** that is:
1. **Grounded** — every stated risk, predicted respondent argument, and cite
   traces to a real holding, confirmed by an independent verification pass;
2. **Specific** — it surfaces the exposures and respondent arguments for *this*
   matter, not generic recitations true of any layoff;
3. **Honest** — it flags where the corpus is thin and which legal
   characterizations a human attorney must check.

**Falsified if** the memo is (a) **generic/horoscope** — a blind reader can't
match it to its matter because it would fit any layoff; or (b) **un-keepable-
honest** — after the verify pass, grounding stays low or legal characterizations
are confidently wrong (the W9 failure mode, un-caught); or (c) **starved** — the
2-year structured argument/outcome substrate is too thin to populate per-issue
risk with anything an attorney couldn't get from a single search. A **mixed**
result that says *which issue areas are richly supported and which aren't* is an
honest, useful outcome.

## Why it matters

This is the tool a district-side attorney actually opens when a new layoff lands:
"here's my matter — where am I exposed, what will respondents argue, what does the
precedent say, what should I shore up before the board adopts the resolution."
It composes the whole stack: F1 retrieves, the **P4-style argument substrate**
supplies "what respondents will argue," P2 conditions on the assigned ALJ, and the
W9 verify pass keeps it honest. Validating it validates the **one-main-app
thesis** — P3 (resolution linter) and P5 (report studio) become modes of this
workbench rather than separate apps.

**Destination:** the **interactive heart of the main app** — the one principled
exception to the repo's "no inference at query time" rule, because each matter is
novel. The design still pushes everything possible to deterministic/query-time-
cheap (retrieval, argument inventory, ALJ tendencies, the verification re-query);
LLM inference is confined to issue-spotting and per-issue synthesis.

## Data inputs

- **F1 search** (`engine.py` / the `research_tool.py` CLI from prototype 04) over
  `holdings` (267 structured 2004/2009, with `arguments[{party,summary}]` +
  `prevailing_party`), `gold_holdings` (3,955 longitudinal 1979–2015), and
  `decisions` (full text).
- **P4 substrate (folded in):** per canonical issue, the inventory of arguments
  made by each party in analogous holdings and how they came out — built
  instance-based (retrieve analogous holdings, surface *their* arguments +
  outcomes) rather than as thin aggregate win-rates, since structured data is only
  2 years. An optional aggregate view (argument-type × success count) is secondary
  and must show its n.
- **P2 dossiers** (`prototypes/03-alj-scouting/output/dossiers/{alj}.json`) when
  the matter names an assigned ALJ — pull that ALJ's issue-footprint + any
  significance-labeled tendency for the issues in play.
- **Matter input:** a structured object (schema below). Test matters are
  **synthetic** (invented, no real client facts), authored to exercise the main
  issue areas — unless Nick supplies a real, de-identified fact pattern.

Limits that bound the result: structured arguments/outcomes are **2 years**;
gold is editorial; "what respondents will argue" is strongest for issues
well-represented in 2004/2009 (skipping, bumping, seniority, procedural) and
thinner elsewhere — the memo must say so per issue.

## Compute profile

`local-LLM-light`. LLM steps: (1) issue-spotting from the matter description,
(2) per-issue risk synthesis over the deterministic evidence pack, (3) the
verification pass. **Idea-validation via Claude subagent fan-out; local
feasibility via gemma4:31b / qwen3.5:122b spot-run** (check `gpu_status()`
first). GPU-busy fallback: the deterministic evidence-pack assembly (retrieval +
argument inventory + ALJ pull) needs no GPU; only spotting/synthesis/verify do,
and those are the fan-out pattern. A subagent memo validates the idea; a local
re-run is required to claim a local build-time/interactive feasibility — FINDINGS
names the backend per result.

## Approach

Six stages; 1–3 are deterministic substrate, 4 is the thin LLM layer, 5 is the
W9 verify pass, 6 assembles.

1. **Matter intake schema + synthetic test matters.** A JSON schema:
   `district`, `alj` (optional), `basis` (PKS reduction / ADA decline / particular
   services), `reductions` (services/positions being cut), `proposed_skips`
   (`[{retained_junior_role, claimed_special_skill, specific_need, in_board_resolution: bool}]`),
   `tiebreak` (criteria + whether a lottery is used), `board_resolution_criteria`,
   `attorney_concerns` (free text). Author 2–3 synthetic matters exercising
   skipping, bumping/seniority, tie-breaking, and a procedural defect.

2. **Issue-spotting.** Map the matter to canonical issue categories in play
   (skipping, seniority, bumping, competency, tie_breaking, procedural_issues,
   pks_allowed, attrition). Light LLM classification, grounded by the facet list;
   each spotted issue carries the matter facts that triggered it.

3. **Per-issue evidence pack (deterministic — the P4 substrate).** For each
   spotted issue: F1-retrieve the most analogous holdings (hybrid search seeded
   from the matter facts, filtered by category; both structured + gold), and for
   each, surface `cite (District(ALJ))`, `year`, `prevailing_party`, the
   `arguments` by party, and the ALJ's reasoning. If `alj` set, attach that ALJ's
   P2 tendency for the issue. Output a cited evidence pack per issue — no LLM yet.

4. **Per-issue risk synthesis (thin grounded LLM).** Over each evidence pack, the
   LLM writes: the **exposure** for this matter, **what respondents will likely
   argue** (drawn from the analogous holdings' respondent arguments), **how it has
   tended to land** (from the retrieved outcomes, with honest n), and **what to
   shore up**. Hard rule: every claim cites an evidence-pack holding; no claim
   without a cite; flag any legal characterization as needs-review.

5. **Verification pass (first-class — the W9 lesson).** An independent step
   re-queries the corpus to confirm each cited holding supports its claim, and
   separately flags every legal characterization for human check (the W9 failure
   mode was confident mis-framing on top of a correct cite). Emits per-memo
   `grounded%` + a list of "attorney must verify" items.

6. **Assemble memo.** A matter risk memo: overall risk summary + per-issue
   sections, District(ALJ) cites only, with verification annotations and the
   needs-review flags inline. **Name-scrub gate** on all output (W9 privacy
   finding: non-roster names can leak).

## Deliverables

`schema.py`/`matters/*.json` (intake + synthetic matters), `evidence.py`
(issue-spotting + per-issue evidence packs over F1), a synthesis+verify workflow,
`cli.py` to render a memo, one **committed de-identified `sample_memo.md`**,
`FINDINGS.md`, and STATUS/README/IDEAS updates. `output/` gitignored.

## Success criteria

- **Grounding ≥90%** of memo claims trace to a verified holding on independent
  re-query. Below ⇒ tighten retrieval discipline before trusting it.
- **Specificity** — a blind judge matches each memo to its own matter (vs. a decoy
  matter) clearly above chance (the P2 discriminability test, reused). At chance ⇒
  generic/horoscope.
- **Usefulness (subagent judge panel)** — a panel of 2–3 independent subagent
  judges, each given the matter + the memo, rates whether it surfaces the
  exposures and respondent arguments a district-side attorney would want, and
  flags anything generic, missing, or wrong. Reproducible and unblocking; caveat
  that a subagent-judge approximates, not replaces, a practicing attorney (Nick
  spot-checks). Decision confirmed with Nick (2026-06-13).
- **Honesty** — the memo flags thin issues and legal characterizations rather than
  overclaiming.

## Out of scope

- **No outcome prediction** ("you will win/lose"). The memo surfaces exposure and
  precedent, not a forecast (W5 territory; 2-year data can't support it).
- **No real client data** — synthetic matters only.
- **Not a filing-ready document** — an internal, attorney-reviewed risk memo.
- **No UI**; `cli.py` prints markdown. No multi-session matter memory (parked
  personalization).

## Privacy notes

Synthetic matters carry no real client facts. All output cites **District (ALJ)**
only; a **name-scrub gate** runs on every generated memo (the W9 finding that
non-roster individuals — e.g. a retained junior teacher — survive `deidentify`).
The committed `sample_memo.md` is hand-checked before commit.

## Key decisions (confirmed with Nick, 2026-06-13)

1. **Test matter source** — **synthetic now, real later**: author synthetic fact
   patterns grounded in the corpus's issue areas and validate on those; a real
   de-identified matter can be swapped in whenever Nick provides one.
2. **Eval instrument** — **subagent judge panel** for usefulness (2–3 independent
   judges), alongside automated grounding% and blind matter-match discriminability.
   Nick spot-checks rather than serving as the sole judge.
