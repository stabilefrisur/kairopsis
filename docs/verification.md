# Verify a distribution

These are maintainer checks for release artifacts. Target installation follows
the single [agent setup runbook](../src/kairopsis/docs/agent-setup.md).

Verify the built artifacts as well as the source checkout. Source tests establish
application behavior; installed-package checks establish that the distribution
contains the code, browser assets and guides needed outside the checkout.

## 0.2.3 installation candidate — 23 October 2026

The compact transfer builder omits the upstream lockfile while the full source
distribution retains it. Dependency resolution uses the target's approved
sources after local metadata adaptation. The runbook also handles earlier
transfers that still carry the upstream lock.

The bundled `kairopsis --self-check` (or `python -I -m kairopsis.self_check`)
checks mock routes, page assets, calculations, evidence save/reopen and image
export. It uses temporary state and in-process requests without opening a port,
reading user configuration or requiring extra test dependencies. JSON reports
include the imported package path, version and completed checks; failures return
a nonzero exit status.
Live provider behavior, local adapter patches, browser rendering and launchers
still require the runbook's target acceptance checks.

All 447 source tests pass, including inherited
live settings, temporary-state cleanup and injected asset/persistence failures.
Mypy passes for all 28 application modules. A separately installed
wheel passes from outside the checkout with conflicting inherited launch settings;
its resource, vendor and source-byte inventory checks pass. This is local Linux
verification, not target Windows/live acceptance. Version 0.2.3 carries these
changes and requires copying both bundled skills to the outer agent workspace
and verifying discovery. The original 0.2.2 transfer remains available unchanged.
Standards and specification reviews found no outstanding installation issues.

## Code-view transfer preparation — 21 October 2026

The 0.2.2 candidate adds a compact text transfer and an agent upgrade runbook.
It carries deployment source and reuses seven browser-library files from the
0.1.0 wheel only after SHA-256 verification. Developer tests, scripts and sample
datasets remain in the full source distribution. Application behavior is unchanged.

The full source suite passes 440 tests; three further transfer cases also pass.
All 16 transfer cases cover copied text, UTF-8 BOM/CRLF, paths with spaces,
old-package discovery without importing its code, missing/changed libraries,
payload corruption, existing destinations, directory links and archive paths.
Mypy checks 27 application files. Wheel inventory/vendor hashes and strict
metadata checks pass. Public artifact scans found no private target material.

Actual Windows Python 3.12 extraction reuses the 0.1.0 wheel's libraries and
reconstructs every application file byte-for-byte. Re-extraction rejects the
existing directory. A separate Linux editable installation resolves offline
from cached dependencies and serves all main pages and vendor assets in mock
mode. Rebuilding a wheel from the transferred source produces identical wheel
contents. These checks do not establish target mirror coverage, live-provider
access, research migration or target launcher behavior; the runbook checks those.

### Rebuild the copyable file

Build and audit wheel/source artifacts first, then run:

```sh
python scripts/build_transfer.py /path/to/kairopsis-VERSION.tar.gz /fresh/output/kairopsis-VERSION.py
python /fresh/output/kairopsis-VERSION.py --check --reuse-from /path/to/old/kairopsis
python /fresh/output/kairopsis-VERSION.py --extract /fresh/deployment --reuse-from /path/to/old/kairopsis
```

Use the approved baseline wheel's package directory for the reuse check. Compare
every reconstructed runtime file against the candidate wheel, test Windows
extraction and build/install from the deployment source. Review the readable
bootstrap, decoded payload and reused-file manifest for public suitability.
The builder selects deployment files only from the audited sdist, normalizes
archive metadata and rejects output over 500 KB. Verify the complete generated
file is available in GitHub's Code tab before handing out its pinned link.

Replace the versioned file under `transfer/` only with the verified candidate.
The generated transfer is excluded from wheel/sdist inputs, avoiding recursive
bundles. Regenerate it after any packaged change; retain artifact hashes and
detailed checks in private maintainer records. Do not bundle a locally adapted
installation, environments, credentials or research.

## 0.2.1 publication link correction — 11 October 2026

Post-publication checks found that PyPI resolved the README's relative CSV-demo
link against its own project page. Version 0.2.1 uses the absolute public
repository URL and aligns package, lock and setup-guide versions. Application
code and browser assets are unchanged from the tested 0.2.0 release. Repeat
artifact inventories, metadata, source rebuild and released-install checks for
the patch; retain the 0.2.0 numerical/browser evidence below.

## 0.2.0 release candidate — 11 October 2026

The source suite passes 427 tests; mypy checks 27 source files and bundled
application JavaScript passes syntax checks. The source-archive suite against
the separately installed wheel passes 426 tests; one historical Git-baseline
check is intentionally unavailable outside the checkout. The existing upstream
Starlette/httpx deprecation warning remains.

Fresh wheel/source inventories, vendor hashes, portable skill references,
packaged documentation links and strict Twine metadata checks pass. All three
guides are bundled. The public-source and artifact audit found no branding or
private material requiring removal. Numerical variables, third-party identifiers
and the required `gs-quant` dependency name remain legitimate matches.

Installed Chromium checks cover the shared editor, automatic previews,
save/discard, chart/Idea notes, exports and clipboard fallback, CSV Library/data
reuse, chart dates and responsive layouts. The general browser journey now uses
the shared editor and explicitly saves/reopens a fractional monitoring threshold;
Explore acceptance targets the current observation disclosures. CSV research
bytes survive restart and a trial restore into a separate directory.

These checks use isolated Linux environments with mock/local CSV data. They do
not establish corporate Windows launcher behavior, private mirror coverage,
live-provider freshness or P8's larger scale fixture. Private records and
artifact hashes are retained in `.scratch/release-0.2.0/`, outside distributions.

## Explore date controls — 11 October 2026

Single-date comparisons show a date; changes add a From date; histories show a
period. A single workspace/chart date choice replaces overlapping cutoff and end
controls. Missing-date handling, observation filters and display zoom are separate.
Incomplete or inverted periods show a prompt without posting an invalid preview.
Existing explicit sample ends survive unrelated edits.

`scripts/explore-dates-acceptance.py` passes against the CSV demo: numerical change
and percentage endpoints, required dates, workspace/custom dates, exact/backward
matching, history versus zoom, and legacy date preservation. Library definitions
remain unchanged; no JavaScript errors or horizontal overflow were observed.
Review images are in `.scratch/explore-date-review/`. JavaScript syntax and
diff whitespace checks pass.

## Shared Analysis editor and reference periods — 11 October 2026

Library creation/editing and monitoring open one Analysis editor. Charts update
automatically; explicit Save/Discard preserves the distinction between a draft,
the saved definition and Idea evidence. Atomic saves retain revision checks and
staged Series edits. Failures preserve the draft; older responses cannot replace
a newer chart. Legacy Library edit URLs redirect to the same editor.

Reference modes are As-of window (legacy default), Rolling window (new UI
definitions) and Fixed dates. Numerical tests cover prior-only calendar windows,
native-date exclusions, constant/short samples, fixed inclusive dates, forbidden
unfinished references, rank in original units, retrieval warmup, reference-drift
monitoring comparisons, persistence and per-point rolling reference CSV evidence.
Regression fitting independently offers As-of and Rolling windows. Legacy
definitions retain the current retrospective fit; new UI definitions select
rolling fitting. Tests cover prior-only fits, unchanged earlier residuals when
data advances, calendar coverage, missing/carried observations, constant/stale
samples, large input levels, combined fitting/reference/risk warmup, rolling
Z-scores, monitoring refit noise and per-point JSON/CSV evidence across restarts.

Original-units reference controls are collapsed under Percentile reference;
Z-score controls remain visible. A separate browser check verifies preserved
dates, accessible invalid dates and independent monitoring disclosures in the
editor and Explore. Risk history labels distinguish rolling finite windows from
expanding all-history samples. Four risk estimators were checked against earlier
evaluation cutoffs for both finite and expanding histories; past values agree.

All **427 tests** pass. Mypy checks the changed Python modules; changed
JavaScript passes syntax checks. `scripts/analysis-editor-acceptance.py` verifies
the shared editor, all three modes, automatic updates, save/discard, conflicts,
preview failure/retry, response ordering, inline Series edits, independent Idea
capture and desktop/laptop/narrow layouts without JavaScript errors. Review
images are in `.scratch/editor-review/`.
The extended journey also verifies independent regression/reference modes,
expanding fit history, saved/reloaded rolling settings, latest-fit scatter labels
and copied per-point fit evidence. The CSV rolling regression chart updated in
0.89 seconds in this local run; images are in `.scratch/rolling-fit-review/`.
The existing CSV Explore browser journey also passes, including all 74 Library
series, cached updates, explicit refresh and local Analysis construction. The
restarted demo's existing Analysis opens with As-of window selected; a before/after
Library comparison confirms its saved definitions were not changed.

## CSV demo and Explore data reuse — 11 October 2026

The active review demo now reads all 74 manifest series through Metapyle's
`localfile` adapter and Library validation. The manifest's credit symbol/field
associations populate Explore; query fields remain omitted for CSV retrieval.
The importer explicitly declares the generated no-fill observation dates while
preserving unverified market freshness. A weekly spread change matches the
two actual CSV endpoints. No monitoring is enabled.

Explore preloads a selected collection, reuses observation coverage and calculated
results, fetches only missing dates and explicitly replaces its snapshot on
Refresh data. Failed replacement preserves the prior snapshot. Cache isolation,
eviction, capture identity and date/provenance retention are tested.

All **408 tests** pass; mypy checks 25 source files and modified JavaScript passes
syntax checks. Both the CSV browser acceptance and existing usability journey
pass, including delayed updates, failure/retry, field grouping and local Analysis
construction. One measured cached chart-type change took 0.81 seconds including
debounce and rendering; this is a local example, not a latency guarantee.
Reproducible launch: `scripts/run_csv_demo.py`; browser check:
`scripts/csv-demo-acceptance.py`. Local review images: `.scratch/csv-demo/review-final/`.

## Explore controls — 11 October 2026

Explore legends sit below every chart. Long labels wrap; chart cards grow to
preserve plotting height. Browser checks cover all six chart families, full/half
width and narrow layouts, long labels, legend toggling, repeated redraws and PNG
export. Review images are in `.scratch/legend-review/`; no JavaScript errors were
observed. The date-control acceptance still passes. The older CSV-demo journey
stops at its fresh-Library assumption of exactly 74 entries in the populated demo;
the targeted checks use the existing Library without changing saved definitions.

Explore now updates charts automatically after settings changes. Authoring controls
use plain labels; source definitions are read-only, grouping and classifications
have separate forms, and chart selection/evidence roles appear in the save/export
flow. The overview has an explicit return action from an enlarged chart.

The 73 exploration/statistics tests pass. Chromium acceptance covers all six chart
families, immutable captures, offline reopening and editable copies. The dedicated
`scripts/explore-usability-acceptance.py` journey verifies automatic series/type
updates, delayed-response ordering, text-edit preservation, failed-update retry,
unchanged provider queries after grouping edits, classification entry, calculation
input dialogs, explicit chart selection and desktop/laptop layout. JavaScript
syntax and both browser scripts' Python compilation pass. No browser script errors
were observed. Local evidence: `.scratch/explore-ux-review/`.

## Explore foundation — 10 October 2026

Milestone 1 (P1–P6) is implemented on `codex/explore-workspace-prototype`.
GPT-6.1 SOL at high effort built the feature; the parent agent independently
reviewed the changes from `a2b6daa`, checked numerical results and exercised the
production UI. The source suite passes **377 tests**; mypy checks all 24 modules,
and modified JavaScript passes syntax checks.

All **23 independent acceptance checks** pass. They use actual Metapyle `localfile`
retrieval through Library, with three symbols, multiple fields, gaps and a signed
series crossing zero. Pearson/Spearman, OLS and Gaussian KDE match SciPy;
histogram density and box quartiles match NumPy. Checks cover historical cutoffs,
display independence, distinct binding revisions, retained drilldown samples,
auxiliary size/colour
fields, save conflicts, capture hashes, restart/export and old-model compatibility.

Chromium journeys verify Library selection, matrix-to-scatter drilldown, question
and notes, multi-view capture from Focus, saved/frozen reopen, multiple fields per
symbol, non-time heatmaps, size/None, rendered percentage units, empty selections
and shared local Analysis controls. The existing Library/Analysis acceptance
journey also passes its 13 checks. No script errors or laptop page overflow were
observed. Additional checks verify readable distribution legends at 1440/1180px,
Focus/PNG export, and forking with Library additions and a fresh preview while
the original capture remains byte-identical. Reusable Explore checks:
`scripts/explore-ui-acceptance.py`.

Review fixes include stale draft labels, filtered drilldown membership, missing
encoding dependencies, percentage units, Plotly title compatibility, first-click
editor actions, initial distribution grouping, compact chart legends,
unprovenanced fit rows and schema-2 Idea serialization. Evidence:
`.scratch/explore-milestone-review/` and the builder's isolated acceptance records.

One existing Starlette/httpx deprecation warning remains. These source/mock and
local-file checks do not establish external market-provider coverage, corporate
Windows deployment or release-scale performance. P7 research operations and P8
release/scale acceptance remain planned; no distribution release is claimed.

## 0.1.2 release verification — 8 October 2026

All 304 source tests and mypy checks for 20 files pass. The release wheel and
source archive pass inventory, local-link, vendor-checksum and strict Twine
checks. Both skills and guides are present; eval tooling and reports remain
outside the distributions. No project branding or private material required
removal; numerical variables, vendor internals and the `gs-quant` dependency
identity remain legitimate matches.

A clean Linux wheel install passes the Chromium research journey: chart and Idea
notes, saved/Latest exports, clipboard fallback, Library editing and desktop/mobile
layouts, with no script errors or external browser requests. Notes, shortlist
state and original image hashes survive restart. Three acceptance selectors now
target chart notes specifically, because rationale adds a separate prose element.
CLI/resource discovery, editable source-archive installation and a byte-identical
sdist-to-wheel rebuild pass. Evidence: `.scratch/release-0.1.2/`.

One upstream Starlette/httpx deprecation warning remains. These are Linux/mock
checks; corporate Windows, mirror coverage, live-provider behavior and economic
calibration require target evidence.

## Hatchling migration verification — 8 October 2026

The Hatchling migration passes all 304 source tests and mypy checks for 20 source
files. One upstream Starlette/httpx deprecation warning remains. Locked uv sync,
wheel/source builds, resource inventory and strict Twine checks pass. Both skills,
guides, browser assets and vendor licenses match the checkout. Source archives
retain project metadata, tests, acceptance scripts, lockfile and domain docs;
eval suites, harnesses and run records are excluded.

A clean wheel installation outside the checkout serves all navigation pages and
linked local assets in mock mode. CLI/resource discovery and an editable install
from the extracted source archive pass. Rebuilding that archive produces a
byte-identical wheel. Evidence: `.scratch/hatchling-migration-2026-10-08/`.
Final documentation and package checks: `.scratch/chat-completion-2026-10-08/`.
These checks establish Linux package behavior; Windows/mirror/live-provider
acceptance and statistical calibration remain unverified.

### Skill evaluations — 7 October 2026

Five fresh GPT-5.6 Sol High subjects tested the frozen screening skill: four
clean passes, one partial, 49/50 completeness. The start/retry case was blocked
before subject dispatch and remains unscored. The partial confused a weekly move
with between-evaluation materiality. See the repository-only
[screening report](https://github.com/stabilefrisur/kairopsis/blob/main/docs/research/screening-skill-sol56-evaluation-2026-10-07.md).

After the shared setup and interpretation guidance changed, three fresh GPT-5.6
Sol High subjects scored two clean passes and one partial, 29/30 completeness,
with no critical failures. The partial omitted the overlap explanation for
weekly changes. See the repository-only
[systematic monitoring report](https://github.com/stabilefrisur/kairopsis/blob/main/docs/research/systematic-monitoring-skill-evaluation-2026-10-07.md).
Different cases and one execution per case do not establish comparative
improvement, production reliability or statistical calibration.

Reusable cases, rubrics and harness instructions live in the repository's
[screening suite](https://github.com/stabilefrisur/kairopsis/tree/main/evals/kairopsis-screening)
and [systematic monitoring suite](https://github.com/stabilefrisur/kairopsis/tree/main/evals/kairopsis-systematic-monitoring).
Keep generated fixtures, complete subject outputs and machine-readable run
records in ignored local storage; commit concise reports and reusable tests.
Repository links are intentional: these eval resources are absent from published
distributions. Historical sections below record the checks performed at each
stage; their test counts describe those stages.

## Economic Rationale — 7 October 2026

The full source suite passes 279 tests, including 16 rationale HTTP cases; mypy
and modified JavaScript syntax checks pass. Coverage includes omitted versus
cleared text, both save/preview routes, definition revisions, retained Latest and
export after Library edits/deletion, and byte-identical legacy evidence. Focused
Chromium verification passes draft retention, literal multiline rendering,
outdated preview text and exploratory transfer, with no script errors.

The built wheel passes the 16 rationale cases from an isolated environment outside
the checkout. Wheel/source builds, inventory and strict Twine checks pass. Four
skill files match the installed wheel and source archive; an independently copied
skill validates with 108 local links/anchors. An independent GPT-6.1 Sol High trial
saved/read back rationale, assessed challenging historical evidence using its
captured reasoning, and handled a supplied simulated older schema without claiming
an unsupported save. These are synthetic-data and offline-schema checks; they do
not establish live-provider or corporate Windows acceptance. Standards and Spec
reviews report no findings. Evidence: `.scratch/analysis-economic-rationale/`.

## Retained screening — 7 October 2026

The source suite and the source-archive tests against the installed wheel outside
the checkout each pass 304 tests; mypy checks 20 files and compilation passes.
Coverage includes idempotent starts, concurrent catalogue/Idea edits, actual
comparison baselines, partial/failed/unverified/retained outcomes, empty and
300-Analysis universes, restart recovery, failed publication, disk-full status
fallback and path containment. Repeated runs retain at most two evaluations per
Analysis; original bytes survive copying. A real local-CSV Metapyle test verifies
that an intervening catalogue edit cannot change captured request bindings.

Eight portable-helper regressions cover uncertain submissions, exact-run polling,
read-only access, independent folder copies, containment and brief versions with
readback. Chromium verifies automatic and manual dashboard retention against
both source and installed Linux apps, with no script errors. Wheel/source builds,
inventory and strict Twine checks pass. Both independently copied skills match
the wheel/source archive: seven files and 110 local links/anchors. The inventory
rejects a missing screening entry point or linked helper.

An independent GPT-6.1 Sol High trial reviewed a real copied mock run and disclosed
synthetic overlapping-theme/incomplete-coverage fixtures. It accounted for every
monitored summary, inspected supporting and challenging evidence and baselines,
and saved/read back separate briefs without changing evidence or refreshing data.
The normal screen-now CLI trial was blocked by automatic execution review without
a stated reason. The trial then mistakenly invoked the helper through another
script; that execution is recorded as a deviation, not a clean CLI pass. Subsequent
review remained offline. Automated helper and application tests passed separately.

Standards and Spec reviews have no outstanding findings after containment fixes.
Evidence: `.scratch/agent-screening/`, including the corrected retained-baseline
trial in `trials/evidence-report-v2.md`. These checks do not establish corporate
Windows operation, live-provider freshness or economic calibration.

## Source and packaging checks

```sh
uv sync --locked
uv run pytest -q
uv run mypy src/kairopsis
uv build
uv run python scripts/acceptance/inspect_wheel.py dist/kairopsis-VERSION-py3-none-any.whl --require-assets --source-directory . --output /absolute/output/wheel-inventory.json
uvx --from twine twine check --strict dist/*
```

Hatchling builds the wheel and source archive; uv remains the build frontend and
dependency manager. The inventory requires all three installed guides and both skills,
checks that each skill's local Markdown links resolve within its own
folder, checks source completeness and vendor checksums, and rejects accidental
private runtime material. Source archives include docs, tests, acceptance scripts,
the lockfile and domain context. Eval suites, harnesses and evaluation reports
are excluded from both distributions. Full run records stay in ignored local
storage. Keep scratch records and credentials outside published artifacts.

## Installed application

Install the wheel into a separate environment with approved dependencies. Launch
from outside the checkout using fresh writable directories. Verify Analyses,
Explore, Ideas and Library, local assets, an Analysis, saved Idea evidence, notes,
exports and restart persistence. Verify all three guides through
`importlib.resources.files('kairopsis').joinpath('docs')`.

Check both skills through `importlib.resources.files('kairopsis').joinpath('skills')`:
`kairopsis-analysis` and `kairopsis-screening`. Copy each entire folder into an
isolated directory and validate it there: entry points, local references and
helper scripts must work without the repository. Verify the same files survive
an sdist-to-wheel rebuild. Bundling is distinct from registering the skills with
the user's agent; the setup guide describes discovery.

Verify screening through real HTTP requests with isolated storage: idempotent
starts, exact-run polling, no-refresh reads, manual/daily retention, frozen
definitions, mixed data outcomes, interrupted runs and failed publication.
Check portable current/comparison evidence and separately versioned briefs.
Exercise hundreds of summaries without embedding complete histories. Agent trials
must cover starting a run, reviewing existing competing themes, and quiet or
incomplete coverage; mock success does not establish live-provider freshness.

For an automated journey against an isolated running demo instance:

```sh
uv run python scripts/browser_acceptance.py --url http://127.0.0.1:8765 --output /absolute/output/browser
uv run python scripts/screening_acceptance.py --url http://127.0.0.1:8765 --output /absolute/output/screening-browser
```

The scripts create verification records; the screening journey needs a fresh
workspace to verify the initial daily run. Supply a separate workspace rather than
an existing research workspace. Prepare Playwright Chromium before network-limited
checks. `scripts/acceptance/run_windows.py` also provides an installed Windows
harness; its output directory must not exist.

## Historical verification before the v2 controls

The analysis-skill packaging follow-up verifies identical skill resources in a
fresh wheel and source archive, installed-resource discovery from an isolated
environment outside the checkout, and validation of a separately copied skill
folder. The wheel inventory rejects a missing skill entry point, a missing linked
reference, and a reference escaping the skill folder. Agent trials cover relative
weekly shocks, a level-over-risk request, event pass-through and precomputed
monthly returns; the guidance distinguishes unsupported calculation/cadence
requirements from economic recommendations. These checks concern the skill and
distribution contents, not a new release or target live-data acceptance.

At this stage, the implementation passed 88 source tests. Typechecking, packaged source
and browser-asset inventory, installed guide discovery and strict Twine checks
have passed. Tests also run from an extracted source archive without a checkout.

An installed Linux demo has loaded all navigation pages and local assets and
produced a mock Analysis preview from a separate environment. Full installed
Windows and live-provider acceptance must be verified for the target release.
Provider credentials, data semantics, calendars, freshness and monitoring
threshold suitability are separate from package completeness.

The longer-period follow-up passes source/type/syntax checks and actual browser
verification of reference, fitting and risk-estimation choices through 30 years.
HTTP coverage verifies combined retrieval bounds, explicit short-history
limitations and preserved long settings in defaults and captured evidence after
restart. A browser calculation completed 30-year weekly volatility estimates for
both regression inputs using 7,828 prior observations each. Screenshot:
`.scratch/period-controls/library.jpg`. Distribution checks must be repeated for
the next release.

The month/all-history follow-up covers calendar month-end and leap-date windows,
prior-only reference percentiles, common-history OLS and leg risk estimates,
retrieval bounds and defaults/Snapshot persistence after restart. Mock history
has a finite 1960 inception. Library controls and Investigation calculations
were checked in the browser, including a longest-history regression using
17,413 prior common observations from 1 January 1960 to 29 September 2026.
Screenshot: `.scratch/period-controls/months-and-available.jpg`. Source validation does not establish live-provider
acceptance of a longest-history retrieval request.

Longest-history risk estimates were compared with the direct estimators for
beta, equal/exponential volatility, VaR and Expected Shortfall. Online moments
and ordered losses avoid repeatedly fitting or sorting the growing history.
Browser verification completed equal-weight volatility for both regression
inputs using 17,404 prior common measured observations; no console errors.

Z-score standardization passes hand-worked standalone changes/returns, pair
spread-gap and prior-only regression-residual examples. Coverage includes
carried-observation exclusion, constant/short references, unsupported
configurations, reference-roll novelty suppression and native threshold
crossings, plus defaults/Snapshot/CSV persistence after restart. Full source
suite: 88 passing tests; type and JavaScript syntax checks pass. Browser checks
verified standalone weekly changes, the current prior-history reference and
±2 threshold lines. Screenshot: `.scratch/period-controls/standalone-zscore.jpg`.

## Historical verification: Analysis controls and v2 contract

The v2 follow-up adds the 120-combination evaluation/serialization matrix,
hand-worked level and ratio Z-scores, all four level-risk methods with both
estimation bases, prior-only cutoffs and reference-only eligibility, the six unit
examples, negative/self beta, divisor cancellation and optimized/direct parity.
HTTP checks cover preview/defaults/restart, independent per-input bases,
retrieval warm-up, incompatible contract baselines and retained Latest. Old
payloads with omitted fields survive restart and export with original files
unchanged. The full source suite passes 263 tests; mypy and JavaScript syntax
checks pass.

`scripts/analysis_controls_acceptance.py` checks actual Chromium controls in both
surfaces: level/volatility, ratio Z-score save/reopen, shared formula/units,
independent regression bases, arity restoration, keyboard editing, threshold
clearing, delayed-response suppression and invalid-source draft retention. The
existing browser journey also passes notes, saved/Latest exports, inline staged
series and desktop/mobile checks. Both journeys passed against an isolated
installed Linux wheel launched from outside the checkout, with no script errors.
Evidence is retained under `.scratch/analysis-controls/`.

Fresh wheel/sdist builds, source/browser-asset inventory, strict Twine metadata
and installed guide discovery pass. Five skill Markdown files match between
wheel/sdist and validate independently after copying (13 portable links).
The source-archive test suite also passes against the installed wheel outside
the checkout. This verifies Linux synthetic data only; installed Windows,
actual provider calendars/freshness, live long-history retrieval and economic
monitoring calibration remain unverified. Existing monthly-cadence limitations
remain in place. No release was published.

## Analysis skill evaluation — 7 October 2026

Three matched cases used six fresh GPT-6.1 Sol agents at High effort, with and
without the frozen skill. Both arms met all five criteria in every case; no
accuracy advantage established. The repository-only [evaluation report](https://github.com/stabilefrisur/kairopsis/blob/main/docs/research/analysis-skill-evaluation-2026-10-07.md)
records prompts, scoring, observed differences and limits. All runs completed
before targeted guidance changes; scores describe the pre-edit skill.

Four generated drafts validate against the application model; illustrative
arithmetic and exact percentile boundaries pass direct checks. Final validation
passes frontmatter, 104 local links/anchors and unchanged 60 worked rows covering
120 settings. Four skill Markdown files match a fresh wheel/source distribution,
with no web links or bundled source-notes file. Research citations remain in repo
docs. No live application/provider test or monitoring change was performed.
