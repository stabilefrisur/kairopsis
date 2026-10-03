# Verify a distribution

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
exports and restart persistence. Locate the two installed guides through
`importlib.resources` as described in the [agent setup guide](../src/kairopsis/docs/agent-setup.md).

For an automated journey against an isolated running demo instance:

```sh
uv run python scripts/browser_acceptance.py --url http://127.0.0.1:8765 --output /absolute/output/browser
```

The script creates verification records. Supply a separate workspace rather than
an existing research workspace. Prepare Playwright Chromium before network-limited
checks. `scripts/acceptance/run_windows.py` also provides an installed Windows
harness; its output directory must not exist.

## Recorded scope

The current implementation passes 63 source tests. Typechecking, packaged source
and browser-asset inventory, installed guide discovery and strict Twine checks
have passed. Tests also run from an extracted source archive without a checkout.

An installed Linux demo has loaded all navigation pages and local assets and
produced a mock Analysis preview from a separate environment. Full installed
Windows and live-provider acceptance must be verified for the target release.
Provider credentials, data semantics, calendars, freshness and monitoring
threshold suitability are separate from package completeness.
