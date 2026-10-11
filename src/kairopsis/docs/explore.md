# Explore relative-value relationships

Explore is a saved research workspace with a collection and several related
charts. Add Library series or saved Analysis outputs, then select the series in
each chart's settings. Source identifiers are read-only. When different inputs
need a shared symbol or semantic field, use **Source details → Change chart
grouping**. This changes their chart associations, not the provider query. Several
fields can describe one symbol. Different revisions/queries retain distinct
collection identities; give revised versions distinct fields if they share a symbol.
Library entries may supply a **Research symbol** and **Research field** under
additional details. Explore uses these as its initial grouping. CSV column names
remain the exact Metapyle query identifiers; the grouping never enters that query.

Use **Add calculation** for existing Standalone/Pair calculations. The controls
are shared with the Analysis editor: input measure, Frequency, risk scaling,
comparison, fitting/reference periods and output scale. Each scatter
axis can use its own workspace Analysis. **Define new input** supplies an input
for that calculation; **Add to workspace** adds its calculated output. Inputs
remain local until **Save calculation to Library** saves the definition and its
inputs for reuse. New saved calculations have monitoring disabled; updating an
existing Analysis preserves its monitoring setting. **Connect new data** creates
a reusable Library series. Adding a calculation or saving a workspace does not
enable monitoring. Opening Explore never starts screening.

## Choose observations and views

The overview shows data, the ordered chart grid and the selected chart's settings.
**Enlarge** focuses one chart; **Back to overview** restores the grid. **Add chart**
sits beside the charts. Add, duplicate, reorder and widen charts to
compare definitions or samples. The working question and notes are optional;
they accompany frozen captures.

History, scatter, ranked comparison, distribution (KDE/histogram/box), heatmap
and correlation render retained server results. **Show** chooses whether a row
represents a symbol on one date, each series over time, two series on matching
dates, or symbols across multiple dates. Choose X and Y explicitly for paired
scatter; the selected collection can contain additional series.

Legends sit below the plots. Long labels wrap and chart cards grow vertically
to keep room for the data. Legend entries remain clickable; PNG exports include
the legend. Series identifiers in retained data remain unchanged.

## Choose chart dates

**Workspace date** supplies the default end date. Each chart can **Follow
workspace date** or **Set chart date**. The latter keeps its own date when the
workspace date changes; it can be earlier or later than the workspace default.

| What to compare | Date controls |
| --- | --- |
| Levels across symbols | **Level on a date**, then the comparison date |
| Changes across symbols | **Change between dates** or **Percentage change**, then **From** and **To** |
| History, distributions over dates or paired scatter | **Start date (optional)** and **End date**; a blank start uses all loaded history |

Change means end minus start, with its sign retained. Percentage change requires
a strictly positive start value. Missing or reversed dates show a prompt;
complete them before the charts can update. Captions describe the dates used by
the displayed result, including while an older chart remains visible.

**Missing dates** defaults to **Leave missing**: the requested date must have an
observation. Weekends and data gaps can therefore produce an empty comparison.
**Use an earlier observation** needs a maximum lookback in calendar days. The UI
starts that limit at seven days when no limit was set; review it for the series.
Every selected field keeps its actual row date and native observation date.
Unknown native dates remain visibly unverified; this choice does not relax the
Analysis engine's risk, regression or Z-score eligibility rules.

**Filter observations** holds symbol selection, row exclusions and matrix
drilldown restrictions. Earlier saved date filters remain visible there when
applicable. Changing chart family preserves those restrictions. Highlighting
changes emphasis only. **Zoom chart** changes the displayed extent while keeping
the calculation sample and Analysis estimation periods. It is available for
history, time heatmaps and scatter over dates.

## Matrices, grouping and visual encodings

Correlation supports series across dates and fields across symbols, Pearson or
Spearman, common complete or pairwise samples. Click a cell to create a scatter
of its exact paired observations. Missing/constant cells remain unavailable.
Symbols × dates and symbols × fields heatmaps retain exact contributors. Mixed
field units use independent column scales; compare the labelled raw values.

Marker size defaults to constant **None**. **Size by** uses a supplied numeric
field and maps its value to area, with a size legend and units. Missing/negative
sizes receive a reported constant fallback. Colour/facets use supplied numeric
fields or explicitly sourced attributes; provider parameters never become
classifications. Dated attributes may not overlap; static assignments are labelled
when applied to history.
Use **Grouping & classifications → Edit classifications** to enter a symbol,
classification, value, source and optional effective dates in ordinary form fields.

## Read the mathematics

Analysis values use the production engine and captured calculation contract.
Risk scales are estimated separately at each chart date: finite histories roll,
and **Longest available history** expands. Regression **Fitting period** chooses
one **As-of window** fit across the chart or a **Rolling window** fit before each
date. Z-score **Reference period** independently chooses **As-of window**,
**Rolling window** or **Fixed dates**. Existing definitions retain their modes;
new UI Analyses start with rolling fitting and reference periods.

Z-scores use eligible observations and sample standard deviation. Fixed-date
references can use later information for earlier chart points; an As-of
regression fit remains retrospective even with rolling Z-scores. Reference
controls also govern percentile in **Original units**, where they sit inside
**Percentile reference** without changing plotted values. See the
[Analysis guide](human-guide.md#investigate-an-analysis) for timing and sample
limits. Descriptive scatter OLS is separate: it fits the view's retained pairs,
and a panel fit requires explicit pooling.

Descriptive statistics execute in Python; Plotly only renders returned values.
Captured algorithm metadata identifies the sample and these conventions:

- Pearson uses centred equal-row sums; Spearman uses average ranks for ties.
  Fewer than two pairs or constant inputs yield unavailable coefficients.
- Intercept OLS requires at least two nonconstant-x pairs; records fitted and
  evaluated rows, equation, original units, residuals and extrapolation.
- Gaussian KDE uses weighted Scott bandwidth and effective sample count. Shared
  bandwidth requires comparable known units. Bandwidth controls scale the recorded
  bandwidth. Tiny/constant samples remain observed points.
- Histogram uses explicit/equal-width bin edges, includes the rightmost endpoint
  in the final bin and records probability density/weights.
- Box summaries use linearly interpolated Hyndman–Fan type7 quartiles for equal
  rows, weighted inverse-CDF quartiles for equal-symbol weighting, and Tukey
  1.5-IQR whiskers terminating at observations.
- Heatmap cell aggregation records the method, count and exact contributor IDs.

Review input source, units, currency, supplied Comparison Basis/description,
retrieval outcome, actual dates and calculation limitations. A total-return index's
percentage growth has the meaning of the supplied index; spread growth describes
proportional repricing. Unknown semantics are labelled rather than inferred.

## Loaded data and refresh

Adding a series loads its observations automatically, even before adding a chart.
All charts in the workspace reuse the loaded observations. Chart settings and
calculation changes reuse these data; unchanged statistics and Analysis outputs
are reused too. A longer history fetches only uncovered dates. Display changes
never enlarge the analytical history.

**Refresh data** explicitly reloads the current collection through Metapyle.
Replacement is atomic: a failed refresh keeps the previous data and reports the
failure. New Library revisions are still adopted explicitly. Retrieval timestamps,
requests, native dates and outcomes are retained; reuse does not imply freshness.

This cache lives in the application process, with at most eight recently used
workspaces, 32 recent chart results and 32 Analysis calculations per workspace.
Restarting the app or evicting an inactive workspace causes its next edit/open to reload.
Saved evidence is independent of the cache and remains immutable.
Provider requests for missing coverage or explicit refresh still bypass
Metapyle's observation cache; workspace reuse happens inside Kairopsis.

For local files only, Library can explicitly declare **File dates are actual
observation dates**. Use this only with documented native dates and no filling or
resampling. The default remains unknown; missing values stay missing. This
declaration allows eligible historical calculations but does not certify market
freshness or enable monitoring.

## Save and retain evidence

**Save workspace** keeps its full retained definitions and sample/view choices.
On reopen, newer/deleted Library records are reported. Refresh uses retained
queries; explicitly update revisions to adopt Library edits. Concurrent saves
return a conflict and preserve your draft.
The version in source details refers to the saved query definition, not a frozen
vintage of market data.

Selecting series or changing chart settings updates charts automatically after
a short pause; text and date edits apply when the field is completed. **Refresh
data** requests a fresh update. While updating, the previous chart remains labelled
and saving/exporting its evidence is disabled. Failed updates offer **Retry update**.
Late responses cannot replace newer choices, and explicit drilldown samples survive
chart-type changes.

Each update creates immutable result IDs, definition/data fingerprints and complete
input evidence. Unsaved results expire after 24 hours. A new update supersedes the
older bundle for capture, including while that update is in progress.

Choose **Save to Idea**, select charts, then **Continue**. The dialog asks for a
title, destination Idea and whether the evidence supports the argument, challenges
it or provides background context. The role organises evidence without changing
calculations. Chart checkboxes appear only in this selection flow or **Export charts**.
Saving evidence copies current result IDs and matching PNGs;
it never retrieves data or recalculates. The capture retains the entire working
question, notes, definitions, calculation inputs, retained/excluded observations,
measurement endpoints, algorithms, provenance and hashes.

Frozen evidence reopens and exports offline after Library edits/deletion or an
application restart. **Download evidence ZIP** includes PNGs, CSVs, full
JSON definitions/data, readable notes and a hash manifest. Copy/fork its workspace
definition with **Make an editable copy** to investigate again; subsequent updates/captures leave the original
evidence unchanged. Copying an entire Idea folder to a compatible workspace
preserves both legacy Analysis charts and Explore evidence.

This foundation implements the six basic chart families and portable workspaces.
Named regimes, events, peer/fixed-weight composites, common-anchor rebasing and
rolling stability operations belong to the subsequent research-operations milestone.
No release-scale performance or new live-provider coverage is implied.
