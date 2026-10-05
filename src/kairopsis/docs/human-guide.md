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

## Investigate an analysis

Open **Analyses**, find a name and select it. Use **All** to browse the full set;
**Flagged** draws attention to configured conditions worth investigating.
A quiet Flagged view can be empty even when analyses are available in All.

Read the chart alongside its current value, period change and historical
standing. Check the observation date before treating a value as current.
Unavailable values and data limitations are shown explicitly.

Choose the display period and reference history independently. For a closer
comparison, change the measurement or use the **Risk adjustment** panel.
Reference and estimation periods include 3 and 6 months, longer year windows,
and **Longest available history**. The longest option uses common eligible
history for pairs. Short windows still require enough observations. These choices
are exploratory; editing an Analysis in Library saves its defaults.

Choose **Standardization → Z-score** for standalone changes, percentage changes,
pair differences or regression residuals. The score shows how many standard
deviations the result sits above or below its reference mean. Reference history
sets that mean and sample standard deviation; the latest observation is excluded.
The chart uses the same current reference throughout. **Z-score threshold (±)**
controls the extreme-value flag and dashed chart lines; the default is ±2.
A zero-variance or insufficient reference produces an unavailable score.

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
