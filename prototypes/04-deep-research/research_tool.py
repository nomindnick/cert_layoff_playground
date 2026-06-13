#!/usr/bin/env python3
"""One clean corpus interface for the deep-research loop (W9 stage 1).

Wraps the F1 engine + corpuslib so an agent (or a person) can drive the
retrieve->read step with a single command, without the MCP server being
connected. De-identifies roster respondent names on the full-holding read.

  research_tool.py search "<query>" [--collection holdings|gold_holdings|decisions]
                   [--year Y] [--category C] [--district D] [--alj A]
                   [--prevailing-party P] [-k N]
  research_tool.py holding <case:idx>       # full rich, de-identified holding
  research_tool.py decision <case_no>       # decision record (no full_text)
  research_tool.py facets [collection]

PRIVACY NOTE: de-identification covers ROSTER (respondent) names only. Non-roster
individuals named in a holding (e.g. a junior teacher who was retained) can still
appear — scrub any personal name to District (ALJ) form before committing output.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "prototypes" / "01-search-mcp"))

from corpuslib import load_decisions  # noqa: E402
from corpuslib.deident import deidentify  # noqa: E402
from engine import Engine  # noqa: E402

_eng = None
_dec = {}


def engine():
    global _eng
    if _eng is None:
        _eng = Engine()
    return _eng


def decision(case_no):
    if not _dec:
        _dec.update({c: r for c, r in load_decisions()})
    return _dec.get(case_no)


def _deid(obj, rec):
    if isinstance(obj, str):
        return deidentify(obj, rec)[0]
    if isinstance(obj, list):
        return [_deid(x, rec) for x in obj]
    if isinstance(obj, dict):
        return {k: _deid(v, rec) for k, v in obj.items()}
    return obj


def cite(m):
    cs = m.get("cites")
    if cs:
        return "; ".join(f"{c.get('district')} ({c.get('alj')})" for c in cs)
    return f"{m.get('district')} ({m.get('alj')})"


def cmd_search(a):
    filters = {k: getattr(a, k) for k in
               ("year", "category", "district", "alj", "prevailing_party")
               if getattr(a, k)}
    hits = engine().search(a.collection, a.query, filters, k=a.k, mode=a.mode)
    for i, h in enumerate(hits, 1):
        m = h["meta"]
        tags = " ".join(filter(None, [m.get("year"), m.get("category"),
                        ",".join(m.get("categories") or []) or None,
                        m.get("prevailing_party")]))
        body = (m.get("summary") or h["text"])[:550]
        print(f"{i:2d}. [{h['id']}] {cite(m)}  ({tags})")
        print(f"    {body}\n")


def cmd_holding(a):
    case_no, _, idx = a.id.partition(":")
    rec = decision(case_no)
    if not rec:
        print(f"unknown case {case_no}"); return
    try:
        h = (rec.get("holdings") or [])[int(idx)]
    except (IndexError, ValueError):
        print(f"no holding {idx} in {case_no}"); return
    out = _deid(h, rec)
    ident = rec.get("identity") or {}
    out["_cite"] = f"{(ident.get('district') or {}).get('raw')} ({(ident.get('alj') or {}).get('raw')})"
    print(json.dumps(out, indent=1, ensure_ascii=False))


def cmd_decision(a):
    rec = decision(a.case_no)
    if not rec:
        print(f"unknown case {a.case_no}"); return
    out = {k: v for k, v in rec.items() if k not in ("full_text", "provenance")}
    out = _deid(out, rec)
    for r in ((out.get("outcome") or {}).get("roster") or []):
        r.pop("name", None)
    print(json.dumps(out, indent=1, ensure_ascii=False))


def cmd_facets(a):
    print(json.dumps(engine().list_facets(a.collection), indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("query")
    s.add_argument("--collection", default="holdings",
                   choices=["holdings", "gold_holdings", "decisions"])
    s.add_argument("--mode", default="hybrid", choices=["hybrid", "bm25", "embed"])
    s.add_argument("-k", type=int, default=8)
    for f in ("year", "category", "district", "alj"):
        s.add_argument(f"--{f}", default="")
    s.add_argument("--prevailing-party", dest="prevailing_party", default="")
    s.set_defaults(func=cmd_search)
    h = sub.add_parser("holding"); h.add_argument("id"); h.set_defaults(func=cmd_holding)
    d = sub.add_parser("decision"); d.add_argument("case_no"); d.set_defaults(func=cmd_decision)
    fa = sub.add_parser("facets"); fa.add_argument("collection", nargs="?", default="holdings")
    fa.set_defaults(func=cmd_facets)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
