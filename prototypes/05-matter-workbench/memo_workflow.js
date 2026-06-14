export const meta = {
  name: 'matter-risk-memo',
  description: 'P1: synthesize an issue-by-issue risk memo per matter over the deterministic evidence packs, then verify grounding, judge usefulness (subagent panel), and test discriminability',
  phases: [
    { title: 'Synthesize', detail: 'one agent per matter: evidence pack -> grounded risk memo' },
    { title: 'Verify', detail: 'independent re-query: grounding% + legal-characterization flags' },
    { title: 'Usefulness', detail: '2 independent judges per memo (litigator + skeptic lenses)' },
    { title: 'Discriminate', detail: 'blind match: anonymized memo -> its own matter fingerprint' },
  ],
}

const A = typeof args === 'string' ? JSON.parse(args) : args
const matters = A.matters
const TOOL = '/home/nick/Projects/cert_layoff_playground/prototypes/01-search-mcp/.venv/bin/python /home/nick/Projects/cert_layoff_playground/prototypes/04-deep-research/research_tool.py'
const MEMO_DIR = '/home/nick/Projects/cert_layoff_playground/prototypes/05-matter-workbench/output/memos'

const SYNTH_SCHEMA = {
  type: 'object',
  properties: {
    memo: { type: 'string' },
    claims: { type: 'array', items: { type: 'object', properties: {
      text: { type: 'string' },
      cite: { type: 'string', description: 'District (ALJ), year — from the evidence pack' },
      holding_id: { type: 'string' },
      type: { type: 'string', enum: ['risk', 'respondent_argument', 'precedent', 'recommendation', 'legal_characterization'] },
      hedged: { type: 'boolean' },
    }, required: ['text', 'cite', 'type', 'hedged'] } },
  },
  required: ['memo', 'claims'],
}

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, grounded: { type: 'boolean' }, note: { type: 'string' },
    }, required: ['claim', 'grounded', 'note'] } },
    grounded_pct: { type: 'number' },
    characterization_flags: { type: 'array', items: { type: 'string' }, description: 'legal characterizations a human attorney must check (W9 failure mode)' },
    overreach: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
  required: ['verdicts', 'grounded_pct', 'characterization_flags', 'overreach', 'summary'],
}

const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    exposure_coverage: { type: 'number', description: '1-5: did it surface the real exposures in this matter?' },
    respondent_args: { type: 'number', description: '1-5: quality/specificity of "what respondents will argue"' },
    actionability: { type: 'number', description: '1-5: could a district attorney act on it?' },
    honesty: { type: 'number', description: '1-5: appropriately hedged, flags thin areas/characterizations?' },
    overall: { type: 'number', description: '1-5' },
    missing: { type: 'array', items: { type: 'string' } },
    wrong_or_generic: { type: 'array', items: { type: 'string' } },
    verdict: { type: 'string' },
  },
  required: ['exposure_coverage', 'respondent_args', 'actionability', 'honesty', 'overall', 'missing', 'wrong_or_generic', 'verdict'],
}

const CHOICE_SCHEMA = {
  type: 'object',
  properties: { choice: { type: 'string', enum: ['A', 'B'] }, confidence: { type: 'number' }, reason: { type: 'string' } },
  required: ['choice', 'confidence', 'reason'],
}

const synthPrompt = (m) => `You are a California school-district attorney's research associate. Write an issue-by-issue RISK MEMO for a live certificated-employee layoff (Education Code 44949/44955).

THE MATTER: read ${m.matter_path}
THE EVIDENCE (de-identified holdings retrieved for each issue in this matter, with arguments-by-party, outcomes, and — if an ALJ is assigned — that ALJ's tendencies): read ${m.evidence_path}

Write the memo in markdown:
  ## Overall risk summary   (3-5 sentences: where is this district most exposed?)
  ## <one section per issue in the evidence pack>
     For each issue: the **exposure** for THIS matter; **what respondents will likely argue** (drawn from the analogous holdings' respondent arguments); **how it has tended to land** (from the retrieved outcomes — give counts honestly, note when thin); **what to shore up**.
  ## What to verify   (legal characterizations and thin spots a human attorney must check)

HARD RULES (these are the experiment):
- Every assertion must cite a holding FROM THE EVIDENCE PACK — inline as "District (ALJ), year" with the holding id. Do NOT invent holdings, cites, or outcomes, and do NOT pull in outside knowledge of education law as if it were corpus-grounded.
- If the evidence for an issue is thin (few holdings, only one year), SAY SO; do not manufacture confidence.
- If an ALJ is assigned, use the tendency block but OBEY its significance labels (e.g. "win-rate not distinguishable from base" means do NOT claim an outcome lean).
- Tie every "what respondents will argue" to a real respondent argument in the evidence.
- PRIVACY: cite District (ALJ) only. Never output a personal name (a retained junior teacher, a witness). If a snippet contains one, refer to "a junior teacher"/"the senior respondent".
- Flag legal characterizations explicitly in the "What to verify" section — the known failure mode is a confident mis-statement of a rule sitting on top of a correct citation.

Save the memo to ${MEMO_DIR}/${m.id}.md (create the dir if needed) with the Write tool.

Return JSON: the "memo" markdown, and "claims" — every discrete assertion with its "cite", "holding_id", "type", and whether you "hedged" it.`

const verifyPrompt = (m, claims) => `You are an adversarial verifier for a layoff risk memo about a matter ("${m.id}"). Be skeptical — catch ungrounded claims and, especially, confident mis-statements of law sitting on a correct citation (the known failure mode of this system).

The evidence pack the memo was built from: ${m.evidence_path} (read it).
You may also independently re-query the full corpus:
  ${TOOL} search "<query>" --collection gold_holdings|holdings [-k N]
  ${TOOL} holding <case:idx>

THE CLAIMS:
${JSON.stringify(claims, null, 1)}

For each claim: grounded = does the cited holding exist in the evidence pack (or corpus) and actually support the assertion? Mark false if the cite is wrong, the holding doesn't say it, the outcome is misreported, or the claim generalizes beyond the evidence. Separately, list characterization_flags: any statement of a legal RULE that an attorney should double-check (even if a cite is attached). List overreach claims.

Return JSON: verdicts [{claim, grounded, note}], grounded_pct (0-100), characterization_flags, overreach, summary.`

const judgePrompt = (m, memo, lens) => {
  const persona = lens === 'litigator'
    ? 'You are a seasoned district-side layoff litigator. Judge whether this memo would actually help you prepare THIS matter: does it spot the real exposures, anticipate the respondent arguments you would actually face, and tell you what to shore up before the board acts?'
    : 'You are a skeptical senior partner reviewing a junior\'s work. Judge harshly whether anything is generic boilerplate (true of any layoff), missing, or legally off — and whether the memo earns its length over just reading the cases.'
  return `${persona}

THE MATTER: read ${m.matter_path}
THE MEMO:
${memo}

Score 1-5 (5 best) on: exposure_coverage, respondent_args (quality/specificity of the predicted respondent arguments), actionability, honesty (appropriate hedging / flags thin areas), and overall. List what's missing and anything wrong_or_generic. One-line verdict. Be discriminating — do not give 5s by default.`
}

// ---- phases 1+2: synth -> verify, pipelined ----
const results = await pipeline(
  matters,
  (m) => agent(synthPrompt(m), { label: `synth:${m.id}`, phase: 'Synthesize', schema: SYNTH_SCHEMA }),
  (synth, m) => {
    if (!synth) return null
    return agent(verifyPrompt(m, synth.claims), { label: `verify:${m.id}`, phase: 'Verify', schema: VERIFY_SCHEMA })
      .then((v) => ({ m, memo: synth.memo, claims: synth.claims, verify: v }))
  }
)
const ok = results.filter(Boolean).filter((r) => r.verify)
log(`synthesized+verified ${ok.length}/${matters.length} memos`)

// ---- phase 3: usefulness judge panel (2 lenses per memo) ----
const judged = await parallel(
  ok.flatMap((r) => ['litigator', 'skeptic'].map((lens) => () =>
    agent(judgePrompt(r.m, r.memo, lens), { label: `judge:${r.m.id}:${lens}`, phase: 'Usefulness', schema: JUDGE_SCHEMA })
      .then((s) => (s ? { id: r.m.id, lens, score: s } : null))
  ))
)
const panel = judged.filter(Boolean)

// ---- phase 4: discriminability (anonymized memo -> its fingerprint) ----
function anon(text, m) {
  let t = text.split(m.district).join('the District')
  if (m.alj) t = t.replace(new RegExp('\\b' + m.alj + '\\b', 'g'), '[ALJ]')
  return t
}
const present = ok.map((r) => r.m.id)
const fpById = Object.fromEntries(matters.map((m) => [m.id, m.fingerprint]))
const trials = ok.map((r, i) => {
  const decoyId = present[(i + 1) % present.length]
  const correctIsA = i % 2 === 0
  return {
    id: r.m.id,
    memo: anon(r.memo, r.m),
    correct: correctIsA ? 'A' : 'B',
    A: correctIsA ? fpById[r.m.id] : fpById[decoyId],
    B: correctIsA ? fpById[decoyId] : fpById[r.m.id],
  }
})
const choices = await parallel(trials.map((t) => () =>
  agent(
    `A layoff risk memo (district & ALJ names redacted) is below. Two matter fingerprints follow; exactly one is the matter this memo was written for. Which?\n\n=== MEMO ===\n${t.memo}\n\n=== FINGERPRINT A ===\n${t.A}\n\n=== FINGERPRINT B ===\n${t.B}\n\nAnswer A or B, confidence 0-1, one-line reason from specific issue/fact overlap.`,
    { label: `discriminate:${t.id}`, phase: 'Discriminate', schema: CHOICE_SCHEMA }
  ).then((c) => (c ? { id: t.id, correct: c.choice === t.correct, confidence: c.confidence } : null))
))
const dc = choices.filter(Boolean)

// ---- aggregate ----
const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0)
const byMatter = ok.map((r) => {
  const ps = panel.filter((p) => p.id === r.m.id).map((p) => p.score)
  return {
    id: r.m.id,
    n_claims: r.claims.length,
    grounded_pct: r.verify.grounded_pct,
    characterization_flags: r.verify.characterization_flags.length,
    overreach: r.verify.overreach.length,
    verify_summary: r.verify.summary,
    usefulness: {
      exposure: +mean(ps.map((s) => s.exposure_coverage)).toFixed(1),
      respondent_args: +mean(ps.map((s) => s.respondent_args)).toFixed(1),
      actionability: +mean(ps.map((s) => s.actionability)).toFixed(1),
      honesty: +mean(ps.map((s) => s.honesty)).toFixed(1),
      overall: +mean(ps.map((s) => s.overall)).toFixed(1),
      missing: ps.flatMap((s) => s.missing),
      wrong_or_generic: ps.flatMap((s) => s.wrong_or_generic),
    },
  }
})

return {
  n_memos: ok.length,
  mean_grounded_pct: +mean(byMatter.map((b) => b.grounded_pct)).toFixed(1),
  mean_usefulness_overall: +mean(byMatter.map((b) => b.usefulness.overall)).toFixed(2),
  discriminability: { n: dc.length, correct: dc.filter((c) => c.correct).length },
  per_matter: byMatter,
}
