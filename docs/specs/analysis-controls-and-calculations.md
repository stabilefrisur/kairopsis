# Analysis controls and calculation contract

Implementation specification, 6 October 2026.

## Objective

Make Analysis definitions understandable in calculation order and allow all
120 basic combinations of calculation, input measure, risk adjustment and result
standardization. Recommendations guide choices; they do not hide combinations.
Undefined mathematics, incompatible subtraction and inadequate data still produce
specific validation errors or unavailable results.

This spec supersedes the earlier
[interface proposal](../research/analysis-interface-proposal.md) where it resolves
details differently. The [analysis skill](../../src/kairopsis/skills/kairopsis-analysis/SKILL.md)
contains the economic rationale and examples. Implement the controls and engine
described here; update that guidance to match the implemented capabilities.

## Scope and existing behaviour

The existing pipeline measures each input, optionally scales it, calculates a
standalone result or pair relationship, then optionally standardizes the result.
Retain that order. The current model restricts adjustment to changes/percentage
changes and rejects Z-scores for standalone levels and ratios. Remove those
restrictions for the new calculation contract, with explicit semantics below.

Preserve the distinction between Library defaults, exploratory Investigation
settings, and immutable captured evidence. Follow
[ADR 0004](../adr/0004-portable-idea-evidence.md). Existing saved observations,
definitions, chart evidence and historical calculations must not be reinterpreted.

The working tree already contains the analysis skill, distribution checks and
documentation changes from this conversation. Preserve those changes. This task
authorizes implementation and verification, not publication or unrelated cleanup.

## User experience

### Economic Rationale

[ADR 0005](../adr/0005-analysis-economic-rationale.md) adds optional Economic
Rationale to the Analysis definition and its captured evidence. Library edits
the text; evidence details show the rationale captured with the displayed
evaluation. Implemented 7 October 2026; the calculation sequence and contract
versions below remain unchanged.

### One sequence in Library and Investigation

Use shared control rendering/state rules for the analytical settings in both
surfaces. Preserve the current Library preview workspace and staged-series flow;
this is an editor cleanup, not a new application shell.

**Inputs → Measure → Scale inputs → Compare → Historical context**

| Section | Controls | Behaviour |
| --- | --- | --- |
| Inputs | Type: Standalone / Pair; one or two Data Series | Type controls input count; it is not stored as a second competing calculation field |
| Measure | Level / Absolute change / Percentage change; Frequency: Daily / Weekly / Monthly | Measure applies to each input before comparison; Frequency remains visible because it also controls risk estimation and reported level-result changes |
| Scale inputs | Method: None / Volatility / Beta to reference / Value at Risk / Expected Shortfall | Available for every input measure; None hides inactive calibration controls |
| Compare | Difference / Ratio / Regression residual | Shown for Pair only; regression additionally shows Fitting window |
| Historical context | Reference history; Output scale: Original units / Z-score | Both output scales available for every calculation and measure; show underlying magnitude with a standardized result |
| Monitoring | Separate collapsed section with enable state and applicable thresholds | Distinct from the mathematical definition; retain Library versus exploratory persistence semantics |

Chart-only display range and chart-view controls remain with the chart, separate
from estimation/history settings. No combined “Type / calculation” selector.
The internal standalone calculation may remain named `level`; user-facing labels
must distinguish Standalone from Measure Level.

Use First input / Second input for differences, Numerator / Denominator for
ratios, and Dependent series (y) / Explanatory series (x) for regression. Pair
defaults to Difference when no previous pair choice exists. Preserve the last
pair choice and second input in the unsaved UI draft when toggling type; only
active inputs/settings are sent in the saved definition.

### Scaling controls

Shared settings are the default; retain optional Customize per series for pairs.
Each active scaling definition exposes:

- Reference series: This series itself / a named available Data Series. For
  shared settings, “Each series itself” means a separate self-reference per input.
- Estimate risk from: Follow input measure / Absolute changes / Percentage
  changes. Follow input measure resolves to absolute changes for Level and
  otherwise follows the selected measure. Display that resolved meaning beside
  the control. This preserves automatic defaults while allowing explicit choices.
- Estimation history, using the existing period options.
- Volatility only: Equal / Exponential weighting; half-life in weekday sessions
  only when exponential.
- VaR/ES only: Confidence (%) and Downside: Increasing / Decreasing values.
- Beta: the chosen reference and the estimated signed beta in preview details.

Frequency is shared by numerator measurement and risk estimation in this release.
Independent risk-estimation Frequency is out of scope. Explicit estimation-measure
choices remain unchanged when the numerator measure changes. A Follow choice
updates its resolved meaning transparently.

Selecting an adjustment must never switch Level to Change. Changing calculation
must never disable Z-score. Inactive calibration fields can remain in the local
draft for convenient restoration, but must have no numerical or dependency effect.
Changing pair arity reconciles per-input overrides without losing the first input's
settings or sending an invalid override count.

### Formula, interpretation and preview

Show the complete formula, not just raw A minus B. Include input measure,
Frequency, scale method/reference, comparison, and final Z-score when selected.
Show actual output units; make risk-estimation and reference windows accessible.
Examples:

- “HY spread level / SD of prior weekly HY spread changes.”
- “Weekly HY spread change / its prior SD − weekly IG spread change / its prior SD.”
- “Z-score of the HY / IG spread-level ratio.”

Add a short interpretation appropriate to the formula. For generic data, use
neutral language such as “First input exceeds its fitted relationship with the
second.” Describe spread widening or investment return only when source semantics
establish that interpretation; never infer total return solely from `%` units.

For ratios of changes, show “Ratio of changes” explicitly. For level-over-risk,
identify both the level numerator and the risk-estimation measure. Provide
contextual guidance on signed/near-zero denominators, sparse tail estimates,
self-beta, and common-divisor cancellation without blocking defined calculations.

Preview uses the complete current draft. A late response for an older draft must
not be presented under the new formula. If retaining the last successful chart
after an error, label it as the previous definition and show the current error.
Preserve user-entered values and keyboard focus through conditional rerenders.

Original units means the completed, possibly risk-adjusted calculation's units;
it does not undo input scaling. Z-score previews retain the unstandardized result
and underlying input values for interpretation, chart details and export.

### Monitoring

Keep the existing percentile/Z-score and movement/materiality rule capabilities;
this task does not introduce a new alert engine. Put them in the Monitoring
section rather than among calculation controls. Only the applicable extreme rule
is active: symmetric percentile tails for original output, absolute Z-score
threshold for standardized output.

Changing measure, calculation, scaling method/reference/estimation basis or output
scale clears optional move/materiality thresholds in the edited draft and explains
why they need reconsideration. Retain the user's monitoring enable state and
extreme-rule parameters; do not claim defaults are calibrated. Save only through
the existing explicit save flow; exploratory edits do not silently rewrite defaults.

## Versioned definition

Add an explicit calculation-contract discriminator to Analysis settings. Suggested
field: `calculation_contract`, with `input-pipeline-v1` and `input-pipeline-v2`.
These names are part of the new persisted contract; use them consistently.

- Missing discriminator on existing persisted payloads means v1.
- Newly created UI definitions explicitly use v2. Document that new API callers
  should request v2 rather than relying on legacy defaults.
- Opening an existing v1 definition preserves it. Selecting a v2-only feature in
  its draft promotes that draft to v2; saving records a normal revised definition.
  Name/display-only changes need not upgrade its calculation contract.
- v1 preserves existing valid numerical, date, unit and monitoring semantics.
  Existing snapshots/evaluations load and render without rewriting their files.
- Latest evaluation from old captured evidence uses its retained v1 definition.
  Comparisons across contract/definition changes are incompatible baselines, not
  newly discovered market moves.
- Unsupported discriminator values fail explicitly.

Add `estimation_measure` to each RiskAdjustment record: null/omitted (Follow),
`change`, or `return`. Resolve Follow as specified above. For v1, retain the
legacy same-measure estimation behaviour; using an explicit new basis is a v2
feature. Persist the chosen setting and expose its resolved basis in evidence.

All existing numerical conventions remain unchanged unless expressly extended
here. The v2 contract enables new inputs and unit combinations; it does not add
annualization, log returns, a new OLS algorithm or new tail estimators.

## Calculation semantics

### 1. Measure the numerator

For input i at eligible date t, let b be its existing backward-only baseline for
Frequency. Define numerator n_i(t):

- Level: A_i(t), in the supplied unit U_i.
- Absolute change: A_i(t) − A_i(b), in U_i.
- Percentage change: 100 × (A_i(t)/A_i(b) − 1), in percentage points of relative
  change, displayed using the existing `%` convention. Baseline must be positive.

Retain existing native-observation, date alignment, weekday and baseline-tolerance
rules. A level numerator needs a valid observation at t; it does not require its
own change baseline merely because its risk denominator uses a reference series.

For pair results, both numerators must be eligible on the same t. Different
measurement endpoints remain visible in evidence under the existing conventions.
Do not fill, interpolate, forward-shift, or replace missing observations.

### 2. Form the risk-estimation sample independently

When method is None, q_i(t) = 1 and no reference retrieval/estimation is required.
Otherwise resolve reference R_i and effective estimation measure e_i.

Construct target and reference historical moves using e_i and the shared
Frequency, independent of the numerator measure. For Beta, use aligned target
and reference moves with identical start and end dates. Other methods estimate
the reference's historical move distribution.

Define the information cutoff explicitly:

- For Change/Percentage-change numerators, use that numerator's actual baseline
  date b, preserving the current exclusion of the measured interval.
- For Level numerators, use the existing nominal Frequency target for t
  (previous weekday, seven days earlier, or previous calendar month with day
  clamping). This deliberately excludes the current Frequency interval from the
  denominator sample, even though the numerator itself is a level.

Include historical risk moves ending no later than the cutoff and within the
configured estimation lookback. They require their own valid baselines. Preserve
existing stale-sample and minimum-sample checks, and the current all-history
common-input-history convention. Return sample dates/count and scale limitations.
Missing level-numerator baselines must not contaminate a reference-only estimator.

Extend retrieval warm-up whenever any input has active scaling, including when
Measure is Level. Audit preview, ordinary evaluation and retained-evidence Latest
retrieval paths; all must fetch enough numerator, reference and risk-baseline data.

### 3. Estimate the divisor

Preserve current historical estimator conventions:

| Method | q_i(t) |
| --- | --- |
| None | 1 |
| Volatility, equal weights | Sample SD of reference moves, denominator N−1 |
| Volatility, exponential | Existing normalized exponentially weighted SD with finite-sample correction; half-life in weekday sessions |
| Beta | Intercept-OLS slope of target moves on reference moves: Cov(target, reference) / Var(reference) |
| VaR | Empirical adverse-move quantile at confidence, inverse empirical CDF convention |
| Expected Shortfall | Average of the worst tail, retaining the existing fractional boundary-observation convention |

Downside transforms the estimation losses, not the numerator's sign. Negative
nonzero beta is supported. Preserve current numerical tolerance for unusable
scales: near-zero beta, zero/near-zero SD, nonpositive VaR/ES or nonfinite estimates
make that observation unavailable. Sample minima remain computational floors,
not economic guarantees. Keep optimized and direct estimators numerically aligned.

### 4. Scale the input and derive its unit

The transformed input is u_i(t) = n_i(t) / q_i(t). Never subtract the numerator's
mean or a beta intercept during this stage.

Units must use the numerator and estimator basis separately. Let U_n be the
numerator unit, U_e the target-estimation-move unit, and U_r the reference-
estimation-move unit. Percentage estimation moves use `%`; absolute estimation
moves use the respective supplied series units.

| Method | Transformed unit |
| --- | --- |
| None | U_n |
| Volatility/VaR/ES | U_n / U_r |
| Beta | U_n × U_r / U_e |

Retain the existing requirement that target/reference estimation-move units match
for volatility/VaR/ES. Percentage estimation supplies compatible `%` units;
absolute estimation requires compatible supplied units. Beta can relate unlike
units. No automatic bp/percent conversion or currency/curve adjustment is added.

Represent and simplify unit expressions deterministically. Equal units cancel;
dimensionless risk-scaled inputs can keep the existing “risk units” label.
Composite units must remain visible, not be mislabeled dimensionless. Unit
comparison must not depend on cosmetic differences in equivalent expressions.
A small internal representation suffices; no general unit-conversion library is
required. Preserve legacy output labels in v1.

Examples establishing the convention:

- Level 450 bp / absolute-change SD 30 bp = 15 risk units.
- Level 450 bp / percentage-change SD 5% = 90 bp/%; percentage changes are stored
  numerically as 5, not 0.05. No hidden factor of 100.
- Absolute change 20 bp / percentage-change SD 5% = 4 bp/%.
- Percentage change 2% / absolute-change SD 10 bp = 0.2 %/bp.
- Level 450 bp / beta 2 estimated from target/reference percentage changes =
  225 bp, because that beta is dimensionless.
- A beta estimated from target bp changes on reference price-point changes has
  units bp/point; dividing a bp numerator by it produces reference points.

Pair differences require equal transformed units. Equal dimensionless units with
different risk conventions are mathematically comparable; explain the economic
difference instead of inventing an additional method whitelist.

### 5. Calculate the relationship

- Standalone: x(t) = u_A(t).
- Difference: x(t) = u_A(t) − u_B(t).
- Ratio: x(t) = u_A(t) / u_B(t). Exactly zero denominator is unavailable. A finite
  negative or very small nonzero denominator remains inspectable with its value
  and sign visible; nonfinite arithmetic is unavailable.
- Regression residual: fit u_A = a + b × u_B on eligible prior fitting-window
  observations, excluding the latest observation, and return
  x(t) = u_A(t) − (a + b × u_B(t)). Retain the current intercept fit, sample/coverage
  requirements and descriptive retrospective residual-history convention.

Ratio units are the quotient; regression residual units are those of u_A. A
negative ratio or residual does not by itself say which exposure is attractive.
Preserve fit diagnostics and explicit insufficient/constant-input failure states.

### 6. Apply optional result Z-score

Available for every v2 calculation/measure/adjustment combination. Build the
reference sample from eligible completed x values within Reference history,
excluding the latest observation. Compute z(t) = (x(t) − mean(x_history)) /
sample_SD(x_history). Retain current minimum history and zero-dispersion handling.

Use the current reference throughout the displayed history, preserving the
current retrospective convention. Preserve unstandardized x values and unit in
the result and exports. Reference standardization follows the relationship;
it never standardizes inputs separately.

Z-score availability does not certify stationarity, denominator stability or
mean reversion. The skill and contextual help explain those distinctions.

### 7. Report changes and findings without changing existing meanings

Retain the current distinction: with Measure Level, the reported `change` is
the Frequency change in the completed result; with Change/Percentage change,
it reuses the current measured result. Make the labels understandable rather
than silently turning the latter into an acceleration statistic.

Preserve comparison behaviour that holds the previous fit/Z-score reference fixed
when distinguishing market movement from reference recalibration. Version/definition
changes must not generate a false new market finding. This task does not redesign
rolling-risk recalibration attribution; preserve existing behaviour and evidence.

## Evidence, serialization and integration

Retain raw inputs, transformed inputs, risk scales, measurement endpoints, resolved
references, estimation basis, sample dates/counts, fit, unstandardized results and
standardization reference. Extend evidence fields only where needed; older records
must deserialize through backward-compatible defaults.

Chart captions, measured-input views, Source and chart details, CSV exports and
Idea snapshots must describe the actual level/change numerator and actual risk
basis. A new level-over-risk analysis must not appear as “weekly change” merely
because a risk estimator is active. Regression scatter uses transformed inputs
and the corresponding fit, as before.

Reuse the existing definition-resolution/evaluation interface as the main seam.
Concentrate effective-measure, unit and validation rules in the analytics/domain
modules so preview, monitoring and retained-evidence calculations agree. Avoid
duplicating mathematical eligibility rules in JavaScript; UI conditions primarily
control visibility and explanation, while the backend is authoritative.

## Acceptance criteria and tests

Test observable definitions/results through existing evaluation and HTTP/persistence
interfaces. Use small hand-verifiable data for numerical examples and real browser
interaction for conditional controls. Do not mirror private implementation steps.

1. A parameterized v2 fixture covers all 4 × 3 × 5 × 2 = 120 basic combinations,
   using compatible units and sufficient nondegenerate data. None fails solely
   because its calculation/measure/adjustment/Z-score combination is disallowed.
2. The same shared-method matrix covers serialization/validation; representative
   combinations additionally pass Library and Investigation preview/save/reopen.
3. Standalone-level and level-ratio Z-scores match hand-computed reference values.
4. Ratio-of-changes Z-score is allowed; zero-denominator observations are excluded
   with an explicit limitation rather than converted to zero or carried forward.
5. All four active methods support a level numerator without converting it to a
   change. Tests verify both absolute and percentage risk-estimation bases.
6. Changing today's input cannot alter its same-date prior-only risk estimate.
   Tests verify the Level cutoff rule and a reference-only estimator when the
   level numerator has no valid historical change baseline.
7. Follow versus explicit estimation basis behaves predictably after numerator
   Measure changes; per-input overrides remain independent and reproducible.
8. Unit examples above pass, including percentage-point scaling, beta unit
   cancellation, composite units and incompatible-unit differences.
9. Common-divisor ratio cancellation and self-beta invariance hold; negative beta
   retains its sign. Direct and optimized estimator paths agree where applicable.
10. Zero/near-zero scale, sparse/stale history, constant regression input, missing
    observations and nonfinite results remain explicit unavailable cases.
11. Level-with-scaling fetches enough warm-up through draft preview, ordinary
    evaluation and Latest from captured evidence; external references are included.
12. Legacy fixtures without the new fields preserve previous outputs and labels.
    Old Snapshots survive deserialize/restart/export and Latest retains v1.
13. A v2 feature applied to a legacy draft records an explicit new contract;
    comparisons across changed definitions do not report a new market event.
14. The UI separates Type and pair calculation, hides only irrelevant controls,
    and never silently changes Measure or removes Z-score.
15. Both surfaces show the same effective formula/units for the same definition.
    Custom per-input settings, shared settings and type toggling survive editing.
16. A delayed preview cannot overwrite the latest draft result; previous charts
    retained after failure are clearly identified as belonging to older settings.
17. Monitoring is separate; meaningful formula/unit changes clear optional move
    thresholds with explanation and do not silently toggle monitoring or save.
18. Updated keyboard-accessible controls pass browser checks for a level/volatility
    analysis, a ratio Z-score, a regression with per-input basis and invalid data.
19. The bundled skill, human guide and risk/calculation documentation match the
    new capabilities. Distinguish recommendations from constraints and preserve
    the current known cadence limitations rather than implying they were fixed.
20. Appropriate source tests, type checks, JavaScript syntax checks, fresh wheel/
    sdist builds and the existing distribution inventory pass. Verify skill
    portability remains intact. Report exact unverified target/live-data behaviour.

## Out of scope

- Arbitrary event/cycle selectors, event-cohort filtering or configurable ratio
  denominator floors. Keep denominator evidence/guidance; do not imply these
  proposed later controls exist.
- New provider transformations, FX hedging, duration neutralization, index
  rebasing, log changes, winsorization or automatic economic classification.
- Separate per-input numerator measures or independent risk-estimation Frequency.
- Cadence-aware monthly-only regression support, calendar redesign, nonoverlapping
  return sampling or changes to existing freshness eligibility.
- New robust/quantile/cointegration regressions, portfolio VaR/ES, backtesting,
  causal inference or new monitoring/calibration models.
- A generic unit-conversion engine, release/version publication, unrelated UI
  redesign, or wholesale editorial refactoring of the skill.

## Delivery

Implement in the current checkout while preserving prior work. Update domain
terminology narrowly where necessary: Risk Adjustment can now scale input levels
as well as changes/returns using an explicitly specified change-based estimate.
Keep Frequency and Comparison Basis terminology consistent with CONTEXT.md.

Report completed acceptance criteria, validation results, changed files and any
specific limitations. Do not report completion on the strength of removing
validators alone; the preview, evidence and saved-calculation semantics must agree.
