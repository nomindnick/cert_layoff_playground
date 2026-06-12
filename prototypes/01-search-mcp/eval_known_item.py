#!/usr/bin/env python3
"""Known-item retrieval eval from the lab's gold alignment files.

For each gold entry with status == "recovered" in alignment_{year}.json,
query = the gold entry's text, target = extracted holding "{case_no}:{idx}".
Searches the holdings collection restricted to that year; reports Recall@5,
Recall@10, MRR for bm25 / embed / hybrid so the fusion has to earn its keep.

Caveat for FINDINGS: the alignment was computed by token-similarity matching
within a case, so gold text and target holding are known to be lexically
related — this eval measures whether ranking over the WHOLE year's holdings
recovers the right one, not whether the pairing exists.

Usage: eval_known_item.py [--model arctic-l-v2|bge-large] [--years 2009 2004]
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from corpuslib import corpus_paths  # noqa: E402
from engine import Engine  # noqa: E402

MODES = ("bm25", "embed", "hybrid")


def eval_year(eng, year):
    align = json.loads((corpus_paths()["eval"] / f"alignment_{year}.json").read_text())
    items = [g for g in align["gold"] if g["status"] == "recovered"]
    results = {m: [] for m in MODES}  # list of ranks (None = not found)
    for g in items:
        target = f"{g['case_no']}:{g['holding_idx']}"
        for mode in MODES:
            rank = eng.rank_of("holdings", g["text"], target,
                               filters={"year": year}, mode=mode)
            results[mode].append(rank)
    report = {}
    for mode, ranks in results.items():
        n = len(ranks)
        report[mode] = {
            "n": n,
            "recall@5": round(sum(1 for r in ranks if r and r <= 5) / n, 3),
            "recall@10": round(sum(1 for r in ranks if r and r <= 10) / n, 3),
            "mrr": round(sum(1.0 / r for r in ranks if r) / n, 3),
        }
    # the misses, for failure analysis (case refs only — no names)
    report["misses@10"] = [
        {"case_no": g["case_no"], "holding_idx": g["holding_idx"],
         "categories": g.get("categories"), "rank": results["hybrid"][i]}
        for i, g in enumerate(items)
        if not (results["hybrid"][i] and results["hybrid"][i] <= 10)
    ]
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="arctic-l-v2")
    ap.add_argument("--years", nargs="*", type=int, default=[2009, 2004])
    args = ap.parse_args()
    eng = Engine(args.model)
    out = {"model": args.model}
    for year in args.years:
        print(f"== {year} ==")
        rep = eval_year(eng, year)
        out[str(year)] = rep
        for mode in MODES:
            m = rep[mode]
            print(f"  {mode:7s} n={m['n']}  R@5={m['recall@5']}  "
                  f"R@10={m['recall@10']}  MRR={m['mrr']}")
        print(f"  hybrid misses@10: {len(rep['misses@10'])}")
    path = HERE / "output" / f"eval_known_item__{args.model}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
