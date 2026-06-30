# Difficulty-stratified test suite — FINDINGS

Status: **instrument BUILT + VALIDATED** (2026-06-30). Supersedes the 72-case thick
set for technique comparison. All numbers de-identified; District(ALJ)-only if committed.

## What it is
399 matter-issues sampled from the full 823-decision / 2,448-holding corpus (`suite.json`),
stratified by era × outcome with known weights (199 resp / 200 district; over-sample
exposure ~4× for power, re-weightable to the 23% corpus base rate). Issue-covered
(every major category ≥13), 82 ALJs. Each case difficulty-labeled by a **blind Opus
rating** (facts + issue only, no outcome) that also yields a blind closed-book prediction
(= Opus frontier reference). Files: `build_candidate_pool.py`, `build_suite.py`,
`difficulty_{prep.py,judge.js,eval.py}`, `output/{candidate_pool,suite,difficulty.*}.json`.

## VALIDATION — the difficulty label is real
Opus blind accuracy falls monotonically down its own difficulty scale:
| diff | n | acc | resp_acc |
|---|---|---|---|
| 1 | 28 | 82% | 86% |
| 2 | 232 | 76% | 57% |
| 3 | 82 | 67% | 59% |
| 4 | 55 | 53% | 51% |
| 5 | 2 | 50% | — |
Opus frontier overall: **acc 71% / resp_acc 58%** on this balanced suite.

## Load-bearing findings
1. **Cheap model-free difficulty signals FAILED.** Editorial inclusion (incl 2.41 vs not
   2.35), per-issue base rate (corr 0.02), reasoning length (corr −0.06) — none track
   case-level difficulty. Stratifying on them would have produced a difficulty axis that
   doesn't track difficulty. **Only the model (Opus) judgment works** → Nick's Opus-rating
   idea was essential, not optional.
2. **Real headroom exists.** Opus blind = 53% on hard / 58% on resp — hard cases are hard
   even for the frontier, so "does the corpus help DIRECTION on hard cases?" is now
   answerable on a set with room to help (the old 80% was likely an easy-case ceiling).
3. Issue is a weak difficulty signal (seniority hardest 2.88 → attrition 2.20); difficulty
   is mostly case-level, not category-level.

## Decisions (2026-06-30)
- Model-disagreement pass: SKIP (Opus rating validated + is itself a model judgment;
  local-disagreement adds little at high GPU cost). Revisit only if a second independent
  signal is wanted.
- Hard stratum = 57 (diff 4-5); 139 at diff 3-5. Sufficient if difficulty treated as
  graded; can rate more candidates (~14% land hard) for a beefier stratum if needed.

## Next
Run the technique comparison (cb / naive-RAG / balanced-RAG / predict-then-ground) on
the 399 suite with a local base, **sliced by difficulty** — the experiment the suite was
built for. Multi-hour GPU run (5× the old set).
