# cert_layoff_playground

A prototyping playground exploring what can be built on a corpus of California
OAH certificated-employee (teacher) layoff decisions (Ed. Code §§ 44949/44955).
This is a "no bad ideas" space: the goal is to validate or falsify as many
product ideas as possible before the full production corpus exists, so that
corpus-day arrives with a portfolio of tested concepts instead of guesses.

This repo is **many small subprojects inside one repo**. Read this file, then
`STATUS.md`, before doing anything else in any session.

## Companion repos

- **`/home/nick/Projects/cert_layoff_lab`** — the completed extraction spike.
  Read its `PROJECT_CONTEXT.md` for the full domain brief (who Nick is, what
  the corpus is, the capability ladder). Its `MIGRATION.md` describes the
  production corpus build that will eventually replace our data source.
- **`/home/nick/Projects/cert_layoff_corpus`** — the production corpus build
  (now exists). Its `output/` holds the first tier: **93 decisions, 2018–2025**,
  schema v0.4.0 (richer than the spike — adds `procedure`, `board_action`
  including structured resolution `artifacts`, `holdings[].notable`,
  `authorities[].role/proposition`; `identity.district/alj` gained `canonical*`
  but kept `.raw`; `pks_allowed`+`pks_not_allowed` merged to `pks_reduction`).
  **Verified 2026-06-16: prototypes re-point and run unchanged** via
  `CORPUS_ROOT=/home/nick/Projects/cert_layoff_corpus/output` — same relative
  paths, non-breaking deltas (see STATUS lesson). No gold past 2015;
  `alj.canonical_id` null this run (still surname-joining). Compose multi-era
  views by symlinking decision dirs (`03-alj-scouting/make_merged_corpus.sh`).

## Data access

All corpus data is accessed through `corpuslib/` (never hardcode paths in
prototypes). Current source is the spike's output:

- **267 decision records** (2009 clean-text + 2004 image-OCR) — rich
  per-holding schema: issue, arguments by party, facts, authorities,
  reasoning, roster, per-respondent dispositions, board artifacts, full text.
- **3,955 gold holdings, 1979–2015** (19 expert-written annual volumes),
  each tagged district + ALJ + canonical issue category. A 35-year
  longitudinal dataset usable today — treat it as a first-class corpus, not
  just eval scaffolding.
- Frozen issue taxonomy, case index, 2004/2009 eval alignments.

## PRIVACY — load-bearing, this repo is public

The decision records contain respondent (teacher) names. Rules:

1. Corpus data lives **outside this repo** and is never copied in. All
   `output/` and `data/` directories are gitignored.
2. Nothing derived from decisions gets committed (findings, examples,
   screenshots, fixtures) unless it cites **District (ALJ) only** — the
   convention of the human volumes. Never a respondent name, never an
   un-checked verbatim dump.
3. When in doubt, don't commit; describe instead.

## The prototype lifecycle

```
IDEAS.md entry  →  prototypes/NN-slug/SPEC.md  →  build  →  FINDINGS.md  →  STATUS.md updated
```

- **`IDEAS.md`** (root) — the idea ledger: specific prototype ideas plus
  vaguer concepts not yet shaped into prototypes.
- **`prototypes/NN-slug/SPEC.md`** — written from `templates/SPEC.md`. Must be
  detailed enough that a fresh session told only "Prototype NN, go build it"
  can churn through implementation unattended. State the hypothesis so the
  builder knows what *falsified* looks like, not just what *done* looks like.
- **`prototypes/NN-slug/FINDINGS.md`** — written from `templates/FINDINGS.md`
  when results exist. Honest verdicts; falsified is a success outcome. Always
  record which LLM backend produced each result.
- **`STATUS.md`** (root) — dashboard + cross-cutting lessons. **Every session
  that changes a prototype's state ends by updating STATUS.md** (and the
  README gallery table if the state is user-visible). Lessons that transcend
  one prototype (model quirks, infra constraints, dead-end patterns) go in
  the Lessons section so future sessions don't rediscover them.

Each prototype is self-contained: own venv if it needs exotic deps, own
`output/` (gitignored), no imports from sibling prototypes (shared code goes
in `corpuslib/` only when a second prototype actually needs it).

## Compute

Strix Halo, 126GB unified memory (96GB GPU). Local inference via ollama is
free; wall-clock is the only cost. Models up to ~128B (qwen3.5:122b,
gpt-oss:120b, mistral-medium-3.5:128b; see `ollama list`).

- Ollama parallel-worker support is config- and version-dependent (it is
  currently configured on, from an experiment). Regardless, the production
  corpus build will swallow GPU capacity for weeks once it starts. Practical
  rule: **check GPU/memory availability before heavy testing**
  (`corpuslib.llm.gpu_status()` / `ollama ps`), front-load GPU-heavy
  prototypes, and treat GPU-busy periods as build-infrastructure time.
- Prototypes declare a **compute profile** in their SPEC (`none / embeddings /
  local-LLM-light / local-LLM-heavy`).
- **Never call Claude from code** (`claude -p` bills at API rates, not the
  subscription). In-session subagents DO use the subscription, so the cloud
  fallback is **subagent fan-out orchestrated by the main session**: code
  writes batch input files containing exactly the data a prompt would
  inject, the session spawns parallel Agent subagents with instructions,
  each writes an output file, code validates/merges (hard-fail on
  missing/extra entries). Worked example: cert_layoff_lab's
  `annotate_summary.py --skeleton/--merge` flow. A subagent result validates
  the idea, not local-model feasibility — FINDINGS must say which backend
  produced what.

## Working style

- Prototypes are prototypes: optimize for answering the hypothesis, not for
  polish. Throwaway code is fine; misleading results are not.
- Honest pushback over agreement. If an idea is failing, say so in FINDINGS
  and move on — falsifying cheaply is the point of this repo.
- Nick is an attorney-builder: domain claims get scrutiny from him; don't
  over-explain basic programming, do flag downstream consequences of
  technical choices.
