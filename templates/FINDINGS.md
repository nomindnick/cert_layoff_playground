# FINDINGS — {NN. Prototype name}

## Verdict

`validated | falsified | mixed | parked` — one paragraph of plain-language
summary a future session (or blog post) can lift directly.

## What we learned

The substance: results, numbers, examples (de-identified — District (ALJ)
only). Honest about weaknesses. Falsified-because-X is a success outcome;
say X precisely.

## Backend notes

Which backend produced each result (`ollama:<model>`, or subagent fan-out
with the subagent model named). Subagent results validate the idea, not
local feasibility — flag any result that still needs a local re-run, and any
model-specific quirks discovered (these also go to STATUS.md Lessons).

## Blocked on full corpus?

What would change with the production corpus (more years, more ALJs,
post-2017 decisions)? What should be re-run, and is the code ready to
re-point via corpuslib?

## Production recommendation

Build / don't build / build differently — and what the production version
should look like if built. Name the destination (see IDEAS.md "Product
shape"): query-time feature of the main app / build-time artifact
generator / internal operator tool / standalone experiment.
