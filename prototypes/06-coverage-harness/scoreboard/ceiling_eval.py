#!/usr/bin/env python3
"""Analyze the recall-ceiling calibration.

Reads ceiling_key.json + ceiling_scored.json (saved from the workflow result).
Reports:
  - CEILING      : recoverable-rate among REAL issues (max recall a facts-only arm
                   can hit; 1 - this = answer-key under-determination)
  - decoy rate   : recoverable-rate among DECOYS — negative control (should be low)
                   AND the plausible-but-not-adjudicated rate
  - per-category : which issue categories are systematically un-recoverable from
                   facts (their spotter-misses are CEILING, not model failure)
  - --rescore M  : re-run spotter M, recompute recall vs the RECOVERABLE-only key
                   ("fair recall") to isolate true headroom from the ceiling.

Usage: ceiling_eval.py [--rescore gemma4:12b]
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
sys.path.insert(0, str(PROTO))
sys.path.insert(0, str(PROTO / "exp-bakeoff"))

from harness.metrics import rarity_weight, _cats          # noqa: E402

OUT = HERE / "output"


def _recoverable_map():
    key = json.loads((OUT / "ceiling_key.json").read_text())
    scored = {s["matter_id"]: s for s in json.loads((OUT / "ceiling_scored.json").read_text())
              if s.get("judgments")}
    rec = {}   # matter -> {category: recoverable bool}
    for mid, s in scored.items():
        rec[mid] = {j["category"]: j["recoverable"] for j in s["judgments"]}
    return key, scored, rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rescore", default=None, help="spotter model to re-score, e.g. gemma4:12b")
    a = ap.parse_args()
    key, scored, rec = _recoverable_map()
    print(f"judged {len(scored)}/{len(key)} matters\n")

    # ---- ceiling (real) + plausible (decoy) ----
    real_tot = real_rec = dec_tot = dec_rec = 0
    cat_real = defaultdict(lambda: [0, 0])   # cat -> [recoverable, total] as a real issue
    cat_dec = defaultdict(lambda: [0, 0])    # cat -> [recoverable, total] as a decoy
    wr_num = wr_den = 0.0
    for mid, k in key.items():
        rm = rec.get(mid, {})
        for c in k["real"]:
            r = bool(rm.get(c, False))
            real_tot += 1
            real_rec += r
            cat_real[c][1] += 1
            cat_real[c][0] += r
            w = rarity_weight(c)
            wr_den += w
            wr_num += w * r
        for c in k["decoy"]:
            r = bool(rm.get(c, False))
            dec_tot += 1
            dec_rec += r
            cat_dec[c][1] += 1
            cat_dec[c][0] += r

    ceiling = real_rec / real_tot if real_tot else 0
    w_ceiling = wr_num / wr_den if wr_den else 0
    decoy_rate = dec_rec / dec_tot if dec_tot else 0
    print(f"CEILING (real issues recoverable from facts): {real_rec}/{real_tot} = {ceiling:.3f}")
    print(f"  rarity-weighted ceiling: {w_ceiling:.3f}  (the real cap on rarity_recall)")
    print(f"under-determination (real issues NOT in facts): {1-ceiling:.3f}")
    print(f"decoy recoverable-rate (negative control / plausible bucket): "
          f"{dec_rec}/{dec_tot} = {decoy_rate:.3f}")
    print(f"  -> judge discriminates real vs decoy by {ceiling-decoy_rate:+.3f} "
          f"({'OK' if ceiling-decoy_rate > 0.25 else 'WEAK — judge may be lenient'})")

    print("\n--- per-category recoverability as a REAL issue (low = under-determined) ---")
    for c in sorted(cat_real, key=lambda c: cat_real[c][0] / cat_real[c][1]):
        r, t = cat_real[c]
        if t >= 2:
            print(f"  {c:26s} {r}/{t} = {r/t:.2f}")
    print("--- decoy categories most often judged recoverable (the plausible bucket) ---")
    for c in sorted(cat_dec, key=lambda c: -(cat_dec[c][0] / cat_dec[c][1])):
        r, t = cat_dec[c]
        if t >= 2 and r:
            print(f"  {c:26s} {r}/{t} = {r/t:.2f}")

    report = {"ceiling": round(ceiling, 3), "weighted_ceiling": round(w_ceiling, 3),
              "decoy_rate": round(decoy_rate, 3),
              "per_category_real": {c: round(v[0]/v[1], 2) for c, v in cat_real.items() if v[1] >= 2}}

    # ---- optional: re-score a spotter vs the RECOVERABLE-only key (fair recall) ----
    if a.rescore:
        from build_evalset import load_evalset
        from arms.issue_spotter import make_arm
        arm = make_arm(f"ollama:{a.rescore}")
        evalset = {m["matter_id"]: m for m in load_evalset()}
        n = fr_num = fr_den = std_num = std_den = 0.0
        for mid, k in key.items():
            m = evalset.get(mid)
            rm = rec.get(mid, {})
            recoverable_real = {c for c in k["real"] if rm.get(c)}
            if not recoverable_real:
                continue
            spotted = _cats(arm(m)["spotted_issues"])
            for c in k["real"]:                       # standard rarity recall (full key)
                w = rarity_weight(c); std_den += w; std_num += w * (c in spotted)
            for c in recoverable_real:                # fair rarity recall (recoverable only)
                w = rarity_weight(c); fr_den += w; fr_num += w * (c in spotted)
            n += 1
        std = std_num / std_den if std_den else 0
        fair = fr_num / fr_den if fr_den else 0
        print(f"\n--- {a.rescore} re-scored over {int(n)} matters ---")
        print(f"  standard rarity_recall (full key):        {std:.3f}")
        print(f"  FAIR rarity_recall (recoverable-only key): {fair:.3f}")
        print(f"  -> headroom above the spotter (fair gap to 1.0): {1-fair:.3f} "
              f"= real recoverable misses for arms B/C/D to close")
        report["rescore"] = {"model": a.rescore, "standard": round(std, 3), "fair": round(fair, 3)}

    (OUT / "ceiling_report.json").write_text(json.dumps(report, indent=1))
    print(f"\n-> {OUT/'ceiling_report.json'}")


if __name__ == "__main__":
    main()
