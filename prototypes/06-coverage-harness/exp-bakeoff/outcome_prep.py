"""Prep for the DOMAIN-AWARE bottom-line outcome metric (the confound fix).

Ground truth per matter-issue = the source holding's prevailing_party (authoritative;
the OLD confound was in the JUDGE's winner-inference, not the truth). We blind the
analyses to codes and carry the truth in a side meta file the judge never sees.

  CORPUS_ROOT=... outcome_prep.py --tag gemma4-31b.think --tag gemma4-12b.think --name gemma-think
-> output/runs/outcome.<name>.input.json  ({code, issue, analysis})
   output/runs/outcome.<name>.meta.json   ({code: {tag, matter_issue, arm, truth}})
"""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
RUNS = HERE / "output" / "runs"
sys.path.insert(0, str(PROTO))
sys.path.insert(0, str(PROTO / "scoreboard"))

from correctness_prep import truth_map            # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", action="append", required=True)
    ap.add_argument("--name", required=True)
    a = ap.parse_args()
    truth = truth_map()

    rows = []
    for tag in a.tag:
        for it in json.loads((RUNS / f"depth.{tag}.input.json").read_text()):
            iid = it["item_id"]                       # matter:issue:arm
            parts = iid.split(":")
            mi, arm = ":".join(parts[:2]), parts[-1]
            h = hashlib.sha1(f"{tag}|{iid}".encode()).hexdigest()
            rows.append((h, tag, mi, arm, it))
    rows.sort(key=lambda r: r[0])

    blind, meta = [], {}
    for n, (_, tag, mi, arm, it) in enumerate(rows, 1):
        code = f"O{n:03d}"
        blind.append({"code": code, "issue": it["issue"], "analysis": it["analysis"]})
        meta[code] = {"tag": tag, "matter_issue": mi, "arm": arm, "truth": truth.get(mi)}

    (RUNS / f"outcome.{a.name}.input.json").write_text(json.dumps(blind, indent=1, ensure_ascii=False))
    (RUNS / f"outcome.{a.name}.meta.json").write_text(json.dumps(meta, indent=1))
    gradeable = sum(1 for v in meta.values() if v["truth"] in ("district", "respondent"))
    print(f"{len(blind)} items -> outcome.{a.name}.input.json  (tags {a.tag})")
    print("per matter-issue truth dist:",
          dict(Counter(v["truth"] for v in meta.values())))
    print(f"gradeable (district|respondent) items: {gradeable}/{len(blind)}")
    print("codes:", json.dumps([b["code"] for b in blind]))


if __name__ == "__main__":
    main()
