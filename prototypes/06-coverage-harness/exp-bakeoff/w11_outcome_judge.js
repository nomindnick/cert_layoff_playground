export const meta = {
  name: 'w11-outcome-judge',
  description: 'Domain-aware bottom-line outcome extraction (does the district action STAND?) — the winner-inference confound fix.',
  phases: [ { title: 'Extract', detail: 'one agent per analysis' } ],
}
// args: { input_path: "<abs outcome.<name>.input.json>", codes: ["O001", ...] }
const A = typeof args === 'string' ? JSON.parse(args) : args
const INPUT = A.input_path
const CODES = A.codes

// The anti-inversion domain rules. The OLD metric's confound: a judge reads
// "the employee is probationary" and mis-maps it to a respondent win, when
// probationary status actually lets the district lay her off (district win).
// These rules pin the mapping from legal conclusion -> bottom line.
const RULES = `BOTTOM LINE = does the DISTRICT'S action against the affected employee on THIS issue STAND?
- "district" = the district's action (layoff / release / non-retention / its seniority list / its PKS reduction / its notice) is UPHELD on this issue.
- "respondent" = the employee prevails on this issue: the action is OVERTURNED, the employee is retained/reinstated, the accusation is dismissed, or the district's position is rejected.

MAP THE LEGAL CONCLUSION CORRECTLY (these are the inversions to avoid):
- Employee found PROBATIONARY or TEMPORARY (not permanent) => the district MAY lay off / release them => tends DISTRICT. (Do NOT read "probationary" as employee-favorable.)
- Employee found PERMANENT and thereby protected/retained (seniority or bumping rights entitle them to a remaining position) => tends RESPONDENT.
- District's "skipping"/retention of a junior employee for a special credential UPHELD => DISTRICT; found improper => RESPONDENT.
- Board's PKS (particular-kinds-of-service) reduction UPHELD => DISTRICT; reduction found improper/unsupported => RESPONDENT.
- Procedural/notice defect found to INVALIDATE the layoff as to this employee => RESPONDENT; defect deemed technical/non-prejudicial => DISTRICT.
- Seniority date / tie-break resolved in the district's favor (list stands) => DISTRICT; employee shows an error entitling them to retention => RESPONDENT.
Judge by the analysis's BOTTOM-LINE CONCLUSION on this issue, not by which side's facts sound sympathetic.`

const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    code: { type: 'string' },
    district_action: { type: 'string', description: 'the district action at stake on this issue, one phrase' },
    predicted: { type: 'string', enum: ['district', 'respondent', 'unclear'] },
    rationale: { type: 'string' },
  },
  required: ['code', 'predicted', 'rationale'],
}

const prompt = (code) => `You are a California certificated-layoff (Education Code 44949/44955) expert extracting the BOTTOM-LINE conclusion of a candidate legal ANALYSIS of ONE issue. You are NOT judging whether the analysis is right — only WHICH WAY it concludes.

${RULES}

Load your item (code = "${code}"):
  python3 -c "import json;d=json.load(open('${INPUT}'));print(json.dumps([x for x in d if x['code']=='${code}'][0],indent=1))"

It has: issue; analysis (the candidate; it may hedge or discuss both sides — extract the direction it ultimately predicts/recommends for THIS issue).

Return: code ("${code}"); district_action (the action at stake, one phrase); predicted ∈ {district, respondent, unclear} per the rules above (use "unclear" ONLY if the analysis genuinely reaches no bottom line on this issue); one-line rationale naming the operative conclusion you mapped.`

const scored = await parallel(CODES.map((code) => () =>
  agent(prompt(code), { label: `outcome:${code}`, phase: 'Extract', schema: SCHEMA })
    .then((s) => (s ? s : { code, predicted: null, rationale: 'failed' }))))

const ok = scored.filter((s) => s && s.predicted !== null)
log(`extracted ${ok.length}/${CODES.length}`)
return { n: ok.length, scored }
