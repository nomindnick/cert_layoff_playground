"""Score grounding over a saved depth run, by arm.

  CORPUS_ROOT=... grounding_eval.py --tag gemma4-31b.think
  CORPUS_ROOT=... grounding_eval.py --input output/runs/depth.<tag>.input.json \
                                    --key   output/runs/depth.<tag>.key.json

For RAG items the retrieved evidence set is reconstructed deterministically
(retrieve(matter, issue, exclude_ids, k=6, balanced=False) — the run_depth config)
so we can separate "cited a real corpus holding" from "cited a holding it was
actually handed". Saves output/runs/depth.<tag>.grounding.json.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
sys.path.insert(0, str(PROTO))
sys.path.insert(0, str(PROTO / "scoreboard"))

from build_evalset import load_evalset            # noqa: E402
from arms.retrieval import retrieve               # noqa: E402
from grounding import score_analysis              # noqa: E402

OUT = HERE / "output" / "runs"


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 3) if xs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag")
    ap.add_argument("--input")
    ap.add_argument("--key")
    ap.add_argument("--balanced", action="store_true", help="reconstruct balanced retrieval (W11 runs)")
    ap.add_argument("--k", type=int, default=6, help="retrieval k to reconstruct (W11 uses 8)")
    a = ap.parse_args()
    inp = Path(a.input) if a.input else OUT / f"depth.{a.tag}.input.json"
    keyp = Path(a.key) if a.key else OUT / f"depth.{a.tag}.key.json"
    tag = a.tag or inp.stem.replace("depth.", "").replace(".input", "")

    items = {it["item_id"]: it for it in json.loads(inp.read_text())}
    key = json.loads(keyp.read_text())
    matters = {m["matter_id"]: m for m in load_evalset()}

    scored, by_arm = [], defaultdict(list)
    for iid, k in key.items():
        it = items.get(iid)
        if not it:
            continue
        arm = k["arm"]
        ev = None
        if arm != "closedbook":                    # closed-book has no evidence
            m = matters.get(k["matter"])
            if m:
                hs = retrieve(m, k["issue"], set(m.get("exclude_ids") or []),
                              k=a.k, balanced=a.balanced)
                ev = [h["hid"] for h in hs]
        g = score_analysis(it["analysis"], ev)
        g.update({"item_id": iid, "arm": arm, "issue": k["issue"]})
        scored.append(g)
        by_arm[arm].append(g)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"depth.{tag}.grounding.json").write_text(json.dumps(scored, indent=1))

    print(f"=== grounding: {tag} ===")
    print(f"{'arm':<11}{'n':>4}{'cite_any%':>10}{'cites/item':>12}"
          f"{'resolved%':>11}{'in_evid%':>10}")
    for arm in sorted(by_arm):
        rows = by_arm.get(arm, [])
        if not rows:
            continue
        n = len(rows)
        cite_any = sum(1 for r in rows if r["n_cites"] > 0) / n
        cites = _mean([r["n_cites"] for r in rows])
        res = _mean([r["resolution_rate"] for r in rows])           # over citing items
        inev = _mean([r["in_evidence_rate"] for r in rows])
        print(f"{arm:<11}{n:>4}{cite_any*100:>9.0f}%{cites:>12}"
              f"{(res*100 if res is not None else float('nan')):>10.0f}%"
              f"{(inev*100 if inev is not None else float('nan')):>9.0f}%")
    print(f"-> {OUT / f'depth.{tag}.grounding.json'}")


if __name__ == "__main__":
    main()
