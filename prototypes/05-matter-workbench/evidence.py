#!/usr/bin/env python3
"""Stage 1-3 (deterministic, no LLM): turn a matter into per-issue evidence packs.

issue-spot the matter -> for each issue, retrieve analogous holdings (structured +
gold) via the F1 engine, attach each holding's arguments-by-party + outcome +
reasoning (de-identified), and the assigned ALJ's P2 tendency if available.

Output: output/evidence/{matter_id}.json — the cited substrate the LLM memo is
written over. Built so the LLM never sees anything but de-identified, retrieved
facts.

Usage: evidence.py matters/matter_01_riverton.json   (or --all)
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

OUT = HERE / "output"
DOSSIER_DIR = REPO / "prototypes" / "03-alj-scouting" / "output" / "dossiers"

_eng = None
_decs = {}


def engine():
    global _eng
    if _eng is None:
        _eng = Engine()
    return _eng


def decision(case_no):
    if not _decs:
        _decs.update({c: r for c, r in load_decisions()})
    return _decs.get(case_no)


def _d(text, rec):
    return deidentify(text or "", rec)[0]


# ---------- issue spotting (deterministic from the matter structure) ----------

def spot_issues(m):
    """Return [{issue, triggers, queries}] from the matter's own fields."""
    issues = {}

    def add(issue, trigger, *queries):
        slot = issues.setdefault(issue, {"issue": issue, "triggers": [], "queries": []})
        slot["triggers"].append(trigger)
        slot["queries"].extend(q for q in queries if q)

    for s in m.get("proposed_skips") or []:
        t = (f"Skip: retain junior {s['retained_junior_role']} for "
             f"{s['claimed_special_skill']} (need: {s['specific_need']}; "
             f"in resolution: {s['in_board_resolution']})")
        add("skipping", t,
            f"district skip junior {s['claimed_special_skill']} retain over senior "
            f"{s['specific_need']}",
            "senior teacher competent and certificated to teach the program, skip improper")
        add("competency", t,
            f"competency standard {s['claimed_special_skill']} special training necessary")
        if not s.get("in_board_resolution", True):
            add("skipping", "Skip criterion NOT in the board PKS resolution",
                "skip criterion not in PKS board resolution competency not defined")

    for b in m.get("bumping_disputes") or []:
        t = f"Bumping: {b['senior_employee_role']} — {b['claims']}"
        add("bumping", t,
            f"senior teacher bump junior {b['claims']}",
            "senior employee competent to perform all services of junior position bump")
        add("competency", t, "competent to teach entire position bumping credential")

    tb = m.get("tiebreak") or {}
    if tb.get("lottery_used") or tb.get("lottery_detail"):
        add("tie_breaking", f"Tie-break: {tb.get('lottery_detail') or tb.get('criteria')}",
            "lottery to break tie seniority after applying tie-breaking criteria needs of district",
            "random method resolving tied seniority date needs of the district and students")

    for pf in m.get("procedural_facts") or []:
        add("procedural_issues", f"Procedural: {pf}", pf)
    # targeted procedural seeds
    if m.get("procedural_facts"):
        add("procedural_issues", "(procedural seeds)",
            "March 15 notice deadline mailed late excused no prejudice",
            "district noticed more employees than resolution FTE bumping proper",
            "ADA FTE calculation preparation period full time load")

    basis = (m.get("basis") or "").lower()
    if "pks" in basis or "particular" in basis or "categorical" in basis:
        add("pks_allowed", f"Basis: {m.get('basis')}",
            "particular kinds of services reduction PKS necessary budget",
            "categorically funded program elimination funding lapsed layoff")
    if "ada" in basis or "attrition" in basis or "decline" in basis:
        add("attrition", f"Basis: {m.get('basis')}",
            "attrition positively assured retirements resignations offset layoff ADA")

    # attorney concerns enrich every issue's query pool
    concern = m.get("attorney_concerns") or ""
    if concern:
        for slot in issues.values():
            slot["queries"].append(concern)
    return list(issues.values())


# ---------- retrieval per issue ----------

CAT = {"skipping": "skipping", "bumping": "bumping", "competency": "competency",
       "seniority": "seniority", "tie_breaking": "tie_breaking",
       "procedural_issues": "procedural_issues", "pks_allowed": "pks_allowed",
       "attrition": "attrition"}


def structured_args(hid):
    case_no, _, idx = hid.partition(":")
    rec = decision(case_no)
    if not rec:
        return None
    try:
        h = (rec.get("holdings") or [])[int(idx)]
    except (IndexError, ValueError):
        return None
    return {
        "arguments": [{"party": a.get("party"), "summary": _d(a.get("summary"), rec)}
                      for a in (h.get("arguments") or []) if a.get("summary")],
        "reasoning": _d((h.get("reasoning") or {}).get("summary"), rec),
        "authorities": [a.get("raw_cite") for a in (h.get("authorities") or [])
                        if a.get("raw_cite")][:5],
    }


def gold_cite(m):
    cs = m.get("cites")
    return "; ".join(f"{c.get('district')} ({c.get('alj')})" for c in cs) if cs else ""


def retrieve_issue(issue, queries, k_each=5, keep=7):
    cat = CAT.get(issue)
    pool = {}  # id -> hit (best score)
    for q in dict.fromkeys(queries):  # dedupe queries, preserve order
        for coll in ("holdings", "gold_holdings"):
            for filt in ([{"category": cat}, None] if cat else [None]):
                try:
                    hits = engine().search(coll, q, filt, k=k_each)
                except Exception:
                    continue
                for h in hits:
                    cur = pool.get(h["id"])
                    if cur is None or h["score"] > cur["score"]:
                        h["_coll"] = coll
                        pool[h["id"]] = h
                if filt and len(hits) >= 3:
                    break  # category filter gave enough; skip the unfiltered fallback
    ranked = sorted(pool.values(), key=lambda h: -h["score"])[:keep]
    out = []
    for h in ranked:
        meta = h["meta"]
        struct = h["_coll"] == "holdings"
        row = {
            "id": h["id"],
            "source": "structured" if struct else "gold",
            "cite": (f"{meta.get('district')} ({meta.get('alj')})" if struct
                     else gold_cite(meta)),
            "year": meta.get("year"),
            "category": meta.get("category") or (meta.get("categories") or [None])[0],
            "prevailing_party": meta.get("prevailing_party"),
            "summary": meta.get("summary") or h["text"][:500],
        }
        if struct:
            extra = structured_args(h["id"])
            if extra:
                row.update(extra)
        out.append(row)
    return out


def alj_tendency(alj, issues):
    path = DOSSIER_DIR / f"{alj}.json"
    if not alj or not path.exists():
        return None
    d = json.loads(path.read_text())
    over = {r["category"]: r for r in d["issue_footprint"]["over_represented"]}
    rel = {iss: over[iss] for iss in issues if iss in over}
    return {
        "density": d["density"],
        "outcome": d["outcome"].get("interpretation"),
        "relevant_footprint": rel,
        "editor_observations": [o["text"] for o in d.get("editor_observations", [])[:4]],
    }


def build(matter_path):
    m = json.loads(Path(matter_path).read_text())
    spotted = spot_issues(m)
    issue_names = [s["issue"] for s in spotted]
    pack = {
        "matter_id": m["matter_id"],
        "district": m["district"],
        "alj": m.get("alj"),
        "basis": m.get("basis"),
        "alj_tendency": alj_tendency(m.get("alj"), issue_names),
        "issues": [],
    }
    for s in spotted:
        holdings = retrieve_issue(s["issue"], s["queries"])
        pack["issues"].append({
            "issue": s["issue"],
            "triggers": s["triggers"],
            "n_holdings": len(holdings),
            "holdings": holdings,
        })
    return pack


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("matter", nargs="?")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    (OUT / "evidence").mkdir(parents=True, exist_ok=True)
    paths = (sorted((HERE / "matters").glob("*.json")) if args.all
             else [Path(args.matter)])
    for p in paths:
        pack = build(p)
        out = OUT / "evidence" / f"{pack['matter_id']}.json"
        out.write_text(json.dumps(pack, indent=1, ensure_ascii=False))
        n = sum(i["n_holdings"] for i in pack["issues"])
        print(f"{pack['matter_id']}: {len(pack['issues'])} issues, {n} holdings, "
              f"alj={pack['alj']} -> {out.name}")


if __name__ == "__main__":
    main()
