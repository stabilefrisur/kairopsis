# Relative-value exploration: design

Proposed implementation design, 10 October 2026. Source baseline: `615334c`;
branch: `codex/explore-workspace-prototype`. No production implementation yet.
Read the [implementation plan](relative-value-exploration-implementation-plan.md)
for sequence, use-case coverage and acceptance gates.

## Decision in brief

Add **Explore**, a saved workspace for constructing and challenging Relative
Value Relationships. A workspace holds many Data Series, Analysis outputs and
related views. An Analysis retains its existing one/two-input meaning.

Reuse Library bindings, Analysis controls and the calculation engine. Add explicit
symbol/field associations, sample selection and multi-view evidence around them.
One resolved result must supply each chart, statistic, drilldown and capture.

Use Workbench as the initial layout, with an enlarged Focus view and optional
question/notes. Six chart families cover the [research catalogue](../research/relative-value-exploration-workspace.md).
The prototype supplies interaction evidence; its calculation code is disposable.

## Scope and user workflow

1. Start empty, from selected Library series/Analyses, or from a saved workspace.
2. Associate fields with symbols where needed; inspect source, units and basis.
3. Add views; choose observations, measures and analytical settings.
4. Highlight, filter, duplicate and compare alternative definitions or samples.
5. Save the workspace for refresh; capture selected views into an Idea as frozen
   supporting, challenging or contextual evidence.

Starting requires neither a thesis nor monitoring. Save an eligible calculation
to Library explicitly; enabling monitoring remains a separate action. No
automatic monitoring when opening, refreshing or saving an exploration.

All 20 core research cases remain in scope, delivered in phases. Curves, RV12
multi-factor modelling and RV20 lag/forward-outcome diagnostics are deferred.
Trading, sizing, backtesting and arbitrary user-code/formula execution are outside
scope. Transforms discussed in the skill but absent from the engine do not become
implemented features merely by appearing in a menu.

## Collection and identity

Library remains the sole catalogue. Metapyle remains the market-data access
interface, following [ADR 0003](../adr/0003-metapyle-data-access.md).

- Each collection item references a Library binding or an explicitly local
  Analysis draft/output. Retain IDs, revisions and resolved definitions.
- Multiple fields for one symbol are separate bindings. Workspace associations
  map a binding/output to a member and semantic field, for example
  `US IG / spread` and `US IG / duration`. These mappings do not alter provider
  queries or convert observations.
- Suggest associations from source/instrument identity; require explicit
  resolution of ambiguity. Provider parameters remain part of query identity.
  Never join on display names. Explicit associations can connect provider-specific
  symbols for the same subject; derived relationships have their own member IDs.
- Retain unit, currency, Comparison Basis, source and return/index semantics per
  measure. Unknown semantics remain unknown. Equal units do not establish economic
  comparability; incompatible subtraction is rejected by the existing engine.
- New provider series use Library's existing create/preview/save flow. Local
  Analysis drafts can use staged series through its existing validation path;
  saving a workspace does not publish those drafts to Library.
- Rating/sector/group attributes are optional workspace metadata, explicitly
  entered or imported with source and effective dates. Numeric conditions can use
  mapped fields. No invented provider classifications or interpretation of arbitrary
  `params` as metadata. Static/current classifications are labelled as such when
  applied to history; overlapping historical assignments are rejected.

Pinned definition revisions are the default. On reopen, report newer Library
revisions and offer an explicit update. Data refresh uses the retained queries;
it does not silently adopt today's Library definitions. Deleted bindings do not
erase a saved definition or frozen evidence.

## Calculations and time

The [Analysis contract](../../src/kairopsis/skills/kairopsis-analysis/references/application-contract.md)
and [calculation order](../../src/kairopsis/skills/kairopsis-analysis/references/combination-map.md#read-the-calculation-in-the-correct-order)
remain authoritative:

**Measure inputs → scale inputs → Standalone/Pair calculation → result standardization.**

Expose existing daily/weekly/monthly Frequency, risk methods and references,
per-input overrides, differences/ratios/residuals and standardization through the
shared editor. Independent scatter axes may use separate Standalone definitions
or Analysis outputs. A Pair still has the engine's shared Measure/Frequency;
independent axis choices must not silently become different Pair semantics.

Keep these purposes separate:

| Setting | Effect |
| --- | --- |
| As-of date | Retrieval/evaluation cutoff; no later observations enter calculations |
| View sample | Dates, members, conditions and measurement endpoints used by the view |
| Analysis histories | Existing reference, fitting and risk-estimation settings |
| Display range/zoom | Visible extent only; never recalculates reference or fit estimates |

Workspace context supplies defaults; each view can override and pin its sample
and as-of date. Historical as-of evaluation uses the actual cutoff, not a cached
latest fit cropped to an earlier date. Such results still use the retrieved data
vintage; they are not claimed to be knowledge available at that historical time.

Percentage changes require positive baselines. Analysis Z-score keeps prior-only
history, sample SD and minimum-history rules. Risk samples, baseline search,
fit timing and unavailable results retain the existing contract. Remove the
prototype's alternative Window Z-score from production choices.

Add only named exploration operations with explicit formulas: common-date
rebasing, chosen-endpoint comparisons, peer summaries/fixed linear comparators,
event alignment and descriptive statistics. Keep their order and inputs visible.
For example, percentage change of a gap differs from a difference of percentage
changes. Engine-supported Analysis construction stays in the shared engine;
exploration operations do not masquerade as saved Analyses or provider series.
Conversions, hedging and other upstream shaping use supplied, documented series
until specifically implemented. Promotion to Library must preserve the exact
formula and is available only when its inputs/settings are representable there.

## Samples and analytical results

An explicit observation selector determines what one mark means:

| Shape | Row identity | Example |
| --- | --- | --- |
| History | Series/output and date | Several spread histories |
| Cross-section | Member at a chosen date/interval | Spread against duration across symbols |
| Two-series history | Two measures matched on date | IG changes against equity-index returns |
| Panel | Member and date | Several symbols over several periods |
| Summary | Group/event/estimate and its contributing rows | Peer median or rolling correlation |

Exact row-date matching is the default. Optional backward as-of selection needs
a maximum age and each field's selected row date and `observed_on`; never fill
from the future. Unknown native dates remain visibly unverified. Descriptive
views may inspect supplied numeric observations under a recorded provenance
policy; Analysis fit/risk/reference eligibility is not relaxed to manufacture
results. Monitoring eligibility never becomes a blanket plotting filter.

Retain candidate/accepted/excluded row IDs and reasons, measurement endpoints,
distinct member/date counts, units, provenance and contributing rows for summaries.
Pooling is explicit; default equal row weights, with equal-member weighting as
an alternative. Missing rows remain missing. Fixed/matched versus each-date peer
membership, dated classifications, weights, and inclusion of the subject in its
own benchmark are explicit choices.

Highlighting changes emphasis only. Filtering creates a new sample/result and
identifies any reference sample kept fixed. Correlation defaults to one complete
common sample; optional pairwise samples retain cell-specific rows/counts.
Drilldowns retain the exact source sample. Chart-family changes either preserve
that restriction or require an explicit release; they cannot bypass it.

Correlation, density, aggregation and descriptive fitting execute in Python over
the resolved sample. Plotly renders returned values. No second statistics path in
JavaScript. A descriptive scatter fit can use the displayed rows or an explicitly
separate fit sample; it records equation, units, sample, residuals and extrapolation.
It remains distinct from an Analysis regression residual. No automatic inference
or pooled-panel fit. Rolling estimates identify the window and actual samples.

## Views and controls

Workbench has a collection at left, ordered/resizable view grid, and selected-view
editor at right. Focus enlarges the same view/result. Optional question and notes
belong to the workspace, without a required Research-sheet workflow. Collapse
secondary diagnostics; show formula, sample meaning and material limitations near
the chart. Reuse the existing visual shell and bundled Plotly.

| Family | Required forms and controls |
| --- | --- |
| History | Overlay or aligned small multiples; explicit rebasing anchor; event-relative paths |
| Scatter | Cross-section, two-series history or explicit panel; independent axes; optional descriptive fit/facets |
| Ranked comparison | Levels or interval changes; paired start/end markers; retained comparator |
| Distribution | KDE default, histogram and box; history/cross-section/panel sample; grouping and selected-value marker |
| Heatmap | Symbols × dates; symbols × fields at a date; grouped dimensions with explicit aggregation |
| Correlation | Series across dates or fields across symbols; Pearson/Spearman; exact-sample drilldown |

Relationship matrices use the Correlation family; they do not require a time axis.
Mixed-unit field heatmaps use separate column scales or explicit comparable
standardized outputs. Never imply raw duration and spread share a numeric scale.

Default marker size is constant. Optional **Size by** maps a suitable numeric
field to marker area with units and a size legend; negative/missing sizes are
reported, not silently absolutized. Highlight uses an outline. Colour/facet/group
choices come only from available fields or explicit attributes.

Distribution evidence records bandwidth/weights or bin edges/normalization or
quartile/whisker rules. KDE offers shared smoothing for comparable overlays,
adjustable bandwidth and observed points; tiny/constant samples remain points.
Dates need ticks and hover values, never an axis title. Use “symbol”, “series” or
“relationship”, not “exposure”. The distribution selector says “KDE”. Explanations
follow each measure's semantics: total-return-index growth is index return;
spread growth is proportional repricing.

## Module interfaces and persistence

Extend the current FastAPI/Jinja/plain-JavaScript application. No new frontend
framework, external browser dependency or required installation-time Node step.
Proposed records/modules below describe responsibilities, not a second catalogue.

| Record / module | Responsibility |
| --- | --- |
| `WorkspaceDefinition` | Versioned collection/mappings, local drafts, attributes, operations, views, context, layout, question and notes |
| `ViewDefinition` | Measure references, observation shape, sample/filter/weight policies, pins and rendering choices |
| Exploration evaluator | Resolve definitions; retrieve union of required bindings/history; reuse Analysis calculations; materialize samples and statistics |
| `ViewResult` | Immutable resolved definition/context, input evidence, rows/exclusions, calculated values/estimates, units and limitations |
| Exploration repository | Save/read versioned workspaces and result bundles; publish complete captures atomically |
| `ExplorationSnapshot` | Frozen workspace context, selected ViewResults, notes/roles, images and portable data |

Reuse draft validation, `catalogue.resolve_definition`, `analytics.evaluate`,
period/risk/standardization logic and repository atomic-write/locking primitives.
Resolve saved workspaces against their captured binding set; today's
`Catalogue.resolve_draft` alone consults the mutable Library and is insufficient
for revision pinning. Keep different revisions of the same ID distinct in the
retrieval bundle, projecting the appropriate bindings into each engine evaluation.
Extract reusable editor context from today's global `state` dependencies. Keep
retrieval, numerical evaluation and rendering testable with supplied data and a clock.

Preview resolves one consistent data bundle for related views and returns a result
ID plus definition/data fingerprints. Retrieve sufficient baseline, risk, fit and
reference history beyond plotted dates; deduplicate identical binding queries.
Partial retrieval fails dependent calculations with reasons while independent
views remain usable. Late responses cannot replace newer drafts. Preview/capture
never updates monitored results, screening runs or Library defaults.

The application interface needs four operations: preview a draft workspace;
save/read a versioned workspace; inspect a resolved result; capture selected
results into an Idea. Route names can follow existing conventions. Validation
errors identify the affected view/measure; revision conflicts preserve the draft.

Save workspaces under `explorations/<id>/versions/` with a current pointer and
expected-version conflict checks. Idea captures live inside the Idea folder and
contain their own definitions, raw/derived observations, sample membership,
estimates, question/rationale, metadata, notes and images. Retain full calculation
inputs beyond visible points. Sharing/copying an Idea requires no live workspace
or current Library entry. Selected views and whole-workspace captures are supported.

Capture takes existing result IDs and matching rendered images; never refetch or
recalculate during capture. Block capture of a superseded preview or expired
result. Publish manifests/pointers only when all referenced files and hashes are
complete. Revisit creates a new result/capture; original evidence stays unchanged.

Keep existing Analysis Snapshot records intact. Add a distinct exploration
evidence entry to Ideas and update every reader/export path to dispatch by kind;
do not stretch the two-input `DisplaySettings`/`Snapshot` into a universal shape.
Use a versioned workspace/Idea upgrade with legacy read support, preservation of
old file bytes and restart recovery. An older binary must reject the new workspace
format rather than silently dropping exploration evidence. Detail and test that
migration before enabling persistent Explore writes.

## Sources and decision status

This design carries forward the [research](../research/relative-value-exploration-workspace.md),
[prototype feedback](../../scripts/explore-prototype-notes.md) and the analytical
review reproduced in the [plan](relative-value-exploration-implementation-plan.md#review-regressions).
It follows ADRs [0003](../adr/0003-metapyle-data-access.md),
[0004](../adr/0004-portable-idea-evidence.md) and
[0005](../adr/0005-analysis-economic-rationale.md).

Workbench, revision pinning and the separate exploration evidence format are
recommended decisions for this implementation. Record an ADR when the persistence
design is finalized; existing ADRs and shipped capability claims remain unchanged
during planning.
