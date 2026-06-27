"""E0 metrics: breadth (issue-spotting), depth proxy, grounding, cost.

Arm-agnostic. An *arm* returns, per matter:
  {spotted_issues:[{category, confidence}|category],
   per_issue:[{issue, analysis, cited_holding_ids}],
   _cost:{wall_clock_s, n_calls, tokens}}

Breadth is rarity-weighted (spotting `domino_theory` is worth more than the
ubiquitous `procedural_issues`) and reports precision separately so an arm that
shouts every common issue doesn't win. The depth PROXY here is a cheap
content-word overlap; the trustworthy depth score is the Opus-subagent rubric
judge, wired when real arms run (kept separate so the judge can be calibrated
against this proxy + a human set).
"""

import math
import re

from .corpus import census, norm_cat

# ---- category rarity weights (computed once from the live corpus) -----------
_W = None


def _weights():
    global _W
    if _W is None:
        cats = census()["by_category"]
        tot = sum(cats.values()) or 1
        raw = {k: -math.log(v / tot) for k, v in cats.items() if v}
        mean = (sum(raw.values()) / len(raw)) if raw else 1.0
        _W = {k: v / mean for k, v in raw.items()}   # normalize so mean≈1
    return _W


def rarity_weight(cat):
    return _weights().get(cat, 1.0)


def _cats(spotted):
    out = []
    for s in spotted or []:
        c = s.get("category") if isinstance(s, dict) else s
        if c:
            out.append(norm_cat(c))
    return set(out)


# ---- breadth ----------------------------------------------------------------

def breadth_score(spotted, key_issues):
    spotted, key = _cats(spotted), {norm_cat(c) for c in key_issues}
    tp, fp, fn = spotted & key, spotted - key, key - spotted
    recall = len(tp) / len(key) if key else 0.0
    precision = len(tp) / len(spotted) if spotted else 0.0
    wden = sum(rarity_weight(c) for c in key)
    wrecall = (sum(rarity_weight(c) for c in tp) / wden) if wden else 0.0
    return {"recall": round(recall, 3), "precision": round(precision, 3),
            "rarity_recall": round(wrecall, 3),
            "tp": sorted(tp), "fp_candidates": sorted(fp), "fn": sorted(fn)}


# ---- depth proxy (deterministic; LLM judge replaces/augments later) ---------
_WORD = re.compile(r"[a-zà-ÿ]{4,}")
_STOP = {"that", "this", "with", "from", "were", "have", "been", "such", "which",
         "their", "would", "could", "there", "respondent", "respondents",
         "district", "because", "where", "when", "shall", "must", "than",
         "they", "them", "into", "more", "less", "year", "years", "alj",
         "section", "education", "code", "board", "school", "teacher", "teachers"}


def _content(t):
    return {w for w in _WORD.findall((t or "").lower()) if w not in _STOP}


def depth_proxy(analysis, key_entry):
    """Recall of the held-out reasoning/operative-fact content words in the arm's
    analysis. Crude proxy for 'did it recover the operative distinction'."""
    k = _content(key_entry.get("reasoning", "") + " "
                 + " ".join(key_entry.get("operative_facts", [])))
    if not k:
        return None
    return round(len(_content(analysis) & k) / len(k), 3)


# ---- grounding (cite-resolution instrument) ---------------------------------

def grounding_score(cited_ids, valid_ids):
    cited = [c for c in (cited_ids or [])]
    if not cited:
        return {"rate": None, "n_cited": 0, "n_unresolved": 0, "unresolved": []}
    bad = [c for c in cited if c not in valid_ids]
    return {"rate": round(1 - len(bad) / len(cited), 3), "n_cited": len(cited),
            "n_unresolved": len(bad), "unresolved": bad[:10]}


# ---- per-matter rollup ------------------------------------------------------

def score_matter(arm_out, matter, valid_ids):
    b = breadth_score(arm_out.get("spotted_issues"), matter["answer_key"]["issues"])
    key_by_issue = {}
    for e in matter["answer_key"]["depth"]:
        key_by_issue.setdefault(e["issue"], e)   # one key entry per issue (first)
    depth = []
    cited = []
    for pi in arm_out.get("per_issue") or []:
        iss = norm_cat(pi.get("issue"))
        cited += pi.get("cited_holding_ids") or []
        if iss in key_by_issue and iss in set(b["tp"]):
            p = depth_proxy(pi.get("analysis", ""), key_by_issue[iss])
            if p is not None:
                depth.append({"issue": iss, "proxy": p})
    g = grounding_score(cited, valid_ids)
    return {"matter": matter["matter_id"], "era": matter["era"],
            "leak_rate": matter["diagnostics"]["leak_rate"],
            "breadth": b, "depth": depth, "grounding": g,
            "cost": arm_out.get("_cost") or {}}
