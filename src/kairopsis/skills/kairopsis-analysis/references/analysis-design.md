# Designing an Analysis from its economic question

This guide helps an agent choose a defensible definition without limiting the
user to a preset list. A mathematically defined specialist analysis can be useful
even when it is not the usual starting point. Explain its interpretation and
trade-offs. Availability, economic suitability and data sufficiency are separate
judgments.

Read the relevant branch rather than treating every parameter as a decision the
human must make. The [combination map](combination-map.md) supplies the exhaustive
examples; the [application contract](application-contract.md) supplies the mapping
to the current engine. Combination classifications are analytical judgments;
worked values are illustrative, not observed market readings.

## Contents

- [Start with the question](#start-with-the-question)
- [Select and shape the inputs](#select-and-shape-the-inputs): [identity](#identity-and-comparison-basis), [units/returns](#units-index-bases-and-return-semantics), [dates](#dates-and-sampling), [event samples](#event-samples), [transformations](#transformations-that-change-the-question).
- [Choose calculation order and measure](#choose-calculation-order-and-measure)
- [Choose risk scaling and references](#choose-risk-scaling-and-references)
- [Choose histories and Frequency](#choose-histories-and-frequency)
- [Choose result standardization](#choose-result-standardization)
- [Separate monitoring from calculation](#separate-monitoring-from-calculation)
- [Worked starting points](#worked-starting-points): [quoted compensation](#compare-quoted-credit-compensation), [credit shock](#compare-the-size-of-a-credit-shock), [sector return](#explain-a-sector-return), [pass-through](#examine-policy-pass-through), [tail stress](#compare-stress-relative-to-historical-tails), [compensation/risk](#examine-compensation-per-unit-of-movement-risk).
- [Preview and retain the definition](#preview-and-retain-the-definition)

## Start with the question

Define the observation that would help the user form or challenge a Relative
Value View. “Is HY cheap?” is underspecified: it could mean a high standalone
spread, a wide HY–IG gap, a high HY/IG multiple, or a positive residual after
accounting for a historical relationship. These produce different evidence.

| Question | Useful starting definition | What it cannot establish alone |
| --- | --- | --- |
| What compensation is quoted? | Standalone spread level | Expected return or compensation sufficient for the risk |
| How much additional compensation does A offer? | Difference of comparable spread levels | Hedged profit after duration, currency and financing costs |
| How large is A relative to B? | Ratio of meaningful levels | An investment-performance comparison when index bases are arbitrary |
| Which market repriced more? | Difference of absolute changes | Relative shock size when normal variability differs |
| Which move was larger for that market? | Difference of each input's volatility-scaled changes | The standard deviation or risk of a long-short portfolio |
| Which exposure performed better? | Difference of percentage changes in comparable total-return indices | Implementable funded portfolio P&L without weights and costs |
| Did A depart from its usual relationship with B? | Regression residual on appropriate levels or changes/returns | Causal explanation or persistent alpha |
| What fraction of B's change passed through to A? | Ratio of changes over a defined episode | A stable fitted beta or an all-date screening statistic |
| How unusual is the result? | Historical percentile or final-result Z-score | Probability of reversal or investment recommendation |

For a pair, identify the ordered inputs explicitly: A minus B, A divided by B,
or dependent A explained by B. A positive result has a different meaning for
spread widening and investment returns. Write that meaning in the definition.

## Record economic rationale

Draft `economic_rationale` from the user's investment question: why examine this
series or compare these exposures, what the result could mean, and which
assumptions or alternative explanations qualify that reading. Preserve explicit
user reasoning; mark assumptions and unresolved context honestly. A statistical
extreme alone supplies no economic justification.

For example: “Compare A's credit spread with B's in the same currency to examine
whether A offers more compensation. A positive A-minus-B gap means more quoted
spread; differences in credit quality, duration or liquidity could explain it.”
This describes a question to investigate, not a finding that A is attractive.

When revising a definition, review whether its rationale still fits. Preserve
text on unrelated changes and revise it with an authorized change of research
question. Empty rationale is supported; missing context need not block an
otherwise specified task. Follow the [field and capture rules](application-contract.md#economic-rationale)
for saves, older applications and interpretation of historical evidence.

## Select and shape the inputs

### Identity and Comparison Basis

Resolve actual source, instrument, field and provider parameters. Establish units,
currency, reference curve, tenor/duration, rating/sector composition, treatment of
options, and whether income is reinvested. These need not all match: differences
may be the very subject of investigation. State them rather than treating equal
unit labels as proof of economic comparability.

For credit-credit comparisons across currencies, the Relationship Family remains
credit-credit. A common currency or reference curve requires an explicit provider
series or transformation; choosing a metadata label does not perform conversion.
FX hedging, swap-curve rebasing and duration matching need their own conventions
and data. A raw cross-market gap can still be descriptive if labelled accordingly.

### Units, index bases and return semantics

Convert observations, not just labels. One percentage point is 100 bp. If one
provider supplies a yield/spread in percent and another in bp, perform the
conversion upstream before an absolute difference.

An index's raw point level depends on its base. Comparing total-return index
percentage changes is usually appropriate for interval performance. Comparing
cumulative wealth paths needs a stated common investment date and common base;
rebasing to 100 changes the question to growth since that date. Use an existing
transformed series or prepare a documented one through the established provider
workflow; the current measure selector does not rebase index levels.

Percentage change in a total-return index is index return; in a price index it
is price return; in a spread it is proportional repricing. A spread changing
100 → 120 bp is +20 bp and +20%, not a +20% bond return. Proportional spread moves
can be economically useful; approximate spread-driven return also needs spread
duration.

For yields/spreads that approach or cross zero, absolute changes often retain a
clearer interpretation. Ordinary growth rates around zero can be explosive or
undefined; check the engine's
[baseline eligibility](application-contract.md#dates-and-estimation).

### Dates and sampling

Align actual observation dates and measurement endpoints. Inspect market holidays,
time zones, stale observations and differing closing times. Forward filling a
non-trading day creates a different data process; it must not masquerade as an
observed zero move. The current engine's date rules are described in the
[application contract](application-contract.md#dates-and-estimation).

For non-overlapping periods, cumulative policy cycles, event windows or intraday
responses, define shaping separately and verify the application can consume it.
For precomputed period returns, Level preserves the supplied return; another
percentage change would answer a different question. Neither choice establishes
cadence support: check [sampling, fit freshness and monitoring eligibility](application-contract.md#dates-and-estimation),
especially for monthly-only observations. Report a cadence gap, obtain suitable
observed data or specify the needed engine change; forward-filling returns would
manufacture observations.

### Event samples

For a decision-week or other event comparison, define the interval endpoints and
event calendar. Calculate both moves from the retained observation history,
then select intervals using the event condition and material-denominator rule.
Filtering raw levels first can remove required measurement baselines. Apply the
same eligibility definition to the current observation and prior comparison
history before computing ranks or Z-scores. Sufficient daily observations do not
establish sufficient eligible events.

If supplying precomputed eligible moves upstream, use Measure Level to preserve
them; another Change would transform them again. Verify
[sparse-cadence support](application-contract.md#dates-and-estimation) and
[monitoring capability](application-contract.md#monitoring-rules) separately.

### Transformations that change the question

Log changes, FX conversion/hedging, duration neutralization, common-start rebasing,
event filtering, seasonal adjustment and outlier treatment are substantive
choices. Preserve their conventions and provenance. The current selectors do not
silently provide these transformations. Winsorizing a tiny-denominator ratio may
conceal the problem; a stated denominator rule or a different question is usually
more informative.

Choose shaping because the economic question requires it, not to manufacture
normality, improve an attractive backtest or make a result cross a threshold.

## Choose calculation order and measure

Use the [input-first pipeline](combination-map.md#read-the-calculation-in-the-correct-order)
to distinguish the intended statistic from a similarly named control.

Write out ambiguous cases:

| Intended meaning | Formula | Relationship to current selectors |
| --- | --- | --- |
| Difference between moves | ΔA − ΔB | Difference + Change |
| Change in a level gap | Δ(A − B) | Same result as above only with identical endpoints and no input scaling |
| Ratio between moves | ΔA / ΔB | Ratio + Change |
| Change in a level ratio | Δ(A / B) | Different operation; not Ratio + Change |
| Return difference | rA − rB | Difference + Percentage change, using appropriate index levels |
| Growth in relative wealth | (1 + rA) / (1 + rB) − 1, with decimal returns | Different from rA/rB; requires an explicit relative-wealth series or transformation |
| Deviation from a fitted relationship | A − (a + bB), on selected measured inputs | Regression residual |

Use regression levels for a justified level relationship; examine trends,
structural changes and stability before interpreting the residual as mispricing.
For a co-movement question, changes or returns often match the question more
directly. A high R-squared by itself is not a reason to prefer either model.

A question relating credit-spread changes to equity returns needs independent
input transformations. Check [shared-measure constraints](application-contract.md#version-and-combination-rules)
before choosing controls; explicit supplied-series shaping may be required.

## Choose risk scaling and references

Begin unadjusted when native economic magnitude answers the question. Adjustment
should introduce a named comparison, not an automatic claim of greater accuracy.

| Method | Select it for | Reference choice | Parameters that matter |
| --- | --- | --- | --- |
| Volatility | Move size relative to usual variability | Each input itself for own-risk shocks; common reference for common-risk units | Frequency, lookback, equal/exponential weighting, half-life |
| Beta | Movement per unit of sensitivity to a named reference | An economically relevant common factor; self-beta only when intentionally leaving the benchmark leg unchanged | Same measured interval, aligned pairs, lookback, beta magnitude/sign/stability |
| VaR | Fraction of a historical adverse-move threshold | Own input for own-tail comparison; named external reference for reference-tail units | Downside direction, confidence, Frequency, lookback, tail sample support |
| ES | Movement relative to average historical tail severity | Same distinction as VaR | Same controls plus sensitivity to sparse/extreme tail observations |

Volatility scaling divides the move by SD without subtracting its mean. Beta
scaling divides by a signed slope without subtracting the benchmark's move or
intercept. VaR/ES scale by the selected series' adverse moves, not an inferred
portfolio loss. See the applicable [worked combination](combination-map.md#examples-for-every-defined-base-combination) before describing
any of these as risk-adjusted performance.

Choose downside from the exposure and question: increasing spreads may represent
stress for a long credit exposure; decreasing total-return indices represent
losses. The engine retains the original numerator sign. Therefore positive
spread stress and negative return stress can each be adverse. Comparing both
as a single directional stress score needs explicit sign shaping.

Use matched conventions for pair comparisons unless the differing convention is
deliberate. Each input's own volatility and an external common volatility answer
different questions. Check [cancelling scales and self-beta](combination-map.md#redundant-settings-rather-than-invalid-economics)
when an adjustment may leave the intended result unchanged.

Beta near zero or changing sign may be statistically computable but unsuitable
as a stable divisor. Examine estimates rather than relying on the engine's
numerical-zero threshold. A negative stable beta can be meaningful for an inverse
exposure; state how that changes the output's sign.

Adjusted levels need two explicit decisions: which level remains the numerator,
and which changes/returns estimate its risk denominator. Use
[estimation-measure fields and unit rules](application-contract.md#riskadjustment-fields)
to implement that separation. Preview the composite units and resolved basis.

## Choose histories and Frequency

The app has three separate analytical histories and a display range. Choose them
by purpose rather than copying one number into all four.

| Setting | Purpose | Selection considerations |
| --- | --- | --- |
| Frequency | Interval of each change/return and its risk estimate | Match the decision horizon and data cadence; use native same-frequency estimates rather than automatic annualization |
| Risk-estimation history | Estimate the scale available before each measured move | Recency versus stability; market regime, missing data, beta noise and tail evidence |
| Fitting window | Estimate the pair relationship | Relevant regime, sample coverage, structural breaks, residual stability and out-of-range explanatory inputs |
| Reference history | Describe percentile or Z-score of the completed result | The historical comparison the user actually means: recent regime, full cycle, or longest comparable history |
| Display range | Select what is visible | Readability and context; it does not change estimation |

Longer histories improve sample size but may mix incompatible regimes. Shorter
histories react faster but can leave estimates unstable. “Longest available”
depends on source inception and common eligible dates; it is not a claim that
all available observations are economically comparable.

For exponential volatility, half-life is measured in weekday sessions in this
engine, independent of Frequency. Equal weighting gives each eligible move equal
weight. Choose the responsiveness required by the question; inspect sensitivity
to a plausible alternative if the choice changes the conclusion.

For tail methods, inspect actual tail support. At 95% confidence, 60 observations
provide roughly three tail observations; at 99%, fewer than one full observation
lies in the nominal 1% tail. Fractional weighting is an estimator convention,
not new information. Overlapping monthly observations also share most of their
underlying days. The minimum sample setting is a computational floor, not proof
of economic or statistical adequacy.

A reasonable first preview may use the installed defaults while clearly labeling
them provisional. Replace that convenience with a reasoned choice before calling
the definition calibrated. Do not present a universal three-year/weekly/95% recipe
as appropriate for all markets.

Before interpreting a displayed move or setting a movement threshold, resolve
the returned [change-field meaning](application-contract.md#dates-and-estimation).

## Choose result standardization

Retain original result units when absolute magnitude matters. Add a Z-score when
the question concerns deviation from the result's own historical mean. Inspect
the unstandardized result alongside it so an economically tiny deviation is not
mistaken for a material opportunity.

An empirical percentile reports rank within the reference history; Z-score
reports distance from its mean in SD units. Both depend on the chosen sample.
Z-scoring does not make the distribution Gaussian. A Z-score threshold and a
percentile threshold need not identify the same observations.

Classify a result as extreme against a stated, purpose-appropriate rule. When no
such rule is established, report its score and reference history descriptively;
an illustrative ±2 cutoff alone does not establish that a result is usual or unusual.

Check the [fixed-versus-rolling scaling rules](combination-map.md#redundant-settings-rather-than-invalid-economics)
before treating risk adjustment plus Z-score as redundant. Inspect the preview's
[reference and fit timing](application-contract.md#dates-and-estimation) before
using historical chart values as evidence of past signals.

For ratios of moves, use the [event-sample requirements](#event-samples) for both
Z-scores and percentile monitoring. If the engine cannot define that sample, describe the
current episode without claiming an all-date Z-score is a reliable extreme-value
signal. A level-ratio Z-score can instead have a clear descriptive meaning when
the denominator remains economically meaningful; check version support.

## Separate monitoring from calculation

First verify what the result measures. Then decide whether to monitor it, which
conditions matter, and in what output units. A Flag draws attention for
investigation; it is not an investment instruction.

Check [monitoring rules and exact threshold boundaries](application-contract.md#monitoring-rules)
against the intended trigger, particularly when the user cares only about widening
or underperformance. Symmetric extremes and one-sided policy rules answer
different monitoring questions.

Changing measure, adjustment or standardization changes the units or distribution.
Reassess thresholds accordingly. A default ±2 Z-score or 95th-percentile rule is
illustrative until the user's purpose, reference data and observed behaviour
justify it. Leave monitoring off when the request is only exploratory; honor an
explicit monitoring request while reporting unresolved calibration or data issues.

## Worked starting points

These are recipes to adapt, not a list of permitted combinations.

### Compare quoted credit compensation

Question: is USD HY offering unusually more spread than USD IG?

Use compatible HY and IG OAS Data Series in bp. Start with Difference, Level,
no input adjustment. Compare the native gap with its history; add Z-score when
supported and useful. Explain the rating/duration/composition differences rather
than interpreting a wide gap as automatic cheapness. Choose reference history
for the relevant credit regime. Frequency still controls the app's reported
change in the completed level gap.

### Compare the size of a credit shock

Question: did HY widen more than IG relative to their own normal weekly moves?

Use Difference, Absolute change, Weekly, each input's own volatility. Choose the
risk lookback and weighting for the desired regime responsiveness. A positive
result means a larger HY shock in own-volatility units. Optional final Z-score
answers whether that difference itself is unusual. Neither statistic is the
volatility or P&L of a duration-neutral credit trade.

### Explain a sector return

Question: did a bank-sector index outperform its usual relationship with the
broad equity market over the month?

Use comparable-currency total-return indices, dependent banks and explanatory
broad market. Start with Percentage change, Monthly, Regression residual, no
input scaling. Choose the fit window for the relevant regime and inspect sample,
R-squared, residual size and extrapolation. Add Z-score for residual unusualness.
The month-on-month observations overlap at daily endpoints in the current engine.

### Examine policy pass-through

Question: what share of a policy-rate rise passed through to deposit rates?

Define the policy episode and endpoints, use comparable rate units, and calculate
Δdeposit rate / Δpolicy rate. Keep the material policy move visible. This is a
realised response ratio, distinct from the engine's OLS beta adjustment. If the
episode exceeds the supported measurement windows or needs event selection,
record that shaping/capability requirement instead of substituting a daily ratio.

### Compare stress relative to historical tails

Question: which credit market's weekly widening used more of its own typical
tail-widening scale?

Use Difference, Absolute change, Weekly and ES with increasing values as downside
for both long-credit interpretations. Match confidence and estimation conventions;
inspect tail support and the actual scales. The result compares fractions of
own tail widening, not portfolio ES. Use VaR instead if the question concerns a
quantile threshold rather than average tail severity.

### Examine compensation per unit of movement risk

Question: is HY spread high relative to its spread-change variability?

Specify the intended ratio explicitly, such as current OAS / prior weekly
spread-change SD. This retains a level numerator and uses change risk as its
denominator. In v2 choose Standalone, Level, Weekly, Volatility, Each series
itself, and Estimate risk from Absolute changes. Check the prior sample and scale.
Switching the numerator to a weekly change would instead answer a shock-size question.

## Preview and retain the definition

Check the actual preview, including unavailable values and source freshness.
Trace a representative observation from raw inputs through the transformations to
the result. Verify signs, units, dates and denominator sizes; examine estimation
samples and limitations. An accepted JSON payload alone establishes none of these.

Return a compact record with the question, ordered inputs and Comparison Basis,
shaping, formula, settings/rationale, interpretation of positive/negative values,
preview evidence, limitations and saved/monitoring state. Retain it where the user
asked: retain Economic Rationale in the supported Analysis field; keep the wider
record in an Idea note or requested research record. Check
[rationale support](application-contract.md#economic-rationale)
and [persistence rules](application-contract.md#interpretation-and-persistence-checks)
when retaining rationale, saving defaults or revisiting a Snapshot.
