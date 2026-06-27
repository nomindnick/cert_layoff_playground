#!/usr/bin/env python3
"""W11 verify-repair run. Emits the balanced-RAG draft (arm 'rag') and the repaired
analysis (arm 'w11') per recoverable issue, in the depth.<tag> format so every metric
tool (grounding/usefulness/outcome/recovery) works by --tag.

  CORPUS_ROOT=... run_w11.py --model qwen3.5:35b --think on [--n 12 --max-issues 3 --smoke]
-> output/runs/depth.w11-<model>.think.{input,key}.json  (arms: rag, w11)
   output/runs/w11-<model>.think.critiques.json          (draft/critique/repaired, de-id)
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
sys.path.insert(0, str(PROTO))
sys.path.insert(0, str(PROTO / "scoreboard"))

from build_evalset import load_evalset            # noqa: E402
from arms.w11 import make_w11_arm                  # noqa: E402
from harness.deid import scrub_external           # noqa: E402
from run_depth import recoverable_map, depth_key  # noqa: E402

OUT = HERE / "output" / "runs"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3.5:35b")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--max-issues", type=int, default=3)
    ap.add_argument("--think", choices=["on", "off"], default="on")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--num-predict", type=int, default=8000)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if a.smoke:
        a.n, a.max_issues = 1, 1
    think = a.think == "on"
    tag = "w11-" + a.model.replace(":", "-") + (".think" if think else ".nothink")
    rec = recoverable_map()
    arm = make_w11_arm(f"ollama:{a.model}", k=a.k, think=think, num_predict=a.num_predict)

    items, key, critiques, count = [], {}, [], 0
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
            kr = scrub_external(dk["reasoning"])
            kf = [scrub_external(f) for f in dk["operative_facts"]]
            for arm_name, text in (("rag", pi["draft"]), ("w11", pi["repaired"])):
                iid = f"{m['matter_id']}:{pi['issue']}:{arm_name}"
                items.append({"item_id": iid, "issue": pi["issue"],
                              "matter_excerpt": excerpt, "key_reasoning": kr,
                              "key_facts": kf, "analysis": scrub_external(text)})
                key[iid] = {"matter": m["matter_id"], "issue": pi["issue"], "arm": arm_name,
                            "n_evidence": pi["n_evidence"], "cost_s": out["_cost"]["wall_clock_s"]}
            critiques.append({"matter": m["matter_id"], "issue": pi["issue"],
                              "draft": scrub_external(pi["draft"]),
                              "critique": scrub_external(pi["critique"]),
                              "repaired": scrub_external(pi["repaired"])})
        print(f"{m['matter_id']}: {len(out['per_issue'])} issue(s) x(draft+repair)  "
              f"({count}/{a.n})  {out['_cost']['wall_clock_s']:.0f}s")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"depth.{tag}.input.json").write_text(json.dumps(items, indent=1, ensure_ascii=False))
    (OUT / f"depth.{tag}.key.json").write_text(json.dumps(key, indent=1))
    (OUT / f"{tag}.critiques.json").write_text(json.dumps(critiques, indent=1, ensure_ascii=False))
    print(f"\ntag: {tag}  ({len(items)} items = {len(items)//2} matter-issues x (rag-draft + w11-repair))")
    print("item_ids:", json.dumps([it["item_id"] for it in items]))
    if a.smoke and critiques:
        c = critiques[0]
        print("\n--- SMOKE: draft vs repaired (verify no names) ---")
        print("DRAFT[:350]:", c["draft"][:350])
        print("\nCRITIQUE[:400]:", c["critique"][:400])
        print("\nREPAIRED[:350]:", c["repaired"][:350])


if __name__ == "__main__":
    main()
