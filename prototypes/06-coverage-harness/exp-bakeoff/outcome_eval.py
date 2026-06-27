"""Aggregate the domain-aware bottom-line outcome metric (the confound fix).

  outcome_eval.py --scored output/runs/outcome.<name>.scored.json \
                  --meta   output/runs/outcome.<name>.meta.json

Correctness = predicted direction == the source holding's prevailing_party.
Reports per-(model,arm) accuracy, accuracy on RESPONDENT-WIN items only (where a
district-biased model fails — the high-value exposure cases), and the
always-say-district baseline (the skew a useful model must beat).
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True)
    ap.add_argument("--meta", required=True)
    a = ap.parse_args()
    scored = {s["code"]: s for s in json.loads(Path(a.scored).read_text()) if s.get("predicted")}
    meta = json.loads(Path(a.meta).read_text())

    cell = defaultdict(lambda: {"n": 0, "correct": 0, "n_resp": 0, "correct_resp": 0,
                                "pred_d": 0, "pred_r": 0, "unclear": 0})
    base = {"n": 0, "district": 0}
    for code, m in meta.items():
        truth = m["truth"]
        if truth not in ("district", "respondent"):
            continue
        base["n"] += 1
        base["district"] += (truth == "district")
        s = scored.get(code)
        if not s:
            continue
        ck = (m["tag"], m["arm"])
        c = cell[ck]
        c["n"] += 1
        pred = s["predicted"]
        c["pred_d"] += (pred == "district")
        c["pred_r"] += (pred == "respondent")
        c["unclear"] += (pred == "unclear")
        c["correct"] += (pred == truth)
        if truth == "respondent":
            c["n_resp"] += 1
            c["correct_resp"] += (pred == truth)

    print("=== domain-aware bottom-line outcome accuracy ===")
    bd = base["district"] / base["n"] if base["n"] else 0
    print(f"always-say-district baseline: {bd*100:.0f}%  ({base['district']}/{base['n']} matter-issues are district-win)\n")
    print(f"{'model':<20}{'arm':<11}{'n':>4}{'acc':>7}{'resp_acc':>10}"
          f"{'pred d/r/?':>14}")
    for ck in sorted(cell):
        c = cell[ck]
        acc = c["correct"] / c["n"] if c["n"] else 0
        racc = c["correct_resp"] / c["n_resp"] if c["n_resp"] else float("nan")
        print(f"{ck[0]:<20}{ck[1]:<11}{c['n']:>4}{acc*100:>6.0f}%"
              f"{racc*100:>9.0f}%   {c['pred_d']:>3}/{c['pred_r']}/{c['unclear']}")
    print("\nresp_acc = accuracy on respondent-WIN matter-issues only (the exposure cases).")


if __name__ == "__main__":
    main()
