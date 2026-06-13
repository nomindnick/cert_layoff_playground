#!/usr/bin/env python3
"""Local-model spot synthesis — records whether a local LLM (not a Claude
subagent) can produce a grounded ALJ scouting report from a dossier. For the
FINDINGS backend note; the workflow fan-out validates the idea, this validates
local feasibility.

Usage: synth_local.py Sarli [--model gemma4:31b]
"""

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from corpuslib.llm import generate, gpu_status  # noqa: E402

from common import OUT  # noqa: E402
from cli import lbl  # noqa: E402

SYSTEM = (
    "You write ALJ scouting reports for California school-district attorneys "
    "preparing for certificated-employee layoff hearings (Education Code "
    "44949/44955). You write ONLY from the supplied dossier. Every tendency "
    "claim must trace to a dossier fact; never invent cites, numbers, or "
    "holdings. If the outcome note says a win-rate is not significant or the "
    "profile is gold-only, you must NOT assert an outcome tendency. Issue "
    "footprint is what the ALJ HEARS (docket draw), not how they rule. Never "
    "include a respondent name. A short, well-hedged report beats a confident "
    "one."
)


def dossier_text(d):
    a = d["alj"]
    L = [f"DOSSIER FOR ALJ {a}", f"Density: {json.dumps(d['density'])}"]
    L.append(f"Outcome interpretation (OBEY THIS): {d['outcome']['interpretation']}")
    L.append("Over-represented issues (docket share vs corpus): " + "; ".join(
        f"{lbl(r['category'])} {int(r['rate']*100)}% vs {int(r['corpus_rate']*100)}% ({r['count']} holdings)"
        for r in d["issue_footprint"]["over_represented"]) or "none")
    if d.get("persuasive_arguments"):
        L.append("Decided 2004/2009 holdings by issue:")
        for cat, v in d["persuasive_arguments"].items():
            L.append(f"  - {lbl(cat)}: respondent prevailed {v['respondent_wins']}/{v['decided']}")
            for ex in v["examples"]:
                wa = (ex.get("winning_argument") or [""])[0]
                if wa:
                    L.append(f"      {ex['won']} prevailed: {wa[:200]}")
    if d.get("authorities_leaned_on"):
        L.append("Authorities above corpus rate: " + "; ".join(
            f"{r['cite']} ({r['count']}x)" for r in d["authorities_leaned_on"]))
    L.append("Verbatim editor observations naming this ALJ (quote these, with cites):")
    for ob in d["editor_observations"][:8]:
        tag = f"{ob['district']} ({a}), {ob['year']}" if ob["district"] else f"{a}, {ob['year']}"
        L.append(f"  - \"{ob['text'].strip()}\" [{tag}]")
    return "\n".join(L)


PROMPT = """{dossier}

Write the scouting report in markdown with these sections:
## Bottom line
## Outcome tendency
## What this ALJ hears a lot of
## How arguments have landed
## In the editors' words
## Watch-outs & data caveats

Cite inline in "District ({alj})" form with the year, exactly as the dossier does.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("alj")
    ap.add_argument("--model", default="gemma4:31b")
    args = ap.parse_args()
    print("GPU:", gpu_status(), flush=True)
    d = json.loads((OUT / "dossiers" / f"{args.alj}.json").read_text())
    prompt = PROMPT.format(dossier=dossier_text(d), alj=args.alj)
    t0 = time.time()
    out = generate(f"ollama:{args.model}", prompt, system=SYSTEM,
                   options={"temperature": 0.3, "seed": 7, "num_predict": 1200})
    dt = time.time() - t0
    outdir = OUT / "reports_local"
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{args.alj}__{args.model.replace(':', '-')}.md"
    path.write_text(out)
    print(f"\n=== {args.alj} via {args.model} ({dt:.0f}s, {len(out)} chars) -> {path} ===\n")
    print(out)


if __name__ == "__main__":
    main()
