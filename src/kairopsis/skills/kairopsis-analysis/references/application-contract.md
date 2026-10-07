# Mapping an Analysis to the current application

This is the contract inspected on 6 October 2026. Source checkouts and installed
distributions bearing the same development version may have different features.
For existing evidence, resolve the captured contract and settings first. For new
or revised definitions, inspect the running `/openapi.json`, installed models and
preview behaviour. This reference owns version, field, date and persistence rules;
economic examples in other references do not establish installed capability.

## Contents

- [Data and operations](#data-and-operations): discover, preview, save and reconcile revisions.
- [Analysis fields](#analysis-fields): map a definition to its payload.
- [RiskAdjustment fields](#riskadjustment-fields): active scaling, estimators and units.
- [Version and combination rules](#version-and-combination-rules): new definitions and captured legacy evidence.
- [Dates and estimation](#dates-and-estimation): endpoints, missing results, sparse cadence and retrospective charts.
- [Monitoring rules](#monitoring-rules): exact threshold boundaries and input-filter limitations.
- [Interpretation and persistence checks](#interpretation-and-persistence-checks): evidence, save/readback and monitoring.

## Data and operations

Use the app's Library UI or its running application interface. Library owns the
catalogue and provider bindings; writing catalogue JSON/YAML directly bypasses
validation, revision handling and consistency checks.

| Operation | Current interface | Meaning |
| --- | --- | --- |
| Inspect series and analyses | `GET /api/library` | Discover actual IDs, definitions and revisions |
| Preview a series query | `POST /api/library/series/preview` | Body contains `series` and `period`; inspect raw observations/metadata |
| Preview a draft analysis | `POST /api/library/analyses/preview` | Body contains `analysis`, optional `series_drafts`, and `period`; no Library save |
| Preview changes to an existing analysis | `POST /api/analyses/{key}/preview` | Settings overrides; inspect schema/implementation for accepted shape |
| Save an analysis | `POST /api/library/analyses` | Save a definition referencing existing series |
| Save analysis with staged series | `POST /api/library/analyses/bundle` | `analysis`, `series_drafts`, `base_revisions`; preserve concurrency checks |
| Set monitoring | `PATCH /api/library/analyses/{key}/monitoring` | Explicit boolean monitoring state |

Use identifiers returned by the target application. Preserve user edits/revisions;
on conflict, reread the affected definitions and reconcile the intended changes.
Previewing may retrieve market data but does not authorize saving defaults,
enabling monitoring or changing unrelated records.

## Analysis fields

| Economic concept | Current field and values | Notes |
| --- | --- | --- |
| Standalone | `calculation: "level"`, one `series_ids` entry | The internal calculation name does not force Measure Level |
| Pair | `calculation: "difference"`, `"ratio"` or `"regression"`, two ordered IDs | IDs must differ; first is minuend/numerator/dependent input |
| Input measure | `settings.measure: "level"`, `"change"`, `"return"` | `return` means percentage change of the supplied values; shared across both inputs |
| Frequency | `settings.horizon: "day"`, `"week"`, `"month"` | Also sets completed-result change interval when Measure is Level |
| Calculation contract | `settings.calculation_contract: "input-pipeline-v1"` or `"input-pipeline-v2"` | Omitted means v1; new callers should explicitly request v2 |
| Result standardization | `settings.standardization: "none"` or `"zscore"` | Applied after calculation; all v2 combinations supported |
| Historical comparison | `settings.history_years` | Reference for percentile and result Z-score |
| Regression fit | `settings.fit_years` | Relevant to regression only |
| Shared input scaling | `settings.risk_adjustment` | A RiskAdjustment record applied to each input |
| Per-input scaling | `settings.risk_overrides` | Empty uses shared settings; otherwise one record per input, replacing shared settings |
| Monitoring | `monitored` | Separate from successfully defining or previewing the analysis |
| Extreme-value thresholds | `settings.upper_percentile`, `settings.zscore_threshold` | Symmetric lower/upper percentile tails or absolute Z-score rule |
| Move/materiality thresholds | `settings.move_threshold`, `settings.material_change` | Optional, positive, in completed analysis units |

Period fields currently accept 3 or 6 months (`0.25`, `0.5`), whole years 1–30,
or `"all"`. Inspect the installed schema for accepted values. Display/preview
`period` or chart range is distinct from reference, fit and estimation windows.

An Analysis has no arbitrary free-form rationale field in this version. Keep
the rationale in the requested research record or an Idea note; series have
descriptions for their own semantics/shaping. Use a concise Analysis name.

## RiskAdjustment fields

| Field | Values and purpose |
| --- | --- |
| `method` | `none`, `volatility`, `beta`, `var`, `es` |
| `estimation_measure` | Null/omitted follows input measure; `change` or `return` chooses an independent risk basis in v2. Follow resolves Level to absolute changes. |
| `reference_id` | Null uses this input itself; otherwise a discovered Data Series ID |
| `lookback_years` | Estimation history, using the period values above |
| `weighting` | `equal` or `exponential`; volatility only |
| `half_life` | Positive weekday sessions, up to 2520; exponential volatility only |
| `confidence` | Percent strictly between 50 and 100; VaR/ES only |
| `downside` | `increase` or `decrease`; defines loss direction for VaR/ES |
| `minimum_samples` | Computational sample minimum; current default 60, not an adequacy guarantee |
| `estimator` | Versioned calculation convention; current `historical-risk-v1` |

The engine divides each measured input by its scale without subtracting a mean
or intercept. Equal-weight volatility is sample SD; exponential volatility uses
decaying session-age weights with a finite-sample correction. Beta is the signed
intercept-OLS slope of target moves on reference moves. Historical VaR uses the
inverse empirical CDF; ES averages the worst tail with fractional boundary weight.

For v2, distinguish numerator unit U_n, target-estimation unit U_e and
reference-estimation unit U_r. Percentage estimation moves use `%` numerically
as percentage points, without a hidden factor of 100. Volatility/VaR/ES require
U_e = U_r and produce U_n/U_r. Beta produces U_n × U_r/U_e. Equal units cancel;
dimensionless inputs display `risk units`. Composite units such as `bp/%` remain
visible. Differences require equal transformed units; differing dimensionless
risk conventions are mathematically allowed and need economic interpretation.
Ratios simplify quotient units; residuals retain the dependent input's units.

## Version and combination rules

All 120 basic calculation/measure/method/output-scale combinations are supported
under `input-pipeline-v2`, subject to defined mathematics, compatible units and
adequate observations. Explicitly set `settings.calculation_contract` to
`"input-pipeline-v2"` for new API definitions. Newly created UI definitions use v2. Selecting level
scaling, explicit estimation basis, standalone-level Z-score or ratio Z-score in
a legacy draft promotes that draft to v2. A name-only edit preserves v1.

Omitted `calculation_contract` means `input-pipeline-v1`: active scaling requires
changes/percentage changes estimated on that same measure; Z-score is restricted
to differences, residuals and standalone changes. Its numerical/date/unit rules
remain preserved. Existing Snapshots/evaluations load with backward-compatible
defaults and retain v1 for Latest; changed definitions/contracts are incompatible
market baselines. Unsupported contract names fail explicitly.

Input measure and Frequency remain shared across a pair. Risk settings, including
estimation measure, may vary per input. Inactive None settings have no reference
dependency or numerical effect. Independent numerator measures/Frequencies,
event cohorts and configurable material-denominator floors remain unavailable.
Zero denominators are excluded; signed/small finite nonzero denominators remain
inspectable. Plain OLS remains descriptive, without a new causal/hedged/portfolio
interpretation.

Library and Investigation share Inputs → Measure → Scale inputs → Compare →
Historical context. Monitoring is a separate collapsed section. Meaningful
formula changes clear optional move/materiality rules and retain monitoring
enable state and extreme-rule parameters. Draft edits require an explicit save
to change Library defaults. A failed/delayed preview retains a labelled previous
chart without replacing the user's draft.

## Dates and estimation

Daily uses the previous weekday. Weekly uses seven calendar days; monthly uses
the previous calendar month with day clamping. Weekly/monthly baselines search
backward by up to three calendar days. Moves are sampled at daily endpoints and
therefore overlap. Native-date eligibility and exact-date pair alignment matter;
provider calendars/freshness still need verification.

Percentage changes require a positive baseline. Missing observations remain
missing unless an explicit upstream shaping convention supplies them; relabeling
units or Comparison Basis does not transform observations.

Risk samples end at the actual change numerator baseline; Level uses the nominal
Frequency target (previous weekday, seven days earlier or previous clamped month).
Risk moves are measured independently from the numerator and exclude the current
Frequency interval. Level needs only its native current observation, without a
change baseline for a reference-only estimator.
Beta samples align both endpoints. Near-zero beta, zero variance, nonpositive
tail scales, inadequate or stale estimation samples produce unavailable values.
All-history estimates use common eligible history according to the engine's
rules, not an unlimited economic history.

Regression is fitted on eligible observations before the latest point. The
current fit is then used retrospectively for plotted residual history. Z-score
uses eligible prior result history excluding the latest point; its current mean
and sample SD are applied throughout the chart. Neither chart is a historical
point-in-time strategy backtest. Read fit, adjustment and standardization
estimates and limitations returned by the preview.

The current regression additionally requires its newest prior sample within
seven days of the previous session, and fixed-window fitting requires a sample
near the window start. Monthly-only return observations can therefore be
economically suitable inputs but unavailable for this implementation's fit.
Supplying those returns as Measure Level avoids a second transformation; it does
not remove the cadence restriction. Weekday eligibility and latest-session
freshness also constrain low-frequency series and monitoring.

The returned `change` field depends on Measure: Level computes the difference in
the completed result over Frequency; Change/Percentage change reuse the current
measured analysis result. It is not always a second difference or acceleration.
This also affects the interpretation of movement thresholds.

## Monitoring rules

For eligible results, `standardization: "none"` flags percentile
`<= 100 - upper_percentile` **or** `>= upper_percentile`, including both boundaries.
Thus `upper_percentile: 90` includes both tails and equality at 10 and 90;
it cannot express a strict lower-only `< 10` condition.

With Z-score standardization, `abs(result) >= zscore_threshold` replaces the
extreme-percentile rule; displayed percentile remains descriptive. Optional
`move_threshold` tests `abs(change) >= move_threshold` using the returned
[change-field meaning](#dates-and-estimation). Move/materiality settings use
completed-result units; neither filters an input's denominator in native units.

The schema has no event-calendar filter, material-denominator floor or one-sided
percentile rule. If these define the requested alert, retain a proposed
calculation with monitoring off and identify the missing capability. An unrestricted
percentile is not a substitute for the requested eligible-event distribution.

## Interpretation and persistence checks

1. Inspect input identity, units, currency and Comparison Basis against the source.
2. Check measured endpoints and transformed inputs, then risk divisors and result.
3. Confirm fit/reference histories and sample support; inspect missing data,
   extrapolation, denominator instability and provider freshness limitations.
4. Read back the saved definition when saving was requested. A successful write
   is not evidence of a successful live evaluation.
5. Preserve captured evidence: Library defaults affect future evaluations;
   Snapshots retain their resolved definitions and observations.

Changes to measure, scaling or standardization require reconsidering the
[monitoring rules](#monitoring-rules) in the resulting units and distribution.
