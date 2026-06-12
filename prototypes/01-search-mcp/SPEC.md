# SPEC — 01. Hybrid corpus search + MCP server (F1)

> Written so a fresh Claude Code session told only "Prototype 01, go build
> it" can implement this unattended. Read the repo root `CLAUDE.md` and
> `STATUS.md` first.

## Hypothesis

Hybrid BM25 + local-embedding retrieval over the layoff corpus returns the
right holdings for issue-shaped natural-language queries — measurably
(known-item eval below) and usably (an MCP server a Claude session can lean
on as a research tool). Falsified if recall on the known-item eval stays low
after honest tuning, or if results are too noisy to ground agent work.

## Why it matters

This is the substrate prototype (capability-ladder rung 1). P4/P5 query it,
W7 uses it for novelty checks, W9-stage-1 (deep research via a Claude session
+ this MCP server) becomes nearly free once it exists, W10 uses it for
candidate search. It is the most load-bearing and least risky prototype —
a port of validated FPPC patterns to a new corpus.

## Prior art to reuse (read before designing)

- `/home/nick/Projects/fppc-opinions-app/backend/` — production hybrid
  search: `search/engine.py` (BM25 + embedding score fusion),
  `mcp_server.py`, build-or-load index pattern. Port the *patterns*, not the
  code wholesale (that engine is citation-routing-specific and uses OpenAI
  embeddings; we use local embeddings).
- `/home/nick/Projects/fppc-tuned-embeddings/` — benchmarked open embedding
  models on legal-retrieval text. See `scripts/check2_open_baselines.py`
  (`MODELS` dict, incl. required query/doc prefixes) and `results/` for
  which open model won. Pick the best open model from those results
  (likely a bge or nomic variant); do NOT use OpenAI (no API spend) and do
  NOT fine-tune (out of scope).

## Data inputs

All via `corpuslib` (`from corpuslib import load_decisions, load_gold_holdings, load_taxonomy, load_case_index`).

Three searchable collections:

1. **`holdings`** — extracted holdings from the 267 decision records
   (2009 ≈193 cases / 2004 ≈74). Unit = one holding. Per record
   (`load_decisions()` yields `(case_no, record)`); each `record["holdings"][i]`
   has `issue.category/statement/subtype`, `ruling.prevailing_party/remedies`,
   `arguments[]`, `facts[]`, `authorities[]`, `reasoning.summary/quotes`,
   `summary_style_holding`. Compose the embedded/BM25 text as
   `issue.statement + summary_style_holding + reasoning.summary` (keep the
   composition a single function so it's easy to revisit). Holding ID =
   `f"{case_no}:{holding_idx}"`.
2. **`gold_holdings`** — 3,955 rows, 1979–2015, via `load_gold_holdings()`.
   Fields: `sort_year`, `category_raw`, `category_canonical[]`, `text`,
   `cites[] ({district, alj})`, `letter`, `item_number`. **Gotcha:** rows
   with `category_raw == None` are volume headers/front-matter — exclude
   from the index. Searchable text = `text`.
3. **`decisions`** — the 267 full records for case-level lookup and
   full-text BM25 (`record["full_text"]`). No embedding chunking — BM25
   only is fine here; embeddings operate on the holdings collections.

Facet/filter fields:
- holdings: `year` (first 4 digits of case_no — `identity.decision_date` is
  sometimes null, never key on it), `category` (issue.category), `district`
  (identity.district.raw; canonical is currently null), `alj`
  (identity.alj.raw), `prevailing_party`, `overall` (outcome.overall),
  `decision_kind`.
- gold_holdings: `sort_year`, `category_canonical`, cite `district`/`alj`.

Known data limitations to carry into FINDINGS: only 2 extracted years; 2004
text carries OCR noise; gold holdings are editorial (not exhaustive);
district/ALJ strings are raw (not canonicalized — exact-match filters will
miss spelling variants; note instances, don't solve canonicalization here).

## Compute profile

`embeddings`. ~4.2k gold + ~600 extracted holdings — minutes of embedding,
CPU-viable (sentence-transformers). GPU-busy fallback: fully functional on
CPU; no LLM calls anywhere in this prototype. Full validation possible
without the GPU.

## Approach

1. **Prototype venv** (`prototypes/01-search-mcp/.venv`): `rank_bm25`,
   `sentence-transformers`, `numpy`, `mcp` (official Python SDK / FastMCP).
2. **`build_index.py`** — build-or-load: compose docs from corpuslib, embed
   (respecting the model's query/doc prefixes), tokenize for BM25, pickle
   to `output/indexes/` keyed by a content hash of the source docs +
   model name. Idempotent; rebuilds only on corpus/model change.
3. **`engine.py`** — `search(collection, query, filters=None, k=10)`:
   BM25 ranks + embedding cosine ranks → **RRF fusion** (k=60) as the
   default; apply filters as pre-restriction of candidates, not
   post-filtering of top-k (so filtered queries still return k results).
   Also `get_decision(case_no)`, `list_facets(collection)`.
4. **`eval_known_item.py`** — see Success criteria. Run for 2009 and 2004
   separately. Also report BM25-only and embedding-only baselines so the
   hybrid's contribution is visible (FPPC lesson: fusion wins, but prove it
   on this corpus).
5. **`cli.py`** — thin manual-testing CLI: `query`, `--collection`,
   `--filter k=v`, pretty-printed results with District (ALJ) cites.
6. **`mcp_server.py`** — stdio MCP server (FastMCP) exposing:
   - `search_holdings(query, year=None, category=None, district=None,
     alj=None, prevailing_party=None, k=10)` → holding summaries + IDs +
     District (ALJ) cites
   - `search_gold_holdings(query, year=None, category=None, k=10)`
   - `get_decision(case_no, include_full_text=False, deidentify=True)` —
     deidentify replaces roster names with their R-refs (reuse the approach
     of the lab's `render_summary.py` de-identification pass); full_text
     excluded by default for context economy
   - `get_holding(holding_id)` — the full rich holding record
   - `list_facets(collection)` — available categories/ALJs/districts/years
   Register it in a committed project `.mcp.json` at repo root so any
   Claude Code session in this repo gets the tools.
7. **Smoke demo for FINDINGS**: 8–10 hand-written natural queries an
   attorney would ask ("can a district skip BTSA-trained teachers",
   "tie-breaking criteria lottery", "competency criteria for bumping",
   "untimely request for hearing waiver") — eyeball and record results
   (de-identified) in FINDINGS.

Experiments-within-the-experiment (uncertain parts, time-box them):
- Which embedding model wins on the known-item eval (try the top 1–2 from
  fppc-tuned-embeddings results, report both).
- Whether composing holding text with vs without `reasoning.summary`
  changes recall materially.

## Deliverables

`build_index.py`, `engine.py`, `eval_known_item.py`, `cli.py`,
`mcp_server.py`, repo-root `.mcp.json` entry, `FINDINGS.md`, and an updated
root `STATUS.md` + README gallery row.

## Success criteria

**Known-item eval** (deterministic, from existing lab artifacts): for each
gold entry in `{corpus_root}/eval/alignment_{year}.json` (`gold` list) with
`status == "recovered"`, query = the gold entry's `text`, target = extracted
holding `f"{case_no}:{holding_idx}"`. Search the `holdings` collection
(filtered to that year); report Recall@5, Recall@10, MRR.

- Validated: hybrid Recall@10 ≥ 0.75 and MRR ≥ 0.5 on 2009, with 2004
  reported honestly (OCR noise may drag it; explain gaps, don't tune them
  away).
- These targets are judgment calls, not contracts — if results land near
  the line, FINDINGS should argue the verdict from the failure cases, not
  the raw number alone.
- Plus the smoke demo: results an attorney would call relevant, recorded in
  FINDINGS.

## Out of scope

Web UI (production decision, later). Query-time LLM synthesis or re-ranking
(W9's territory). Embedding fine-tuning. District/ALJ canonicalization
(note the problem, don't solve it). Cross-linking gold ↔ extracted holdings
beyond what the alignment files already provide. Anything write-side.

## Privacy notes

Extracted holdings/decisions contain respondent names (quotes, facts,
roster, full_text). The MCP server and CLI are local-only tools — fine. But:
`get_decision` defaults to `deidentify=True`; anything committed (FINDINGS
examples, eval outputs, smoke-demo transcripts) cites District (ALJ) only
and never includes roster names. `.mcp.json` and all code are safe to
commit; `output/` (indexes) is already gitignored.
