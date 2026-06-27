#!/usr/bin/env python3
"""Aggregate the depth bake-off: closed-book vs RAG, scored by the E0 depth judge.

Reads output/depth_key.json (item_id -> {matter, issue, arm, ...}) and
output/depth_scored.json (item_id -> {score 0-3}, saved from the judge workflow).
Reports mean depth per arm, the PAIRED per-(matter,issue) RAG-minus-closedbook
delta (the marginal effect of retrieval, model held constant), win/tie/loss, and
wall-clock.

Usage: depth_bakeoff_eval.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=str(OUT / "depth_key.json"))
    ap.add_argument("--scored", default=str(OUT / "depth_scored.json"))
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    if a.label:
        print(f"=== {a.label} ===")
    key = json.loads(Path(a.key).read_text())
    scored = {s["item_id"]: s for s in json.loads(Path(a.scored).read_text())
              if s.get("score") is not None}

    by_arm = defaultdict(list)
    cost = defaultdict(list)
    # pair on (matter, issue)
    pair = defaultdict(dict)   # (matter,issue) -> {arm: score}
    for iid, k in key.items():
        s = scored.get(iid)
        if not s:
            continue
        by_arm[k["arm"]].append(s["score"])
        cost[k["arm"]].append(k.get("cost_s", 0))
        pair[(k["matter"], k["issue"])][k["arm"]] = s["score"]

    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0
    print(f"{'arm':12s} {'n':>3s} {'mean_depth':>11s} {'sec/issue':>10s}   score dist")
    from collections import Counter
    for arm in ("closedbook", "rag"):
        v = by_arm.get(arm, [])
        dist = dict(sorted(Counter(v).items()))
        # cost is per arm-call over issues; approximate per-issue
        print(f"{arm:12s} {len(v):>3d} {mean(v):>11.2f} {mean(cost[arm]):>10.1f}   {dist}")

    # paired RAG - closedbook
    deltas, wins, ties, losses = [], 0, 0, 0
    for (m, iss), d in pair.items():
        if "rag" in d and "closedbook" in d:
            delta = d["rag"] - d["closedbook"]
            deltas.append(delta)
            wins += delta > 0
            ties += delta == 0
            losses += delta < 0
    if deltas:
        print(f"\nPAIRED (RAG - closed-book) over {len(deltas)} matter-issues:")
        print(f"  mean delta: {mean(deltas):+.2f}   RAG wins {wins} / ties {ties} / losses {losses}")
        print(f"  -> retrieval {'HELPS' if mean(deltas) > 0.2 else 'no clear effect' if abs(mean(deltas)) <= 0.2 else 'HURTS'}"
              f" (model held constant)")

    (OUT / "depth_bakeoff_report.json").write_text(json.dumps({
        "mean_depth": {a: round(mean(by_arm[a]), 2) for a in by_arm},
        "paired_delta_rag_minus_cb": round(mean(deltas), 2) if deltas else None,
        "win_tie_loss": [wins, ties, losses], "n_pairs": len(deltas),
    }, indent=1))
    print(f"\n-> {OUT/'depth_bakeoff_report.json'}")


if __name__ == "__main__":
    main()
