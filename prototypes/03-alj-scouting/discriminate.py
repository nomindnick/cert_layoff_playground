"""The falsification core: do per-ALJ tendencies differ beyond sampling noise,
or are they a horoscope? Pure-stdlib permutation tests (no numpy).

Two questions, each with a global null and a stricter within-year null (the
within-year shuffle controls for temporal drift — e.g. 'skipping' surging in
the post-2008 budget years — so a surviving signal is ALJ-specific, not era):

  1. WIN-RATE dispersion across ALJs (structured 2004/2009 decided holdings).
       statistic Q = sum_a (k_a - n_a*p)^2 / (n_a*p(1-p))   [chi-square-like]
       null: shuffle the win/loss labels across holdings, keep each ALJ's n.
  2. ISSUE-MIX dispersion across ALJs (gold footprint).
       statistic = Pearson chi-square of the ALJ x category table.
       null: shuffle category labels across gold-cite units, keep each ALJ's
       count and the category marginals (expected counts are therefore constant
       across permutations — precomputed once).

p = (1 + #{stat_perm >= stat_obs}) / (1 + n_perm).
"""

import argparse
import random
from collections import Counter, defaultdict

from common import DECIDED, assemble


def _perm_pvalue(obs, gen, n_perm):
    ge = sum(1 for _ in range(n_perm) if gen() >= obs)
    return (1 + ge) / (1 + n_perm)


# ---------- 1. win-rate dispersion ----------

def winrate_test(aljs, min_n=12, n_perm=5000, seed=7):
    rng = random.Random(seed)
    # decided holdings as (alj, label, year); restrict ALJs to those with >=min_n
    pool = []
    for s, rec in aljs.items():
        if rec["ambiguous"]:
            continue
        dh = [(h["prevailing_party"] == "respondent", h["year"])
              for h in rec["structured"] if h["prevailing_party"] in DECIDED]
        if len(dh) >= min_n:
            for won, yr in dh:
                pool.append((s, 1 if won else 0, yr))
    aljs_in = sorted({s for s, _, _ in pool})
    idx = {s: i for i, s in enumerate(aljs_in)}
    a_arr = [idx[s] for s, _, _ in pool]
    labels = [l for _, l, _ in pool]
    years = [y for _, _, y in pool]
    n_a = Counter(a_arr)
    p = sum(labels) / len(labels)
    denom = [n_a[i] * p * (1 - p) for i in range(len(aljs_in))]

    def Q(lab):
        k = [0] * len(aljs_in)
        for a, l in zip(a_arr, lab):
            k[a] += l
        return sum((k[i] - n_a[i] * p) ** 2 / denom[i]
                   for i in range(len(aljs_in)) if denom[i] > 0)

    obs = Q(labels)
    # year strata for the within-year null
    strata = defaultdict(list)
    for j, y in enumerate(years):
        strata[y].append(j)

    def shuffle_global():
        lab = labels[:]
        rng.shuffle(lab)
        return Q(lab)

    def shuffle_within_year():
        lab = labels[:]
        for js in strata.values():
            vals = [lab[j] for j in js]
            rng.shuffle(vals)
            for j, v in zip(js, vals):
                lab[j] = v
        return Q(lab)

    return {
        "n_aljs": len(aljs_in), "n_holdings": len(pool), "base": round(p, 3),
        "stat": round(obs, 2),
        "p_global": _perm_pvalue(obs, shuffle_global, n_perm),
        "p_within_year": _perm_pvalue(obs, shuffle_within_year, n_perm),
        "aljs": aljs_in,
    }


# ---------- 2. issue-mix dispersion ----------

def issuemix_test(aljs, min_gold=20, n_perm=5000, seed=7):
    rng = random.Random(seed)
    # units: (alj, category, year) — one per (citing ALJ, holding-category)
    units = []
    for s, rec in aljs.items():
        if rec["ambiguous"] or rec["density"]["gold_cites"] < min_gold:
            continue
        for g in rec["gold"]:
            for c in g["categories"]:
                units.append((s, c, g["year"]))
    aljs_in = sorted({s for s, _, _ in units})
    cats = sorted({c for _, c, _ in units})
    ai = {s: i for i, s in enumerate(aljs_in)}
    ci = {c: i for i, c in enumerate(cats)}
    A, C = len(aljs_in), len(cats)
    a_arr = [ai[s] for s, _, _ in units]
    c_arr = [ci[c] for _, c, _ in units]
    years = [y for _, _, y in units]
    N = len(units)
    row = Counter(a_arr)
    col = Counter(c_arr)
    # expected is constant under label permutation (row & col totals fixed)
    exp = [[row[i] * col[j] / N for j in range(C)] for i in range(A)]

    def chi2(cs):
        o = [[0] * C for _ in range(A)]
        for a, c in zip(a_arr, cs):
            o[a][c] += 1
        return sum((o[i][j] - exp[i][j]) ** 2 / exp[i][j]
                   for i in range(A) for j in range(C) if exp[i][j] > 0)

    obs = chi2(c_arr)
    strata = defaultdict(list)
    for j, y in enumerate(years):
        strata[y].append(j)

    def shuffle_global():
        cs = c_arr[:]
        rng.shuffle(cs)
        return chi2(cs)

    def shuffle_within_year():
        cs = c_arr[:]
        for js in strata.values():
            vals = [cs[j] for j in js]
            rng.shuffle(vals)
            for j, v in zip(js, vals):
                cs[j] = v
        return chi2(cs)

    # which ALJ x category cells drive it (largest standardized residuals)
    o = [[0] * C for _ in range(A)]
    for a, c in zip(a_arr, c_arr):
        o[a][c] += 1
    resid = []
    for i in range(A):
        for j in range(C):
            e = exp[i][j]
            if e >= 3 and o[i][j] >= 3:
                resid.append((round((o[i][j] - e) / e ** 0.5, 2),
                              aljs_in[i], cats[j], o[i][j], round(e, 1)))
    resid.sort(reverse=True)

    return {
        "n_aljs": A, "n_categories": C, "n_units": N, "stat": round(obs, 1),
        "p_global": _perm_pvalue(obs, shuffle_global, n_perm),
        "p_within_year": _perm_pvalue(obs, shuffle_within_year, n_perm),
        "top_residuals": resid[:12],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-perm", type=int, default=5000)
    ap.add_argument("--min-gold", type=int, default=20)
    ap.add_argument("--min-n", type=int, default=12)
    args = ap.parse_args()

    aljs = assemble()

    print("=== 1. WIN-RATE dispersion across ALJs (structured 2004/2009) ===")
    w = winrate_test(aljs, min_n=args.min_n, n_perm=args.n_perm)
    print(f"  {w['n_aljs']} ALJs, {w['n_holdings']} decided holdings, base={w['base']}")
    print(f"  Q = {w['stat']}")
    print(f"  p (global shuffle)      = {w['p_global']:.4f}")
    print(f"  p (within-year shuffle) = {w['p_within_year']:.4f}")
    verdict = ("REAL signal" if w["p_within_year"] < 0.05 else
               "weak/era-only" if w["p_global"] < 0.05 else "indistinguishable (horoscope)")
    print(f"  -> {verdict}\n")

    print("=== 2. ISSUE-MIX dispersion across ALJs (gold footprint) ===")
    m = issuemix_test(aljs, min_gold=args.min_gold, n_perm=args.n_perm)
    print(f"  {m['n_aljs']} ALJs x {m['n_categories']} categories, {m['n_units']} units")
    print(f"  chi2 = {m['stat']}")
    print(f"  p (global shuffle)      = {m['p_global']:.4f}")
    print(f"  p (within-year shuffle) = {m['p_within_year']:.4f}")
    verdict = ("REAL ALJ-specific signal" if m["p_within_year"] < 0.05 else
               "era/docket-driven only" if m["p_global"] < 0.05 else "indistinguishable")
    print(f"  -> {verdict}")
    print("  top ALJ x category fingerprints (std. residual, alj, cat, obs, exp):")
    for r in m["top_residuals"]:
        print(f"     {r[0]:+5.2f}  {r[1]:14s} {r[2]:22s} obs={r[3]:2d} exp={r[4]}")


if __name__ == "__main__":
    main()
