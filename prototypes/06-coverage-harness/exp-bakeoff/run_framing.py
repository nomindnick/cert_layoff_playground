#!/usr/bin/env python3
"""W11 v4 — PRESENTATION diagnostic: raw cases vs rules+example vs rules-only.

Tests whether the pattern-matching pull (predictions track the retrieved-outcome MIX, not
the facts) is a PRESENTATION artifact. For each recoverable matter-issue, the SAME analyzer
(qwen3.5:35b) analyzes under three evidence framings, varying ONLY presentation:
  raw       — the balanced case pack (current pattern-match baseline)
  rulesex   — the distilled rules WITH worked illustration + outcome (treatise style)
  rulesonly — the distilled rules, APPLICATION/outcome lines stripped

Distillation is a cheap gemma4:12b pre-pass. Runs in TWO passes (distill all on gemma, then
analyze all on qwen) to avoid reloading the 23GB analyzer between every distill call.

  CORPUS_ROOT=... run_framing.py [--analyzer qwen3.5:35b --distiller gemma4:12b --n 12
                                  --max-issues 3 --k 8 --smoke]
-> output/runs/depth.frame-<analyzer>.{input,key}.json   (arms: raw, rulesex, rulesonly)
   output/runs/frame-<analyzer>.digests.json             (the distilled rule digests, de-id)
"""

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
sys.path.insert(0, str(PROTO))
sys.path.insert(0, str(PROTO / "scoreboard"))

from build_evalset import load_evalset                 # noqa: E402
from arms.rule_distill import distill, retrieve_pack   # noqa: E402
from arms.depth_analyzer import _evidence_block        # noqa: E402
from harness.issues import ISSUE_DEFS                   # noqa: E402
from harness.deid import scrub_external                # noqa: E402
from run_depth import recoverable_map, depth_key       # noqa: E402
from corpuslib.llm import generate                      # noqa: E402

OUT = HERE / "output" / "runs"


def _framing_prompt(matter, issue, block, kind):
    src = ("ANALOGOUS HOLDINGS FROM THE CORPUS (facts + the ALJ's reasoning + who prevailed)"
           if kind == "raw" else
           "RULE DIGEST FOR THIS ISSUE (the operative rules, distilled from corpus decisions)")
    ground = "the holdings" if kind == "raw" else "these rules"
    return (f"ISSUE: {issue} — {ISSUE_DEFS.get(issue, issue)}\n\n{matter['matter_text']}\n\n"
            f"{src}:\n{block}\n\n"
            f"Using {ground}, analyze how this issue is likely to be resolved in THIS matter: "
            "state the operative legal distinction/test that governs it, reason about how THESE "
            "facts map onto it, and give the likely outcome (does the district's action STAND?). "
            f"Ground your analysis in {ground}; cite the supporting authority (District (ALJ), year).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyzer", default="qwen3.5:35b")
    ap.add_argument("--distiller", default="gemma4:12b")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--max-issues", type=int, default=3)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--num-predict", type=int, default=8000)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if a.smoke:
        a.n, a.max_issues = 1, 1
    tag = "frame-" + a.analyzer.replace(":", "-")

    rec = recoverable_map()
    # select matter-issues
    sel = []
    for m in load_evalset():
        if len({x[0] for x in sel}) >= a.n:
            break
        issues = [c for c in m["answer_key"]["issues"]
                  if rec.get(m["matter_id"], {}).get(c) and depth_key(m, c)][:a.max_issues]
        for iss in issues:
            sel.append((m["matter_id"], iss, m))

    # PASS 1 — distill all (gemma loaded once)
    print(f"PASS 1: distilling {len(sel)} packs on {a.distiller} ...", flush=True)
    t0 = time.time()
    packs = {}
    for mid, iss, m in sel:
        ev = retrieve_pack(m, iss, k=a.k, balanced=True)
        d = distill(f"ollama:{a.distiller}", m, iss, ev)
        packs[(mid, iss)] = (ev, d)
    print(f"  distilled in {time.time()-t0:.0f}s", flush=True)

    # PASS 2 — analyze all 3 framings (qwen loaded once)
    print(f"PASS 2: analyzing 3 framings x {len(sel)} on {a.analyzer} ...", flush=True)
    items, key, digests = [], {}, []
    for mid, iss, m in sel:
        ev, d = packs[(mid, iss)]
        dk = depth_key(m, iss)
        excerpt = scrub_external(m["matter_text"][:900])
        kr, kf = scrub_external(dk["reasoning"]), [scrub_external(f) for f in dk["operative_facts"]]
        framings = {"raw": _evidence_block(ev), "rulesex": d["rules_full"],
                    "rulesonly": d["rules_only"]}
        for arm, block in framings.items():
            txt = generate(f"ollama:{a.analyzer}", _framing_prompt(m, iss, block, arm),
                           system=("You are a California school-district attorney analyzing a "
                                   "certificated-employee layoff (Education Code 44949/44955). Be "
                                   "specific: the operative test and how it applies to these facts."),
                           think=True, options={"temperature": 0.3, "num_predict": a.num_predict})
            iid = f"{mid}:{iss}:{arm}"
            items.append({"item_id": iid, "issue": iss, "matter_excerpt": excerpt,
                          "key_reasoning": kr, "key_facts": kf, "analysis": scrub_external(txt)})
            key[iid] = {"matter": mid, "issue": iss, "arm": arm, "n_evidence": len(ev), "cost_s": 0}
        digests.append({"matter": mid, "issue": iss,
                        "rules_full": scrub_external(d["rules_full"]),
                        "rules_only": scrub_external(d["rules_only"])})
        print(f"  {mid}:{iss} x3 framings", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"depth.{tag}.input.json").write_text(json.dumps(items, indent=1, ensure_ascii=False))
    (OUT / f"depth.{tag}.key.json").write_text(json.dumps(key, indent=1))
    (OUT / f"{tag}.digests.json").write_text(json.dumps(digests, indent=1, ensure_ascii=False))
    print(f"\ntag: {tag}  ({len(items)} items = {len(sel)} matter-issues x 3 framings)")
    print("item_ids:", json.dumps([it["item_id"] for it in items]))
    if a.smoke and digests:
        print("\n--- SMOKE: rule digest (verify no names) ---")
        print("RULES_FULL[:600]:\n", digests[0]["rules_full"][:600])
        print("\nRULES_ONLY[:300]:\n", digests[0]["rules_only"][:300])


if __name__ == "__main__":
    main()
