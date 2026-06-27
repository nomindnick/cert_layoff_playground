export const meta = {
  name: 'depth-recovery-judge',
  description: 'Reference-based depth-recovery judge (0-3) for one depth run; one Opus agent per analysis item.',
  phases: [ { title: 'Judge', detail: 'one agent per analysis item' } ],
}
// args: { judge_path: "<abs path to depth.<tag>.input.json>", item_ids: [..] }
const A = typeof args === 'string' ? JSON.parse(args) : args
const JUDGE_PATH = A.judge_path
const ITEM_IDS = A.item_ids
const SCORE_SCHEMA = {
  type: 'object',
  properties: {
    item_id: { type: 'string' }, score: { type: 'integer', enum: [0, 1, 2, 3] },
    justification: { type: 'string' }, recovered_facts: { type: 'array', items: { type: 'string' } },
  },
  required: ['item_id', 'score', 'justification'],
}
const prompt = (id) => `You are grading how well a candidate ANALYSIS recovers the operative legal reasoning an Administrative Law Judge ACTUALLY used to decide one issue in a California certificated-employee (teacher) layoff (Education Code 44949/44955).

Load your item (id = "${id}"):
  python3 -c "import json;d=json.load(open('${JUDGE_PATH}'));print(json.dumps([x for x in d if x['item_id']=='${id}'][0],indent=1))"

It has: issue; matter_excerpt (facts); key_reasoning + key_facts (the ALJ's ACTUAL reasoning = GROUND TRUTH); analysis (the candidate to grade).

Score how well "analysis" recovers what the ALJ actually reasoned:
- 0 = bare/generic or addresses a DIFFERENT issue/reasoning than the reference.
- 1 = names the right operative FACTS but not the legal distinction.
- 2 = recovers the actual legal DISTINCTION the ALJ relied on.
- 3 = recovers the distinction AND its rationale, tied to these facts.
Judge only on overlap with the reference; credit recovery of the reference distinction anywhere in the analysis. Return item_id ("${id}"), score, one-line justification, recovered_facts.`

const scored = await parallel(ITEM_IDS.map((id) => () =>
  agent(prompt(id), { label: `judge:${id}`, phase: 'Judge', schema: SCORE_SCHEMA })
    .then((s) => (s ? s : { item_id: id, score: null, justification: 'failed' }))))
const ok = scored.filter((s) => s && s.score !== null)
log(`judged ${ok.length}/${ITEM_IDS.length}`)
return { n: ok.length, scored }
