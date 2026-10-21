# Agent setup: Windows source workspace

This is the single installation runbook for replacing an existing version,
including 0.1.0, from a local text file. The transfer contains all current
application code, guides and skills; unchanged browser libraries are copied from
the existing package only after checksum verification. The agent owns every
technical step through a tested launcher. The [human guide](human-guide.md)
covers everyday use.

## Give this task to a local agent

Open the release file linked on the
[transfer page](https://github.com/stabilefrisur/kairopsis/tree/main/transfer)
in GitHub's **Code** tab. Copy its complete contents into a local UTF-8 file
named `kairopsis-0.2.2.py`. Raw access is unnecessary. Give the local IDE agent
its absolute path with this task:

```text
Install Kairopsis from <absolute path to kairopsis-0.2.2.py>.
Inspect its first 200 lines; keep the encoded payload out of chat.
Use the existing Kairopsis installation's Python 3.12 to run --check, then
--extract into a fresh per-user source directory. If using another Python,
locate the existing kairopsis package and pass --reuse-from PACKAGE_DIRECTORY.
Read the extracted src/kairopsis/docs/agent-setup.md and execute it from step 1.

An existing 0.1.0 installation may work: inspect it and reuse its approved
package routing and private data provider. Prepare and verify the replacement
before switching launchers. Preserve research and a recoverable backup.
You own installation, configuration, verification and launcher creation.
Keep all target-specific information and adaptations private; never submit them
to web searches, public repositories, issues or uploads. Hand me a tested
launcher, stop method and human guide. Ask only for missing information or
required tool permissions; report exact blockers locally.
```

Use the bundled guide; GitHub main may describe a newer version. If source is
already extracted, continue below without extracting again. Preserve 0.1.0
until its browser libraries have been copied and the replacement verified.

## 1. Inspect and preserve the existing setup

Work under the ordinary user account in its active Windows session. Use the
existing Python 3.12, uv, Chrome and virtual environments. No administrator
rights or Node.js are required. Public package-index access, GitHub cloning and
Raw downloads are not installation routes. Extraction needs no network. The
application serves this user on `127.0.0.1`.

Inspect the IDE workspace, existing launcher, package tools and working
data-access project. Establish these inputs locally:

- Absolute paths to Python 3.12, uv and Chrome.
- The approved mirror, authentication, proxy and certificate configuration.
  Keep credential values out of transcripts and setup records.
- The working data-access distribution's actual name, immutable version/revision,
  source routing and provider environment. A renamed distribution may still
  import as `metapyle`; inspect metadata rather than guessing from a folder name.
- Existing Kairopsis executable/interpreter, version, installed dependencies,
  local source adaptations, configuration, research, launcher and owned process.
  Inspect the interpreter behind the launcher, not whichever Python is on PATH.

Set `$KairopsisPython`, `$KairopsisUv` and `$KairopsisMirror` from these findings.
Use the old application's Python for transfer when possible. Otherwise find its
package directory with its interpreter, without importing the application:

```powershell
& $KairopsisOldPython -c "import importlib.util; from pathlib import Path; print(Path(importlib.util.find_spec('kairopsis').origin).parent)"
```

Set `$KairopsisPackage` to that directory and pass
`--reuse-from $KairopsisPackage` on both transfer commands below. It is the
directory containing `__init__.py` and `static`, not the environment root.
If the old package is absent or its browser hashes differ, recover the approved
0.1.0 artifact through the established mirror/cache into an isolated temporary
installation. Keep its dependencies/provider separate from the replacement.
Never substitute CDN downloads or bypass checksum checks.

Choose a writable per-user root; inspect `Join-Path $env:LOCALAPPDATA 'Kairopsis'`
as the default. Separate transfer files, source, configuration, research, cache,
logs, launchers, private records and backups. Keep mutable state outside source
and environments. Save package versions and routing in the private record.

uv does not read pip configuration. Verify approved sources explicitly and
preserve existing authentication and trust. An earlier successful installation
establishes working routes, not availability of every new dependency version.

Keep organization/person names, internal addresses, private package identities,
local paths, credentials, logs, research and adapted source local. Never include
these in web searches, public issues, repositories or diagnostic uploads. The
public runbook describes generic steps; discovered values stay private.

Retain the old environment and launcher during preparation. Stop only the
identified application process before copying the entire research workspace.
Verify backup file inventory and hashes; preserve external configuration needed
for recovery privately. Restart the old app if needed during preparation.
Test the new version against a separate backup copy; it must not write the
original research yet.

**Done:** tools, approved sources, provider identity and installation paths are
known; a verified research backup and private setup record exist.

## 2. Verify the local transfer file

Set `$KairopsisTransfer` to the user-supplied file and `$KairopsisSourceParent`
under the chosen root. Run through your terminal tool:

```powershell
$KairopsisVersion = '0.2.2'
& $KairopsisPython $KairopsisTransfer --check
if ($LASTEXITCODE -ne 0) { throw 'Transfer verification failed; inspect the reported cause' }
```

Add `--reuse-from $KairopsisPackage` if using a different interpreter.
Confirm the reported version matches the release. Verification covers both the
text payload and every reused browser library before writing any files.

The embedded SHA-256 detects damaged/truncated payloads; it does not authenticate
the executable wrapper. Use the intended repository revision and compare an
external release manifest if supplied. Preserve the original transfer file and
its hashes. LF/CRLF line endings in correctly saved UTF-8 files are supported.
Syntax errors or payload mismatches require a complete copy from the Code tab,
not disabling verification. Expand any collapsed code; exclude line numbers,
page navigation and Markdown fences. If the page cannot expose the complete
text, report that precise transfer limitation.

**Done:** payload and reused libraries pass verification without downloads;
version and hashes are recorded privately.

## 3. Extract and preserve the source snapshot

Choose a fresh directory. If this exact transfer was already extracted
successfully, reuse that directory and skip the extraction command:

```powershell
$KairopsisSource = Join-Path $KairopsisSourceParent "kairopsis-$KairopsisVersion"
& $KairopsisPython $KairopsisTransfer --extract $KairopsisSource
if ($LASTEXITCODE -ne 0) { throw 'Source extraction failed' }
Set-Location -LiteralPath $KairopsisSource
```

Add `--reuse-from $KairopsisPackage` when needed. The extractor rejects existing
destinations, including empty directories. After an interrupted extraction,
retain that directory for inspection and retry to a fresh path. It copies only
verified vendor files from the old package; all application code comes from
the new payload.

Confirm `pyproject.toml`, `src`, `docs`, `uv.lock`, `AGENTS.md`, `CONTEXT.md`
and `transfer-manifest.json` exist, and project/manifest versions agree. This
deployment workspace omits developer tests, scripts and sample datasets to keep
the Code-view transfer small. Those remain in the full source distribution;
installation and the built-in mock mode do not require them. Packaging another
public release from this adapted deployment workspace is outside this runbook.

Retain the transfer file and pristine dependency metadata privately before
adaptation. This source has no Git history or remote. Read its `AGENTS.md` and
domain pointers before changing project files.

**Done:** complete application source, browser assets, guides and skills are
local; original installation and research remain recoverable.

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
the mirror and selected private sources next. Move the upstream `uv.lock` to the
private backup record before resolving, so its public artifact URLs cannot
be reused for installation. Preserve the working provider
project; its code/configuration is not part of the public Kairopsis distribution.

Reuse the working provider artifact, including its import/version metadata.
Changing a distribution name alone does not establish compatible imports. If
the selected artifact fails to import without the public package beside it,
record that packaging mismatch instead of installing overlapping providers.

**Done:** local metadata and routing explicitly select the established private
distribution, with no unintended public Metapyle dependency.

## 5. Resolve and install the local project with uv

Run from the extracted source directory. First try the existing cache without
network access; if packages/build requirements are missing, retry through only
the approved mirror/private sources. Preserve complete diagnostics locally:

```powershell
& $KairopsisUv sync --offline --no-dev --python $KairopsisPython --no-python-downloads --default-index $KairopsisMirror
if ($LASTEXITCODE -ne 0) {
    & $KairopsisUv sync --no-dev --python $KairopsisPython --no-python-downloads --default-index $KairopsisMirror
}
if ($LASTEXITCODE -ne 0) { throw 'Local resolution or installation failed' }
$KairopsisEnvironment = Join-Path $KairopsisSource '.venv'
$KairopsisAppPython = Join-Path $KairopsisEnvironment 'Scripts\python.exe'
$KairopsisCommand = Join-Path $KairopsisEnvironment 'Scripts\kairopsis.exe'
& $KairopsisUv pip check --python $KairopsisAppPython
if ($LASTEXITCODE -ne 0) { throw 'Installed dependency check failed' }
& $KairopsisCommand --help
```

uv installs the project in editable form. Retain its source, `.venv` and local
lockfile. This is a separate environment: do not copy an old `.venv`, use global
site-packages, or uninstall the working provider to make resolution pass.
The mirror/cache must also supply build requirements such as Hatchling.
Mirror coverage may be incomplete: report exact missing versions locally.
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
templates, bundled JS/CSS/vendor assets and all three guides (human, Explore and setup) under the installed
`kairopsis` resources. Also verify the complete `skills/kairopsis-analysis` and
`skills/kairopsis-screening` folders, including references and scripts. No frontend
compilation is needed.

Locate both bundled skills through the installed interpreter:

```powershell
& $KairopsisAppPython -c "from importlib.resources import files; print(files('kairopsis').joinpath('skills', 'kairopsis-analysis', 'SKILL.md'))"
& $KairopsisAppPython -c "from importlib.resources import files; print(files('kairopsis').joinpath('skills', 'kairopsis-screening', 'SKILL.md'))"
```

Use the analysis skill to define calculations and record their economic rationale.
Use the screening skill to run and retain a screening, or review an existing run,
then interpret its evidence and save a brief. In the extracted source workspace,
`AGENTS.md` points to both skills under `src/kairopsis/skills`. For an agent using
a separate workspace, load the relevant entry point directly or copy each **whole**
skill folder into that agent's supported skill directory (for
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

Use Chrome/browser tools and HTTP checks for Analyses, Explore, Ideas, Library, charts
and local assets. All frontend resources load from localhost without external
fonts, CDNs, runtime package installation or Node.js/npm. Start background Windows
processes hidden. Record the process you own and stop only it.

**Done:** the isolated demo starts from outside the source directory and serves
pages/assets without external frontend requests.

## 7. Configure the existing live-data access

Create a separate live configuration/workspace using the working data-access
project's provider runtime setup. For an upgrade, point verification at the
backup copy and use a distinct port. Authentication, private endpoints and environment
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
- Where supported by the target checkout, verify Library and Analyses open the
  same editor. Preview a draft automatically, save/read back a deliberate change,
  and discard a second draft without changing the saved definition.
- Verify Explore separately: add Library series, confirm automatic charts, select
  chart dates, save/reopen a workspace and capture/reopen frozen evidence. Check
  cached edits and explicit Refresh data without enabling monitoring. Use the
  [Explore guide](explore.md) for controls and scope; older releases may lack them.
- Export an image and spreadsheet-ready observations. Check clipboard reuse or
  its explicit download fallback through available Chrome tools.
- Stop/restart with the same configuration; verify retained evidence, note contents
  and configured series remain intact.
- Start a screening through the screening skill. Verify its run ID, retained
  evidence, coverage and saved brief; review that same run after restart without
  another refresh. Treat demo or unverified results according to their labels.
- Stop before backing up the whole workspace. Restore into a fresh directory and
  verify it opens without altering the original research.

Use browser tools or the local API contract. Record unavailable visual/clipboard
checks as unverified; HTTP success alone does not establish those behaviors.
Preserve existing files on schema/corruption errors rather than deleting research.

**Done:** save/export/restart and trial restore pass; all untested behaviors and
live-data limitations are explicit in the private record.

For an upgrade, also open existing Ideas, charts, notes, Library entries and
retained screening evidence in the copied workspace. Compare file inventories
and representative records with the backup. Stop on schema or compatibility
errors and keep the original usable; do not reset or delete research to pass.

## 9. Switch and test the user's launcher

Switch only after replacement dependency, demo, live-provider and copied-research
checks pass. If live access is unavailable, keep the existing working live
launcher and report the prepared replacement's limitation.

Stop the old owned process for final cutover. If research changed during setup,
make and verify a fresh backup, copy it to the replacement's permanent research
directory, and repeat the existing-record checks there. Point the replacement
configuration at that directory. Preserve the old launcher/environment and
original workspace for rollback; never run both versions against one workspace.

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

Retire the old active shortcut after the replacement starts correctly. Rollback
means stopping the replacement and restoring the old launcher with its original
workspace, never pointing 0.1.0 at files the new version changed. Research
created after cutover belongs to the replacement and must be preserved before
rollback. Retain the verified backup. If removing the old installation, first
prove its environment/directory is dedicated to Kairopsis; remove only that
installation, never a shared provider environment, configuration or research.

**Done:** start/open, duplicate launch, stop and restart work; the user needs no
terminal commands to open the prepared workspace.

## 10. Hand off and retain private evidence

Save `setup-record.md` outside source/package directories with the transfer and
payload hashes, reused-library verification, old/new package versions,
local metadata adaptations, tool/dependency versions, private provider identity,
source/environment/configuration/research/backup paths, mirror outcome, launcher
and stop paths, check results and exact unresolved blockers. Redact credentials;
internal setup records and research remain private.

Give the user the launcher, stop method, local browser address, backup location,
verified demo/live status and local [human guide](human-guide.md). Explain remaining
limitations briefly. The human manages research, not archive extraction or setup.

**Done:** the transferred source workspace uses approved dependency routes and the intended private provider;
the tested launcher/handoff work and target-only checks are accurately recorded.
This guide specifies the recorded target; mock checks elsewhere cannot establish
its actual mirror or live-data availability.
