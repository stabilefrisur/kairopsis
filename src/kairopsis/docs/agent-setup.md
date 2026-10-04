# Set up Kairopsis for a user

Use this runbook to install Kairopsis, configure the user's data and provide a
working local launch method. Finish with a verified handoff; installation alone
is not completion. The [human guide](human-guide.md) covers everyday use.

## Give this task to GitHub Copilot

Use [Copilot Agent mode in your IDE](https://docs.github.com/en/copilot/how-tos/copilot-in-your-ide/use-copilot-agents/use-agent-mode?tool=vscode)
connected to the machine where Kairopsis should run. Paste this task into chat:

```text
Set up Kairopsis 0.1.0 for me on this machine using a source tarball; GitHub
cloning is unavailable. Read and execute this agent runbook:
https://github.com/stabilefrisur/kairopsis/blob/main/src/kairopsis/docs/agent-setup.md

You own the download, checksum verification, extraction, environment creation,
installation, configuration and verification. Use your tools to perform these
steps; do not hand me extraction commands to execute. Discover the OS, Python
and existing package-index configuration. Preserve existing research and use
the organization's approved dependency route and compatible Metapyle.

Start with the demo unless I have supplied live-data access. Create and test
a simple start/open launcher and stop method, verify save/export and restart,
and give me the human guide and a concise setup record. Continue through the
handoff criteria. Ask only for genuinely missing information or permissions
required by your tools; report any exact access or policy blocker.
```

The following steps are instructions to the agent. Perform them using terminal,
file, network and browser tools available in the target IDE. The human is not
responsible for downloading or extracting the archive. Fetch this current
runbook before setup; the original 0.1.0 archive contains an earlier guide.
The [plain-text guide](https://raw.githubusercontent.com/stabilefrisur/kairopsis/main/src/kairopsis/docs/agent-setup.md)
is available if that host is permitted; otherwise read the GitHub page through
your available tools.
If access to the runbook or a required tool is blocked, report that blocker
instead of claiming the installation is complete. Keep the configured proxy,
certificate trust and package-index settings in use.

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

For a local source tree when Git cloning is unavailable, follow
[the source archive steps below](#extract-and-install-a-source-archive).

The two guides are installed alongside the package. Locate them without GitHub:

```console
python -c "from importlib.resources import files; print(files('kairopsis').joinpath('docs'))"
```

**Done:** the installed console command runs, dependency checks pass, versions are
recorded and both guide files are available locally.

### Extract and install a source archive

Use this route when you can read GitHub in a browser but cannot clone it, or
when you need local source files for inspection or adaptation.

1. Discover a Python 3.12 or later interpreter. Commands below use `python`;
   substitute the discovered absolute executable, `python3` or Windows launcher
   as needed. Select a writable per-user installation directory. Create a fresh
   download/extraction directory there and set your tool's working directory to
   it. Preserve existing source trees and environments; choose a new directory
   for this trial when one already exists.

   **Done:** the interpreter version and absolute extraction directory are known;
   the directory is empty and existing installations remain intact.

2. Download the named source asset from the
   [0.1.0 release](https://github.com/stabilefrisur/kairopsis/releases/tag/v0.1.0)
   yourself. This command uses Python's standard library:

   ```console
   python -c "import urllib.request; urllib.request.urlretrieve('https://github.com/stabilefrisur/kairopsis/releases/download/v0.1.0/kairopsis-0.1.0.tar.gz', 'kairopsis-0.1.0.tar.gz')"
   ```

   If direct asset downloads are unavailable, obtain the same source distribution
   through the configured approved package index:

   ```console
   python -m pip download --no-deps --no-binary=kairopsis --dest . kairopsis==0.1.0
   ```

   Downloading source metadata through pip can require build dependencies from
   that index. If neither route is permitted, report the failed route and exact
   error; keep extraction and installation pending.

   Verify the published source-distribution checksum before extracting:

   ```console
   python -c "from pathlib import Path; import hashlib; actual = hashlib.sha256(Path('kairopsis-0.1.0.tar.gz').read_bytes()).hexdigest(); expected = '3f7a049b15e6641d3bad49d05a8d9babe3e85ff57e9d93a9fc78655a50b2167c'; print(actual); raise SystemExit(0 if actual == expected else 'Source archive checksum mismatch')"
   ```

   **Done:** the named archive is present and its SHA-256 matches. GitHub's
   automatic **Source code** archives are different artifacts; these commands
   and checksum refer to the attached `kairopsis-0.1.0.tar.gz` distribution.

3. Extract the verified archive, then set your tool's working directory to the
   extracted source directory:

   ```console
   python --version
   python -m tarfile --extract kairopsis-0.1.0.tar.gz . --filter data
   cd kairopsis-0.1.0
   ```

   Confirm `pyproject.toml`, `src`, `tests`, `docs` and `scripts` are present.
   The extracted directory is a source snapshot, with no Git history or remote.

   **Done:** those paths exist under the absolute `kairopsis-0.1.0` source path.

4. Create a dedicated environment in the extracted directory:

   ```console
   python -m venv .venv
   ```

   Use the organization's configured package index for dependencies and the
   `uv_build` build backend. Browser access to GitHub does not supply these
   packages. If using a wheelhouse, add
   `--no-index --find-links /absolute/wheelhouse` to the install command below;
   it must contain compatible runtime dependencies and `uv_build>=0.12.19,<0.13.0`.
   Select any required compatible Metapyle distribution through that same route.

   **Done:** the environment's absolute Python and console-command paths are
   recorded, and the runtime/build dependency route is established.

5. Install the extracted project, check dependencies and launch the demo. The
   explicit environment paths avoid shell activation requirements.

   **Windows PowerShell:**

   ```powershell
   .\.venv\Scripts\python.exe -m pip install .
   .\.venv\Scripts\python.exe -m pip check
   .\.venv\Scripts\kairopsis.exe --help
   .\.venv\Scripts\kairopsis.exe --mode mock
   ```

   **Linux/macOS:**

   ```console
   .venv/bin/python -m pip install .
   .venv/bin/python -m pip check
   .venv/bin/kairopsis --help
   .venv/bin/kairopsis --mode mock
   ```

   Pass explicit writable workspace/config/cache/log paths established in step 1
   of the main runbook. Choose an unused loopback port if 8765 is occupied.
   Run the server in a managed terminal or background process that allows your
   tools to continue verification. On Windows, launch background helpers hidden.
   Open the local browser address through your tools and confirm Analyses, Ideas
   and Library load; HTTP checks can also verify these routes and bundled assets.
   Stop only the process you started using its terminal interrupt or process ID.

   **Done:** installation, dependency checks, console help and local page/asset
   requests succeed in the dedicated environment.

6. Continue at step 3 of the main runbook below to create the user's launcher,
   configure live data when requested, verify persistence/exports, establish
   backup/recovery and complete the user handoff. The local guides
   are at `src/kairopsis/docs/human-guide.md` and `src/kairopsis/docs/agent-setup.md`.

   **Done:** all applicable main-runbook completion criteria pass; unresolved
   live-data or tool limitations are explicit in the setup record.

The installed application keeps configuration and research outside the extracted
source directory. Keep that directory if you intend to adapt the code; after
editing, rerun its environment's `python -m pip install .`, or use
`python -m pip install -e .` for an editable development installation. Preserve
the user's workspace separately when downloading a newer source snapshot.

**Done:** the source tree is available locally, installation and dependency checks
pass, and the demo opens using the environment's installed command. No GitHub
clone or Node.js is required.

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

Perform these checks through your browser tools or the documented local API;
read `/openapi.json` before constructing API requests. If visual or clipboard
verification is unavailable to your tools, record it as unverified and complete
the HTTP/API checks you can run. Report the limitation in the handoff.

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

Save a local `setup-record.md` outside the installed package with the version,
archive checksum, source/environment paths, dependency route (without secrets),
configuration/workspace/backup paths, launch/stop methods and check results.
Test the launcher from outside the source directory, including its browser-open
behavior and stop/restart path. The human handoff is the launcher, stop method
and guide; include any remaining access or verification blockers.

**Done:** the user can open the dashboard, investigate an analysis, save an Idea
and find their notes without running installation or configuration commands.
