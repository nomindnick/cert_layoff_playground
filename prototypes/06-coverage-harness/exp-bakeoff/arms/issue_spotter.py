"""E1 arm: local-model issue-spotter (BREADTH only).

The cheapest test of the local-primary thesis (W9 stage 2): give a local model
the matter facts + the 22-issue menu and ask which issues are implicated. Scored
on the E0 breadth metric (rarity_recall) vs the frequency-prior floor (~0.37).
No per-issue depth analysis — this probe answers "can a local model spot the
issues at all," before we build the heavier retrieval/analysis arms.

`make_arm("ollama:gemma4:31b")` -> arm_fn(matter) in the E0 contract.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # prototype dir

from harness.issues import CANONICAL_ISSUES, issue_menu        # noqa: E402

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from corpuslib.llm import generate                              # noqa: E402

SYSTEM = ("You are a California school-district attorney issue-spotting a "
          "certificated-employee (teacher) layoff under Education Code "
          "sections 44949 and 44955.")

# NOTE: no free-text field. A 'basis' string triggers gemma4 runaway / unterminated
# JSON under grammar-constrained format mode (lesson: 02-taste-judge). Keep the
# output short + enum-constrained so it can't loop.
SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": CANONICAL_ISSUES},
                    "confidence": {"type": "number"},
                },
                "required": ["category", "confidence"],
            },
        }
    },
    "required": ["issues"],
}

# temp ~0.2 + a num_predict cap (lesson: temp-0 grammar gemma4 loops); 22 short
# objects fit well under 2048 output tokens.
OPTS = {"temperature": 0.2, "num_predict": 2048}


def _prompt(matter):
    return f"""Below is the ESTABLISHED FACTUAL SITUATION in a layoff matter. Identify EVERY issue from the menu that these facts plausibly put in play. Be thorough — a missed issue is worse than an extra one — but ground each pick in something in the facts (do not list an issue the facts give no hook for). Give each a confidence 0-1 and the triggering fact.

ISSUE MENU:
{issue_menu()}

{matter['matter_text']}

Return JSON: {{"issues": [{{"category": <one of the menu keys>, "confidence": <0-1>}}]}}."""


def make_arm(backend, min_conf=0.0):
    def arm_fn(matter):
        t0 = time.time()
        try:
            out = generate(backend, _prompt(matter), system=SYSTEM,
                            json_schema=SCHEMA, options=OPTS, think=False)
            items = out.get("issues") or []
        except Exception as e:                       # one bad call must not kill the sweep
            return {"spotted_issues": [], "per_issue": [],
                    "_cost": {"wall_clock_s": round(time.time() - t0, 1),
                              "n_calls": 1, "error": str(e)[:120]}}
        spotted, seen = [], set()
        for it in items:
            c = it.get("category")
            if c in CANONICAL_ISSUES and c not in seen and it.get("confidence", 1) >= min_conf:
                seen.add(c)
                spotted.append({"category": c, "confidence": it.get("confidence", 1.0)})
        return {"spotted_issues": spotted, "per_issue": [],
                "_cost": {"wall_clock_s": round(time.time() - t0, 1), "n_calls": 1}}
    arm_fn.backend = backend
    return arm_fn
