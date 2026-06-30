#!/usr/bin/env python3
"""Difficulty-suite candidate pool + cheap (model-free) difficulty signals.

Direction-focused suite: we GIVE the model the issue and grade its outcome call vs
the real prevailing_party. So the breadth-era leakage filters (zero-leak issue-
telegraphing + recoverability cap) DO NOT apply here — the only leakage protections
that matter are already built in: the matter is assembled from de-identified
facts[].summary ONLY (never ruling/reasoning → no outcome leak), and exclude_ids
blocks self-retrieval. That unlocks ~the whole corpus as candidates.

For every gradeable matter-issue (a holding with prevailing_party in
{district,respondent}) attach the cheap difficulty signals:
  - per-issue base rate (predictability prior; near 0/100% = easy, mid = harder)
  - editorial inclusion (eval/alignment_*.json: did the human editors catalogue it?)
  - structural proxies (reasoning length, #authorities, #arguments = contested-ness)
Persist the pool + report distributions so we can design the stratification.

  CORPUS_ROOT=/home/nick/Projects/cert_layoff_merged build_candidate_pool.py
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
sys.path.insert(0, str(PROTO))

from harness.corpus import decisions, holdings              # noqa: E402
from harness.matters import make_matter, eligible           # noqa: E402

ALIGN_DIR = Path("/home/nick/Projects/cert_layoff_corpus/output/eval")
OUT = HERE / "output"


def inclusion_map():
    """hid -> True (editor-included / matched to a gold holding) / False (extracted
    but not catalogued). Only covers gold-overlap years."""
    m = {}
    for f in sorted(ALIGN_DIR.glob("alignment_*.json")):
        d = json.loads(f.read_text())
        for s in d.get("system", []):
            m[f"{s['case_no']}:{s['holding_idx']}"] = bool(s.get("matched_gold_idxs"))
    return m


def _lab(c):
    return "incl" if c["included"] else ("not" if c["included"] is False else "unknown")


def main():
    incl = inclusion_map()
    print(f"editorial-inclusion labels: {len(incl)} holdings ({sum(incl.values())} included)")

    byiss = defaultdict(Counter)
    hview = {}
    for h in holdings():
        hview[h["hid"]] = h
        if h.get("prevailing_party") in ("district", "respondent"):
            byiss[h["category"]][h["prevailing_party"]] += 1
    base_rate = {iss: (ctr["respondent"] / (ctr["district"] + ctr["respondent"]))
                 for iss, ctr in byiss.items() if (ctr["district"] + ctr["respondent"])}

    cands, n_elig = [], 0
    for cn, dec in decisions():
        if not eligible(dec):
            continue
        n_elig += 1
        m = make_matter(cn, dec)
        for d in m["answer_key"]["depth"]:
            hid, h = d["hid"], hview.get(d["hid"])
            if not h or h.get("prevailing_party") not in ("district", "respondent"):
                continue
            cands.append({
                "hid": hid, "matter_id": cn, "issue": d["issue"], "era": m["era"],
                "alj": h.get("alj"), "truth": h["prevailing_party"],
                "base_rate_resp": round(base_rate.get(d["issue"], 0.0), 2),
                "included": incl.get(hid),
                "reason_words": len((h.get("reasoning") or "").split()),
                "n_auth": len(h.get("authorities") or []),
                "n_args": len(h.get("arguments") or []),
            })

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "candidate_pool.json").write_text(json.dumps(cands, indent=1))

    n = len(cands)
    print(f"\neligible decisions: {n_elig} | gradeable candidate matter-issues: {n}")
    print("by era:", dict(Counter(c["era"] for c in cands)))
    rs = sum(c["truth"] == "respondent" for c in cands)
    print(f"truth: district {n - rs} / respondent {rs}  (resp share {round(rs / n * 100)}%)")
    print("editorial inclusion:", dict(Counter(_lab(c) for c in cands)))
    print("  inclusion vs outcome (does 'included' skew toward respondent-wins = harder?):")
    for lab in ("incl", "not", "unknown"):
        sub = [c for c in cands if _lab(c) == lab]
        if sub:
            print(f"    {lab:<8} n={len(sub):<5} resp%={round(sum(c['truth']=='respondent' for c in sub)/len(sub)*100)}")
    print("distinct ALJs in pool:", len(set(c["alj"] for c in cands if c["alj"])))
    print("reason_words quartiles (contested-ness proxy):",
          sorted(c["reason_words"] for c in cands)[::max(1, n // 4)][:5])
    print(f"-> {OUT / 'candidate_pool.json'}")


if __name__ == "__main__":
    main()
