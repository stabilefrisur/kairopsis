# Verify a distribution

These are maintainer checks for release artifacts. Target installation follows
the single [agent setup runbook](../src/kairopsis/docs/agent-setup.md).

Verify the built artifacts as well as the source checkout. Source tests establish
application behavior; installed-package checks establish that the distribution
contains the code, browser assets and guides needed outside the checkout.

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
uv run python scripts/acceptance/inspect_wheel.py dist/kairopsis-0.1.2-py3-none-any.whl --require-assets --source-directory . --output /absolute/output/wheel-inventory.json
uvx --from twine twine check --strict dist/*
```

Hatchling builds the wheel and source archive; uv remains the build frontend and
dependency manager. The inventory requires both installed guides and both skills,
checks that each skill's local Markdown links resolve within its own
folder, checks source completeness and vendor checksums, and rejects accidental
private runtime material. Source archives include docs, tests, acceptance scripts,
the lockfile and domain context. Eval suites, harnesses and evaluation reports
are excluded from both distributions. Full run records stay in ignored local
storage. Keep scratch records and credentials outside published artifacts.

## Installed application

Install the wheel into a separate environment with approved dependencies. Launch
from outside the checkout using fresh writable directories. Verify all three
navigation destinations, local assets, an Analysis, saved Idea evidence, notes,
exports and restart persistence. Verify both guides through
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
