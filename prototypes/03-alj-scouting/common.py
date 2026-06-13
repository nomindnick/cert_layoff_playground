"""Per-ALJ evidence assembly for the scouting reports.

Joins two sources on **ALJ surname** (the only key the gold cites carry):
  - gold holdings (1979-2015): the 35-year issue footprint + the editors' own
    ALJ-attributed prose observations. Already de-identified by volume convention.
  - structured holdings (2004/2009 decisions): per-holding prevailing_party,
    arguments-by-party, authorities. De-identified here, at assembly time.

Surname conflation is real (Johnson = Perry O. + Vallera J.). We detect it from
the decision records' raw full names and mark the surname `ambiguous` so the
caller can sequester it. Gold-only surnames can't be disambiguated; that caveat
rides on every report.
"""

import collections
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from corpuslib import load_decisions, load_gold_holdings  # noqa: E402
from corpuslib.deident import alj_surname, deidentify, district_short  # noqa: E402

OUT = HERE / "output"

# decided = a holding where one side actually prevailed (excludes none_ruled/mixed)
DECIDED = ("district", "respondent")
# editor prose that explicitly narrates adjudicative conduct (the 535-set):
# these gold holdings are the editors' own ALJ observations, not just footprint.
CONDUCT_RE = re.compile(r"\b(ALJ|Judge|hearing officer)\b", re.I)


def _d(text, rec):
    out, _ = deidentify(text or "", rec)
    return out


def _fold(s):
    """Accent- and case-fold a name for identity comparison."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def _gold_real():
    return [g for g in load_gold_holdings() if g.get("category_raw")]


def assemble():
    """Return {surname: alj_record}. Each alj_record:
        surname, raw_names (set), ambiguous (bool),
        gold:        [ {year, categories, district, text, conduct_obs} ]
        structured:  [ {case_no, idx, year, category, subtype, prevailing_party,
                        district, issue_statement, summary, reasoning,
                        arguments:[{party,summary}], authorities:[{cite,type,role}]} ]
        density:     {gold_cites, structured_holdings, decided_holdings,
                      years_span:[lo,hi], n_years, n_categories, n_districts,
                      conduct_obs}
    """
    aljs = collections.defaultdict(lambda: {
        "surname": None, "raw_names": set(), "gold": [], "structured": [],
    })

    # ---- gold footprint + attributed prose ----
    for g in _gold_real():
        text = (g.get("text") or "").strip()
        cats = g.get("category_canonical") or []
        year = g.get("sort_year")
        conduct = bool(CONDUCT_RE.search(text))
        cited = [(c.get("alj") or "").strip() for c in (g.get("cites") or [])]
        cited = [a for a in cited if a]
        n_aljs = len(set(cited))
        seen = set()  # one footprint row per ALJ per holding (a holding may cite an ALJ twice)
        for sn in cited:
            if sn in seen:
                continue
            seen.add(sn)
            # names_self: this ALJ's surname appears in the PROSE (not just the
            # cite list) — the strongest attribution. A multi-cite row's prose
            # may narrate a different ALJ's point, so verbatim observations are
            # drawn only from names_self rows.
            names_self = bool(re.search(rf"\b{re.escape(sn)}\b", text))
            rec = aljs[sn]
            rec["surname"] = sn
            rec["gold"].append({
                "year": year, "categories": cats,
                "district": next((c.get("district", "").strip()
                                  for c in g["cites"] if (c.get("alj") or "").strip() == sn), ""),
                "text": text, "conduct_obs": conduct,
                "names_self": names_self, "solo": n_aljs == 1,
            })

    # ---- structured holdings (2004/2009), de-identified ----
    for case_no, dec in load_decisions():
        ident = dec.get("identity") or {}
        raw = (ident.get("alj") or {}).get("raw") or ""
        sn = alj_surname(raw)
        if not sn:
            continue
        district = district_short((ident.get("district") or {}).get("raw") or "")
        rec = aljs[sn]
        rec["surname"] = sn
        if raw.strip():
            rec["raw_names"].add(raw.strip())
        for i, h in enumerate(dec.get("holdings") or []):
            issue = h.get("issue") or {}
            ruling = h.get("ruling") or {}
            rec["structured"].append({
                "case_no": case_no, "idx": i, "year": case_no[:4],
                "category": issue.get("category"), "subtype": issue.get("subtype"),
                "prevailing_party": ruling.get("prevailing_party"),
                "district": district,
                "issue_statement": _d(issue.get("statement"), dec),
                "summary": _d(h.get("summary_style_holding"), dec),
                "reasoning": _d((h.get("reasoning") or {}).get("summary"), dec),
                "arguments": [
                    {"party": a.get("party"), "summary": _d(a.get("summary"), dec)}
                    for a in (h.get("arguments") or []) if a.get("summary")],
                "authorities": [
                    {"cite": a.get("raw_cite"), "type": a.get("type"), "role": a.get("role")}
                    for a in (h.get("authorities") or []) if a.get("raw_cite")],
            })

    # ---- density + ambiguity ----
    for sn, rec in aljs.items():
        years = sorted({g["year"] for g in rec["gold"] if g["year"]}
                       | {int(h["year"]) for h in rec["structured"]})
        cats = {c for g in rec["gold"] for c in g["categories"]} \
            | {h["category"] for h in rec["structured"] if h["category"]}
        dists = {g["district"] for g in rec["gold"] if g["district"]} \
            | {h["district"] for h in rec["structured"] if h["district"]}
        decided = [h for h in rec["structured"] if h["prevailing_party"] in DECIDED]
        # ambiguous only if the raw full names are genuinely different people —
        # accent/whitespace variants of one name (Rene/René) don't count.
        rec["ambiguous"] = len({_fold(n) for n in rec["raw_names"]}) > 1
        rec["density"] = {
            "gold_cites": len(rec["gold"]),
            "structured_holdings": len(rec["structured"]),
            "decided_holdings": len(decided),
            "years_span": [years[0], years[-1]] if years else None,
            "n_years": len(years),
            "n_categories": len(cats),
            "n_districts": len(dists),
            "conduct_obs": sum(1 for g in rec["gold"] if g["conduct_obs"]),
        }
    return dict(aljs)


# ---------- corpus-level aggregates (denominators for tendency comparison) ----------

def corpus_aggregates(aljs=None):
    if aljs is None:
        aljs = assemble()
    cat_counts = collections.Counter()
    win, decided = 0, 0
    auth_counts = collections.Counter()
    for rec in aljs.values():
        for g in rec["gold"]:
            for c in g["categories"]:
                cat_counts[c] += 1
        for h in rec["structured"]:
            if h["prevailing_party"] in DECIDED:
                decided += 1
                win += h["prevailing_party"] == "respondent"
            for a in h["authorities"]:
                if a["cite"]:
                    auth_counts[_norm_cite(a["cite"])] += 1
    return {
        "category_dist": cat_counts,
        "category_total": sum(cat_counts.values()),
        "respondent_win_base": win / decided if decided else 0.0,
        "decided_total": decided,
        "authority_counts": auth_counts,
    }


_CITE_TRIM = re.compile(r"\s*[\(,].*$")


def _norm_cite(cite):
    """Coarse normalization so 'Ed. Code, § 44955' and 'Ed. Code § 44955 (a)'
    collapse — enough to count which authorities an ALJ leans on."""
    c = (cite or "").strip()
    c = _CITE_TRIM.sub("", c)
    return re.sub(r"\s+", " ", c).strip().rstrip(".").lower()
