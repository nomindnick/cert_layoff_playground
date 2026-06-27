export const meta = {
  name: 'w11-usefulness-judge',
  description: 'Reference-free usefulness panel (litigator + skeptic lenses, 1-5 dims) over blinded depth analyses.',
  phases: [ { title: 'Judge', detail: 'two lenses per analysis' } ],
}
// args: { input_path: "<abs useful.<name>.input.json>", codes: ["U001", ...] }
const A = typeof args === 'string' ? JSON.parse(args) : args
const INPUT = A.input_path
const CODES = A.codes

const DIMS = `- issue_grasp: does it identify the ACTUAL operative legal distinction/test that governs THIS issue (not a generic recitation)?
- respondent_args: does it engage the employee/respondent's best counter-arguments and the district's real exposure (not just the district-favorable read)?
- actionability: would a practicing district attorney get something CONCRETE to do or verify (specific to these facts), vs boilerplate?
- soundness: is the legal reasoning correct and free of INVERTED or CONFABULATED rules (e.g. getting the direction of a doctrine backwards, or inventing holdings)?
- overall: holistic usefulness of this analysis to a district-side layoff litigator.`

const SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    code: { type: 'string' },
    issue_grasp: { type: 'integer', enum: [1, 2, 3, 4, 5] },
    respondent_args: { type: 'integer', enum: [1, 2, 3, 4, 5] },
    actionability: { type: 'integer', enum: [1, 2, 3, 4, 5] },
    soundness: { type: 'integer', enum: [1, 2, 3, 4, 5] },
    overall: { type: 'integer', enum: [1, 2, 3, 4, 5] },
    missing: { type: 'array', items: { type: 'string' } },
    weak_or_wrong: { type: 'array', items: { type: 'string' } },
    verdict: { type: 'string' },
  },
  required: ['code', 'issue_grasp', 'respondent_args', 'actionability', 'soundness', 'overall', 'verdict'],
}

const LENSES = {
  litigator: `You are a CALIFORNIA SCHOOL-DISTRICT layoff litigator (Education Code 44949/44955) preparing this exact matter. You are reading a junior associate's analysis of ONE issue. Judge how much it would actually HELP you prepare — does it nail the operative distinction, flag the respondent's best arguments and your real exposure, and give you concrete next steps? Be demanding; generic issue-spotting is not useful.`,
  skeptic: `You are a SKEPTICAL senior partner pressure-testing a junior associate's legal reasoning on ONE layoff issue. Your job is to catch overreach, hand-waving, INVERTED rules (stating a doctrine backwards), and CONFABULATED authority. Reward analysis that is precise, correctly-directed, and honest about uncertainty; punish confident-but-wrong.`,
}

const prompt = (lens, code) => `${LENSES[lens]}

Load your item (code = "${code}") — you ONLY see the issue, the de-identified matter facts, and the candidate analysis (NO answer key; judge it on its own merits):
  python3 -c "import json;d=json.load(open('${INPUT}'));print(json.dumps([x for x in d if x['code']=='${code}'][0],indent=1))"

Score each dimension 1 (useless/wrong) to 5 (excellent), from YOUR lens:
${DIMS}

Names are de-identified (parties as R1/R2, some names as [name]); do not penalize that. Return code ("${code}"), the five integer scores, missing[] (key things a competent analysis should have included), weak_or_wrong[] (specific overreach/inversion/confabulation — quote the phrase), and a one-line verdict.`

const tasks = []
for (const code of CODES) for (const lens of ['litigator', 'skeptic'])
  tasks.push({ code, lens })

const scored = await parallel(tasks.map((t) => () =>
  agent(prompt(t.lens, t.code), { label: `${t.lens}:${t.code}`, phase: 'Judge', schema: SCHEMA })
    .then((s) => (s ? { ...s, lens: t.lens } : { code: t.code, lens: t.lens, overall: null }))))

const ok = scored.filter((s) => s && s.overall !== null)
log(`judged ${ok.length}/${tasks.length} (lens x item)`)
return { n: ok.length, scored }
