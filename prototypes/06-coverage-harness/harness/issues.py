"""The canonical issue ontology an arm spots against — normalized (PKS collapsed)
to match the breadth answer key. One-line definitions so a model that has never
seen the taxonomy can map facts to categories fairly.
"""

# Order roughly by frequency/centrality; definitions are the operative trigger,
# not legal exhaustive. Keys MUST match harness.corpus.norm_cat output.
ISSUE_DEFS = {
    "skipping": "retaining a JUNIOR employee out of seniority order because the district needs their special training, experience, or credential (Ed. Code 44955(d)(1)).",
    "bumping": "a SENIOR employee displacing a junior one whose position the senior is certificated AND competent to fill.",
    "seniority": "seniority date / order — first date of paid probationary service, ties in date, how the seniority list is built.",
    "competency": "the STANDARD for 'competent' to serve a position — how the district defined it and whether it was applied properly.",
    "tie_breaking": "resolving employees with the SAME seniority date — the tie-break criteria, lotteries, and the 'needs of the district and students'.",
    "pks_reduction": "whether a reduction of 'particular kinds of service' (PKS) is proper/necessary (budget, program elimination, declining need).",
    "procedural_issues": "notice/timing/jurisdiction defects — the March 15 deadline, service of the accusation, board-resolution specificity, hearing rights.",
    "attrition": "whether retirements/resignations/leaves ('positively assured attrition') offset the need to lay off the noticed number.",
    "calculations_ada_fte": "ADA / FTE / enrollment math — how positions and full-time-equivalents are counted and projected.",
    "temporary_employees": "classification as TEMPORARY vs probationary/permanent, and whether temporaries must be released first.",
    "assignments_reassignments": "reassignment to another position, whether a position is full-time, how assignments bear on who is laid off.",
    "credentials": "credential validity/scope — whether an employee actually holds a credential authorizing a given position.",
    "categorically_funded": "layoff tied to categorically / specially funded programs and the lapse of that funding.",
    "domino_theory": "chain/cascade effects of bumping and reassignment rippling through the seniority list.",
    "reemployment_rights": "reappointment / reemployment preference rights (the 39-month list) of laid-off employees.",
    "substitutes": "the status and rights of substitute employees in the layoff.",
    "discrimination": "discrimination or retaliation in how employees were selected for layoff.",
    "eera_cba_aa": "interaction of EERA, the collective-bargaining agreement, or affirmative-action obligations with the layoff.",
    "contractual_issues": "contract-based claims (beyond the CBA) affecting the layoff.",
    "county_office_issues": "layoff issues specific to a county office of education.",
    "adult_education": "layoff issues specific to adult-education programs.",
    "miscellaneous": "a genuine layoff issue that fits none of the above categories.",
}

CANONICAL_ISSUES = list(ISSUE_DEFS)   # 22 normalized categories


def issue_menu():
    """Render the menu for a prompt."""
    return "\n".join(f"- {c}: {d}" for c, d in ISSUE_DEFS.items())
