#!/usr/bin/env python3
"""Depth bake-off: run closed-book vs RAG local analysis over recoverable issues,
emit SCRUBBED judge items for the E0 depth judge.

Analyzes only recoverable answer-key issues that have a non-empty source reasoning
(so depth is scored against a real reference). All cloud-bound text is run through
harness.deid.scrub_external (eval != product: public OAH data + best-effort scrub).

  CORPUS_ROOT=... run_depth.py --smoke            # 2 matters, eyeball one item
  CORPUS_ROOT=... run_depth.py [--model gemma4:12b --n 10 --max-issues 3]
then: depth_judge_workflow over output/depth_judge_input.json -> aggregate.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
sys.path.insert(0, str(PROTO))
sys.path.insert(0, str(PROTO / "scoreboard"))

from build_evalset import load_evalset                 # noqa: E402
from arms.depth_analyzer import make_depth_arm         # noqa: E402
from harness.deid import scrub_external                # noqa: E402

OUT = HERE / "output"
SCB = PROTO / "scoreboard" / "output"


def recoverable_map():
    scored = {s["matter_id"]: s for s in json.loads((SCB / "ceiling_scored.json").read_text())
              if s.get("judgments")}
    return {mid: {j["category"]: j["recoverable"] for j in s["judgments"]}
            for mid, s in scored.items()}


def depth_key(m, issue):
    for d in m["answer_key"]["depth"]:
        if d["issue"] == issue and d.get("reasoning"):
            return d
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemma4:12b")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--max-issues", type=int, default=3)
    ap.add_argument("--think", choices=["on", "off"], default="on",
                    help="let the model emit reasoning tokens before answering")
    ap.add_argument("--num-predict", type=int, default=8000)
    ap.add_argument("--call-timeout", type=int, default=900,
                    help="per-analysis ollama socket timeout (s); a hung call fails THIS "
                         "issue (recorded as error) and the run continues + checkpoints, "
                         "instead of blocking the whole run")
    ap.add_argument("--balanced", action="store_true",
                    help="RAG arm retrieves 50/50 district/respondent (counter the skew)")
    ap.add_argument("--arms", default="closedbook,rag",
                    help="comma list of arms to run: closedbook,rag (e.g. 'rag' to skip "
                         "regenerating the retrieval-independent closed-book arm)")
    ap.add_argument("--tag-suffix", default="",
                    help="append to the tag (e.g. 'tk' for the thick eval) so a re-baseline "
                         "doesn't clobber a prior same-model run")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if a.smoke:
        a.n, a.max_issues = 2, 1
    think = a.think == "on"
    tag = a.model.replace(":", "-") + (".think" if think else ".nothink")
    if a.balanced:
        tag += ".bal"
    if a.tag_suffix:
        tag += f".{a.tag_suffix}"
    rec = recoverable_map()
    np_cb = a.num_predict if think else 700
    all_arms = {"closedbook": make_depth_arm(f"ollama:{a.model}", use_retrieval=False,
                                             think=think, num_predict=np_cb,
                                             timeout=a.call_timeout),
                "rag": make_depth_arm(f"ollama:{a.model}", use_retrieval=True, k=6,
                                      think=think, num_predict=np_cb, balanced=a.balanced,
                                      timeout=a.call_timeout)}
    want = [s.strip() for s in a.arms.split(",") if s.strip()]
    arms = {n: all_arms[n] for n in want if n in all_arms}

    runs = OUT / "runs"
    tagged_inp = runs / f"depth.{tag}.input.json"
    tagged_key = runs / f"depth.{tag}.key.json"

    # RESUME: reload prior progress so a kill/crash/stall doesn't lose completed
    # matters (run_depth checkpoints after each matter; rerun continues where it left off).
    items, key = [], {}
    if tagged_inp.exists() and tagged_key.exists():
        items = json.loads(tagged_inp.read_text())
        key = json.loads(tagged_key.read_text())
    done_matters = {v["matter"] for v in key.values()}
    if done_matters:
        print(f"resume: {len(done_matters)} matters / {len(items)} items already done for {tag}",
              flush=True)

    def flush():
        OUT.mkdir(parents=True, exist_ok=True)
        runs.mkdir(parents=True, exist_ok=True)
        for p in (OUT / "depth_judge_input.json", tagged_inp):
            p.write_text(json.dumps(items, indent=1, ensure_ascii=False))
        for p in (OUT / "depth_key.json", tagged_key):
            p.write_text(json.dumps(key, indent=1))

    count = 0
    for m in load_evalset():
        if count >= a.n:
            break
        rm = rec.get(m["matter_id"], {})
        issues = [c for c in m["answer_key"]["issues"]
                  if rm.get(c) and depth_key(m, c)][:a.max_issues]
        if not issues:
            continue
        count += 1
        if m["matter_id"] in done_matters:
            print(f"{m['matter_id']}: already done, skip  ({count}/{a.n})", flush=True)
            continue
        for arm_name, arm in arms.items():
            out = arm(m, issues)
            for pi in out["per_issue"]:
                dk = depth_key(m, pi["issue"])
                iid = f"{m['matter_id']}:{pi['issue']}:{arm_name}"
                items.append({
                    "item_id": iid, "issue": pi["issue"],
                    "matter_excerpt": scrub_external(m["matter_text"][:900]),
                    "key_reasoning": scrub_external(dk["reasoning"]),
                    "key_facts": [scrub_external(f) for f in dk["operative_facts"]],
                    "analysis": scrub_external(pi["analysis"]),
                })
                key[iid] = {"matter": m["matter_id"], "issue": pi["issue"],
                            "arm": arm_name, "n_evidence": pi.get("n_evidence", 0),
                            "cost_s": out["_cost"]["wall_clock_s"]}
        flush()   # checkpoint after each matter — kill/stall-safe + resumable
        print(f"{m['matter_id']}: {len(issues)} issue(s) x{len(arms)} arms  "
              f"({count}/{a.n})  [checkpoint: {len(key)} items]", flush=True)

    flush()
    print(f"\ntag: {tag}  ({len(items)} judge items, {len(arms)} arm(s))", flush=True)
    if a.smoke and items:
        print("\n--- sample SCRUBBED judge item (verify no names) ---")
        s = dict(items[0])
        print("item:", s["item_id"])
        print("analysis[:400]:", s["analysis"][:400])
    else:
        print("item_ids:", json.dumps([it["item_id"] for it in items]))
    print(f"-> {OUT/'depth_judge_input.json'}")


if __name__ == "__main__":
    main()
