#!/usr/bin/env python3
"""Blind the suite for the Opus difficulty rating (+ frontier closed-book prediction).

The judge sees ONLY the issue + de-identified matter facts — NEVER the outcome — so
its difficulty rating is "how hard to call from the facts," not hindsight, and its
prediction is a genuine blind closed-book call (a frontier reference + difficulty
signal). Truth + signals are carried in a side meta the judge never sees.

  difficulty_prep.py   (reads output/suite.json)
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from harness.deid import scrub_external          # noqa: E402

OUT = HERE / "output"


def main():
    suite = json.loads((OUT / "suite.json").read_text())
    rows = sorted(suite, key=lambda c: hashlib.sha1(c["hid"].encode()).hexdigest())
    blind, meta = [], {}
    for n, c in enumerate(rows, 1):
        code = f"D{n:03d}"
        blind.append({"code": code, "issue": c["issue"],
                      "matter_text": scrub_external(c["matter_text"])})
        meta[code] = {"hid": c["hid"], "matter_id": c["matter_id"], "truth": c["truth"],
                      "era": c["era"], "issue": c["issue"], "alj": c["alj"],
                      "base_rate_resp": c["base_rate_resp"], "included": c["included"],
                      "weight": c["weight"], "reason_words": c["reason_words"]}
    (OUT / "difficulty.input.json").write_text(json.dumps(blind, indent=1, ensure_ascii=False))
    (OUT / "difficulty.meta.json").write_text(json.dumps(meta, indent=1))
    (OUT / "difficulty.codes.json").write_text(json.dumps([b["code"] for b in blind]))
    print(f"{len(blind)} blinded items -> difficulty.input.json (+ meta, codes)")


if __name__ == "__main__":
    main()
