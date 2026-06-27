"""Adversarial-proceeding arm (W11 v2): simulate the OAH hearing.

v1 (single corpus-grounded verify-repair) FALSIFIED — a one-directional "did you
miss the respondent's case?" critic over-corrects every draft toward the respondent
(balanced evidence always supplies a respondent-win holding to point at). v2 fixes
the asymmetry STRUCTURALLY by simulating the adversarial proceeding:

  1. DISTRICT counsel writes the best good-faith case for the District, grounded in
     and quoting the RAG holdings that favor it (distinguishing the contrary ones).
  2. RESPONDENT counsel does the same for the employee.
  3. a neutral ALJ JUDGE reads the facts + the RAG pack + BOTH briefs and writes a
     decision, weighing both sides and concluding who prevails on the issue.

The JUDGE's opinion is what we score. Each advocate is told to advocate hard but
NOT misstate facts/law/holdings (officer of the tribunal). All local (same base in
three roles — the SYSTEM is the adversarial structure, not a stronger model).

think=OFF for all three roles: these are reasoning-heavy tasks and think=ON starves
the visible answer to empty (the v1 verify lesson); think=OFF makes the reasoning the
output, reliably + faster.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from corpuslib.llm import generate                    # noqa: E402

from .retrieval import retrieve                        # noqa: E402
from .depth_analyzer import _evidence_block            # noqa: E402

_OFFICER = ("You zealously advocate for your client, but you are an officer of the "
            "tribunal: do NOT misstate facts, law, or what a cited holding actually "
            "held. Make the strongest GOOD-FAITH case the record and authorities "
            "support.")

DISTRICT_SYS = ("You are experienced counsel for a California SCHOOL DISTRICT in a "
                "certificated-employee layoff hearing (Education Code 44949/44955). " + _OFFICER)
RESP_SYS = ("You are experienced counsel for the RESPONDENT (the certificated "
            "employee/teacher) in a California layoff hearing (Education Code "
            "44949/44955). " + _OFFICER)
JUDGE_SYS = ("You are a neutral, rigorous Administrative Law Judge deciding a California "
             "certificated-employee layoff (Education Code 44949/44955). You weigh both "
             "parties' arguments against the facts and the cited holdings and reach a "
             "clear, well-grounded conclusion on the issue.")


def _facts(matter):
    return matter["matter_text"]


def _advocate_prompt(side, matter, issue, ev):
    who = ("the DISTRICT should prevail (its layoff/release/action on this issue should "
           "STAND)" if side == "district" else
           "the RESPONDENT (employee) should prevail (the District's action on this issue "
           "should NOT stand / the employee should be retained)")
    return (f"ISSUE: {issue}\n\nMATTER FACTS:\n{_facts(matter)}\n\n"
            "ANALOGOUS CORPUS HOLDINGS (with the ALJ's actual reasoning and WHO PREVAILED "
            "— your evidentiary record; the set is balanced district/respondent):\n"
            + _evidence_block(ev) + "\n\n"
            f"Write your POSITION STATEMENT arguing that {who}. Ground every argument in "
            "these facts and the holdings above: cite and QUOTE the holdings (District "
            "(ALJ), year) that support your client, and distinguish the ones that cut "
            "against you. Be specific and persuasive.\n\n"
            "CITATION RULE (strict): You may cite ONLY (a) the holdings listed above, by "
            "their 'District (ALJ), year' tag, and (b) the Education Code sections at issue "
            "(e.g. 44949, 44955). Do NOT name or cite ANY other case — no 'Name v. Name' "
            "citations, no outside or remembered authority. Inventing or half-remembering a "
            "case is worse than citing none; if you lack support, argue from the facts and "
            "the listed holdings only.")


def _judge_prompt(matter, issue, ev, dbrief, rbrief):
    return (f"ISSUE: {issue}\n\nMATTER FACTS:\n{_facts(matter)}\n\n"
            "ANALOGOUS CORPUS HOLDINGS (the record, with real outcomes):\n"
            + _evidence_block(ev) + "\n\n"
            f"=== DISTRICT'S POSITION ===\n{dbrief}\n\n"
            f"=== RESPONDENT'S POSITION ===\n{rbrief}\n\n"
            "Write your DECISION on this issue. Weigh both sides' arguments against the "
            "facts and the cited holdings; state the operative legal distinction the issue "
            "turns on; and conclude clearly WHO PREVAILS — does the District's action on "
            "this issue STAND, or does the employee prevail — and why. You may correct a "
            "point both parties missed, but stay grounded in the record and the authorities "
            "presented; cite the holdings (District (ALJ), year) you rely on.")


def _judge_anchored_prompt(matter, issue, ev, dbrief, rbrief, anchor):
    """v3 judge: anchored to a closed-book prediction (the base's strong prior) + base
    rate, so a persuasive brief can't flip an already-correct direction."""
    return (f"ISSUE: {issue}\n\nMATTER FACTS:\n{_facts(matter)}\n\n"
            "ANALOGOUS CORPUS HOLDINGS (the record, with real outcomes):\n"
            + _evidence_block(ev) + "\n\n"
            "=== YOUR PRELIMINARY READ (closed-book, before briefing — your own strong prior "
            "on the law, which is correct in the large majority of cases) ===\n"
            f"{anchor}\n\n"
            f"=== DISTRICT'S POSITION ===\n{dbrief}\n\n"
            f"=== RESPONDENT'S POSITION ===\n{rbrief}\n\n"
            "Write your DECISION on this issue. START from your preliminary read and the "
            "fact that, in this area, the DISTRICT's action is upheld in roughly three out "
            "of four cases — do NOT overturn it lightly. Change direction from your "
            "preliminary read ONLY if a party's argument is CLEARLY compelled by the FACTS "
            "and a closely-analogous holding in the record (a merely persuasive or "
            "well-written brief is not enough). Weigh both briefs critically against the "
            "facts and the cited holdings; state the operative distinction; conclude clearly "
            "WHO PREVAILS — does the District's action STAND — and why. Cite only the "
            "holdings (District (ALJ), year) in the record.")


def make_adversarial_arm(backend, k=8, num_predict=4000, anchors=None):
    """arm_fn(matter, issues) -> per_issue {district_brief, respondent_brief, opinion,...}.

    anchors: optional {(matter_id, issue): closed_book_analysis}. When provided, the JUDGE
    is anchored to that closed-book prediction + base rate (v3 fix for the v2 respondent-lean).
    """
    opts = {"temperature": 0.4, "num_predict": num_predict}      # a bit warmer for advocacy

    def arm_fn(matter, issues):
        out, t0 = [], time.time()
        excl = set(matter.get("exclude_ids") or [])
        for iss in issues:
            ev = retrieve(matter, iss, excl, k=k, balanced=True)
            anchor = (anchors or {}).get((matter["matter_id"], iss))
            try:
                dbrief = generate(backend, _advocate_prompt("district", matter, iss, ev),
                                  system=DISTRICT_SYS, think=False, options=opts)
                rbrief = generate(backend, _advocate_prompt("respondent", matter, iss, ev),
                                  system=RESP_SYS, think=False, options=opts)
                jp = (_judge_anchored_prompt(matter, iss, ev, dbrief, rbrief, anchor)
                      if anchor else _judge_prompt(matter, iss, ev, dbrief, rbrief))
                opinion = generate(backend, jp, system=JUDGE_SYS, think=False, options=opts)
            except Exception as e:
                dbrief = rbrief = opinion = f"(error: {str(e)[:80]})"
            out.append({"issue": iss, "district_brief": dbrief, "respondent_brief": rbrief,
                        "opinion": opinion,
                        "cited_holding_ids": [h["hid"] for h in ev], "n_evidence": len(ev)})
        return {"per_issue": out, "_cost": {"wall_clock_s": round(time.time() - t0, 1)}}

    arm_fn.backend = backend
    return arm_fn
