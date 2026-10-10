# Explore relative-value relationships

Explore is a saved research workspace with a collection and several related
views. Add actual Library series or saved Analysis outputs, then explicitly
associate each item with a symbol and semantic field. Several fields can describe
one symbol. Different revisions/queries retain distinct collection identities;
give revised versions distinct field names if they share a symbol.

Use **Local Analysis** for existing Standalone/Pair calculations. The controls
are shared with Library: input measure, Frequency, risk adjustment/references,
comparison, fitting/reference histories and output standardization. Each scatter
axis can use its own local Analysis. Staged series remain local until explicitly
saved to Library. Applying a local calculation or saving a workspace does not
enable monitoring. Opening Explore never starts screening.

## Choose observations and views

Workbench shows the collection, ordered view grid and selected-view editor.
Focus enlarges the selected view. Add, duplicate, reorder and widen views to
compare definitions or samples. The working question and notes are optional;
they accompany frozen captures.

History, scatter, ranked comparison, distribution (KDE/histogram/box), heatmap
and correlation use the same retained server result. Choose a history, explicit
panel, paired-date history or cross-section. Cross-sections select the as-of
endpoint; ranked interval changes require an explicit start. Percentage changes
require a strictly positive start value.

Exact date matching is the default. Backward selection needs a maximum age and
retains every field's actual row date and native observation date. Unknown native
dates remain visibly unverified. Descriptive numeric inspection does not relax
the Analysis engine's risk, regression or Z-score eligibility rules.

The workspace as-of is a retrieval/evaluation cutoff. A view can use an independent
as-of date; pinning retains that date. Sample start/end, symbols, numeric conditions,
explicit row exclusions and matrix drilldown restrictions determine the analytical
sample. Highlighting only changes emphasis. Display range/zoom changes the visible
extent; it leaves the calculated rows and analytical reference histories intact.
Changing chart family preserves the retained sample restriction.

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

## Read the mathematics

Analysis values use the existing production engine and calculation-contract
version. Z-score uses eligible prior results, sample standard deviation, its own
reference history and minimum sample rule. Current-fit residual/Z-score history
remains retrospective. Descriptive scatter OLS is a separate operation over the
view's retained pairs; an explicit panel fit requires pooling opt-in.

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

## Save and retain evidence

**Save workspace** keeps its full retained definitions and sample/view choices.
On reopen, newer/deleted Library records are reported. Refresh uses retained
queries; explicitly update revisions to adopt Library edits. Concurrent saves
return a conflict and preserve your draft.

Preview creates immutable result IDs, definition/data fingerprints and complete
input evidence. A changed draft requires a new preview before capture. A failed
or late response keeps the previous labelled chart; it cannot overwrite a newer
draft. Unsaved previews expire after 24 hours. A new preview supersedes the older
bundle for capture, including while that preview is in progress.

Select one or several views and **Capture to Idea** as supporting, challenging
or contextual evidence. Capture copies current result IDs and matching PNGs;
it never retrieves data or recalculates. The capture retains the entire working
question, notes, definitions, calculation inputs, retained/excluded observations,
measurement endpoints, algorithms, provenance and hashes.

Frozen evidence reopens and exports offline after Library edits/deletion or an
application restart. **Export evidence** downloads a ZIP with PNGs, CSVs, full
JSON definitions/data, readable notes and a hash manifest. Copy/fork its workspace
definition to investigate again; subsequent previews/captures leave the original
evidence unchanged. Copying an entire Idea folder to a compatible workspace
preserves both legacy Analysis charts and Explore evidence.

This foundation implements the six basic chart families and portable workspaces.
Named regimes, events, peer/fixed-weight composites, common-anchor rebasing and
rolling stability operations belong to the subsequent research-operations milestone.
No release-scale performance or new live-provider coverage is implied.
