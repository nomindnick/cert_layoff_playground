export const meta = {
  name: 'cite-faithfulness-judge',
  description: 'Per-cite faithfulness: does the analysis use of a RESOLVED corpus cite represent what the holding actually held, or mischaracterize/INVERT it (laundered confabulation)?',
  phases: [ { title: 'Judge', detail: 'one agent per (analysis, cite)' } ],
}
// args: { input_path: "<abs faith.<name>.input.json>", codes: ["F0001", ...] }
const A = typeof args === 'string' ? JSON.parse(args) : args
const INPUT = A.input_path
const CODES = A.codes

const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    code: { type: 'string' },
    verdict: { type: 'string', enum: ['faithful', 'tangential', 'unfaithful'] },
    used_for: { type: 'string', description: 'the proposition the analysis attributes to this cite, one phrase' },
    rationale: { type: 'string' },
  },
  required: ['code', 'verdict', 'rationale'],
}

const prompt = (code) => `You are a California certificated-layoff (Ed. Code 44949/44955) expert checking whether a candidate ANALYSIS uses a citation FAITHFULLY. You are given the REAL holding(s) the citation resolves to (GROUND TRUTH) and must judge whether the analysis's use of that citation represents what the holding actually held. You are NOT grading the analysis overall — only this one citation's use.

Load your item (code = "${code}"):
  python3 -c "import json;d=json.load(open('${INPUT}'));print(json.dumps([x for x in d if x['code']=='${code}'][0],indent=1))"

It has: cite (the citation string as it appears); analysis (the candidate — find where it uses this cite); candidates[] (the real holding(s) the cite resolves to: category, issue, prevailing_party, holding, reasoning = GROUND TRUTH). If more than one candidate, the cite is ambiguous at (ALJ, year) granularity — judge "faithful" if the use matches ANY candidate.

Verdict:
- "faithful" = the proposition the analysis attributes to this cite matches what the holding actually held, INCLUDING direction (do NOT credit citing a DISTRICT-win holding to support a RESPONDENT conclusion, or vice versa).
- "tangential" = the cite is real and roughly on-topic but does NOT actually support the specific proposition the analysis attaches to it (a decorative cite).
- "unfaithful" = the analysis MISCHARACTERIZES, OVERSTATES, or INVERTS the holding — attributes a proposition the holding does not contain, or flips its direction. The dangerous laundered-confabulation case.

Return code ("${code}"), verdict, used_for (the proposition the analysis attributes to the cite, one phrase), and a one-line rationale naming the match or the mismatch.`

const scored = await parallel(CODES.map((code) => () =>
  agent(prompt(code), { label: `faith:${code}`, phase: 'Judge', schema: SCHEMA })
    .then((s) => (s ? s : { code, verdict: null, rationale: 'failed' }))))

const ok = scored.filter((s) => s && s.verdict !== null)
log(`judged ${ok.length}/${CODES.length}`)
return { n: ok.length, scored }
