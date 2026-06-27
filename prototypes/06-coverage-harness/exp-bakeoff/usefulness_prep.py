"""Prep a depth run for the reference-free usefulness panel — BLIND to arm.

The usefulness judge scores an analysis on its own merits (no ALJ reference), so
we (a) strip key_reasoning/key_facts and (b) replace item_ids with opaque codes
so the judge cannot tell closed-book from RAG (or which model). Blinding order is
deterministic (sha1 of item_id) so re-runs are reproducible.

  CORPUS_ROOT=... usefulness_prep.py --tag gemma4-31b.think [--tag ...]
-> output/runs/useful.<combined>.input.json  ({code: {issue, matter_excerpt, analysis}})
   output/runs/useful.<combined>.keymap.json ({code: {item_id, arm, issue, matter, tag}})
Pass multiple --tag to pool several runs into ONE blinded set (cross-model blind).
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "output" / "runs"
sys.path.insert(0, str(HERE.parent / "scoreboard"))


def _key(tag, iid):
    return hashlib.sha1(f"{tag}|{iid}".encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", action="append", required=True)
    ap.add_argument("--name", default=None, help="output basename (default: first tag)")
    a = ap.parse_args()

    rows = []
    for tag in a.tag:
        items = {it["item_id"]: it for it in
                 json.loads((OUT / f"depth.{tag}.input.json").read_text())}
        key = json.loads((OUT / f"depth.{tag}.key.json").read_text())
        for iid, k in key.items():
            it = items.get(iid)
            if not it:
                continue
            rows.append((_key(tag, iid), tag, iid, k, it))
    rows.sort(key=lambda r: r[0])              # deterministic blind order

    blind, keymap = {}, {}
    for n, (_, tag, iid, k, it) in enumerate(rows, 1):
        code = f"U{n:03d}"
        blind[code] = {"code": code, "issue": it["issue"],
                       "matter_excerpt": it["matter_excerpt"], "analysis": it["analysis"]}
        keymap[code] = {"item_id": iid, "tag": tag, "arm": k["arm"],
                        "issue": k["issue"], "matter": k["matter"]}

    name = a.name or a.tag[0]
    (OUT / f"useful.{name}.input.json").write_text(json.dumps(list(blind.values()), indent=1, ensure_ascii=False))
    (OUT / f"useful.{name}.keymap.json").write_text(json.dumps(keymap, indent=1))
    print(f"{len(blind)} blinded items -> useful.{name}.input.json  (tags: {a.tag})")
    print("codes:", json.dumps(list(blind)))


if __name__ == "__main__":
    main()
