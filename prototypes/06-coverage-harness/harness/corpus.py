"""Schema-tolerant access to the merged 3-era corpus for prototype 06.

Wraps `corpuslib` so experiments never branch on `schema_version` themselves,
de-identifies every prose field at read time (via `harness.deid`), normalizes the
one category that drifted (PKS), and derives era/year robustly from the case
number (production `decision_date` is null on many records).

Point it at the merged corpus:  export CORPUS_ROOT=/home/nick/Projects/cert_layoff_merged
(build it with ../setup_merged_corpus.sh).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from corpuslib import load_decisions, load_gold_holdings, corpus_paths  # noqa: E402
from corpuslib.deident import district_short, alj_surname  # noqa: E402

from .deid import deid  # noqa: E402

# ---- category normalization -------------------------------------------------
# Only drift across gold / 0.2.0 / 0.4.0 (audited 2026-06-17): gold splits PKS
# into allowed/not_allowed; every decision schema uses pks_reduction. Collapse
# all three to one canonical issue (the allowed/not-allowed distinction is a
# holding OUTCOME, not a distinct ISSUE — irrelevant for issue-spotting).
_CANON = {"pks_allowed": "pks_reduction", "pks_not_allowed": "pks_reduction"}


def norm_cat(c):
    return _CANON.get(c, c) if c else c


# ---- era / year -------------------------------------------------------------

def case_year(case_no):
    """Year from the OAH case number (e.g. 'N-1999020316' -> 1999). The temporal
    key; `decision_date` is null on ~1/5 of production records."""
    m = re.search(r"(\d{4})", case_no or "")
    return int(m.group(1)) if m else None


def era(year):
    if year is None:
        return "unknown"
    if year <= 2001:
        return "1999-2001"          # production, early
    if year <= 2010:
        return "2004-2009"          # spike
    return "2018-2025"              # production, recent


# ---- holdings (de-identified, schema-tolerant) ------------------------------

def holding_view(case_no, dec, i, h):
    """One de-identified, normalized holding record. Stable id 'case_no:idx'."""
    ident = dec.get("identity") or {}
    issue = h.get("issue") or {}
    ruling = h.get("ruling") or {}
    reasoning = h.get("reasoning") or {}
    yr = case_year(case_no)

    def d(t):
        return deid(t, dec)

    return {
        "hid": f"{case_no}:{i}",
        "case_no": case_no,
        "year": yr,
        "era": era(yr),
        "district": district_short((ident.get("district") or {}).get("raw") or ""),
        "alj": alj_surname((ident.get("alj") or {}).get("raw") or ""),
        "category": norm_cat(issue.get("category")),
        "category_raw": issue.get("category"),
        "subtype": issue.get("subtype"),
        "prevailing_party": ruling.get("prevailing_party"),
        "issue_statement": d(issue.get("statement")),
        "summary": d(h.get("summary_style_holding")),
        "reasoning": d(reasoning.get("summary")),
        "facts": [d(f.get("summary")) for f in (h.get("facts") or []) if f.get("summary")],
        "arguments": [{"party": a.get("party"), "summary": d(a.get("summary"))}
                      for a in (h.get("arguments") or []) if a.get("summary")],
        "authorities": [a.get("raw_cite") for a in (h.get("authorities") or [])
                        if a.get("raw_cite")],
        "notable": bool((h.get("notable") or {}).get("flag")),
    }


def holdings(year=None):
    """Yield de-identified holding views across the merged corpus."""
    for case_no, dec in load_decisions(year=year):
        for i, h in enumerate(dec.get("holdings") or []):
            yield holding_view(case_no, dec, i, h)


def decisions(year=None):
    """Yield (case_no, raw decision record). RAW — caller must de-identify any
    prose it surfaces (use holding_view / harness.deid.deid)."""
    yield from load_decisions(year=year)


def decision_issue_set(dec):
    """Normalized set of issue categories a decision adjudicated — the breadth
    answer key for a held-out decision."""
    return {norm_cat((h.get("issue") or {}).get("category"))
            for h in (dec.get("holdings") or [])
            if (h.get("issue") or {}).get("category")}


def related_case_nos(dec):
    """Case numbers of related proceedings (0.4.0) — to widen the eval-time
    exclusion set beyond the decision itself (quasi-self-retrieval)."""
    out = set()
    for r in (dec.get("related_proceedings") or []):
        cn = r.get("oah_case_no") or r.get("case_no") if isinstance(r, dict) else r
        if cn:
            out.add(re.sub(r"[^0-9]", "", str(cn)))
    return out


# ---- corpus census (runtime — counts drift as the build runs) ---------------

def census():
    n_dec = n_hold = 0
    eras = {}
    cats = {}
    for case_no, dec in load_decisions():
        n_dec += 1
        e = era(case_year(case_no))
        eras[e] = eras.get(e, 0) + 1
        for h in dec.get("holdings") or []:
            n_hold += 1
            c = norm_cat((h.get("issue") or {}).get("category"))
            if c:
                cats[c] = cats.get(c, 0) + 1
    gold = sum(1 for _ in load_gold_holdings())
    return {"root": str(corpus_paths()["root"]), "decisions": n_dec,
            "holdings": n_hold, "gold_holdings": gold,
            "by_era": eras, "by_category": cats}
