export const meta = {
  name: 'p1-synth-bakeoff',
  description: 'Score risk memos written by different synthesizer models (local + Opus baseline) with one fixed Opus-4.8 eval harness: grounding, usefulness, discriminability',
  phases: [{ title: 'Evaluate', detail: 'per memo: verify grounding + 2 usefulness judges + blind matter-match' }],
}

const A = typeof args === 'string' ? JSON.parse(args) : args
const items = A.items
const fps = A.fingerprints
const matterIds = Object.keys(fps)
const TOOL = '/home/nick/Projects/cert_layoff_playground/prototypes/01-search-mcp/.venv/bin/python /home/nick/Projects/cert_layoff_playground/prototypes/04-deep-research/research_tool.py'

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    grounded_pct: { type: 'number', description: '0-100: share of the memo\'s factual/legal assertions that trace to a real holding correctly' },
    n_claims_checked: { type: 'number' },
    invented_cites: { type: 'array', items: { type: 'string' }, description: 'cites/holdings the memo asserts that do NOT exist in the evidence pack or corpus' },
    characterization_flags: { type: 'array', items: { type: 'string' }, description: 'legal rule statements that are wrong or need human check despite a correct cite' },
    overreach: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
  required: ['grounded_pct', 'n_claims_checked', 'invented_cites', 'characterization_flags', 'overreach', 'summary'],
}
const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    exposure_coverage: { type: 'number' }, respondent_args: { type: 'number' },
    actionability: { type: 'number' }, honesty: { type: 'number' }, overall: { type: 'number' },
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

const verifyPrompt = (it) => `You are an adversarial verifier grading a layoff risk memo for GROUNDING. Be skeptical and identify the memo's own failure modes — especially invented holdings and confident mis-statements of law on top of a correct citation.

The memo: read ${it.memo_path}
The evidence pack it was supposed to be built from: read ${it.evidence_path}
You may independently re-query the corpus:  ${TOOL} search "<query>" --collection gold_holdings|holdings [-k N]   |   ${TOOL} holding <case:idx>

Identify the memo's discrete factual/legal assertions (cites, outcomes, rules). For each, check: does the cited holding exist (in the pack or corpus) and actually support the assertion? Count:
- grounded_pct = share of checked assertions that are correctly grounded.
- invented_cites = any holding/cite the memo states that does NOT exist (hallucination — the worst failure).
- characterization_flags = legal rule statements that are wrong, or that a human must check, even though a cite is attached.
- overreach = claims generalizing beyond the evidence.
Be precise; sample the load-bearing claims thoroughly. Return the JSON.`

const judgePrompt = (it, lens) => {
  const persona = lens === 'litigator'
    ? 'You are a seasoned district-side layoff litigator. Judge whether this memo would help you prepare THIS matter: does it spot the real exposures, anticipate the respondent arguments you would face, and say what to shore up?'
    : 'You are a skeptical senior partner reviewing a junior\'s work. Judge harshly: anything generic (true of any layoff), missing, or legally off, and whether it earns its length.'
  return `${persona}

THE MATTER: read ${it.matter_path}
THE MEMO: read ${it.memo_path}

Score 1-5 (5 best): exposure_coverage, respondent_args, actionability, honesty, overall. List missing and wrong_or_generic. One-line verdict. Be discriminating; do not default to 5s. (You are scoring memo quality only — ignore who or what wrote it.)`
}

function discriminatePrompt(it, A_fp, B_fp) {
  return `A layoff risk memo (district & assigned-ALJ names redacted) is below. Two matter fingerprints follow; exactly one is the matter this memo was written for. Which?\n\nRead the memo: ${it.anon_memo_path}\n\n=== FINGERPRINT A ===\n${A_fp}\n\n=== FINGERPRINT B ===\n${B_fp}\n\nAnswer A or B, confidence 0-1, one-line reason from specific issue/fact overlap.`
}

async function evalItem(it, idx) {
  const decoyId = matterIds.find((x) => x !== it.matter_id)
  const correctIsA = idx % 2 === 0
  const Afp = correctIsA ? fps[it.matter_id] : fps[decoyId]
  const Bfp = correctIsA ? fps[decoyId] : fps[it.matter_id]
  const label = `${it.arm}:${it.matter_id}`
  const [verify, jLit, jSkep, choice] = await Promise.all([
    agent(verifyPrompt(it), { label: `verify:${label}`, phase: 'Evaluate', schema: VERIFY_SCHEMA }),
    agent(judgePrompt(it, 'litigator'), { label: `lit:${label}`, phase: 'Evaluate', schema: JUDGE_SCHEMA }),
    agent(judgePrompt(it, 'skeptic'), { label: `skep:${label}`, phase: 'Evaluate', schema: JUDGE_SCHEMA }),
    agent(discriminatePrompt(it, Afp, Bfp), { label: `disc:${label}`, phase: 'Evaluate', schema: CHOICE_SCHEMA }),
  ])
  if (!verify || !jLit || !jSkep) return null
  const u = (k) => (jLit[k] + jSkep[k]) / 2
  return {
    arm: it.arm, matter: it.matter_id,
    grounded_pct: verify.grounded_pct,
    invented: verify.invented_cites.length,
    char_flags: verify.characterization_flags.length,
    overreach: verify.overreach.length,
    verify_summary: verify.summary,
    usefulness: { exposure: u('exposure_coverage'), respondent_args: u('respondent_args'), actionability: u('actionability'), honesty: u('honesty'), overall: u('overall') },
    missing: [...jLit.missing, ...jSkep.missing],
    discriminated: choice ? (choice.choice === (correctIsA ? 'A' : 'B')) : null,
  }
}

const evaluated = (await parallel(items.map((it, i) => () => evalItem(it, i)))).filter(Boolean)
log(`evaluated ${evaluated.length}/${items.length} memos`)

// aggregate by arm
const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0)
const arms = {}
for (const e of evaluated) (arms[e.arm] = arms[e.arm] || []).push(e)
const summary = Object.entries(arms).map(([arm, es]) => ({
  arm,
  n: es.length,
  grounded_pct: +mean(es.map((e) => e.grounded_pct)).toFixed(1),
  invented_total: es.reduce((a, e) => a + e.invented, 0),
  char_flags_total: es.reduce((a, e) => a + e.char_flags, 0),
  usefulness_overall: +mean(es.map((e) => e.usefulness.overall)).toFixed(2),
  exposure: +mean(es.map((e) => e.usefulness.exposure)).toFixed(2),
  respondent_args: +mean(es.map((e) => e.usefulness.respondent_args)).toFixed(2),
  honesty: +mean(es.map((e) => e.usefulness.honesty)).toFixed(2),
  discriminated: `${es.filter((e) => e.discriminated).length}/${es.length}`,
})).sort((a, b) => b.usefulness_overall - a.usefulness_overall)

return { summary, per_memo: evaluated }
