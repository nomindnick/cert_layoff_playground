"""Aggregate the reference-free usefulness panel: per (model, arm), per dimension.

  usefulness_eval.py --scored output/runs/useful.<name>.scored.json \
                     --keymap output/runs/useful.<name>.keymap.json

Reports per-(tag,arm) mean of each 1-5 dimension (averaged across both lenses),
the PAIRED RAG-minus-closedbook delta on overall (the marginal usefulness of
retrieval, model held constant — the core W11 question the recovery metric was
blind to), and a litigator-vs-skeptic harshness check.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

DIMS = ["issue_grasp", "respondent_args", "actionability", "soundness", "overall"]


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 2) if xs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True)
    ap.add_argument("--keymap", required=True)
    a = ap.parse_args()
    scored = json.loads(Path(a.scored).read_text())
    keymap = json.loads(Path(a.keymap).read_text())

    # per code: collect lens scores
    by_code = defaultdict(list)
    lens_overall = defaultdict(list)
    for s in scored:
        if s.get("overall") is None:
            continue
        by_code[s["code"]].append(s)
        if s.get("lens"):
            lens_overall[s["lens"]].append(s["overall"])

    # per-item (code) averaged across lenses
    item = {}
    for code, ss in by_code.items():
        item[code] = {d: _mean([x.get(d) for x in ss]) for d in DIMS}

    # group by (tag, arm)
    cell = defaultdict(lambda: defaultdict(list))     # (tag,arm) -> dim -> [vals]
    pair = defaultdict(dict)                           # (tag, matter:issue) -> arm -> overall
    for code, dims in item.items():
        km = keymap.get(code)
        if not km:
            continue
        ck = (km["tag"], km["arm"])
        for d in DIMS:
            if dims[d] is not None:
                cell[ck][d].append(dims[d])
        mi = f"{km['matter']}:{km['issue']}"
        pair[(km["tag"], mi)][km["arm"]] = dims["overall"]

    print("=== usefulness (1-5, mean across litigator+skeptic) ===")
    print(f"{'model':<20}{'arm':<11}{'n':>3} " + " ".join(f"{d[:9]:>10}" for d in DIMS))
    for ck in sorted(cell):
        row = cell[ck]
        n = len(row["overall"])
        vals = " ".join(f"{(_mean(row[d]) if row[d] else float('nan')):>10.2f}" for d in DIMS)
        print(f"{ck[0]:<20}{ck[1]:<11}{n:>3} {vals}")

    print("\nPAIRED RAG - closedbook on OVERALL (per model, per matter-issue):")
    bym = defaultdict(list)
    for (tag, mi), arms in pair.items():
        if "rag" in arms and "closedbook" in arms and arms["rag"] is not None and arms["closedbook"] is not None:
            bym[tag].append(arms["rag"] - arms["closedbook"])
    for tag in sorted(bym):
        ds = bym[tag]
        wins = sum(1 for d in ds if d > 0.01)
        losses = sum(1 for d in ds if d < -0.01)
        print(f"  {tag:<20} mean delta {(_mean(ds) or 0):+.2f}  "
              f"(RAG wins {wins} / ties {len(ds)-wins-losses} / losses {losses}, n={len(ds)})")

    print("\nlens harshness (mean overall):",
          {k: _mean(v) for k, v in lens_overall.items()})


if __name__ == "__main__":
    main()
