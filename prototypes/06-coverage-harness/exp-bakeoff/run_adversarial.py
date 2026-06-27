#!/usr/bin/env python3
"""W11 v2 adversarial-proceeding run. Per recoverable issue: district brief +
respondent brief + neutral JUDGE opinion. The JUDGE opinion is emitted (arm 'judge')
in the depth.<tag> format so every metric tool works by --tag.

  CORPUS_ROOT=... run_adversarial.py --model qwen3.5:35b [--n 12 --max-issues 3 --smoke]
-> output/runs/depth.adv-<model>.{input,key}.json   (arm: judge)
   output/runs/adv-<model>.briefs.json              (district/respondent/opinion, de-id)
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
sys.path.insert(0, str(PROTO))
sys.path.insert(0, str(PROTO / "scoreboard"))

from build_evalset import load_evalset                # noqa: E402
from arms.adversarial import make_adversarial_arm     # noqa: E402
from harness.deid import scrub_external               # noqa: E402
from run_depth import recoverable_map, depth_key      # noqa: E402

OUT = HERE / "output" / "runs"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3.5:35b")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--max-issues", type=int, default=3)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--num-predict", type=int, default=4000)
    ap.add_argument("--anchor-tag", default=None,
                    help="v3: depth.<tag> whose closed-book arm anchors the judge "
                         "(e.g. qwen3.5-35b.think)")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if a.smoke:
        a.n, a.max_issues = 1, 1

    anchors = None
    if a.anchor_tag:
        anchors = {}
        for it in json.loads((OUT / f"depth.{a.anchor_tag}.input.json").read_text()):
            mat, iss, arm = it["item_id"].split(":")
            if arm == "closedbook":
                anchors[(mat, iss)] = it["analysis"]
        print(f"loaded {len(anchors)} closed-book anchors from depth.{a.anchor_tag}")

    tag = ("adv3-" if a.anchor_tag else "adv-") + a.model.replace(":", "-")
    rec = recoverable_map()
    arm = make_adversarial_arm(f"ollama:{a.model}", k=a.k, num_predict=a.num_predict,
                               anchors=anchors)

    items, key, briefs, count = [], {}, [], 0
    for m in load_evalset():
        if count >= a.n:
            break
        issues = [c for c in m["answer_key"]["issues"]
                  if rec.get(m["matter_id"], {}).get(c) and depth_key(m, c)][:a.max_issues]
        if not issues:
            continue
        count += 1
        out = arm(m, issues)
        excerpt = scrub_external(m["matter_text"][:900])
        for pi in out["per_issue"]:
            dk = depth_key(m, pi["issue"])
            iid = f"{m['matter_id']}:{pi['issue']}:judge"
            items.append({"item_id": iid, "issue": pi["issue"], "matter_excerpt": excerpt,
                          "key_reasoning": scrub_external(dk["reasoning"]),
                          "key_facts": [scrub_external(f) for f in dk["operative_facts"]],
                          "analysis": scrub_external(pi["opinion"])})
            key[iid] = {"matter": m["matter_id"], "issue": pi["issue"], "arm": "judge",
                        "n_evidence": pi["n_evidence"], "cost_s": out["_cost"]["wall_clock_s"]}
            briefs.append({"matter": m["matter_id"], "issue": pi["issue"],
                           "district_brief": scrub_external(pi["district_brief"]),
                           "respondent_brief": scrub_external(pi["respondent_brief"]),
                           "opinion": scrub_external(pi["opinion"])})
        print(f"{m['matter_id']}: {len(out['per_issue'])} issue(s) x(D+R+judge)  "
              f"({count}/{a.n})  {out['_cost']['wall_clock_s']:.0f}s")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"depth.{tag}.input.json").write_text(json.dumps(items, indent=1, ensure_ascii=False))
    (OUT / f"depth.{tag}.key.json").write_text(json.dumps(key, indent=1))
    (OUT / f"{tag}.briefs.json").write_text(json.dumps(briefs, indent=1, ensure_ascii=False))
    print(f"\ntag: {tag}  ({len(items)} judge opinions)")
    print("item_ids:", json.dumps([it["item_id"] for it in items]))
    if a.smoke and briefs:
        b = briefs[0]
        print("\n--- SMOKE (verify no names; lengths) ---")
        print(f"district_brief {len(b['district_brief'])}  respondent_brief "
              f"{len(b['respondent_brief'])}  opinion {len(b['opinion'])} chars")
        print("\nOPINION[:500]:", b["opinion"][:500])


if __name__ == "__main__":
    main()
