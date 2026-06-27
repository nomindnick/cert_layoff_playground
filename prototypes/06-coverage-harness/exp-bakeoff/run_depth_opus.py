#!/usr/bin/env python3
"""Opus reference depth arm (frontier ceiling, subagent fan-out).

corpuslib.llm is ollama-only by design, so the frontier arm runs as a Workflow.
This script does the Python halves (skeleton/merge pattern, per CLAUDE.md):

  --prep  : for the SAME matter-issues as run_depth, build SCRUBBED analysis
            prompts (closed-book + RAG, same templates/evidence as the local arm)
            -> output/opus_prompts.json (item_id -> prompt) + opus_key.json
  (then run the opus analysis Workflow over opus_prompts.json -> opus_analyses.json)
  --merge : combine the Opus analyses into opus_judge_input.json + opus_depth_key.json
            (same format as the local depth judge) for the SAME depth judge.

Distinct opus_* filenames so this never collides with a running local run_depth.
"""

import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
sys.path.insert(0, str(PROTO))
sys.path.insert(0, str(PROTO / "scoreboard"))

from build_evalset import load_evalset                   # noqa: E402
from arms.depth_analyzer import _prompt                  # noqa: E402
from arms.retrieval import retrieve                      # noqa: E402
from harness.deid import scrub_external                  # noqa: E402
from run_depth import recoverable_map, depth_key         # noqa: E402

OUT = HERE / "output"


def _select(n=12, max_issues=3):
    rec = recoverable_map()
    out, count = [], 0
    for m in load_evalset():
        if count >= n:
            break
        rm = rec.get(m["matter_id"], {})
        issues = [c for c in m["answer_key"]["issues"]
                  if rm.get(c) and depth_key(m, c)][:max_issues]
        if issues:
            count += 1
            out.append((m, issues))
    return out


def _scrub_ev(ev):
    out = []
    for h in ev:
        h2 = dict(h)
        h2["facts"] = [scrub_external(f) for f in h["facts"]]
        h2["reasoning"] = scrub_external(h["reasoning"])
        out.append(h2)
    return out


def prep(balanced=False, k=6, rag_only=False, suffix=""):
    prompts, key = {}, {}
    for m, issues in _select():
        sm = copy.deepcopy(m)
        sm["matter_text"] = scrub_external(m["matter_text"])
        for iss in issues:
            ev = _scrub_ev(retrieve(m, iss, set(m["exclude_ids"]), k=k, balanced=balanced))
            dk = depth_key(m, iss)
            arms = (("rag", ev),) if rag_only else (("closedbook", []), ("rag", ev))
            for arm, use_ev in arms:
                iid = f"{m['matter_id']}:{iss}:{arm}"
                prompts[iid] = _prompt(sm, iss, use_ev)
                key[iid] = {"matter": m["matter_id"], "issue": iss, "arm": arm,
                            "n_evidence": len(use_ev),
                            "matter_excerpt": scrub_external(m["matter_text"][:900]),
                            "key_reasoning": scrub_external(dk["reasoning"]),
                            "key_facts": [scrub_external(f) for f in dk["operative_facts"]]}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"opus_prompts{suffix}.json").write_text(json.dumps(prompts, indent=1, ensure_ascii=False))
    (OUT / f"opus_key{suffix}.json").write_text(json.dumps(key, indent=1, ensure_ascii=False))
    print(f"{len(prompts)} opus prompts (suffix='{suffix}', balanced={balanced}, k={k})")
    print("item_ids:", json.dumps(list(prompts)))


def merge(suffix=""):
    key = json.loads((OUT / f"opus_key{suffix}.json").read_text())
    analyses = {a["item_id"]: a["analysis"]
                for a in json.loads((OUT / f"opus_analyses{suffix}.json").read_text())}
    items, dkey = [], {}
    for iid, k in key.items():
        items.append({"item_id": iid, "issue": k["issue"],
                      "matter_excerpt": k["matter_excerpt"],
                      "key_reasoning": k["key_reasoning"], "key_facts": k["key_facts"],
                      "analysis": scrub_external(analyses.get(iid, "(missing)"))})
        dkey[iid] = {"matter": k["matter"], "issue": k["issue"], "arm": k["arm"],
                     "n_evidence": k["n_evidence"], "cost_s": 0}
    (OUT / f"opus_judge_input{suffix}.json").write_text(json.dumps(items, indent=1, ensure_ascii=False))
    (OUT / f"opus_depth_key{suffix}.json").write_text(json.dumps(dkey, indent=1))
    print(f"{len(items)} judge items -> opus_judge_input{suffix}.json")
    print("item_ids:", json.dumps(list(key)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", action="store_true")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--balanced", action="store_true")
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--rag-only", action="store_true")
    ap.add_argument("--suffix", default="")
    a = ap.parse_args()
    if a.merge:
        merge(a.suffix)
    else:
        prep(balanced=a.balanced, k=a.k, rag_only=a.rag_only, suffix=a.suffix)


if __name__ == "__main__":
    main()
