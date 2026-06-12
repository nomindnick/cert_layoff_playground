# FINDINGS — 01. Hybrid corpus search + MCP server (F1)

## Verdict

**Validated.** Hybrid BM25 + local-embedding retrieval over the layoff corpus
comfortably clears the SPEC bar (2009: Recall@10 0.868, MRR 0.766 vs targets
0.75 / 0.5; 2004: Recall@10 0.951, MRR 0.823), attorney-style smoke queries
return on-point, properly cited results, and the corpus is now exposed as an
MCP server registered in the repo's `.mcp.json` — every future Claude Code
session in this repo has `search_holdings` / `search_gold_holdings` /
`search_decisions` / `get_holding` / `get_decision` / `list_facets` as tools.
The substrate for P4/P5/W7/W9/W10 exists.

## What we learned

**Known-item eval** (query = human gold-volume text, target = the specific
extracted holding the lab's alignment matched it to; year-filtered):

| Year | Mode | R@5 | R@10 | MRR |
|------|------|-----|------|-----|
| 2009 (n=235) | bm25 | 0.821 | 0.877 | 0.778 |
| 2009 | embed (arctic) | 0.817 | 0.855 | 0.725 |
| 2009 | hybrid | 0.834 | 0.868 | 0.766 |
| 2004 (n=103) | bm25 | 0.932 | 0.951 | 0.850 |
| 2004 | embed (arctic) | 0.854 | 0.913 | 0.780 |
| 2004 | hybrid | 0.922 | 0.951 | 0.823 |

- **BM25 alone slightly beats hybrid on this eval.** Expected circularity:
  the alignment pairs were created by token-similarity matching, so the eval
  is biased toward lexical retrieval. Embedding-only being within ~2 points
  shows semantic search is genuinely competitive; the smoke demo (paraphrase
  queries like "can a district skip BTSA induction support teachers") is
  where hybrid earns its keep. Keep hybrid as default.
- **Misses concentrate in `seniority`** (14 of 31 hybrid misses@10 in 2009) —
  the largest, most lexically homogeneous category, where the true item ranks
  below near-duplicate holdings from other cases. Benign failure mode for an
  attorney (top hits are still correct-issue holdings), but a real signal for
  W7: near-duplicate holdings cluster tightly, which is exactly what the
  dedup layer needs.
- **2004 (OCR-era) outscores 2009.** Retrieval over *extracted holdings* is
  insulated from OCR noise — the extraction layer already normalized the
  text, and the smaller per-year pool (74 vs 193 cases) makes ranking easier.
  OCR damage shows up in extraction recall (the lab's 66% vs 82%), not here.
- **Embedding model:** arctic-l-v2 > bge-large on this corpus (2009 hybrid
  R@10 0.868 vs 0.838; embed-only 0.855 vs 0.809) — same ordering as the
  FPPC benchmark. Arctic is the default; both indexes are kept.
- **Privacy by construction:** respondent names are de-identified (lab's
  `deidentify` pass) at *index build time*, so search results and snippets
  are District (ALJ)-safe everywhere downstream, not just at render points.
  `get_decision` deep-de-identifies on read and passed a roster-leak audit.
  Known boundary (inherited from the lab's convention): *non-roster* names —
  e.g. a retained junior employee discussed in a holding — are not redacted.
- Cosmetics worth carrying to production: a few holdings have empty
  `summary_style_holding` (display falls back to composed text);
  `title_case` renders "Placentia-Yorba Linda" as "Placentia-yorba Linda"
  (hyphen handling).

## Backend notes

No LLM anywhere — CPU-only sentence-transformers (arctic-l-v2, 568M params).
Full build: ~5 min for ~4.8k docs on CPU; queries ~0.2s. Fully GPU-independent,
so this prototype (and its index rebuilds) never competes with corpus
extraction runs. The MCP server loads the embedding model lazily on first
search (~5s); `HF_HUB_OFFLINE=1` silences hub HEAD-request chatter.

## Blocked on full corpus?

Nothing blocks; everything re-points via `corpuslib` (`$CORPUS_ROOT`) and
rebuilds in minutes (content-hash build-or-load). At ~2,800 cases /
~10k holdings, brute-force cosine over a numpy matrix is still trivially
fast — no ANN index needed. The known-item eval re-runs wherever the lab's
alignment files exist (gold-covered years only). Expect the seniority
near-duplicate effect to grow with corpus size; if it bothers attorneys,
that's a display/grouping problem (cluster near-identical holdings), not a
retrieval problem.

## Production recommendation

**Build — query-time feature of the main app** (the search/browse core), plus
the MCP server as the permanent agent-facing surface (substrate for W9 deep
research and any future agent work). Port notes: keep build-time
de-identification, add the near-duplicate grouping idea to the UI backlog,
fix the two cosmetics above, and consider serving both gold and extracted
collections in one UI with a clear "editorial volumes vs extracted records"
distinction.
