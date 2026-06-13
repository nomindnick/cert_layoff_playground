#!/usr/bin/env python3
"""Stage 4: score judge arms vs labels and baselines; write the disagreement
sample. Threshold policy: 0.5 on `confidence` by default; --sweep reports the
best-F1 threshold on 2009 (dev) which is then FROZEN for 2004 via --threshold.

Usage:
  eval_taste.py --year 2009 [--sweep]
  eval_taste.py --year 2004 --threshold 0.55
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from common import OUT


def load_judgments(year):
    arms = {}
    base = OUT / "judgments" / str(year)
    if not base.exists():
        return arms
    for d in sorted(base.iterdir()):
        if not d.is_dir():
            continue
        js = {}
        for f in d.glob("*.json"):
            j = json.loads(f.read_text())
            js[j["_id"]] = j
        if js:
            arms[d.name] = js
    return arms


def prf(pairs):
    tp = sum(1 for y, p in pairs if y and p)
    fp = sum(1 for y, p in pairs if not y and p)
    fn = sum(1 for y, p in pairs if y and not p)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3),
            "f1": round(f1, 3), "n_predicted": tp + fp}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--sweep", action="store_true")
    args = ap.parse_args()

    cands = {c["id"]: c for c in
             json.loads((OUT / f"features_{args.year}.json").read_text())}
    arms = load_judgments(args.year)
    report = {"year": args.year, "n_candidates": len(cands),
              "base_rate": round(sum(c["label"] for c in cands.values()) / len(cands), 3),
              "arms": {}}

    for arm, js in arms.items():
        pairs = [(cands[i]["label"], j["score"] >= args.threshold)
                 for i, j in js.items() if i in cands]
        entry = {"n_judged": len(pairs),
                 "include_rate": round(sum(p for _, p in pairs) / len(pairs), 3),
                 f"at_{args.threshold}": prf(pairs)}
        if args.sweep:
            best = None
            for t in [x / 20 for x in range(1, 20)]:
                m = prf([(cands[i]["label"], j["score"] >= t)
                         for i, j in js.items() if i in cands])
                if best is None or m["f1"] > best[1]["f1"]:
                    best = (t, m)
            entry["best_threshold"] = {"threshold": best[0], **best[1]}
        # per-category f1 (categories with >=10 candidates)
        bycat = defaultdict(list)
        for i, j in js.items():
            if i in cands:
                bycat[cands[i]["category"] or "?"].append(
                    (cands[i]["label"], j["score"] >= args.threshold))
        entry["per_category"] = {
            c: prf(v) for c, v in sorted(bycat.items()) if len(v) >= 10}
        report["arms"][arm] = entry

    path = OUT / f"eval_{args.year}.json"
    path.write_text(json.dumps(report, indent=1))
    for arm, e in report["arms"].items():
        line = e.get("best_threshold") or e[f"at_{args.threshold}"]
        print(f"{args.year} {arm}: n={e['n_judged']} include_rate={e['include_rate']} "
              f"P={line['precision']} R={line['recall']} F1={line['f1']}"
              + (f" (t={line['threshold']})" if "threshold" in line else
                 f" (t={args.threshold})"))
    print(f"wrote {path}")

    # disagreement sample for the strongest arm (most judged, then best f1)
    if arms:
        arm = max(report["arms"],
                  key=lambda a: (report["arms"][a]["n_judged"],
                                 report["arms"][a][f"at_{args.threshold}"]["f1"]))
        js = arms[arm]
        rows = []
        for i, j in js.items():
            c = cands.get(i)
            if not c:
                continue
            pred = j["score"] >= args.threshold
            if pred != bool(c["label"]):
                rows.append((j["score"], c, j))
        rows.sort(key=lambda r: -abs(r[0] - 0.5))
        fp = [r for r in rows if r[0] >= args.threshold][:15]
        fn = [r for r in rows if r[0] < args.threshold][:15]
        lines = [f"# Disagreements — {args.year}, arm {arm}, t={args.threshold}",
                 "", "Labels come from the human volume via the lab alignment; "
                 "negatives include holdings the editors may simply not have "
                 "catalogued (label noise — metrics are a floor).", ""]
        for title, rs in (("Judge says INCLUDE, volume omitted", fp),
                          ("Judge says OMIT, volume catalogued", fn)):
            lines += [f"## {title} ({len(rs)} shown)", ""]
            for conf, c, j in rs:
                lines += [f"### {c['id']} — {c['category']} (conf {conf})",
                          c["summary"] or c["text"][:400], "",
                          f"*Judge:* {j['rationale']} `{','.join(j['reasons'])}`", ""]
        (OUT / f"disagreements_{args.year}.md").write_text("\n".join(lines))
        print(f"wrote disagreements_{args.year}.md (arm {arm})")


if __name__ == "__main__":
    main()
