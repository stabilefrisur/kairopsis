# Analysis controls with explicit calculation order

Proposal, 6 October 2026. Allow combinations whose formulas are defined, while
using examples, contextual guidance and previews to help users choose. Economic
recommendations belong in the bundled
[analysis skill](../../src/kairopsis/skills/kairopsis-analysis/SKILL.md), not in a
hidden whitelist. This proposal changes no current application behaviour.

## Organize controls around the calculation

Use one editor in Library and Investigation, preserving their different save
semantics. Show the calculation as a short sequence next to the preview:

**Inputs → Measure → Scale inputs → Compare → Historical context**

| Section | Visible controls | Conditional detail |
| --- | --- | --- |
| Inputs | One series or two; named inputs | Comparison Basis, source and unit details; regression labels dependent/explanatory |
| Measure | Level / Absolute change / Percentage change | Frequency for measuring changes; explain what a percentage change means for the selected series |
| Scale inputs | None / Volatility / Beta to reference / VaR / Expected Shortfall | Relevant reference, estimation history and method-specific parameters; optional per-input overrides |
| Compare | Difference / Ratio / Regression residual for two inputs | Fitting window for regression; standalone has no comparison selector |
| Historical context | Reference history; Result units / Z-score | Mean/SD and sample details, descriptive percentile |
| Monitoring | Separate collapsed section | Enable monitoring; extreme, movement and materiality rules in actual output units |

This removes the overloaded Type / calculation label and separates the internal
`calculation=level` value from Measure Level. Display range stays with the chart.
If Frequency is hidden for level inputs, keep the interval of the reported result
change visible beside that statistic and in monitoring; do not hide a setting that
still affects reported behaviour.

The visual sequence should match execution order even if users choose controls
in another order. Changing a control retains other explicit choices where they
remain defined. Unsupported settings produce a precise capability message rather
than silently switching the input measure.

## Make the result legible

Show a continuously updated formula and one plain-language interpretation. For
example:

> Weekly HY spread change / its prior weekly-change SD
> minus weekly IG spread change / its prior weekly-change SD.
>
> Positive: HY widened more relative to its own usual movement.

With result Z-score enabled, append:

> Show how unusual that difference is relative to its reference history.

Display actual units, ordered inputs, risk references and estimation/reference
windows. The formula must describe the transformed values, rather than always
showing raw A minus B. Keep the unstandardized magnitude available alongside a
Z-score.

For ambiguous choices, add specific contextual text: “Ratio of weekly changes;
not weekly change in the ratio.” For Percentage change, explain “proportional
spread change” when the source is a spread; it must not be labelled bond return.

## Allow the combinations without inventing missing semantics

Result Z-score should be available for every completed numeric statistic with a
usable reference distribution, including standalone levels and ratios. An
unstable ratio deserves an explanation and denominator evidence; changing the
statistic behind the user's back would answer a different question.

Level plus input scaling requires an explicit additional choice:

**Estimate risk from: Absolute changes / Percentage changes**, with Frequency.

Preserve Level as the numerator. A spread level divided by the volatility of
weekly spread changes is a compensation-versus-variability proxy; a weekly spread
change divided by that volatility is a shock measure. These must remain visibly
different. For changes/percentage changes, default the estimation basis to the
measured input's basis. Independent choices need their units and formula shown;
defaults are suggestions, not automatic remapping.

This extension needs a versioned calculation contract before implementation:
estimation basis, per-input overrides, units, dates, minimum samples, serialized
definitions and Snapshot compatibility. Removing validators alone is insufficient.

## Guidance and validation

Use guidance to recommend, explain and identify redundancy. Keep mathematical
constraints explicit: division by zero, unusable scale/reference dispersion,
incompatible subtraction, wrong input count and unavailable observations.
Distinguish those from warnings about a questionable reference, near-zero
denominator, sparse tails or a fragile level regression.

For ratios of moves, show the denominator's magnitude and sign. Propose an
optional user-defined materiality threshold and explicit interval/sample filter
for event analysis. When a filter changes the historical sample, show that sample
definition alongside the score. Preserve unrestricted inspection when a user
deliberately wants it; a descriptive output does not imply suitability for
automatic flagging.

Method-specific controls appear only where relevant: reference for active scaling,
weighting/half-life for volatility, confidence/downside for VaR/ES, fitting window
for regression. Keep advanced per-input configuration reachable. Surface common
divisor cancellation and self-beta as informational redundancy, not errors.

## Suggested examples without presets becoming restrictions

Offer optional starting points: quoted spread gap, spread multiple, relative
weekly shock, return outperformance, regression departure and pass-through.
Selecting one should fill a transparent draft that the user can edit. Expose the
formula and rationale before saving; preserve existing user settings unless they
explicitly choose to replace them with the starting point.

## Implementation acceptance criteria

- Every choice either retains its explicit meaning or produces a specific
  mathematical/data/capability explanation; no silent Level-to-Change switch.
- Formula, units and interpretation track input order, measure, scaling and
  standardization in both Library and Investigation.
- Level-over-risk and wider Z-score support have defined, serialized semantics;
  old Snapshots continue using their captured definitions.
- Preview exposes missing data, estimation samples and denominator behaviour.
- Monitoring settings are separate and are reconsidered when output units change.
- The bundled skill reflects implemented capabilities without turning recommended
  economic uses into hardcoded availability rules.
