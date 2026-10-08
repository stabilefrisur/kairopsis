# Relative-value exploration workspace

Research and recommendations, 8 October 2026. Current-capability audit: Kairopsis `c384dd1`. Requirements discussion only; no implementation decisions. All worked examples are hypothetical.

## Conclusion

Build a flexible investigation space around **selected exposures, their fields, dates and derived relationships**. Its purpose is to develop and challenge Relative Value Views, including Cross-Market Inconsistencies without an identified trade expression. Keep rarity monitoring a separate, optional destination.

**Multiple fields per symbol can supply both cross-sectional and panel data.** The earlier claim that adding series would not suffice was too broad. A collection containing spread and duration histories for several symbols already contains the required observations. The missing requirement is reliable association and reshaping: which exposure, field and date each observation represents.

Recommended scope:

- Six chart families: multi-series history, scatter, ranked comparisons, distributions, heatmaps and correlation matrices. KDE is the preferred distribution view; include histogram and box alternatives.
- Shared capabilities: independent field transformations, peer selection, date/regime comparison, grouping, simple relationship construction and linked selection.
- Save refreshable investigations and frozen evidence into Ideas. Starting exploration requires neither an Economic Rationale nor a monitored Analysis.
- Curves deferred. Full econometric modelling, trading simulation and portfolio optimisation remain outside this proposal.

The catalogue below defines the intended research coverage. It is a bounded starting scope, not an exhaustive list of possible combinations or a whitelist of permitted questions.

## Project fit and current position

Kairopsis exists to support relative-value investigation and investment views for team discussion. Its domain already includes Ideas, Research Assets, Snapshots and Comparison Basis. An Analysis currently investigates one or two Data Series. A broader workspace therefore fits the project, but should not force every view into that existing definition. [Domain](../../CONTEXT.md)

The current foundations are useful:

- A `SeriesBinding` already identifies source, instrument, field and provider parameters. Separate fields for one instrument can have separate catalogue names. Data requests already accept multiple bindings; the one/two-input restriction belongs to Analyses and associated display/evidence structures. [Models](../../src/kairopsis/models.py), [catalogue mapping](../../src/kairopsis/metapyle_catalogue.py)
- Current ingestion handles dated numeric observations, not arbitrary text attributes or undated reference-data tables. Its adapter also rejects multiple observations for one calendar day. Multi-field numeric history is consequently closer to current capability than historical rating classifications or intraday panels. [Adapter](../../src/kairopsis/metapyle_adapter.py)
- Data access must remain through Metapyle. Portable Idea evidence must retain observations and analytical choices. These recommendations follow ADRs 0003/0004; this research does not revise them. [Data boundary](../adr/0003-metapyle-data-access.md), [evidence retention](../adr/0004-portable-idea-evidence.md)

Gaps include explicit associations between exposures and semantic fields, grouping attributes, general multi-input views, cross-sectional sampling, and evidence containing several related views. Current regression scatter filters points using existing evaluation eligibility; exploration needs its own visible sample-validity rules, separate from monitoring qualification. [Charts](../../src/kairopsis/static/charts.js)

Existing Analysis/Snapshot reuse needs later design work; current persistence should not be presented as already supporting this workspace.

## One collection, several observation shapes

Treat **exposure × field × date** as a logical view over the series collection, not a prescribed replacement database. Retain binding identity, units, Comparison Basis and provenance alongside it. Preserve supplied row dates separately from verified observation dates; unknown provenance stays unknown. Long and wide tables are alternative representations; standard reshaping supports moving between them. [pandas reshaping](https://pandas.pydata.org/docs/user_guide/reshaping.html)

| Shape | One observation means | Example |
| --- | --- | --- |
| History | A date/interval for one exposure or derived relationship | Weekly HY spread change |
| Cross-section | An exposure at a selected date or over one selected interval | Spread, duration and monthly spread change for each credit index |
| Panel | An exposure-date or exposure-interval combination | Monthly spread and duration for every selected index |
| Derived summary | A group, period, event or fitted statistic | Sector median spread, interquartile dispersion, rolling correlation |

A correlation matrix can compare series across dates **or** fields across exposures at one date. Neither requires panel regression. Following the same exposures across dated cross-sections produces a panel; membership can be unbalanced. Pooling its rows is an additional analytical choice.

Provider symbols are not universal exposure identities: one provider may reuse a symbol across fields while another supplies a separate symbol for every measure. Permit explicit associations and sensible suggestions where unambiguous. Bindings with different provider parameters remain distinct even when symbol and field match. Distinguish numeric fields, such as duration, from categorical attributes, such as sector. Both can change over time; historical grouping must state whether it uses historical or current classifications.

## Use-case catalogue

**Core** means the intended workspace should cover the question; it is not a promise that every convenience ships first. **Extension** means relevant, but unnecessary for initial coverage. Each row names the observation unit so chart choices do not conceal a change of question.

### Establish the comparison

| ID / scope | Research question and required capability | Shape; example | Views |
| --- | --- | --- | --- |
| RV01 Core | How do several exposures evolve and diverge? Compare levels, absolute changes, returns where meaningful, or common-start rebased paths. | History; IG, HY, EM and MBS spread moves since a chosen date. | Overlaid lines; small multiples |
| RV02 Core | What do several fields reveal about one exposure? Transform each measure independently and retain its units. | History; an index's spread, duration, volatility and total-return history. | Aligned small multiples; scatter |
| RV03 Core | Which expression of a relationship best addresses the question? Compare differences, ratios, existing Analysis outputs and simple named benchmark-relative measures. | History or exposure-date; a sector's spread less its peer median, beside the raw spread. | Lines; scatter; distributions |
| RV04 Core | Does interpretation depend on currency/reference basis or risk scaling? Compare supplied alternatives with formulas visible. | History/cross-section; native US/European credit spreads beside explicitly swap-rebased comparisons; raw versus volatility-scaled widening. | Small multiples; ranked dots |
| RV05 Core | Which peers offer more quoted compensation at a date? Rank one measure, retain a chosen comparator, inspect underlying observations. | Cross-section; spreads for selected same-currency credit indices. | Ranked dots/bars |
| RV06 Core | Which peers repriced most, and did their order change? Select interval endpoints; compare levels, changes and paired dates. | Cross-section; sector bp widening this month; connect each sector's start/end spread. | Ranked dots/bars; paired markers; scatter arrows |

### Explain the apparent discrepancy

| ID / scope | Research question and required capability | Shape; example | Views |
| --- | --- | --- | --- |
| RV07 Core | Is an exposure unusual relative to peers with different characteristics? Assign fields independently to axes and optional colour, size or facets. | Cross-section; spread versus duration, colour by rating, optionally size by index market value. | Scatter; labelled peer table |
| RV08 Core | Does the discrepancy survive a more comparable peer set? Filter/stratify by sector, rating, currency or duration band; retain a broader reference. | Cross-section/panel; compare an index with similarly rated, similar-duration peers. | Faceted scatter; ranked dots; box plots |
| RV09 Core | How do two measures move together historically? Inspect shape, outliers and optional descriptive fit; highlight selected/latest dates. | Paired dates; weekly IG bp changes versus equity-index returns, with independent axis transforms. | Scatter; linked histories |
| RV10 Core | Does the relationship differ by regime or a third variable? Compare explicitly selected periods, groups or field-defined conditions. | Dates, exposures or exposure-dates; MBS/IG moves in high- versus low-rate-volatility periods. | Faceted scatter; KDE; small multiples |
| RV11 Core | How far is an observation from a stated fitted relationship? Select fit sample, show equation and residual units, inspect influential points. | Dates or exposures; rank peer spreads above/below a spread-duration fit; compare a recent date with a prior-period fit. | Scatter with fit; residual dots/history |
| RV12 Extension | Does a discrepancy persist after several characteristics are considered together? | Dates or exposures; spread residual after duration and credit-quality controls. | Observed/fitted scatter; residual views |

RV08/RV10 cover conditional comparisons without requiring a full modelling package. NIST's conditioning plots examine how a two-variable relationship changes with a third variable; its scatter guidance also covers nonlinear patterns and outliers. Multi-factor adjustment in RV12 needs separate statistical requirements. [NIST conditioning](https://www.itl.nist.gov/div898/handbook/eda/section3/eda33qc.htm), [NIST scatter](https://www.itl.nist.gov/div898/handbook/eda/section3/scatterp.htm)

### Understand distributions, breadth and stability

| ID / scope | Research question and required capability | Shape; example | Views |
| --- | --- | --- | --- |
| RV13 Core | Where does a selected value sit within its history, and what does the distribution look like? Mark the value and retain original magnitudes. | Dates; MBS-minus-IG spread gap over a selected history. | KDE; histogram; box plot |
| RV14 Core | How does dispersion differ across peer groups or dates? Distinguish between-peer variation from variation through time. | Exposures at a date; spread distributions by rating; repeat before/after a market move. | KDE/box plots; ranked dots |
| RV15 Core | Is repricing broad or concentrated, and is peer dispersion changing? Drill from group aggregates to members; retain counts and aggregation. | Exposure-period/group-date; sector × week bp moves; sector × rating median spreads; dispersion history. | Heatmaps; lines; member scatter |
| RV16 Core | Which measures co-move, and which evidence may be redundant? Support both matrix orientations; drill a cell into its actual paired observations. | Dates across series, or exposures across fields; sector weekly-move correlations; spread/duration/volatility relationships across peers. | Correlation matrix; pair scatter |
| RV17 Core | Is co-movement or sensitivity stable? Compare selected windows/regimes and inspect rolling correlations or slopes. | Dated estimates from defined samples; recent versus longer-run MBS/IG association. | Side-by-side matrices; rolling lines; scatter |
| RV18 Core | Does the conclusion survive reasonable sample/definition changes? Duplicate a view with changed window, frequency, peer membership, weighting or transformation. | Any shape; compare fixed peers with each-date membership and daily with weekly moves. | Matched views; difference heatmap |
| RV19 Core | What happened during chosen episodes? Compare distributions and trajectories; retain event definitions and measurement endpoints. | Dates or event-relative dates; sector spread moves during two selected stress episodes. | Event-aligned lines; ranked dots; KDE/box plots |
| RV20 Extension | Are moves delayed, persistent or followed by different outcomes? Explicitly align lags and forward outcomes; label retrospective evidence. | Date/lag or event/forward interval; starting spread gap versus subsequent gap change. | Lagged scatter; lag-correlation/ACF lines |

Historical percentile, cross-sectional rank and fitted residual answer different questions. Keep each available, distinctly named; none alone establishes investment attractiveness. This follows the existing [Analysis design guidance](../../src/kairopsis/skills/kairopsis-analysis/references/analysis-design.md).

### Construct, preserve and revisit evidence

| ID / scope | Research question and required capability | Shape; example | Views |
| --- | --- | --- | --- |
| RV21 Core | Does a simple composite comparator improve the comparison? Define equal/explicitly weighted peer summaries or fixed linear combinations, with membership and missingness rules. | Group-date; a chosen credit sector versus a fixed-weight comparator of related sectors. | Lines; ranked dots; residual distribution |
| RV22 Core | What evidence supports or challenges the view, and what changed on revisit? Save selections, alternatives, notes and frozen data; reopen a refreshable investigation; copy/export selected views or the investigation with data and provenance. | Several related views; retain a cross-section, its historical context and a challenging peer comparison within one Idea. | Linked workspace; dated Snapshots |

These composites are research comparators. They do not acquire the meaning of investable portfolio returns without appropriate return, weighting and rebalancing conventions. RV22 extends existing portable evidence principles; it must preserve supporting and challenging findings, including views that never become monitored Analyses. [Evidence ADR](../adr/0004-portable-idea-evidence.md)

## Findings that affect the requirements

### Distributions need explicit sample meaning

KDE estimates a smooth density; bandwidth strongly affects the result and can obscure multiple modes. Provide visible, adjustable smoothing, sample counts and optional observed points. Default each compared distribution to unit area; expose weighting separately. Tiny or constant samples should remain inspectable as observations rather than acquiring an invented smooth shape. [SciPy KDE](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gaussian_kde.html)

Histograms expose observed frequencies and bin sensitivity. Box plots compactly compare medians, quartiles and spread across many groups. Retain both as alternate views of the same selected observations. Specify bin and whisker conventions. [NIST histogram](https://www.itl.nist.gov/div898/handbook/eda/section3/histogra.htm), [NIST box plot](https://www.itl.nist.gov/div898/handbook/eda/section3/boxplot.htm)

An ECDF is a useful later alternative for exact empirical tail/percentile questions; it is a stepwise cumulative distribution rather than a smoothed density. No need to make it an initial seventh chart family. [SciPy ECDF](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ecdf.html)

### Correlation and fitting need visible samples

Pearson measures linear association; it can miss nonlinear dependence. Constant inputs have undefined correlation. Offer Pearson and Spearman, keep scatter drilldowns, and show unavailable cells honestly. Avoid automatic significance claims: default correlation tests make distributional assumptions, while repeated dates and exposures require additional consideration. [SciPy Pearson](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html)

**Recommendation:** suggest changes or appropriate returns for temporal co-movement; permit deliberate level comparisons and cross-sectional field levels. Preserve field meaning: percentage spread change measures proportional repricing, not investment return. [Analysis shaping guidance](../../src/kairopsis/skills/kairopsis-analysis/references/analysis-design.md)

Default a matrix to one common aligned sample. Optional pairwise samples should expose each cell's count and dates: pandas uses pairwise-complete observations, and R documents that this can produce a matrix that is not positive semidefinite. The proposed default is a comparability choice, not a claim that complete-case sampling eliminates bias. [pandas correlation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.corr.html), [R correlation](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/cor.html)

Keep fit periods, evaluation periods and display periods distinct. A full-sample descriptive fit and a fit frozen before a selected episode answer different questions. Rolling estimates also need an explicit window and missingness rule; missing observations can reduce observations inside a nominal window. [statsmodels rolling regression](https://www.statsmodels.org/stable/examples/notebooks/generated/rolling_ls.html)

### Panel data should preserve the distinctions researchers need

With equal weight per row, pooling every exposure-date gives longer histories more influence. Between-exposure differences can also differ from changes within one exposure. **Recommendation:** default to date slices, individual histories or explicit facets; allow deliberate pooling with counts, weighting and grouping visible. Do not imply independent observations or automatically fit a pooled regression.

Likewise, changing membership or classification can move group summaries without any continuing member repricing. Support matched-member comparisons and explicit each-date membership. When historical membership is unavailable, label a current-universe history accordingly.

These controls have a direct investment-research purpose. For example, the Bank of England adjusts investment-grade spread comparisons for changing credit quality and duration. That supports examining composition and risk characteristics alongside pricing; it does not prescribe one universal adjustment. [December 2025 FSR, Chart 2.2](https://www.bankofengland.co.uk/-/media/boe/files/financial-stability-report/2025/financial-stability-report-december-2025.pdf)

### Linked views should retain research context

Selection in one view should identify the same exposures/dates elsewhere: a heatmap anomaly opens its history; a correlation cell opens the paired sample; selected scatter points identify their dates or peers. Linked selection is an established visualisation pattern. [Bokeh linked behaviour](https://docs.bokeh.org/en/latest/docs/user_guide/interaction/linking.html)

**Recommendation:** distinguish highlighting from filtering, and allow a reference sample to remain fixed. Otherwise selecting an apparent outlier could silently replace the benchmark used to judge it. Comparable panels should share scales where units permit; mixed-unit heatmaps require explicit standardisation or separate scales.

## Proposed defaults and decisions to retain for design

| Decision | Suggested default; flexibility to preserve |
| --- | --- |
| Starting a workspace | Begin with any selected collection; optional question/notes. Offer domain examples without mandatory thesis entry. |
| Field and exposure identity | Reuse bindings; add explicit associations and semantic field names where needed. Do not infer identity solely from display labels. |
| Transformations | Independent per measure: raw levels initially; explicit changes, percentage changes, rebasing, scaling and derived measures. Preserve order and formulas. |
| As-of cross-sections | Exact-date observations first; permit explicit backward as-of selection with bounded age and per-field actual dates. No silent forward filling. |
| Intervals and frequency | Match endpoints/cadence for compared moves. Distinguish observation date, measurement interval, sampling frequency and display range. |
| Economic comparability | Keep units, currency, reference curve and option/risk conventions visible where relevant. Metadata labels never perform conversions. Unknown basis remains unknown. |
| Groups and weights | Equal weights and explicit selected membership initially; allow supplied weights, exclusions and historical group membership. State whether a selected exposure participates in its own peer benchmark. |
| Pooling and missingness | No automatic pooling or imputation. Show retained/dropped observations and distinct exposure/date counts. Use operation-specific sufficiency, not one universal minimum count. |
| Fits and conditional comparisons | No fit by default; explicit descriptive linear fit and simple strata first. Defer automated model selection and multi-factor adjustment. |
| KDE comparisons | Show bandwidth; allow changing it. Comparable same-unit overlays should offer a shared bandwidth and scale, with sample counts retained. |
| Latest versus historical knowledge | Store retrieved observations and retrieval context. Do not call revised historical data “known at the time” without vintage support. |
| Save and revisit | Save refreshable definitions separately from frozen observations, settings, selections, metadata, images and notes. Explicit promotion to monitoring only where representable. |

The timing distinction is substantive: FRED distinguishes today's information about the past from historical information vintages. Support truthful labels before requiring vintage-capable providers everywhere. [FRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html)

These defaults extend the project's [data-shaping guidance](../../src/kairopsis/skills/kairopsis-analysis/references/analysis-design.md), rather than assuming every transformation already exists. A provider/freshness limitation relevant to monitoring should remain visible, but should not automatically prohibit descriptive exploration with a usable sample.

## Requirements to carry forward

Use RV01–RV22 as coverage checks when evaluating a later design. First settle exposure/field associations, sample semantics and evidence capture; then evaluate how the six chart families share those capabilities. No separate storage architecture, chart library or screen layout is selected here.

Keep extensions narrow: multi-factor residualisation, lead/lag diagnostics, ECDF and dense-scatter alternatives are plausible later additions. Defer curve comparison as requested. Exclude execution, account sizing, portfolio optimisation, automated trade recommendations, strategy backtesting and a general-purpose BI/formula environment.

The desired result is a free research workspace whose operations remain legible: what is being compared, which observations support the comparison, and what evidence was retained for the investment discussion.
