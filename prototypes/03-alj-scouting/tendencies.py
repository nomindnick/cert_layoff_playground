"""Deterministic per-ALJ tendency statistics. No LLM. Every number here is the
verdict-bearing part of the prototype; the prose layer only dresses it.

Stats per ALJ (each with its supporting cite list):
  - issue footprint   : category mix vs corpus base rate (over/under)
  - outcome tendency  : respondent-win rate, Wilson 95% CI, vs base 0.240,
                        binomial p (BH-FDR corrected across tested ALJs)
  - procedural posture: procedural-category holdings + editor conduct prose
  - authorities       : authorities cited above corpus rate
  - persuasive args   : by category, which side's argument prevailed
"""

import argparse
import json
import math
from collections import Counter, defaultdict

from common import DECIDED, OUT, assemble, corpus_aggregates


# ---------- statistics (stdlib only) ----------

def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def _binom_pmf(k, n, p):
    return math.comb(n, k) * p ** k * (1 - p) ** (n - k)


def binom_two_sided_p(k, n, p0):
    """Exact two-sided binomial test p-value (n small here, <=70)."""
    if n == 0:
        return 1.0
    obs = _binom_pmf(k, n, p0)
    # numerical slack so the observed bin always counts
    tol = obs * (1 + 1e-9)
    return min(1.0, sum(_binom_pmf(i, n, p0) for i in range(n + 1)
                        if _binom_pmf(i, n, p0) <= tol))


def bh_fdr(pairs, q=0.05):
    """Benjamini-Hochberg. pairs: [(key, p)]. Returns {key: (p, qval, reject)}."""
    m = len(pairs)
    ordered = sorted(pairs, key=lambda kp: kp[1])
    out, qprev = {}, 1.0
    # compute adjusted q-values (monotone from the top)
    adj = [0.0] * m
    for i in range(m - 1, -1, -1):
        rank = i + 1
        qv = ordered[i][1] * m / rank
        qprev = min(qprev, qv)
        adj[i] = qprev
    thresh = max([i + 1 for i in range(m) if ordered[i][1] <= q * (i + 1) / m]
                 or [0])
    for i, (key, p) in enumerate(ordered):
        out[key] = (p, min(1.0, adj[i]), (i + 1) <= thresh)
    return out


# ---------- per-ALJ tendencies ----------

def issue_footprint(rec, agg, min_n=3):
    cc = Counter(c for g in rec["gold"] for c in g["categories"])
    n = sum(cc.values())
    base_total = agg["category_total"]
    rows = []
    for cat, k in cc.items():
        p = k / n if n else 0
        q = agg["category_dist"][cat] / base_total if base_total else 0
        rows.append({"category": cat, "count": k, "rate": round(p, 3),
                     "corpus_rate": round(q, 3), "lift": round(p - q, 3)})
    rows.sort(key=lambda r: -r["lift"])
    over = [r for r in rows if r["count"] >= min_n and r["lift"] > 0.03][:4]
    under = [r for r in rows if r["lift"] < -0.03][-3:]
    return {"n": n, "over": over, "under": under, "all": rows}


def outcome_tendency(rec, agg):
    decided = [h for h in rec["structured"] if h["prevailing_party"] in DECIDED]
    n = len(decided)
    if n == 0:
        return None
    k = sum(h["prevailing_party"] == "respondent" for h in decided)
    base = agg["respondent_win_base"]
    lo, hi = wilson_ci(k, n)
    p = binom_two_sided_p(k, n, base)
    return {
        "n_decided": n, "respondent_wins": k, "win_rate": round(k / n, 3),
        "ci95": [round(lo, 3), round(hi, 3)], "base_rate": round(base, 3),
        "direction": "respondent-leaning" if k / n > base else "district-leaning",
        "p_value": p,
        "examples": [{"case_no": h["case_no"], "idx": h["idx"], "year": h["year"],
                      "category": h["category"], "won": h["prevailing_party"],
                      "district": h["district"]} for h in decided],
    }


def editor_observations(rec, limit=12):
    """Verbatim gold prose that NAMES this ALJ — the editors' own attributed
    observations. Prefer rows that name only this ALJ (solo) and narrate
    adjudicative conduct, since multi-cite rows can describe another judge."""
    obs = [g for g in rec["gold"] if g["names_self"]]
    obs.sort(key=lambda g: (not (g["solo"] and g["conduct_obs"]),
                            not g["conduct_obs"], not g["solo"], len(g["text"])))
    seen, out = set(), []
    for g in obs:
        key = g["text"][:80]
        if key in seen:
            continue
        seen.add(key)
        out.append({"year": g["year"], "district": g["district"],
                    "solo": g["solo"], "conduct": g["conduct_obs"], "text": g["text"]})
        if len(out) >= limit:
            break
    return out


def procedural_posture(rec):
    proc = [h for h in rec["structured"]
            if (h["category"] or "") == "procedural_issues"]
    pwins = sum(h["prevailing_party"] == "respondent" for h in proc
                if h["prevailing_party"] in DECIDED)
    pdec = sum(h["prevailing_party"] in DECIDED for h in proc)
    return {
        "structured_procedural": len(proc),
        "procedural_respondent_wins": f"{pwins}/{pdec}" if pdec else "0/0",
    }


def authorities_above_corpus(rec, agg, min_count=2):
    from common import _norm_cite
    cc = Counter(_norm_cite(a["cite"]) for h in rec["structured"]
                 for a in h["authorities"] if a["cite"])
    n = sum(cc.values())
    base = agg["authority_counts"]
    base_n = sum(base.values()) or 1
    rows = []
    for cite, k in cc.most_common():
        if k < min_count:
            continue
        rate = k / n if n else 0
        crate = base[cite] / base_n
        rows.append({"cite": cite, "count": k, "rate": round(rate, 3),
                     "corpus_rate": round(crate, 4), "lift": round(rate - crate, 3)})
    rows.sort(key=lambda r: -r["lift"])
    return rows[:6]


def persuasive_args(rec, max_cat=4, max_ex=2):
    by_cat = defaultdict(lambda: {"decided": 0, "respondent_wins": 0, "examples": []})
    for h in rec["structured"]:
        if h["prevailing_party"] not in DECIDED:
            continue
        cat = h["category"] or "uncategorized"
        slot = by_cat[cat]
        slot["decided"] += 1
        won = h["prevailing_party"]
        slot["respondent_wins"] += won == "respondent"
        if len(slot["examples"]) < max_ex and h["arguments"]:
            winning = [a["summary"] for a in h["arguments"] if a["party"] == won]
            slot["examples"].append({
                "case_no": h["case_no"], "idx": h["idx"], "won": won,
                "issue": h["issue_statement"], "winning_argument": winning[:1],
            })
    rows = sorted(by_cat.items(), key=lambda kv: -kv[1]["decided"])[:max_cat]
    return {cat: v for cat, v in rows}


def tendencies_for(rec, agg):
    return {
        "surname": rec["surname"],
        "ambiguous": rec["ambiguous"],
        "density": rec["density"],
        "issue_footprint": issue_footprint(rec, agg),
        "outcome": outcome_tendency(rec, agg),
        "procedural": procedural_posture(rec),
        "authorities": authorities_above_corpus(rec, agg),
        "persuasive_args": persuasive_args(rec),
        "editor_observations": editor_observations(rec),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-gold", type=int, default=20,
                    help="density bar: minimum gold cites to be 'usable'")
    ap.add_argument("--dump", action="store_true", help="write tendencies_all.json")
    args = ap.parse_args()

    aljs = assemble()
    agg = corpus_aggregates(aljs)
    OUT.mkdir(parents=True, exist_ok=True)

    usable = {s: r for s, r in aljs.items()
              if r["density"]["gold_cites"] >= args.min_gold and not r["ambiguous"]}
    tend = {s: tendencies_for(r, agg) for s, r in usable.items()}

    # BH-FDR across the win-rate tests of every ALJ with >=12 decided holdings
    tested = [(s, t["outcome"]["p_value"]) for s, t in tend.items()
              if t["outcome"] and t["outcome"]["n_decided"] >= 12]
    fdr = bh_fdr(tested) if tested else {}

    print(f"corpus respondent-win base = {agg['respondent_win_base']:.3f} "
          f"(n={agg['decided_total']})")
    print(f"usable ALJs (>= {args.min_gold} gold cites, non-ambiguous): {len(usable)}")
    print(f"  with >=12 decided structured holdings (win-rate testable): {len(tested)}")
    print(f"  surviving BH-FDR (q=.05) on win-rate: "
          f"{sum(1 for v in fdr.values() if v[2])}\n")

    print(f"{'ALJ':16s} {'gold':>4s} {'dec':>4s} {'win':>5s} {'95% CI':>13s} "
          f"{'p':>7s} {'q':>6s} sig  top-over-category")
    for s, t in sorted(tend.items(),
                       key=lambda kv: -(kv[1]['outcome']['n_decided'] if kv[1]['outcome'] else 0)):
        o = t["outcome"]
        over = t["issue_footprint"]["over"]
        oc = f"{over[0]['category']}({over[0]['rate']}v{over[0]['corpus_rate']})" if over else "-"
        if o:
            q = fdr.get(s, (o["p_value"], 1.0, False))
            ci = f"[{o['ci95'][0]:.2f},{o['ci95'][1]:.2f}]"
            sig = "***" if q[2] else ("*" if o["p_value"] < 0.05 else "")
            print(f"{s:16s} {t['density']['gold_cites']:4d} {o['n_decided']:4d} "
                  f"{o['win_rate']:5.2f} {ci:>13s} {o['p_value']:7.4f} "
                  f"{q[1]:6.3f} {sig:3s}  {oc}")
        else:
            print(f"{s:16s} {t['density']['gold_cites']:4d} {'-':>4s} "
                  f"{'-':>5s} {'(gold-only)':>13s} {'':7s} {'':6s} {'':3s}  {oc}")

    if args.dump:
        for s, t in tend.items():
            t["_fdr"] = fdr.get(s)
        (OUT / "tendencies_all.json").write_text(json.dumps(tend, indent=1))
        print(f"\nwrote {OUT / 'tendencies_all.json'} ({len(tend)} ALJs)")


if __name__ == "__main__":
    main()
