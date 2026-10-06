# Agent setup: Windows source workspace

This is the single installation runbook: obtain the published source archive
through the configured mirror, extract a local source workspace, and adapt its
dependencies to the existing private data-access setup. The agent performs every
technical step and hands the user a working launcher. The [human guide](human-guide.md)
covers everyday use.

## Give this task to GitHub Copilot

Use Copilot Agent mode in the IDE running in the target Windows session. Paste:

```text
Read and execute this runbook:
https://github.com/stabilefrisur/kairopsis/blob/main/src/kairopsis/docs/agent-setup.md

Set up Kairopsis 0.1.0 as an extracted upstream source workspace on this Windows
machine. You own archive acquisition, extraction, local dependency adaptation,
installation, configuration, verification and launcher creation. Use the existing
package mirror and working private Metapyle setup. Preserve existing research.
Hand me a tested launcher, stop method and human guide. Ask only for missing
private setup information or required tool permissions; report exact blockers
instead of giving me technical steps to carry out.
```

Read this current GitHub guide before starting; the published 0.1.0 archive
contains an earlier guide. GitHub pages are documentation references. Archive
and package acquisition use the existing mirror, not GitHub asset downloads.

## 1. Inspect the existing Windows setup

Work under the ordinary user account in its active session. The target provides
Windows, Python 3.12, Chrome, uv and virtual environments, without administrator
rights or Node.js/npm. Public package-index access and GitHub cloning are not
installation routes. The application serves this user on `127.0.0.1`.

Inspect the current IDE workspace, working data-access project and configured
package tools. Establish these private inputs before installation:

- Absolute paths to Python 3.12, uv and Chrome.
- The existing mirror, authentication, proxy and certificate configuration.
  Keep credential values out of transcripts and setup records.
- The working renamed data-access project's actual distribution name, immutable
  version/revision, source routing and provider environment. Its import namespace
  remains `metapyle`; read package metadata rather than inferring the distribution
  identity from the project directory's name.
- Existing Kairopsis installations, research workspaces and launchers to preserve.

Set `$KairopsisPython` and `$KairopsisMirror` from these findings. Set
`$KairopsisRoot` to an approved writable per-user directory; inspect
`Join-Path $env:LOCALAPPDATA 'Kairopsis'` as the default. Establish separate
directories for downloads, source, bootstrap tools, configuration, research,
cache, logs, launchers, private evidence and backups. Keep mutable state outside
the source tree and environments.

uv does not read pip configuration. Verify the mirror is explicit for both tools
and every active index is approved; preserve existing authentication and trust.
Internal URLs, package identities and credentials stay in private configuration.
Missing access is a specific blocker, not permission to install a substitute
provider or a new toolchain.

**Done:** tools, mirror, private provider route, preserved research and absolute
paths are identified; a private setup record is established.

## 2. Obtain the upstream source archive from the mirror

Define `$KairopsisDownloads`, `$KairopsisBootstrap` and `$KairopsisSourceParent`
under the chosen root, using fresh version-specific directories. Reuse an
existing directory only when its record proves it belongs to this installation.
Preserve modified source and environments. Run through your terminal tool:

```powershell
$KairopsisVersion = '0.1.0'
New-Item -ItemType Directory -Force -Path $KairopsisDownloads | Out-Null
uv venv $KairopsisBootstrap --python $KairopsisPython --no-python-downloads --seed --default-index $KairopsisMirror
if ($LASTEXITCODE -ne 0) { throw 'Bootstrap environment failed' }
$KairopsisBootstrapPython = Join-Path $KairopsisBootstrap 'Scripts\python.exe'
& $KairopsisBootstrapPython -m pip download --index-url $KairopsisMirror --no-deps --no-binary=kairopsis --dest $KairopsisDownloads "kairopsis==$KairopsisVersion"
if ($LASTEXITCODE -ne 0) { throw 'Upstream source download failed' }
```

Seeding pip and obtaining source metadata may require build packages, including
`uv_build`, from that mirror. Confirm it supplies this version's source `.tar.gz`.
If only a wheel is available, or the release/backend has not reached the mirror,
record the exact missing artifact/package and stop this step. Retain the source
workspace route. No manual download or extraction is assigned to the human.

Verify the source distribution published for this release:

```powershell
$KairopsisArchive = Join-Path $KairopsisDownloads 'kairopsis-0.1.0.tar.gz'
$KairopsisArchiveHash = (Get-FileHash -LiteralPath $KairopsisArchive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($KairopsisArchiveHash -ne '3f7a049b15e6641d3bad49d05a8d9babe3e85ff57e9d93a9fc78655a50b2167c') {
    throw 'Upstream source checksum mismatch'
}
```

**Done:** the mirror-supplied source archive matches the published SHA-256;
version, hash and private acquisition route are recorded.

## 3. Extract and preserve the source snapshot

Ensure the destination does not contain modified source. Extract with the
discovered interpreter:

```powershell
New-Item -ItemType Directory -Force -Path $KairopsisSourceParent | Out-Null
& $KairopsisPython -m tarfile --extract $KairopsisArchive $KairopsisSourceParent --filter data
if ($LASTEXITCODE -ne 0) { throw 'Source extraction failed' }
$KairopsisSource = Join-Path $KairopsisSourceParent 'kairopsis-0.1.0'
Set-Location -LiteralPath $KairopsisSource
```

Confirm `pyproject.toml`, `src`, `tests`, `docs`, `scripts` and `uv.lock` exist.
Retain the archive and pristine dependency metadata before local adaptation.
This source tree has no upstream Git history or remote. Read its `AGENTS.md`
and domain pointers before changing project files.

**Done:** complete local source and recoverable upstream metadata exist without
overwriting research.

## 4. Adapt private dependency routing locally

The published project declares `metapyle>=0.1.6`. Reuse the existing working
private distribution's established installation source and immutable revision;
retain its `metapyle` import namespace. Edit only the extracted local project:

- Replace the public `metapyle` requirement in `[project].dependencies` with the
  actual private distribution requirement and established source mapping. A
  renamed distribution does not satisfy the original metadata requirement merely
  because `import metapyle` works.
- Copy the applicable private uv source/index definitions from the working setup.
  Make the approved mirror the default index; retain approved package-specific
  routing and existing authentication, with credential values outside metadata.

Keep these adaptations and the resulting lockfile private. The published
`uv.lock` contains an upstream dependency set and public artifact URLs; it is a
reference, not a lock to force onto this environment. Resolve a local lock against
the mirror and selected private sources next. Preserve the working provider
project; its code/configuration is not part of the public Kairopsis distribution.

Reuse the working provider artifact, including its import/version metadata.
Changing a distribution name alone does not establish compatible imports. If
the selected artifact fails to import without the public package beside it,
record that packaging mismatch instead of installing overlapping providers.

**Done:** local metadata and routing explicitly select the established private
distribution, with no unintended public Metapyle dependency.

## 5. Resolve and install the local project with uv

Run from the extracted source directory:

```powershell
uv sync --no-dev --python $KairopsisPython --no-python-downloads --default-index $KairopsisMirror
if ($LASTEXITCODE -ne 0) { throw 'Local resolution or installation failed' }
$KairopsisEnvironment = Join-Path $KairopsisSource '.venv'
$KairopsisAppPython = Join-Path $KairopsisEnvironment 'Scripts\python.exe'
$KairopsisCommand = Join-Path $KairopsisEnvironment 'Scripts\kairopsis.exe'
uv pip check --python $KairopsisAppPython
if ($LASTEXITCODE -ne 0) { throw 'Installed dependency check failed' }
& $KairopsisCommand --help
```

uv installs the project in editable form. Retain its source, `.venv` and local
lockfile. Mirror coverage may be incomplete: report exact missing versions.
Use an alternative set only when an existing validated setup or explicit owner
decision supplies it; record changes and rerun relevant checks. Never silently
relax pins. Startup uses the installed environment without dependency resolution.

Verify the provider import:

```powershell
& $KairopsisAppPython -c "import json, importlib.metadata as m, metapyle; print(json.dumps({'kairopsis_version': m.version('kairopsis'), 'metapyle_import': metapyle.__file__, 'metapyle_distributions': m.packages_distributions().get('metapyle', [])}, indent=2))"
```

Match it to the expected installed distribution and immutable private artifact
or revision. An import path/version alone does not establish that identity.
Record exact resolved dependencies and metadata changes privately. Verify
templates, bundled JS/CSS/vendor assets and both guides under the installed
`kairopsis` resources. Also verify the complete `skills/kairopsis-analysis` folder,
including its references. No frontend compilation is needed.

Locate the bundled analysis skill through the installed interpreter:

```powershell
& $KairopsisAppPython -c "from importlib.resources import files; print(files('kairopsis').joinpath('skills', 'kairopsis-analysis', 'SKILL.md'))"
```

Read that entry point when configuring analyses. In the extracted source workspace,
`AGENTS.md` points to the same skill under `src/kairopsis/skills`. For an agent using
a separate workspace, load the entry point directly or copy the **whole**
`kairopsis-analysis` folder into that agent's supported skill directory (for
example, `.agents/skills` for an agent supporting that convention). Preserve any
existing customized copy; record the package version and refresh the copy when
upgrading. Package inclusion alone does not register a skill with every agent.

**Done:** resolution, dependencies, console command, private provider identity
and complete local assets are checked.

## 6. Configure and verify an isolated demo

Create a private verification TOML and fresh mock workspace outside the source
tree. Use the CLI's actual `--help` options and `[kairopsis]` keys: `mode`, `host`,
`port`, `timezone`, `workspace`, `config_dir`, `cache_dir`, `log_dir`. Set `mock`,
`127.0.0.1`, an unused permitted port, the user's IANA timezone and absolute
writable paths. Preserve existing live research separately. Resolve inherited
`KAIROPSIS_*` settings so they cannot redirect verification to another workspace;
CLI overrides environment and TOML.

Set `$KairopsisConfig` to the verification TOML. Start the installed command
in an agent-managed process so your tools remain available:

```powershell
& $KairopsisCommand --config $KairopsisConfig
```

Use Chrome/browser tools and HTTP checks for Analyses, Ideas, Library, charts
and local assets. All frontend resources load from localhost without external
fonts, CDNs, runtime package installation or Node.js/npm. Start background Windows
processes hidden. Record the process you own and stop only it.

**Done:** the isolated demo starts from outside the source directory and serves
pages/assets without external frontend requests.

## 7. Configure the existing live-data access

Create a separate live configuration/workspace using the working data-access
project's provider runtime setup. Authentication, private endpoints and environment
requirements remain private. Launch the installed command with that configuration
under the active user session, without installing/upgrading packages at startup.

Read the [analysis configuration skill](../skills/kairopsis-analysis/SKILL.md)
before selecting series, shaping and analytical settings. Read the running
`/openapi.json`. Use its API or Library UI to add authorized
series and a Standalone or Pair Analysis with established symbols, fields,
parameters and units. Library owns `workspace/metapyle.yaml`; change entries
through the application. The adapter requires compatible `Client`, catalogue
validation/load/export, `get()` and `close()` behavior; see
[runtime](../../../docs/runtime.md) in the extracted source.

Check observations, dates and units against the authorized source. Provider
failures remain explicit; never substitute demo observations. API freshness,
native-date provenance and monitoring calibration remain unverified unless the
implementation and actual data establish them. A chart alone does not establish
fresh monitoring or calibrated thresholds.

**Done:** the live workflow is checked with the existing private provider, or its
precise access/API/data limitation is recorded. Demo success alone is not live setup.

## 8. Verify research, persistence and recovery

In the isolated demo, then authorized live workspace where available:

- Open an Analysis; save a verification Idea/chart; add and reopen a note.
- Export an image and spreadsheet-ready observations. Check clipboard reuse or
  its explicit download fallback through available Chrome tools.
- Stop/restart with the same configuration; verify retained evidence, note contents
  and configured series remain intact.
- Stop before backing up the whole workspace. Restore into a fresh directory and
  verify it opens without altering the original research.

Use browser tools or the local API contract. Record unavailable visual/clipboard
checks as unverified; HTTP success alone does not establish those behaviors.
Preserve existing files on schema/corruption errors rather than deleting research.

**Done:** save/export/restart and trial restore pass; all untested behaviors and
live-data limitations are explicit in the private record.

## 9. Create and test the user's launcher

Create a start/open shortcut and stop method in the user's writable launcher
directory, using absolute installed-executable/configuration paths. Start hidden,
wait for the expected localhost page, then open it in Chrome. Track the owned
process; repeated starts reuse the correct instance and stopping affects only it.
Report failures with local logs rather than opening an unrelated service on an
occupied port. Test spaces in paths and launch from another working directory.

The launcher performs no `uv run`, `uv sync`, pip installation, frontend build,
dependency resolution or external download. It runs under the active user session;
shared hosting and operation after logout are outside this setup. Automatic
session launch is optional only if requested, through the existing user-level
scheduling mechanism.

**Done:** start/open, duplicate launch, stop and restart work; the user needs no
terminal commands to open the prepared workspace.

## 10. Hand off and retain private evidence

Save `setup-record.md` outside source/package directories with the archive hash,
local metadata adaptations, tool/dependency versions, private provider identity,
source/environment/configuration/research/backup paths, mirror outcome, launcher
and stop paths, check results and exact unresolved blockers. Redact credentials;
internal setup records and research remain private.

Give the user the launcher, stop method, local browser address, backup location,
verified demo/live status and local [human guide](human-guide.md). Explain remaining
limitations briefly. The human manages research, not archive extraction or setup.

**Done:** the source workspace uses the mirror and intended private provider;
the tested launcher/handoff work and target-only checks are accurately recorded.
This guide specifies the recorded target; mock checks elsewhere cannot establish
its actual mirror or live-data availability.
