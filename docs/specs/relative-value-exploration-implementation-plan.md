# Relative-value exploration: implementation plan

Updated 11 October 2026 through `42706f8`. Branch: `codex/explore-workspace-prototype`;
implementation baseline: `a2b6daa`. **Milestone 1 (P1–P6) is implemented.**
P7 remains planned; P8's full research, scale and target-deployment gates remain open.
See the [implemented guide](../../src/kairopsis/docs/explore.md) and
[verification record](../verification.md#explore-foundation--10-october-2026).
Implement against the [design](relative-value-exploration-workspace.md) and
[Analysis contract](../../src/kairopsis/skills/kairopsis-analysis/SKILL.md).

## Implemented refinements after P6

- Automatic data loading and chart updates; process-local observation and
  calculation reuse; explicit atomic Refresh data.
- Persisted CSV demo with all 74 series imported through Metapyle/Library.
- One saved Analysis editor with Save/Discard, also supplying the controls for
  workspace-local calculations. Explicit As-of/Rolling/Fixed reference periods
  and As-of/Rolling Analysis regression fits, with per-point evidence.
- Chart-specific date controls, signed Change labels, separate filters/zoom,
  bottom legends and wrapping long labels.

[Verification](../verification.md) records numerical/browser checks and their
limits. P1–P6 below describe the implemented foundation; P7–P8 remain the delivery
plan. Rolling Analysis residuals do not complete P7's rolling correlation,
descriptive slope, regime or event operations. The 0.2.0 foundation candidate
passes Linux packaging and installed mock/local-CSV checks; P8's larger scale
fixture, remaining research cases and target/live-provider acceptance remain open.

## Delivery approach

Build a thin, real Library → calculation → view → saved evidence path first.
Then complete chart families and the remaining research operations. The prototype
is a visual reference; do not migrate its independent calculation/state engine.

Two milestones distinguish progress from completion:

- **Usable foundation, after P6:** real bindings and Analysis drafts, six basic
  chart families, saved workspaces and portable Idea evidence.
- **Core feature complete, after P8:** every core RV use case below demonstrated,
  including regimes, comparators, events and stability checks.

P1 → P2 → P3 → P4 → P5 → P6 → P7 → P8. Keep changes reviewable at these seams;
split a phase into smaller commits where useful. No calendar estimates until the
first real-data slice establishes costs and limits.

## P1 — Contracts and regression fixtures

Add exploration records separately from the existing one/two-input models.
Define discriminated measure references, symbol/field mappings, explicit samples,
result identity, exclusions, source semantics and versioned workspace/capture
payloads. Reject ambiguous associations, duplicate field assignments and invalid
operation dependencies. Preserve full binding query identity and revisions.
Two revisions of one binding ID can coexist in an investigation; key retrieval
reuse by resolved query/revision, not the ID or display label alone.

Create deterministic fixtures with three-plus symbols, several fields, gaps,
zero/negative values, mixed units, sparse cadence and unknown observation dates.
Turn the four [review regressions](#review-regressions) into focused acceptance
cases at the relevant implementation seams.

Likely files: new `exploration_models.py`; focused `tests/test_exploration_*.py`.
Gate: contracts round-trip and distinguish raw series, local/saved Analysis
outputs, supplied metadata and missing data without fabricated defaults.

## P2 — Reuse Analysis evaluation with explicit cutoffs

Build an exploration evaluator around existing Catalogue/MarketData/evaluation
interfaces. Add explicit as-of/display context to retrieval while preserving
current callers' defaults. Resolve one input bundle with enough baseline and
estimation history; reuse it across views and isolate partial dependency failures.
Do not use refresh/monitoring paths to produce exploration results.

Reuse all existing Analysis combinations and settings. Read calculation values
and their provenance separately from overall monitoring eligibility; retain the
engine's own risk, fit and standardization eligibility. Keep v1/v2 interpretation
unchanged. Raw or descriptive inspection must never manufacture an unavailable
Analysis estimate.

Likely files: `service.py`, `periods.py`, new `exploration.py`; narrow extraction
from `analytics.py` only if required. Gate: the same resolved Analysis and data
produce identical values, units and estimates through Library and Explore.
Historical as-of excludes later inputs; changing display range leaves overlapping
calculated values unchanged. Existing analytical tests still pass.

## P3 — One sample/result path

Materialize history, cross-section, paired-date and explicit panel rows with
stable identities and retained/dropped reasons. Add exact and bounded-backward
date policies, explicit interval endpoints, independent view samples and pins.
Separate highlighting, filtering, analytical references and display cropping.

Add a preview interface returning immutable result IDs, resolved definitions and
data fingerprints. Rendering, statistics, observations tables, drilldowns and
capture consume these results. Reject stale preview responses/results after edits.
Define result expiry and recovery: an expired unsaved preview requires a fresh
preview, never a silent replacement during capture.

Likely files: `exploration.py`, `app.py`, exploration result storage.
Gate: every plotted value traces to retained rows; an excluded row cannot enter
a statistic or heatmap. Exact-date and as-of tests preserve actual field dates;
partial failures and unverified provenance are visible without hiding usable peers.

## P4 — Workbench with Library and shared controls

Add `/explore` and `/explore/{id}` in the existing shell. Build collection selection,
explicit field association, view creation/duplication/order/width, Focus, question
and notes. Start with history and scatter as the real vertical slice.

Extract the shared editor's catalogue, control-memory and monitoring presentation
dependencies from global page state. Reuse its mathematical controls and staged
series flow. Explore edits local drafts; Library save and monitoring are explicit.
Show older/newer definition revisions and dirty/previewing/current/failed states.

Likely files: `app.py`, `templates/app.html`, `static/analysis-controls.js`,
`static/library.js`, new `static/explore.js`/`explore.css`; shared chart helpers
where useful. Gate: real bindings → independent axis calculations → linked
views works with keyboard controls at desktop/laptop sizes. Existing Library and
Analysis editing still work; opening Explore does not start a screening refresh.

## P5 — Six chart families and descriptive statistics

Complete ranked/paired comparisons, distributions, heatmaps and correlation.
Support both correlation orientations, Pearson/Spearman and common/pairwise
samples with exact drilldowns. Heatmaps include time and non-time layouts.
Implement Size by/None with area legend, available colour fields and faceting.

Compute descriptive fits/residuals and distribution summaries server-side. Record
each algorithm and sample, including fit versus evaluation rows. Specify numerical
conventions before writing each routine: Gaussian KDE bandwidth and weights,
histogram edges/density, quartiles/whiskers, tied ranks and constant-input behavior.
Use shared scales/bandwidth only where comparable; preserve original units.

Likely files: exploration statistics module; `static/explore.js`, chart rendering
helpers. Gate: independent numerical oracles for every statistic; matrices,
drilldowns and captured rows agree. Tiny/constant samples show honest unavailable
states/points. No date-axis titles, unexplained marker sizing or field-blind prose.

## P6 — Save, capture, reopen and export

Implement versioned workspace storage and conflict checks; retained definitions
remain usable after Library edits/deletion. Extend Idea entries/readers for the
new exploration evidence kind while preserving existing Analysis snapshots.
Capture selected views or the workspace from existing result IDs, including the
working question, local notes, roles, data, samples and complete calculation inputs.

Define and implement the workspace/Idea schema upgrade before writes are enabled.
Test legacy reads, byte preservation, backup/restore, interrupted publication and
clean rejection by older binaries. Use repository locking and atomic publication.
Copy/export PNGs and CSV/JSON evidence; include a portable manifest and readable
notes. Reopen a frozen capture offline; fork its definition for a new investigation.
Refresh creates new evidence rather than altering the original.

Likely files: `repository.py`, `models.py` Idea entries, exploration repository,
`app.py`, Idea rendering/export paths. Gate: capture → restart → Library changes
→ offline reopen/export preserves hashes and interpretation. A concurrent edit
returns a conflict; no partial multi-view capture becomes visible. This completes
the usable foundation, not the entire core catalogue.

## P7 — Complete the research operations

Add the remaining typed operations and corresponding controls in three slices:

1. **Peers and comparators:** supplied/datable attributes, numeric filters,
   fixed/matched/each-date membership, group summaries, explicit weights, fixed
   linear combinations and peer-relative measures. Record self-inclusion,
   missing-member policy and effective weights. Default a fixed comparator to
   unavailable when a required member is missing; renormalization is explicit.
2. **Episodes and samples:** named date/condition regimes, common-anchor rebasing,
   event definitions/relative dates, equal-row versus equal-member pooling,
   paired endpoints and comparable reference samples. Display samples/filters
   do not silently redefine an Analysis's estimation sample.
3. **Stability and residuals:** separate descriptive fit/evaluation samples,
   residual rankings, window/regime comparisons and rolling correlation/slopes
   with explicit minimum support. Reuse numerical primitives, not monitoring
   thresholds. No implicit pooled-panel regression or backtest interpretation.

Support these operations over raw or calculated outputs using a small typed,
acyclic operation graph; no expression language or recursive provider catalogue.
Define units, weighting and missingness per operation. Derived summaries can be
plotted/reused in the workspace; promote only exactly representable definitions
through existing Library save/bundle paths, with monitoring disabled by default.

Gate: every remaining core row below has a worked, reproducible journey.
Historical metadata provenance, changing membership and comparator renormalization
remain visible in the captured evidence. Unsupported upstream transformations
stay explicit capability gaps, with supplied-series alternatives.

Finish each slice's numerical contract before its implementation: define the
rebasing anchor/zero rule, endpoint matching, weighted-summary conventions,
event origin/calendar and rolling-window alignment/minimum count. These are
calculation decisions with fixture-based acceptance, not visual-only options.

## P8 — Acceptance, packaging and documentation

Run relevant existing analytics, Library, HTTP, storage and screening regression
suites; type checks and JavaScript syntax checks. Add a focused Playwright Explore
journey using the production app, not the throwaway runner. Check keyboard/focus,
large labels, empty/error/loading states and desktop/laptop layouts.

Exercise a bounded scale fixture: 50 symbols × 4 fields × 10 years of daily rows,
eight views and duplicate calculations. Record retrieval/evaluation/render/capture
time and size. Verify query reuse, stale-response rejection and explicit resource
limits. Any rendering decimation must be labelled and keep full analytical rows;
never silently truncate the statistic or evidence. Set supported limits from these
measurements before release rather than promise untested scale.

Build wheel/source artifacts; verify assets, new guides and offline mock journeys
outside the checkout using existing acceptance tooling. Demonstrate one supported
Metapyle provider workflow separately; mock checks do not establish live calendars
or provider coverage. Remove prototype assets from the production package path
once their useful behavior has been replaced.

Update the human guide, runtime/backup guide and verification record. Extend the
Analysis skill's integration guidance only for implemented behavior; exploration
operations need their own concise contract. Record finalized persistence decisions
in an ADR. Gate: all core cases, review regressions and legacy evidence checks pass;
remaining deployment/provider limits are stated with evidence.

## Use-case coverage

“Complete” below means the intended capability is available with suitable supplied
data; it does not promise a provider supplies every field or classification.

| Research ID | Required demonstration | Complete by |
| --- | --- | --- |
| RV01 | Multi-series levels/moves; common-start rebasing | P7 |
| RV02 | Multiple fields per symbol; independent measures/units | P4 |
| RV03 | Pair outputs and named peer-relative alternatives | P7 |
| RV04 | Supplied Comparison Basis alternatives and engine risk scaling | P4 |
| RV05 | As-of ranking with retained comparator/observations | P5 |
| RV06 | Explicit start/end interval, moves and changed rankings | P5 |
| RV07 | Cross-sectional axes, available colour/size/facets | P5 |
| RV08 | Comparable peer subsets, attributes and retained reference | P7 |
| RV09 | Two-series dated scatter and descriptive fit | P5 |
| RV10 | Named regimes/conditions with comparable samples | P7 |
| RV11 | Separate fit sample, residuals and explanatory range | P7 |
| RV12 | Multi-factor adjustment | Deferred extension |
| RV13 | Historical KDE/histogram/box with selected value | P5 |
| RV14 | Peer/group dispersion across dates | P7 |
| RV15 | Time/field/group heatmaps, breadth and contributor drilldown | P7 |
| RV16 | Both correlation orientations and exact paired evidence | P5 |
| RV17 | Window/regime and rolling correlation/slope comparison | P7 |
| RV18 | Duplicate views varying samples, Frequency, weights and definitions | P7 |
| RV19 | Event-aligned trajectories and distributions | P7 |
| RV20 | Lag/forward-outcome diagnostics | Deferred extension |
| RV21 | Explicit peer summaries/fixed-weight comparators | P7 |
| RV22 | Saved workspace; frozen multi-view Idea evidence; reopen/export | P6 |

## Review regressions

Reproduced against prototype `615334c`, 10 October 2026. Retain these cases in the
production tests; the prototype's happy-path checks did not cover them.

| Failure | Reproduction / observed evidence | Required result |
| --- | --- | --- |
| Sample bypass | Correlation → US IG/MBS cell → add scatter → exclude EM HY → change to Correlation. Rendered n=52, capture n=44; CMBS/USIG r=0.449295 versus retained-data 0.487750. Heatmap family changes also show excluded cells. | One retained sample drives every output, or explicitly release it everywhere. |
| Negative baseline | History of MBS spread less US IG → percentage change. −3.403674 to +4.896498 bp displays −243.859173%. | Nonpositive baseline produces an unavailable percentage change with reason. |
| Lost rationale | Enter Working question in Research sheet; capture chart. Notes survive but question is absent. | Capture the question and rationale applicable at capture time. |
| Wrong explanation | Total-return index + percentage change receives “spread change … not investment return” text. | Field-aware meaning for both axes and captured evidence. |

Also test the acknowledged integration gaps: Analysis Z-score uses prior-only
sample SD and independent reference history; descriptive scatter OLS is not an
Analysis residual; classifications require supplied provenance; binding/output
identity comes from Library or explicit local drafts. Check the
[application contract](../../src/kairopsis/skills/kairopsis-analysis/references/application-contract.md)
and [input semantics](../../src/kairopsis/skills/kairopsis-analysis/references/analysis-design.md)
when implementing these gates.
