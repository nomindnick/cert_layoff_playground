#!/usr/bin/env python3
"""Render an ALJ dossier as a deterministic markdown scouting report.

This is the zero-LLM product form: every line traces to a dossier field, so it
is grounded by construction and safe to commit (District (ALJ) cites only).

Usage:
  cli.py Sarli                 # print report
  cli.py Sarli -o out.md       # write to file
  cli.py --list                # list available dossiers
"""

import argparse
import json

from common import OUT

CAT_LABEL = {  # canonical -> human
    "pks_allowed": "PKS / reduction allowed", "pks_not_allowed": "PKS not allowed",
    "pks_reduction": "PKS reduction", "procedural_issues": "procedural",
    "tie_breaking": "tie-breaking", "temporary_employees": "temporary employees",
    "categorically_funded": "categorically-funded positions",
}


def lbl(c):
    return CAT_LABEL.get(c, (c or "").replace("_", " "))


def render(d):
    L = []
    a = d["alj"]
    den = d["density"]
    span = den["years_span"]
    L.append(f"# ALJ scouting report — {a}")
    L.append("")
    L.append(f"*Evidence base: {den['gold_cites']} catalogued holdings "
             f"{span[0]}–{span[1]} across {den['n_districts']} districts and "
             f"{den['n_categories']} issue categories; "
             f"{den['structured_holdings']} structured holdings from 2004/2009 "
             f"({den['decided_holdings']} decided).*")
    L.append("")

    # outcome
    L.append("## Outcome tendency")
    o = d["outcome"]
    L.append(o["interpretation"])
    if o.get("n_decided"):
        L.append("")
        L.append(f"- Respondent-win rate **{o['win_rate']}** "
                 f"(95% CI {o['ci95'][0]}–{o['ci95'][1]}) vs corpus base "
                 f"{o['base_rate']}, on {o['n_decided']} decided 2004/2009 holdings.")
    L.append("")

    # issue footprint
    L.append("## Issue footprint — what this ALJ hears a lot of")
    L.append("*(share of this ALJ's catalogued holdings vs the corpus share; a "
             "docket signal, not a disposition tendency)*")
    L.append("")
    for r in d["issue_footprint"]["over_represented"]:
        L.append(f"- **{lbl(r['category'])}**: {int(r['rate']*100)}% vs "
                 f"{int(r['corpus_rate']*100)}% corpus ({r['count']} holdings)")
    if not d["issue_footprint"]["over_represented"]:
        L.append("- No category materially over its corpus share.")
    L.append("")

    # persuasive arguments / outcomes by issue
    pa = d["persuasive_arguments"]
    if pa:
        L.append("## By issue (2004/2009 decided holdings)")
        for cat, v in pa.items():
            L.append(f"- **{lbl(cat)}**: respondent prevailed "
                     f"{v['respondent_wins']}/{v['decided']}.")
            for ex in v["examples"]:
                wa = ex["winning_argument"]
                if wa and wa[0]:
                    L.append(f"    - {ex['won']} prevailed — {wa[0][:240]}")
        L.append("")

    # authorities
    if d["authorities_leaned_on"]:
        L.append("## Authorities leaned on (above corpus rate)")
        for r in d["authorities_leaned_on"]:
            L.append(f"- {r['cite']} — cited {r['count']}×")
        L.append("")

    # editor observations
    if d["editor_observations"]:
        L.append("## What the volume editors noted (verbatim, attributed)")
        for ob in d["editor_observations"][:8]:
            tag = f"{ob['district']} ({a}), {ob['year']}" if ob["district"] else f"{a}, {ob['year']}"
            L.append(f"- “{ob['text'].strip()}”  \n  — *{tag}*")
        L.append("")

    # caveats
    L.append("## Data caveats")
    for c in d["data_caveats"]:
        L.append(f"- {c}")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("alj", nargs="?")
    ap.add_argument("-o", "--out")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    ddir = OUT / "dossiers"
    if args.list or not args.alj:
        idx = json.loads((OUT / "dossiers_index.json").read_text())
        for r in idx:
            flag = " [FDR-sig win-rate]" if r["fdr_significant"] else ""
            print(f"  {r['alj']:16s} gold={r['gold_cites']:3d} "
                  f"decided={r['decided']:2d} editor_obs={r['n_editor_obs']}{flag}")
        return
    d = json.loads((ddir / f"{args.alj}.json").read_text())
    md = render(d)
    if args.out:
        open(args.out, "w").write(md)
        print(f"wrote {args.out}")
    else:
        print(md)


if __name__ == "__main__":
    main()
