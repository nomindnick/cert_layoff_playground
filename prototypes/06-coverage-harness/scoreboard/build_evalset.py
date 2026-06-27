#!/usr/bin/env python3
"""Build the E0 eval set: zero-leak matters, stratified by era.

Per the matter-design decision (deterministic + zero-leak pool), we draw eval
matters only from decisions whose facts telegraph ZERO answer-key issues, so the
breadth metric can't be gamed by keyword-matching. Persists each matter (incl.
answer keys + exclude_ids) to output/evalset/.

Usage:  CORPUS_ROOT=/home/nick/Projects/cert_layoff_merged build_evalset.py [--per-era N]
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))          # the prototype dir (for `harness`)

from harness.corpus import decisions          # noqa: E402
from harness.matters import make_matter, eligible  # noqa: E402

OUT = HERE / "output" / "evalset"
SEED = 0


def build(per_era):
    pools = defaultdict(list)
    n_elig = 0
    for cn, dec in decisions():
        if not eligible(dec):
            continue
        n_elig += 1
        m = make_matter(cn, dec)
        if m["diagnostics"]["leak_rate"] == 0.0:      # zero-leak only
            pools[m["era"]].append(m)
    rng = random.Random(SEED)
    chosen = []
    for era_name, pool in sorted(pools.items()):
        rng.shuffle(pool)
        chosen.extend(pool[:per_era])
    OUT.mkdir(parents=True, exist_ok=True)
    for m in chosen:
        (OUT / f"{m['matter_id']}.json").write_text(
            json.dumps(m, indent=1, ensure_ascii=False))
    idx = {"n_eligible": n_elig,
           "zero_leak_by_era": {e: len(p) for e, p in sorted(pools.items())},
           "selected_by_era": defaultdict(int),
           "matters": [m["matter_id"] for m in chosen]}
    for m in chosen:
        idx["selected_by_era"][m["era"]] += 1
    (HERE / "output" / "evalset_index.json").write_text(json.dumps(idx, indent=1))
    return idx


def load_evalset():
    return [json.loads(p.read_text()) for p in sorted(OUT.glob("*.json"))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-era", type=int, default=12)
    a = ap.parse_args()
    idx = build(a.per_era)
    print(f"eligible matters: {idx['n_eligible']}")
    print(f"zero-leak by era: {dict(idx['zero_leak_by_era'])}")
    print(f"selected by era:  {dict(idx['selected_by_era'])}  "
          f"(total {len(idx['matters'])})")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
