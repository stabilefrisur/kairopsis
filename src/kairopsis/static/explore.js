/* Workspaces edit definitions. Charts, tables and capture use immutable server results. */
const explore = {
  workspace: null, selected: null, results: new Map(), status: "dirty", sequence: 0,
  saved: [], capture: null, conflict: null, highlighted: [], libraryQuery: "", checked: new Set(),
  selectionMode: null, previewTimer: null, previewInFlight: false, previewQueued: false, editingText: false, refreshQueued: false,
};
const exploreFamilies = {history: "History", scatter: "Scatter", ranking: "Ranked comparison", distribution: "Distribution", heatmap: "Heatmap", correlation: "Correlation"};
const exploreID = () => crypto.randomUUID().replaceAll("-", "");
const exploreButton = (text, action, extra = "") => `<button type="button" data-explore="${action}" ${extra}>${text}</button>`;
const exploreSelect = (label, name, value, choices) => `<label>${esc(label)}<select name="${name}" aria-label="${esc(label)}">${choices.map(([id, text]) => `<option value="${esc(id)}" ${String(id) === String(value) ? "selected" : ""}>${esc(text)}</option>`).join("")}</select></label>`;
const exploreInput = (label, name, value, type = "text") => `<label>${esc(label)}<input name="${name}" type="${type}" value="${esc(value || "")}"></label>`;
function exploreNewWorkspace() {
  return {schema_version: 1, id: exploreID(), version: null, name: "Untitled exploration", collection: [], views: [], as_of: document.body.dataset.explorationAsOf || null, question: "", notes: "", attributes: [], layout: "workbench"};
}
function exploreCurrentView() { return explore.workspace.views.find(view => view.id === explore.selected); }
function exploreVisibleViews() { return explore.workspace.views.filter(view => !explore.capture || explore.results.has(view.id)); }
function exploreFields(view) {
  return [...new Set(explore.workspace.collection.filter(item => view.measures.includes(item.id)).map(item => view.shape === "paired_date" ? item.id : item.field))];
}
function exploreItemLabel(item) { return item ? `${item.symbol} / ${item.field}` : "Removed collection item"; }
function exploreAxisLabel(axis) {
  const item = explore.workspace.collection.find(item => item.id === axis);
  return item ? exploreItemLabel(item) : axis;
}
function exploreResolvedAnalyses() { return Object.values(state.catalogue.resolved_analyses || {}); }
function exploreAnalysisContext() {
  const choices = new Map(state.catalogue.series.map(binding => [binding.id, binding]));
  for (const binding of Object.values(state.stagedSeries || {})) choices.set(binding.id, binding);
  const item = explore.workspace.collection.find(item => item.id === explore.analysisItem);
  for (const binding of [...(item?.analysis?.inputs || []), ...(item?.analysis?.references || [])]) choices.set(binding.id, binding);
  return {series: [...choices.values()], analyses: state.catalogue.analyses, memory: state.controlMemory,
    monitoring: false, thresholdNotice: "Monitoring is separate from exploration.", notice: text => notify(text)};
}
function exploreStatusText() {
  if (explore.capture) return "Saved chart evidence";
  const incomplete = explore.workspace.views.find(view => exploreDateProblem(view));
  if (incomplete) return `${incomplete.name}: ${exploreDateProblem(incomplete)}`;
  if (!explore.workspace.collection.length) return "Add data from Library, then add a chart.";
  if (!explore.workspace.views.length) return {dirty: "Loading data…", previewing: "Loading data…", current: "Data loaded · Add a chart.", failed: "Could not load data. Check the error below, then retry."}[explore.status];
  return {dirty: "Changes pending · charts update automatically", previewing: "Updating charts…", current: "Charts up to date", failed: "Could not update charts. Check the error below, then retry."}[explore.status];
}
function exploreUpdateStatus() {
  const status = document.querySelector("#explore-status");
  if (status) { status.textContent = exploreStatusText(); status.className = `explore-status ${explore.status}`; }
  document.querySelectorAll('[data-explore="capture"], [data-explore="capture-dialog"], [data-explore="export-png"], [data-explore="copy-png"]').forEach(button => button.disabled = explore.status !== "current" || button.dataset.explore !== "copy-png" && !explore.checked.size);
  document.querySelectorAll('[data-explore="preview"]').forEach(button => { button.disabled = explore.status === "previewing"; button.textContent = explore.status === "failed" ? "Retry update" : "Refresh data"; });
  document.querySelectorAll('.explore-result-state').forEach(node => {
    if (!explore.capture) node.textContent = explore.status === "current" ? "" : explore.workspace.views.some(view => exploreDateProblem(view)) ? "Previous chart · complete date settings" : explore.status === "failed" ? "Previous chart · update failed" : "Updating · previous chart shown";
  });
  const dateProblem = document.querySelector('.explore-date-problem');
  if (dateProblem) { dateProblem.textContent = exploreDateProblem(exploreCurrentView()); dateProblem.hidden = !dateProblem.textContent; }
}
function exploreSchedulePreview() {
  clearTimeout(explore.previewTimer);
  if (explore.capture || explore.editingText || !explore.workspace.collection.length) return;
  explore.previewTimer = setTimeout(() => explorePreview(), 150);
}
function exploreDirty(message, schedule = true) {
  explore.sequence++;
  explore.status = "dirty";
  explore.conflict = null;
  exploreUpdateStatus();
  if (message) notify(message);
  if (schedule) exploreSchedulePreview(); else clearTimeout(explore.previewTimer);
}
function exploreAddItem(kind, record, resolved, origin = "library") {
  const definition = kind === "series" ? record : resolved;
  if (!definition) throw Error("This Analysis could not be resolved. Open it in Library to inspect its inputs.");
  const duplicate = explore.workspace.collection.find(item => item.kind === kind && (item.binding || item.analysis).id === record.id && (item.binding || item.analysis).revision === record.revision);
  if (duplicate) { notify("This revision is already in the collection."); return; }
  explore.workspace.collection.push({id: exploreID(), kind, origin, symbol: kind === "series" ? record.research_symbol || record.instrument : record.name,
    field: kind === "series" ? record.research_field || record.field || record.name : record.name,
    ...(kind === "series" ? {binding: structuredClone(definition)} : {analysis: structuredClone(definition)})});
  exploreDirty(); exploreRender();
}
function exploreAddView(family = "history") {
  const collection = explore.workspace.collection;
  if (!collection.length) { notify("Add a Data Series or Analysis to the collection first."); return; }
  const measures = collection.map(item => item.id);
  const fields = [...new Set(collection.map(item => item.field))];
  const shape = family === "scatter" ? (fields.length > 1 ? "cross_section" : "paired_date") : family === "ranking" ? "cross_section" : "history";
  const axes = shape === "paired_date" ? measures.slice(0, 2) : fields.slice(0, family === "scatter" ? 2 : family === "distribution" ? 1 : undefined);
  const view = {id: exploreID(), name: exploreFamilies[family], family, measures, shape,
    sample: {start: null, end: null, members: null, excluded_row_ids: [], row_ids: [], date_policy: "exact", maximum_age_days: 0, interval_start: null, interval_measure: "level"},
    as_of: null, display_start: null, display_end: null, pinned: false, width: 1, highlight: [],
    size_by: null, color_by: "symbol", facet_by: null,
    options: {axes, x: axes[0], y: axes[1], distribution: "kde", group_by: "symbol", weight_policy: "equal_row", descriptive_fit: false, heatmap_layout: "time", correlation_orientation: "series", correlation_method: "pearson", correlation_sample: "common"}};
  explore.workspace.views.push(view); explore.selected = view.id; explore.checked.add(view.id);
  exploreDirty(); exploreRender();
}
function exploreCollectionHTML() {
  const items = explore.workspace.collection;
  const query = explore.libraryQuery.toLowerCase();
  const records = [...state.catalogue.series.map(record => ["series", record]), ...state.catalogue.analyses.map(record => ["analysis", record])]
    .filter(([, record]) => `${record.name} ${record.instrument || ""} ${record.field || ""}`.toLowerCase().includes(query));
  return `<aside class="explore-collection" aria-label="Data and calculations"><h2>Data & calculations</h2>
    <p class="meta">Choose which series to show in each chart.</p>
    <div class="explore-collection-list">${items.map(item => {
      const definition = item.binding || item.analysis;
      const current = state.catalogue[item.kind === "series" ? "series" : "analyses"].find(record => record.id === definition.id);
      const revision = explore.capture ? `Saved definition, version ${definition.revision}.` : current && current.revision !== definition.revision ? `Using version ${definition.revision}; Library has version ${current.revision}. ${exploreButton("Use Library update", "adopt", `data-id="${item.id}"`)}` : !current ? item.origin === "local" ? "Saved with this workspace. Not in Library." : "Saved definition. This entry is no longer in Library." : `Using Library definition version ${definition.revision}. Future Library edits are adopted explicitly.`;
      return `<div class="explore-binding" data-item="${item.id}"><strong>${esc(definition.name)}</strong>
        <small>${item.kind === "series" ? `${esc(definition.instrument)}${definition.field ? " / " + esc(definition.field) : ""} · ${esc(definition.unit)}` : esc(exploreCalculationSummary(definition))}</small>
        ${item.origin === "local" ? '<small>Workspace calculation</small>' : ""}
        ${current && current.revision !== definition.revision && !explore.capture ? '<small class="explore-revisions">Library update available — see details</small>' : ""}
        <details class="explore-source" data-details="source-${item.id}"><summary>${item.kind === "series" ? "Source details" : "Calculation details"}</summary>
          <p class="meta">${item.kind === "series" ? `${esc(definition.source)}<br>${esc(definition.basis?.label || "")}` : esc(definition.inputs.map(input => input.name).join("; "))}</p><p class="meta">${revision}</p>
          <p class="meta">Chart grouping: ${esc(item.symbol)} / ${esc(item.field)}</p>
          ${explore.capture ? "" : exploreButton("Change chart grouping…", "mapping", `data-id="${item.id}"`)}</details>
        ${explore.capture ? "" : `<div class="actions">${item.kind === "analysis" ? exploreButton("Edit calculation", "edit-analysis", `data-id="${item.id}"`) : ""}${exploreButton("Remove", "remove-item", `data-id="${item.id}" class="quiet"`)}</div>`}</div>`;
    }).join("") || '<p class="empty">Select Library entries below to begin.</p>'}</div>
    ${explore.capture ? "" : `<details open><summary>Add from Library</summary><input id="explore-library-search" class="search" placeholder="Find series or Analysis" aria-label="Find Library entries" value="${esc(explore.libraryQuery)}"><div id="explore-library-choices">${records.map(([kind, record]) => `<div class="explore-library-row">${exploreButton(esc(record.name) + `<small>${kind === "series" ? `${esc(record.instrument)}${record.field ? " / " + esc(record.field) : ""} · ${esc(record.unit)}` : "Analysis output"}</small>`, "add-item", `data-kind="${kind}" data-id="${record.id}"`)}</div>`).join("")}</div></details>
      <div class="explore-data-actions">${exploreButton("Add calculation…", "new-analysis")}${exploreButton("Connect new data…", "new-series")}</div>
      <details data-details="collection-tools"><summary>Grouping & classifications</summary><p class="meta">Supply sourced labels for colour and grouping.</p>${exploreButton("Edit classifications…", "attributes")}</details><a href="/library">Open Library</a>`}</aside>`;
}
function exploreCalculationSummary(definition) {
  const settings = definition.settings, frequency = {day: "Daily", week: "Weekly", month: "Monthly"}[settings.horizon] || settings.horizon;
  const measure = settings.measure === "level" ? "Level" : `${frequency} ${settings.measure === "return" ? "% change" : "change"}`;
  const risk = settings.risk_adjustment?.method;
  const comparison = {ratio: "Ratio", difference: "Difference", regression: "Regression residual"}[definition.calculation];
  const scaling = settings.risk_overrides?.length ? "Custom input scaling" : risk && risk !== "none" ? `${{volatility: "Volatility", beta: "Beta", var: "VaR", es: "ES"}[risk] || risk} scaled` : "";
  return `${definition.inputs.map(input => input.name).join(", ")} · ${measure}${scaling ? ` · ${scaling}` : ""}${comparison ? ` · ${comparison}` : ""}${settings.standardization === "zscore" ? " · Z-score" : ""}`;
}
function exploreDateEnd(view, fallback = explore.workspace.as_of) {
  return view.sample.end || view.as_of || fallback || explore.results.get(view.id)?.as_of || null;
}
function exploreDateProblem(view) {
  if (!view) return "";
  const end = exploreDateEnd(view), cutoff = view.as_of || explore.workspace.as_of;
  if (view.pinned && !view.as_of) return "Choose a date for this chart.";
  if (view.sample.end && cutoff && view.sample.end > cutoff) return "End date exceeds the data cutoff. Choose the chart date again.";
  if (view.sample.start && end && view.sample.start > end) return "Start date must be on or before the end date.";
  if (view.sample.interval_measure !== "level") {
    if (!view.sample.interval_start) return "Choose a From date to calculate the change.";
    if (end && view.sample.interval_start > end) return "From date must be on or before the comparison date.";
  }
  return "";
}
function exploreDateControls(view) {
  const single = view.shape === "cross_section", interval = view.sample.interval_measure !== "level";
  const custom = !!(view.as_of || view.sample.end || view.pinned), end = exploreDateEnd(view);
  const workspaceDate = explore.workspace.as_of || explore.results.get(view.id)?.as_of;
  const canCompare = single || view.family === "ranking" || interval;
  return `<fieldset class="explore-dates"><legend>${single ? "Comparison" : "History period"}</legend>
    ${canCompare ? exploreSelect("Values", "interval_measure", view.sample.interval_measure, [["level", single ? "Level on a date" : "Level"], ["change", "Change between dates"], ["return", "Percentage change"]]) : ""}
    ${!single ? exploreInput("Start date (optional)", "start", view.sample.start, "date") : ""}
    ${interval ? exploreInput("From", "interval_start", view.sample.interval_start, "date").replace('<input ', '<input required ') : ""}
    ${exploreSelect(single ? interval ? "To" : "Date" : "End date", "date_source", custom ? "chart" : "workspace", [["workspace", "Follow workspace date"], ["chart", "Set chart date"]])}
    ${custom ? exploreInput(single ? interval ? "To date" : "Comparison date" : "End date for this chart", "chart_date", end, "date").replace('<input ', '<input required ') : ""}
    <p class="meta">${custom ? "This chart keeps its own date when the workspace date changes." : `Uses ${workspaceDate ? esc(dateText(workspaceDate)) : "today"}; follows changes to the workspace date.`}${!single ? " Leave start blank to use all loaded history." : ""}${interval ? " Changes compare the two endpoints." : ""}</p>
    <p class="warning explore-date-problem" role="status" ${exploreDateProblem(view) ? "" : "hidden"}>${esc(exploreDateProblem(view))}</p>
    <details data-details="date-matching"><summary>Missing dates</summary>${exploreSelect("When a date is missing", "date_policy", view.sample.date_policy, [["exact", "Leave missing"], ["backward", "Use an earlier observation"]])}
      ${view.sample.date_policy === "backward" ? exploreInput("Look back at most (calendar days)", "maximum_age_days", view.sample.maximum_age_days, "number") : ""}
      <p class="meta">${view.sample.date_policy === "backward" ? "Uses an earlier available date only within this limit. Actual dates remain in the observations table." : "Requires an observation on the requested date. Weekends and gaps stay missing."}</p>
    </details></fieldset>`;
}
function exploreReadDates(view, data, changedControl) {
  if (changedControl === "date_source" || changedControl === "chart_date") {
    const end = exploreDateEnd(view);
    view.pinned = data.get("date_source") === "chart";
    view.as_of = view.pinned ? (changedControl === "date_source" ? end || new Date().toISOString().slice(0, 10) : data.get("chart_date") || null) : null;
    view.sample.end = null;
  }
  if (data.has("start")) view.sample.start = data.get("start") || null;
  if (data.has("interval_measure")) view.sample.interval_measure = data.get("interval_measure");
  if (data.has("interval_start")) view.sample.interval_start = data.get("interval_start") || null;
  if (view.sample.interval_measure === "level") view.sample.interval_start = null;
  if (data.has("date_policy")) view.sample.date_policy = data.get("date_policy");
  if (data.has("maximum_age_days")) view.sample.maximum_age_days = Number(data.get("maximum_age_days") || 0);
  else if (changedControl === "date_policy" && view.sample.date_policy === "backward" && !view.sample.maximum_age_days) view.sample.maximum_age_days = 7;
}
function exploreDateSummary(view, asOf) {
  const end = exploreDateEnd(view, asOf);
  if (view.sample.interval_measure !== "level") return `${view.sample.interval_measure === "return" ? "Percentage change" : "Change"} from ${dateText(view.sample.interval_start)} to ${dateText(end)}`;
  if (view.shape === "cross_section") return `Level on ${dateText(end)}`;
  return `${view.sample.start ? "History from " + dateText(view.sample.start) : "History"} through ${dateText(end)}`;
}
function exploreEditorHTML() {
  const view = exploreCurrentView();
  if (!view) return '<aside class="explore-editor"><h2>Chart settings</h2><p class="meta">Add a chart to choose its series and date range.</p></aside>';
  const choices = exploreFields(view).map(axis => [axis, exploreAxisLabel(axis)]), fields = [...new Set(explore.workspace.collection.map(item => item.field))];
  const members = [...new Set(explore.workspace.collection.map(item => item.symbol))];
  const attributes = [...new Set(explore.workspace.attributes.map(attribute => attribute.name || attribute.field).filter(Boolean))];
  return `<aside class="explore-editor" aria-label="Selected chart settings"><h2>${esc(exploreFamilies[view.family])} settings</h2><p class="meta">${explore.capture ? "Saved settings. Make a copy to edit." : "Changes update this chart automatically."}</p><form id="explore-view-form"><fieldset ${explore.capture ? "disabled" : ""}>
    ${exploreInput("Chart title", "name", view.name)}${exploreSelect("Chart type", "family", view.family, Object.entries(exploreFamilies))}
    ${exploreSelect("Show", "shape", view.shape, [["history", "Each series over time"], ["cross_section", "Symbols on one date"], ["paired_date", "Two series on matching dates"], ["panel", "Symbols across multiple dates (panel)"]])}
    <fieldset><legend>Series in this chart</legend><div class="measure-list">${explore.workspace.collection.map(item => `<label><input name="measures" type="checkbox" value="${item.id}" ${view.measures.includes(item.id) ? "checked" : ""}>${esc(exploreItemLabel(item))}</label>`).join("")}</div>${view.shape === "paired_date" ? '<p class="meta">Choose the two series below as X and Y. Each dot represents one matching date.</p>' : ""}</fieldset>
    ${view.family === "scatter" ? `<div class="fields">${exploreSelect("X axis", "x", view.options.x || choices[0]?.[0], choices)}${exploreSelect("Y axis", "y", view.options.y || choices[1]?.[0], choices)}</div>` : ["correlation", "heatmap"].includes(view.family) ? '<p class="meta">Selected measures supply the fields.</p>' : exploreSelect("Field", "axis", view.options.axes?.length > 1 ? "all" : view.options.axes?.[0] || choices[0]?.[0], view.family === "history" ? [["all", "All selected fields"], ...choices] : choices)}
    ${view.family === "history" ? exploreSelect("History layout", "history_layout", view.options.history_layout || "overlay", [["overlay", "Overlay (comparable units)"], ["small_multiples", "Aligned small multiples"]]) : ""}
    ${view.family === "scatter" ? `<label><input name="descriptive_fit" type="checkbox" ${view.options.descriptive_fit ? "checked" : ""}> Descriptive linear fit</label>${view.shape === "panel" ? `<label><input name="allow_pooled_fit" type="checkbox" ${view.options.allow_pooled_fit ? "checked" : ""}> Explicitly pool panel rows for the fit</label>` : ""}<p class="meta">Fit uses this view’s retained observations. It is separate from an Analysis residual.</p>` : ""}
    ${view.family === "distribution" ? `${exploreSelect("Distribution", "distribution", view.options.distribution, [["kde", "KDE"], ["histogram", "Histogram"], ["box", "Box"]])}${exploreInput("Bandwidth multiplier", "bandwidth_multiplier", view.options.bandwidth_multiplier || 1, "number")}<label><input name="shared_bandwidth" type="checkbox" ${view.options.shared_bandwidth ? "checked" : ""}> Shared bandwidth (comparable units)</label>${exploreSelect("Group by", "group_by", view.options.group_by || "symbol", [["symbol", "Symbol"], ...attributes.map(name => [name, name])])}${exploreSelect("Pooling weights", "weight_policy", view.options.weight_policy || "equal_row", [["equal_row", "Equal rows"], ["equal_member", "Equal symbols"]])}` : ""}
    ${view.family === "heatmap" ? exploreSelect("Layout", "heatmap_layout", view.options.heatmap_layout, [["time", "Symbols × dates"], ["fields", "Symbols × fields"]]) : ""}
    ${view.family === "correlation" ? `${exploreSelect("Compare", "correlation_orientation", view.options.correlation_orientation, [["series", "Series across dates"], ["fields", "Fields across symbols"]])}<div class="fields">${exploreSelect("Coefficient", "correlation_method", view.options.correlation_method, [["pearson", "Pearson"], ["spearman", "Spearman"]])}${exploreSelect("Sample", "correlation_sample", view.options.correlation_sample, [["common", "Common complete"], ["pairwise", "Pairwise"]])}</div>` : ""}
    ${view.family === "scatter" ? `${exploreSelect("Size by", "size_by", view.size_by || "", [["", "None"], ...explore.workspace.collection.map(item => [item.id, exploreItemLabel(item)])])}${exploreSelect("Colour by", "color_by", view.color_by || "", [["", "None"], ["symbol", "Symbol"], ...(view.shape === "paired_date" ? explore.workspace.collection.map(item => [item.id, exploreItemLabel(item)]) : fields.map(field => [field, field])), ...attributes.map(name => [name, name])])}${exploreSelect("Facet by", "facet_by", view.facet_by || "", [["", "None"], ...attributes.map(name => [name, name])])}` : ""}
    ${exploreDateControls(view)}
    <details data-details="sample-filters"><summary>Filter observations</summary>
      ${view.shape === "cross_section" && view.sample.start ? `${exploreInput("Existing filter: exclude dates before", "start", view.sample.start, "date")}<p class="meta">Clear to remove this earlier history filter. It is separate from the change's From date.</p>` : ""}
      ${members.map(member => `<label><input name="members" type="checkbox" value="${esc(member)}" ${view.sample.members == null || view.sample.members.includes(member) ? "checked" : ""}> ${esc(member)}</label>`).join("")}
      ${view.sample.row_ids.length ? `<p class="meta">Restricted to ${view.sample.row_ids.length} drilldown rows.</p>${exploreButton("Release drilldown sample", "release-sample")}` : ""}
      ${view.sample.excluded_row_ids.length ? `<p class="meta">${view.sample.excluded_row_ids.length} observations excluded.</p>${exploreButton("Restore excluded rows", "restore-rows")}` : ""}
    </details>
    ${view.family === "history" || view.family === "heatmap" && view.options.heatmap_layout !== "fields" || view.family === "scatter" && view.shape !== "cross_section" ? `<details><summary>Zoom chart</summary><p class="meta">Display only; calculations keep the full history period above.</p><div class="fields">${exploreInput("Show from", "display_start", view.display_start, "date")}${exploreInput("Show through", "display_end", view.display_end, "date")}</div></details>` : ""}
    <div class="actions">${exploreButton("Duplicate chart", "duplicate")}${exploreButton("Move earlier", "earlier")}${exploreButton(view.width === 2 ? "Half width" : "Full width", "width")}${exploreButton("Remove chart", "remove-view", 'class="quiet"')}</div></fieldset></form></aside>`;
}
function exploreRowsHTML(result) {
  const axes = [...new Set(result.rows.flatMap(row => Object.keys(row.values || {})))];
  return `<details><summary>Observations · ${result.rows.length} retained / ${(result.excluded || []).length} excluded</summary>${result.rows.length > 500 ? '<p class="meta">Table displays first 500 rows. Charts, statistics and evidence retain the full sample.</p>' : ""}<div class="table-region" tabindex="0"><table><thead><tr><th>Symbol</th><th>Date</th>${axes.map(axis => `<th>${esc(exploreAxisLabel(axis))}</th>`).join("")}<th>Field dates / provenance</th>${explore.capture ? "" : "<th>Sample</th>"}</tr></thead><tbody>${result.rows.slice(0, 500).map(row => `<tr><td>${esc(row.symbol)}</td><td>${esc(row.date || "Not dated")}</td>${axes.map(axis => `<td>${number(row.values[axis])}</td>`).join("")}<td>${esc(JSON.stringify(row.dates || {}))}<small>${esc(JSON.stringify(row.observed_on || {}))}</small></td>${explore.capture ? "" : `<td>${exploreButton("Exclude", "exclude-row", `data-view="${result.view_id}" data-row="${esc(row.id)}"`)}</td>`}</tr>`).join("")}</tbody></table></div>
    ${(result.excluded || []).length ? `<p class="meta">Excluded: ${esc(JSON.stringify(result.excluded))}</p>` : ""}</details>`;
}
function exploreViewHTML(view) {
  const result = explore.results.get(view.id), retainedView = result?.view || view;
  return `<section class="explore-view ${view.id === explore.selected ? "selected" : ""} ${view.width === 2 ? "wide" : ""}" data-view="${view.id}">
    <div class="explore-view-title"><h2>${exploreButton(esc(view.name), "select", `data-id="${view.id}" class="quiet" title="Edit this chart"`)}</h2><div class="actions">${explore.selectionMode ? `<label class="explore-select-chart"><input type="checkbox" data-capture-view="${view.id}" aria-label="Select ${esc(view.name)}" ${explore.checked.has(view.id) ? "checked" : ""}> Select</label>` : ""}${exploreButton("Copy PNG", "copy-png", `data-id="${view.id}" ${explore.status !== "current" ? "disabled" : ""}`)}${exploreButton(explore.workspace.layout === "focus" ? "Back to overview" : "Enlarge", explore.workspace.layout === "focus" ? "layout" : "focus-view", `data-id="${view.id}"`)}</div></div>
    <p class="meta explore-result-state">${result ? explore.capture ? `Saved evidence · <a href="/api/explore/captures/${explore.capture.idea_id}/${explore.capture.id}/images/${result.id}" download>Original PNG</a>` : explore.status === "current" ? "" : "Updating · previous chart shown" : "Waiting for data…"}</p>
    ${result ? `<p class="meta explore-date-summary">${esc(exploreDateSummary(retainedView, result.as_of))}</p>` : ""}
    <div id="explore-plot-${view.id}" class="plot" role="img" aria-label="${esc(view.name)}"><p class="empty">${result ? "Drawing chart…" : "Updating chart…"}</p></div>
    ${result ? `<p class="meta">${esc(result.sample_meaning || {history: "One observation per series and date", cross_section: "One observation per symbol at the chosen date", paired_date: "Two series, one observation per matched date", panel: "One observation per symbol and date"}[retainedView.shape])} · ${result.rows.length} retained rows</p><details data-details="measure-details-${view.id}"><summary>Series and units</summary><p class="meta">${Object.entries(result.measures || {}).filter(([id]) => retainedView.measures.includes(id)).map(([, measure]) => `${esc(measure.symbol)} / ${esc(measure.field)}: ${esc(measure.unit)}${measure.meaning ? " · " + esc(measure.meaning) : ""}`).join("</p><p class=meta>")}</p></details>
      ${result.statistics?.size_legend ? `<div class="explore-size-legend" aria-label="Marker area legend"><strong>${esc(exploreAxisLabel(result.statistics.size_legend.field))}</strong>${result.statistics.size_legend.values.map((value, index) => `<span><i style="width:${result.statistics.size_legend.sizes[index]}px;height:${result.statistics.size_legend.sizes[index]}px"></i>${number(value, result.statistics.size_legend.unit)}</span>`).join("")}</div><p class="meta">Marker area represents the selected field. Missing or negative values use a constant marker and are reported.</p>` : ""}
      ${result.statistics?.fit ? `<p class="meta">Descriptive fit: ${esc(result.statistics.fit.unavailable_reason || result.statistics.fit.equation || "Unavailable")} · ${result.statistics.fit.count} fit rows / ${result.statistics.fit.evaluation_row_ids?.length || 0} evaluation rows. Display cropping does not change the fit.</p>` : ""}
      ${[...(result.limitations || []), ...(result.statistics?.limitations || [])].length ? `<p class="warning">${esc([...new Set([...(result.limitations || []), ...(result.statistics?.limitations || [])])].join(" "))}</p>` : ""}${exploreRowsHTML(result)}
      <details><summary>Calculation and statistical evidence</summary><pre>${esc(JSON.stringify({view: result.view, axes: result.axes, measures: result.measures, algorithm: result.statistics?.algorithm, fit: result.statistics?.fit ? {...result.statistics.fit, residuals: `${result.statistics.fit.residuals?.length || 0} retained residual rows`, row_ids: `${result.statistics.fit.row_ids?.length || 0} retained fit rows`, evaluation_row_ids: `${result.statistics.fit.evaluation_row_ids?.length || 0} evaluation rows`} : null}, null, 2))}</pre><p class="meta">Complete observations, estimates and calculation inputs are retained in the capture’s JSON and CSV export.</p></details>` : ""}
  </section>`;
}
function exploreRender() {
  const workspace = explore.workspace, visibleViews = exploreVisibleViews();
  const focused = document.activeElement, formID = focused?.form?.id;
  const focusSelector = focused?.id ? `#${CSS.escape(focused.id)}` : formID && focused?.name ? `#${formID} [name="${CSS.escape(focused.name)}"]${focused.type === "checkbox" ? `[value="${CSS.escape(focused.value)}"]` : ""}` : null;
  const opened = new Set([...main.querySelectorAll("details[open]")].map(details => details.dataset.details || details.querySelector("summary")?.textContent));
  const editorScroll = main.querySelector(".explore-editor")?.scrollTop || 0;
  main.innerHTML = `<div class="explore-top"><div><h1>${explore.capture ? "Saved exploration" : "Explore"}</h1><p id="explore-status" class="explore-status ${explore.status}" role="status" aria-live="polite">${exploreStatusText()}</p></div><div class="actions">${explore.capture ? exploreButton("Make an editable copy", "fork", 'class="primary"') : `${exploreButton("Refresh data", "preview", `${explore.status === "previewing" ? "disabled" : ""}`)}${exploreButton("Save workspace", "save", 'class="primary"')}${exploreButton("New workspace", "new")}`}</div></div>
    ${explore.conflict ? `<div class="explore-conflict" role="alert">${esc(explore.conflict)} Your draft is retained. ${exploreButton("Save as new workspace", "save-copy")}${exploreButton("Open saved version", "open-saved", `data-id="${workspace.id}"`)}</div>` : ""}
    ${explore.libraryChanges?.length && !explore.capture ? `<p class="explore-revisions">Library changes available: ${explore.libraryChanges.map(change => `${esc(exploreItemLabel(workspace.collection.find(item => item.id === change.collection_id)))} (saved version ${change.retained_revision}; ${change.current_revision == null ? "no longer in Library" : `Library version ${change.current_revision}`})`).join("; ")}. Review each series’ details to update its saved definition.</p>` : ""}
    <div class="explore-context" aria-label="Workspace">${exploreInput("Workspace name", "workspace_name", workspace.name)}${exploreInput("Workspace date", "workspace_as_of", workspace.as_of, "date")}${explore.capture ? "" : `${exploreSelect("Saved workspaces", "saved_workspace", "", [["", "Choose workspace"], ...explore.saved.map(record => [record.id || record.workspace?.id, record.name || record.workspace?.name])])}${exploreButton("Open", "open")}`}</div>
    ${explore.capture ? `<p class="meta">Saved ${esc(explore.capture.captured_at || explore.capture.created_at || "")} · <a href="${explore.capture.export_url || `/api/explore/captures/${explore.capture.idea_id}/${explore.capture.id}/export`}">Download evidence ZIP</a></p>` : ""}
    <div class="explore-layout ${workspace.layout}">${exploreCollectionHTML()}<div class="explore-canvas">${exploreChartToolbar()}
      ${workspace.layout === "focus" ? `<div class="explore-filmstrip" aria-label="Charts">${visibleViews.map(view => exploreButton(esc(view.name), "select", `data-id="${view.id}" aria-pressed="${view.id === explore.selected}"`)).join("")}</div>` : ""}<div class="explore-grid">${visibleViews.map(exploreViewHTML).join("") || '<section class="explore-view wide"><h2>Explore a relationship</h2><p class="empty">Add series from Library on the left, then choose a chart above.</p></section>'}</div></div>${exploreEditorHTML()}</div>
    <details class="explore-research" ${workspace.question || workspace.notes ? "open" : ""}><summary>Working question and notes</summary><div class="fields"><label>Working question<textarea id="explore-question" maxlength="10000" ${explore.capture ? "readonly" : ""}>${esc(workspace.question)}</textarea></label><label>Notes<textarea id="explore-notes" ${explore.capture ? "readonly" : ""}>${esc(workspace.notes)}</textarea></label></div></details>`;
  if (explore.capture) document.querySelectorAll('.explore-context input').forEach(input => input.disabled = true);
  main.querySelectorAll("details").forEach(details => { if (opened.has(details.dataset.details || details.querySelector("summary")?.textContent)) details.open = true; });
  if (focusSelector) main.querySelector(focusSelector)?.focus({preventScroll: true});
  if (main.querySelector(".explore-editor")) main.querySelector(".explore-editor").scrollTop = editorScroll;
  exploreUpdateStatus();
  exploreRenderPlots();
}
function exploreChartToolbar() {
  const mode = explore.selectionMode;
  return `<div class="explore-chart-toolbar" aria-label="Chart actions"><h2>${explore.workspace.layout === "focus" ? "Chart" : "Charts"}</h2>
    ${explore.capture ? "" : `<div class="explore-add-chart">${exploreSelect("Chart type to add", "new_family", "history", Object.entries(exploreFamilies))}${exploreButton("Add chart", "add-view", explore.workspace.collection.length ? "" : "disabled")}</div>`}
    <div class="actions">${!explore.capture && explore.workspace.views.length ? exploreButton("Save to Idea…", "select-save") : ""}${explore.workspace.views.length ? exploreButton("Export charts…", "select-export") : ""}</div>
    ${explore.highlighted.length ? exploreButton("Clear highlight", "clear-highlight", 'class="quiet"') : ""}</div>
    ${mode ? `<div class="explore-selection-bar" aria-label="Choose charts"><strong>${mode === "save" ? "Choose charts to save to an Idea" : "Choose charts to export"}</strong><span id="explore-selection-count">${explore.checked.size} selected</span><div class="actions">${exploreButton("Select all", "check-all")}${exploreButton("Clear selection", "uncheck-all")}${exploreButton(mode === "save" ? "Continue…" : "Download PNGs", mode === "save" ? "capture-dialog" : "export-png", 'class="primary"')}${exploreButton("Cancel", "cancel-selection")}</div></div>` : ""}`;
}
function exploreCaptureDialog() {
  if (explore.status !== "current" || !explore.checked.size) throw Error("Wait for the charts to update, then select charts to save.");
  exploreDialog(`<h2>Save charts to an Idea</h2><p>Save ${explore.checked.size} selected ${explore.checked.size === 1 ? "chart" : "charts"} with their data and settings. This evidence stays fixed as you continue exploring.</p>
    <label>Title<input id="explore-capture-title" value="${esc(explore.workspace.name)}"></label>
    <label>Idea<select id="explore-capture-idea"><option value="">Create a new Idea</option>${(state.exploreIdeas || []).map(record => `<option value="${record.idea?.id || record.id}">${esc(record.idea?.title || record.title)}</option>`).join("")}</select></label>
    <label>How does this evidence relate to the Idea?<select id="explore-capture-role" aria-label="How does this evidence relate to the Idea?"><option value="contextual">Background context</option><option value="supporting">Supports the argument</option><option value="challenging">Challenges the argument</option></select></label>
    <p class="meta">This label organises the evidence. It does not affect calculations.</p><div class="actions">${exploreButton("Save evidence", "capture", 'class="primary"')}${exploreButton("Cancel", "close-dialog")}</div>`);
}
async function exploreRenderPlots() {
  const generation = explore.renderGeneration = (explore.renderGeneration || 0) + 1;
  for (const view of explore.workspace.views) {
    const result = explore.results.get(view.id), plot = document.querySelector(`#explore-plot-${view.id}`);
    if (!result || !plot || explore.workspace.layout === "focus" && view.id !== explore.selected) continue;
    const statistics = result.statistics || {}, chart = exploreChartData(result.view || view, result), traces = chart.traces;
    if (!traces.length || !result.rows.length) { const retained = result.view || view; plot.innerHTML = `<p class="empty">${retained.shape === "cross_section" ? `No matching observations for ${esc(dateText(exploreDateEnd(retained, result.as_of)))}. Check the comparison date, Missing dates or filters.` : "No available values for this period. Check the history dates and filters."}</p>`; continue; }
    plot.innerHTML = "";
    plot.style.height = "";
    const baseHeight = plot.clientHeight, plotHeight = baseHeight - chart.layout.margin.t - chart.layout.margin.b;
    await Plotly.newPlot(plot, traces, chart.layout, {responsive: true, displaylogo: false, modeBarButtonsToRemove: ["sendDataToCloud"]});
    if (generation !== explore.renderGeneration || !plot.isConnected) return;
    // Let legend rows grow the card instead of consuming the plotting area.
    const missingHeight = plotHeight - plot._fullLayout._size.h;
    if (missingHeight > 1 && plot.querySelector(".legend")) {
      const height = baseHeight + Math.ceil(missingHeight * (1 - chart.layout.legend.y));
      plot.style.height = `${height}px`;
      await Plotly.relayout(plot, {height, autosize: true});
      if (generation !== explore.renderGeneration || !plot.isConnected) return;
    }
    plot.on("plotly_click", event => explorePlotClick(result.view || view, result, event));
  }
}
function exploreLegendLabel(text) {
  const context = document.createElement("canvas").getContext("2d");
  context.font = "11px Segoe UI, Calibri, sans-serif";
  const lines = []; let line = "";
  // Bound individual labels as well as wrapping entries onto further rows.
  // Splitting long identifiers also keeps legends inside narrow chart cards.
  for (const word of String(text).split(/\s+/)) {
    if (line && context.measureText(`${line} ${word}`).width > 200) { lines.push(line); line = ""; }
    if (line) line += " ";
    for (const character of word) {
      if (context.measureText(line + character).width > 200) { lines.push(line); line = ""; }
      line += character;
    }
  }
  if (line) lines.push(line);
  return lines.map(esc).join("<br>");
}
function exploreChartData(view, result) {
  const statistics = result.statistics || {}, traces = structuredClone(statistics.traces || []);
  const layout = {font: {family: "Segoe UI, Calibri, sans-serif", color: "#203047", size: 12}, paper_bgcolor: "white", plot_bgcolor: "white", margin: {l: 65, r: 25, t: 25, b: 60}, ...structuredClone(statistics.layout || {}), autosize: true};
  if (!result.rows.length || !traces.length) return {traces: [], layout: {...layout, annotations: [{text: "No available values for the retained sample", x: .5, y: .5, xref: "paper", yref: "paper", showarrow: false}], xaxis: {visible: false}, yaxis: {visible: false}}};
  const labelText = text => Object.entries(result.measures).reduce((label, [id, measure]) => label.replaceAll(id, `${measure.symbol} / ${measure.field}`), String(text));
  // Keep server units, including interval percentage changes and raw endpoint axes.
  for (const key of Object.keys(layout)) if (/^[xy]axis\d*$/.test(key) && layout[key].title) {
    if (typeof layout[key].title === "string") layout[key].title = labelText(layout[key].title);
    else if (layout[key].title.text) layout[key].title.text = labelText(layout[key].title.text);
  }
  traces.forEach(trace => { if (trace.name) trace.name = labelText(trace.name); });
  layout.legend = {...layout.legend,
    orientation: "h", x: 0, xanchor: "left", y: -.25, yanchor: "top", font: {size: 11}, groupclick: "togglegroup"};
  if (view.family === "distribution") {
    // Retained group metadata also identifies auxiliary traces in older captures.
    const groups = (statistics.groups || []).map(group => {
      const unit = result.axis_units?.[group.axis], axis = `${group.axis}${unit ? ` (${unit})` : ""}`;
      return labelText(group.group === "All" ? axis : `${axis} · ${group.group}`);
    });
    const colors = layout.colorway || ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"];
    for (const trace of traces) {
      const group = groups.filter(name => trace.name === name || trace.name?.startsWith(`${name} `)).sort((left, right) => right.length - left.length)[0];
      if (!group) continue;
      const color = colors[groups.indexOf(group) % colors.length];
      trace.legendgroup = group; trace.showlegend = trace.name === group;
      trace.marker = {...trace.marker, color};
      if (trace.mode?.includes("lines")) trace.line = {...trace.line, color};
    }
  }
  if (view.family === "history") for (const key of Object.keys(layout)) if (/^xaxis\d*$/.test(key)) layout[key].title = null;
  if (["history", "heatmap"].includes(view.family) && view.options.heatmap_layout !== "fields") layout.xaxis = {...layout.xaxis, title: null};
  if ((view.display_start || view.display_end) && (view.family === "history" || view.family === "heatmap" && view.options.heatmap_layout !== "fields")) layout.xaxis = {...layout.xaxis, range: [view.display_start || undefined, view.display_end || undefined]};
  const highlighted = view.highlight?.length ? view.highlight : explore.highlighted;
  traces.forEach(trace => {
    if ((view.display_start || view.display_end) && view.family === "scatter" && trace.mode?.includes("markers")) {
      const display = new Set(result.display_row_ids), indices = (trace.customdata || []).map((datum, index) => display.has(datum?.[0]) ? index : -1).filter(index => index >= 0);
      for (const field of ["x", "y", "customdata", "text"]) if (Array.isArray(trace[field])) trace[field] = indices.map(index => trace[field][index]);
      for (const field of ["size", "color"]) if (Array.isArray(trace.marker?.[field])) trace.marker[field] = indices.map(index => trace.marker[field][index]);
    }
    if (trace.type === "scatter" && trace.mode?.includes("markers")) {
      trace.marker ||= {}; if (!view.size_by) trace.marker.size = view.family === "history" ? 4 : 8;
      trace.marker.line = {color: "#203047", width: (trace.x || []).map((_, index) => {
        const datum = trace.customdata?.[index]; return highlighted.some(item => item === datum?.id || item === datum?.row_id || item === datum?.[0] || item === datum?.[1] || item === datum || item === trace.name) ? 3 : 0;
      })};
      trace.hovertemplate ||= "%{customdata[1]}<br>%{customdata[2]}<br>%{x}<br>%{y}<extra>%{fullData.name}</extra>";
    }
  });
  for (const key of Object.keys(layout)) if (/^[xy]axis\d*$/.test(key)) {
    const title = layout[key].title;
    layout[key].title = typeof title === "string" ? {text: title} : title || {text: ""};
  }
  for (const trace of traces) for (const colorbar of [trace.colorbar, trace.marker?.colorbar]) if (colorbar) {
    const title = colorbar.title;
    colorbar.title = typeof title === "string" ? {text: labelText(title)} : title || {text: ""};
  }
  // Format only presentation copies; retained series labels and evidence stay exact.
  traces.forEach(trace => { if (trace.name) trace.name = exploreLegendLabel(trace.name); });
  return {traces, layout};
}
function explorePlotClick(view, result, event) {
  const point = event.points?.[0]; if (!point) return;
  if (view.family === "correlation" && !explore.capture) {
    if (explore.status !== "current") { notify("Wait for the chart to update before opening this comparison."); return; }
    const cells = result.statistics?.cells || [];
    const cell = cells.find(cell => (cell.x === point.x && cell.y === point.y) || (cell.left === point.x && cell.right === point.y));
    const custom = point.customdata;
    const rowIDs = cell?.row_ids || (Array.isArray(custom?.[0]) ? custom[0] : custom?.row_ids);
    if (!rowIDs?.length) { notify("This cell has no retained paired observations."); return; }
    const duplicate = structuredClone(view); duplicate.id = exploreID(); duplicate.name = `${point.y} against ${point.x}`; duplicate.family = "scatter";
    duplicate.sample.row_ids = rowIDs; duplicate.options.axes = [cell?.x_axis || point.x, cell?.y_axis || point.y];
    duplicate.options.x = duplicate.options.axes[0]; duplicate.options.y = duplicate.options.axes[1];
    if (view.options.correlation_orientation === "series") {
      const field = view.options.axes[0];
      const left = explore.workspace.collection.find(item => item.symbol === point.x && item.field === field);
      const right = explore.workspace.collection.find(item => item.symbol === point.y && item.field === field);
      if (!left || !right) { notify("The cell’s series associations could not be resolved."); return; }
      duplicate.shape = "paired_date"; duplicate.measures = [left.id, right.id]; duplicate.options.axes = [left.id, right.id];
      duplicate.options.x = left.id; duplicate.options.y = right.id;
    }
    explore.workspace.views.push(duplicate); explore.selected = duplicate.id; explore.checked.add(duplicate.id);
    exploreDirty("Opening a scatter with the observations from this correlation cell."); exploreRender(); return;
  }
  const datum = point.customdata;
  explore.highlighted = [datum?.symbol || datum?.[1] || (typeof datum === "string" ? datum : point.data.name)];
  if (!explore.capture) { explore.workspace.views.forEach(view => view.highlight = [...explore.highlighted]); exploreDirty("Highlight changed; sample unchanged. Preview before capturing."); }
  exploreRenderPlots();
}
function exploreReadView(form, changedControl) {
  const view = exploreCurrentView(), data = new FormData(form), oldShape = view.shape, oldFamily = view.family;
  view.name = data.get("name"); view.family = data.get("family"); view.shape = data.get("shape"); view.measures = data.getAll("measures");
  if (changedControl === "family" && view.family !== oldFamily) {
    if (view.name === exploreFamilies[oldFamily]) view.name = exploreFamilies[view.family];
    const fields = new Set(explore.workspace.collection.filter(item => view.measures.includes(item.id)).map(item => item.field));
    // An explicit drilldown/exclusion sample must survive chart-type changes.
    if (!view.sample.row_ids.length && !view.sample.excluded_row_ids.length) {
      view.shape = view.family === "scatter" ? fields.size > 1 ? "cross_section" : "paired_date" : view.family === "ranking" ? "cross_section" : "history";
    }
  }
  for (const name of ["display_start", "display_end", "size_by", "color_by", "facet_by"]) if (data.has(name)) view[name] = data.get(name) || null;
  exploreReadDates(view, data, changedControl);
  const members = data.getAll("members"), all = new Set(explore.workspace.collection.map(item => item.symbol));
  view.sample.members = members.length === all.size ? null : members;
  const axes = exploreFields(view), x = data.get("x"), y = data.get("y"), axis = data.get("axis");
  view.options.x = axes.includes(x) ? x : axes[0]; view.options.y = axes.includes(y) && oldShape === view.shape ? y : axes[1];
  view.options.axes = view.family === "scatter" ? [view.options.x, view.options.y].filter(Boolean) : ["ranking", "distribution"].includes(view.family) ? [axes.includes(axis) ? axis : axes[0]].filter(Boolean) : axis && axes.includes(axis) && !["heatmap", "correlation"].includes(view.family) ? [axis] : axes;
  for (const name of ["distribution", "heatmap_layout", "correlation_orientation", "correlation_method", "correlation_sample", "group_by", "weight_policy", "history_layout"]) if (data.has(name)) view.options[name] = data.get(name);
  if (view.family === "distribution") {
    view.options.group_by ||= "symbol";
    view.options.weight_policy ||= "equal_row";
  }
  if (changedControl !== "shape" && (view.family === "heatmap" && view.options.heatmap_layout === "fields" || view.family === "correlation" && view.options.correlation_orientation === "fields")) {
    view.shape = "cross_section"; view.options.axes = exploreFields(view); view.options.x = view.options.axes[0]; view.options.y = view.options.axes[1];
  }
  view.options.descriptive_fit = data.has("descriptive_fit");
  view.options.allow_pooled_fit = data.has("allow_pooled_fit");
  view.options.shared_bandwidth = data.has("shared_bandwidth");
  if (data.has("bandwidth_multiplier")) view.options.bandwidth_multiplier = Number(data.get("bandwidth_multiplier"));
  // Changing family preserves explicit row restrictions and exclusions.
  exploreDirty();
}
async function explorePreview(refreshData = false) {
  clearTimeout(explore.previewTimer);
  if (explore.capture || !explore.workspace.collection.length) return;
  if (explore.workspace.views.some(view => exploreDateProblem(view))) { explore.status = "dirty"; exploreUpdateStatus(); return; }
  if (explore.previewInFlight) { explore.previewQueued = true; explore.refreshQueued ||= refreshData; return; }
  refreshData ||= explore.refreshQueued;
  explore.refreshQueued = false;
  explore.previewInFlight = true; explore.previewQueued = false;
  const sequence = ++explore.sequence;
  explore.status = "previewing"; exploreUpdateStatus();
  try {
    const response = await api("/api/explore/preview", "POST", {workspace: structuredClone(explore.workspace), refresh_data: refreshData});
    if (sequence !== explore.sequence) return;
    // Layout and save version may change during a calculation; neither changes its sample.
    explore.workspace = {...(response.workspace || explore.workspace), layout: explore.workspace.layout, version: explore.workspace.version};
    explore.results = new Map((response.resolved_results || response.results || []).map(result => [result.view_id, result]));
    const message = document.querySelector('#message');
    if (explore.previewError && message?.textContent === explore.previewError) message.classList.remove('visible');
    explore.previewError = null;
    explore.status = "current"; exploreRender();
  } catch (error) {
    if (sequence !== explore.sequence) return;
    explore.previewError = error.message;
    explore.status = "failed"; exploreRender(); notify(error.message);
  } finally {
    explore.previewInFlight = false;
    if (explore.previewQueued || sequence !== explore.sequence && explore.status === "dirty") exploreSchedulePreview();
  }
}
async function exploreSave(copy = false) {
  if (copy) { explore.workspace.id = exploreID(); explore.workspace.version = null; explore.workspace.name += " (copy)"; }
  try {
    const response = await api("/api/explore/workspaces", "POST", {workspace: explore.workspace, expected_version: explore.workspace.version});
    explore.workspace = response.workspace || response;
    explore.saved = await api("/api/explore/workspaces"); explore.saved = explore.saved.workspaces || explore.saved;
    history.replaceState(null, "", `/explore/${explore.workspace.id}`); explore.conflict = null; exploreRender(); notify("Workspace saved.");
  } catch (error) { explore.conflict = error.message; exploreRender(); }
}
async function exploreOpen(id) {
  if (!id) return;
  const response = await api(`/api/explore/workspaces/${encodeURIComponent(id)}`);
  state.catalogue = await api("/api/explore/library");
  explore.libraryChanges = response.library_changes || [];
  explore.workspace = response.workspace || response; explore.capture = null; explore.results.clear(); explore.status = "dirty"; explore.sequence++;
  explore.selectionMode = null;
  explore.selected = explore.workspace.views[0]?.id; explore.checked = new Set(explore.workspace.views.map(view => view.id));
  history.replaceState(null, "", `/explore/${id}`); exploreRender(); exploreSchedulePreview();
}
async function exploreCapture() {
  if (explore.status !== "current") throw Error("Wait for the charts to update before saving evidence.");
  const sequence = explore.sequence, workspace = structuredClone(explore.workspace), views = workspace.views.filter(view => explore.checked.has(view.id));
  if (!views.length) throw Error("Select at least one chart to save.");
  const resultIDs = [], images = {};
  for (const view of views) {
    const result = explore.results.get(view.id); if (!result) throw Error(`Preview ${view.name} before capturing.`);
    resultIDs.push(result.id);
    let plot = document.querySelector(`#explore-plot-${view.id}`), temporary = null;
    if (!plot?.data) {
      temporary = document.createElement("div"); temporary.style.cssText = "position:fixed;left:-2000px;width:1100px;height:650px"; document.body.append(temporary);
      const chart = exploreChartData(view, result); await Plotly.newPlot(temporary, chart.traces, {...chart.layout, width: 1100, height: 650}); plot = temporary;
    }
    try { images[result.id] = await Plotly.toImage(plot, {format: "png", width: 1400, height: 850}); }
    finally { if (temporary) { Plotly.purge(temporary); temporary.remove(); } }
  }
  if (sequence !== explore.sequence || explore.status !== "current") throw Error("Draft changed while rendering capture. Preview and capture again.");
  const response = await api("/api/explore/captures", "POST", {workspace, result_ids: resultIDs, images,
    title: document.querySelector("#explore-capture-title").value || workspace.name,
    idea_id: document.querySelector("#explore-capture-idea").value || null, role: document.querySelector("#explore-capture-role").value});
  const capture = response.snapshot || response.capture || response;
  notify("Frozen exploration captured.");
  const destination = response.url || `/explore/captures/${response.idea?.id || response.idea_id || capture.idea_id}/${capture.id || response.snapshot_id}`;
  location.href = destination;
}
async function exploreExportPNGs() {
  if (explore.status !== "current") throw Error("Wait for the charts to update before exporting.");
  const views = explore.workspace.views.filter(view => explore.checked.has(view.id));
  if (!views.length) throw Error("Select at least one view to export.");
  for (const view of views) {
    const result = explore.results.get(view.id); if (!result) throw Error(`Preview ${view.name} first.`);
    const plot = document.querySelector(`#explore-plot-${view.id}`);
    if (plot?.data) {
      const url = await Plotly.toImage(plot, {format: "png", width: 1400, height: 850});
      const link = document.createElement("a"); link.href = url; link.download = `${view.name.replace(/[^a-z0-9_-]/gi, "_")}.png`; link.click();
    } else {
      const temporary = document.createElement("div"); temporary.style.cssText = "position:fixed;left:-2000px;width:1100px;height:650px"; document.body.append(temporary);
      try { const chart = exploreChartData(view, result); await Plotly.newPlot(temporary, chart.traces, {...chart.layout, width: 1100, height: 650});
        const url = await Plotly.toImage(temporary, {format: "png", width: 1400, height: 850});
        const link = document.createElement("a"); link.href = url; link.download = `${view.name.replace(/[^a-z0-9_-]/gi, "_")}.png`; link.click();
      } finally { Plotly.purge(temporary); temporary.remove(); }
    }
  }
}
function exploreDialog(content) {
  document.querySelector("#explore-dialog")?.remove();
  const dialog = document.createElement("dialog"); dialog.id = "explore-dialog"; dialog.className = "explore-dialog";
  dialog.innerHTML = content; document.body.append(dialog); dialog.showModal(); return dialog;
}
function exploreMappingDialog(item) {
  explore.mappingItem = item.id;
  exploreDialog(`<h2>Chart grouping</h2><p>Associate this series with a symbol and a comparable field in your charts. For example, group spread and duration under the same symbol.</p><p class="meta">The data provider’s identifiers and query stay unchanged.</p><form id="explore-mapping-form"><div class="fields">${exploreInput("Symbol used in charts", "symbol", item.symbol)}${exploreInput("Field used in charts", "field", item.field)}</div><div class="actions">${exploreButton("Use grouping", "apply-mapping", 'class="primary"')}${exploreButton("Cancel", "close-dialog")}</div></form>`);
}
function exploreApplyMapping() {
  const values = new FormData(document.querySelector('#explore-mapping-form'));
  const symbol = values.get('symbol').trim(), field = values.get('field').trim();
  if (!symbol || !field) throw Error("Enter both a symbol and a field for chart grouping.");
  const item = explore.workspace.collection.find(item => item.id === explore.mappingItem), previousField = item.field;
  if (explore.workspace.collection.some(other => other.id !== item.id && other.symbol === symbol && other.field === field)) throw Error("Another series already uses this symbol and field. Choose a distinct field.");
  item.symbol = symbol; item.field = field;
  for (const view of explore.workspace.views.filter(view => view.measures.includes(item.id) && view.shape !== "paired_date")) {
    const available = exploreFields(view), replace = axis => axis === previousField && !available.includes(axis) ? field : axis;
    view.options.axes = (view.options.axes || []).map(replace);
    for (const axis of ["x", "y"]) if (view.options[axis]) view.options[axis] = replace(view.options[axis]);
    if (view.family === "history" && !view.options.axes.includes(field)) view.options.axes.push(field);
  }
  document.querySelector('#explore-dialog').close(); exploreDirty(); exploreRender();
}
function exploreAttributeRow(attribute = {}) {
  const symbols = [...new Set(explore.workspace.collection.map(item => item.symbol))];
  if (attribute.symbol && !symbols.includes(attribute.symbol)) symbols.push(attribute.symbol);
  return `<fieldset class="explore-attribute-row"><legend>Classification</legend><div class="fields">${exploreSelect("Symbol", "symbol", attribute.symbol || symbols[0], symbols.map(symbol => [symbol, symbol]))}${exploreInput("Classification (e.g. sector)", "name", attribute.name)}${exploreInput("Value", "value", attribute.value)}${exploreInput("Source", "source", attribute.source)}${exploreInput("Valid from (optional)", "effective_start", attribute.effective_start, "date")}${exploreInput("Valid through (optional)", "effective_end", attribute.effective_end, "date")}</div>${exploreButton("Remove classification", "remove-attribute", 'class="quiet"')}</fieldset>`;
}
function exploreAttributesDialog() {
  exploreDialog(`<h2>Classifications</h2><p>Supply labels you can use to colour or group symbols, such as a sector from your data source.</p><p class="meta">Record where each label came from. Without dates, a label is treated as a fixed classification throughout history.</p><form id="explore-attributes-form"><div id="explore-attribute-rows">${explore.workspace.attributes.map(exploreAttributeRow).join("")}</div><div class="actions">${exploreButton("Add classification", "add-attribute")}${exploreButton("Save classifications", "apply-attributes", 'class="primary"')}${exploreButton("Cancel", "close-dialog")}</div></form>`);
}
function exploreApplyAttributes() {
  const attributes = [...document.querySelectorAll('.explore-attribute-row')].map(row => {
    const attribute = Object.fromEntries([...row.querySelectorAll('[name]')].map(input => [input.name, input.value.trim()]));
    if (!["symbol", "name", "value", "source"].every(key => attribute[key])) throw Error("Each classification needs a symbol, name, value and source.");
    attribute.effective_start ||= null; attribute.effective_end ||= null;
    if (attribute.effective_start && attribute.effective_end && attribute.effective_start > attribute.effective_end) throw Error("The end date must be on or after the start date.");
    return attribute;
  });
  const names = new Set(attributes.map(attribute => attribute.name));
  for (const view of explore.workspace.views) {
    if (view.facet_by && !names.has(view.facet_by)) view.facet_by = null;
    if (view.options.group_by && view.options.group_by !== "symbol" && !names.has(view.options.group_by)) view.options.group_by = "symbol";
    if (explore.workspace.attributes.some(attribute => attribute.name === view.color_by) && !names.has(view.color_by)) view.color_by = "symbol";
  }
  explore.workspace.attributes = attributes;
  document.querySelector('#explore-dialog').close(); exploreDirty(); exploreRender();
}
function exploreAnalysisDialog(item = null) {
  const definition = item?.analysis;
  state.stagedSeries = {};
  explore.analysisItem = item?.id || null;
  explore.analysisDraft = definition ? {id: definition.id, revision: definition.revision, name: definition.name, calculation: definition.calculation, economic_rationale: definition.economic_rationale || "", series_ids: definition.inputs.map(binding => binding.id), monitored: false, settings: structuredClone(definition.settings)} : newDraft("analyses");
  if (definition) for (const binding of [...definition.inputs, ...(definition.references || [])]) state.stagedSeries[binding.id] = structuredClone(binding);
  exploreReplaceAnalysisDialog();
}
function exploreReplaceAnalysisDialog() {
  const draft = explore.analysisDraft, old = document.querySelector("#explore-dialog"), focused = document.activeElement;
  const open = analysisDisclosureState(old);
  const selector = focused?.dataset.risk ? `[data-risk="${focused.dataset.risk}"][data-leg="${focused.dataset.leg}"]` : focused?.name ? `[name="${CSS.escape(focused.name)}"]` : null;
  const content = `<h2>${explore.analysisItem ? "Edit calculation" : "Add a calculation"}</h2><p class="meta">Use the Analysis controls to calculate a series for this workspace. Select the result in a chart to display it.</p><form id="explore-analysis-form">${exploreInput("Name", "name", draft.name)}<label>Economic rationale<textarea name="economic_rationale" maxlength="10000">${esc(draft.economic_rationale)}</textarea></label>${analysisControls(draft, [], exploreAnalysisContext())}<p class="meta">Need an input that is not in Library? Define it below for this calculation.</p><div class="actions">${exploreButton(explore.analysisItem ? "Update calculation" : "Add to workspace", "apply-analysis", 'class="primary"')}${exploreButton("Define new input…", "stage-series")}${exploreButton("Save calculation to Library", "save-analysis-library")}${exploreButton("Cancel", "close-dialog")}</div></form>`;
  if (old) { old.innerHTML = content; if (!old.open) old.showModal(); } else exploreDialog(content);
  restoreAnalysisDisclosures(document.querySelector("#explore-dialog"), open);
  if (selector) document.querySelector("#explore-dialog")?.querySelector(selector)?.focus({preventScroll: true});
}
function exploreSeriesDialog(staged = false) {
  explore.stagingSeries = staged; explore.seriesDraft = newDraft("series");
  exploreReplaceSeriesDialog();
}
function exploreReplaceSeriesDialog() {
  const staged = explore.stagingSeries;
  const previousDraft = state.draft, previousTab = state.libraryTab;
  state.draft = explore.seriesDraft; state.libraryTab = "series";
  const content = libraryEditor().replace('id="library-form"', 'id="explore-series-form"').replace(/<div class="actions">[\s\S]*?<\/div>(?=<\/form>)/, `<div class="actions">${exploreButton("Check data", "preview-series")}${exploreButton(staged ? "Use as calculation input" : "Save to Library and add", "apply-series", 'class="primary"')}${exploreButton("Cancel", "close-dialog")}</div>`);
  state.draft = previousDraft; state.libraryTab = previousTab;
  exploreDialog(`<p class="meta">${staged ? "Define a data source for this calculation. It stays in this workspace until you save it to Library." : "Enter the exact identifiers expected by your data provider. This creates a reusable Library series."}</p>` + content + '<p id="explore-series-status" role="status"></p>');
}
async function exploreApplyAnalysis(librarySave = false) {
  const form = document.querySelector("#explore-analysis-form");
  readAnalysisControls(form, explore.analysisDraft, exploreAnalysisContext()); explore.analysisDraft.monitored = false;
  let draft = activeAnalysis(explore.analysisDraft), selected = retainedSeries(draft), staged = Object.values(state.stagedSeries).filter(series => selected.has(series.id)), resolved;
  if (librarySave) {
    const original = state.catalogue.analyses.find(record => record.id === draft.id);
    draft.monitored = original?.monitored || false;
    const baseRevisions = {analyses: original ? {[original.id]: draft.revision} : {}, series: Object.fromEntries(staged.flatMap(series => {
      const previous = state.catalogue.series.find(record => record.id === series.id); return previous ? [[previous.id, series.revision]] : [];
    }))};
    const saved = await api("/api/library/analyses/bundle", "POST", {analysis: draft, series_drafts: staged.map(seriesForSave), base_revisions: baseRevisions});
    draft = saved.analysis; explore.analysisDraft = structuredClone(draft);
    state.catalogue = await api("/api/explore/library"); notify(`Saved ${saved.analysis?.name || draft.name} to Library. Monitoring ${draft.monitored ? "preserved" : "disabled"}.`);
    resolved = exploreResolvedAnalyses().find(definition => definition.id === draft.id);
    staged.forEach(binding => delete state.stagedSeries[binding.id]);
  }
  if (!resolved) { const response = await api("/api/explore/resolve", "POST", {analysis: draft, series_drafts: staged.map(binding => ({...binding, catalog_name: binding.catalog_name || null}))}); resolved = response.definition || response.analysis || response; }
  const item = explore.workspace.collection.find(item => item.id === explore.analysisItem);
  if (item) { item.analysis = resolved; item.origin = librarySave ? "library" : "local"; exploreDirty(); exploreRender(); }
  else exploreAddItem("analysis", draft, resolved, librarySave ? "library" : "local");
  document.querySelector("#explore-dialog")?.close();
  if (!librarySave) notify("Calculation added to this workspace. Choose it under Series in this chart.");
}
document.addEventListener("input", event => {
  if (page !== "explore" || explore.capture) return;
  const control = event.target;
  if (control.id === "explore-library-search") {
    explore.libraryQuery = control.value;
    document.querySelectorAll(".explore-library-row").forEach(row => row.hidden = !row.textContent.toLowerCase().includes(control.value.toLowerCase())); return;
  }
  if (["explore-question", "explore-notes"].includes(control.id)) { explore.workspace[control.id === "explore-question" ? "question" : "notes"] = control.value; explore.editingText = true; exploreDirty(undefined, false); }
  if (control.name === "workspace_name") { explore.workspace.name = control.value; explore.editingText = true; exploreDirty(undefined, false); }
  if (control.name === "workspace_as_of") { explore.editingText = true; exploreDirty(undefined, false); }
  if (control.closest('#explore-view-form') && ["text", "number", "date"].includes(control.type)) { explore.editingText = true; exploreDirty(undefined, false); }
  if (control.closest("#explore-analysis-form")) readAnalysisControls(control.form, explore.analysisDraft, exploreAnalysisContext());
});
document.addEventListener("change", event => {
  if (page !== "explore") return;
  const control = event.target;
  if (control.dataset.captureView) {
    control.checked ? explore.checked.add(control.dataset.captureView) : explore.checked.delete(control.dataset.captureView);
    document.querySelector('#explore-selection-count').textContent = `${explore.checked.size} selected`;
    exploreUpdateStatus(); return;
  }
  if (explore.capture) return;
  if (["explore-question", "explore-notes"].includes(control.id) || control.name === "workspace_name") { explore.editingText = false; exploreSchedulePreview(); }
  if (control.name === "workspace_as_of") { explore.workspace.as_of = control.value || null; explore.editingText = false; exploreDirty(); }
  if (control.closest("#explore-view-form")) {
    explore.editingText = false;
    if (control.name === "measures" && !control.form.querySelector('[name="measures"]:checked')) { control.checked = true; notify("Keep at least one series in this chart, or remove the chart."); return; }
    exploreReadView(control.form, control.name);
    if (control.tagName === "SELECT" || ["measures", "pinned"].includes(control.name)) exploreRender();
  }
  if (control.closest("#explore-analysis-form")) {
    readAnalysisControls(control.form, explore.analysisDraft, exploreAnalysisContext());
    if (control.tagName === "SELECT" || control.hasAttribute("data-risk-customize")) exploreReplaceAnalysisDialog();
  }
  if (control.closest("#explore-series-form") && control.name === "provider") { explore.seriesDraft = readSeriesDraft(control.form, explore.seriesDraft); exploreReplaceSeriesDialog(); }
});

// Returning an input to its original value may omit `change`; never leave updates paused.
document.addEventListener("focusout", event => {
  if (page !== "explore" || explore.capture || !explore.editingText) return;
  const control = event.target;
  if (control.closest('#explore-view-form')) { explore.editingText = false; exploreReadView(control.form, control.name); }
  else if (["explore-question", "explore-notes"].includes(control.id) || control.name === "workspace_name") { explore.editingText = false; exploreSchedulePreview(); }
  else if (control.name === "workspace_as_of") { explore.editingText = false; explore.workspace.as_of = control.value || null; exploreDirty(); }
});
document.addEventListener("submit", event => {
  if (page === "explore") { event.preventDefault(); event.stopImmediatePropagation(); }
}, true);
document.addEventListener("click", async event => {
  const button = event.target.closest("[data-explore]"); if (page !== "explore" || !button) return;
  button.disabled = true;
  try {
    const action = button.dataset.explore, view = exploreCurrentView();
    if (action === "add-item") { const records = state.catalogue[button.dataset.kind === "series" ? "series" : "analyses"], record = records.find(record => record.id === button.dataset.id);
      const resolved = exploreResolvedAnalyses().find(definition => definition.id === record.id);
      exploreAddItem(button.dataset.kind, record, resolved); }
    else if (action === "adopt") { const item = explore.workspace.collection.find(item => item.id === button.dataset.id), definition = item.binding || item.analysis;
      if (item.kind === "series") item.binding = structuredClone(state.catalogue.series.find(record => record.id === definition.id));
      else item.analysis = structuredClone(exploreResolvedAnalyses().find(record => record.id === definition.id)); explore.libraryChanges = (explore.libraryChanges || []).filter(change => change.collection_id !== item.id); exploreDirty(); exploreRender(); }
    else if (action === "remove-item") { explore.workspace.collection = explore.workspace.collection.filter(item => item.id !== button.dataset.id); explore.workspace.views.forEach(view => view.measures = view.measures.filter(id => id !== button.dataset.id)); exploreDirty(); exploreRender(); }
    else if (action === "add-view") exploreAddView(document.querySelector('[name="new_family"]').value);
    else if (action === "select" || action === "focus-view") { explore.selected = button.dataset.id; if (action === "focus-view") explore.workspace.layout = "focus"; exploreRender(); }
    else if (action === "layout") { explore.workspace.layout = explore.workspace.layout === "focus" ? "workbench" : "focus"; exploreRender(); }
    else if (action === "duplicate") { const duplicate = structuredClone(view); duplicate.id = exploreID(); duplicate.name += " (copy)"; explore.workspace.views.splice(explore.workspace.views.indexOf(view) + 1, 0, duplicate); explore.selected = duplicate.id; explore.checked.add(duplicate.id); exploreDirty(); exploreRender(); }
    else if (action === "earlier") { const index = explore.workspace.views.indexOf(view); if (index > 0) [explore.workspace.views[index - 1], explore.workspace.views[index]] = [view, explore.workspace.views[index - 1]]; exploreDirty(); exploreRender(); }
    else if (action === "width") { view.width = view.width === 1 ? 2 : 1; exploreDirty(); exploreRender(); }
    else if (action === "remove-view") { explore.workspace.views = explore.workspace.views.filter(item => item.id !== view.id); explore.selected = explore.workspace.views[0]?.id; explore.checked.delete(view.id); exploreDirty(); exploreRender(); }
    else if (action === "exclude-row") { const selected = explore.workspace.views.find(view => view.id === button.dataset.view); selected.sample.excluded_row_ids.push(button.dataset.row); exploreDirty(); exploreRender(); }
    else if (action === "restore-rows" || action === "release-sample") { view.sample[action === "restore-rows" ? "excluded_row_ids" : "row_ids"] = []; exploreDirty(); exploreRender(); }
    else if (action === "preview") await explorePreview(true);
    else if (action === "save" || action === "save-copy") await exploreSave(action === "save-copy");
    else if (action === "open" || action === "open-saved") await exploreOpen(button.dataset.id || document.querySelector('[name="saved_workspace"]').value);
    else if (action === "new") { explore.workspace = exploreNewWorkspace(); explore.results.clear(); explore.selected = null; explore.selectionMode = null; exploreDirty(); history.replaceState(null, "", "/explore"); exploreRender(); }
    else if (action === "select-save" || action === "select-export") { explore.selectionMode = action === "select-save" ? "save" : "export"; explore.workspace.layout = "workbench"; exploreRender(); }
    else if (action === "cancel-selection") { explore.selectionMode = null; exploreRender(); }
    else if (action === "capture-dialog") exploreCaptureDialog();
    else if (action === "capture") await exploreCapture();
    else if (action === "export-png") { await exploreExportPNGs(); explore.selectionMode = null; exploreRender(); }
    else if (action === "copy-png") { const plot = document.querySelector(`#explore-plot-${button.dataset.id}`); if (!plot?.data) throw Error("Wait for the chart to finish drawing, then copy it.");
      const dataURL = await Plotly.toImage(plot, {format: "png", width: 1400, height: 850}), blob = await (await fetch(dataURL)).blob();
      await navigator.clipboard.write([new ClipboardItem({"image/png": blob})]); notify("Chart PNG copied."); }
    else if (action === "check-all") { explore.checked = new Set(explore.workspace.views.map(view => view.id)); exploreRender(); }
    else if (action === "uncheck-all") { explore.checked.clear(); exploreRender(); }
    else if (action === "clear-highlight") { explore.highlighted = []; if (!explore.capture) { explore.workspace.views.forEach(view => view.highlight = []); exploreDirty(); } exploreRenderPlots(); }
    else if (action === "fork") {
      const capture = explore.capture, workspace = structuredClone(explore.workspace);
      const context = await exploreAuthoringContext(true);
      if (explore.capture !== capture) return;
      state.catalogue = context.catalogue; explore.saved = context.saved; state.exploreIdeas = context.ideas;
      workspace.id = exploreID(); workspace.version = null; workspace.name += " (copy)";
      explore.workspace = workspace; explore.capture = null; explore.libraryChanges = []; explore.selectionMode = null;
      exploreDirty(); history.replaceState(null, "", "/explore"); exploreRender();
    }
    else if (action === "new-analysis" || action === "edit-analysis") exploreAnalysisDialog(explore.workspace.collection.find(item => item.id === button.dataset.id));
    else if (action === "new-series" || action === "stage-series") exploreSeriesDialog(action === "stage-series");
    else if (action === "mapping") exploreMappingDialog(explore.workspace.collection.find(item => item.id === button.dataset.id));
    else if (action === "apply-mapping") exploreApplyMapping();
    else if (action === "attributes") exploreAttributesDialog();
    else if (action === "add-attribute") document.querySelector('#explore-attribute-rows').insertAdjacentHTML('beforeend', exploreAttributeRow());
    else if (action === "remove-attribute") button.closest('.explore-attribute-row').remove();
    else if (action === "apply-attributes") exploreApplyAttributes();
    else if (action === "apply-analysis" || action === "save-analysis-library") await exploreApplyAnalysis(action === "save-analysis-library");
    else if (action === "close-dialog") { document.querySelector("#explore-dialog").close(); if (explore.stagingSeries) { explore.stagingSeries = false; exploreReplaceAnalysisDialog(); } }
    else if (action === "preview-series" || action === "apply-series") {
      const form = document.querySelector("#explore-series-form"); if (!form.reportValidity()) return;
      explore.seriesDraft = readSeriesDraft(form, explore.seriesDraft);
      if (action === "preview-series") { const response = await api("/api/library/series/preview", "POST", {series: previewBinding(explore.seriesDraft), period: 3}); document.querySelector("#explore-series-status").textContent = `Preview resolved: ${JSON.stringify(response.limitations || response.data?.failures || [])}`; }
      else if (explore.stagingSeries) { state.stagedSeries[explore.seriesDraft.id] = structuredClone(explore.seriesDraft); explore.analysisDraft.series_ids[0] = explore.seriesDraft.id; explore.stagingSeries = false; exploreReplaceAnalysisDialog(); }
      else { const record = await api("/api/library/series", "POST", seriesForSave(explore.seriesDraft)); state.catalogue = await api("/api/explore/library"); exploreAddItem("series", record); document.querySelector("#explore-dialog").close(); }
    }
  } catch (error) { notify(error.message); }
  finally { if (button.isConnected) button.disabled = false; }
});
async function exploreAuthoringContext(requireAll = false) {
  const responses = await Promise.allSettled([api("/api/explore/library"), api("/api/explore/workspaces"), api("/api/ideas")]);
  const failure = requireAll ? responses.find(response => response.status === "rejected") : responses[0].status === "rejected" ? responses[0] : null;
  if (failure) throw failure.reason;
  return {catalogue: responses[0].value,
    saved: responses[1].status === "fulfilled" ? responses[1].value.workspaces || responses[1].value : [],
    ideas: responses[2].status === "fulfilled" ? responses[2].value.ideas || responses[2].value : []};
}
async function exploreStart() {
  const segments = location.pathname.split("/").filter(Boolean);
  state.catalogue = {series: [], analyses: [], resolved_analyses: []}; state.stagedSeries = {}; state.controlMemory = {};
  if (segments[1] === "captures") {
    const response = await api(`/api/explore/captures/${segments[2]}/${segments[3]}`);
    explore.capture = response.snapshot || response.capture || response;
    explore.capture.idea_id = segments[2];
    explore.workspace = explore.capture.workspace;
    const results = explore.capture.results || explore.capture.resolved_results || response.results || [];
    explore.results = new Map(results.map(result => [result.view_id, result])); explore.status = "current";
  } else {
    const context = await exploreAuthoringContext();
    state.catalogue = context.catalogue; explore.saved = context.saved; state.exploreIdeas = context.ideas;
    explore.workspace = exploreNewWorkspace();
    if (segments[1]) { const response = await api(`/api/explore/workspaces/${segments[1]}`); explore.workspace = response.workspace || response; explore.libraryChanges = response.library_changes || []; }
  }
  const visible = exploreVisibleViews(); explore.selected = visible[0]?.id; explore.checked = new Set(visible.map(view => view.id)); exploreRender();
  if (!explore.capture) exploreSchedulePreview();
}
window.exploreWorkspace = explore;
exploreStart().catch(error => { main.innerHTML = `<h1>Unable to load Explore</h1><p class="warning">${esc(error.message)}</p><a href="${esc(location.pathname)}">Retry</a>`; });
