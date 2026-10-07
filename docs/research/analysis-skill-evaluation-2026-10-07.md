# Analysis skill paired evaluation — 7 October 2026

Six fresh GPT-6.1 Sol agents, each at High reasoning effort: three cases, one
with the frozen skill and one without it. Both arms scored **10/10 on each case**.
These runs show no accuracy advantage. They do show that the skill can substitute
for some application-source inspection.

## Method

- Each pair received the same synthetic case and frozen raw application files.
- The skill arm could read the four skill Markdown files; the control arm was
  explicitly exempted from the repository's skill-loading instruction.
- Every agent started without conversation history. No peer results, rubric,
  other cases, internet, live app or mutations were permitted for the agents.
- Three concurrency slots were used. All six runs finished before skill changes.
- A five-criterion rubric per case was fixed before dispatch: 0 absent/wrong,
  1 partial, 2 complete. The parent scored answers against that rubric.
- Agents answered in at most 550 words plus a resource audit. Scores assess
  supplied scenarios, not general economic competence or production behaviour.
- Application source: commit `872c3f3`. The tested skill was the uncommitted,
  reviewed version with web sources removed; its frozen hashes are in the
  [evaluation data](analysis-skill-eval-2026-10-07.json).
- That data retains exact case prompts, criteria, response summaries/excerpts,
  resource audits and all four generated JSON drafts. Summaries are not complete
  transcripts. Resource counts are self-reported files, not tokens or elapsed time.

## Comparison

| Case | With skill | Without skill | Observed difference |
| --- | --- | --- | --- |
| Saved v1 Snapshot | 10/10 | 10/10 | Both calculate +2 Z-score, reject acceleration and a backtest interpretation, and retain captured settings. Skill arm reports zero raw-source files; control four. |
| Level divided by proportional spread variability | 10/10 | 10/10 | Both convert units, obtain 47.5 bp/% and +1.5 Z-score, and label the converted series unavailable. Skill arm explicitly explains why Follow is wrong here and avoids adding an alert threshold. Raw-source files: two versus seven. |
| Event-conditioned pass-through monitoring | 10/10 | 10/10 | Both retain the ratio and monitoring off, identify event/denominator/one-sided-rule gaps, and distinguish inclusive from strict thresholds. Control includes upper_percentile 90 while clearly warning that it cannot express the request. Raw-source files: four versus seven. |

Each skill arm also reported reading all four skill documents, though different
sections. Fewer source files therefore does not establish lower total context
cost or faster execution. With one run per arm per case, no statistical claim is
warranted. Both arms had unusually complete evidence and source access.

## Improvements after all runs

No observed correctness failure justified a broad rewrite. The changes instead
capture useful reasoning that the agents supplied consistently:

1. **Exact monitoring semantics.** The contract now states inclusive two-sided
   percentile bounds, absolute Z-score/move thresholds, and why a result threshold
   cannot gate a native-unit input denominator. Both monitoring agents inspected
   application code for these details.
2. **Event-sample construction.** Design guidance now explains computing moves
   before filtering intervals, applying the same eligibility to current and prior
   results, checking eligible-event support, and preserving precomputed moves as
   Level. Both agents independently explained these steps; the earlier skill
   described the requirement without the order of operations.
3. **Targeted routing.** Ratio monitoring points directly to those two sections,
   so these details are reachable without a broad source-code search.

Other successful guidance is retained: captured v1 semantics, separate numerator
and estimator measures, explicit unit conversion, offline proposal status and
the distinction between valid settings and usable monitoring. All 60 worked
rows covering 120 settings remain unchanged; the packaged skill has no web links.

## Validation and limits

All four generated drafts validate against `AnalysisDefinition`. Both design
drafts intentionally reference unavailable converted-series placeholders: model
validation does not make them executable against a Library. Arithmetic was
checked independently from the supplied figures.

After the targeted edits, validation passed: frontmatter, 104 local links/anchors,
zero skill web links, unchanged worked rows, exact percentile boundaries against
the implementation, and all four skill documents matching a fresh wheel and source
distribution. No additional agent reruns were performed after these edits; the
paired scores describe the frozen pre-edit skill only. No live save, provider
request or monitoring enablement occurred.
