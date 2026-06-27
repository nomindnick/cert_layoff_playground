#!/usr/bin/env python3
"""Correctness-metric prep.

GROUND TRUTH per matter-issue = the source holding's actual `prevailing_party`
(who won — district or respondent). Then combine the existing run analyses into one
outcome-judge input so a judge can extract WHICH WAY each analysis concludes;
correctness = predicted direction matches the real prevailing_party. This is the
axis the recovery metric is blind to (it captures the inversion failure mode).

Writes output/outcome_judge_input.json + output/correctness_meta.json.
Usage: CORPUS_ROOT=/home/nick/Projects/cert_layoff_merged correctness_prep.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
sys.path.insert(0, str(PROTO))
sys.path.insert(0, str(PROTO / "scoreboard"))

from build_evalset import load_evalset          # noqa: E402
from run_depth import depth_key                 # noqa: E402
from harness.corpus import holdings             # noqa: E402

OUT = HERE / "output"
RUNS = OUT / "runs"
# the existing runs' analysis files (item field "analysis")
RUNFILES = {
    "gemma4-12b.nothink": RUNS / "depth_judge_input.gemma4-12b.json",
    "gemma4-12b.think": RUNS / "depth.gemma4-12b.think.input.json",
    "gemma4-31b.nothink": RUNS / "depth.gemma4-31b.nothink.input.json",
    "opus": OUT / "opus_judge_input.json",
}


def truth_map():
    pp = {h["hid"]: h["prevailing_party"] for h in holdings()}
    out = {}
    for m in load_evalset():
        for d in m["answer_key"]["depth"]:
            dk = depth_key(m, d["issue"])
            if dk:
                out[f"{m['matter_id']}:{dk['issue']}"] = pp.get(dk["hid"])
    return out


def main():
    truth = truth_map()
    items, meta = [], {}
    for tag, path in RUNFILES.items():
        if not path.exists():
            print(f"  (skip missing {tag}: {path.name})")
            continue
        for it in json.loads(path.read_text()):
            iid = it["item_id"]                  # matter:issue:arm
            parts = iid.split(":")
            mi = ":".join(parts[:2])
            arm = parts[-1]
            oid = f"{tag}::{iid}"
            items.append({"oid": oid, "issue": it["issue"], "analysis": it["analysis"]})
            meta[oid] = {"tag": tag, "matter_issue": mi, "arm": arm, "truth": truth.get(mi)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "outcome_judge_input.json").write_text(json.dumps(items, indent=1, ensure_ascii=False))
    (OUT / "correctness_meta.json").write_text(json.dumps(meta, indent=1))
    print(f"{len(items)} outcome-judge items across {len(RUNFILES)} runs")
    print("ground-truth prevailing_party dist (per matter-issue):",
          dict(Counter(v for k, v in truth.items())))
    decided = sum(1 for o in meta.values() if meta and o["truth"] in ("district", "respondent"))
    print(f"gradeable (decided) items: {decided}/{len(items)}")
    print("OIDS:", json.dumps([i["oid"] for i in items]))


if __name__ == "__main__":
    main()
