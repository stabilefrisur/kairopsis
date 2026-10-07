# Analysis skill evaluation with GPT-5.6 Luna — 7 October 2026

Six fresh **GPT-5.6 Luna agents at High effort** repeated the same three paired
cases. Original rubric totals: **28/30 with the skill, 22/30 without it**.
The skill prevented an incorrect Snapshot interpretation, but its design answer
still produced an unusable payload despite correct conversion advice.

## Method

Used the original [Sol experiment](analysis-skill-evaluation-2026-10-07.md)'s exact
case prompts, arm instructions, raw application modules, rubric and frozen skill.
Every original manifest hash passed before dispatch. Only the model changed.
Fresh contexts, three concurrency slots, no peer results, rubric access, other
cases, web research, mutations or live application operations permitted.

The frozen skill predates the event-sample and exact-monitoring changes made after
the Sol evaluation. This rerun tests model choice; it does not retest those later
edits. The parent scored the same five criteria per case (0 absent/wrong,
1 partial, 2 complete), without blinding. [Result data](analysis-skill-luna56-eval-2026-10-07.json)
retains criterion scores, answer summaries/excerpts, resources and draft JSON.

## Results

| Case | With skill | Without skill | Material observation |
| --- | --- | --- | --- |
| Saved Snapshot | 10/10 | 7/10 | Control incorrectly says weekly change is an increase in the Z-score and treats omitted contract fields as unresolved. Skill correctly identifies the repeated current result and v1 default. |
| Adjusted spread levels | 9/10 | 8/10 | Both calculate 47.5 and +1.5 correctly. Skill names the conversion but its JSON still uses the original percent series; evaluator rejects it. Control unnecessarily replaces the known IG ID with an unavailable placeholder and omits overlap/composition caveats. |
| Event-conditioned monitoring | 9/10 | 7/10 | Both leave monitoring off and identify unsupported filters/one-sided alerts. Skill gives both worked ratios and the wrong-cohort explanation. Both upstream-filtering alternatives lack complete baseline/precomputed-move handling. |

Scores are equally weighted completeness checks, not execution success rates.
The **9/10 design answer still contains a blocking configuration error**.

## Confirmed payload failure

The skill-backed answer says to convert HY from 4.5% to 450 bp, and correctly
computes the example using 450. Its JSON nevertheless contains:

```json
"series_ids": ["hy_oas_percent", "ig_oas_bp"]
```

With the supplied series metadata and percentage-change risk basis, transformed
units are dimensionless `%/%` for HY and `bp/%` for IG. An ordinary
`AnalysisDefinition` schema check accepts the JSON, but a synthetic call to the
actual evaluator raises:

```text
Difference requires matching units; no implicit conversion
```

The unit probe used invented dated observations solely to execute the check; it
was not a live provider test or a reconstruction of the case's market history.
A complete offline proposal should reference an explicitly unavailable converted
HY series and retain the existing `ig_oas_bp` ID. Prose conversion advice alone
does not make the emitted payload implement that conversion.

## Scoring details

- Control Snapshot: zero for incorrect change-field semantics; one for preserving
  captured evidence without resolving the absent contract to v1.
- Skill design: partial offline/dependency criterion. It acknowledges conversion
  and no live preview, but does not represent the converted-input prerequisite
  in the JSON.
- Control design: partial economic/sampling caveats and partial input-dependency
  handling. The supplied IG ID is wrongly labelled unavailable. Its conventional
  ±2 “not unusual” judgement is also uncalibrated; no extra deduction was added.
- Skill monitoring: partial fallback criterion because prefiltered observations
  are proposed without preserving baselines or selecting Level for precomputed moves.
- Control monitoring: partial worked arithmetic (10000 given, 0.25 omitted),
  partial eligible-history support, and the same incomplete upstream fallback.
- Both control drafts that omit the version field remain structurally valid; the
  monitoring calculation is supported in v1. No deduction for omission alone.

## Across the three experiments

| Model, High effort | With skill | Without skill |
| --- | --- | --- |
| GPT-6.1 Sol | 30/30 | 30/30 |
| GPT-6 Luna | 29/30 | 25/30 |
| GPT-5.6 Luna | 28/30 | 22/30 |

This sample suggests a completeness benefit for the Luna runs, with a substantive
Snapshot error avoided in the 5.6 pair. One response per model/arm/case cannot
establish a reliable effect or rank models generally. Complete fixtures and
optional source access also limit how representative these tasks are.

## Implications and validation

All four emitted drafts pass the application model and resolve to monitoring off.
That structural validation missed the confirmed semantic unit error above.
Illustrative arithmetic was checked independently. No provider request, save or
alert activation occurred.

The existing post-Sol event-sample guidance addresses the incomplete monitoring
fallback, but was intentionally excluded from this frozen-skill rerun. The new
design failure identifies a separate improvement: explicitly check emitted
series IDs and their units against every required upstream transformation,
even when only drafting offline. Skill and application files were not changed
during this evaluation.
