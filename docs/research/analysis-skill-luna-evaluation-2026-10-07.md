# Analysis skill evaluation with GPT-6 Luna — 7 October 2026

Repeated all three cases with six fresh **GPT-6 Luna agents at High effort**,
one with and one without the skill per case. Using the original rubric, the
skill arm scored **29/30**, the control **25/30**. The earlier GPT-6.1 Sol arms
both scored 30/30.

## Controlled comparison

Exact case prompts, raw application modules, rubric, skill and arm instructions
were retained from the [Sol experiment](analysis-skill-evaluation-2026-10-07.md).
All original manifest hashes passed before dispatch. Only the selected model
changed. Three concurrency slots; no conversation history, peer results, rubric
access, web research, file edits or live application operations permitted.

The frozen skill predates the event-sample and exact-monitoring refinements made
after the Sol run. This tests a model change, not those later refinements.
[Result data](analysis-skill-luna-eval-2026-10-07.json) contains criterion scores,
response summaries/excerpts, resource audits and all generated payloads; original
prompts and rubric remain in the referenced baseline data.

## Results

| Case | Luna with skill | Luna without skill | What differed |
| --- | --- | --- | --- |
| Saved Snapshot | 10/10 | 9/10 | Both interpret the +2 correctly and reject acceleration/profit claims. Skill arm explicitly resolves the omitted contract to v1; control only says to use captured evidence. |
| Adjusted spread levels | 10/10 | 8/10 | Both calculate 47.5 and +1.5 correctly. Skill arm names bp per percentage point and overlapping weekly observations; control uses vague “statistic units” and omits overlap. |
| Event-conditioned monitoring | 9/10 | 8/10 | Both retain monitoring off and recognize unsupported event/denominator/one-sided rules. Skill arm supplies more sample interpretation but leaves its precomputed-change fallback incomplete. Control omits worked ratios and explicit eligible-history/sample support. |

Scores use the same five criteria and 0–2 scale as the Sol experiment. Differences
are mainly missing explanation and incomplete procedures, not wrong arithmetic
or rejected payloads. The parent was not a blinded evaluator. In particular:

- Control Snapshot: one point lost for not resolving the omitted version field.
- Control adjusted levels: one point for vague output units; one for omitted
  overlapping-sample caveat.
- Skill monitoring: one point lost because an upstream sample of precomputed
  weekly changes was proposed without changing Measure to Level. Applying the
  supplied Change draft to those inputs would transform them again.
- Control monitoring: one point for omitted worked ratios; one for not checking
  the eligible historical distribution and its support explicitly.
- Control monitoring omits the contract field and therefore defaults to v1.
  This base ratio/change calculation is supported in v1; no point deducted.

The skill was helpful for completeness in this small sample. It did not prevent
every omission. One run per arm per case cannot establish a reliable performance
difference; these cases also supply unusually complete evidence and source access.

## Implication for the skill

No new edit was required. The monitoring fallback omission is precisely the
workflow covered by the **Event samples** section added after the earlier Sol
run: compute moves before filtering, apply eligibility to current and prior
history, and use Level for precomputed moves. That revised section was deliberately
excluded from this controlled rerun. Its effectiveness with Luna remains untested.

## Validation

All four generated drafts validate against the current application model and
resolve to monitoring off. Converted-HY identifiers are explicitly unavailable
placeholders; structural validity does not make them runnable Library definitions.
Arithmetic was checked independently against the case fixtures. No saves,
provider calls or alert activation occurred. Skill and application files unchanged.
