# Run and preserve research

Python 3.12, FastAPI/Uvicorn, Jinja2 and plain JavaScript. All browser assets are packaged locally. Prepare the extracted source workspace through the [agent setup runbook](../src/kairopsis/docs/agent-setup.md); startup never resolves dependencies. Three destinations: Analyses, Ideas, Library.

```powershell
kairopsis --mode mock --host 127.0.0.1 --port 8765 --workspace C:\Users\Me\Kairopsis\rebuild-mock
```

Use the environment's absolute `Scripts\kairopsis.exe` in Windows Task Scheduler. Working directory does not matter. Paths (`--workspace`, `--config-dir`, `--cache-dir`, `--log-dir`) must be absolute, writable and outside the installed package. `--timezone Europe/London` sets daily refresh boundaries. CLI overrides `KAIROPSIS_<KEY>` environment variables, optional `--config C:\absolute\kairopsis.toml` (`[kairopsis]` keys with underscores), then platform defaults.

Mock fixtures are deterministic, explicitly fabricated native-market observations through **30 September 2026**. No credentials/provider connection. New Library bindings require a matching fixture; unavailable bindings produce explicit failures. Monitoring is independent of saving to an Idea.

## Data retrieval and refresh

The first request to the Analyses list (`GET /api/analyses`) on a configured local day starts a background refresh if no refresh attempt has been recorded for that day. Process startup alone does not trigger retrieval. The **Refresh** button (`POST /api/refresh`) runs another attempt every time, including on the same day. Both refresh paths fetch and evaluate every saved Analysis and publish the list's dated results. Failed analyses retain their prior result and lose fresh finding eligibility. There is no timed background polling of the provider.

Opening an Analysis, previewing its settings, previewing a Library Data Series or Analysis, and selecting **Latest data** on an Idea chart each make a separate provider request. These evaluations do not replace the Analyses list's refresh results. Latest uses the chart's captured definition. Reading the Library catalogue, opening or saving an entry without Preview, and viewing Saved evidence do not fetch observations.

A browser reload follows the page's normal behavior: an Analysis chart requests data again; the Analyses list uses its dated refresh results unless the daily trigger applies. Live requests bypass Metapyle's observation cache, but a new request does not guarantee newer observations or verified source freshness. Check the returned observation dates and limitations. Saved Snapshots remain unchanged.

## Retained screening runs

Every manual or daily refresh retains a Screening Run under
`workspace/screenings/<run_id>/`. The dedicated
[screening skill](../src/kairopsis/skills/kairopsis-screening/SKILL.md) can start
and wait for a run, or review one already retained. Calculation and storage remain
in Kairopsis; the external agent interprets the evidence and writes the brief.
There is no embedded agent service or new scheduled polling.

At the start, the run freezes resolved Analysis definitions, Economic Rationale,
monitoring membership, comparison evaluations and relevant Idea references. All
saved Analyses are evaluated, preserving dashboard behavior; the agent normally
reviews the monitored subset. Each result carries its own observation and
retrieval dates. Completion does not imply successful or fresh data: failed,
retained, synthetic, partial and unverified results remain explicit.

`manifest.json` contains a compact summary for every Analysis. Full evaluations,
comparison evidence and failed-attempt records live alongside it. The manifest
is published after its evidence, so an incomplete write cannot appear as a
completed run. A failed publication preserves the preceding dashboard results.
Unfinished runs become interrupted after restart. Run evidence is immutable;
briefs are new, separately identified outputs under `briefs/`.

`POST /api/screenings` accepts a caller-generated `request_id` and returns a
run ID promptly. Repeating that ID returns the same run. The agent polls that
exact ID and resumes it after a timeout; it must not substitute an older run.
Listing and reading runs, detailed evidence or briefs do not refresh data.
The [run contract](../src/kairopsis/skills/kairopsis-screening/references/run-contract.md)
defines routes, fields, coverage and offline review. The existing refresh response
retains its fields and adds `screening_run_id` and `screening_path`.

Copy a completed run's whole folder for review elsewhere; it carries its own
evidence without requiring the original catalogue or workspace. Retained runs
consume disk space; automatic pruning is not provided. Keep one application
process per workspace. Back up the complete workspace while the app is stopped.

## Evidence and recovery

The rebuild uses workspace schema 2. Older/unmarked nonempty workspaces are refused without modification. Choose a new empty directory; no migration or deletion is performed. Retain older user directories independently.

`workspace/ideas/<id>/current.json` selects a committed version under `versions/<version>/idea.json` and `notes.md`. `snapshots/<id>/` contains `snapshot.json`, `image.png` and `data.csv`. Snapshot JSON embeds resolved inputs/risk references, analytical settings, raw/aligned observations, measured inputs/scales/interval starts and retrieval/capture times. Display settings include hidden trace indices and axis ranges; the PNG has a verified content hash. Catalogue and dated evaluation/refresh records live outside the package. No database index is the only copy of evidence.

Files for a version are written before its atomic commit pointer. Interrupted saves leave the previous version readable; unpublished directories are ignored. Snapshot metadata is committed last. Disk/read errors stop capture/export with an actionable message. Removing a chart/note preserves prior versions and Snapshots internally. No History destination is required.

Analysis definitions and resolved evaluation/Snapshot definitions carry optional
`economic_rationale` text. Library edits advance the definition revision; saved
evidence and Latest keep their captured text. Older records default to empty
without file migration or backfilling from Library. On an update, omission
preserves stored rationale and an explicit empty string clears it. Rationale
does not affect numerical calculations, thresholds or data eligibility; a revised
definition follows the existing incompatible-baseline rules.

Saved charts render their frozen observations and settings with the current presentation; Saved/Latest share chart geometry. Original PNGs remain unchanged and can be downloaded under Source and chart details. A chart note sits directly below its plot, with Edit/Delete beside it and source disclosure last.

Legend click shows/hides a series; double-click isolates it. Hidden labels stay dimmed and axes remain fixed while toggling. Image exports and Save to Idea capture `hidden_traces` and `axis_ranges` in DisplaySettings. Older records default to all traces visible and automatic initial scales. Latest keeps the captured selection and recalculates scales from all current traces; changing chart view resets selection. Underlying values and analytical metrics remain unchanged by visibility.

Idea chart actions are Copy data, Copy chart, Download chart, Remove chart. Image actions use the selected view. Copy data uses its full displayed period and supplies spreadsheet-ready TSV with calculated/input values, units, ISO chart/source dates, measured/adjusted inputs, risk scales and interval starts, full numeric precision and blank missing cells. Legend visibility does not remove input columns. Clipboard denial downloads the corresponding PNG or TSV. Copy/export first captures another Snapshot; a capture failure stops completion and preserves the clipboard. Original saved evidence is never overwritten.

Footnotes deduplicate shared source, currency/reference curve and observation dates, with a compact method/reference/Frequency summary for adjusted views. Demo status and applicable fit period remain explicit. Full per-series bindings, calibration, retrieval and quality details stay folded and in portable records. Date axes have no title; numeric scatter axes retain series/unit titles. Idea detail omits the saved-chart count. Owned UI asset URLs include content hashes, so refresh loads changed scripts/styles.

Stop the application before copying the entire workspace for backup. Restore to a separate empty directory and point `--workspace` there. An Idea folder can also be copied under another compatible workspace's `ideas/`; its current pointer and embedded evidence suffice to reopen it. Never copy only images or an index. Preserve corrupt content for recovery; restore a known-good backup rather than resetting a directory.

## Live data and verification

Start `--mode live` in a separate workspace. Library **Add data series** creates a Metapyle catalogue entry; Edit/Delete update it. No separate translation configuration is needed for new entries.

The form uses actual provider identifiers:

| Source | Required query fields |
| --- | --- |
| Bloomberg | Symbol/ticker and field |
| Macrobond | Series symbol; no field or path |
| Local file | Case-sensitive column name and absolute CSV/Parquet path; no field |
| Other registered source | Registered adapter name and its supported symbol/field/path/parameters |

Name is the display label. Catalogue name (`my_name`) defaults to the name with underscores and can be edited under additional details. Units are required. Currency describes the data; Description is optional. Reference curve, comparison currency and adjustment/rebasing have been removed from the form. New series do not generate a comparison-basis record; existing metadata remains readable in earlier definitions and saved evidence. Provider credentials remain in the provider's runtime configuration, outside catalogue query parameters.

`workspace/metapyle.yaml` is a real YAML catalogue readable by Metapyle. Library owns this file: edit entries through Library. `catalogue.json` commits series metadata and analysis dependencies together; YAML is a validated projection rebuilt at startup. A failed metadata commit restores the preceding YAML. Both files belong in workspace backups. Concurrent external edits/import of independent catalogues are not supported in this version.

Metapyle validates source-specific attributes and registered sources before publication. Structural validation does not prove that a symbol exists or that it represents the intended asset. Library save does not fetch observations. Source failures and missing expected columns remain explicit.

Retrieval uses `Client(catalog=..., cache_enabled=False)` → `get([my_name], ..., use_cache=False)` → `close()`. A new client loads a temporary catalogue containing each request's captured bindings. Concurrent Library edits cannot change an in-flight request, and frozen definitions remain usable after active entries change or disappear. No frequency alignment is requested from Metapyle; analytical Frequency remains in Kairopsis.

Public adapter responses remain freshness **unverified** and native observation dates unknown. They support inspectable charts and saved evidence but cannot establish eligible findings. Observation cache bypass remains deliberate; catalogue files are definitions, not an observation cache. Installed adapter capabilities, upstream freshness, calendars and dependency routing require verification in the target environment.

Existing demo fixtures and old snapshots without `catalog_name` keep their previous binding contract. Old live bindings alone may use private `config-dir/metapyle.json` mappings and `get_raw()` for compatibility, including explicitly configured observation-date columns. Edit an old live series, select its real provider and supply its actual symbol/field/path to move future evaluations to the catalogue API. Prior snapshots keep their captured definitions. No automatic translation or guessed migration is performed.

Public Metapyle 0.1.6 has no add/update/remove API or CLI. Kairopsis uses `Catalog` export/load and public `Client` validation behind one module. A generic upstream request tracks those additions: [Metapyle issue #3](https://github.com/stabilefrisur/metapyle/issues/3).

## Analytical conventions

| Item | Applied rule |
| --- | --- |
| Standing | Current-excluded eligible history; `100 × (below + 0.5 × equal) / N`; default reference 3 calendar years; at least 60 prior points. Shorter available history is qualified by sample count. |
| Alignment | Exact supplied row dates, no fill/interpolation. Findings require finite inputs and known native dates equal to the row; weekdays only. Union rows remain inspectable with missing arithmetic. Provider holiday calendars are not verified. |
| Day move | Exact previous weekday session; never skip a missing baseline. |
| Week/month move | Seven calendar days / previous calendar month (day clamped); backward-only baseline within three calendar days. Missing baseline yields unavailable, never zero. |
| Pair | Ordered first minus second, first divided by second (zero denominator unavailable), or first dependent on second explanatory. Difference requires same units; different bases remain explicitly labelled. |
| OLS | Intercept fit over selected full trailing calendar window excluding current. At least 20 eligible pairs; seven-day endpoint tolerance; constant x unavailable. Residual history uses current fit retrospectively. Fit and display/reference windows are independent. |
| Sensitivity | Compare 1y/5y fits where full history permits; indicate a residual direction reversal. Unavailable checks are explicit; no invented stability score. |
| Finding | Configured symmetric level tails and optional native-unit move thresholds. `demo-native-v1` explicitly illustrative. Compatible new native observations establish threshold entry or material movement; same evidence stays quiet. Corrections/definition/method changes suppress market novelty. Regression material movement holds the earlier fit fixed. |
| Ordering | New, materially changed, first-observed condition; then case-folded name and stable ID. One row per analysis, no composite score/quota. |

Risk adjustment is available in the Investigation side panel and as saved Analysis defaults in Library. Supported methods: volatility, beta, historical VaR and Expected Shortfall (CVaR), with common or per-input references/settings. [Calculation conventions](risk-adjustment.md) specify Frequency, prior-only estimation, half-life, downside, units and unavailable cases. Snapshots preserve raw/reference data and adjustment choices; Latest uses the captured definition. Estimator suitability and risk-adjusted monitoring thresholds require target-environment validation.
