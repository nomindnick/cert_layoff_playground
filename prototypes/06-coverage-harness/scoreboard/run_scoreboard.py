#!/usr/bin/env python3
"""E0 scoreboard: score an arm over the eval set, and the discrimination test.

`score(arm_fn, evalset)` is the entry point E1 arms plug into. This module also
defines deterministic SANITY ARMS (random floor / frequency-prior / keyword /
oracle) whose ordering on the metric is E0's validation gate: if
random < frequency-prior < keyword < oracle, the breadth metric discriminates.

Usage:  CORPUS_ROOT=/home/nick/Projects/cert_layoff_merged run_scoreboard.py
        (builds the eval set if missing, runs the sanity arms, prints leaderboard)
"""

import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from harness.corpus import holdings, census                 # noqa: E402
from harness.metrics import score_matter, _content          # noqa: E402
from build_evalset import build, load_evalset, OUT          # noqa: E402

# ---- corpus-derived helpers (built once) ------------------------------------
_VALID_IDS = None
_PROFILES = None
_COMMON = None


def _corpus_index():
    """valid holding ids (grounding), per-category distinctive terms (keyword
    arm), and the most common categories (frequency-prior arm)."""
    global _VALID_IDS, _PROFILES, _COMMON
    if _VALID_IDS is not None:
        return
    _VALID_IDS = set()
    cat_terms = defaultdict(Counter)
    for h in holdings():
        _VALID_IDS.add(h["hid"])
        if not h["category"]:
            continue
        words = _content(" ".join([h["issue_statement"], h["summary"],
                                   *h["facts"]]))
        cat_terms[h["category"]].update(words)
    # TF-IDF over categories-as-documents: a term's weight in a category balances
    # frequency-in-category against how many categories use it (pure freq-ratio
    # surfaced rare junk → keyword arm scored at random). profile = {term: weight}.
    n_cats = len(cat_terms)
    df = Counter()
    for ctr in cat_terms.values():
        df.update(ctr.keys())
    _PROFILES = {}
    for cat, ctr in cat_terms.items():
        tot = sum(ctr.values()) or 1
        tfidf = {w: (c / tot) * math.log(n_cats / df[w]) for w, c in ctr.items()}
        top = sorted(tfidf, key=tfidf.get, reverse=True)[:40]
        _PROFILES[cat] = {w: tfidf[w] for w in top}
    _COMMON = [c for c, _ in Counter(census()["by_category"]).most_common()]


# ---- sanity arms ------------------------------------------------------------
_RNG = random.Random(0)
TOPN = 3   # arms commit to their top-N spots (mean issues/matter ≈ 3.1)


def random_arm(m):
    _corpus_index()
    cats = _RNG.sample(list(_PROFILES), TOPN)
    return {"spotted_issues": [{"category": c, "confidence": 0.5} for c in cats],
            "per_issue": [], "_cost": {"wall_clock_s": 0, "n_calls": 0}}


def frequency_prior_arm(m):
    _corpus_index()
    cats = _COMMON[:TOPN]
    return {"spotted_issues": [{"category": c, "confidence": 0.5} for c in cats],
            "per_issue": [], "_cost": {"wall_clock_s": 0, "n_calls": 0}}


def keyword_arm(m):
    _corpus_index()
    mwords = _content(m["matter_text"])
    cat_score = {c: sum(prof[w] for w in mwords & prof.keys())
                 for c, prof in _PROFILES.items()}
    scored = sorted(cat_score, key=cat_score.get, reverse=True)
    cats = [c for c in scored if cat_score[c] > 0][:TOPN]
    return {"spotted_issues": [{"category": c, "confidence": 0.6} for c in cats],
            "per_issue": [], "_cost": {"wall_clock_s": 0, "n_calls": 0}}


def oracle_arm(m):
    """Returns the answer key — recall must hit 1.0 (metric tops out correctly).
    Also feeds the depth key back as 'analysis' so the depth proxy reads high."""
    key = m["answer_key"]
    by_issue = {e["issue"]: e for e in key["depth"]}
    return {
        "spotted_issues": [{"category": c, "confidence": 1.0} for c in key["issues"]],
        "per_issue": [{"issue": c, "analysis": by_issue.get(c, {}).get("reasoning", ""),
                       "cited_holding_ids": [by_issue[c]["hid"]] if c in by_issue else []}
                      for c in key["issues"]],
        "_cost": {"wall_clock_s": 0, "n_calls": 0}}


# ---- aggregation ------------------------------------------------------------

def score(arm_fn, evalset):
    _corpus_index()
    rows = [score_matter(arm_fn(m), m, _VALID_IDS) for m in evalset]
    mean = lambda xs: round(sum(xs) / len(xs), 3) if xs else 0.0
    depth_vals = [d["proxy"] for r in rows for d in r["depth"]]
    g_rates = [r["grounding"]["rate"] for r in rows if r["grounding"]["rate"] is not None]
    return {
        "n": len(rows),
        "recall": mean([r["breadth"]["recall"] for r in rows]),
        "precision": mean([r["breadth"]["precision"] for r in rows]),
        "rarity_recall": mean([r["breadth"]["rarity_recall"] for r in rows]),
        "depth_proxy": mean(depth_vals) if depth_vals else None,
        "grounding": mean(g_rates) if g_rates else None,
        "rows": rows,
    }


def main():
    if not list(OUT.glob("*.json")):
        build(per_era=12)
    evalset = load_evalset()
    arms = {"random": random_arm, "freq-prior": frequency_prior_arm,
            "keyword": keyword_arm, "oracle": oracle_arm}
    print(f"eval set: {len(evalset)} matters\n")
    print(f"{'arm':12s} {'recall':>7s} {'rarity_R':>9s} {'precision':>10s} "
          f"{'depth_px':>9s} {'grounding':>10s}")
    print("-" * 62)
    cards = {}
    for name, fn in arms.items():
        s = score(fn, evalset)
        cards[name] = s
        dp = f"{s['depth_proxy']:.3f}" if s["depth_proxy"] is not None else "  —  "
        gr = f"{s['grounding']:.3f}" if s["grounding"] is not None else "  —  "
        print(f"{name:12s} {s['recall']:>7.3f} {s['rarity_recall']:>9.3f} "
              f"{s['precision']:>10.3f} {dp:>9s} {gr:>10s}")
    (HERE / "output" / "sanity_scorecard.json").write_text(
        json.dumps({k: {m: v for m, v in c.items() if m != "rows"}
                    for k, c in cards.items()}, indent=1))
    # discrimination gate. The floor an E1 arm must beat is the FREQUENCY PRIOR
    # (common issues are genuinely predictive), not random. The metric passes if
    # it orders random < freq-prior, a real lexical baseline beats the prior, and
    # oracle tops out.
    r = {k: cards[k]["rarity_recall"] for k in arms}
    ok = (r["random"] < r["freq-prior"] < r["keyword"] < r["oracle"] == 1.0)
    print(f"\ndiscrimination (rarity_recall): random {r['random']} < "
          f"freq-prior {r['freq-prior']} < keyword {r['keyword']} < "
          f"oracle {r['oracle']}  ->  {'PASS' if ok else 'FAIL'}")
    print(f"E1 floor-to-beat (frequency prior, rarity_recall): {r['freq-prior']}")


if __name__ == "__main__":
    main()
