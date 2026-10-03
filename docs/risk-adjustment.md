# Risk adjustment

Investigation uses the Risk adjustment side panel. Changes there are exploratory; **Edit defaults in Library → Use exploratory settings → Save defaults** explicitly adopts them for that Analysis. Opening and monitoring use saved defaults. Idea Snapshots preserve the resolved references, settings, raw observations, transformed inputs and historical scales. Latest uses the captured definition even after catalogue edits/deletion.

## Controls and evidence

Reference series can be each input itself, a common named series or an external catalogue series. Customize per series exposes independent references/methods/calibration. Each estimator has a lookback; volatility adds equal/exponential weights and half-life, while VaR/CVaR add confidence and downside direction. Frequency belongs to the Analysis and is daily, weekly or monthly. Self-beta is allowed, so both inputs can be adjusted to the first input.

Legend click toggles a trace; double-click isolates it. Axes stay fixed and hidden labels remain dimmed. Visibility changes presentation only. Save to Idea and image exports preserve the selected visibility and scales; older Snapshots remain readable. Shared source metadata and adjustment summaries appear once in the footnote, with full calibration and estimates under Source and chart details.

## Calculation contract

Adjustment applies to each measured input before the Standalone or Pair calculation. The Measured / adjusted series chart compares the individual inputs; Analysis shows the selected difference, ratio or regression residual. Underlying series shows original levels. Display range never changes estimation.

Frequency uses the existing calendar convention: daily = previous weekday; weekly = seven calendar days; monthly = previous calendar month with day clamped. Weekly/monthly baselines are backward-only within three calendar days. Both endpoints require actual observations on their row dates; no fill. Weekly/monthly moves are overlapping observations sampled at daily endpoints. No square-root-of-time conversion or annualization is applied.

Change is `current − baseline`, in supplied units. Percentage change is `100 × (current / baseline − 1)` and requires a positive baseline. This is a percentage change in the supplied measure, not a total investment return inferred from spread levels. To examine supplied cumulative return series, choose their configured Data Series.

For each date, the risk sample ends at the measured interval's start and begins the selected number of calendar years earlier. The current measured interval is excluded. At least 60 valid prior moves are required by default. Estimation history older than seven calendar days at that cutoff is unavailable. Beta uses paired moves with identical start/end dates. Source freshness qualifications still apply to findings.

| Method | Divisor / convention |
| --- | --- |
| None | 1; preserves measured changes. Existing Analyses retain unadjusted levels by default. |
| Volatility | Demeaned sample standard deviation. Equal weights use `N−1`. Exponential weights use `w = 2^(−age/half-life)`, with age/half-life in weekday sessions; normalized weighted variance uses denominator `Σw − Σw²/Σw`. |
| Beta to reference | Intercept OLS slope `Σ(x−x̄)(y−ȳ) / Σ(x−x̄)²`; y is the target and x the reference. Self-beta equals 1 when reference moves vary. Signed negative beta is retained; absolute beta below `1e−12` is unavailable. |
| Value at Risk | Historical loss quantile: sorted loss at `ceil(confidence × N)`. Confidence is converted from percent. Increasing or decreasing values explicitly defines downside. |
| Expected Shortfall (CVaR) | Mean of the worst `(1−confidence) × N` losses, including proportional weight for a fractional boundary observation. Uses the same downside direction as VaR. |

The input is divided by its estimated scale without subtracting a drift or intercept. Volatility/VaR/ES yield dimensionless **risk units** and require matching target/reference units, or percentage changes. Beta yields the reference's units. Pair differences require identical resulting units; ratios preserve the units of the quotient. Zero variance, missing estimates, near-zero beta and nonpositive downside scales produce unavailable values. Per-series customization can therefore produce incompatible differences; the UI retains the last accepted evaluation and explains the incompatibility.

VaR/ES describe downside moves of the selected Data Series, not portfolio P&L or capital requirements. High confidence with few observations has little tail evidence; disclosed sample counts and periods are essential. These historical estimates are comparisons, not calibrated trading or investment recommendations.

## Defaults, thresholds and continuity

None preserves existing level behavior and older stored evidence remains readable. Selecting an adjustment from a level Analysis switches Measure to Change. Changing risk configuration or Measure clears exploratory move/materiality thresholds, preventing old measurement-unit rules from being reused silently. Library exposes explicit thresholds in the resulting Analysis units; production threshold calibration remains separate.

References are resolved and fetched through Metapyle alongside the inputs. Reference edits advance dependent Analysis revisions; deletion is prevented while an active Analysis uses that reference. Captured definitions retain the binding needed for Latest evaluation independently of active catalogue entries. Snapshots contain raw reference data in JSON; CSV/clipboard exports additionally include measured inputs, scales and period starts.

## Sources and scope

Definitions follow [BIS market-risk terminology](https://www.bis.org/committees/bcbs/basel-framework/standard/mar?allChapters=true&q=PPP0QQQ&sort=PPP1QQQ&year=PPP2QQQ) for VaR/ES, [NIST least squares](https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd431.htm) for intercept regression, and [NIST exponential smoothing](https://www.itl.nist.gov/div898/handbook/pmc/section4/pmc43.htm) for decaying weights. The finite-sample correction, empirical quantile, fractional-tail and calendar conventions above are explicit implementation choices; no regulatory methodology is claimed.

Mock tests establish numerical and persistence behavior. Provider calendars, actual source semantics, estimator suitability and risk-adjusted monitoring thresholds require validation in the target environment.

The [verification guide](verification.md) describes source and installed-package checks. A source test result does not establish acceptance for a different operating system or data provider.
