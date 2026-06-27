#!/usr/bin/env python3
"""Build the depth-judge calibration ladder.

Before any real arm exists, validate the depth rubric judge against synthetic
analyses of KNOWN quality, built blind from each matter's answer key:
  L3 = reasoning + operative facts   (perfect      -> expect 3)
  L2 = reasoning only                (distinction  -> expect 2)
  L1 = operative facts only          (right facts  -> expect 1)
  L0 = a different issue's reasoning  (decoy        -> expect 0)

Writes output/depth_calib_input.json for depth_judge_workflow.js. A judge that
orders L0<L1<L2<=L3 and tracks the deterministic proxy is trusted for E1.

Usage: CORPUS_ROOT=/home/nick/Projects/cert_layoff_merged depth_calibration.py [--n 12]
"""

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from harness.metrics import depth_proxy           # noqa: E402
from build_evalset import load_evalset            # noqa: E402

OUT = HERE / "output"


def build(n, seed=0):
    evalset = load_evalset()
    rng = random.Random(seed)
    # collect (matter, depth_entry) pairs that have real reasoning + facts
    pairs = []
    for m in evalset:
        for e in m["answer_key"]["depth"]:
            if e.get("reasoning") and e.get("operative_facts"):
                pairs.append((m, e))
    rng.shuffle(pairs)
    pairs = pairs[:n]
    # a pool of decoy reasonings from a DIFFERENT issue category
    decoys = {}
    for m, e in pairs:
        decoys.setdefault(e["issue"], [])
    for m in evalset:
        for e in m["answer_key"]["depth"]:
            if e.get("reasoning"):
                for iss in decoys:
                    if e["issue"] != iss:
                        decoys[iss].append(e["reasoning"])

    items = []
    for i, (m, e) in enumerate(pairs):
        facts = " ".join(e["operative_facts"])
        decoy_pool = decoys.get(e["issue"]) or [""]
        levels = {
            "L3": (e["reasoning"] + " " + facts).strip(),
            "L2": e["reasoning"].strip(),
            "L1": facts.strip(),
            "L0": rng.choice(decoy_pool).strip(),
        }
        excerpt = m["matter_text"][:900]
        for lvl, analysis in levels.items():
            items.append({
                "item_id": f"{i:02d}-{lvl}",
                "matter_id": m["matter_id"],
                "issue": e["issue"],
                "level": lvl,                      # held out from the judge
                "matter_excerpt": excerpt,
                "key_reasoning": e["reasoning"],
                "key_facts": e["operative_facts"],
                "analysis": analysis,
                "proxy": depth_proxy(analysis, e),
            })
    rng.shuffle(items)                              # judge sees them out of order
    OUT.mkdir(parents=True, exist_ok=True)
    # judge-facing file: NO level / proxy (those would leak the answer)
    judge_fields = ("item_id", "issue", "matter_excerpt",
                    "key_reasoning", "key_facts", "analysis")
    judge = [{k: it[k] for k in judge_fields} for it in items]
    key = {it["item_id"]: {"level": it["level"], "proxy": it["proxy"],
                           "matter_id": it["matter_id"]} for it in items}
    (OUT / "depth_calib_judge.json").write_text(json.dumps(judge, indent=1, ensure_ascii=False))
    (OUT / "depth_calib_key.json").write_text(json.dumps(key, indent=1, ensure_ascii=False))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    a = ap.parse_args()
    items = build(a.n)
    print(f"built {len(items)} calibration items ({a.n} matters x 4 levels)")
    print(f"-> {OUT/'depth_calib_input.json'}")
    print("next: run depth_judge_workflow.js, then depth_judge_eval.py")


if __name__ == "__main__":
    main()
