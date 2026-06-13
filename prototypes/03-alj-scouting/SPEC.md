# SPEC — 03. ALJ scouting reports (P2)

> Buildable cold. Numbers below are from the data probe done while writing this
> spec; a fresh session can trust them as starting facts but should re-run the
> probe blocks in `common.py` to confirm.

## Hypothesis

Per-ALJ **scouting reports** — issue footprint, outcome tendencies, procedural
posture, persuasive-argument patterns, and the human editors' own
ALJ-attributed observations — can be built **now**, from the ALJ-tagged data,
with enough *density* and *discriminating, verifiable* signal to be useful to
an attorney appearing before that ALJ.

**Falsified if any of:**
- **(a) Density** — too few ALJs clear a usable evidence bar to be a product.
  (Probe ceiling: 228 ALJs in gold, but only **26 with ≥50 cites, 60 with ≥20,
  77 with ≥10**, median 3. If <10 clear the bar, falsified-by-thinness.)
- **(b) Horoscope** — per-ALJ tendencies do **not** differ beyond sampling
  noise; the "tendencies" are generic, equally true of any ALJ. This is the
  load-bearing test (echoes W7's "beat the cheap baseline" lesson: prove the
  signal is real before dressing it in prose).
- **(c) Inertness** — the only trustworthy content is a bare cite list with no
  actionable tendency an attorney couldn't get from search alone.

**Validated looks like:** a density-gated set of reports where (i) per-ALJ
outcome / issue-mix stats discriminate beyond a permutation null for a
meaningful subset of ALJs, (ii) the editors' attributed observations supply
real, cited tendency content, and (iii) an LLM synthesis layer presents this
with every claim grounded in a cite and survives an adversarial
horoscope/grounding check. A frankly **mixed** verdict (some axes carry signal,
others are noise) is the expected and acceptable outcome.

## Why it matters

Rung-3 practice tool. A district-side attorney walking into a §44949 hearing
wants to know, before they ever see the ALJ: what does this ALJ see a lot of,
how have they ruled, where are they procedurally strict, what arguments have
moved them. The human volumes captured ALJ-attributed observations only
incidentally; **nobody has ever assembled a per-ALJ dossier across 35 years.**
Outcome feeds P1 (matter workbench conditions on the assigned ALJ) and W1 (the
simulator's ALJ persona). **Destination: build-time artifact generator** —
frozen per-ALJ dossiers the main app serves; synthesis runs in batch, never at
query time.

## Data inputs

- `load_gold_holdings()` — 3,932 real holdings (1979–2015). The ALJ tag lives
  in each holding's `cites: [{district, alj}]` (**surname only**). 3,802
  holdings carry ≥1 ALJ cite; **535 name an ALJ in the prose itself** ("In ALJ
  Doyle's cases…", "ALJ refused evidence offered to show…"). Fields used:
  `cites`, `category_canonical`, `text`, `sort_year`, `letter_title`.
- `load_decisions()` — 267 structured decisions (**2004, 2009 only**). Per
  holding: `ruling.prevailing_party` (`district` 608 / `respondent` 192 /
  `none_ruled` 17 / `mixed` 18 — 100% present), `arguments:[{party,summary}]`
  (97%), `authorities`, `issue.category/subtype`. ALJ from `identity.alj.raw`
  → `alj_surname()`. 54 ALJs, 835 holdings.
- **Join key: ALJ surname** (gold cites are surname-only). Corpus respondent-win
  base rate on decided structured holdings = **0.240**.

**Known limits that bound the result — state these in FINDINGS:**
- **Surname conflation.** `Johnson` = *two* people (Perry O. Johnson AND
  Vallera J. Johnson). Surname-only joining merges them. Detect collisions from
  the decision records' raw full names; mark such surnames `ambiguous` and
  sequester them from the shipped set. Gold-only surnames can't be
  disambiguated at all — every report carries the caveat.
- **Structured outcomes are 2 years only.** Win-rate tendencies rest on small
  per-ALJ n (12–69 decided holdings) from 2004/2009, confounded by case mix
  (which districts/issues that ALJ happened to draw), not longitudinal.
- **Gold has no structured outcome.** It gives a 35-year *issue footprint*; who
  won is in the prose, not a field. Gold is **editorial, not exhaustive** —
  issue mix reflects what editors catalogued, not the ALJ's full docket.

## Compute profile

`local-LLM-light` for the synthesis layer; **the verdict-bearing core is
`none`** (pure statistics, stdlib only). Synthesis model: **subagent fan-out**
(Claude via Agent tool / Workflow) for idea-validation, plus a **local
spot-run** (gemma4:31b and/or qwen3.5:122b) to record local feasibility. Check
`gpu_status()` before any local run. GPU-busy fallback is the design itself:
the entire deterministic core + discriminability test needs no GPU; only the
prose presentation needs a model, and that is the fan-out pattern. A
subagent-written report validates **the idea** (can grounded ALJ prose be
written from a dossier); a local re-run is required to claim **local
feasibility** — FINDINGS names the backend per result.

## Approach

Five stages. **Stages 1–3 are the experiment (deterministic, no LLM); 4–5 are
the product demo.** The verdict can be reached from 1–3 alone.

1. **Evidence assembly (`common.py`).** Per ALJ surname, gather:
   - gold holdings citing them (text already de-ID'd by volume convention),
     each with category + year + the district cited;
   - structured 2004/2009 holdings from their decisions, with
     `prevailing_party`, arguments-by-party, authorities, **de-identified via
     `deidentify(text, rec)` at assembly time** (build-time de-ident lesson);
   - the subset of gold prose that names them inline (regex `ALJ <Name>` /
     `(<Name>)` attribution) — the editors' own observations, verbatim + cite.

   Emit a per-ALJ **density block**: `gold_cites`, `structured_holdings`,
   `years_span`, `n_categories`, `n_districts`, `prose_mentions`. Detect
   surname collisions (≥2 distinct `identity.alj.raw` full names → `ambiguous`).

2. **Tendency stats (`tendencies.py`)** — deterministic, every stat carries its
   supporting cite list:
   - *Issue footprint*: distribution over canonical categories vs corpus base
     rate; over/under-represented categories with the cited holdings behind
     each.
   - *Outcome tendency*: respondent-win rate on decided structured holdings,
     **Wilson 95% CI**, vs base 0.240; z and **BH-FDR-corrected** significance
     across the tested ALJs.
   - *Procedural posture*: rate/identity of procedural-category holdings + the
     editor prose flagging procedural rulings (notice, service, evidence
     exclusion).
   - *Authorities*: authorities cited above their corpus rate.
   - *Persuasive arguments*: for decided holdings, which party's argument
     prevailed, by category (structured `arguments` × `prevailing_party`).

3. **Discriminability / horoscope test (`discriminate.py`) — the falsification
   core.** Two questions:
   - *Do ALJs differ beyond noise?* **Permutation test**: shuffle ALJ labels
     across holdings (≥5,000 perms, seeded), recompute the spread of per-ALJ
     win-rates and an issue-mix χ²-like statistic; compare observed to the null.
     Report the permutation p-value and how many ALJs survive BH-FDR on
     win-rate. (Sniff: Waxman 0.57 / Brandt 0.69 / Flores 0.48 high; Cole 0.00 /
     Harman 0.07 / Rasmussen 0.11 low vs 0.24 — several should survive; issue
     mix: Sarli skipping 0.39 vs 0.13.)
   - *Era/district confound*: compare an ALJ's issue mix to the pooled mix of
     the districts/years they served, to gauge how much "footprint" is just
     docket draw vs ALJ-specific.

4. **Dossier assembly (`build_dossiers.py`).** For the top-N density,
   non-ambiguous ALJs, write `output/dossiers/{alj}.json` containing exactly the
   de-identified evidence a synthesis prompt would inject: density block, stats
   block (with CIs + significance flags), the editor-attributed prose verbatim
   with cites, and a per-category sample of structured holdings (issue, outcome,
   key arguments, authorities). These are the batch inputs for fan-out.

5. **Synthesis + verification (Workflow fan-out).** Pipeline per ALJ:
   - *Synthesize*: a subagent reads `dossiers/{alj}.json` and writes a scouting
     report. **Hard rules**: every tendency claim cites the supporting
     holding(s) from the dossier; no claim without a cite; state data thinness
     where n is small; no respondent names. Sections: *Issue footprint /
     Outcome tendencies / Procedural posture / Persuasive arguments / Watch-outs
     & data caveats.*
   - *Verify (adversarial)*: a second subagent checks each claim (i) traces to a
     dossier cite (**grounding**) and (ii) is ALJ-specific, not generic
     (**horoscope**) — flag any claim equally true of a random ALJ. Per-report
     verdict: grounded% and horoscope%.
   - *Discriminability judge*: given two **name-stripped** reports, can the judge
     match each to its dossier? Real signal ⇒ separable; chance ⇒ generic prose.
   - *Local spot-run*: regenerate 1–2 reports with a local model for the backend
     note.

## Deliverables

- `common.py`, `tendencies.py`, `discriminate.py`, `build_dossiers.py`, a small
  `cli.py` that prints a dossier/report as markdown.
- `output/` (gitignored): per-ALJ dossiers, synthesized reports,
  discriminability results, verification verdicts.
- One **committed**, fully de-identified example scouting report (District
  (ALJ)-cite only) as `sample_report.md`, hand-checked for names.
- `FINDINGS.md` with discriminability numbers + grounding%; STATUS.md dashboard
  + lessons updated; README gallery row; IDEAS/dashboard state.

## Success criteria

- **Density** — ≥10 ALJs clear a usable bar (predict 26 at ≥50 gold cites; 77
  at ≥10). <10 ⇒ falsified-by-thinness.
- **Discriminability** — per-ALJ win-rate spread exceeds the permutation null
  (p<0.05) **and** ≥5 ALJs survive BH-FDR; issue-mix beats its null. If
  win-rates are indistinguishable from shuffled labels ⇒ falsified-by-horoscope.
- **Grounding** — ≥90% of synthesized claims trace to a dossier cite. <90% ⇒
  the prose layer hallucinates; ship stats-only.
- **Horoscope (prose)** — the discriminability judge matches name-stripped
  reports to dossiers clearly above chance. At chance ⇒ prose is generic even if
  the stats aren't.

## Out of scope

- No per-ALJ predictive model ("this ALJ will rule X on your case") — W5
  territory; 2-year data can't support it.
- No cross-ALJ ranking / "toughest ALJ" leaderboard — invites misuse and the
  data won't support a defensible ranking.
- No disambiguation research on conflated surnames beyond flag-and-sequester.
- No UI; `cli.py` prints markdown.

## Privacy notes

Everything keys on **District (ALJ surname)** — the volumes' own convention.
Respondent names: gold prose is already de-identified by the volumes; structured
holding text passes through `deidentify(text, rec)` at assembly time. Dossiers
and reports carry District (ALJ) cites only. The committed `sample_report.md` is
hand-checked for names before commit. **ALJ names are public adjudicator
identities in public decisions — in scope to name, exactly as the volumes do.**
