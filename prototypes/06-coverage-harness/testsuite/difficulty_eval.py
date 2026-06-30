#!/usr/bin/env python3
"""Analyze the blind Opus difficulty rating.

The load-bearing check is VALIDATION: does Opus's own blind-prediction accuracy fall
as its rated difficulty rises? If yes, "difficulty" is a real signal (it predicts where
even a frontier model fails). Also reports Opus frontier accuracy (blind cb reference)
and whether the cheap signals (editorial inclusion / per-issue base rate / reasoning
length) track the Opus difficulty rating.

  difficulty_eval.py [--scored output/difficulty.scored.json --meta output/difficulty.meta.json]
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def _corr(x, y):
    n = len(x)
    if n < 2:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sx = sum((a - mx) ** 2 for a in x) ** 0.5
    sy = sum((b - my) ** 2 for b in y) ** 0.5
    return cov / (sx * sy) if sx and sy else 0.0


def _inc(r):
    return "incl" if r["included"] else ("not" if r["included"] is False else "unknown")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", default="output/difficulty.scored.json")
    ap.add_argument("--meta", default="output/difficulty.meta.json")
    a = ap.parse_args()
    scored = {s["code"]: s for s in json.loads(Path(a.scored).read_text()) if s.get("difficulty")}
    meta = json.loads(Path(a.meta).read_text())
    rows = [{**meta[c], "difficulty": s["difficulty"], "predicted": s["predicted"]}
            for c, s in scored.items() if c in meta]
    n = len(rows)
    gr_all = [r for r in rows if r["truth"] in ("district", "respondent")]
    print(f"=== rated {n} items ===")
    dd = Counter(r["difficulty"] for r in rows)
    print("difficulty dist (1=easy..5=hard):", {k: dd.get(k, 0) for k in (1, 2, 3, 4, 5)})

    print("\n=== VALIDATION: Opus blind accuracy by rated difficulty (should fall as diff rises) ===")
    print(f"{'diff':>5}{'n':>5}{'acc':>7}{'resp_acc':>10}")
    for d in (1, 2, 3, 4, 5):
        gr = [r for r in gr_all if r["difficulty"] == d]
        if not gr:
            continue
        acc = sum(r["predicted"] == r["truth"] for r in gr) / len(gr)
        rsub = [r for r in gr if r["truth"] == "respondent"]
        racc = (sum(r["predicted"] == "respondent" for r in rsub) / len(rsub) * 100) if rsub else float("nan")
        print(f"{d:>5}{len(gr):>5}{acc * 100:>6.0f}%{racc:>9.0f}%")

    acc = sum(r["predicted"] == r["truth"] for r in gr_all) / len(gr_all)
    rsub = [r for r in gr_all if r["truth"] == "respondent"]
    racc = sum(r["predicted"] == "respondent" for r in rsub) / len(rsub)
    print(f"\nOpus frontier (blind cb) overall: acc {acc*100:.0f}% | resp_acc {racc*100:.0f}% "
          f"(n_resp={len(rsub)})")

    print("\n=== do the cheap signals track Opus difficulty? ===")
    for lab in ("incl", "not", "unknown"):
        sub = [r for r in rows if _inc(r) == lab]
        if sub:
            print(f"  inclusion={lab:<8} n={len(sub):<4} mean_diff={sum(r['difficulty'] for r in sub)/len(sub):.2f}")
    print(f"  corr(difficulty, per-issue base_rate_resp): {_corr([r['difficulty'] for r in rows], [r['base_rate_resp'] for r in rows]):.2f}")
    print(f"  corr(difficulty, reason_words):             {_corr([r['difficulty'] for r in rows], [r['reason_words'] for r in rows]):.2f}")

    print("\n=== mean Opus difficulty by issue (hardest first) ===")
    byiss = defaultdict(list)
    for r in rows:
        byiss[r["issue"]].append(r["difficulty"])
    for iss, ds in sorted(byiss.items(), key=lambda x: -sum(x[1]) / len(x[1])):
        if len(ds) >= 8:
            print(f"  {iss:<24} n={len(ds):<4} mean={sum(ds)/len(ds):.2f}")


if __name__ == "__main__":
    main()
