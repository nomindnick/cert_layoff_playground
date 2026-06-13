export const meta = {
  name: 'corpus-deep-research',
  description: 'W9 stage 1: run the agentic retrieve->read->synthesize loop over the layoff corpus on hard questions, then adversarially verify grounding/insight',
  phases: [
    { title: 'Research', detail: 'one harness instance per question: query corpus -> grounded memo' },
    { title: 'Verify', detail: 'independent re-query: is every claim grounded, is the insight real or overreach?' },
  ],
}

const TOOL = '/home/nick/Projects/cert_layoff_playground/prototypes/01-search-mcp/.venv/bin/python /home/nick/Projects/cert_layoff_playground/prototypes/04-deep-research/research_tool.py'

const QUESTIONS = [
  {
    id: 'Q2-argument-efficacy',
    q: 'Against a district\'s §44955(d)(1) "skip" (retaining a junior employee for special training/experience), what RESPONDENT arguments actually succeed, and what reliably loses? Give the winning pattern and the losing pattern, each with cited holdings and, where possible, the ALJ\'s stated reason.',
  },
  {
    id: 'Q3-procedural-exposure',
    q: 'What recurring PROCEDURAL defects have gotten districts\' layoffs partially rescinded or notices invalidated (e.g. the March-15 board/employee notice deadline, service defects, board-resolution specificity, ADA/FTE miscalculation)? For each, say whether the corpus treats it as FATAL (rescission) or CURABLE/excused (no prejudice), with cited holdings across eras.',
  },
  {
    id: 'Q4-tiebreaker-doctrine',
    q: 'How does the corpus treat lottery / random tie-breakers and the requirement that tie-breaking serve the "needs of the district and the students"? When is a lottery UPHELD vs STRUCK DOWN, and is there any evolution or tension across ALJs/years? Cite holdings.',
  },
]

const researchPrompt = (item) => `You are a legal research agent with tool access to a corpus of California OAH teacher-layoff decisions (Education Code 44949/44955): 267 richly-structured decisions from 2004 & 2009, plus 3,900+ expert-written summary holdings spanning 1979-2015. Answer this question by actually querying the corpus — do NOT answer from prior knowledge of California education law:

QUESTION: ${item.q}

YOUR TOOL (run from any directory; use absolute paths as given):
  ${TOOL} search "<query>" --collection gold_holdings|holdings|decisions [--year Y] [--category C] [--alj A] [--prevailing-party district|respondent] [-k N]
  ${TOOL} holding <case:idx>     # full structured holding: issue, ruling, arguments by party, facts, authorities, reasoning
  ${TOOL} facets <collection>    # available years / categories
Canonical categories include: skipping, bumping, seniority, competency, procedural_issues, tie_breaking, pks_allowed, attrition, tie_breaking.
'gold_holdings' is the 35-year longitudinal source (editorial, not exhaustive); 'holdings' is the 2004/2009 structured source (has prevailing_party + arguments). Use BOTH where relevant.

METHOD: run several searches (vary phrasing, collections, eras), then READ a few full holdings to get the ALJ's actual reasoning before you generalize. Aim for ~6-12 tool calls.

HARD RULES:
- Every assertion in your memo must be backed by a holding you actually retrieved. Cite inline in "District (ALJ)" form with the year, and keep the holding id.
- PRIVACY: cite by District (ALJ) only. If a retrieved snippet contains a person's name (e.g. a retained junior teacher), do NOT reproduce it — refer to "a junior teacher" / "the senior respondent". Never output a personal name.
- Be honest about limits: the structured outcome data is only 2 years; gold is editorial. Flag where the evidence is thin.
- Distinguish what's genuinely non-obvious from what any layoff lawyer already knows.

Return JSON:
- memo: the markdown research memo (with an opening "Answer in one paragraph", then the winning/losing or fatal/curable breakdown with inline cites).
- claims: every discrete factual assertion, each with its supporting "cite" (District (ALJ), year), the "holding_ids" you read, and a one-line "basis".
- insight_rating: one of "novel_nonobvious" | "known_but_now_evidenced" | "shallow_or_obvious".
- data_limits: one or two sentences.
- queries_run: integer count of tool calls you made.`

const verifyPrompt = (item, research) => `You are an adversarial verifier. A research agent answered a question about the California teacher-layoff corpus and you must independently check it against the same corpus — be skeptical, your job is to catch ungrounded claims and overreach.

QUESTION: ${item.q}

THE AGENT'S CLAIMS:
${JSON.stringify(research.claims, null, 1)}

THE AGENT'S MEMO:
${research.memo}

YOUR TOOL (independently re-query — do not trust the agent's cites blindly):
  ${TOOL} search "<query>" --collection gold_holdings|holdings|decisions [--year Y] [--category C] [-k N]
  ${TOOL} holding <case:idx>

For a representative sample of the claims (especially the load-bearing ones and any that sound too clean), verify: does the cited holding actually exist and actually support the claim? Mark grounded=false if the cite is wrong, the holding doesn't say it, or the claim generalizes beyond what the evidence supports. Then judge the memo's HEADLINE insight: is it genuinely grounded and non-obvious, grounded but something any practitioner knows, partly overreach, or shallow?

Return JSON:
- verdicts: [{claim, grounded (bool), note}]
- grounded_pct: 0-100 over the claims you checked
- overreach: list of any specific claims that overreach the evidence (may be empty)
- insight_verdict: "grounded_nonobvious" | "grounded_but_known" | "partly_overreach" | "shallow"
- summary: one or two sentences.`

const RESEARCH_SCHEMA = {
  type: 'object',
  properties: {
    memo: { type: 'string' },
    claims: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, cite: { type: 'string' },
      holding_ids: { type: 'array', items: { type: 'string' } }, basis: { type: 'string' },
    }, required: ['claim', 'cite', 'basis'] } },
    insight_rating: { type: 'string', enum: ['novel_nonobvious', 'known_but_now_evidenced', 'shallow_or_obvious'] },
    data_limits: { type: 'string' },
    queries_run: { type: 'number' },
  },
  required: ['memo', 'claims', 'insight_rating', 'data_limits', 'queries_run'],
}

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, grounded: { type: 'boolean' }, note: { type: 'string' },
    }, required: ['claim', 'grounded', 'note'] } },
    grounded_pct: { type: 'number' },
    overreach: { type: 'array', items: { type: 'string' } },
    insight_verdict: { type: 'string', enum: ['grounded_nonobvious', 'grounded_but_known', 'partly_overreach', 'shallow'] },
    summary: { type: 'string' },
  },
  required: ['verdicts', 'grounded_pct', 'overreach', 'insight_verdict', 'summary'],
}

const results = await pipeline(
  QUESTIONS,
  (item) => agent(researchPrompt(item), { label: `research:${item.id}`, phase: 'Research', schema: RESEARCH_SCHEMA }),
  (research, item) => {
    if (!research) return null
    return agent(verifyPrompt(item, research), { label: `verify:${item.id}`, phase: 'Verify', schema: VERIFY_SCHEMA })
      .then((v) => ({ id: item.id, question: item.q, research, verify: v }))
  }
)

const ok = results.filter(Boolean).filter((r) => r.verify)
log(`completed ${ok.length}/${QUESTIONS.length} research+verify cycles`)

return {
  n: ok.length,
  per_question: ok.map((r) => ({
    id: r.id,
    n_claims: r.research.claims.length,
    queries_run: r.research.queries_run,
    insight_self: r.research.insight_rating,
    grounded_pct: r.verify.grounded_pct,
    insight_verdict: r.verify.insight_verdict,
    overreach_count: r.verify.overreach.length,
    verify_summary: r.verify.summary,
    data_limits: r.research.data_limits,
    memo: r.research.memo,
  })),
}
