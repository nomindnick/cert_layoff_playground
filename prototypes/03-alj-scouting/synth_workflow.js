export const meta = {
  name: 'alj-scouting-synth',
  description: 'Synthesize per-ALJ scouting reports from dossiers, then adversarially verify grounding/horoscope and test discriminability',
  phases: [
    { title: 'Synthesize', detail: 'one agent per ALJ: dossier -> grounded narrative report' },
    { title: 'Verify', detail: 'adversarial grounding + horoscope check per report' },
    { title: 'Discriminate', detail: 'forced-choice: match anonymized report to its statistical fingerprint' },
  ],
}

const A = typeof args === 'string' ? JSON.parse(args) : args
const { dossier_dir, aljs, fingerprints } = A

const SYNTH_SCHEMA = {
  type: 'object',
  properties: {
    report: { type: 'string', description: 'the full markdown scouting report' },
    claims: {
      type: 'array',
      description: 'every discrete tendency assertion the report makes',
      items: {
        type: 'object',
        properties: {
          text: { type: 'string' },
          evidence: { type: 'string', description: 'the dossier field / cite it rests on' },
          hedged: { type: 'boolean', description: 'true if the report explicitly hedged it as thin/uncertain' },
        },
        required: ['text', 'evidence', 'hedged'],
      },
    },
  },
  required: ['report', 'claims'],
}

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          grounded: { type: 'boolean', description: 'traces to a specific dossier fact/cite' },
          specific: { type: 'boolean', description: 'ALJ-specific, NOT a generic statement true of any layoff ALJ' },
          note: { type: 'string' },
        },
        required: ['claim', 'grounded', 'specific', 'note'],
      },
    },
    grounded_pct: { type: 'number' },
    specific_pct: { type: 'number' },
    summary: { type: 'string' },
  },
  required: ['verdicts', 'grounded_pct', 'specific_pct', 'summary'],
}

const CHOICE_SCHEMA = {
  type: 'object',
  properties: {
    choice: { type: 'string', enum: ['A', 'B'] },
    confidence: { type: 'number' },
    reason: { type: 'string' },
  },
  required: ['choice', 'confidence', 'reason'],
}

const synthPrompt = (alj) => `You are writing an ALJ scouting report for a California school-district attorney who is about to appear before Administrative Law Judge ${alj} in a certificated-employee layoff hearing (Education Code 44949/44955).

Read the dossier of de-identified evidence at: ${dossier_dir}/${alj}.json

It contains: density stats, an outcome block with an "interpretation" hint, an issue footprint (over/under-represented categories vs corpus), procedural posture, authorities, persuasive-argument examples by issue, and verbatim editor observations that name this ALJ (with District (ALJ) cites).

Write a scouting report in markdown with these sections:
  ## Bottom line   (3-4 sentences an attorney can act on)
  ## Outcome tendency
  ## What this ALJ hears a lot of   (issue footprint)
  ## How arguments have landed   (persuasive arguments by issue)
  ## In the editors' words   (the attributed observations)
  ## Watch-outs & data caveats

HARD RULES — this is the whole point of the exercise:
- Every tendency claim MUST trace to a specific fact in the dossier. Cite it inline as the dossier does — "District (${alj})" form, with the year. Do NOT invent cites, numbers, or holdings.
- OBEY the outcome "interpretation" field. If it says the win-rate is not significant / too thin / gold-only, you MUST NOT assert an outcome tendency — say plainly there is none establishable and why.
- Issue footprint is what this ALJ HEARS (docket draw), NOT how they rule. Frame it that way; never imply a docket share is a disposition lean.
- Quote the editor observations rather than paraphrasing their legal substance.
- NEVER include a respondent (teacher) name. The dossier is already de-identified to District (ALJ) cites; keep it that way.
- Be honest about thin data. A short, well-hedged report beats a confident one.

After writing, save the report to ${dossier_dir}/../reports/${alj}.md (create the directory if needed) using the Write tool.

Return JSON: the full "report" markdown, and "claims" — the list of every discrete tendency assertion you made, each with the dossier "evidence" it rests on and whether you "hedged" it.`

const verifyPrompt = (alj, claims) => `You are an adversarial fact-checker for an ALJ scouting report about ALJ ${alj}. Be skeptical: your job is to catch ungrounded or generic claims, not to be agreeable.

The ground-truth dossier is at: ${dossier_dir}/${alj}.json . Read it.

Here are the claims the report made:
${JSON.stringify(claims, null, 1)}

For EACH claim decide two things:
- grounded: does it trace to a SPECIFIC fact, stat, or cite in the dossier? If the dossier does not support it (wrong number, invented cite, asserts an outcome tendency the interpretation field says is not significant), grounded = false. Default to false when unsure.
- specific: is it genuinely ALJ-SPECIFIC, or is it a horoscope — a statement that would be equally true of essentially any layoff ALJ ("applies the 44955 standard", "weighs the evidence carefully")? Generic = specific:false.

Then report grounded_pct and specific_pct (0-100, over all claims) and a one-line summary. Be strict; a claim must clearly earn each "true".`

// ---------- phases 1+2: synthesize then verify, pipelined per ALJ ----------
const results = await pipeline(
  aljs,
  (alj) => agent(synthPrompt(alj), { label: `synth:${alj}`, phase: 'Synthesize', schema: SYNTH_SCHEMA }),
  (synth, alj) => {
    if (!synth) return null
    return agent(verifyPrompt(alj, synth.claims), { label: `verify:${alj}`, phase: 'Verify', schema: VERIFY_SCHEMA })
      .then((v) => ({ alj, report: synth.report, claims: synth.claims, verify: v }))
  }
)

const ok = results.filter(Boolean).filter((r) => r.verify)
log(`synthesized+verified ${ok.length}/${aljs.length} reports`)

// ---------- phase 3: discriminability forced-choice ----------
// mechanically strip the ALJ surname so the judge must rely on substance.
function anon(text, alj) {
  return text.replace(new RegExp('\\b' + alj + '\\b', 'g'), 'the ALJ')
}
const byAlj = Object.fromEntries(ok.map((r) => [r.alj, r]))
const present = ok.map((r) => r.alj)

const trials = present.map((alj, i) => {
  const decoy = present[(i + 3) % present.length]
  const correctIsA = i % 2 === 0
  return {
    alj,
    decoy,
    correct: correctIsA ? 'A' : 'B',
    A: correctIsA ? fingerprints[alj] : fingerprints[decoy],
    B: correctIsA ? fingerprints[decoy] : fingerprints[alj],
  }
})

const choices = await parallel(
  trials.map((t) => () =>
    agent(
      `An ALJ scouting report (ALJ name redacted to "the ALJ") is below. Two statistical fingerprints follow. Exactly one was computed from the same ALJ this report describes. Which one matches?\n\n` +
      `=== REPORT ===\n${anon(byAlj[t.alj].report, t.alj)}\n\n` +
      `=== FINGERPRINT A ===\n${t.A}\n\n=== FINGERPRINT B ===\n${t.B}\n\n` +
      `Answer with the matching fingerprint (A or B), your confidence 0-1, and a one-line reason grounded in specifics (issue mix, span, districts, outcome).`,
      { label: `discriminate:${t.alj}`, phase: 'Discriminate', schema: CHOICE_SCHEMA }
    ).then((c) => (c ? { alj: t.alj, correct: c.choice === t.correct, confidence: c.confidence, reason: c.reason } : null))
  )
)
const dc = choices.filter(Boolean)
const nCorrect = dc.filter((c) => c.correct).length
log(`discriminability: ${nCorrect}/${dc.length} reports correctly matched to their fingerprint (chance = 50%)`)

// ---------- aggregate ----------
const grounded = ok.map((r) => r.verify.grounded_pct)
const specific = ok.map((r) => r.verify.specific_pct)
const mean = (xs) => (xs.length ? Math.round(xs.reduce((a, b) => a + b, 0) / xs.length) : 0)

return {
  n_reports: ok.length,
  mean_grounded_pct: mean(grounded),
  mean_specific_pct: mean(specific),
  per_report: ok.map((r) => ({
    alj: r.alj,
    n_claims: r.claims.length,
    grounded_pct: r.verify.grounded_pct,
    specific_pct: r.verify.specific_pct,
    summary: r.verify.summary,
  })),
  discriminability: {
    n_trials: dc.length,
    n_correct: nCorrect,
    accuracy: dc.length ? Math.round((100 * nCorrect) / dc.length) : 0,
    trials: dc,
  },
}
