"""Rule-distillation pre-pass (W11 v4): convert a retrieved case pack into issue rules.

Tests Nick's hypothesis (STATUS lesson "RAG examples act as outcome-VOTES"): models
soft-nearest-neighbor over the retrieved cases' OUTCOMES instead of deriving + applying
the rule. The lever may be PRESENTATION. A cheap, fast model (gemma4:12b) distills the
balanced RAG pack into doctrine in treatise/Restatement form:

  RULE: <operative test/distinction>
  APPLICATION: when <fact pattern>, the result is <outcome> (District (ALJ), year)

The RULE/APPLICATION split lets the framing runner present three evidence framings from
ONE distill call: (a) raw cases, (b) rules + worked illustration, (c) rules-only (the
APPLICATION lines stripped → outcomes removed). think=OFF: the distiller reasons over the
cases to extract rules and must OUTPUT them — think=ON starves it (the verify/judge lesson).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from corpuslib.llm import generate                    # noqa: E402

from .retrieval import retrieve                        # noqa: E402
from .depth_analyzer import _evidence_block            # noqa: E402

DISTILL_SYS = ("You are a legal editor building a focused rule digest for ONE issue in "
               "California certificated-employee layoffs (Education Code 44949/44955), from "
               "a set of decided cases. You derive the operative RULE from the ALJ's "
               "REASONING (not just the outcome), and you NEVER invent a rule or a case.")


def _distill_prompt(issue, ev):
    return (f"ISSUE: {issue}\n\nDECIDED CASES (facts, the ALJ's reasoning, and who prevailed):\n"
            + _evidence_block(ev) + "\n\n"
            "Write a RULE DIGEST for this issue — the 2-4 operative rules these cases turn on. "
            "Use EXACTLY this format, one block per rule:\n\n"
            "RULE: <the operative legal test or distinction, stated generally>\n"
            "APPLICATION: when <fact pattern>, the result is <who prevails and why> "
            "(District (ALJ), year)\n\n"
            "Derive each RULE from the reasoning the ALJs actually used; make the operative "
            "distinction explicit (especially counter-intuitive ones, e.g. that an undesignated "
            "contract DEFAULTS an employee to probationary, or that a lottery is NOT a valid "
            "tie-break). Cite ONLY the cases above. Output only the RULE/APPLICATION blocks.")


def distill(backend, matter, issue, ev, num_predict=2200):
    """Return {rules_full, rules_only} text from one distill call. rules_only strips the
    APPLICATION (outcome) lines to remove the exemplar-outcome pull for framing (c)."""
    opts = {"temperature": 0.2, "num_predict": num_predict}
    txt = generate(backend, _distill_prompt(issue, ev), system=DISTILL_SYS,
                   think=False, options=opts)
    rules_only = "\n".join(ln for ln in txt.splitlines()
                           if not re.match(r"\s*APPLICATION\s*:", ln, re.I))
    return {"rules_full": txt, "rules_only": rules_only.strip()}


def retrieve_pack(matter, issue, k=8, balanced=True):
    return retrieve(matter, issue, set(matter.get("exclude_ids") or []), k=k, balanced=balanced)
