#!/usr/bin/env python3
"""Prep for the CITE-FAITHFULNESS metric (the mandatory rail for richer artifacts).

Grounding tells us a cite RESOLVES to a real holding (identity). Faithfulness asks the
harder question: does the analysis's USE of that cite actually represent what the holding
held -- or mischaracterize/overstate/INVERT it (cite a district-win holding to support a
respondent conclusion; attribute a proposition the holding never contained)? RAG worsened
authority-confab (150->204); identity-grounding is blind to it. The richer the artifact
(rule+comment, treatise, advocacy), the more a confabulation gets LAUNDERED into
authoritative prose -- so this rail rides alongside R3/R4/SYS.

For each analysis we parse+resolve corpus cites (reuse grounding.parse_cites/resolve) and
emit one BLINDED judge item per (analysis, resolved cite): the full analysis + the cite
string + the REAL holding content (de-identified) it resolves to. UNRESOLVED cites are a
GROUNDING miss (already scored there), not a faithfulness item.

  CORPUS_ROOT=... cite_faithfulness_prep.py --tag gemma4-31b.think [--tag ...] --name <name>
-> output/runs/faith.<name>.input.json  ({code, cite, analysis, candidates:[{...holding}]})
   output/runs/faith.<name>.meta.json   ({code: {tag, matter_issue, arm, hids, cite}})
"""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
RUNS = HERE / "output" / "runs"
sys.path.insert(0, str(PROTO))
sys.path.insert(0, str(PROTO / "scoreboard"))

from grounding import parse_cites, resolve            # noqa: E402
from harness.corpus import holdings                   # noqa: E402

MAX_CAND = 3   # an (alj, year) cite can be ambiguous; show up to this many candidates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", action="append", required=True)
    ap.add_argument("--name", required=True)
    a = ap.parse_args()
    H = {h["hid"]: h for h in holdings()}

    rows = []
    for tag in a.tag:
        inpf = RUNS / f"depth.{tag}.input.json"
        if not inpf.exists():
            print(f"  (skip missing {tag}: {inpf.name})")
            continue
        for it in json.loads(inpf.read_text()):
            iid = it["item_id"]
            parts = iid.split(":")
            mi, arm = ":".join(parts[:2]), parts[-1]
            analysis = it["analysis"]
            seen = set()
            for c in parse_cites(analysis):
                dedup = (c[1].lower(), c[2])
                if dedup in seen:
                    continue
                seen.add(dedup)
                hids = sorted(resolve(c))
                if not hids:                       # unresolved => grounding miss, not faithfulness
                    continue
                cite_str = f"{c[0] or '?'} ({c[1]}), {c[2]}"
                h = hashlib.sha1(f"{tag}|{iid}|{cite_str}".encode()).hexdigest()
                rows.append((h, tag, mi, arm, cite_str, hids[:MAX_CAND], analysis))
    rows.sort(key=lambda r: r[0])

    blind, meta = [], {}
    for n, (_, tag, mi, arm, cite_str, hids, analysis) in enumerate(rows, 1):
        code = f"F{n:04d}"
        cand = []
        for hid in hids:
            h = H.get(hid)
            if not h:
                continue
            cand.append({"category": h["category"], "issue": h["issue_statement"],
                         "prevailing_party": h["prevailing_party"],
                         "holding": h["summary"], "reasoning": h["reasoning"]})
        blind.append({"code": code, "cite": cite_str, "analysis": analysis, "candidates": cand})
        meta[code] = {"tag": tag, "matter_issue": mi, "arm": arm, "hids": hids, "cite": cite_str}

    RUNS.mkdir(parents=True, exist_ok=True)
    (RUNS / f"faith.{a.name}.input.json").write_text(json.dumps(blind, indent=1, ensure_ascii=False))
    (RUNS / f"faith.{a.name}.meta.json").write_text(json.dumps(meta, indent=1))
    print(f"{len(blind)} resolved-cite items -> faith.{a.name}.input.json  (tags {a.tag})")
    print("per-arm cite items:", dict(Counter(m["arm"] for m in meta.values())))
    print("codes:", json.dumps([b["code"] for b in blind]))


if __name__ == "__main__":
    main()
