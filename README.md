# cert_layoff_playground

Prototyping experiments on a corpus of California OAH certificated-employee
(teacher) layoff decisions — Education Code §§ 44949/44955.

## Background

California school districts lay off teachers through a statutory process;
disputes go to the Office of Administrative Hearings, where an ALJ issues a
proposed decision. These decisions are not published or searchable anywhere.
My firm assembled a large set via Public Records Act requests, and for
decades attorneys hand-wrote annual summary volumes cataloguing each year's
holdings by issue — a practice that died out in the mid-2010s.

A previous project built and validated an LLM extraction pipeline that turns
each decision into a rich structured record (issues, holdings, arguments by
party, facts, authorities, reasoning, dispositions). A production run over
the full ~2,800-decision corpus is upcoming.

**This repo asks: what could we build on top of that corpus?** It is a
deliberate playground — many small prototypes, each testing one idea, each
ending in an honest verdict. Falsifying an idea cheaply counts as success.
The aim is that when the full corpus lands, there's a portfolio of validated
concepts ready to build for real, not guesses.

Everything runs against a two-year sample corpus (plus 35 years of parsed
human summary holdings) on local LLMs — AMD Strix Halo, 128GB unified
memory, models up to ~128B via ollama.

## The data is not here

The underlying decisions were obtained via CPRA and contain individuals'
names. The corpus lives outside this repo, all derived outputs are
untracked, and anything committed cites decisions de-identified — by
district and ALJ only — following the convention of the original human
volumes.

## Prototype gallery

| ID | Prototype | State | Verdict |
|----|-----------|-------|---------|
| 01 | [Hybrid corpus search + MCP server](prototypes/01-search-mcp/SPEC.md) | **validated** | BM25+embedding hybrid over holdings; known-item R@10 0.87–0.95; corpus exposed as MCP tools for agent sessions. [FINDINGS](prototypes/01-search-mcp/FINDINGS.md) |
| 02 | [Editorial-taste judge](prototypes/02-taste-judge/SPEC.md) | **partially validated (weak)** | Can an LLM reproduce the human editors' selection of "noteworthy" holdings? It loses to a simple logistic regression and adds no signal; both fall to ~chance on a held-out year. Taste is mostly mechanical and year-specific — curate with a transparent feature filter, not an LLM gate. [FINDINGS](prototypes/02-taste-judge/FINDINGS.md) |
| 03 | [ALJ scouting reports](prototypes/03-alj-scouting/SPEC.md) | **validated** | Per-judge dossiers — issue footprint, outcome tendencies, procedural posture, and the human editors' own attributed observations. A permutation test confirms the tendencies are real, not a horoscope (ALJs differ in win-rate and issue mix beyond chance, surviving a within-year control); only the deterministic, fully-cited render is shipped, with a thin LLM narrative that stays 99% grounded. [sample](prototypes/03-alj-scouting/sample_report.md) · [FINDINGS](prototypes/03-alj-scouting/FINDINGS.md) |
| 04 | [Corpus deep-research harness](prototypes/04-deep-research/SPEC.md) | **validated (stage 1)** | Can an agent use the corpus as a tool to answer hard, multi-step longitudinal questions? Across four questions, ~100% of cited holdings were grounded on independent re-query and most insights were genuinely non-obvious; the failure mode is subtle legal over-generalization in prose (not invented cites), caught by an adversarial verify pass. [sample memo](prototypes/04-deep-research/sample_memo.md) · [FINDINGS](prototypes/04-deep-research/FINDINGS.md) |

*(see [IDEAS.md](IDEAS.md) for the full slate)*

## Repo layout

- `IDEAS.md` — the idea ledger, from concrete candidates to half-formed concepts
- `STATUS.md` — live dashboard of prototype states + cross-cutting lessons
- `prototypes/NN-slug/` — one directory per prototype: `SPEC.md` (detailed
  enough to build from cold), code, `FINDINGS.md` (the verdict)
- `corpuslib/` — shared data-access layer and a thin LLM shim over local
  ollama
- `templates/` — SPEC and FINDINGS templates
