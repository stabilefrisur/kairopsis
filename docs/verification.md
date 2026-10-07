# Verify a distribution

These are maintainer checks for release artifacts. Target installation follows
the single [agent setup runbook](../src/kairopsis/docs/agent-setup.md).

Verify the built artifacts as well as the source checkout. Source tests establish
application behavior; installed-package checks establish that the distribution
contains the code, browser assets and guides needed outside the checkout.

## Source and packaging checks

```sh
uv sync --locked
uv run pytest -q
uv run mypy src/kairopsis
uv build
uv run python scripts/acceptance/inspect_wheel.py dist/kairopsis-0.1.1-py3-none-any.whl --require-assets --source-directory . --output /absolute/output/wheel-inventory.json
uvx --from twine twine check --strict dist/*
```

The inventory requires both installed guides and the analysis skill, checks that
the skill's local Markdown links resolve within its own folder, checks source
completeness and vendor checksums, and rejects accidental private runtime material. Source archives
include docs, tests, scripts, the lockfile and domain context. Keep scratch records
and credentials outside published artifacts.

## Installed application

Install the wheel into a separate environment with approved dependencies. Launch
from outside the checkout using fresh writable directories. Verify all three
navigation destinations, local assets, an Analysis, saved Idea evidence, notes,
exports and restart persistence. Verify both guides through
`importlib.resources.files('kairopsis').joinpath('docs')`.

Check the analysis skill through
`importlib.resources.files('kairopsis').joinpath('skills', 'kairopsis-analysis')`.
Copy that entire folder into an isolated directory and validate it there: the
entry point and all local references must work without the repository. Verify
the same files survive an sdist-to-wheel rebuild. Bundling is distinct from
registering the skill with the user's agent; the setup guide describes discovery.

For an automated journey against an isolated running demo instance:

```sh
uv run python scripts/browser_acceptance.py --url http://127.0.0.1:8765 --output /absolute/output/browser
```

The script creates verification records. Supply a separate workspace rather than
an existing research workspace. Prepare Playwright Chromium before network-limited
checks. `scripts/acceptance/run_windows.py` also provides an installed Windows
harness; its output directory must not exist.

## Recorded scope

The analysis-skill packaging follow-up verifies identical skill resources in a
fresh wheel and source archive, installed-resource discovery from an isolated
environment outside the checkout, and validation of a separately copied skill
folder. The wheel inventory rejects a missing skill entry point, a missing linked
reference, and a reference escaping the skill folder. Agent trials cover relative
weekly shocks, a level-over-risk request, event pass-through and precomputed
monthly returns; the guidance distinguishes unsupported calculation/cadence
requirements from economic recommendations. These checks concern the skill and
distribution contents, not a new release or target live-data acceptance.

The current implementation passes 88 source tests. Typechecking, packaged source
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

## Analysis controls and v2 contract

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
accuracy advantage established. The [evaluation report](research/analysis-skill-evaluation-2026-10-07.md)
records prompts, scoring, observed differences and limits. All runs completed
before targeted guidance changes; scores describe the pre-edit skill.

Four generated drafts validate against the application model; illustrative
arithmetic and exact percentile boundaries pass direct checks. Final validation
passes frontmatter, 104 local links/anchors and unchanged 60 worked rows covering
120 settings. Four skill Markdown files match a fresh wheel/source distribution,
with no web links or bundled source-notes file. Research citations remain in repo
docs. No live application/provider test or monitoring change was performed.
