"""Depth arms: per-issue legal analysis, with or without corpus retrieval.

The depth bake-off's foundational comparison:
  - closed-book : local model analyzes the issue from the matter facts + its own
                  knowledge (the "model only" baseline).
  - RAG         : local model analyzes over retrieved analogous holdings WITH their
                  ALJ reasoning (the "system" — does the corpus add depth?).

Scored by the E0 depth judge against the SOURCE decision's actual reasoning. Free
prose (not structured) so the model can articulate the operative distinction —
think=False + a num_predict cap (lesson: reasoning models starve free-prose answers).

make_depth_arm("ollama:gemma4:12b", use_retrieval=True) -> arm_fn(matter, issues).
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from harness.issues import ISSUE_DEFS                       # noqa: E402

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from corpuslib.llm import generate                          # noqa: E402

from .retrieval import retrieve                             # noqa: E402

SYSTEM = ("You are a California school-district attorney advising on a "
          "certificated-employee (teacher) layoff (Education Code 44949/44955). "
          "Write tight, specific analysis — the operative legal test/distinction "
          "and how it applies to these facts, not generalities.")


def _evidence_block(holdings_):
    lines = []
    for h in holdings_:
        cite = f"{h['district']} ({h['alj']}), {h['year']}"
        pp = f" [{h['prevailing_party']} prevailed]" if h.get("prevailing_party") else ""
        lines.append(f"- {cite}{pp} [{h['hid']}]\n  facts: {' '.join(h['facts'])[:300]}\n  "
                     f"ALJ reasoning: {h['reasoning'][:400]}")
    return "\n".join(lines)


def _prompt(matter, issue, ev):
    defn = ISSUE_DEFS.get(issue, issue)
    head = (f"ISSUE: {issue} — {defn}\n\n{matter['matter_text']}\n\n")
    if ev:
        return (head + "ANALOGOUS HOLDINGS FROM THE CORPUS (with the ALJ's actual reasoning; "
                "note each one's outcome — some are cases the DISTRICT prevailed, some the "
                "RESPONDENT/employee prevailed):\n"
                + _evidence_block(ev) + "\n\n"
                "Using these analogous holdings, analyze how this issue is likely to be "
                "resolved in THIS matter: state the operative distinction/test the holdings "
                "turn on, pay attention to what distinguishes the cases the district LOST from "
                "those it won, reason about which pattern THESE facts match, and give the likely "
                "outcome. Cite the holdings (District (ALJ), year) you rely on; do not invent holdings.")
    return (head + "Analyze how this issue is likely to be resolved in THIS matter: state the "
            "operative legal distinction/test that governs it and how the facts here map onto "
            "it, and the likely outcome. Be specific about the governing standard.")


def make_depth_arm(backend, use_retrieval=True, k=6, think=True, num_predict=8000,
                   balanced=False):
    # think=True lets reasoning models emit a chain-of-thought before answering
    # (response comes back CoT-stripped); a generous num_predict keeps the CoT
    # from starving the answer (lab lesson). think=False suppresses reasoning.
    # balanced=True: 50/50 district/respondent evidence (counter the corpus skew).
    opts = {"temperature": 0.3, "num_predict": num_predict}

    def arm_fn(matter, issues):
        per_issue, t0, ncalls = [], time.time(), 0
        excl = set(matter.get("exclude_ids") or [])
        for iss in issues:
            ev = retrieve(matter, iss, excl, k, balanced=balanced) if use_retrieval else []
            try:
                txt = generate(backend, _prompt(matter, iss, ev), system=SYSTEM,
                               think=think, options=opts)
                ncalls += 1
            except Exception as e:
                txt = f"(error: {str(e)[:80]})"
            per_issue.append({"issue": iss, "analysis": txt,
                              "cited_holding_ids": [h["hid"] for h in ev],
                              "n_evidence": len(ev)})
        return {"per_issue": per_issue,
                "_cost": {"wall_clock_s": round(time.time() - t0, 1), "n_calls": ncalls}}
    arm_fn.backend = backend
    arm_fn.use_retrieval = use_retrieval
    return arm_fn
