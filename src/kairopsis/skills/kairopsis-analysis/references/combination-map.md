# Economic meaning of Analysis combinations

Research: 5 October 2026. Guidance updated: 6 October 2026. **A combination is meaningful only when its inputs, units, reference and economic question agree.** The dropdown labels alone cannot determine validity.

This map covers all **120 basic combinations**: 4 calculations × 3 input measures × 5 shared adjustment methods × 2 standardization choices. Standalone is counted as a calculation for enumeration; conceptually it has no pair calculation. Each of the 44 worked rows below has both an unstandardized and a Z-score interpretation, covering 88 settings. The remaining 32 settings combine levels with change-based adjustment and are mapped separately. Product support is separate from economic validity.

All numerical examples are **illustrative scenarios involving real markets**, not observed market readings. Specialised combinations are constructed diagnostics, not claims of established industry practice. HY = high yield; IG = investment grade; OAS = option-adjusted spread; bp = basis points. Example OAS inputs are assumed already converted into bp. Changing a unit label does not convert data.

Per-input method overrides and arbitrary references add configurations beyond 120; their compatibility rules appear below.

## Read the calculation in the correct order

The current [calculation contract](application-contract.md) is:

**Measure each input → divide each input by its risk scale → calculate Standalone, Difference, Ratio or Regression residual → optionally Z-score the completed result.**

For an input A:

- Level: `A(t)`.
- Absolute change: `A(t) − A(t−h)`.
- Percentage change: `100 × [A(t)/A(t−h) − 1]`. The app requires a positive baseline.
- Adjusted input: `uA = measured A / scale A`.
- Standalone: `uA`; difference: `uA − uB`; ratio: `uA/uB`; residual: `uA − (intercept + slope × uB)`.

Thus a ratio of changes is `ΔA/ΔB`, not `Δ(A/B)`. A difference of percentage changes is a return difference when inputs are total-return indices; it is not the percentage change in their level difference. In the current engine, the additional `change` field measures a change in the completed result when Measure is Level; with Change/Percentage change it reuses the measured analysis result. It does not then describe acceleration/deceleration.

## Overview of all settings

**Core:** clear routine question with appropriate inputs. **Conditional:** coherent specialist question; requirements below matter. **Event:** a material-denominator response ratio over a specified interval; unsuitable for unrestricted automatic screening. Level scaling is Conditional under v2: its risk basis is specified independently.

Each cell represents both **None and Z-score** standardization; the Z-score conditions in the next section apply.

| Calculation | Measure | None | Volatility | Beta | VaR | ES |
| --- | --- | --- | --- | --- | --- | --- |
| Standalone | Level | Core | Conditional | Conditional | Conditional | Conditional |
| Standalone | Absolute change | Core | Core | Conditional | Conditional | Conditional |
| Standalone | Percentage change | Core | Core | Conditional | Conditional | Conditional |
| Difference | Level | Core | Conditional | Conditional | Conditional | Conditional |
| Difference | Absolute change | Core | Core | Conditional | Conditional | Conditional |
| Difference | Percentage change | Core | Core | Conditional | Conditional | Conditional |
| Ratio | Level | Core | Conditional | Conditional | Conditional | Conditional |
| Ratio | Absolute change | Event | Event | Event | Event | Event |
| Ratio | Percentage change | Event | Event | Event | Event | Event |
| Regression residual | Level | Conditional | Conditional | Conditional | Conditional | Conditional |
| Regression residual | Absolute change | Core | Conditional | Conditional | Conditional | Conditional |
| Regression residual | Percentage change | Core | Conditional | Conditional | Conditional | Conditional |

These classifications guide recommendations, not availability; they do not certify arbitrary series combinations. An unrestricted ratio-of-moves Z-score does **not** become sound merely because its cell says Event.

## What standardization adds

**None:** retain the result's units and magnitude. **Z-score:** `(result − historical mean) / historical sample SD`, applied after the complete calculation. A score of +2 means two reference SDs above that result's mean, including for results already expressed in risk units. It does not imply a particular tail probability or mean reversion. [NIST definition](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/zscore.htm)

For example, a HY–IG spread gap of 350 bp with historical mean 300 and SD 25 has Z-score +2. A volatility-scaled gap of +1 with historical mean 0.2 and SD 0.4 also has Z-score +2. These answer different economic questions despite sharing the same Z-score.

- Standalone levels and level ratios: economically defensible as descriptive historical comparisons; supported by v2; scrutinize trends and reference suitability.
- Changes, percentage changes, differences and residuals: meaningful if the underlying calculation and reference history are meaningful.
- Ratios of changes/percentage changes: historical scoring needs an explicitly defined comparison sample and a material denominator rule. Without them, extremes can be denominator accidents. **V2 permits ratio Z-scores; the UI still provides neither event-cohort selection nor a material denominator floor.**
- Nonstationary/trending levels: a descriptive score is possible, but a stable “cheap/rich” or mean-reversion interpretation needs additional justification. Spurious level relationships are a known time-series problem. [Royal Swedish Academy scientific background](https://www.nobelprize.org/uploads/2018/06/advanced-economicsciences2003-1.pdf)
- Risk-adjusted then Z-scored is not automatically double counting: rolling risk scales change the input series; the final score measures unusualness of the resulting statistic.
- Current charts use a single current reference mean/SD retrospectively; regression history uses the current fit. These are not historical point-in-time signals or a backtest.

## Examples for every defined base combination

Each row covers two complete configurations: **Standardization None** uses the fourth column; **Standardization Z-score** uses the fifth. The same real-market example supplies the underlying economic justification for both. An asterisk on a Z-score interpretation denotes economic caution; v2 supports the calculation subject to data and numerical eligibility.

Unless otherwise stated: volatility/VaR/ES use each input's own history; beta uses the named common reference; frequency and estimation conventions are consistent. Examples of VaR/ES use 95% confidence solely for illustration.

### Standalone

| Measure and adjustment | Scope | Real-market example with illustrative values | None: interpretation and question | Z-score: interpretation and question |
| --- | --- | --- | --- | --- |
| Level / None | Core | US high-yield option-adjusted spread (OAS), e.g. 450 bp. | How much spread does this market offer over its reference curve? Level in bp; comparison still depends on credit quality, duration and options. | **\*** How high is the HY spread relative to its own reference-history mean? |
| Absolute change / None | Core | US HY OAS widens 20 bp over a week. | How much did credit pricing move? +20 bp means widening, not a 20 bp investment loss. | How unusual is this weekly spread widening? |
| Absolute change / Volatility | Core | HY OAS widens 20 bp; prior weekly-change SD is 10 bp: +2 risk units. | How large is the widening relative to typical weekly spread moves? No mean is subtracted. | How unusual is the volatility-scaled widening relative to past scaled widenings? |
| Absolute change / Beta | Conditional | HY OAS widens 20 bp; beta of its changes to a broad credit-spread reference is 2: +10 reference bp. | What reference-sized move corresponds to this HY move at its estimated sensitivity? This is not a residual or hedge P&L. | How unusual is the benchmark-equivalent spread move? |
| Absolute change / VaR | Conditional | HY OAS widens 20 bp; its prior 95% widening quantile is 30 bp: +0.67. | What fraction of the selected historical adverse-move threshold did this widening use? | How unusual is that fraction of the contemporaneous widening threshold? |
| Absolute change / ES | Conditional | HY OAS widens 20 bp; its prior average worst-5% widening is 45 bp: +0.44. | How large is the widening relative to the average historical tail widening? | How unusual is that widening relative to its contemporaneous tail scale? |
| Percentage change / None | Core | A USD corporate-bond total-return index rises from 100 to 101.2: +1.2%. | What was the index's holding-period return? For a spread input instead, this would be proportional spread growth. | How unusual is the index return versus its return history? |
| Percentage change / Volatility | Core | The corporate-bond total-return index gains 1.2%; prior same-frequency return SD is 0.6%: +2. | How large was the return relative to typical return variation? This single-period observation is not a Sharpe ratio. | How unusual is the volatility-scaled return versus past scaled returns? |
| Percentage change / Beta | Conditional | An equity-sector total-return index gains 3%; return beta to the broad equity index is 1.5: +2 benchmark percentage points. | What broad-market-sized return corresponds to the sector move? The benchmark's actual return has not been subtracted. | How unusual is this benchmark-equivalent return? |
| Percentage change / VaR | Conditional | The corporate-bond total-return index loses 1.2%; prior 95% loss quantile is 2%: -0.60. | How large was the loss relative to its historical loss threshold? The app keeps the negative return sign. | How unusually weak is the return after allowing for its changing loss threshold? |
| Percentage change / ES | Conditional | The corporate-bond total-return index loses 1.2%; prior average worst-5% loss is 3%: -0.40. | How large was the loss relative to typical historical tail losses? | How unusually weak is the return relative to its contemporaneous average tail loss? |

### Difference

| Measure and adjustment | Scope | Real-market example with illustrative values | None: interpretation and question | Z-score: interpretation and question |
| --- | --- | --- | --- | --- |
| Level / None | Core | US HY OAS is 450 bp and US IG OAS is 100 bp: a 350 bp gap. | How much additional spread does HY offer over IG? The gap includes differences in credit quality, duration, liquidity and options. | How wide is that spread gap relative to its own history? |
| Absolute change / None | Core | HY OAS widens 20 bp; IG OAS widens 5 bp: +15 bp. | Which spread widened more in absolute terms? With identical dates and no adjustment this is also the change in their spread gap. | How unusual is the weekly change in the HY–IG spread gap? |
| Absolute change / Volatility | Core | HY widens 20 bp with SD 10; IG widens 5 bp with SD 5: 2 - 1 = +1. | Which market had the larger widening relative to its own usual move size? +1 is a difference of input risk units, not one SD of the pair. | How unusual is the difference between their volatility-scaled widenings? |
| Absolute change / Beta | Conditional | HY and IG widen 20 and 5 bp; betas to the same credit-spread reference are 2 and 0.5: 10 - 10 = 0 reference bp. | Did either market move more after translating both into the same reference's sensitivity units? | How unusual is the gap between benchmark-equivalent spread moves? |
| Absolute change / VaR | Conditional | HY and IG widen 20 and 5 bp; own 95% widening thresholds are 30 and 10: 0.67 - 0.50 = +0.17. | Which widening used more of its own historical adverse-move threshold? Same tail convention required. | How unusual is the difference in fractions of widening thresholds? |
| Absolute change / ES | Conditional | HY and IG widen 20 and 5 bp; own average worst-5% widenings are 45 and 15: 0.44 - 0.33 = +0.11. | Which market had the larger move relative to its own typical tail widening? | How unusual is their difference in tail-scaled widening? |
| Percentage change / None | Core | USD HY and IG total-return indices gain 1.2% and 0.8%: +0.4 percentage points. | Which index outperformed over the interval? This is the return difference for equal reference notionals, before financing and implementation. | How unusual is the HY-minus-IG return difference? |
| Percentage change / Volatility | Core | HY and IG total-return indices gain 1.2% and 0.8%; own return SDs are 1.5% and 0.4%: 0.8 - 2 = -1.2. | Which index performed better per unit of its own return volatility? IG had the stronger scaled move despite the lower raw return. | How unusual is that difference in volatility-scaled returns? |
| Percentage change / Beta | Conditional | HY and IG index returns are 1.2% and 0.8%; betas to a common USD bond benchmark are 1.5 and 0.5: 0.8 - 1.6 = -0.8 reference percentage points. | Which index performed better after scaling to common benchmark sensitivity? Assumes the benchmark is economically appropriate for both. | How unusual is the difference in benchmark-equivalent returns? |
| Percentage change / VaR | Conditional | HY and IG returns are -1.2% and -0.8%; own 95% loss thresholds are 3% and 1%: -0.4 - (-0.8) = +0.4. | Which index suffered more relative to its own loss threshold? IG used more; positive result means HY was less negative on this scale. | How unusual is the return difference measured in each index's loss-threshold units? |
| Percentage change / ES | Conditional | HY and IG returns are -1.2% and -0.8%; own average tail losses are 4.5% and 1.5%: -0.267 - (-0.533) = +0.267. | Which index suffered more relative to its average historical tail loss? | How unusual is the difference in tail-scaled returns? |

### Ratio

| Measure and adjustment | Scope | Real-market example with illustrative values | None: interpretation and question | Z-score: interpretation and question |
| --- | --- | --- | --- | --- |
| Level / None | Core | US HY OAS is 450 bp and IG OAS is 100 bp: 4.5 times. | How many times the IG spread does HY offer? Positive, meaningful denominator and comparable spread conventions required. | **\*** How high is the spread multiple versus its own historical mean? A descriptive score, not evidence of mean reversion. |
| Absolute change / None | Event only | Over a policy-tightening interval, deposit rates rise 25 bp and the policy rate rises 100 bp: 0.25. | What fraction of the policy-rate increase passed through to deposit rates? This realised pass-through ratio is not OLS beta or proof of causality. | **\*** Only for a comparable set of intervals with material policy changes: how unusual is pass-through? |
| Absolute change / Volatility | Event only | In a credit-widening episode, HY moves 20 bp with SD 10; IG moves 5 bp with SD 5: 2 / 1 = 2. | Was the HY shock twice as large as the IG shock relative to each market's usual move size? Requires a material IG move. | **\*** Only within a consistently defined episode sample: how unusual is the ratio of scaled shocks? |
| Absolute change / Beta | Event only | In a widening episode, HY and IG moves are 20 and 5 bp; common-reference betas are 2 and 0.5: 10 / 10 = 1. | Are their realised moves proportional to their estimated benchmark sensitivities? A ratio of 1 indicates equal reference-equivalent moves. | **\*** Only with stable, nonzero denominator moves and usable betas: how unusual is relative sensitivity-scaled amplification? |
| Absolute change / VaR | Event only | In a widening episode, HY and IG move 20 and 5 bp; own widening thresholds are 30 and 10: 0.67 / 0.50 = 1.33. | Did HY use a larger fraction of its own stress threshold than IG? Useful as an episode diagnostic, not a standard valuation ratio. | **\*** Only for a comparable, denominator-bounded episode sample: how unusual is relative threshold usage? |
| Absolute change / ES | Event only | In a widening episode, HY and IG move 20 and 5 bp; own average tail widenings are 45 and 15: 0.44 / 0.33 = 1.33. | How do the moves compare as fractions of each market's typical tail widening? | **\*** Only within a comparable episode sample: how unusual is their relative tail-scaled shock size? |
| Percentage change / None | Event only | During an equity rally, a bank-sector total-return index gains 6% and the broad equity index gains 3%: 2. | How many times the broad-market return did banks deliver in this episode? This is realised amplification, not estimated beta. | **\*** Only for comparable, material benchmark moves: how unusual is the realised return multiple? |
| Percentage change / Volatility | Event only | Banks gain 6% with prior return SD 3%; the broad equity market gains 3% with SD 1%: 2 / 3 = 0.67. | Was the bank-sector move larger relative to its own usual size than the market move? Here it was smaller. | **\*** Only within a denominator-bounded episode sample: how unusual is relative volatility-scaled performance? |
| Percentage change / Beta | Event only | Banks gain 6% with beta 1.5 to the equity market; the market gains 3% with self-beta 1: 4 / 3 = 1.33. | Did banks amplify the market move more than their estimated beta would suggest? No intercept is removed. | **\*** Only with usable beta and material market returns: how unusual is the sensitivity-scaled return multiple? |
| Percentage change / VaR | Event only | Banks lose 6% with prior loss threshold 8%; the equity market loses 3% with threshold 4%: (-0.75) / (-0.75) = 1. | Did both losses consume the same fraction of their own historical downside thresholds? Both falling gives a positive ratio. | **\*** Only in a comparable loss-episode sample: how unusual is relative loss-threshold usage? |
| Percentage change / ES | Event only | Banks lose 6% with average tail loss 12%; the market loses 3% with average tail loss 6%: (-0.5) / (-0.5) = 1. | Did the losses have the same size relative to each market's typical tail loss? | **\*** Only within a comparable loss-episode sample: how unusual is relative tail-loss usage? |

### Regression residual

| Measure and adjustment | Scope | Real-market example with illustrative values | None: interpretation and question | Z-score: interpretation and question |
| --- | --- | --- | --- | --- |
| Level / None | Conditional | Fit HY OAS against IG OAS. HY is 450 bp while the fitted relation implies 420 bp: +30 bp residual. | Is HY wider than its historical relationship with IG would predict? Valid as a descriptive relationship; a fair-value or mean-reversion claim needs more evidence. | How unusually wide is the residual relative to its residual history? |
| Absolute change / None | Core | HY widens 20 bp while a regression on the same week's IG change predicts 12 bp: +8 bp. | Did HY widen more than the historical co-movement with IG would predict? Regression includes an intercept. | How unusual is the unexplained weekly HY widening? |
| Absolute change / Volatility | Conditional | Regress HY spread changes divided by their rolling SD on IG changes divided by their rolling SD. | Did HY experience an unusually large scaled shock after accounting for IG's scaled shock? Requires a reason to model state-dependent risk units. | How unusual is that residual between volatility-scaled spread changes? |
| Absolute change / Beta | Conditional | Scale bank and industrial credit-spread changes by their rolling betas to the same broad credit reference, then regress bank on industrial. | Do their reference-equivalent moves diverge beyond their historical relation? Rolling sensitivities can matter; fixed scaling adds no new standardized information. | How unusual is the residual relationship between the benchmark-equivalent spread moves? |
| Absolute change / VaR | Conditional | Regress HY widening divided by its prior 95% widening threshold on similarly scaled IG widening. | Is HY using more of its widening threshold than its historical relation with IG threshold usage predicts? This is ordinary OLS on scaled data, not tail or quantile regression. | How unusual is the unexplained difference in modeled widening-threshold usage? |
| Absolute change / ES | Conditional | Regress HY spread changes divided by average historical tail widening on equivalently scaled IG changes. | Is HY experiencing more tail-scaled spread stress than the historical relationship with IG predicts? Scaling does not make the fit a tail-dependence model. | How unusual is the residual between tail-scaled spread moves? |
| Percentage change / None | Core | Regress USD HY total returns on a USD bond benchmark. HY returns 1.2%; fitted return is 0.9%: +0.3 percentage points. | Did HY outperform what its historical benchmark relationship predicts for this interval? A one-period residual, not proof of persistent alpha. | How unusual is that unexplained return? |
| Percentage change / Volatility | Conditional | Regress bank-sector total returns divided by their rolling SD on broad-equity returns divided by their rolling SD. | Did banks outperform their historical relationship with the market after allowing for changing volatilities? | How unusual is the unexplained volatility-scaled sector return? |
| Percentage change / Beta | Conditional | Scale bank and insurance sector returns by rolling betas to the same equity index, then regress one scaled series on the other. | Is either sector diverging even after translating both into broad-market-equivalent returns? Useful only if rolling sensitivity treatment serves a stated purpose. | How unusual is the residual between their benchmark-equivalent returns? |
| Percentage change / VaR | Conditional | Regress HY total returns divided by their prior loss quantile on similarly scaled IG total returns. | Did HY fare worse than predicted given IG's return expressed in its own loss-threshold units? This is not a portfolio VaR estimate. | How unusual is the residual relationship between loss-threshold-scaled returns? |
| Percentage change / ES | Conditional | Regress HY total returns divided by average historical tail loss on equivalently scaled IG total returns. | Did HY underperform the relationship with IG after allowing for changing average-tail-loss scales? | How unusual is the unexplained tail-scaled HY return? |

## Conditions that make those examples economically defensible

| Area | Necessary interpretation or restriction |
| --- | --- |
| Absolute versus percentage spread changes | Both can matter. A spread rising from 100 to 120 bp changes by 20 bp and 20%; a rise from 400 to 420 bp is also 20 bp but only 5%. The former measures absolute repricing; the latter measures proportional repricing. Duration-times-spread research links proportional spread moves to spread-driven returns through duration: approximately `−D × Δs = −(D × s) × (Δs/s)`, in consistent units. Neither spread-change measure alone is total bond return. [Original DTS paper](https://www.robeco.com/files/docm/docu-201708-duration-times-spread.pdf) |
| Data Series semantics | Percentage change in a total-return index measures index return; percentage change in a price index excludes distributed income; percentage change in OAS measures spread growth. Raw point changes of separately based indices do not measure comparable performance. [S&P index methodology](https://www.spglobal.com/spdji/en/research-insights/index-literacy/methodology-matters/) |
| Comparison Basis | Matching “bp” is insufficient. Differences in currency, reference curve, maturity, rating mix and optionality must either be aligned or explicitly be the object of investigation. A cross-currency spread comparison can be informative without claiming it is a hedged trading opportunity. |
| Volatility | Current move divided by prior SD, with no drift subtraction. A current return/SD is not the historical Sharpe ratio, which uses mean differential return. [Sharpe's definition](https://web.stanford.edu/~wfsharpe/art/sr/sr.htm) |
| Beta | Estimated from aligned measured changes/returns. Needs an economically relevant reference and stable, materially nonzero sensitivity. Beta division expresses reference-equivalent movement; it does not subtract a benchmark move or regression intercept. Negative beta can be meaningful for an inverse exposure but reverses sign interpretation. Self-beta is one when estimable. [OLS beta example](https://www.msci.com/downloads/web/msci-com/research-and-insights/paper/the-msci-private-real-estate-factor-model/The-MSCI-Private-Real-Estate-Factor-Model.pdf) |
| VaR versus ES | VaR scale is a chosen adverse-move quantile; ES scale is the average tail beyond that quantile, with the app's stated finite-sample convention. Spread widening is usually the adverse direction for long credit exposure; negative total returns use the opposite direction. These scales describe the input, not portfolio P&L. [BIS definitions](https://www.bis.org/committees/bcbs/basel-framework/standard/mar?allChapters=true&q=PPP0QQQ&sort=PPP1QQQ&year=PPP2QQQ) |
| Tail comparison | Use a stated downside direction, confidence and interval. A difference of two separately scaled legs is not the VaR/ES of their difference: joint behaviour and positions are missing. Historical ES at 95% with 60 observations averages only about three tail observations; positive output alone is not adequate statistical evidence. |
| Ratios of moves | Require a meaningful nonzero denominator, direction interpretation and aligned interval. Same-sign negatives yield a positive ratio; a tightening/tightening ratio does not mean widening. Deposit pass-through is an established example of a ratio of changes. [New York Fed](https://libertystreeteconomics.newyorkfed.org/2022/11/how-do-deposit-rates-respond-to-monetary-policy/) |
| Regression | A residual is observed minus fitted prediction. It describes an association, not necessarily causation, mispricing or persistent alpha. Unlike units can be legitimate because the slope carries the unit conversion. [NIST residual definition](https://www.itl.nist.gov/div898/handbook/pri/section6/pri619.htm) |
| Regression after scaling | Rolling scales produce a different relationship, so there can be a specialist question. Fixed positive scales merely re-express an OLS fit: its residual changes by the dependent variable's scale and its Z-score is unchanged. VaR/ES-scaled OLS is not quantile regression or a tail-dependence model. |
| Windows | Match measurement intervals across legs and risk estimation. The app samples overlapping weekly/monthly moves at daily endpoints; observation count is not a count of independent intervals. Fit history, risk-estimation history and Z-score history have different jobs. |

## The 32 level plus adjustment settings

The following 16 base settings each cover both **Original units and Z-score**,
hence 32 complete v2 configurations. They retain Level as numerator and explicitly
estimate change-based risk. They are conditional economic diagnostics, not a
claim of carry/volatility: carry period, duration and other return components
remain unspecified. Existing v1 records preserve their earlier restrictions.

### Conditional adjusted-level meanings

Under **input-pipeline-v2**, choose the following conditional definition: preserve the spread level as numerator; estimate each denominator from prior same-frequency **absolute spread changes**. Beta refers to a common credit-spread reference. Volatility/VaR/ES refer to each sector's own spread-change distribution. This is executable with Estimate risk from Absolute changes; Follow also resolves Level to that basis.

These are **conditional compensation-versus-movement-risk proxies**, not annualized risk-adjusted returns, fair values or established named metrics. VaR/ES use spread widening as the adverse direction. Comparing sectors requires matched horizon and conventions; duration and other return components are needed before making a carry/P&L claim.

| Level calculation | Adjustment | Real-market example and unstandardized economic question | Z-score question for that same example |
| --- | --- | --- | --- |
| Standalone | Volatility | HY OAS 450 bp / weekly spread-change SD 30 bp = 15. How much quoted spread is available per unit of weekly spread variability? | Is that compensation-versus-variability proxy high versus its own history? |
| Standalone | Beta | HY OAS 450 bp / beta 2 to broad-credit spread changes = 225 reference bp. How much spread is quoted per unit of broad-credit change sensitivity? | Is compensation per unit of estimated sensitivity historically high? |
| Standalone | VaR | HY OAS 450 bp / 95% weekly widening quantile 60 bp = 7.5. How large is quoted spread relative to the historical adverse-move threshold? | Is the spread-to-widening-threshold proxy historically high? |
| Standalone | ES | HY OAS 450 bp / average worst-5% weekly widening 90 bp = 5. How large is quoted spread relative to typical tail widening? | Is the spread-to-tail-widening proxy historically high? |
| Difference | Volatility | Compare HY OAS/own spread-change SD with IG OAS/own SD. Which sector offers more spread per unit of its own spread variability, and by how much? | Is the gap between those compensation proxies unusual? |
| Difference | Beta | Compare HY OAS/beta(HY,credit reference) with IG OAS/beta(IG,same reference). Which offers more spread per unit of common-reference sensitivity? | Is the sensitivity-scaled compensation gap unusual? |
| Difference | VaR | Subtract IG spread/IG widening quantile from HY spread/HY widening quantile. Which has more quoted spread relative to its adverse-move threshold? | Is the gap in spread-to-threshold proxies unusual? |
| Difference | ES | Subtract IG spread/IG tail widening from HY spread/HY tail widening. Which has more spread per unit of typical tail widening? | Is the gap in spread-to-tail proxies unusual? |
| Ratio | Volatility | Divide HY's spread/SD proxy by IG's. How many times IG's compensation-versus-variability proxy does HY offer? | Is that relative compensation multiple unusual? |
| Ratio | Beta | Divide HY's spread/beta proxy by IG's, using the same credit reference. What is the multiple of compensation per reference sensitivity? | Is that sensitivity-scaled compensation multiple unusual? |
| Ratio | VaR | Divide HY's spread/widening-quantile proxy by IG's. What is the relative multiple of quoted spread per adverse-threshold unit? | Is that relative threshold-scaled compensation multiple unusual? |
| Ratio | ES | Divide HY's spread/tail-widening proxy by IG's. What is the relative multiple of compensation per tail-widening unit? | Is that relative tail-scaled compensation multiple unusual? |
| Regression residual | Volatility | Regress HY spread/own SD on IG spread/own SD. Is HY's compensation-versus-variability proxy above its fitted relationship with IG's? | Is that proxy residual historically unusual? |
| Regression residual | Beta | Regress sensitivity-scaled bank-sector credit spread on sensitivity-scaled industrial spread, using a common credit reference. Does bank compensation depart from their historical proxy relationship? | Is the departure between sensitivity-scaled compensation proxies unusual? |
| Regression residual | VaR | Regress HY spread/own widening quantile on the corresponding IG proxy. Is HY compensation high relative to the relationship between these threshold-scaled proxies? | Is that threshold-scaled proxy residual unusual? |
| Regression residual | ES | Regress HY spread/own tail widening on the corresponding IG proxy. Is HY compensation high relative to the historical relation between these tail-scaled proxies? | Is that tail-scaled proxy residual unusual? |

All 16 examples require a separately defined input-risk estimator before either standardization choice is meaningful. Stable positive spread levels, usable estimates and meaningful denominators remain necessary. The regression variants in particular add complexity without an obvious default workflow; include them only for a demonstrated question. These are conditional interpretations; they do not establish economic adequacy or calibrated monitoring.


## Combinations and interpretations that do not make sense

These rules override every cell in the overview.

| Invalid or misleading instance | Concrete example | Why it fails or what would be needed |
| --- | --- | --- |
| Subtract incompatible economic quantities | HY spread in bp minus an equity index level in points | No interpretable common quantity. Explicit conversion or a justified regression/ratio is a different analysis. |
| Compare arbitrary index bases as value or performance | HY index 240 minus IG index 180; or ratio 240/180 called “HY is 33% richer” | Index bases/divisors are arbitrary. A common-start wealth comparison or interval returns provides a defined interpretation. |
| Treat spread percentage changes as bond returns | OAS rises 100 → 120 bp and is reported as +20% investment performance | It is spread growth. Spread-driven price effect needs duration and has the opposite sign for a long fixed-rate credit position, other things equal. |
| Percentage change in a zero/negative baseline with ordinary growth interpretation | Yield moves −10 bp → +10 bp | Standard positive-base growth interpretation breaks. The app rejects nonpositive baselines; use absolute changes where appropriate. |
| Divide by zero, or present a tiny denominator as a strong signal | HY widens 10 bp and IG changes 0.001 bp: ratio 10,000 | Huge output reflects a tiny denominator. A materiality rule and purpose-specific treatment are necessary; a Z-score does not repair it. |
| Treat a move ratio as stable beta or causality | Banks return 6%, market 3%, therefore banks “have beta 2” | One interval's ratio is not an estimated relationship and does not identify a causal effect. |
| Treat beta division as hedging/residualization | A returns 3%, beta is 1.5; call 3/1.5 = 2% “market-neutral alpha” | Actual market move and intercept were never subtracted. |
| Use near-zero beta as a meaningful divisor | Sector return 1% divided by beta 0.001 | Implausibly large benchmark-equivalent result. Numerical nonzero is insufficient; economic sensitivity must be usable. |
| Claim standardized input difference is standardized pair movement | `ΔA/σA − ΔB/σB` called the Z-score of `ΔA−ΔB` | Different formulas; pair dispersion depends on covariance and centering. Final-result Z-score is a separate step. |
| Call separately normalized differences portfolio tail risk | `rA/ES_A − rB/ES_B` called the ES of a long-short portfolio | Joint distribution, weights and positions are absent. |
| Subtract unlike risk scores without a common interpretation | A scaled by 95% VaR minus B scaled by 99% ES, both labelled “risk units” | Same dimension does not establish comparable risk budgets. An explicit allocation/budget definition would create a different justified comparison. |
| Call OLS on tail-scaled inputs a tail model | Regression after dividing by ES described as “conditional crash loss” | It is still mean least-squares fitting on scaled inputs. |
| Infer fair value from trending levels solely because R² is high | Regress unrelated growing wealth indices and trade the residual | Common trends can generate spurious fit. A stable relationship requires economic and time-series justification. |
| Treat Z-score as guaranteed probability or reversal | “Z = 2 means exactly a 2.5% upper-tail event and it must mean-revert” | Distributional and dynamic assumptions are missing. |
| Standardize a constant or inadequately sampled statistic | An exactly constant ratio; zero residual dispersion | No usable SD/reference distribution; unavailable, not a zero-risk opportunity. |
| Treat retrospective scores as historically investable signals | Today's fitted residual/Z-score history presented as a point-in-time backtest | Historical values were computed using today's fit/reference, not the estimates then available. |

## Redundant settings rather than invalid economics

These are algebraic deductions from the pipeline:

- **Common ratio divisor cancels exactly:** `(A/s)/(B/s) = A/B`, even if s changes over time. Same reference plus identical volatility/VaR/ES settings gives the same divisor when information cutoffs and eligible samples also match. Beta to the same reference generally gives different divisors, so does not generally cancel.
- **Self-beta is 1** when the series varies. A benchmark leg using self-beta can be useful when the other leg is adjusted to that benchmark; applying self-beta to every leg adds no analytical change.
- **Fixed positive scaling before Standalone Z-score cancels.** Current rolling scales generally do not cancel because each historical observation has a different divisor.
- **Fixed scaling before refitted regression adds no new standardized residual information.** This requires constant positive scales and identical samples. Rolling scales or changed sample eligibility break the equivalence.
- **Unadjusted difference of changes equals change in the level difference** with identical start/end dates: `ΔA−ΔB = Δ(A−B)`. The analogous ratio identity is false.

## Per-input overrides and references

The 120 count uses one selected method for both legs. The app also allows independent methods, references and calibration. Those extra configurations should follow these rules.

For **differences of ordinary bp or percentage-change inputs**:

| A method / B method | None | Volatility | Beta | VaR | ES |
| --- | --- | --- | --- | --- | --- |
| None | Comparable native units | Incompatible scales | Conditional common units/reference | Incompatible scales | Incompatible scales |
| Volatility | Incompatible scales | Comparable risk convention | Incompatible scales | Explicit common budget needed | Explicit common budget needed |
| Beta | Conditional common units/reference | Incompatible scales | Common or justified comparable reference | Incompatible scales | Incompatible scales |
| VaR | Incompatible scales | Explicit common budget needed | Incompatible scales | Comparable tail convention | Explicit common budget needed |
| ES | Incompatible scales | Explicit common budget needed | Incompatible scales | Explicit common budget needed | Comparable tail convention |

For example, `ΔHY / beta(HY,IG) − ΔIG` is coherent: both terms are in IG-equivalent bp. By contrast, subtracting a bp change from a dimensionless volatility-scaled change is not a common-unit comparison.

“Explicit common budget needed” means **do not offer as a generic relative-strength comparison**. A user might deliberately compare two exposures as fractions of separately mandated risk budgets; that rationale and those budgets would need to be part of the definition.

For **ratios**, unlike units can be meaningful when the quotient answers a named question, but arbitrary mixtures are not justified merely because division succeeds. For **regression**, unlike units can also be meaningful; the dependent variable determines residual units. Neither calculation removes the need for a plausible relationship.

For volatility/VaR/ES, using an external reference changes the question from “relative to this input's own risk” to “relative to the chosen reference's risk.” A shared credit reference can express both moves in broad-credit-risk units. Units must match under the app's current validation. Reference changes are substantive analytical changes.

## Guidance without restricting combinations

The Core, Conditional and Event labels express recommended use, not permission.
Allow the user's chosen combination when its formula is defined and supported;
explain unusual choices and verify the preview. A conditional analysis does not
become prohibited merely because a simpler one is usually preferable.

Keep economic recommendations separate from mathematical constraints and current
version limitations. Undefined division, incompatible subtraction and unusable
estimates still require explicit unavailable/error states. Potential level-over-risk
analyses need a defined estimation measure independent of the level numerator.

Show the actual formula, reference and resulting units. Keep monitoring thresholds
separate from the mathematical definition. Preserve the user's selected measure
when an adjustment is chosen; report unsupported capabilities rather than silently
answering a different question. Existing Snapshots retain their captured definitions.

## Coverage and current implementation

At the setting-enum level, assuming compatible inputs and available estimation data:

- 44 defined calculation/measure/adjustment rows × 2 standardizations = **88 mapped settings**.
- 16 level/adjustment rows × 2 standardizations = **32 conditional level-scaling settings**.
- Total = **120**.
- **V2 permits all 120** enum combinations. V1 retains the prior 76-combination contract. Data sufficiency, undefined mathematics and incompatible subtraction remain constraints.
The [application contract](application-contract.md) records the inspected engine behaviour. Check the installed schema and preview because capabilities can change independently of these economic interpretations.

Additional primary-source rationale: [research source note](sources.md).
