"""Matter-from-held-out-decision generator (E0).

Turn a real decision D into a *facts-only matter* + answer keys, so an arm can be
graded on whether it re-spots the issues D actually litigated (breadth) and
recovers the ALJ's operative reasoning (depth) — see ../scoreboard/SPEC.md.

The matter is built ONLY from de-identified `facts[].summary` (the factual record),
never from `issue.statement`/`reasoning`/`ruling` (which name the issues and
outcomes). That is the defense against circularity; `diagnostics` MEASURES the
residual leakage (issue-telegraphing vocabulary still present in the facts) and a
rough recoverability ceiling, so a human can judge whether deterministic assembly
is clean enough or an LLM neutralizing rewrite is needed.

This is v1 (deterministic). Decision point it surfaces: keep as-is / add a
leak-scrub / switch to an LLM rewrite — to be made on the sample output, not in
the abstract.
"""

import re

from .corpus import (
    case_year, era, norm_cat, decision_issue_set, related_case_nos,
)
from corpuslib.deident import district_short
from .deid import deid, residual_name_candidates

# Strong issue-telegraphing terms — if these appear in the facts, the matter is
# leaking the legal conclusion (an arm could keyword-match instead of reason).
# Deliberately the CONCLUSORY verbs/labels, not fact-adjacent words like
# "seniority"/"first hire date"/"credential" (those are genuinely facts).
_ISSUE_TERMS = {
    "skipping": [r"\bskip(?:p?ed|ping|s)?\b", r"deviat\w+ from seniority"],
    "bumping": [r"\bbump(?:ed|ing|s)?\b"],
    "tie_breaking": [r"tie[- ]?break\w*", r"break\w*\s+the\s+tie", r"tie[d]?\s+seniority"],
    "competency": [r"\bcompeten\w+\b"],
    "pks_reduction": [r"particular kinds? of services", r"\bPKS\b",
                      r"reduction (?:in|of) (?:particular )?services"],
    "domino_theory": [r"\bdomino\b"],
    "attrition": [r"\battrition\b", r"positively assured"],
    "reemployment_rights": [r"reemploy\w*", r"reappoint\w*", r"39[- ]month"],
    "categorically_funded": [r"categorical\w*"],
    "credentials": [r"\bcredential\w*\b"],
}


def _facts_blob(dec):
    """De-identified, de-duplicated facts across all holdings, in order."""
    seen, out = set(), []
    for h in dec.get("holdings") or []:
        for f in h.get("facts") or []:
            s = (f.get("summary") or "").strip()
            if not s:
                continue
            key = re.sub(r"\s+", " ", s.lower())
            if key in seen:
                continue
            seen.add(key)
            out.append(deid(s, dec))
    return out


def make_matter(case_no, dec):
    """Build the matter record for one held-out decision."""
    ident = dec.get("identity") or {}
    district = district_short((ident.get("district") or {}).get("raw") or "")
    facts = _facts_blob(dec)
    matter_text = (
        f"District: {district}.\n"
        f"The following facts are established about a certificated-employee layoff:\n"
        + "\n".join(f"- {f}" for f in facts)
    )

    issues = decision_issue_set(dec)
    # depth key: per holding, the operative facts + the ALJ's reasoning
    depth = []
    for i, h in enumerate(dec.get("holdings") or []):
        cat = norm_cat((h.get("issue") or {}).get("category"))
        reasoning = deid((h.get("reasoning") or {}).get("summary") or "", dec)
        opfacts = [deid(f.get("summary") or "", dec) for f in (h.get("facts") or [])
                   if f.get("summary")]
        if cat and (reasoning or opfacts):
            depth.append({"issue": cat, "hid": f"{case_no}:{i}",
                          "reasoning": reasoning, "operative_facts": opfacts})

    # --- diagnostics ---
    blob = matter_text.lower()
    leak = {}
    for cat, pats in _ISSUE_TERMS.items():
        hits = sorted({m.group(0) for p in pats for m in re.finditer(p, blob)})
        if hits:
            leak[cat] = hits
    # rough recoverability ceiling: an issue is *plausibly* recoverable if the
    # matter facts even mention its telegraphing terms (proxy — the real ceiling
    # is the human/LLM "could you spot it?" judgment on these samples).
    recoverable = {c for c in issues if c in leak}

    return {
        "matter_id": case_no,
        "source_decision": case_no,
        "era": era(case_year(case_no)),
        "district": district,
        "n_facts": len(facts),
        "matter_text": matter_text,
        "answer_key": {"issues": sorted(issues), "depth": depth},
        "exclude_ids": sorted({re.sub(r"[^0-9]", "", case_no)} | related_case_nos(dec)),
        "diagnostics": {
            "issue_terms_present": leak,
            "issues_total": len(issues),
            "issues_with_leaked_term": sorted(recoverable),
            "leak_rate": round(len(recoverable) / len(issues), 2) if issues else 0.0,
            "residual_name_candidates": residual_name_candidates(matter_text)[:15],
        },
    }


def eligible(dec, min_issues=2, min_facts=4):
    """A decision makes a good eval matter if it litigated >=2 distinct issues
    and carries enough facts to reconstruct a fact pattern."""
    issues = decision_issue_set(dec)
    nfacts = sum(1 for h in (dec.get("holdings") or []) for f in (h.get("facts") or [])
                 if f.get("summary"))
    return len(issues) >= min_issues and nfacts >= min_facts
