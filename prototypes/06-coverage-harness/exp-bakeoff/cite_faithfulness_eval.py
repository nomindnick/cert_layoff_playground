#!/usr/bin/env python3
"""Aggregate cite-faithfulness per (tag, arm).

  cite_faithfulness_eval.py --scored output/runs/faith.<name>.scored.json \
                            --meta   output/runs/faith.<name>.meta.json

faithfulness_rate = faithful / (faithful+tangential+unfaithful) over RESOLVED cites.
Reports UNFAITH% separately -- the dangerous laundered-confabulation case (a real cite
used to support a proposition it doesn't, or with its direction inverted). Identity
grounding (resolution_rate) is blind to this; this is the rail for the richer artifacts.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True)
    ap.add_argument("--meta", required=True)
    a = ap.parse_args()
    scored = {s["code"]: s for s in json.loads(Path(a.scored).read_text()) if s.get("verdict")}
    meta = json.loads(Path(a.meta).read_text())

    cell = defaultdict(lambda: {"n": 0, "faithful": 0, "tangential": 0, "unfaithful": 0})
    for code, m in meta.items():
        s = scored.get(code)
        if not s:
            continue
        c = cell[(m["tag"], m["arm"])]
        c["n"] += 1
        c[s["verdict"]] += 1

    print("=== cite-faithfulness (over RESOLVED corpus cites) ===")
    print(f"{'model':<22}{'arm':<11}{'n':>4}{'faith%':>8}{'tang%':>7}{'UNFAITH%':>9}")
    for ck in sorted(cell):
        c = cell[ck]
        n = c["n"] or 1
        print(f"{ck[0]:<22}{ck[1]:<11}{c['n']:>4}{c['faithful'] / n * 100:>7.0f}%"
              f"{c['tangential'] / n * 100:>6.0f}%{c['unfaithful'] / n * 100:>8.0f}%")
    print("\nUNFAITH% = mischaracterized/inverted cites (laundered confabulation; the rail).")


if __name__ == "__main__":
    main()
