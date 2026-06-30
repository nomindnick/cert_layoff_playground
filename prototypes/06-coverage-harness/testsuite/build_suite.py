#!/usr/bin/env python3
"""Sample the difficulty-suite from the candidate pool — stratified with known weights.

Strata = era x outcome (over-sample respondent-wins ~4x for power on the exposure
slice; floor the thin eras). Within a stratum: round-robin by issue (coverage of
rare categories) + a per-ALJ cap (no judge dominates). Each entry carries its
inverse sampling weight (stratum population / sampled) so results can be re-weighted
to the corpus base rate if desired. Emits suite.json with full matter_text +
exclude_ids (ready for blind Opus difficulty rating + local model-disagreement).

  CORPUS_ROOT=/home/nick/Projects/cert_layoff_merged build_suite.py
"""

import json
import random
import sys
from collections import Counter, defaultdict
from itertools import zip_longest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
sys.path.insert(0, str(PROTO))

from harness.corpus import decisions                       # noqa: E402
from harness.matters import make_matter                    # noqa: E402

OUT = HERE / "output"
SEED = 0
ALJ_CAP = 8
TARGETS = {
    ("1999-2001", "respondent"): 20, ("1999-2001", "district"): 40,
    ("2004-2009", "respondent"): 130, ("2004-2009", "district"): 110,
    ("2018-2025", "respondent"): 50, ("2018-2025", "district"): 50,
}


def sample_stratum(cands, target, rng):
    buckets = defaultdict(list)
    for c in cands:
        buckets[c["issue"]].append(c)
    for b in buckets.values():
        rng.shuffle(b)
    order = [c for grp in zip_longest(*buckets.values()) for c in grp if c]  # round-robin by issue
    sel, aljc, leftover = [], Counter(), []
    for c in order:                                  # pass 1: respect ALJ cap
        if len(sel) >= target:
            leftover.append(c)
        elif aljc[c["alj"]] < ALJ_CAP:
            sel.append(c); aljc[c["alj"]] += 1
        else:
            leftover.append(c)
    for c in leftover:                               # pass 2: relax cap to hit target
        if len(sel) >= target:
            break
        sel.append(c)
    return sel


def main():
    cands = json.loads((OUT / "candidate_pool.json").read_text())
    by_stratum = defaultdict(list)
    for c in cands:
        by_stratum[(c["era"], c["truth"])].append(c)

    rng = random.Random(SEED)
    chosen = []
    print(f"{'stratum':<28}{'avail':>7}{'target':>8}{'picked':>8}{'weight':>8}")
    for stratum, target in TARGETS.items():
        avail = by_stratum.get(stratum, [])
        sel = sample_stratum(avail, target, rng)
        w = round(len(avail) / len(sel), 2) if sel else 0
        for c in sel:
            c["weight"] = w
        chosen.extend(sel)
        print(f"{str(stratum):<28}{len(avail):>7}{target:>8}{len(sel):>8}{w:>8}")

    # regenerate matter_text + exclude_ids for selected (group by matter)
    want_matters = {c["matter_id"] for c in chosen}
    matter_obj = {}
    for cn, dec in decisions():
        if cn in want_matters:
            matter_obj[cn] = make_matter(cn, dec)
    suite = []
    for c in chosen:
        m = matter_obj.get(c["matter_id"])
        if not m:
            continue
        suite.append({**c, "matter_text": m["matter_text"],
                      "exclude_ids": m["exclude_ids"]})

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "suite.json").write_text(json.dumps(suite, indent=1, ensure_ascii=False))

    n = len(suite)
    print(f"\n=== SUITE: {n} matter-issues ===")
    print("outcome:", dict(Counter(c["truth"] for c in suite)))
    print("era:", dict(Counter(c["era"] for c in suite)))
    print("issue floors (n per category):")
    for iss, k in sorted(Counter(c["issue"] for c in suite).items(), key=lambda x: -x[1]):
        print(f"    {iss:<24}{k:>4}")
    print("editorial inclusion:",
          dict(Counter("incl" if c["included"] else ("not" if c["included"] is False else "unknown")
                       for c in suite)))
    aljc = Counter(c["alj"] for c in suite if c["alj"])
    print(f"ALJ spread: {len(aljc)} distinct; max per ALJ {max(aljc.values())}; "
          f">cap({ALJ_CAP}): {sum(1 for v in aljc.values() if v > ALJ_CAP)}")
    print(f"-> {OUT / 'suite.json'}")


if __name__ == "__main__":
    main()
