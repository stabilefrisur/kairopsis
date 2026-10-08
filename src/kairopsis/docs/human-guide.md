# Using Kairopsis

Kairopsis helps you investigate relative value and keep the evidence behind an
investment Idea. Your setup agent handles installation and data connections;
you work with analyses, charts and notes.

## Open your workspace

Use the launch shortcut or instructions supplied by your setup agent, then open
Kairopsis in your browser. The usual address is <http://127.0.0.1:8765>.

The top navigation has three destinations:

- **Analyses:** find a comparison or individual series to investigate.
- **Ideas:** return to saved charts and notes.
- **Library:** manage the series and analyses available for investigation.

Demo data is fabricated and labelled. It is useful for learning the workflow;
its observations end on 30 September 2026 and its monitoring thresholds are
illustrative. Live data depends on the sources your setup agent configured.

## When data updates

The first visit to **Analyses** each day starts a background refresh if none has
been attempted that day. Choose **Refresh** to fetch and recalculate all saved
Analyses again, as often as needed. Restarting the app is unnecessary.

Opening an Analysis, choosing **Preview** for an Analysis or Library Data Series,
and selecting **Latest data** on an Idea chart each request data again. These
chart requests do not update the Analyses list's results; use **Refresh** there.
Opening or saving a Library entry without Preview does not fetch observations.
**Saved evidence** always shows the captured observations.

Reloading an Analysis chart requests data again. Reloading the Analyses list
shows its last refresh results unless the daily refresh is due. Data is not
continuously streamed; a new request may return the same observations. Check
observation dates and source limitations before treating values as current.

## Ask for a screening brief

Ask your agent: **“Screen my monitored analyses and brief me.”** The bundled
[screening skill](../skills/kairopsis-screening/SKILL.md) starts a refresh, waits
for its saved results, reviews the monitored analyses and saves a readable brief.
The brief groups related developments, tests the recorded economic rationale,
and identifies evidence and follow-up questions. It reports coverage, observation
dates and data limitations alongside any conclusions.

Every manual or daily refresh retains a dated Screening Run, including quiet
runs and failed analyses. You can ask the agent to review a particular saved run
without fetching data again. Its evidence preserves the definitions and rationale
used then; later Library edits do not rewrite it. New briefs remain separate
from that evidence. Your setup agent can enable the skill in your agent workspace.

The app still calculates all saved analyses; the brief focuses on those marked
for monitoring at the run's start. Missing or unverified data is a coverage gap,
so a quiet brief does not necessarily mean markets were quiet. Demo briefs use
fabricated data. The skill runs through your existing agent; no embedded agent
service is required.

## Investigate an analysis

For help defining an analysis, ask your agent to use the bundled
[analysis configuration skill](../skills/kairopsis-analysis/SKILL.md). It explains
parameter choices, data preparation and the questions each combination answers.

Open **Analyses**, find a name and select it. Use **All** to browse the full set;
**Flagged** draws attention to configured conditions worth investigating.
A quiet Flagged view can be empty even when analyses are available in All.

Read the chart alongside its current value, period change and historical
standing. Check the observation date before treating a value as current.
Unavailable values and data limitations are shown explicitly.

The Analysis settings panel follows **Inputs → Measure → Scale inputs →
Compare → Historical context**, matching Library. Choose Standalone or Pair,
then Level, Absolute change or Percentage change and its Frequency. Pair
comparison is Difference, Ratio or Regression residual. Display range and chart
view stay beside the chart, separately from estimation/reference histories.

Scale inputs offers None, Volatility, Beta to reference, VaR or Expected Shortfall
for every measure. **Estimate risk from** follows the input automatically, using
absolute changes for Level; choose explicit Absolute/Percentage changes to retain
that basis when changing Measure. Level stays a level when scaling is selected.
Shared settings are the default; **Customize per series** allows independent risk
bases and references. Inspect the formula, actual units, scales and sample dates.
For example, spread level / spread-change SD measures level per movement risk;
spread level / percentage-change SD has composite bp/% units.

Reference, fitting and estimation histories include 3 and 6 months, longer year
windows and **Longest available history**. Short windows still need sufficient
observations. Daily-endpoint weekly/monthly changes overlap; monthly-only series
remain subject to existing weekday/freshness and regression coverage limits.

Choose **Output scale → Z-score** for any completed calculation. The score shows
distance above/below its prior mean in sample standard deviations. Latest is
excluded; the current reference applies throughout the chart. Original units
retain any input scaling. Inspect the unstandardized magnitude alongside the
score. Z-score does not establish stationarity, reversal or investment return.
Insufficient/constant references produce an unavailable result.

**Monitoring** is separate and collapsed. Original output uses symmetric
percentile tails; Z-score uses its absolute threshold and dashed chart lines.
Formula changes clear optional move/materiality thresholds with an explanation,
retaining monitoring enable state and extreme-rule settings. Defaults require
calibration. Exploratory edits save only through **Edit defaults in Library →
Use exploratory settings → Save defaults**. Preview failures retain a labelled
previous chart and your edited values; Preview again before saving evidence.

When you ask the agent to set up monitoring across many Analyses, its starting
policy uses the lowest/highest 1% of historical results, a three-year reference
and at least 500 eligible earlier observations. If you choose Z-scores, the shared
starting threshold is an absolute score of 3. Your specified settings take
precedence, including custom move or material-change thresholds for individual
cases. The agent leaves those optional thresholds unset when applying the shared
policy without exceptions.

These are agent setup choices; existing Analyses and application defaults keep
their settings. The shared policy still needs historical testing across the
monitored universe. Too little eligible history remains a limitation; weekly or
monthly changes measured every day overlap. Ask the agent to explain exceptions
and data gaps when setting up monitoring.

New definitions use the v2 calculation contract. Existing saved definitions and
Snapshots retain v1; choosing a v2-only feature revises the draft explicitly.
Earlier evidence and its Latest calculations keep their captured definition.

Click a legend label to hide or show a series; double-click to isolate it.
The chart scales remain fixed while toggling, so the visual comparison stays
consistent. Hiding a series does not change the calculation.

**Source and chart details** explains the inputs, dates and settings when you
need them. A flag is a reason to investigate, not an investment recommendation.

## Save evidence to an Idea

Choose **Save to Idea** from the analysis. Create an Idea or select an existing
one, add the title or thought offered by the save form, and save the chart.

An Idea can contain several charts and notes. Add a chart note to explain what
the evidence shows; add an Idea note for the wider argument. Edit notes as your
view develops. Shortlist Ideas for upcoming discussion, and archive those you
want to set aside.

Saved evidence keeps the observations and settings used at capture time.
Catalogue edits and later market moves do not overwrite it.

## Preview and edit Library entries

Open **Library**, then add or edit a Data Series or Analysis. The editor sits
beside a chart. Choose **Preview** to fetch observations and inspect your
unsaved settings. Preview does not add entries to the catalogue or save evidence.

The optional **Economic rationale** field records what you are investigating,
why it matters and what might explain the result otherwise. Your agent can
propose this text when defining an Analysis. Edit it as the research question
changes; saving an Analysis does not require a rationale.

**Source and chart details** shows the rationale captured with the displayed
evaluation. Saved evidence and its **Latest data** calculations retain that
original reasoning after you revise Library defaults. Older evidence may show
**No economic rationale recorded**. **Use exploratory settings** preserves the
rationale currently in your Library draft.

The display range defaults to 3 years; choose months, longer year windows or
**Longest available history**. Reference history, fitting and risk-estimation
periods control the calculation independently. Switch chart views to inspect
underlying observations, measured inputs or regression scatter where applicable.

Editing a query, setting or display range marks the previous chart **Outdated**.
Choose **Preview** again to update it. If retrieval fails, check the reported
problem and retry; any retained chart still shows its previous settings under
**Source and chart details**. Demo mode previews only the labelled fixture data.

Within an Analysis, use **Add data series** or **Edit** beside an input to stage
a Series. **Preview series** inspects that Series; **Apply series** returns it
to the unsaved Analysis. New Series can also serve as risk references. Choose
the reference and adjustment method in the Analysis editor.

**Save analysis and … series** saves the Analysis and its used staged Series
together. The summary names the updates and other Analyses whose future
evaluations change. Unused drafts are discarded. **Cancel** discards the draft;
previewing or applying a Series does not save it. Saving defaults does not
require a successful preview. Open the saved Analysis to retain chart evidence
in an Idea.

## Revisit your view

Open the Idea through **Ideas**. Use **Saved evidence** to review the captured
observations and **Latest data** to recalculate using the chart's retained
definition. Review the new dates and any limitations before comparing views.

Refreshing data does not rewrite the original snapshot. Notes help record why
your interpretation changed. When a source fails, earlier results may remain
visible with a warning; they are not a successful fresh update.

The public data integration currently cannot verify source observation dates
or retrieval freshness. Live charts can be inspected, but unverified
observations do not generate monitoring findings.

## Copy and export

Idea charts offer **Copy data**, **Copy chart**, **Download chart** and
**Remove chart**.

- **Copy data:** paste values into a spreadsheet. Includes the displayed period
  and underlying inputs; hiding a legend entry does not remove its data columns.
- **Copy chart / Download chart:** use the selected chart view, visible series
  and scales. If clipboard access is denied, a file download provides a fallback.
- **Remove chart:** removes it from the current Idea view. Earlier retained
  evidence is preserved internally.

Exports capture another snapshot before completing. If saving fails, resolve
the reported problem and retry. The original saved image is also available
under Source and chart details.

## Keep your work safe

Your research is saved locally. Before changing computers or reinstalling,
ask the setup agent to back up the entire workspace and verify restoration.
For a data-source problem, provide the analysis name, displayed dates and error
message; the setup agent handles the connection and configuration.

For installation, recovery or data setup, use the [agent setup guide](agent-setup.md).
