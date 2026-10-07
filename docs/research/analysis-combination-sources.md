# Evidence for Analysis combination design

Research provenance retained in the repository; the packaged skill is self-contained.

Research date: 5 October 2026. Examples below are illustrative analytical questions, not current observations. Sources justify component meanings; proposed combination classifications are analytical judgments, not claims endorsed by those sources.

## Source-backed distinctions

| Topic | Supported statement | Consequence for Kairopsis |
| --- | --- | --- |
| Credit spread units | ICE BofA US High Yield OAS is supplied in percent and measures constituent option-adjusted spreads against a spot Treasury curve. [ICE series metadata via FRED](https://fred.stlouisfed.org/series/BAMLH0A0HYM2) | A move from a hypothetical 3% to 3.3% is +30 bp but +10% of the starting spread. Both answer legitimate, different questions; neither is the bond investment return. HY minus IG OAS requires matching spread conventions and unit conversion. |
| Index levels versus returns | Index divisors establish a scale and preserve continuity. Price indices reflect price movements; total return indices include reinvested income. [S&P DJI methodology guide](https://www.spglobal.com/spdji/en/research-insights/index-literacy/methodology-matters/) | Percentage change in a supplied total return index measures its interval return. Subtracting raw point changes of separately based indices is not an economically comparable performance measure. A normalized wealth comparison requires a specified common investment date/base. |
| Volatility scaling versus Sharpe | Sharpe's historical ratio divides the average differential return by its historical standard deviation. [Sharpe, 1994](https://web.stanford.edu/~wfsharpe/art/sr/sr.htm) | One current return divided by prior volatility is a volatility-scaled move, not a Sharpe ratio. Likewise a current spread change divided by spread-change volatility describes move size, not investment performance. |
| OLS beta and noisy estimates | MSCI describes standard market beta as the OLS slope of asset returns against market returns; short histories can produce noisy, implausible estimates. [MSCI factor-model paper](https://www.msci.com/downloads/web/msci-com/research-and-insights/paper/the-msci-private-real-estate-factor-model/The-MSCI-Private-Real-Estate-Factor-Model.pdf) | Dividing a move by beta expresses a benchmark-equivalent move. It does not remove the benchmark component. Small, unstable or sign-changing beta needs restrictions beyond a purely numerical zero check. |
| Regression residual | A residual is observation minus fitted prediction; residual diagnostics assess the fitted model. [NIST model validation](https://www.itl.nist.gov/div898/handbook/pri/section6/pri619.htm) | For measured inputs, the pair result is `A - (intercept + slope × B)`. This differs from `A / beta`; the first asks what A did beyond its fitted relationship to B. Regression can relate unlike input units: slope carries the conversion, residual retains A's units. |
| VaR and ES | BIS defines VaR using a horizon/confidence level and ES as average losses beyond VaR. [BIS market-risk framework](https://www.bis.org/committees/bcbs/basel-framework/standard/mar?allChapters=true&q=PPP0QQQ&sort=PPP1QQQ&year=PPP2QQQ) | With Kairopsis's signed series-change definition, the denominator describes tail spread moves or supplied returns, not a portfolio loss estimate. Scaling spread changes by this denominator can answer a stress-size question, provided downside direction, frequency and confidence are specified. |
| Level regressions | Nonstationary series can produce spurious regression relationships; cointegration addresses meaningful stable relationships between such series. [Royal Swedish Academy, 2003 scientific background](https://www.nobelprize.org/uploads/2018/06/advanced-economicsciences2003-1.pdf) | Level regressions are conditional, not categorically invalid. An apparent high fit between trending price indices does not establish relative value or mean reversion. A historical Z-score does not repair this problem. |
| Ratios of changes | The New York Fed explicitly measures deposit-rate pass-through as cumulative change in deposit rates divided by cumulative change in fed funds rates. [New York Fed, 2022](https://libertystreeteconomics.newyorkfed.org/2022/11/how-do-deposit-rates-respond-to-monetary-policy/) | `ΔA / ΔB` has a clear real-world use. A defined event/window and meaningful nonzero denominator are essential. This deposit beta is a change ratio, distinct from Kairopsis's estimated OLS beta adjustment. |
| Relative spread moves and duration | The original DTS paper models spread-driven return approximately as `−D × Δs = −(D × s) × (Δs/s)`; its empirical work motivates relative spread changes. [Ben Dor et al., 2007, author-hosted paper](https://www.robeco.com/files/docm/docu-201708-duration-times-spread.pdf) | Percentage spread change has a substantive credit-risk interpretation. Converting it into spread-driven price return additionally needs spread duration; it still omits other return components. Level divided by move-risk could form a separately defined compensation/risk proxy, but is not automatically a carry-to-risk measure. |

## Deductions and scope

The classifications are analytical judgments built from the source-backed
distinctions above. Their maintained derivations and examples live in the map:

- [Formula order](../../src/kairopsis/skills/kairopsis-analysis/references/combination-map.md#read-the-calculation-in-the-correct-order):
  relationships between moves versus moves in a relationship.
- [Economic conditions](../../src/kairopsis/skills/kairopsis-analysis/references/combination-map.md#conditions-that-make-those-examples-economically-defensible)
  and [invalid interpretations](../../src/kairopsis/skills/kairopsis-analysis/references/combination-map.md#combinations-and-interpretations-that-do-not-make-sense):
  returns, sensitivity, tail risk and statistical claims.
- [Cancellation and redundancy](../../src/kairopsis/skills/kairopsis-analysis/references/combination-map.md#redundant-settings-rather-than-invalid-economics):
  common divisors, self-beta and fixed versus rolling scales.
- [Adjusted levels](../../src/kairopsis/skills/kairopsis-analysis/references/combination-map.md#the-32-level-plus-adjustment-settings)
  and [per-input conventions](../../src/kairopsis/skills/kairopsis-analysis/references/combination-map.md#per-input-overrides-and-references):
  conditional questions beyond ordinary matched-move comparisons.

Use the [application contract](../../src/kairopsis/skills/kairopsis-analysis/references/application-contract.md#version-and-combination-rules)
for version availability. Implementation support and the economic adequacy of a
particular definition remain separate judgments.
