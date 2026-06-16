# FINDINGS — 03. ALJ scouting reports (P2)

## Verdict

**Validated, with disciplined caveats — build it (the deterministic version).**
Per-ALJ scouting reports are real and buildable now. The load-bearing test was
whether per-ALJ "tendencies" are genuine signal or a **horoscope** (equally true
of any ALJ); a permutation test answers clearly: as a group, ALJs differ in both
respondent-win rate and issue mix **far beyond chance, surviving a within-year
control** (permutation p≈0.0003 each). It is not a horoscope. The honest limits
are equally clear: (1) only ~59 ALJs clear a usable density bar; (2) with only
two years of structured outcomes, **individual** win-rate tendencies are mostly
too thin to name — after multiple-comparison correction across 23 testable ALJs,
only **2** (District(Brandt), District(Waxman)) have a statistically defensible
respondent-lean; (3) the strong, ALJ-specific *issue footprint* is "what this
ALJ hears" (docket draw), not "how they rule." The trustworthy product is a
**deterministic, fully-cited dossier render** plus the human editors' own
attributed observations — not an LLM that narrates tendencies into existence.

## What we learned

### Density — clears the bar (success criterion: ≥10 ALJs)
228 distinct ALJs appear in the gold cites, but the tail is steep (median 3
cites). Usable population:

| Threshold | ALJs |
|---|---|
| ≥50 gold cites | 26 |
| ≥20 gold cites (the bar used) | 60 raw → **59 usable** (District(Johnson) sequestered: it conflates two judges) |
| ≥10 gold cites | 77 |

For the 2004/2009 structured layer: 54 ALJs, 835 holdings, 100% with a
`prevailing_party`. 23 ALJs have ≥12 decided holdings (win-rate testable).

### Discriminability — REAL, not a horoscope (the core test)
Permutation tests (5,000 shuffles, stdlib), with a stricter within-year null
that controls for temporal drift (e.g. "skipping" surging in post-2008 budget
years):

| Test | statistic | p (global) | p (within-year) | verdict |
|---|---|---|---|---|
| Win-rate dispersion (26 ALJs, 589 decided holdings) | Q=57.9 | 0.0006 | **0.0004** | real |
| Issue-mix dispersion (59 ALJs × 22 categories, 3,458 units) | χ²=2343 | 0.0002 | **0.0002** | real, ALJ-specific |

The within-year survival is the important part: the spread isn't just the corpus
drifting over time, it's ALJ-to-ALJ. Strongest issue fingerprints (standardized
residual): District(Sarli)/skipping **+8.7** (56 obs vs 18.5 expected),
District(Lew)/bumping +4.4 & competency +4.1, District(Walker)/bumping +4.0,
District(Benjamin)/seniority +4.9, District(Vorters)/tie-breaking +3.4.

### Outcome tendencies — real as a group, thin per-ALJ
Corpus respondent-win base = 0.240. Per-ALJ win rates range from 0.00 to 0.69.
But across 23 simultaneous tests, Benjamini-Hochberg (q=.05) leaves only:
- **District(Brandt)**: 0.69 respondent-win (n=13), q=.009
- **District(Waxman)**: 0.56 respondent-win (n=23), q=.009

District(Flores) 0.48, District(Walker) 0.56, District(Cole) 0.00 are nominally
notable (p<.05 uncorrected) but do **not** survive correction — the right call
to make on a two-year sample, and exactly the "validate beyond a single slice"
discipline W7 taught. The group-level permutation result says the *signal* is
real; the per-ALJ thinness says *naming individuals* needs the full corpus.

### The editors already wrote ALJ tendencies — 535 attributed observations
The single most trustworthy content is zero-inference: gold-volume prose that
**names the ALJ** while narrating their conduct. 535 holdings do this. Examples
(verbatim, District(ALJ)):
- *"District has discretion to select the programs it wants to reduce and the
  wisdom of that decision is not within the jurisdiction of the ALJ."* —
  Grant (Doyle), 1979
- *"The ALJ ruled that 'the argument was considered and has no merit.'"* —
  San Juan (Sarli), 2009
- *"ALJ upheld respondents' contention that the proper divisor for determining
  the number of periods in a full-time equivalent position should include the
  preparation period."* — Walnut Creek (Doyle), 1980

A gold-only ALJ (District(Doyle), 1979–1984, no structured data) still yields a
useful report from footprint + these observations — see `sample_report.md`.

### LLM synthesis layer — grounding & horoscope test (passes)
10 reports synthesized by Claude subagent fan-out, each adversarially verified by
a *second* skeptical subagent (grounding + horoscope), plus a forced-choice
discriminability judge.

| Metric | Result | Reading |
|---|---|---|
| Mean grounded% (claims tracing to a dossier fact, adversarially checked) | **99%** (94–100) | the prose does **not** invent tendencies |
| Mean ALJ-specific% (claims that aren't generic horoscope) | **83%** (65–100) | most claims discriminate; the rest are caveats/settled law |
| Discriminability forced-choice (anonymized report → its own fingerprint) | **10/10 = 100%** (chance 50%, 0.99 conf) | **decisive: not a horoscope** |

- **Grounding held the honesty line.** The only two non-grounded claims across
  ~210 were minor count slips ("6 of 13" vs 8; "13.8%" vs 12.8% corpus) — not
  fabricated cites or tendencies. Verifiers confirmed every report whose dossier
  said the win-rate was non-significant (Sarli, Lew, Reyes, Cohn, Benjamin, Cole)
  **correctly reported "no tendency"** instead of overclaiming. The "obey the
  interpretation field" rule worked.
- **The 17% "non-specific" is mostly appropriate.** It's dominated by the data
  caveats (which *should* be generic — they're disclaimers) plus settled-law
  recitations. It rises exactly where the data thins: District(Waxman) was the
  least-specific (65%) — an honest signal that a sparse ALJ's report drifts
  toward generic law.
- **Discriminability is the headline.** A judge handed a name-stripped report and
  two statistical fingerprints picked the right one **every time**, citing
  specific axes (span, issue mix, win-rate, district count). The reports carry
  enough ALJ-specific signal to be uniquely identifiable — the strongest possible
  evidence against the horoscope failure mode.

## Backend notes

- **Deterministic core (the verdict): no LLM.** `common.py` / `tendencies.py` /
  `discriminate.py` are pure stdlib; the permutation test runs in ~8s. This is
  the part the verdict rests on and it needs no GPU — important, since the
  production corpus build will occupy the GPU for weeks.
- **Synthesis (idea-validation): Claude subagent fan-out** (Workflow
  `alj-scouting-synth`, 10 ALJs; 30 agents, ~711k tokens, ~4 min). Each report
  was written by one subagent and graded by an independent skeptical subagent —
  the adversarial-verify pattern, so the grounding numbers aren't self-graded.
- **Synthesis (local feasibility): gemma4:31b** via ollama, ~140s/report
  (incl. cold model load; GPU was idle). It produced a grounded report that
  correctly reported the *robust* District(Brandt) 0.69 tendency, framed the
  issue footprint as docket draw, and cited a real holding — so local synthesis
  is feasible, not just the Claude version. (gemma's report was terser and one
  category figure should be spot-checked; the Claude reports were richer.)
- **Surname conflation is a real data hazard** (Lesson): joining gold cites
  (surname-only) to anything risks merging distinct judges — District(Johnson) =
  Perry O. + Vallera J. Detect from the decision records' raw full names
  (accent/whitespace-folded) and sequester. Gold-only surnames can't be
  disambiguated at all.

## Blocked on full corpus?

This is the prototype that most clearly *improves* with the production corpus,
and the code is ready to re-point via `corpuslib`:
- **Per-ALJ outcome tendencies** go from "real as a group, 2 nameable" to
  broadly nameable once structured outcomes span >2 years — re-run
  `tendencies.py` (BH-FDR) and `discriminate.py` unchanged; more years shrink
  every CI and let many more ALJs clear correction.
- **Active-ALJ coverage**: post-2017 decisions add the judges actually sitting
  now (gold ends 2015), which is what an attorney needs.
- **Persuasive-argument patterns** currently lean on 2004/2009 only; full
  structured data makes the "how arguments landed by issue" section dense.

## Longitudinal transfer — first multi-era test (2026-06-16)

When the production extraction shipped its first tier (93 decisions, 2018–2025),
we merged it with the 2004/2009 spike into a **360-decision, three-era** corpus
(`make_merged_corpus.sh` — pure symlinks, `corpuslib` re-points unchanged) and
re-ran the analysis via `longitudinal.py`. This is the first real test of the
"Blocked on full corpus" prediction above, and it came back **positive, with one
structural ceiling**:

- **Corpus-wide win base is era-stable**: 0.240 (2004/09) → 0.226 (2018–25),
  pooled 0.236. Fifteen years, essentially flat.
- **Group-level dispersion *strengthens* with more eras** — the strongest yet:
  win-rate dispersion across 33 ALJs / 737 holdings **Q=74, p=0.0002** (survives
  the within-era control), vs. p=0.0004 on 2009 alone and a borderline p≈0.05 on
  the 2018–25 slice alone. "ALJs genuinely differ" is now confirmed across three
  eras, not one. Issue-mix re-confirmed (p=0.0002) on the larger 5,608-holding
  gold set.
- **More data names more judges** — pooling promoted **3** ALJs past BH-FDR
  (Brandt, Waxman, **Sawyer** n=44) vs. the 2 on 2009 alone. Exactly the
  "broadly nameable at scale" prediction, demonstrated.
- **Individual tendencies persist where measurable.** Only 2 ALJs have ≥12
  decided holdings in *both* eras (Matyszewski, Montoya) — both held their side of
  the base rate (D: 0.12→0.08; R: 0.33→0.25). The 7 other cross-era ALJs show
  apparent "flips," but every flip is a tiny-sample artifact (n=1–4 in one era,
  e.g. Reyes 0.00 on a single holding) — noise, not reversal.
- **The ceiling is judicial rotation, not data volume.** Even merged, only 9 ALJs
  span both eras — judges get appointed/rotate/retire, so dense dockets rarely
  bridge a 15-year gap. The **2010–2017 bridge years** (forthcoming in the full
  corpus) are what will properly connect 2009 → 2018+.

Net: a clean *positive* update — the group finding gets stronger, individual
tendencies persist where there's data to see them, and scale names more judges,
just as predicted. The honest caveat shifts from "is it real?" to "judicial
turnover caps the per-ALJ longitudinal view until the bridge years land."

## Production recommendation

**Build — as a build-time artifact generator, deterministic-first.** The
shippable product is the **cited dossier render** (`cli.py`): issue footprint,
outcome tendency *with its significance honestly labeled*, authorities, and the
editors' verbatim attributed observations — every line traceable, safe to freeze
and serve with no query-time inference. An LLM "Bottom line" narrative over that
dossier is **safe to add** — the verification pass showed it stays grounded (99%)
and discriminating (100% identifiable), provided it is told to obey the dossier's
significance labels — but it must dress the tendencies, never be their source.
Hard product rules learned here:
**label outcome significance** (don't show 0.69 without "n=13, but robust" or
0.36 without "not distinguishable from base"); **frame issue footprint as docket,
not disposition**; **gate on density and sequester conflated surnames**. Feeds
P1 (condition the matter memo on the assigned ALJ) and W1 (the ALJ persona).
Destination: **build-time artifact generator.**
