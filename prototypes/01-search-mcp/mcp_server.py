#!/usr/bin/env python3
"""MCP server over the layoff-decision corpus (stdio).

Tools: search_holdings, search_gold_holdings, get_decision, get_holding,
list_facets. Local-only tool; get_decision de-identifies respondent names by
default (roster names -> R-refs via the lab-validated deidentify pass).

Registered in the repo-root .mcp.json so Claude Code sessions in this repo
get corpus access automatically.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from corpuslib import load_decisions  # noqa: E402
from deident import deidentify  # noqa: E402
from engine import Engine  # noqa: E402

mcp = FastMCP("layoff-corpus")
_engine = Engine()
_decisions_cache = {}


def _decision(case_no):
    if not _decisions_cache:
        _decisions_cache.update({c: r for c, r in load_decisions()})
    return _decisions_cache.get(case_no)


def _hit_view(hit):
    m = hit["meta"]
    cites = m.get("cites")
    cite = ("; ".join(f"{c.get('district')} ({c.get('alj')})" for c in cites)
            if cites else f"{m.get('district')} ({m.get('alj')})")
    return {
        "id": hit["id"],
        "cite": cite,
        "year": m.get("year"),
        "category": m.get("category") or m.get("categories"),
        "prevailing_party": m.get("prevailing_party"),
        "summary": m.get("summary") or hit["text"][:400],
        "rrf_score": hit["score"],
    }


@mcp.tool()
def search_holdings(query: str, year: str = "", category: str = "",
                    district: str = "", alj: str = "",
                    prevailing_party: str = "", k: int = 10) -> list:
    """Hybrid search over extracted holdings from OAH teacher-layoff decisions
    (currently years 2004 and 2009). Each result has a holding id
    ("caseno:idx" — usable with get_holding/get_decision), a District (ALJ)
    cite, and the holding summary. Filters: year (e.g. "2009"), category
    (canonical issue id, see list_facets), district/alj (substring),
    prevailing_party ("district"/"respondent"/"mixed")."""
    filters = {"year": year, "category": category, "district": district,
               "alj": alj, "prevailing_party": prevailing_party}
    hits = _engine.search("holdings", query,
                          {k_: v for k_, v in filters.items() if v}, k=k)
    return [_hit_view(h) for h in hits]


@mcp.tool()
def search_gold_holdings(query: str, year: str = "", category: str = "",
                         district: str = "", alj: str = "", k: int = 10) -> list:
    """Hybrid search over the expert-written annual summary volumes'
    holdings, 1979-2015 (3,800+ entries, already de-identified to District
    (ALJ) cites). Editorial selections, not exhaustive: noteworthy holdings
    only. Filters: year, category (canonical issue id), district/alj
    (substring)."""
    filters = {"year": year, "category": category, "district": district, "alj": alj}
    hits = _engine.search("gold_holdings", query,
                          {k_: v for k_, v in filters.items() if v}, k=k)
    return [_hit_view(h) for h in hits]


@mcp.tool()
def search_decisions(query: str, year: str = "", k: int = 10) -> list:
    """BM25 full-text search over complete decision texts (2004/2009). Use
    when holding-level search misses — e.g. procedural details, witness
    discussion, or phrasing that never made it into a holding."""
    filters = {"year": year} if year else None
    hits = _engine.search("decisions", query, filters, k=k, mode="bm25")
    return [{"case_no": h["id"],
             "cite": f"{h['meta'].get('district')} ({h['meta'].get('alj')})",
             "year": h["meta"].get("year"),
             "overall": h["meta"].get("overall"),
             "n_holdings": h["meta"].get("n_holdings")} for h in hits]


@mcp.tool()
def get_holding(holding_id: str) -> dict:
    """Full rich record for one extracted holding (id "caseno:idx"): issue,
    ruling, arguments by party, facts, authorities cited and how used, and
    the reasoning chain. De-identified (respondent names -> R-refs)."""
    case_no, _, idx = holding_id.partition(":")
    rec = _decision(case_no)
    if not rec:
        return {"error": f"unknown case {case_no}"}
    try:
        h = (rec.get("holdings") or [])[int(idx)]
    except (IndexError, ValueError):
        return {"error": f"no holding {idx} in {case_no}"}
    out = _deidentify_obj(h, rec)
    ident = rec.get("identity") or {}
    out["_case"] = {
        "case_no": case_no,
        "district": (ident.get("district") or {}).get("raw"),
        "alj": (ident.get("alj") or {}).get("raw"),
    }
    return out


@mcp.tool()
def get_decision(case_no: str, include_full_text: bool = False,
                 deidentify_names: bool = True) -> dict:
    """One full decision record: identity, board action, outcome (roster as
    refs, dispositions), all holdings, related proceedings. full_text
    excluded by default (large); deidentify_names=True (default) replaces
    respondent names with R-refs throughout."""
    rec = _decision(case_no)
    if not rec:
        return {"error": f"unknown case {case_no}"}
    out = {k: v for k, v in rec.items()
           if k not in ("full_text", "provenance")}
    if deidentify_names:
        out = _deidentify_obj(out, rec)
        roster = ((out.get("outcome") or {}).get("roster")) or []
        for r in roster:
            r.pop("name", None)
    if include_full_text:
        text = rec.get("full_text") or ""
        if deidentify_names:
            text, _ = deidentify(text, rec)
        out["full_text"] = text
    return out


@mcp.tool()
def list_facets(collection: str = "holdings") -> dict:
    """Available filter values with counts. Collections: holdings,
    gold_holdings, decisions. Shows years, issue categories, districts,
    ALJs, prevailing parties present in the corpus."""
    if collection not in ("holdings", "gold_holdings", "decisions"):
        return {"error": "unknown collection"}
    return _engine.list_facets(collection)


def _deidentify_obj(obj, rec):
    """Deep-walk a structure, de-identifying every string against rec's roster."""
    if isinstance(obj, str):
        out, _ = deidentify(obj, rec)
        return out
    if isinstance(obj, list):
        return [_deidentify_obj(x, rec) for x in obj]
    if isinstance(obj, dict):
        return {k: _deidentify_obj(v, rec) for k, v in obj.items()}
    return obj


if __name__ == "__main__":
    mcp.run()
