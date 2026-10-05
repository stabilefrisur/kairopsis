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
uv run python scripts/acceptance/inspect_wheel.py dist/kairopsis-0.1.0-py3-none-any.whl --require-assets --source-directory . --output /absolute/output/wheel-inventory.json
uvx --from twine twine check --strict dist/*
```

The inventory requires both installed guides, checks source completeness and
vendor checksums, and rejects accidental private runtime material. Source archives
include docs, tests, scripts, the lockfile and domain context. Keep scratch records
and credentials outside published artifacts.

## Installed application

Install the wheel into a separate environment with approved dependencies. Launch
from outside the checkout using fresh writable directories. Verify all three
navigation destinations, local assets, an Analysis, saved Idea evidence, notes,
exports and restart persistence. Verify both guides through
`importlib.resources.files('kairopsis').joinpath('docs')`.

For an automated journey against an isolated running demo instance:

```sh
uv run python scripts/browser_acceptance.py --url http://127.0.0.1:8765 --output /absolute/output/browser
```

The script creates verification records. Supply a separate workspace rather than
an existing research workspace. Prepare Playwright Chromium before network-limited
checks. `scripts/acceptance/run_windows.py` also provides an installed Windows
harness; its output directory must not exist.

## Recorded scope

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
