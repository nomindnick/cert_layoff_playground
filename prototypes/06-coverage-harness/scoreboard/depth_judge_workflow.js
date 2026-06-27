export const meta = {
  name: 'depth-judge-calibration',
  description: 'E0: Opus-subagent depth rubric judge over the calibration ladder (L0..L3, blind to level). Validates the judge orders synthetic analyses by quality.',
  phases: [
    { title: 'Judge', detail: 'one agent per calibration item: score 0-3 vs the held-out ALJ reasoning' },
  ],
}

const A = typeof args === 'string' ? JSON.parse(args) : args
const JUDGE_PATH = A.judge_path
const ITEM_IDS = A.item_ids

const SCORE_SCHEMA = {
  type: 'object',
  properties: {
    item_id: { type: 'string' },
    score: { type: 'integer', enum: [0, 1, 2, 3] },
    justification: { type: 'string' },
    recovered_facts: { type: 'array', items: { type: 'string' } },
  },
  required: ['item_id', 'score', 'justification'],
}

const prompt = (id) => `You are grading how well a candidate ANALYSIS recovers the operative legal reasoning an Administrative Law Judge ACTUALLY used to decide one issue in a California certificated-employee (teacher) layoff (Education Code 44949/44955).

Load your item (id = "${id}") with this exact command:
  python3 -c "import json;d=json.load(open('${JUDGE_PATH}'));print(json.dumps([x for x in d if x['item_id']=='${id}'][0],indent=1))"

The item has:
- issue: the legal issue category.
- matter_excerpt: the underlying facts.
- key_reasoning + key_facts: the ALJ's ACTUAL reasoning and operative facts — this is the GROUND TRUTH / reference answer.
- analysis: the candidate text you must grade against that reference.

Score how well "analysis" recovers what the ALJ actually reasoned (key_reasoning/key_facts):
- 0 = restates a bare holding/conclusion, is generic, or addresses a DIFFERENT issue/reasoning than the reference.
- 1 = names the right operative FACTS but not the legal distinction the ALJ drew.
- 2 = recovers the actual legal DISTINCTION the ALJ relied on.
- 3 = recovers the distinction AND its rationale, tied to these facts.

Judge only on overlap with the reference reasoning — do not reward fluent prose that misses the ALJ's actual basis, and do not penalize terseness that nonetheless captures the distinction. Return: item_id ("${id}"), score (0-3 integer), a one-line justification, and recovered_facts (the operative facts the analysis captured, possibly empty).`

const scored = await parallel(
  ITEM_IDS.map((id) => () =>
    agent(prompt(id), { label: `judge:${id}`, phase: 'Judge', schema: SCORE_SCHEMA })
      .then((s) => (s ? s : { item_id: id, score: null, justification: 'agent failed', recovered_facts: [] }))
  )
)

const ok = scored.filter((s) => s && s.score !== null)
log(`judged ${ok.length}/${ITEM_IDS.length} calibration items`)
return { n: ok.length, scored }
