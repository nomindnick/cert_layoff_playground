#!/usr/bin/env python3
"""Recall-ceiling calibration prep.

For each eval matter, build a judge item = the matter facts + a SHUFFLED,
UNLABELED mix of its real answer-key issues and DECOY non-issues. An Opus judge
then says, per candidate, whether the facts give a genuine hook to raise it. This:
  - ceiling     = recoverable-rate among REAL issues (the true max recall a
                  facts-only arm can hit; the rest is answer-key under-determination)
  - judge audit = decoys should be mostly NOT recoverable (negative control)
  - plausible   = decoys judged recoverable = the plausible-but-not-adjudicated
                  rate that deflates the spotter's precision

Writes output/ceiling_judge_input.json (judge-facing) + output/ceiling_key.json.
Usage: CORPUS_ROOT=/home/nick/Projects/cert_layoff_merged ceiling_prep.py [--n-decoy 4]
"""

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from build_evalset import load_evalset                  # noqa: E402
from harness.issues import ISSUE_DEFS, CANONICAL_ISSUES  # noqa: E402

OUT = HERE / "output"
# the issues the spotter over-spots — decoys drawn here test the plausible bucket
ADJACENT = {"competency", "credentials", "seniority", "bumping", "skipping",
            "assignments_reassignments"}


def build(n_decoy=4, seed=0):
    rng = random.Random(seed)
    judge, key = [], {}
    for m in load_evalset():
        real = list(dict.fromkeys(m["answer_key"]["issues"]))
        nonkey = [c for c in CANONICAL_ISSUES if c not in real]
        adj = [c for c in nonkey if c in ADJACENT]
        rest = [c for c in nonkey if c not in ADJACENT]
        rng.shuffle(adj)
        rng.shuffle(rest)
        decoys = (adj[:2] + rest)[:n_decoy]              # ~half adjacent, half random
        cands = real + decoys
        rng.shuffle(cands)
        judge.append({
            "matter_id": m["matter_id"],
            "matter_text": m["matter_text"],
            "candidates": [{"category": c, "definition": ISSUE_DEFS[c]} for c in cands],
        })
        key[m["matter_id"]] = {"real": real, "decoy": decoys}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ceiling_judge_input.json").write_text(json.dumps(judge, indent=1, ensure_ascii=False))
    (OUT / "ceiling_key.json").write_text(json.dumps(key, indent=1))
    return judge, key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-decoy", type=int, default=4)
    a = ap.parse_args()
    judge, key = build(a.n_decoy)
    nreal = sum(len(k["real"]) for k in key.values())
    ndec = sum(len(k["decoy"]) for k in key.values())
    print(f"{len(judge)} matters | {nreal} real issues + {ndec} decoys to judge")
    print(f"matter_ids: {json.dumps([j['matter_id'] for j in judge])}")
    print(f"-> {OUT/'ceiling_judge_input.json'}")


if __name__ == "__main__":
    main()
