#!/usr/bin/env python3
"""Render a matter's evidence pack as a deterministic per-issue digest (zero LLM,
grounded by construction), or print the LLM-generated risk memo.

  cli.py <matter_id>            # deterministic evidence digest
  cli.py <matter_id> --memo     # the synthesized risk memo (output/memos/)
  cli.py --list
"""

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"

ISSUE_LABEL = {
    "skipping": "Skipping (§44955(d)(1))", "bumping": "Bumping",
    "competency": "Competency", "seniority": "Seniority",
    "tie_breaking": "Tie-breaking", "procedural_issues": "Procedural",
    "pks_allowed": "PKS / reduction of services", "attrition": "Attrition",
}


def digest(pack):
    L = [f"# Evidence digest — {pack['district']}"
         + (f" (before ALJ {pack['alj']})" if pack['alj'] else " (ALJ unassigned)")]
    L.append(f"\n*Deterministic retrieval over the corpus — {sum(i['n_holdings'] for i in pack['issues'])} "
             f"holdings across {len(pack['issues'])} issues. Zero LLM; every line is a retrieved holding.*\n")
    t = pack.get("alj_tendency")
    if t:
        L.append(f"**Assigned-ALJ tendencies ({pack['alj']}):** {t.get('outcome','')}")
        if t.get("relevant_footprint"):
            fp = "; ".join(f"{ISSUE_LABEL.get(k,k)} {int(v['rate']*100)}% vs {int(v['corpus_rate']*100)}% corpus"
                           for k, v in t["relevant_footprint"].items())
            L.append(f"  Relevant docket footprint: {fp}\n")
    for iss in pack["issues"]:
        L.append(f"## {ISSUE_LABEL.get(iss['issue'], iss['issue'])}  ({iss['n_holdings']} holdings)")
        for tr in iss["triggers"]:
            if not tr.startswith("("):
                L.append(f"- *trigger:* {tr}")
        L.append("")
        for h in iss["holdings"]:
            pp = h.get("prevailing_party")
            tag = f"{h['year']}" + (f", {pp}" if pp else "") + f", {h['source']}"
            L.append(f"**{h['cite']}** ({tag}) — {h['summary'][:280]}")
            ra = [a for a in (h.get("arguments") or []) if a["party"] == "respondent"]
            if ra:
                L.append(f"  · respondent argued: {(ra[0]['summary'] or '')[:200]}")
            if h.get("reasoning"):
                L.append(f"  · reasoning: {h['reasoning'][:200]}")
            L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("matter", nargs="?")
    ap.add_argument("--memo", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list or not a.matter:
        for p in sorted((OUT / "evidence").glob("*.json")):
            d = json.loads(p.read_text())
            print(f"  {d['matter_id']:18s} district={d['district']:22s} alj={d['alj']} "
                  f"issues={len(d['issues'])}")
        return
    if a.memo:
        m = OUT / "memos" / f"{a.matter}.md"
        print(m.read_text() if m.exists() else f"(no memo yet at {m})")
        return
    pack = json.loads((OUT / "evidence" / f"{a.matter}.json").read_text())
    print(digest(pack))


if __name__ == "__main__":
    main()
