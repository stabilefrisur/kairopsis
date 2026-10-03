# Set up Kairopsis for a user

Use this runbook to install Kairopsis, configure the user's data and provide a
working local launch method. Finish with a verified handoff; installation alone
is not completion. The [human guide](human-guide.md) covers everyday use.

## 1. Establish the target

Determine the operating system, available Python, approved package index, desired
mode (demo or live), and existing Kairopsis installation/workspace. Ask only for
missing choices. Use mock mode when no live data source has been supplied.
For live setup, identify the authorized Metapyle installation and source access.

Keep an existing workspace intact. Use a separate empty directory for trials or
incompatible formats. Initial deployment is one local user on loopback.

**Done:** interpreter, package route, mode and absolute writable directories are
known; existing research has been identified.

## 2. Install through the approved package route

Use Python 3.12 or later in a dedicated virtual environment. Activate it using
the target platform's normal mechanism, then install:

```console
python -m pip install kairopsis
kairopsis --help
python -m pip check
```

Use the approved index configuration when public PyPI is unavailable. For an
approved local wheelhouse, use:

```console
python -m pip install --no-index --find-links /absolute/wheelhouse kairopsis
```

The wheelhouse must include runtime dependencies for the target Python and
platform. The application wheel does not embed dependencies. Record the installed
Kairopsis and Metapyle versions. If the environment requires a separately maintained
Metapyle distribution, select it through the approved installation route.

If only the published source tarball is available, install that artifact through
pip, or extract it and install its directory. A compatible `uv_build` backend
must also be available through the approved index or build environment. Neither
route needs a GitHub clone or Node.js.

The two guides are installed alongside the package. Locate them without GitHub:

```console
python -c "from importlib.resources import files; print(files('kairopsis').joinpath('docs'))"
```

**Done:** the installed console command runs, dependency checks pass, versions are
recorded and both guide files are available locally.

## 3. Prepare configuration and launch

Inspect `kairopsis --help` for available options. Choose writable absolute paths
outside the installed package for workspace, configuration, cache and logs.
Use distinct mock/live workspaces. Keep the host at `127.0.0.1`; default port is
8765. If it is occupied, choose another port rather than stopping another process.

CLI options override `KAIROPSIS_<NAME>` environment variables, then TOML settings,
then defaults. `--config` accepts an absolute TOML path with a `[kairopsis]` table.
For example:

```toml
[kairopsis]
mode = "mock"
host = "127.0.0.1"
port = 8765
timezone = "Europe/London"
```

Choose the user's actual timezone for daily refresh boundaries. Use the installed
entry point, with explicit paths in launch automation; do not depend on the current
working directory. Create a launch shortcut or script that starts the server,
waits for its local address to respond and opens the browser. Supply a simple stop
method. On Windows, start background helpers hidden; automatic startup is an
optional user preference. Start mock mode for a credential-free check:

```console
kairopsis --mode mock
```

**Done:** the process stays running, its local browser address loads, and the
actual launch command and directories are recorded.

## 4. Configure live data when requested

Start `--mode live` with the selected separate workspace. Use **Library → Data
series → Add data series** to create entries. Enter actual source identifiers,
symbols, applicable fields/paths, units and supported query parameters. For local
CSV/Parquet input, supply an absolute file path and the exact column name.
Provider installation and authentication belong to the provider's runtime setup.

Library manages `workspace/metapyle.yaml`; do not edit it independently of Library.
Its metadata file commits definitions and dependencies together, and startup
rebuilds the YAML projection. For automation, use the application's local API
contract exposed at `/openapi.json`, rather than guessing request fields or writing
workspace files directly.

Create a Standalone Analysis for one series or a Pair for two series. Open its
chart and verify actual observations, units and dates against the authorized
source. Saving a series validates its structure; it does not prove a successful
fetch or the economic meaning of a symbol. A failed source must remain explicit.

The public Metapyle integration leaves retrieval freshness and native observation
dates unverified. Do not describe inspectable live charts as verified monitoring.
Demo thresholds are illustrative; selecting live mode does not calibrate them.

**Done:** each requested source is explicitly configured and its selected data
has been checked, or the exact access/validation blocker is reported. Do not
substitute mock observations for missing live data.

## 5. Verify the installed application

Run from a directory outside the checkout. Check all of the following:

- Analyses, Ideas and Library load; scripts/styles/charts are served locally.
- A configured Analysis displays expected observations and units.
- Save a uniquely named verification Idea and chart; add a note and export it.
- Restart using the same configuration. Reopen the Idea and confirm its chart
  and note persist. For a clipboard failure, verify the download fallback.
- A separate workspace remains separate from the user's existing research.

Use only fabricated data in a clearly labelled demo check, or data the user has
provided for the live check. The application supplies its frontend assets and
requires no runtime asset downloads. This does not remove live-provider network
requirements.

**Done:** installed launch, data display, save/export and restart checks pass;
any remaining live-data limitations are recorded.

## 6. Set up backup and recovery

Stop the application before copying the entire workspace. Restore into another
empty directory and verify the restored Ideas before redirecting the user's
launch method. Preserve existing files on corruption or incompatible-schema
errors; do not reset a workspace to make startup succeed.

**Done:** backup location and restore procedure are recorded; a trial restore
opens the retained evidence without modifying the original workspace.

## 7. Hand off to the human

Provide the launch shortcut, local browser address,
demo/live status, configured analyses, backup location and how to stop the app.
Give the user the local `human-guide.md`. Explain any unresolved data limitations
in plain language; keep implementation details in your setup record.

**Done:** the user can open the dashboard, investigate an analysis, save an Idea
and find their notes without running installation or configuration commands.
