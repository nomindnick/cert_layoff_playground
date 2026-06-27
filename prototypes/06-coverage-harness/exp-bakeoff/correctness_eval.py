#!/usr/bin/env python3
"""Correctness vs recovery, across runs/arms.

Joins the outcome-judge predictions (output/outcome_scored.json) with the
ground-truth prevailing_party (correctness_meta.json) and the recovery scores
(per-run depth-scored files). Reports, per run x arm:
  - recovery (0-3 mean), correctness (overall), correctness on RESPONDENT-wins
    (the minority class where inversions bite; always-district baseline = ~0.74).
Answers: does RAG lift correctness even where it doesn't lift recovery? Does
correctness scale with params like recovery? Does even Opus mis-state outcomes?
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
RUNS = OUT / "runs"

RECOVERY_FILES = {
    "gemma4-12b.nothink": RUNS / "depth_scored.gemma4-12b.json",
    "gemma4-12b.think": RUNS / "depth.gemma4-12b.think.scored.json",
    "gemma4-31b.nothink": RUNS / "depth.gemma4-31b.nothink.scored.json",
    "opus": OUT / "opus_depth_scored.json",
}
ORDER = ["gemma4-12b.nothink", "gemma4-12b.think", "gemma4-31b.nothink", "opus"]


def main():
    meta = json.loads((OUT / "correctness_meta.json").read_text())
    pred = {s["oid"]: s.get("predicted") for s in json.loads((OUT / "outcome_scored.json").read_text())}
    # recovery: tag -> {item_id: score}
    rec = {}
    for tag, p in RECOVERY_FILES.items():
        if p.exists():
            rec[tag] = {s["item_id"]: s["score"] for s in json.loads(p.read_text())
                        if s.get("score") is not None}

    # aggregate per (tag, arm)
    agg = defaultdict(lambda: {"rec": [], "corr": [], "corr_resp": []})
    for oid, m in meta.items():
        tag, arm, truth = m["tag"], m["arm"], m["truth"]
        if truth not in ("district", "respondent"):
            continue
        p = pred.get(oid)
        correct = int(p == truth)
        agg[(tag, arm)]["corr"].append(correct)
        if truth == "respondent":
            agg[(tag, arm)]["corr_resp"].append(correct)
        iid = oid.split("::", 1)[1]
        if tag in rec and iid in rec[tag]:
            agg[(tag, arm)]["rec"].append(rec[tag][iid])

    mean = lambda xs: round(sum(xs) / len(xs), 2) if xs else None
    print(f"{'run':22s} {'arm':11s} {'recovery':>9s} {'correct':>8s} {'correct|resp':>13s}")
    print("-" * 68)
    for tag in ORDER:
        for arm in ("closedbook", "rag"):
            a = agg.get((tag, arm))
            if not a:
                continue
            r, c, cr = mean(a["rec"]), mean(a["corr"]), mean(a["corr_resp"])
            crn = len(a["corr_resp"])
            print(f"{tag:22s} {arm:11s} {str(r):>9s} {str(c):>8s} "
                  f"{(str(cr)+f' (n={crn})'):>13s}")
        print()

    # RAG vs closed-book deltas per run (the key question)
    print("RAG − closed-book (per run):  recovery / correctness / correct|resp")
    for tag in ORDER:
        cb, rg = agg.get((tag, "closedbook")), agg.get((tag, "rag"))
        if not (cb and rg):
            continue
        dr = (mean(rg["rec"]) or 0) - (mean(cb["rec"]) or 0)
        dc = (mean(rg["corr"]) or 0) - (mean(cb["corr"]) or 0)
        dcr = (mean(rg["corr_resp"]) or 0) - (mean(cb["corr_resp"]) or 0)
        print(f"  {tag:22s} {dr:+.2f} / {dc:+.2f} / {dcr:+.2f}")

    (OUT / "correctness_report.json").write_text(json.dumps(
        {f"{t}.{a}": {"recovery": mean(v["rec"]), "correct": mean(v["corr"]),
                      "correct_resp": mean(v["corr_resp"])}
         for (t, a), v in agg.items()}, indent=1))
    print(f"\n-> {OUT/'correctness_report.json'}")


if __name__ == "__main__":
    main()
