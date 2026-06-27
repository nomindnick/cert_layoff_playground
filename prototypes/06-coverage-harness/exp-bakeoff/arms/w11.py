"""W11 verify-repair arm: draft -> corpus-grounded directional critique -> repair.

The "system over model" test. Built on the eval-upgrade finding (FINDINGS, W11 eval
upgrade): naive RAG grounds cites but amplifies the ~79% district-win skew (cratering
exposure accuracy) and leaves inversions / exposure-blindness unfixed. W11 adds three
things, ALL LOCAL (same base model for draft/verify/repair — the SYSTEM is the loop +
corpus-grounding, not a second/stronger model):

  - BALANCED retrieval (50/50 district/respondent) so the evidence isn't skewed.
  - a corpus-grounded VERIFY pass — critique the draft's predicted DIRECTION against
    how the analogous holdings ACTUALLY came out (their real prevailing_party = the
    non-correlated oracle), and name the respondent's strongest argument + any contrary
    holdings / mischaracterized cites the draft ignored.
  - a REPAIR pass that revises the draft to address the critique.

Verify/repair use free-text (think=ON) — the critique text feeds straight into repair,
so no brittle structured parsing. Emits, per issue, BOTH the balanced-RAG draft (arm
'rag') and the repaired (arm 'w11') so the metric tooling shows verify-repair's marginal
effect (and, vs the existing UNBALANCED rag runs, the balanced-retrieval effect too).
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from corpuslib.llm import generate                    # noqa: E402

from .retrieval import retrieve                        # noqa: E402
from .depth_analyzer import _prompt, _evidence_block, SYSTEM  # noqa: E402

VERIFY_SYS = ("You are a meticulous appellate auditor reviewing a junior attorney's "
              "draft analysis of one California certificated-layoff (Education Code "
              "44949/44955) issue. Your job is to catch INVERTED conclusions, ignored "
              "contrary authority, and mischaracterized holdings. Be skeptical, specific, "
              "and grounded in how the cited holdings ACTUALLY came out.")


def _verify_prompt(matter, issue, ev, draft):
    return (f"ISSUE: {issue}\n\nMATTER FACTS:\n{matter['matter_text'][:1600]}\n\n"
            "ANALOGOUS CORPUS HOLDINGS — note WHO ACTUALLY PREVAILED in each (the ground "
            "truth of how this kind of issue really comes out; the set is balanced "
            "district/respondent on purpose):\n"
            + _evidence_block(ev) + "\n\n"
            f"DRAFT ANALYSIS TO AUDIT:\n{draft}\n\n"
            "Audit the draft — be specific and brief:\n"
            "1. DIRECTION: Does the draft's predicted outcome match the pattern of how the "
            "MOST FACTUALLY ANALOGOUS holdings actually came out? If the draft predicts the "
            "district prevails but closely-analogous holdings went to the RESPONDENT (or "
            "vice versa), say so and name which holdings the draft failed to distinguish. "
            "Watch for the classic inversion (e.g. treating 'probationary' as protective "
            "when it lets the district lay the employee off).\n"
            "2. IGNORED EXPOSURE: State the respondent/employee's STRONGEST argument "
            "(supported by a respondent-win holding above) that the draft did not engage.\n"
            "3. CITE FIDELITY: Does the draft characterize any cited holding in a way that "
            "holding's actual reasoning/outcome does not support?\n"
            "If the draft is sound and correctly directed, say so plainly. Otherwise give a "
            "short, pointed critique the drafter can act on.")


def _repair_prompt(matter, issue, ev, draft, critique):
    return (f"ISSUE: {issue}\n\n{matter['matter_text']}\n\n"
            "ANALOGOUS HOLDINGS (with their real outcomes):\n" + _evidence_block(ev) + "\n\n"
            f"YOUR DRAFT:\n{draft}\n\n"
            f"AUDIT OF YOUR DRAFT:\n{critique}\n\n"
            "Revise your analysis to FULLY address the audit: correct any inverted or "
            "mis-directed conclusion, distinguish or follow the contrary holdings the audit "
            "flagged, fix any mischaracterized cite, and engage the respondent's strongest "
            "argument and the district's real exposure. State the operative legal "
            "distinction and the likely outcome for THIS matter, grounded in the cited "
            "holdings (District (ALJ), year). Output the revised analysis only.")


def make_w11_arm(backend, k=8, think=True, num_predict=8000):
    """arm_fn(matter, issues) -> per_issue with {draft, critique, repaired, ...}.

    DRAFT uses think (reasoning helps the base analysis). VERIFY and REPAIR use
    think=OFF — on these reasoning-heavy audit/revise tasks, think=ON starves the
    visible answer to empty (the model spends num_predict in the hidden CoT channel;
    confirmed: qwen3.5:35b verify think=ON -> 0 chars / 140s, think=OFF -> 5.8k chars /
    24s). think=OFF makes the audit reasoning the visible critique, reliably + faster.
    """
    opts = {"temperature": 0.3, "num_predict": num_predict}
    vr_opts = {"temperature": 0.3, "num_predict": 3000}     # verify/repair, think=OFF

    def arm_fn(matter, issues):
        out, t0 = [], time.time()
        excl = set(matter.get("exclude_ids") or [])
        for iss in issues:
            ev = retrieve(matter, iss, excl, k=k, balanced=True)
            try:
                draft = generate(backend, _prompt(matter, iss, ev), system=SYSTEM,
                                 think=think, options=opts)
                critique = generate(backend, _verify_prompt(matter, iss, ev, draft),
                                    system=VERIFY_SYS, think=False, options=vr_opts)
                repaired = generate(backend, _repair_prompt(matter, iss, ev, draft, critique),
                                   system=SYSTEM, think=False, options=vr_opts)
            except Exception as e:
                draft = critique = repaired = f"(error: {str(e)[:80]})"
            out.append({"issue": iss, "draft": draft, "critique": critique,
                        "repaired": repaired,
                        "cited_holding_ids": [h["hid"] for h in ev], "n_evidence": len(ev)})
        return {"per_issue": out, "_cost": {"wall_clock_s": round(time.time() - t0, 1)}}

    arm_fn.backend = backend
    return arm_fn
