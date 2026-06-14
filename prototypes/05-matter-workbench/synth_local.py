#!/usr/bin/env python3
"""Local-model synthesizer arm for the P1 bakeoff.

Reads a matter + its (deterministic) evidence pack and produces a PROSE risk memo
via ollama — the same task the Opus subagent does in memo_workflow.js, with the
same hard rules. Prose only (no forced JSON): we are grading legal reasoning and
grounding, not JSON formatting, and this sidesteps reasoning-model / gpt-oss
structured-output quirks. The Opus verifier self-extracts and checks claims.

  synth_local.py --model gemma4:31b --matter riverton-2026
  synth_local.py --model gemma4:31b --all

Memos -> output/memos_bakeoff/{safe_model}/{matter_id}.md  (+ a .meta.json with timing)
"""

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from corpuslib.llm import generate, gpu_status  # noqa: E402

OUT = HERE / "output"
ISSUE_LABEL = {
    "skipping": "Skipping (sec 44955(d)(1))", "bumping": "Bumping",
    "competency": "Competency", "seniority": "Seniority",
    "tie_breaking": "Tie-breaking", "procedural_issues": "Procedural",
    "pks_allowed": "PKS / reduction of services", "attrition": "Attrition",
}

# Many of these 2026 models are reasoning models in this ollama build (qwen3.5/
# 3.6, gpt-oss, gemma4). We give them ROOM TO REASON: thinking on (think=None ->
# model default), with a large context + generation budget so the hidden CoT does
# not starve the answer. If a model still returns ~nothing (CoT ate the budget),
# we retry with think=False. Grade the memo; the CoT is internal.
# (ollama OLLAMA_NUM_PARALLEL should be 1 for this run so one model gets the whole
# GPU + full context — a 4-slot reservation forces CPU offload on the 120b models.)
NUM_CTX = 24576       # holds prompt (~6k) + reasoning + a full memo, room to spare
NUM_PREDICT = 8000    # generous headroom for CoT + memo (gemma finished under 4k)


SYSTEM = (
    "You are a California school-district attorney's research associate writing an "
    "issue-by-issue RISK MEMO for a live certificated-employee layoff (Education "
    "Code 44949/44955). You write ONLY from the supplied evidence pack. Every "
    "assertion must cite a holding FROM THE PACK, inline as 'District (ALJ), year'. "
    "Never invent holdings, cites, or outcomes, and do not add outside knowledge of "
    "education law as if it were corpus-grounded. If an issue's evidence is thin, "
    "say so. If an assigned ALJ's tendency says the win-rate is not distinguishable "
    "from base, do NOT claim an outcome lean. Tie every 'what respondents will "
    "argue' to a real respondent argument in the pack. PRIVACY: cite District (ALJ) "
    "only; never output a person's name — if a snippet contains one, write 'a junior "
    "teacher' / 'the senior respondent'. Flag legal characterizations a human must "
    "check. A short, well-hedged memo beats a confident one."
)


def pack_text(pack):
    L = [f"MATTER: {pack['district']}"
         + (f"  (assigned ALJ: {pack['alj']})" if pack['alj'] else "  (ALJ unassigned)"),
         f"Basis: {pack.get('basis')}"]
    t = pack.get("alj_tendency")
    if t:
        L.append(f"ASSIGNED-ALJ TENDENCY (obey this): {t.get('outcome','')}")
        if t.get("relevant_footprint"):
            L.append("  docket footprint: " + "; ".join(
                f"{ISSUE_LABEL.get(k,k)} {int(v['rate']*100)}% vs {int(v['corpus_rate']*100)}% corpus"
                for k, v in t["relevant_footprint"].items()))
    L.append("\nEVIDENCE PACK (retrieved holdings per issue):")
    for iss in pack["issues"]:
        L.append(f"\n### ISSUE: {ISSUE_LABEL.get(iss['issue'], iss['issue'])}")
        for tr in iss["triggers"]:
            if not tr.startswith("("):
                L.append(f"  matter fact: {tr}")
        for h in iss["holdings"]:
            pp = h.get("prevailing_party") or "no recorded outcome"
            L.append(f"  - [{h['cite']}, {h['year']}, {pp}] {h['summary'][:300]}")
            ra = [a for a in (h.get("arguments") or []) if a["party"] == "respondent"]
            if ra:
                L.append(f"      respondent argued: {(ra[0]['summary'] or '')[:180]}")
            if h.get("reasoning"):
                L.append(f"      reasoning: {h['reasoning'][:180]}")
    return "\n".join(L)


PROMPT = """{pack}

Write the risk memo in markdown with these sections:
## Overall risk summary   (3-5 sentences: where is this district most exposed?)
## <one section per issue above>
   For each issue: **Exposure** for THIS matter; **What respondents will likely argue** (from the pack's respondent arguments, with cites); **How it has tended to land** (from the retrieved outcomes — honest counts, note thin records, exclude "no recorded outcome" holdings from win/loss tallies); **What to shore up**.
## What to verify   (legal characterizations and thin spots a human attorney must check)

Cite inline as "District (ALJ), year" exactly as the pack does. Do not invent anything.
"""


def synth(model, matter_id):
    pack = json.loads((OUT / "evidence" / f"{matter_id}.json").read_text())
    prompt = PROMPT.format(pack=pack_text(pack))
    safe = model.replace(":", "-").replace("/", "-").replace(".", "p")
    outdir = OUT / "memos_bakeoff" / safe
    outdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    err = None
    opts = {"temperature": 0.3, "seed": 7, "num_predict": NUM_PREDICT}
    # think=None first (let reasoning models reason); fall back to think=False only
    # if the CoT starved the answer (<500 chars) or the param errored.
    used_think = None
    for think in (None, False):
        used_think = think
        try:
            memo = generate(f"ollama:{model}", prompt, system=SYSTEM,
                            think=think, num_ctx=NUM_CTX, timeout=3600, options=opts)
            err = None
        except Exception as e:  # noqa: BLE001
            memo, err = "", f"{type(e).__name__}: {e}"
        if not err and len(memo.strip()) > 500:
            break  # got a real memo
    dt = round(time.time() - t0, 1)
    (outdir / f"{matter_id}.md").write_text(memo)
    (outdir / f"{matter_id}.meta.json").write_text(json.dumps(
        {"model": model, "matter": matter_id, "secs": dt, "chars": len(memo),
         "think": used_think, "error": err}, indent=1))
    print(f"  {model} / {matter_id}: {dt}s, {len(memo)} chars"
          + (f"  ERROR {err}" if err else ""), flush=True)
    return err is None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--matter")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    print("GPU:", gpu_status(), flush=True)
    matters = ([p.stem for p in sorted((OUT / "evidence").glob("*.json"))]
               if a.all else [a.matter])
    print(f"=== {a.model} over {len(matters)} matters ===", flush=True)
    for mid in matters:
        synth(a.model, mid)


if __name__ == "__main__":
    main()
