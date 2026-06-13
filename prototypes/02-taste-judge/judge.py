#!/usr/bin/env python3
"""Stage 2: LLM editorial judge. One JSON per (candidate, arm) under
output/judgments/{year}/{arm}/{id}.json — resumable (skips existing).

Arms:
  A  holding alone
  B  + top-5 prior-volume neighbors (settled-law context)
  C  + top-5 same-year candidate neighbors (duplication context)

Usage:
  judge.py --year 2009 --arm A [--model gemma4:31b] [--limit 50] [--workers 3]
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from corpuslib.llm import generate  # noqa: E402

from common import OUT  # noqa: E402

REASONS = ["novel_issue", "unusual_facts", "respondent_win",
           "recurring_guidance", "clarifies_standard", "routine_settled_law",
           "duplicative", "administrative", "fact_bound"]

SCHEMA = {
    "type": "object",
    "properties": {
        "include": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reasons": {"type": "array", "maxItems": 3,
                    "items": {"type": "string", "enum": REASONS}},
        "rationale": {"type": "string"},
    },
    "required": ["include", "confidence", "reasons", "rationale"],
}

SYSTEM = (
    "You are the editor of an annual volume cataloguing California "
    "teacher-layoff (Education Code sections 44949/44955) administrative "
    "decisions, organized by issue area, used by school-district attorneys as "
    "a practice reference. The volume is a working CATALOG, not a digest of "
    "novelties: editors include any holding that makes a useful catalog entry "
    "for its issue section — novel or unsettled points, respondent (teacher) "
    "wins, clarifications of a standard, unusual fact patterns, AND routine "
    "confirmations of settled rules when they offer concrete guidance on a "
    "recurring dispute (how criteria were applied, what evidence sufficed). "
    "Editors omit: administrative or uncontested dispositions, holdings that "
    "merely duplicate a point another decision states better, boilerplate "
    "recitations, and rulings so fact-bound they guide nothing. Volumes "
    "typically catalogue roughly a third to half of the year's extractable "
    "holdings. Respond with: include (your decision), confidence (0.0-1.0, "
    "how sure you are of THAT decision), up to 3 reasons, and a rationale of "
    "ONE sentence, at most 25 words."
)


def prompt_for(c, arm):
    lines = ["HOLDING UNDER REVIEW",
             f"Issue category: {c['category']}" +
             (f" ({c['subtype']})" if c.get("subtype") else ""),
             f"Prevailing party: {c['prevailing_party']}",
             f"Issue: {c['issue_statement']}",
             f"Holding: {c['summary'] or c['text']}"]
    if c.get("reasoning"):
        lines.append(f"Reasoning: {c['reasoning']}")
    if c.get("authorities"):
        cites = "; ".join(a["cite"] for a in c["authorities"] if a.get("cite"))
        lines.append(f"Authorities cited: {cites}")
    if c.get("arguments"):
        for a in c["arguments"][:4]:
            lines.append(f"Argument ({a['party']}): {a['summary']}")
    if arm == "B":
        lines.append("\nFOR CONTEXT — what PAST years' volumes catalogued on "
                     "the most similar issues (older context may be settled "
                     "law by now):")
        for n in c["prior_neighbors"]:
            lines.append(f"- ({n['year']}, similarity {n['sim']}) {n['text']}")
    if arm == "C":
        lines.append("\nFOR CONTEXT — the most similar OTHER candidate "
                     "holdings from THIS year's decisions (a duplicate of a "
                     "point better stated elsewhere is a reason to omit):")
        for n in c["same_year_neighbors"]:
            lines.append(f"- (similarity {n['sim']}) {n['text']}")
    lines.append("\nWould you include this holding in the annual volume?")
    return "\n".join(lines)


def judge_one(c, arm, model, outdir):
    path = outdir / f"{c['id'].replace(':', '_')}.json"
    if path.exists():
        return "skip"
    t0 = time.time()
    res = None
    # temp 0 sends grammar-constrained gemma into repetition loops (sanity
    # gate: degenerate rationales, timeouts, unterminated JSON). 0.2 + a
    # token cap + one hotter retry clears it.
    # reasoning models (qwen3.5:*) must run think=False or they spend the whole
    # budget thinking and return empty (Lesson: corpuslib/llm.py).
    think = False if "qwen3" in model else None
    for temp in (0.2, 0.6):
        try:
            res = generate(f"ollama:{model}", prompt_for(c, arm), system=SYSTEM,
                           json_schema=SCHEMA, timeout=300, think=think,
                           options={"temperature": temp, "seed": 7,
                                    "num_predict": 600})
            break
        except Exception as e:  # noqa: BLE001 — record failure, try hotter
            err = f"{type(e).__name__}: {e}"
    if res is None:
        path.with_suffix(".err").write_text(err)
        return "err"
    # robust score regardless of how the model reads "confidence"
    conf = min(max(float(res.get("confidence", 0.5)), 0.0), 1.0)
    res["score"] = round(conf if res.get("include") else 1.0 - conf, 3)
    res["_id"] = c["id"]
    res["_arm"] = arm
    res["_model"] = model
    res["_secs"] = round(time.time() - t0, 1)
    path.write_text(json.dumps(res, indent=1))
    return "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--arm", required=True, choices=["A", "B", "C"])
    ap.add_argument("--model", default="gemma4:31b")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sample", type=int, default=0,
                    help="stratified-by-label random sample (seeded) — for "
                         "the 122b scale comparison")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    cands = json.loads((OUT / f"features_{args.year}.json").read_text())
    if args.sample:
        import random
        rng = random.Random(7)
        pos = [c for c in cands if c["label"] == 1]
        neg = [c for c in cands if c["label"] == 0]
        cands = (rng.sample(pos, args.sample // 2)
                 + rng.sample(neg, args.sample - args.sample // 2))
    elif args.limit:
        cands = cands[:args.limit]
    safe_model = args.model.replace(":", "-").replace("/", "-")
    outdir = OUT / "judgments" / str(args.year) / f"{args.arm}__{safe_model}"
    outdir.mkdir(parents=True, exist_ok=True)

    done = 0
    t0 = time.time()
    with ThreadPoolExecutor(args.workers) as ex:
        for status in ex.map(lambda c: judge_one(c, args.arm, args.model, outdir), cands):
            done += 1
            if done % 25 == 0:
                rate = done / (time.time() - t0)
                print(f"{done}/{len(cands)} ({status}) {rate:.2f}/s", flush=True)
    n_ok = len(list(outdir.glob("*.json")))
    n_err = len(list(outdir.glob("*.err")))
    print(f"DONE arm={args.arm} year={args.year} model={args.model}: "
          f"{n_ok} judgments, {n_err} errors -> {outdir}")


if __name__ == "__main__":
    main()
