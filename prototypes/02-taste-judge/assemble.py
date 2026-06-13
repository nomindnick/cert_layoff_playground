#!/usr/bin/env python3
"""Stage 3: set assembly (Task B) — greedy selection by judge confidence with
an MMR-style dedup penalty, scored as set overlap with the human-included set.

For each candidate in confidence order: skip if cosine similarity to an
already-selected same-category holding exceeds tau ("duplicates a holding
we've already included"). Stop at --size (default: the human set's size).

Usage:
  assemble.py --year 2009 --arm A__gemma4-31b [--sweep-tau]
  assemble.py --year 2004 --arm A__gemma4-31b --tau 0.88
"""

import argparse
import json

import numpy as np

from common import OUT


def load(year, arm):
    cands = json.loads((OUT / f"features_{year}.json").read_text())
    emb = np.load(OUT / f"emb_{year}.npy")
    if arm.endswith(".json"):  # a {id: score} file (e.g. logistic probs)
        conf = json.loads((OUT / arm).read_text())
    else:
        jdir = OUT / "judgments" / str(year) / arm
        conf = {}
        for f in jdir.glob("*.json"):
            j = json.loads(f.read_text())
            conf[j["_id"]] = j["score"]
    rows = [(i, c, conf.get(c["id"], 0.0)) for i, c in enumerate(cands)]
    return rows, emb


def select(rows, emb, tau, size):
    chosen = []  # candidate indices
    for i, c, conf in sorted(rows, key=lambda r: -r[2]):
        if len(chosen) >= size:
            break
        dup = False
        for j in chosen:
            if (rows[j][1]["category"] == c["category"]
                    and float(emb[i] @ emb[j]) >= tau):
                dup = True
                break
        if not dup:
            chosen.append(i)
    return chosen


def score(rows, chosen):
    sel = {rows[i][1]["id"] for i in chosen}
    gold = {c["id"] for _, c, _ in rows if c["label"] == 1}
    tp = len(sel & gold)
    p = tp / len(sel) if sel else 0
    r = tp / len(gold) if gold else 0
    f1 = 2 * p * r / (p + r) if p + r else 0
    return {"selected": len(sel), "human_set": len(gold), "overlap": tp,
            "precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--tau", type=float, default=0.88)
    ap.add_argument("--size", type=int, default=0)
    ap.add_argument("--sweep-tau", action="store_true")
    args = ap.parse_args()

    rows, emb = load(args.year, args.arm)
    n_gold = sum(1 for _, c, _ in rows if c["label"] == 1)
    size = args.size or n_gold

    out = {"year": args.year, "arm": args.arm, "size": size}
    if args.sweep_tau:
        out["sweep"] = []
        for tau in (0.80, 0.84, 0.88, 0.92, 0.96, 1.01):  # 1.01 = no dedup
            m = score(rows, select(rows, emb, tau, size))
            out["sweep"].append({"tau": tau, **m})
            print(f"tau={tau}: {m}")
    else:
        m = score(rows, select(rows, emb, args.tau, size))
        out["result"] = {"tau": args.tau, **m}
        print(f"tau={args.tau}: {m}")
    path = OUT / f"assembly_{args.year}.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
