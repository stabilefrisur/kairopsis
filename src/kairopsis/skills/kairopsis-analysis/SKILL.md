---
name: kairopsis-analysis
description: Interpret Kairopsis Analysis results, design definitions from economic questions, or configure and verify analysis settings.
---

# Kairopsis Analysis

Choose the path matching the request. Read linked sections when their condition
applies; the full research library is optional. A design-and-save request uses
Design, then Configure. Preserve explicit analytical choices and distinguish
economic suitability, defined mathematics and installed capability.

## Interpret — explain existing evidence

1. For a conceptual formula question, use the supplied input semantics. For an
   actual result, obtain its captured definition, ordered inputs, units, dates and
   estimation evidence. For a Snapshot, use its captured settings. Resolve
   [contract/version semantics](references/application-contract.md#version-and-combination-rules)
   when interpreting saved settings, and
   [dates and estimation](references/application-contract.md#dates-and-estimation)
   when explaining a move, fitted history, Z-score, sparse cadence or unavailable result.
2. Trace the [calculation order](references/combination-map.md#read-the-calculation-in-the-correct-order).
   Use the applicable checks below to explain the result's economic meaning.

Done: answer the question with formula, units, sign meaning and material
limitations. Identify missing evidence when it prevents an interpretation;
configuration or a new live preview is needed only if the request calls for it.

## Design — choose or revise a definition

1. Identify the [economic question](references/analysis-design.md#start-with-the-question)
   and ordered inputs. Resolve their
   [semantics and shaping](references/analysis-design.md#select-and-shape-the-inputs),
   including Comparison Basis, conversions and cadence.
2. Write the formula and units using
   [calculation order and measure](references/analysis-design.md#choose-calculation-order-and-measure).
   Choose [histories and Frequency](references/analysis-design.md#choose-histories-and-frequency)
   by purpose. Apply the conditional checks below to the choices under consideration.

Done: give a proposed definition with settings, shaping, reasons and unresolved
data/capability needs. Mark untested proposals as such. For an analogous recipe,
consult only the relevant [worked starting point](references/analysis-design.md#worked-starting-points).

## Configure — preview or save settings

1. Use the [application contract](references/application-contract.md): read
   Data and operations, Analysis fields, Version and combination rules, Dates
   and estimation, and Interpretation and persistence checks; add RiskAdjustment
   fields when scaling is active. Verify supported fields against the running
   schema or installed models. Use the definition from Design or the user's
   explicit settings; resolve a capability gap without substituting another formula.
2. Follow [preview verification](references/analysis-design.md#preview-and-retain-the-definition)
   with actual inputs. Trace a representative result through its formula,
   including applicable risk, fit and reference samples. Report an unavailable
   result with its data/calculation limitation.
3. For monitoring requests or revisions affecting monitored results, assess
   thresholds and calibration using
   [monitoring guidance](references/analysis-design.md#separate-monitoring-from-calculation)
   before saving. Save when authorized and read back the definition.

Done: report verified settings, preview evidence or the exact blocker, save state,
and monitoring/calibration state. A successful save alone is not a verified live
evaluation. Keep reproducible detail in the user's requested record.

## Conditional checks — all paths

| When needed | Read |
| --- | --- |
| Interpret, choose or configure a particular combination | The matching row under [Standalone](references/combination-map.md#standalone), [Difference](references/combination-map.md#difference), [Ratio](references/combination-map.md#ratio) or [Regression residual](references/combination-map.md#regression-residual), plus applicable [conditions](references/combination-map.md#conditions-that-make-those-examples-economically-defensible). Core/Conditional/Event guide recommendations, not permission. |
| Interpret or choose risk method, reference, estimation basis or downside | [Risk scaling and references](references/analysis-design.md#choose-risk-scaling-and-references); for Level with active scaling, use [adjusted-level meanings](references/combination-map.md#the-32-level-plus-adjustment-settings) instead of the base worked rows. |
| Compare per-input settings or suspected cancelling adjustments | [Overrides and references](references/combination-map.md#per-input-overrides-and-references) or [redundant settings](references/combination-map.md#redundant-settings-rather-than-invalid-economics). |
| Interpret or choose a Z-score | [Result standardization](references/analysis-design.md#choose-result-standardization), including ratio-of-moves sampling conditions. |
| Interpret or monitor ratios of changes/percentage changes | [Ratio examples](references/combination-map.md#ratio) and [event-sample requirements](references/analysis-design.md#event-samples), including percentile monitoring. Check [available monitoring rules](references/application-contract.md#monitoring-rules). |
| Assess validity or a claimed performance, causal or trading meaning | The relevant [invalid or misleading instance](references/combination-map.md#combinations-and-interpretations-that-do-not-make-sense). |
