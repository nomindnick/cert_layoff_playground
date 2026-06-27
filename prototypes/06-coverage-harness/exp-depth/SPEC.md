# SPEC — E3. Depth pass: reasoning vs summary *(stub — promote after E1)*

> Read `../SPEC.md`. Quantifies the value of the structured-decision substrate
> (`facts`+`reasoning`) over bare gold summaries. `local-LLM-heavy`.

## Hypothesis

Analysis that reads the **full `facts`+`reasoning`** for load-bearing holdings
produces measurably more matter-specific, actionable depth than summary-only RAG —
and the gap is large enough to make the structured decisions (not the 35-year
gold) the real depth substrate. Bare holdings are brittle; this measures how much.

## Approach (sketch)

Two arms over the same E0 matters: **(S) summary-only** (synthesize from
`summary_style_holding` / gold text) vs **(R) reasoning-read** (pull full
`facts`+`reasoning` for the top-k load-bearing holdings, analyze over those).
**Metrics:** E0 depth score (operative-fact-distinction recovery) **+ a 05-style
discriminability** check — a deeper, more matter-specific memo should be *more*
discriminable to its own matter vs a decoy. Report depth lift and the wall-clock
cost of the extra reads.

## Falsified if

Reasoning-read doesn't beat summary-only on depth/discriminability — i.e. the
summaries already carry the operative distinction and the reasoning chain adds
little (would be a cheap, useful result: gold summaries suffice, depth isn't
data-bounded after all). Backend named per result.
