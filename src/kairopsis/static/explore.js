/* Workspaces edit definitions. Charts, tables and capture use immutable server results. */
const explore = {
  workspace: null, selected: null, results: new Map(), status: "dirty", sequence: 0,
  saved: [], capture: null, conflict: null, highlighted: [], libraryQuery: "", checked: new Set(),
};
const exploreFamilies = {history: "History", scatter: "Scatter", ranking: "Ranked comparison", distribution: "Distribution", heatmap: "Heatmap", correlation: "Correlation"};
const exploreID = () => crypto.randomUUID().replaceAll("-", "");
const exploreButton = (text, action, extra = "") => `<button type="button" data-explore="${action}" ${extra}>${text}</button>`;
const exploreSelect = (label, name, value, choices) => `<label>${esc(label)}<select name="${name}">${choices.map(([id, text]) => `<option value="${esc(id)}" ${String(id) === String(value) ? "selected" : ""}>${esc(text)}</option>`).join("")}</select></label>`;
const exploreInput = (label, name, value, type = "text") => `<label>${esc(label)}<input name="${name}" type="${type}" value="${esc(value || "")}"></label>`;
function exploreNewWorkspace() {
  return {schema_version: 1, id: exploreID(), version: null, name: "Untitled exploration", collection: [], views: [], as_of: null, question: "", notes: "", attributes: [], layout: "workbench"};
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
function exploreDirty(message = "Draft changed. Preview to update evidence.") {
  explore.sequence++;
  explore.status = "dirty";
  explore.conflict = null;
  const status = document.querySelector("#explore-status");
  if (status) { status.textContent = message; status.className = "explore-status"; }
  document.querySelectorAll('[data-explore="capture"]').forEach(button => button.disabled = true);
  document.querySelectorAll(".explore-result-state").forEach(node => node.textContent = "Previous preview · draft changed");
}
function exploreAddItem(kind, record, resolved, origin = "library") {
  const definition = kind === "series" ? record : resolved;
  if (!definition) throw Error("This Analysis could not be resolved. Open it in Library to inspect its inputs.");
  const duplicate = explore.workspace.collection.find(item => item.kind === kind && (item.binding || item.analysis).id === record.id && (item.binding || item.analysis).revision === record.revision);
  if (duplicate) { notify("This revision is already in the collection."); return; }
  explore.workspace.collection.push({id: exploreID(), kind, origin, symbol: kind === "series" ? record.instrument : record.name,
    field: kind === "series" ? record.field || record.name : record.name,
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
    options: {axes, x: axes[0], y: axes[1], distribution: "kde", descriptive_fit: false, heatmap_layout: "time", correlation_orientation: "series", correlation_method: "pearson", correlation_sample: "common"}};
  explore.workspace.views.push(view); explore.selected = view.id; explore.checked.add(view.id);
  exploreDirty(); exploreRender();
}
function exploreCollectionHTML() {
  const items = explore.workspace.collection;
  const query = explore.libraryQuery.toLowerCase();
  const records = [...state.catalogue.series.map(record => ["series", record]), ...state.catalogue.analyses.map(record => ["analysis", record])]
    .filter(([, record]) => `${record.name} ${record.instrument || ""} ${record.field || ""}`.toLowerCase().includes(query));
  return `<aside class="explore-collection" aria-label="Collection"><h2>Collection</h2>
    <p class="meta">Associate each binding explicitly with a symbol and field.</p>
    <div class="explore-collection-list">${items.map(item => {
      const definition = item.binding || item.analysis;
      const current = state.catalogue[item.kind === "series" ? "series" : "analyses"].find(record => record.id === definition.id);
      const revision = explore.capture ? `<small>Retained revision ${definition.revision} · Library not consulted</small>` : current && current.revision !== definition.revision ? `<small class="explore-revisions">Pinned r${definition.revision}; Library r${current.revision} ${exploreButton("Adopt revision", "adopt", `data-id="${item.id}"`)}</small>` : !current ? `<small>${item.origin === "local" ? "Local draft · not published to Library" : "Retained definition · absent from Library"}</small>` : `<small>Pinned revision ${definition.revision}</small>`;
      return `<div class="explore-binding" data-item="${item.id}"><strong>${esc(definition.name)}</strong>
        <small>${item.kind === "series" ? `${esc(definition.source)} / ${esc(definition.instrument)} · ${esc(definition.unit)}` : `${esc(definition.calculation === "level" ? "Standalone" : "Pair")} Analysis output`}</small>${revision}
        ${item.origin === "local" && !explore.capture ? '<small>Local Analysis draft · Library defaults untouched</small>' : ""}
        <div class="fields"><label>Symbol<input data-association="symbol" data-id="${item.id}" value="${esc(item.symbol)}" ${explore.capture ? "disabled" : ""}></label><label>Field<input data-association="field" data-id="${item.id}" value="${esc(item.field)}" ${explore.capture ? "disabled" : ""}></label></div>
        ${item.kind === "series" && definition.basis ? `<small>${esc(definition.basis.label)}</small>` : ""}
        ${explore.capture ? "" : `<div class="actions">${item.kind === "analysis" ? exploreButton("Edit local draft", "edit-analysis", `data-id="${item.id}"`) : ""}${exploreButton("Remove", "remove-item", `data-id="${item.id}" class="quiet"`)}</div>`}</div>`;
    }).join("") || '<p class="empty">Select Library entries below to begin.</p>'}</div>
    ${explore.capture ? "" : `<details open><summary>Add from Library</summary><input id="explore-library-search" class="search" placeholder="Find series or Analysis" aria-label="Find Library entries" value="${esc(explore.libraryQuery)}"><div id="explore-library-choices">${records.map(([kind, record]) => `<div class="explore-library-row">${exploreButton(esc(record.name) + `<small>${kind === "series" ? `${esc(record.instrument)} / ${esc(record.field || record.name)} · ${esc(record.unit)}` : "Analysis output"}</small>`, "add-item", `data-kind="${kind}" data-id="${record.id}"`)}</div>`).join("")}</div></details>
      <div class="actions">${exploreButton("Local Analysis", "new-analysis")}${exploreButton("New series", "new-series")}${exploreButton("Supply attributes", "attributes")}</div><a href="/library">Open Library</a>`}</aside>`;
}
function exploreEditorHTML() {
  const view = exploreCurrentView();
  if (!view) return '<aside class="explore-editor"><h2>View settings</h2><p class="meta">Add a view, then choose its measures and sample.</p></aside>';
  const choices = exploreFields(view).map(axis => [axis, exploreAxisLabel(axis)]), fields = [...new Set(explore.workspace.collection.map(item => item.field))];
  const members = [...new Set(explore.workspace.collection.map(item => item.symbol))];
  const attributes = [...new Set(explore.workspace.attributes.map(attribute => attribute.name || attribute.field).filter(Boolean))];
  return `<aside class="explore-editor" aria-label="Selected view settings"><h2>${esc(exploreFamilies[view.family])} settings</h2><form id="explore-view-form"><fieldset ${explore.capture ? "disabled" : ""}>
    ${exploreInput("View name", "name", view.name)}${exploreSelect("Chart family", "family", view.family, Object.entries(exploreFamilies))}
    ${exploreSelect("Observations", "shape", view.shape, [["history", "One series / date"], ["cross_section", "One symbol / chosen date"], ["paired_date", "Two series / matched date"], ["panel", "Symbol / date panel"]])}
    <fieldset><legend>Measures</legend><div class="measure-list">${explore.workspace.collection.map(item => `<label><input name="measures" type="checkbox" value="${item.id}" ${view.measures.includes(item.id) ? "checked" : ""}>${esc(exploreItemLabel(item))}</label>`).join("")}</div></fieldset>
    ${view.family === "scatter" ? `<div class="fields">${exploreSelect("X axis", "x", view.options.x || choices[0]?.[0], choices)}${exploreSelect("Y axis", "y", view.options.y || choices[1]?.[0], choices)}</div>` : ["correlation", "heatmap"].includes(view.family) ? '<p class="meta">Selected measures supply the fields.</p>' : exploreSelect("Field", "axis", view.options.axes?.length > 1 ? "all" : view.options.axes?.[0] || choices[0]?.[0], view.family === "history" ? [["all", "All selected fields"], ...choices] : choices)}
    ${view.family === "history" ? exploreSelect("History layout", "history_layout", view.options.history_layout || "overlay", [["overlay", "Overlay (comparable units)"], ["small_multiples", "Aligned small multiples"]]) : ""}
    ${view.family === "scatter" ? `<label><input name="descriptive_fit" type="checkbox" ${view.options.descriptive_fit ? "checked" : ""}> Descriptive linear fit</label>${view.shape === "panel" ? `<label><input name="allow_pooled_fit" type="checkbox" ${view.options.allow_pooled_fit ? "checked" : ""}> Explicitly pool panel rows for the fit</label>` : ""}<p class="meta">Fit uses this view’s retained observations. It is separate from an Analysis residual.</p>` : ""}
    ${view.family === "distribution" ? `${exploreSelect("Distribution", "distribution", view.options.distribution, [["kde", "KDE"], ["histogram", "Histogram"], ["box", "Box"]])}${exploreInput("Bandwidth multiplier", "bandwidth_multiplier", view.options.bandwidth_multiplier || 1, "number")}<label><input name="shared_bandwidth" type="checkbox" ${view.options.shared_bandwidth ? "checked" : ""}> Shared bandwidth (comparable units)</label>${exploreSelect("Group by", "group_by", view.options.group_by || "symbol", [["symbol", "Symbol"], ...attributes.map(name => [name, name])])}${exploreSelect("Pooling weights", "weight_policy", view.options.weight_policy || "equal_row", [["equal_row", "Equal rows"], ["equal_member", "Equal symbols"]])}` : ""}
    ${view.family === "heatmap" ? exploreSelect("Layout", "heatmap_layout", view.options.heatmap_layout, [["time", "Symbols × dates"], ["fields", "Symbols × fields"]]) : ""}
    ${view.family === "correlation" ? `${exploreSelect("Compare", "correlation_orientation", view.options.correlation_orientation, [["series", "Series across dates"], ["fields", "Fields across symbols"]])}<div class="fields">${exploreSelect("Coefficient", "correlation_method", view.options.correlation_method, [["pearson", "Pearson"], ["spearman", "Spearman"]])}${exploreSelect("Sample", "correlation_sample", view.options.correlation_sample, [["common", "Common complete"], ["pairwise", "Pairwise"]])}</div>` : ""}
    ${view.family === "scatter" ? `${exploreSelect("Size by", "size_by", view.size_by || "", [["", "None"], ...explore.workspace.collection.map(item => [item.id, exploreItemLabel(item)])])}${exploreSelect("Colour by", "color_by", view.color_by || "", [["", "None"], ["symbol", "Symbol"], ...(view.shape === "paired_date" ? explore.workspace.collection.map(item => [item.id, exploreItemLabel(item)]) : fields.map(field => [field, field])), ...attributes.map(name => [name, name])])}${exploreSelect("Facet by", "facet_by", view.facet_by || "", [["", "None"], ...attributes.map(name => [name, name])])}` : ""}
    <fieldset><legend>Sample</legend><label><input name="pinned" type="checkbox" ${view.pinned ? "checked" : ""}> Pin this view’s as-of date</label>
      ${exploreInput(view.pinned ? "Pinned as-of date" : "As-of override (optional)", "as_of", view.as_of, "date")}
      <div class="fields">${exploreInput("Start", "start", view.sample.start, "date")}${exploreInput("End", "end", view.sample.end, "date")}</div>
      ${exploreSelect("Date matching", "date_policy", view.sample.date_policy, [["exact", "Exact"], ["backward", "Bounded backward"]])}
      ${view.sample.date_policy === "backward" ? exploreInput("Maximum age (days)", "maximum_age_days", view.sample.maximum_age_days, "number") : ""}
      ${view.family === "ranking" || view.shape === "cross_section" ? `${exploreInput("Interval start (optional)", "interval_start", view.sample.interval_start, "date")}${exploreSelect("Endpoint measure", "interval_measure", view.sample.interval_measure, [["level", "Level"], ["change", "Absolute change"], ["return", "Percentage change"]])}` : ""}
      <details><summary>Filter symbols</summary>${members.map(member => `<label><input name="members" type="checkbox" value="${esc(member)}" ${view.sample.members == null || view.sample.members.includes(member) ? "checked" : ""}> ${esc(member)}</label>`).join("")}</details>
      ${view.sample.row_ids.length ? `<p class="meta">Restricted to ${view.sample.row_ids.length} drilldown rows.</p>${exploreButton("Release drilldown sample", "release-sample")}` : ""}
      ${view.sample.excluded_row_ids.length ? `<p class="meta">${view.sample.excluded_row_ids.length} observations excluded.</p>${exploreButton("Restore excluded rows", "restore-rows")}` : ""}
    </fieldset>
    <details><summary>Display crop</summary><p class="meta">Changes visible extent only; analytical history remains fixed.</p><div class="fields">${exploreInput("Show from", "display_start", view.display_start, "date")}${exploreInput("Show through", "display_end", view.display_end, "date")}</div></details>
    <div class="actions">${exploreButton("Duplicate", "duplicate")}${exploreButton("Move earlier", "earlier")}${exploreButton(view.width === 2 ? "Half width" : "Full width", "width")}${exploreButton("Remove view", "remove-view", 'class="quiet"')}</div></fieldset></form></aside>`;
}
function exploreRowsHTML(result) {
  const axes = [...new Set(result.rows.flatMap(row => Object.keys(row.values || {})))];
  return `<details><summary>Observations · ${result.rows.length} retained / ${(result.excluded || []).length} excluded</summary>${result.rows.length > 500 ? '<p class="meta">Table displays first 500 rows. Charts, statistics and evidence retain the full sample.</p>' : ""}<div class="table-region" tabindex="0"><table><thead><tr><th>Symbol</th><th>Date</th>${axes.map(axis => `<th>${esc(exploreAxisLabel(axis))}</th>`).join("")}<th>Field dates / provenance</th>${explore.capture ? "" : "<th>Sample</th>"}</tr></thead><tbody>${result.rows.slice(0, 500).map(row => `<tr><td>${esc(row.symbol)}</td><td>${esc(row.date || "Not dated")}</td>${axes.map(axis => `<td>${number(row.values[axis])}</td>`).join("")}<td>${esc(JSON.stringify(row.dates || {}))}<small>${esc(JSON.stringify(row.observed_on || {}))}</small></td>${explore.capture ? "" : `<td>${exploreButton("Exclude", "exclude-row", `data-view="${result.view_id}" data-row="${esc(row.id)}"`)}</td>`}</tr>`).join("")}</tbody></table></div>
    ${(result.excluded || []).length ? `<p class="meta">Excluded: ${esc(JSON.stringify(result.excluded))}</p>` : ""}</details>`;
}
function exploreViewHTML(view) {
  const result = explore.results.get(view.id), retainedView = result?.view || view;
  return `<section class="explore-view ${view.id === explore.selected ? "selected" : ""} ${view.width === 2 ? "wide" : ""}" data-view="${view.id}">
    <div class="explore-view-title"><h2>${exploreButton(esc(view.name), "select", `data-id="${view.id}" class="quiet"`)}</h2><div class="actions"><label title="Include in capture"><input type="checkbox" data-capture-view="${view.id}" aria-label="Capture ${esc(view.name)}" ${explore.checked.has(view.id) ? "checked" : ""}></label>${exploreButton("Copy PNG", "copy-png", `data-id="${view.id}"`)}${exploreButton("Focus", "focus-view", `data-id="${view.id}"`)}</div></div>
    <p class="meta explore-result-state">${result ? explore.capture ? `Frozen evidence · <a href="/api/explore/captures/${explore.capture.idea_id}/${explore.capture.id}/images/${result.id}" download>Original PNG</a>` : explore.status === "current" ? "Current preview" : "Previous preview · draft changed" : "Not previewed"}</p>
    <div id="explore-plot-${view.id}" class="plot" role="img" aria-label="${esc(view.name)}"><p class="empty">${result ? "Rendering retained observations…" : "Preview to resolve this view’s observations."}</p></div>
    ${result ? `<p class="meta">${esc(result.sample_meaning || {history: "One observation per series and date", cross_section: "One observation per symbol at the chosen date", paired_date: "Two series, one observation per matched date", panel: "One observation per symbol and date"}[retainedView.shape])} · ${result.rows.length} retained rows</p><p class="meta">${Object.entries(result.measures || {}).filter(([id]) => retainedView.measures.includes(id)).map(([, measure]) => `${esc(measure.symbol)} / ${esc(measure.field)}: ${esc(measure.unit)}${measure.meaning ? " · " + esc(measure.meaning) : ""}`).join("; ")}</p>
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
  const opened = new Set([...main.querySelectorAll("details[open]")].map(details => details.querySelector("summary")?.textContent));
  const editorScroll = main.querySelector(".explore-editor")?.scrollTop || 0;
  main.innerHTML = `<div class="explore-top"><div><h1>${explore.capture ? "Frozen exploration" : "Explore"}</h1><p id="explore-status" class="explore-status ${explore.status}" role="status" aria-live="polite">${explore.capture ? "Captured evidence · available without live data" : {dirty: "Draft changed. Preview to update evidence.", previewing: "Resolving definitions and observations…", current: "Current preview · ready to capture", failed: "Preview failed. Previous evidence retained."}[explore.status]}</p></div><div class="actions">${explore.capture ? exploreButton("Fork investigation", "fork", 'class="primary"') : `${exploreButton("Preview / refresh", "preview", `class="primary" ${explore.status === "previewing" ? "disabled" : ""}`)}${exploreButton("Save workspace", "save")}${exploreButton("New workspace", "new")}`}${exploreButton(workspace.layout === "focus" ? "Workbench" : "Focus", "layout", `aria-pressed="${workspace.layout === "focus"}"`)}</div></div>
    ${explore.conflict ? `<div class="explore-conflict" role="alert">${esc(explore.conflict)} Your draft is retained. ${exploreButton("Save as new workspace", "save-copy")}${exploreButton("Open saved version", "open-saved", `data-id="${workspace.id}"`)}</div>` : ""}
    ${explore.libraryChanges?.length && !explore.capture ? `<p class="explore-revisions">Library definitions changed. Retained queries remain pinned: ${explore.libraryChanges.map(change => `${esc(exploreItemLabel(workspace.collection.find(item => item.id === change.collection_id)))} r${change.retained_revision} / ${change.current_revision == null ? "deleted from Library" : `Library r${change.current_revision}`}`).join("; ")}. Adopt revisions explicitly in the collection.</p>` : ""}
    <div class="explore-context">${exploreInput("Workspace name", "workspace_name", workspace.name)}${exploreInput("Workspace as-of", "workspace_as_of", workspace.as_of, "date")}${explore.capture ? "" : `${exploreSelect("Add view", "new_family", "history", Object.entries(exploreFamilies))}${exploreButton("Add view", "add-view")}${exploreSelect("Saved workspaces", "saved_workspace", "", [["", "Choose workspace"], ...explore.saved.map(record => [record.id || record.workspace?.id, record.name || record.workspace?.name])])}${exploreButton("Open", "open")}`}</div>
    <div class="explore-capture-bar">${explore.capture ? `<span>Captured: ${esc(explore.capture.captured_at || explore.capture.created_at || "")}</span><a class="button" href="${explore.capture.export_url || `/api/explore/captures/${explore.capture.idea_id}/${explore.capture.id}/export`}">Export evidence ZIP</a>` : `<input id="explore-capture-title" placeholder="Capture title" aria-label="Capture title" value="${esc(workspace.name)}"><select id="explore-capture-idea" aria-label="Idea destination"><option value="">New Idea</option>${(state.exploreIdeas || []).map(record => `<option value="${record.idea?.id || record.id}">${esc(record.idea?.title || record.title)}</option>`).join("")}</select><select id="explore-capture-role" aria-label="Evidence role"><option value="contextual">Contextual</option><option value="supporting">Supporting</option><option value="challenging">Challenging</option></select>${exploreButton("Capture selected views", "capture", explore.status === "current" ? "" : "disabled")}${exploreButton("Select all views", "check-all")}`}${exploreButton("Export selected PNGs", "export-png")}${exploreButton("Clear highlight", "clear-highlight", 'class="quiet"')}</div>
    <div class="explore-layout ${workspace.layout}">${exploreCollectionHTML()}<div class="explore-canvas">${workspace.layout === "focus" ? `<div class="explore-filmstrip" aria-label="Views">${visibleViews.map(view => exploreButton(esc(view.name), "select", `data-id="${view.id}" aria-pressed="${view.id === explore.selected}"`)).join("")}</div>` : ""}<div class="explore-grid">${visibleViews.map(exploreViewHTML).join("") || '<section class="explore-view wide"><h2>Build an investigation</h2><p class="empty">Add Library entries to the collection, associate fields with symbols, then add a view.</p></section>'}</div></div>${exploreEditorHTML()}</div>
    <details class="explore-research" ${workspace.question || workspace.notes ? "open" : ""}><summary>Working question and notes</summary><div class="fields"><label>Working question<textarea id="explore-question" maxlength="10000" ${explore.capture ? "readonly" : ""}>${esc(workspace.question)}</textarea></label><label>Notes<textarea id="explore-notes" ${explore.capture ? "readonly" : ""}>${esc(workspace.notes)}</textarea></label></div></details>`;
  if (explore.capture) document.querySelectorAll('.explore-context input').forEach(input => input.disabled = true);
  main.querySelectorAll("details").forEach(details => { if (opened.has(details.querySelector("summary")?.textContent)) details.open = true; });
  if (focusSelector) main.querySelector(focusSelector)?.focus({preventScroll: true});
  if (main.querySelector(".explore-editor")) main.querySelector(".explore-editor").scrollTop = editorScroll;
  exploreRenderPlots();
}
async function exploreRenderPlots() {
  const sequence = explore.sequence;
  for (const view of explore.workspace.views) {
    const result = explore.results.get(view.id), plot = document.querySelector(`#explore-plot-${view.id}`);
    if (!result || !plot || explore.workspace.layout === "focus" && view.id !== explore.selected) continue;
    const statistics = result.statistics || {}, chart = exploreChartData(result.view || view, result), traces = chart.traces;
    if (!traces.length || !result.rows.length) { plot.innerHTML = '<p class="empty">No available values for this sample. Inspect limitations and excluded rows.</p>'; continue; }
    plot.innerHTML = "";
    await Plotly.newPlot(plot, traces, chart.layout, {responsive: true, displaylogo: false, modeBarButtonsToRemove: ["sendDataToCloud"]});
    if (sequence !== explore.sequence) return;
    plot.on("plotly_click", event => explorePlotClick(result.view || view, result, event));
  }
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
  return {traces, layout};
}
function explorePlotClick(view, result, event) {
  const point = event.points?.[0]; if (!point) return;
  if (view.family === "correlation" && !explore.capture) {
    if (explore.status !== "current") { notify("Preview the current draft before drilling into a correlation cell."); return; }
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
    exploreDirty("Exact correlation sample retained. Preview the paired scatter."); exploreRender(); return;
  }
  const datum = point.customdata;
  explore.highlighted = [datum?.symbol || datum?.[1] || (typeof datum === "string" ? datum : point.data.name)];
  if (!explore.capture) { explore.workspace.views.forEach(view => view.highlight = [...explore.highlighted]); exploreDirty("Highlight changed; sample unchanged. Preview before capturing."); }
  exploreRenderPlots();
}
function exploreReadView(form, changedControl) {
  const view = exploreCurrentView(), data = new FormData(form), oldShape = view.shape;
  view.name = data.get("name"); view.family = data.get("family"); view.shape = data.get("shape"); view.measures = data.getAll("measures");
  for (const name of ["as_of", "display_start", "display_end", "size_by", "color_by", "facet_by"]) view[name] = data.get(name) || null;
  view.pinned = data.has("pinned");
  if (view.pinned && !view.as_of) view.as_of = explore.workspace.as_of || explore.results.get(view.id)?.as_of || new Date().toISOString().slice(0, 10);
  for (const name of ["start", "end", "interval_start"]) view.sample[name] = data.get(name) || null;
  view.sample.date_policy = data.get("date_policy"); view.sample.maximum_age_days = Number(data.get("maximum_age_days") || 0);
  view.sample.interval_measure = data.get("interval_measure") || "level";
  const members = data.getAll("members"), all = new Set(explore.workspace.collection.map(item => item.symbol));
  view.sample.members = members.length === all.size ? null : members;
  const axes = exploreFields(view), x = data.get("x"), y = data.get("y"), axis = data.get("axis");
  view.options.x = axes.includes(x) ? x : axes[0]; view.options.y = axes.includes(y) && oldShape === view.shape ? y : axes[1];
  view.options.axes = ["scatter"].includes(view.family) ? [view.options.x, view.options.y].filter(Boolean) : axis && axes.includes(axis) && !["heatmap", "correlation"].includes(view.family) ? [axis] : axes;
  for (const name of ["distribution", "heatmap_layout", "correlation_orientation", "correlation_method", "correlation_sample", "group_by", "weight_policy", "history_layout"]) if (data.has(name)) view.options[name] = data.get(name);
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
async function explorePreview() {
  const sequence = ++explore.sequence;
  explore.status = "previewing"; exploreRender();
  try {
    const response = await api("/api/explore/preview", "POST", {workspace: structuredClone(explore.workspace)});
    if (sequence !== explore.sequence) return;
    explore.workspace = response.workspace || explore.workspace;
    explore.results = new Map((response.resolved_results || response.results || []).map(result => [result.view_id, result]));
    explore.status = "current"; exploreRender();
  } catch (error) {
    if (sequence !== explore.sequence) return;
    explore.status = "failed"; exploreRender(); notify(error.message);
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
  explore.selected = explore.workspace.views[0]?.id; explore.checked = new Set(explore.workspace.views.map(view => view.id));
  history.replaceState(null, "", `/explore/${id}`); exploreRender();
}
async function exploreCapture() {
  if (explore.status !== "current") throw Error("Preview the current draft before capturing.");
  const sequence = explore.sequence, workspace = structuredClone(explore.workspace), views = workspace.views.filter(view => explore.checked.has(view.id));
  if (!views.length) throw Error("Select at least one view to capture.");
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
  const selector = focused?.dataset.risk ? `[data-risk="${focused.dataset.risk}"][data-leg="${focused.dataset.leg}"]` : focused?.name ? `[name="${CSS.escape(focused.name)}"]` : null;
  const content = `<h2>Local Analysis</h2><p class="meta">Inputs → measure → scaling → comparison → historical context. Library save is explicit; monitoring stays disabled.</p><form id="explore-analysis-form">${exploreInput("Name", "name", draft.name)}<label>Economic rationale<textarea name="economic_rationale" maxlength="10000">${esc(draft.economic_rationale)}</textarea></label>${analysisControls(draft, [], exploreAnalysisContext())}<div class="actions">${exploreButton("Apply local Analysis", "apply-analysis", 'class="primary"')}${exploreButton("Stage new series", "stage-series")}${exploreButton("Save to Library", "save-analysis-library")}${exploreButton("Cancel", "close-dialog")}</div></form>`;
  if (old) old.innerHTML = content; else exploreDialog(content);
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
  const content = libraryEditor().replace('id="library-form"', 'id="explore-series-form"').replace(/<div class="actions">[\s\S]*?<\/div>(?=<\/form>)/, `<div class="actions">${exploreButton("Preview series", "preview-series")}${exploreButton(staged ? "Stage series" : "Save to Library and add", "apply-series", 'class="primary"')}${exploreButton("Cancel", "close-dialog")}</div>`);
  state.draft = previousDraft; state.libraryTab = previousTab;
  exploreDialog(content + '<p id="explore-series-status" role="status"></p>');
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
  if (!librarySave) notify("Local Analysis applied. Preview to update views.");
}
document.addEventListener("input", event => {
  if (page !== "explore" || explore.capture) return;
  const control = event.target;
  if (control.id === "explore-library-search") {
    explore.libraryQuery = control.value;
    document.querySelectorAll(".explore-library-row").forEach(row => row.hidden = !row.textContent.toLowerCase().includes(control.value.toLowerCase())); return;
  }
  if (["explore-question", "explore-notes"].includes(control.id)) { explore.workspace[control.id === "explore-question" ? "question" : "notes"] = control.value; exploreDirty(); }
  if (control.name === "workspace_name") { explore.workspace.name = control.value; exploreDirty(); }
  if (control.dataset.association) { explore.workspace.collection.find(item => item.id === control.dataset.id)[control.dataset.association] = control.value; exploreDirty(); }
  if (control.closest("#explore-analysis-form")) readAnalysisControls(control.form, explore.analysisDraft, exploreAnalysisContext());
});
document.addEventListener("change", event => {
  if (page !== "explore") return;
  const control = event.target;
  if (control.dataset.captureView) { control.checked ? explore.checked.add(control.dataset.captureView) : explore.checked.delete(control.dataset.captureView); return; }
  if (explore.capture) return;
  if (control.name === "workspace_as_of") { explore.workspace.as_of = control.value || null; exploreDirty(); }
  if (control.closest("#explore-view-form")) {
    exploreReadView(control.form, control.name);
    if (control.tagName === "SELECT" || ["measures", "pinned"].includes(control.name)) exploreRender();
  }
  if (control.closest("#explore-analysis-form")) {
    readAnalysisControls(control.form, explore.analysisDraft, exploreAnalysisContext());
    if (control.tagName === "SELECT" || control.hasAttribute("data-risk-customize")) exploreReplaceAnalysisDialog();
  }
  if (control.closest("#explore-series-form") && control.name === "provider") { explore.seriesDraft = readSeriesDraft(control.form, explore.seriesDraft); exploreReplaceSeriesDialog(); }
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
    else if (action === "preview") await explorePreview();
    else if (action === "save" || action === "save-copy") await exploreSave(action === "save-copy");
    else if (action === "open" || action === "open-saved") await exploreOpen(button.dataset.id || document.querySelector('[name="saved_workspace"]').value);
    else if (action === "new") { explore.workspace = exploreNewWorkspace(); explore.results.clear(); explore.selected = null; exploreDirty(); history.replaceState(null, "", "/explore"); exploreRender(); }
    else if (action === "capture") await exploreCapture();
    else if (action === "export-png") await exploreExportPNGs();
    else if (action === "copy-png") { const plot = document.querySelector(`#explore-plot-${button.dataset.id}`); if (!plot?.data) throw Error("Preview this chart before copying.");
      const dataURL = await Plotly.toImage(plot, {format: "png", width: 1400, height: 850}), blob = await (await fetch(dataURL)).blob();
      await navigator.clipboard.write([new ClipboardItem({"image/png": blob})]); notify("Chart PNG copied."); }
    else if (action === "check-all") { explore.checked = new Set(explore.workspace.views.map(view => view.id)); exploreRender(); }
    else if (action === "clear-highlight") { explore.highlighted = []; if (!explore.capture) { explore.workspace.views.forEach(view => view.highlight = []); exploreDirty(); } exploreRenderPlots(); }
    else if (action === "fork") { explore.workspace = structuredClone(explore.workspace); explore.workspace.id = exploreID(); explore.workspace.version = null; explore.workspace.name += " (fork)"; explore.capture = null; exploreDirty(); history.replaceState(null, "", "/explore"); exploreRender(); }
    else if (action === "new-analysis" || action === "edit-analysis") exploreAnalysisDialog(explore.workspace.collection.find(item => item.id === button.dataset.id));
    else if (action === "new-series" || action === "stage-series") exploreSeriesDialog(action === "stage-series");
    else if (action === "attributes") exploreDialog(`<h2>Supplied attributes</h2><p class="meta">Enter explicit symbol assignments with source and optional effective dates. Historical use of undated labels remains current/static.</p><label>Attribute records (JSON)<textarea id="explore-attributes" rows="12" spellcheck="false">${esc(JSON.stringify(explore.workspace.attributes, null, 2))}</textarea></label><p class="meta">Each record: symbol, name, value, source, effective_start, effective_end.</p><div class="actions">${exploreButton("Apply attributes", "apply-attributes", 'class="primary"')}${exploreButton("Cancel", "close-dialog")}</div>`);
    else if (action === "apply-attributes") { const attributes = JSON.parse(document.querySelector("#explore-attributes").value); if (!Array.isArray(attributes)) throw Error("Supply an array of attribute records.");
      if (attributes.some(attribute => !attribute.symbol || !attribute.name || !attribute.source || typeof attribute.value !== "string")) throw Error("Each attribute needs symbol, name, string value and source.");
      explore.workspace.attributes = attributes; document.querySelector("#explore-dialog").close(); exploreDirty(); exploreRender(); }
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
    const responses = await Promise.allSettled([api("/api/explore/library"), api("/api/explore/workspaces"), api("/api/ideas")]);
    if (responses[0].status === "rejected") throw responses[0].reason;
    state.catalogue = responses[0].value;
    explore.saved = responses[1].status === "fulfilled" ? responses[1].value.workspaces || responses[1].value : [];
    state.exploreIdeas = responses[2].status === "fulfilled" ? responses[2].value.ideas || responses[2].value : [];
    explore.workspace = exploreNewWorkspace();
    if (segments[1]) { const response = await api(`/api/explore/workspaces/${segments[1]}`); explore.workspace = response.workspace || response; explore.libraryChanges = response.library_changes || []; }
  }
  const visible = exploreVisibleViews(); explore.selected = visible[0]?.id; explore.checked = new Set(visible.map(view => view.id)); exploreRender();
}
window.exploreWorkspace = explore;
exploreStart().catch(error => { main.innerHTML = `<h1>Unable to load Explore</h1><p class="warning">${esc(error.message)}</p><a href="${esc(location.pathname)}">Retry</a>`; });
