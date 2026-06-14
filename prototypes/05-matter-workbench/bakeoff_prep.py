#!/usr/bin/env python3
"""Collect every arm's memos, make name-stripped copies for the discriminability
test, and emit bakeoff_args.json for the Opus-4.8 eval workflow.

Arms: each subdir of output/memos_bakeoff/ (local models) + the Opus-4.8 baseline
memos in output/memos/ (arm 'opus-4.8'). Same eval method for all, so the
comparison isolates the synthesizer.
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
MATTERS = HERE / "matters"


def fingerprint(m):
    fp = [f"Basis: {m.get('basis','')}"]
    for s in m.get("proposed_skips") or []:
        fp.append(f"Skip junior {s['retained_junior_role']} for {s['claimed_special_skill']} "
                  f"(in resolution: {s['in_board_resolution']})")
    for b in m.get("bumping_disputes") or []:
        fp.append(f"Bumping: {b['senior_employee_role']} claims {b['claims']}")
    tb = m.get("tiebreak") or {}
    if tb.get("lottery_used"):
        fp.append(f"Tie-break lottery: {tb.get('lottery_detail','')}")
    for pf in m.get("procedural_facts") or []:
        fp.append(f"Procedural: {pf}")
    return " | ".join(fp)


def anon(text, district, alj):
    """Strip the matter's own district + assigned-ALJ names so the
    discriminability judge must match on substance. Precedent cites of the form
    'Surname (' are left intact (they're evidence, not the matter's identity)."""
    t = text.replace(district, "the District")
    if alj:
        t = re.sub(rf"\b{re.escape(alj)}\b(?!\s*\()", "[ALJ]", t)
    return t


def main():
    matters = {}
    for p in sorted(MATTERS.glob("*.json")):
        m = json.loads(p.read_text())
        m["_path"] = str(p)
        matters[m["matter_id"]] = m
    fps = {mid: fingerprint(m) for mid, m in matters.items()}

    # discover arms: local bakeoff dirs + opus baseline
    arms = {}
    for d in sorted((OUT / "memos_bakeoff").glob("*")):
        if d.is_dir():
            arms[d.name] = d
    arms["opus-4p8"] = OUT / "memos"  # baseline (Opus 4.8, original run)

    anon_root = OUT / "memos_anon"
    items = []
    for arm, d in arms.items():
        for mid, m in matters.items():
            memo_path = d / f"{mid}.md"
            if not memo_path.exists() or not memo_path.read_text().strip():
                print(f"  skip {arm}/{mid} (missing/empty)")
                continue
            ad = anon_root / arm
            ad.mkdir(parents=True, exist_ok=True)
            anon_path = ad / f"{mid}.md"
            anon_path.write_text(anon(memo_path.read_text(), m["district"], m.get("alj")))
            items.append({
                "arm": arm, "matter_id": mid,
                "memo_path": str(memo_path), "anon_memo_path": str(anon_path),
                "matter_path": m["_path"],
                "evidence_path": str(OUT / "evidence" / f"{mid}.json"),
            })
    args = {"items": items, "fingerprints": fps}
    (OUT / "bakeoff_args.json").write_text(json.dumps(args, indent=1))
    by_arm = {}
    for it in items:
        by_arm.setdefault(it["arm"], []).append(it["matter_id"])
    print(f"wrote bakeoff_args.json: {len(items)} memos across {len(by_arm)} arms")
    for arm, mids in by_arm.items():
        print(f"  {arm}: {len(mids)} memos")


if __name__ == "__main__":
    main()
