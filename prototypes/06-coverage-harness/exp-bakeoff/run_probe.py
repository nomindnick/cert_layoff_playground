#!/usr/bin/env python3
"""E1 issue-spotter probe: sweep local models, score breadth vs the E0 floor.

Usage:
  CORPUS_ROOT=/home/nick/Projects/cert_layoff_merged run_probe.py --smoke
  CORPUS_ROOT=/home/nick/Projects/cert_layoff_merged run_probe.py [model ...]
    (default models: gemma4:31b qwen3.6:27b)
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
sys.path.insert(0, str(PROTO))
sys.path.insert(0, str(PROTO / "scoreboard"))

from run_scoreboard import score, frequency_prior_arm, keyword_arm, oracle_arm  # noqa: E402
from build_evalset import load_evalset                                          # noqa: E402
from arms.issue_spotter import make_arm                                          # noqa: E402
from harness.metrics import rarity_weight                                        # noqa: E402

OUT = HERE / "output"
DEFAULT_MODELS = ["gemma4:31b", "qwen3.6:27b"]
FLOOR = 0.373   # frequency-prior rarity_recall (E0)


def _cost(s):
    cs = [r["cost"].get("wall_clock_s", 0) for r in s["rows"]]
    errs = sum(1 for r in s["rows"] if r["cost"].get("error"))
    return (sum(cs) / len(cs) if cs else 0), errs


def _miss_over(s):
    fn, fp = Counter(), Counter()
    for r in s["rows"]:
        fn.update(r["breadth"]["fn"])
        fp.update(r["breadth"]["fp_candidates"])
    return fn, fp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="*", default=None)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    evalset = load_evalset()
    models = a.models or DEFAULT_MODELS

    if a.smoke:
        m = evalset[0]
        arm = make_arm(f"ollama:{models[0]}")
        out = arm(m)
        print(f"SMOKE  model={models[0]}  matter={m['matter_id']}")
        print("  key issues:", m["answer_key"]["issues"])
        print("  spotted   :", [(s["category"], round(s["confidence"], 2))
                                 for s in out["spotted_issues"]])
        print("  cost:", out["_cost"])
        return

    print(f"eval set: {len(evalset)} matters | floor (freq-prior rarity_recall): {FLOOR}\n")
    print(f"{'arm':16s} {'recall':>7s} {'rarity_R':>9s} {'precision':>10s} "
          f"{'sec/matter':>11s} {'errs':>5s}")
    print("-" * 64)
    results = {}
    scored = {}   # score each local model ONCE; reuse for table + diagnostics
    for model in models:
        s = score(make_arm(f"ollama:{model}"), evalset)
        scored[model] = s
        sec, errs = _cost(s)
        results[model] = {k: s[k] for k in ("recall", "precision", "rarity_recall")}
        results[model].update({"sec_per_matter": round(sec, 1), "errors": errs})
        flag = "  >floor" if s["rarity_recall"] > FLOOR else "  <FLOOR"
        print(f"{model:16s} {s['recall']:>7.3f} {s['rarity_recall']:>9.3f} "
              f"{s['precision']:>10.3f} {sec:>11.1f} {errs:>5d}{flag}")
    # deterministic baselines for context
    for name, fn in (("freq-prior", frequency_prior_arm), ("keyword", keyword_arm),
                     ("oracle", oracle_arm)):
        s = score(fn, evalset)
        print(f"{name:16s} {s['recall']:>7.3f} {s['rarity_recall']:>9.3f} "
              f"{s['precision']:>10.3f} {'0.0':>11s} {0:>5d}")

    # diagnostics for the local models
    print("\n--- what each local model misses / over-spots (by rarity weight) ---")
    for model in models:
        fn, fp = _miss_over(scored[model])
        top_miss = sorted(fn, key=lambda c: fn[c] * rarity_weight(c), reverse=True)[:5]
        print(f"{model}: most-missed {[(c, fn[c]) for c in top_miss]}")
        print(f"{'':{len(model)}}  over-spots {fp.most_common(5)}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "probe_results.json").write_text(json.dumps(
        {"floor": FLOOR, "n_matters": len(evalset), "models": results}, indent=1))
    print(f"\n-> {OUT/'probe_results.json'}")


if __name__ == "__main__":
    main()
