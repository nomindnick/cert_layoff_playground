#!/usr/bin/env python3
"""Longitudinal P2 transfer test on the MERGED corpus (2004/2009 spike +
2018-2025 production). Point CORPUS_ROOT at the merged root.

The open question from P2 FINDINGS: do per-ALJ win-rate tendencies PERSIST across
eras, or are they era-specific? Here we can finally split each ALJ's decided
holdings by era and compare. Caveat surfaced by the data: judicial rotation means
few ALJs have dense dockets ~15 years apart, so this is directional, not
definitive — the bridge years (2010-2017) in the full corpus will firm it up.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import common  # noqa: E402
import tendencies  # noqa: E402

E1 = {"2004", "2009"}
E2 = {str(y) for y in range(2018, 2026)}


def winrate(hs):
    dec = [h for h in hs if h["prevailing_party"] in common.DECIDED]
    if not dec:
        return None
    return sum(h["prevailing_party"] == "respondent" for h in dec) / len(dec), len(dec)


def era_base(aljs, E):
    w = d = 0
    for r in aljs.values():
        for h in r["structured"]:
            if h["year"] in E and h["prevailing_party"] in common.DECIDED:
                d += 1
                w += h["prevailing_party"] == "respondent"
    return (w / d if d else None), d


def main():
    aljs = common.assemble()
    agg = common.corpus_aggregates(aljs)
    base = agg["respondent_win_base"]
    b1, n1 = era_base(aljs, E1)
    b2, n2 = era_base(aljs, E2)
    print(f"corpus respondent-win base:  era1(04/09)={b1:.3f} (n={n1})  "
          f"era2(18-25)={b2:.3f} (n={n2})  pooled={base:.3f}")

    print("\n=== per-ALJ win-rate by era (ALJs decided in BOTH eras; '<<' = >=12 each) ===")
    print(f"{'ALJ':14s} {'era1 win(n)':>13s} {'era2 win(n)':>13s}   side1 side2  stable?")
    rows = []
    for s, r in sorted(aljs.items()):
        if r["ambiguous"]:
            continue
        w1 = winrate([h for h in r["structured"] if h["year"] in E1])
        w2 = winrate([h for h in r["structured"] if h["year"] in E2])
        if not (w1 and w2):
            continue
        side1 = "R" if w1[0] > base else "D"
        side2 = "R" if w2[0] > base else "D"
        stable = "yes" if side1 == side2 else "FLIP"
        wp = w1[1] >= 12 and w2[1] >= 12
        rows.append((s, w1, w2, stable, wp))
        print(f"{s:14s} {w1[0]:.2f}({w1[1]:>2d}){'':5s} {w2[0]:.2f}({w2[1]:>2d}){'':5s}"
              f"   {side1:^5s} {side2:^5s}  {stable}{'  <<' if wp else ''}")
    wp = [r for r in rows if r[4]]
    print(f"\nwell-powered (>=12 decided in BOTH eras): {[r[0] for r in wp]}")
    if wp:
        print(f"  of those, win-rate stays the same side of base across eras: "
              f"{sum(1 for r in wp if r[3] == 'yes')}/{len(wp)}")

    print("\n=== pooled-era per-ALJ tendencies (merged data = more power than either "
          "era alone) ===")
    tested = [(s, tendencies.outcome_tendency(r, agg)) for s, r in aljs.items()
              if not r["ambiguous"]]
    tested = [(s, o) for s, o in tested if o and o["n_decided"] >= 12]
    fdr = tendencies.bh_fdr([(s, o["p_value"]) for s, o in tested])
    sig = [s for s, o in tested if fdr[s][2]]
    print(f"testable ALJs (>=12 pooled decided): {len(tested)};  "
          f"surviving BH-FDR (q=.05): {len(sig)} -> {sig}")
    for s, o in sorted(tested, key=lambda x: x[1]["p_value"]):
        q = fdr[s]
        mark = "***" if q[2] else ("*" if o["p_value"] < 0.05 else "")
        print(f"   {s:14s} n={o['n_decided']:3d} win={o['win_rate']:.2f} "
              f"p={o['p_value']:.3f} q={q[1]:.3f} {mark}")


if __name__ == "__main__":
    main()
