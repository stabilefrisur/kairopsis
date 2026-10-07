# Analysis skill refinement — 7 October 2026

Applied writing-for-agents to the [paired evaluations](analysis-skill-luna56-evaluation-2026-10-07.md).
The confirmed failure was a correct conversion in prose paired with JSON that
still referenced the unconverted series. Model/schema validation had accepted it.

## Changes

- **Sharper trigger:** Design and Configure now require draft consistency before
  returning settings, previewing or saving, including offline proposals.
- **Checkable completion:** resolve every emitted ID, preserve known IDs, represent
  unavailable shaped inputs explicitly, and trace values/units from the IDs actually
  written. A definition is complete when payload, formula and worked result agree.
- **Progressive disclosure:** the procedure lives once in the application contract,
  reached by short pointers. Interpret and the 120-combination map are unchanged.
- **Co-located guidance:** the check points directly to event-sample and monitoring
  rules. Precomputed moves must be paired with a compatible measure.
- **Unusualness:** descriptive Z-scores require a stated appropriate rule before
  assigning a binary extreme/usual classification. An illustrative cutoff is not
  calibration.

## Targeted retests

Two fresh GPT-5.6 Luna agents at High effort received the unchanged case prompts
and raw files, plus the revised skill. They received no previous results, suspected
bugs or intended answers. This was a targeted skill-only check, not another paired
comparison. [Result data](analysis-skill-refinement-eval-2026-10-07.json) retains
drafts, evidence excerpts and resource audits.

| Case | Observed outcome |
| --- | --- |
| Adjusted levels | Correctly names converted HY as unavailable, preserves existing IG ID and reports 47.5 bp/percentage point and +1.5 Z-score. Critical prose/payload inconsistency fixed in this sample. |
| Event monitoring | Computes moves before filtering; applies the same event rule to current and historical samples; uses Level for an upstream event-series alternative. Monitoring remains off because lower-only alert support is missing. |

Under the original rubric, design remains 9/10: this time it omitted the overlapping
weekly-sample caveat rather than emitting incompatible inputs. Monitoring scored
10/10. The sampling guidance is already present; this single omission did not
justify duplicating it throughout the entrypoint.

One retest per case does not establish reliable behaviour across runs. Placeholder
inputs are still prerequisites, not registered or evaluated data. No live save,
provider request or monitoring activation occurred.

## Validation

Passed: frontmatter, 104 local links/anchors, no skill web links, unchanged
combination map, structural validity of both drafts and unit compatibility after
the explicitly required HY conversion. The four skill files match fresh wheel
and source-distribution contents. This verifies the proposed conversion's units,
not the existence of its placeholder series. Application code is unchanged.
