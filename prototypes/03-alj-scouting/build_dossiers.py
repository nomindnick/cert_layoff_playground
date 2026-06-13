"""Assemble per-ALJ dossiers: the de-identified evidence a synthesis prompt
would inject. Writes output/dossiers/{alj}.json + dossiers_index.json.

Each dossier carries honest interpretation hints (win-rate significance, the
group-level discriminability context, standing caveats) so the downstream
synthesizer cannot dress a thin 2-year point estimate as a firm tendency.
"""

import argparse
import json

from common import OUT, assemble, corpus_aggregates
from discriminate import issuemix_test, winrate_test
from tendencies import bh_fdr, tendencies_for

CAVEATS = [
    "ALJ identity is keyed on SURNAME only (the gold volumes cite surnames); "
    "distinct judges who share a surname cannot be separated here.",
    "Structured outcome data covers only 2004 and 2009 — win-rate tendencies "
    "rest on a small, two-year sample and are confounded by case mix.",
    "The 35-year gold footprint is editorial (what expert editors chose to "
    "catalogue), not an exhaustive docket; issue mix reflects what this ALJ "
    "tends to HEAR, not necessarily how they rule.",
]


def win_interpretation(o, fdr_flag):
    if o is None:
        return ("No structured 2004/2009 holdings — no outcome tendency "
                "computable; this profile rests on the gold footprint and the "
                "editors' observations only.")
    wr, base, n, p = o["win_rate"], o["base_rate"], o["n_decided"], o["p_value"]
    if fdr_flag:
        return (f"Respondent-win rate {wr} vs corpus base {base} on {n} decided "
                f"holdings — STATISTICALLY ROBUST: survives Benjamini-Hochberg "
                f"correction across all tested ALJs. One of the few ALJs whose "
                f"individual outcome tendency is defensible on two years of data.")
    if n >= 12 and p < 0.05:
        return (f"Respondent-win rate {wr} vs base {base} (p={p:.3f}) — "
                f"NOMINALLY notable but does NOT survive multiple-comparison "
                f"correction; treat as suggestive only, not established.")
    if n >= 12:
        return (f"Respondent-win rate {wr} on {n} holdings is not distinguishable "
                f"from the corpus base {base}; no outcome tendency to report.")
    return (f"Only {n} decided holdings — too few to assert any outcome "
            f"tendency; report the rate as anecdote at most.")


def gold_footprint_samples(rec, over_cats, per_cat=2):
    out = {}
    cats = {r["category"] for r in over_cats}
    for cat in cats:
        rows = [g for g in rec["gold"] if cat in g["categories"]]
        rows.sort(key=lambda g: (not g["names_self"], len(g["text"])))
        out[cat] = [{"year": g["year"], "district": g["district"], "text": g["text"]}
                    for g in rows[:per_cat]]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-gold", type=int, default=20)
    ap.add_argument("--n-perm", type=int, default=5000)
    args = ap.parse_args()

    aljs = assemble()
    agg = corpus_aggregates(aljs)
    usable = {s: r for s, r in aljs.items()
              if r["density"]["gold_cites"] >= args.min_gold and not r["ambiguous"]}
    tend = {s: tendencies_for(r, agg) for s, r in usable.items()}

    tested = [(s, t["outcome"]["p_value"]) for s, t in tend.items()
              if t["outcome"] and t["outcome"]["n_decided"] >= 12]
    fdr = bh_fdr(tested) if tested else {}

    # group-level discriminability context (constant across dossiers)
    w = winrate_test(aljs, n_perm=args.n_perm)
    m = issuemix_test(aljs, min_gold=args.min_gold, n_perm=args.n_perm)
    disc = {
        "winrate_group_p_within_year": w["p_within_year"],
        "issuemix_group_p_within_year": m["p_within_year"],
        "note": ("As a GROUP, ALJs differ in respondent-win rate and issue mix "
                 "beyond chance (permutation p<0.001, surviving a within-year "
                 "control). But most INDIVIDUAL win-rate estimates are too thin "
                 "(two years) to name confidently — see each ALJ's hint."),
    }

    ddir = OUT / "dossiers"
    ddir.mkdir(parents=True, exist_ok=True)
    index = []
    for s, t in tend.items():
        o = t["outcome"]
        fdr_flag = fdr.get(s, (1, 1, False))[2]
        dossier = {
            "alj": s,
            "data_caveats": CAVEATS,
            "discriminability_context": disc,
            "density": t["density"],
            "outcome": (o and {**o, "fdr_significant": fdr_flag,
                               "interpretation": win_interpretation(o, fdr_flag)}) or
                       {"interpretation": win_interpretation(None, False)},
            "issue_footprint": {
                "over_represented": t["issue_footprint"]["over"],
                "under_represented": t["issue_footprint"]["under"],
                "note": "rates are share of this ALJ's gold holdings vs the corpus share.",
            },
            "procedural_posture": t["procedural"],
            "authorities_leaned_on": t["authorities"],
            "persuasive_arguments": t["persuasive_args"],
            "editor_observations": t["editor_observations"],
            "gold_footprint_samples": gold_footprint_samples(rec=usable[s],
                                                             over_cats=t["issue_footprint"]["over"]),
        }
        (ddir / f"{s}.json").write_text(json.dumps(dossier, indent=1))
        index.append({
            "alj": s, "gold_cites": t["density"]["gold_cites"],
            "structured": t["density"]["structured_holdings"],
            "decided": t["density"]["decided_holdings"],
            "n_editor_obs": len(t["editor_observations"]),
            "fdr_significant": fdr_flag,
            "win_rate": o["win_rate"] if o else None,
        })
    index.sort(key=lambda r: -r["gold_cites"])
    (OUT / "dossiers_index.json").write_text(json.dumps(index, indent=1))
    print(f"wrote {len(index)} dossiers to {ddir}")
    print(f"  FDR-significant win-rate ALJs: "
          f"{[r['alj'] for r in index if r['fdr_significant']]}")
    print(f"  group discriminability (within-year p): win-rate={disc['winrate_group_p_within_year']}, "
          f"issue-mix={disc['issuemix_group_p_within_year']}")


if __name__ == "__main__":
    main()
