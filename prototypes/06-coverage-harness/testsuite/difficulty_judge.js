export const meta = {
  name: 'difficulty-rater',
  description: 'Blind difficulty rating (1-5) + frontier closed-book prediction for the test suite — the outcome is hidden from the judge.',
  phases: [ { title: 'Rate', detail: 'one agent per matter-issue' } ],
}
// args: { input_path: "<abs difficulty.input.json>", codes: ["D001", ...] }
const A = typeof args === 'string' ? JSON.parse(args) : args
const INPUT = A.input_path
const CODES = A.codes

const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    code: { type: 'string' },
    predicted: { type: 'string', enum: ['district', 'respondent', 'unclear'] },
    difficulty: { type: 'integer', enum: [1, 2, 3, 4, 5] },
    rationale: { type: 'string' },
  },
  required: ['code', 'predicted', 'difficulty', 'rationale'],
}

const prompt = (code) => `You are a California certificated-layoff (Education Code 44949/44955) expert. You are given a de-identified FACT PATTERN and ONE issue it raises. The ACTUAL OUTCOME IS HIDDEN from you. From the facts alone, do two things:

1) PREDICT the bottom line on THIS issue — does the DISTRICT's action stand ("district": layoff/skip/PKS/seniority-list/notice upheld) or does the EMPLOYEE prevail ("respondent": overturned / retained / reinstated / accusation dismissed)? Use "unclear" only if the facts genuinely don't determine it.
2) RATE how HARD this issue is to call from these facts: 1 = easy/obvious (a competent layoff attorney would be confident), 3 = moderate, 5 = very hard (genuinely close, the facts cut both ways, reasonable experts could split / coin-flip).

Load your item (code = "${code}"):
  python3 -c "import json;d=json.load(open('${INPUT}'));print(json.dumps([x for x in d if x['code']=='${code}'][0],indent=1))"

It has: issue; matter_text (the de-identified facts — names are roles like R1/[name]; do not penalize that). Judge difficulty by the FACTS' determinacy, not your unfamiliarity. Return code ("${code}"), predicted, difficulty (1-5), and a one-line rationale naming what makes it easy or hard.`

const scored = await parallel(CODES.map((code) => () =>
  agent(prompt(code), { label: `diff:${code}`, phase: 'Rate', schema: SCHEMA })
    .then((s) => (s ? s : { code, predicted: null, difficulty: null, rationale: 'failed' }))))

const ok = scored.filter((s) => s && s.difficulty !== null)
log(`rated ${ok.length}/${CODES.length}`)
return { n: ok.length, scored }
