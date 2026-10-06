---
name: kairopsis-analysis
description: Define or revise a Kairopsis Analysis from an economic question, choosing data shaping, calculation, risk adjustment, historical comparison and monitoring settings. Use for analysis setup or interpretation, rather than application installation.
---

# Configure a Kairopsis Analysis

Produce an Analysis whose formula, inputs and parameter choices answer the
user's economic question. Explain the result in economic terms and check the
actual application supports that definition.

## Shape the question

Identify what the user wants to investigate: pricing level, relative pricing,
movement, performance, stress, pass-through or departure from a historical
relationship. Establish the exposures, direction of comparison and interval.
Use available context; ask only where different answers change the definition.

Read [analysis design](references/analysis-design.md) before choosing parameters.
It covers input semantics and shaping, calculation order, references, estimation
windows, standardization, thresholds and worked starting points.

Write the proposed formula and output units before mapping it to controls.
Distinguish changes in a relationship from relationships between changes.
For percentage changes, establish whether the underlying series is a price,
total-return index, spread or another measure.

## Choose and justify the definition

Use [the combination map](references/combination-map.md) when comparing methods,
using risk adjustment, interpreting ratios of moves, or considering adjusted
levels. It maps all 120 basic combinations, examples, conditional uses,
redundancies and per-input overrides. Its Core/Conditional/Event labels guide
recommendations; they are not a whitelist of permitted choices.

Preserve the user's explicit analytical choices where the formula is defined.
Explain unusual choices and their consequences. Separate an economic concern
from an undefined calculation or a capability the installed version lacks.

Select the series and Comparison Basis, input measure, Frequency, optional input
scaling, relationship calculation and optional result standardization. Give each
history window a purpose. Carry out needed shaping through an established data
source/transformation, with its convention retained in the series description.

Use [sources and deductions](references/sources.md) when checking the rationale
behind an interpretation or explaining why similar formulas answer different
questions. Numerical examples in these references are illustrative, not market
observations or recommended thresholds.

## Configure and verify

Before constructing a payload or saving settings, read
[the application contract](references/application-contract.md) and inspect the
running application's schema or the installed models. Request
`settings.calculation_contract: "input-pipeline-v2"` for new definitions; missing
discriminators retain legacy v1 semantics. The reference documents calculation
constraints separately from economic recommendations. A rejected
combination needs an explicit capability gap; silently switching Level to Change
or substituting another formula would answer a different question.

Use the existing Library UI or application interface. Preview the intended
definition with the actual inputs; inspect transformed values, output units,
dates, fit/risk/reference samples and limitations. Check a representative result
against its formula. Missing observations remain missing unless an explicitly
defined shaping convention says otherwise.

Apply saved changes when the user's request authorizes them. An exploratory
question can finish with a preview and complete proposed definition. Keep
monitoring and its calibration distinct from defining the calculation; select
thresholds in the resulting units rather than inheriting illustrative defaults.
Existing Snapshots retain their captured definitions and observations.

## Completion

Return the configured or proposed definition with:

- Economic question, formula, input identity/semantics, shaping and output units.
- Parameter choices and brief reasons; include material alternative choices.
- Preview evidence and limitations, or the exact missing data/capability.
- Whether defaults were saved and monitoring enabled, with any calibration still
  needed. Distinguish a saved definition from a verified live evaluation.

Keep the user-facing explanation concise; retain the detail needed to reproduce
the analysis in series descriptions, an Idea note or the user's requested record.
