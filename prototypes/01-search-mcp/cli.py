#!/usr/bin/env python3
"""Manual-testing CLI.

Examples:
  cli.py "skipping for dual immersion teachers" --year 2009
  cli.py "tie-breaking lottery" --collection gold_holdings -k 5
  cli.py "bumping junior teacher" --mode bm25 --category bumping
"""

import argparse
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from engine import Engine  # noqa: E402


def cite(meta):
    cites = meta.get("cites")
    if cites:
        return "; ".join(f"{c.get('district')} ({c.get('alj')})" for c in cites)
    d, a = meta.get("district"), meta.get("alj")
    return f"{d} ({a})" if d or a else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--collection", default="holdings",
                    choices=["holdings", "gold_holdings", "decisions"])
    ap.add_argument("--mode", default="hybrid", choices=["hybrid", "bm25", "embed"])
    ap.add_argument("--model", default="arctic-l-v2")
    ap.add_argument("-k", type=int, default=10)
    ap.add_argument("--year")
    ap.add_argument("--category")
    ap.add_argument("--district")
    ap.add_argument("--alj")
    ap.add_argument("--prevailing-party", dest="prevailing_party")
    args = ap.parse_args()

    filters = {k: getattr(args, k) for k in
               ("year", "category", "district", "alj", "prevailing_party")
               if getattr(args, k)}
    eng = Engine(args.model)
    hits = eng.search(args.collection, args.query, filters, k=args.k, mode=args.mode)
    if not hits:
        print("no results")
        return
    for i, h in enumerate(hits, 1):
        m = h["meta"]
        tags = " ".join(filter(None, [
            m.get("year"), m.get("category"),
            ",".join(m.get("categories") or []) or None,
            m.get("prevailing_party")]))
        print(f"{i:2d}. [{h['id']}] {cite(m)}  ({tags})  rrf={h['score']}")
        body = m.get("summary") or h["text"]
        print(textwrap.indent(textwrap.fill(body[:600], width=96), "    "))
        print()


if __name__ == "__main__":
    main()
