const main = document.querySelector("main"),
  page = document.body.dataset.page;
const key = location.pathname.split("/")[2],
  target = new URLSearchParams(location.search).get("target");
let state = {},
  timer,
  querySequence = 0;
document.addEventListener("chart-display-change", event => {
  if (event.target.id === "plot") state.display = event.detail;
});
function notify(message) {
  const box = document.querySelector("#message");
  box.textContent = message;
  box.classList.add("visible");
  clearTimeout(timer);
  timer = setTimeout(() => box.classList.remove("visible"), 12000);
}
async function api(path, method = "GET", body) {
  const response = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body == null ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    let error;
    try {
      error = await response.json();
    } catch {
      error = { detail: "Request failed; retry." };
    }
    throw Error(
      typeof error.detail === "string"
        ? error.detail
        : JSON.stringify(error.detail),
    );
  }
  return response.headers.get("Content-Type")?.includes("application/json")
    ? response.json()
    : response.blob();
}
function actions(items) {
  return `<div class="actions">${items}</div>`;
}
function button(label, action, extra = "") {
  return `<button type="button" data-action="${action}" ${extra}>${label}</button>`;
}
function params() {
  return Object.fromEntries(new FormData(document.querySelector("form")));
}
function listContext() {
  try {
    return (
      JSON.parse(sessionStorage.getItem("analyses-context")) || {
        scope: "flagged",
        q: "",
        kind: "all",
        scroll: 0,
      }
    );
  } catch {
    return { scope: "flagged", q: "", kind: "all", scroll: 0 };
  }
}
function persistContext() {
  sessionStorage.setItem(
    "analyses-context",
    JSON.stringify({ ...state.list, scroll: window.scrollY }),
  );
}
function analysisLink(id) {
  return `/analyses/${encodeURIComponent(id)}${target ? "?target=" + encodeURIComponent(target) : ""}`;
}
function toolbar() {
  return `<div class="toolbar">${button("Flagged", "scope", 'data-scope="flagged" aria-pressed="' + (state.list.scope === "flagged") + '"')}${button("All", "scope", 'data-scope="all" aria-pressed="' + (state.list.scope === "all") + '"')}<input type="search" id="search" aria-label="Search analyses" placeholder="Search all analyses" value="${esc(state.list.q)}"><label class="type"><span class="meta">Analysis type</span> <select id="kind" aria-label="Analysis type"><option value="all">All types</option><option value="standalone">Standalone</option><option value="pair">Pair</option></select></label>${button("Refresh", "refresh")}</div>`;
}
async function analyses() {
  state.list = listContext();
  main.innerHTML = `<h1>Analyses</h1><p class="intro">Review flagged developments or search all analyses.</p>${target ? `<p class="status">Select another chart for your Idea. <a href="/ideas/${encodeURIComponent(target)}">Return to Idea</a></p>` : ""}${toolbar()}<div id="rows"></div>`;
  document.querySelector("#kind").value = state.list.kind;
  document.querySelector("#search").addEventListener("input", (e) => {
    state.list.q = e.target.value;
    if (e.target.value) state.list.scope = "all";
    persistContext();
    loadRows().catch((err) => notify(err.message));
  });
  document.querySelector("#kind").addEventListener("change", (e) => {
    state.list.kind = e.target.value;
    persistContext();
    loadRows().catch((err) => notify(err.message));
  });
  await loadRows();
  window.scrollTo(0, state.list.scroll || 0);
}
async function loadRows() {
  const seq = ++querySequence;
  const result = await api("/api/analyses?" + new URLSearchParams(state.list));
  if (seq !== querySequence) return;
  document
    .querySelectorAll("[data-action=scope]")
    .forEach((b) =>
      b.setAttribute("aria-pressed", b.dataset.scope === state.list.scope),
    );
  const rows = result.rows;
  document.querySelector("#rows").innerHTML =
    `<div class="table-region" role="region" aria-label="Analyses table" tabindex="0"><table><thead><tr><th>Analysis</th><th>Current</th><th>Change</th><th>Historical standing</th><th>Observation</th></tr></thead><tbody>${rows
      .map((r) => {
        const e = r.evaluation;
        return `<tr><td><a href="${analysisLink(r.analysis.id)}">${esc(r.analysis.name)}</a><small>${r.analysis.calculation === "level" ? "Standalone" : esc(r.analysis.calculation)} · ${esc(e?.definition.inputs.map((s) => s.source + " / " + (s.field || s.instrument)).join(" · ") || "Not evaluated")}</small>${e?.reasons.length ? `<small>${esc(e.reasons.join(" · "))}</small>` : ""}${r.failure ? `<small class="warning">Retained result: ${esc(r.failure)}</small>` : ""}${!r.compatible && e ? "<small>Definition changed. Refresh to evaluate; previous result is retained.</small>" : ""}${e && !e.eligible ? `<small>${esc(e.limitations.join(" · "))}</small>` : ""}</td><td>${number(e?.current, e?.unit)}</td><td>${number(e?.change, e?.unit, true)}<small>/ ${esc(r.analysis.settings.horizon)}</small></td><td>${e?.percentile == null ? "Unavailable" : e.percentile.toFixed(1) + "th percentile"}<small>/ ${periodText(r.analysis.settings.history_years)}</small></td><td>${dateText(e?.observation_date)}</td></tr>`;
      })
      .join(
        "",
      )}</tbody></table>${rows.length ? "" : '<p class="empty">No matching analyses. Choose All, clear search or broaden the type filter.</p>'}</div><p class="status">${rows.length} analyses · ${result.refresh.running ? "Refreshing; dated results retained" : result.refresh.completed_at ? "Retrieval attempted " + stamp(result.refresh.completed_at) : "Not refreshed"}</p><details><summary>Flag criteria</summary><p class="meta">Configured level and move thresholds in analysis units; current-excluded historical midrank. New threshold entries and material further moves come first. Unchanged extremes remain in All. Demo calibration is illustrative; risk-adjusted thresholds require separate calibration.</p></details>`;
  if (result.refresh.running)
    setTimeout(() => loadRows().catch((err) => notify(err.message)), 500);
}
const periodYears = [.25, .5, 1, 2, 3, 5, 7, 10, 15, 20, 30];
function periodChoices(current) {
  return [...new Set([...periodYears, ...(current === "all" ? [] : [current])])].sort((a, b) => a - b).concat("all");
}
function supportsZScore(definition) {
  return ["difference", "regression"].includes(definition.calculation) || definition.calculation === "level" && (definition.settings.measure || "level") !== "level";
}
function standardizationControls(definition, library = false) {
  if (!supportsZScore(definition)) return "";
  const settings = definition.settings;
  const zscore = settings.standardization === "zscore";
  return `<label>Standardization<select ${library ? 'name="standardization"' : 'data-setting="standardization"'}><option value="none" ${!zscore ? "selected" : ""}>None</option><option value="zscore" ${zscore ? "selected" : ""}>Z-score</option></select></label>${zscore ? `<label>Z-score threshold (±)<input type="number" ${library ? 'name="z_threshold"' : 'data-setting="zscore_threshold"'} value="${settings.zscore_threshold ?? 2}" min="0.000001" step="any" required></label>` : ""}`;
}
function analysisCaption(e) {
  if (e.definition.settings.standardization !== "zscore") return e.definition.calculation;
  return ({difference: "Difference", regression: "Regression residual"}[e.definition.calculation] || (e.definition.settings.measure === "return" ? "Percentage change" : "Change")) + " Z-score";
}
function chartControls(e, display) {
  return `<div class="controls"><label>Display range<select data-display="years">${[1, 3, 5].map((n) => `<option value="${n}" ${n === display.years ? "selected" : ""}>${n} years</option>`).join("")}</select></label><label>Reference history<select data-setting="history_years">${periodChoices(e.definition.settings.history_years).map((n) => `<option value="${n}" ${n === e.definition.settings.history_years ? "selected" : ""}>${periodText(n)}</option>`).join("")}</select></label><label>Measure<select data-setting="measure">${[["level", "Level"], ["change", "Change"], ["return", "Percentage change"]].map(([v, label]) => `<option value="${v}" ${v === e.definition.settings.measure ? "selected" : ""}>${label}</option>`).join("")}</select></label><label>Frequency<select data-setting="horizon">${["day", "week", "month"].map((n) => `<option ${n === e.definition.settings.horizon ? "selected" : ""}>${n}</option>`).join("")}</select></label>${e.definition.calculation === "regression" ? `<label>Fitting window<select data-setting="fit_years">${periodChoices(e.definition.settings.fit_years).map((n) => `<option value="${n}" ${n === e.definition.settings.fit_years ? "selected" : ""}>${periodText(n)}</option>`).join("")}</select></label>` : ""}${standardizationControls(e.definition)}<label>Chart view<select data-display="view"><option value="analysis" ${display.view === "analysis" ? "selected" : ""}>Analysis</option>${e.definition.settings.measure !== "level" ? `<option value="changes" ${display.view === "changes" ? "selected" : ""}>Measured / adjusted series</option>` : ""}<option value="underlying" ${display.view === "underlying" ? "selected" : ""}>Underlying series</option>${e.definition.calculation === "regression" ? `<option value="scatter" ${display.view === "scatter" ? "selected" : ""}>Regression scatter</option>` : ""}</select></label></div>`;
}
function metrics(e) {
  return `<div class="metric-strip"><div><strong>${number(e.current, e.unit)}</strong><small>Current · ${dateText(e.observation_date)}</small></div><div><strong>${number(e.change, e.unit, true)}</strong><small>${esc(e.definition.settings.horizon)} · from ${dateText(e.change_start)}</small></div><div><strong>${e.percentile == null ? "Unavailable" : e.percentile.toFixed(1) + "th"}</strong><small>Percentile · ${periodText(e.definition.settings.history_years)} reference</small></div></div>`;
}
const defaultRisk = () => ({method: "none", reference_id: null, lookback_years: 3, weighting: "equal", half_life: 63, confidence: 95, downside: "increase", minimum_samples: 60});
function riskOptions(settings, count) {
  return settings.risk_overrides?.length ? settings.risk_overrides : Array.from({length: count}, () => settings.risk_adjustment || defaultRisk());
}
function riskFields(risk, index) {
  const select = (label, name, values) => `<label>${label}<select data-risk="${name}" data-leg="${index}">${values.map(([v, text]) => `<option value="${v}" ${String(risk[name] ?? "") === String(v) ? "selected" : ""}>${esc(text)}</option>`).join("")}</select></label>`;
  const numeric = (label, name, min, max) => `<label>${label}<input type="number" data-risk="${name}" data-leg="${index}" value="${risk[name]}" min="${min}" max="${max}" step="any" required></label>`;
  return `<div class="risk-fields">${select("Reference series", "reference_id", [["", index === "shared" ? "Each series itself" : "This series itself"], ...librarySeriesChoices().map(s => [s.id, s.name])])}${select("Adjustment method", "method", Object.entries(riskMethodNames))}${risk.method !== "none" ? `<div class="risk-calibration">${select("Estimation period", "lookback_years", periodChoices(risk.lookback_years).map(n => [n, periodText(n)]))}${risk.method === "volatility" ? select("Weighting", "weighting", [["equal", "Equal"], ["exponential", "Exponential"]]) + (risk.weighting === "exponential" ? numeric("Half-life (sessions)", "half_life", 1, 2520) : "") : ""}${["var", "es"].includes(risk.method) ? numeric("Confidence (%)", "confidence", 50.01, 99.99) + select("Downside", "downside", [["increase", "Increasing values"], ["decrease", "Decreasing values"]]) : ""}</div>` : ""}</div>`;
}
function riskEditor(settings, inputs, estimates = []) {
  const customized = !!settings.risk_overrides?.length;
  return `<div class="risk-editor">${inputs.length > 1 ? `<label class="risk-customize"><input type="checkbox" data-risk-customize ${customized ? "checked" : ""}> Customize per series</label>` : ""}${customized ? riskOptions(settings, inputs.length).map((r, i) => `<fieldset><legend>${esc(inputs[i]?.name || "Series " + (i+1))}</legend>${riskFields(r, i)}</fieldset>`).join("") : riskFields(settings.risk_adjustment || defaultRisk(), "shared")}${estimates.map((r, i) => `<p class="meta risk-estimate"><strong>${esc(inputs[i].name)}</strong><br>${riskOptions(settings, inputs.length)[i].method === "none" ? "Unadjusted" : `Scale: ${number(r.scale)} · ${r.sample_count} observations`}${r.limitation ? `<br>${esc(r.limitation)}` : ""}</p>`).join("")}</div>`;
}
function renderRiskPanel() {
  const e = state.evaluation;
  document.querySelector("#risk-panel").innerHTML = `<h2>Risk adjustment</h2><p class="meta">Applied to each series before comparison. Estimates use the selected Frequency.</p>${riskEditor(e.definition.settings, e.definition.inputs, e.adjustment_estimates || [])}<p class="meta">Estimates exclude the measured interval. ${["var", "es"].some(m => riskOptions(e.definition.settings, e.definition.inputs.length).some(r => r.method === m)) ? "Downside is defined by the direction selected above." : ""}</p>${button("Reset to defaults", "risk-reset", 'class="quiet"')}<p class="settings-label">${JSON.stringify(e.definition.settings) === JSON.stringify(state.savedSettings) ? "Using saved Analysis defaults." : "Exploratory settings."} <a data-action="edit-defaults" href="/library?edit=${encodeURIComponent(key)}">Edit defaults in Library</a></p>`;
}
async function previewSettings(options) {
  const focused = document.activeElement;
  const focusSelector = focused.dataset.risk ? `[data-risk="${focused.dataset.risk}"][data-leg="${focused.dataset.leg}"]` : focused.dataset.setting ? `[data-setting="${focused.dataset.setting}"]` : focused.hasAttribute("data-risk-customize") ? "[data-risk-customize]" : null;
  const controls = document.querySelectorAll("[data-setting], [data-risk], [data-risk-customize], [data-action=risk-reset], [data-display]");
  controls.forEach(c => c.disabled = true);
  document.querySelector("#risk-panel").insertAdjacentHTML("beforeend", '<p class="meta" role="status">Calculating risk estimates…</p>');
  state.previewPromise = (async () => {
    const evaluation = await api(`/api/analyses/${key}/preview`, "POST", options);
    delete state.display.axis_ranges;
    state.evaluation = evaluation;
    document.querySelector(".chart-heading small").textContent = `${analysisCaption(evaluation)} · ${evaluation.unit} · ${dateText(evaluation.observation_date)}`;
    if (evaluation.definition.settings.measure === "level" && state.display.view === "changes") state.display.view = "analysis";
    document.querySelector(".metric-strip").outerHTML = metrics(evaluation);
    document.querySelector("#investigation-controls").innerHTML = chartControls(evaluation, state.display);
    document.querySelector("#plot").nextElementSibling.outerHTML = evidenceDetails(evaluation, "", state.display);
    renderRiskPanel();
    await plotEvidence(document.querySelector("#plot"), evaluation, state.display);
  })();
  try { await state.previewPromise; }
  finally {
    document.querySelectorAll("[data-setting], [data-risk], [data-risk-customize], [data-action=risk-reset], [data-display]").forEach(c => c.disabled = false);
    // A failed preview leaves the last accepted settings visible and saveable.
    document.querySelector("#investigation-controls").innerHTML = chartControls(state.evaluation, state.display);
    renderRiskPanel();
    state.previewPromise = null;
    if (focusSelector) document.querySelector(focusSelector)?.focus();
  }
}
async function chart() {
  state.display = { years: 3, view: "analysis" };
  state.evaluation = await api(`/api/analyses/${key}/preview`, "POST", {});
  state.savedSettings = structuredClone(state.evaluation.definition.settings);
  state.catalogue = await api("/api/library");
  if (state.evaluation.definition.settings.measure !== "level" && state.evaluation.definition.settings.standardization !== "zscore") state.display.view = "changes";
  renderChart();
  await plotEvidence(
    document.querySelector("#plot"),
    state.evaluation,
    state.display,
  );
}
function renderChart() {
  const e = state.evaluation;
  main.innerHTML = `<div class="workspace risk-workspace" id="workspace"><section class="paper"><div class="chart-heading"><div><h1>${esc(e.definition.name)}</h1><small>${esc(analysisCaption(e))} · ${esc(e.unit)} · ${dateText(e.observation_date)}</small></div>${actions(button("Save to Idea", "open-save", 'class="primary"') + button("Copy chart", "chart-copy") + button("Download chart", "chart-download"))}</div>${metrics(e)}<div id="investigation-controls">${chartControls(e, state.display)}</div><div class="plot" id="plot" role="img" aria-label="${esc(e.definition.name)} chart"></div>${evidenceDetails(e, "", state.display)}</section><div class="investigation-sidebar"><aside id="risk-panel" class="paper"></aside><aside id="save-panel" class="paper save-panel" hidden></aside></div></div>`;
  renderRiskPanel();
}
async function openSave() {
  await state.previewPromise;
  state.saveIdeas = await api("/api/ideas");
  if (target && !state.saveIdeas.some((x) => x.idea.id === target)) {
    const existing = await api(`/api/ideas/${encodeURIComponent(target)}`);
    state.saveIdeas.push({ idea: existing.idea });
  }
  const aside = document.querySelector("#save-panel");
  aside.innerHTML = `<h2>Save to Idea</h2><form id="save-form"><label>Destination<select name="idea_id" id="save-destination" aria-label="Destination"><option value="">New Idea</option>${state.saveIdeas.map((x) => `<option value="${x.idea.id}" ${x.idea.id === target ? "selected" : ""}>${esc(x.idea.title)}</option>`).join("")}</select></label><div id="new-idea-fields"><label>Title<input name="title" maxlength="200" required></label><label>Thought (optional)<textarea name="thought" rows="4"></textarea></label></div><div id="existing-idea-fields" hidden><label>Chart note (optional)<textarea name="note" rows="4"></textarea></label></div>${actions('<button class="primary" type="submit">Save chart</button>' + button("Cancel", "cancel-save"))}</form>`;
  aside.hidden = false;
  document.querySelector("#workspace").classList.add("saving");
  const select = document.querySelector("#save-destination");
  select.addEventListener("change", updateDestination);
  updateDestination();
  document
    .querySelector(select.value ? "textarea[name=note]" : "input[name=title]")
    .focus();
  await plotEvidence(
    document.querySelector("#plot"),
    state.evaluation,
    state.display,
  );
}
function updateDestination() {
  const existing = !!document.querySelector("#save-destination").value;
  document.querySelector("#new-idea-fields").hidden = existing;
  document.querySelector("#existing-idea-fields").hidden = !existing;
  document.querySelector("input[name=title]").required = !existing;
}
async function ideas() {
  state.ideaScope = "active";
  main.innerHTML = `<h1>Ideas</h1><p class="intro">Saved evidence and unfinished views for discussion.</p><div class="toolbar">${["active", "shortlist", "archived"].map((s) => button({ active: "Active", shortlist: "Shortlist", archived: "Archived" }[s], "idea-scope", `data-scope="${s}" aria-pressed="${s === "active"}"`)).join("")}<input type="search" aria-label="Search Ideas" id="idea-search" placeholder="Search Ideas"></div><div class="idea-list" id="idea-list"></div>`;
  document
    .querySelector("#idea-search")
    .addEventListener("input", () =>
      loadIdeas().catch((e) => notify(e.message)),
    );
  await loadIdeas();
}
async function loadIdeas() {
  const records = await api(
    "/api/ideas?" +
      new URLSearchParams({
        scope: state.ideaScope,
        q: document.querySelector("#idea-search").value,
      }),
  );
  document.querySelector("#idea-list").innerHTML =
    records
      .map(
        ({ idea, changes }) =>
          `<article class="paper"><h2><a href="/ideas/${idea.id}">${esc(idea.title)}</a></h2><p class="prose">${esc(idea.thought)}</p><p class="meta">${idea.charts.length} saved charts · ${idea.shortlisted ? "Shortlisted · " : ""}${idea.archived ? "Archived · " : ""}Updated ${stamp(idea.modified_at)}</p><div class="changes">${changes.map((c) => `<a href="/ideas/${idea.id}#chart-${c.chart_id}">${esc(c.name)} · ${esc(c.finding)} since ${dateText(c.since)}</a>`).join("")}</div></article>`,
      )
      .join("") ||
    '<p class="empty">No Ideas match. Save a chart from Analyses, or broaden search/archive selection.</p>';
}
function editor(formId, text, actionLabel = "Save changes", fields = "") {
  return `<form class="inline-editor" data-form="${formId}">${fields}<textarea name="text" aria-label="Note text" required>${esc(text)}</textarea>${actions(`<button type="submit" class="primary">${actionLabel}</button>` + button("Cancel", "cancel-editor"))}</form>`;
}
function chartNote(entry) {
  return `<div class="chart-note"><div class="chart-note-row">${entry.note ? `<p class="prose">${esc(entry.note)}</p>` : ""}<div class="chart-note-actions">${button(entry.note ? "Edit" : "Add note", "edit-chart-note", `class="quiet" aria-expanded="false" aria-controls="note-editor-${entry.id}"`)}${entry.note ? button("Delete", "delete-chart-note", `class="quiet" data-entry="${entry.id}"`) : ""}</div></div><div class="chart-note-editor" id="note-editor-${entry.id}" hidden>${editor("chart-note", entry.note, "Save changes", `<input type="hidden" name="entry_id" value="${entry.id}">`)}</div></div>`;
}
async function idea() {
  const result = await api(`/api/ideas/${key}`);
  state.idea = result.idea;
  state.snapshots = result.snapshots;
  state.latest = {};
  const i = state.idea;
  main.innerHTML = `<section class="idea-top"><h1>${esc(i.title)}</h1>${actions(`<a class="button primary" href="/analyses?target=${key}">Add another chart</a>` + button(i.shortlisted ? "Remove from shortlist" : "Shortlist", "shortlist", `aria-pressed="${i.shortlisted}"`) + button(i.archived ? "Restore" : "Archive", "archive"))}<p class="prose">${esc(i.thought)}</p><details><summary>Edit title / thought</summary><form data-form="idea-edit" class="inline-editor"><label>Title<input name="title" required maxlength="200" value="${esc(i.title)}"></label><label>Thought<textarea name="thought">${esc(i.thought)}</textarea></label>${actions('<button class="primary" type="submit">Save changes</button>' + button("Cancel", "cancel-editor"))}</form></details>${result.changes.length ? `<div class="changes">${result.changes.map((c) => `<a href="#chart-${c.chart_id}">${esc(c.name)} · ${esc(c.reasons.join(" · "))} · ${dateText(c.since)}–${dateText(c.to)}</a>`).join("")}</div>` : ""}${i.archived ? '<p class="meta">Archived</p>' : ""}</section>${i.charts
    .map((entry, index) => {
      const s = state.snapshots[entry.id],
        e = s.evaluation;
      return `<article class="paper saved-chart" id="chart-${entry.id}" data-entry="${entry.id}"><div class="chart-heading"><div><small>Chart ${index + 1} · Saved ${stamp(s.captured_at)}</small><h2>${esc(e.definition.name)}</h2></div>${actions(button("Copy data", "evidence-data", `data-entry="${entry.id}"`) + button("Copy chart", "evidence-copy", `data-entry="${entry.id}"`) + button("Download chart", "evidence-download", `data-entry="${entry.id}"`) + button("Remove chart", "remove-chart", `class="quiet" data-entry="${entry.id}"`))}</div><div class="controls">${button("Saved evidence", "evidence-mode", `data-entry="${entry.id}" data-mode="saved" aria-pressed="true"`)}${button("Latest data", "evidence-mode", `data-entry="${entry.id}" data-mode="latest" aria-pressed="false"`)}</div><div id="evidence-${entry.id}">${savedEvidence(entry.id, s)}</div>${chartNote(entry)}<div id="latest-status-${entry.id}" class="status"></div><footer class="chart-source" id="source-${entry.id}">${chartSource(e, s)}</footer></article>`;
    })
    .join(
      "",
    )}<section><h2 class="notes-heading">Idea notes</h2>${i.notes.map((n) => `<div><p class="prose">${esc(n.text)}</p><div class="note-actions"><time>${stamp(n.created_at)}</time><details><summary>Edit</summary>${editor("idea-note", n.text, "Save changes", `<input type="hidden" name="note_id" value="${n.id}">`)}</details>${button("Delete", "delete-idea-note", `data-note="${n.id}"`)}</div></div>`).join("")}<details><summary>Add Idea note</summary>${editor("add-idea-note", "", "Save note")}</details></section>`;
  if (location.hash) document.querySelector(location.hash)?.scrollIntoView();
  await renderSavedCharts();
}
function savedEvidence(entry, snapshot) {
  return `<div class="plot saved-plot" id="saved-${entry}" role="img" aria-label="${esc(snapshot.evaluation.definition.name)} saved chart"></div>`;
}
function chartSource(evaluation, snapshot) {
  return evidenceDetails(
    evaluation,
    `/api/ideas/${key}/snapshots/${snapshot.id}/image`,
    snapshot.display,
  );
}
async function renderSavedCharts() {
  if (page !== "idea" || !state.snapshots) return;
  for (const [entry, snapshot] of Object.entries(state.snapshots)) {
    if (state.latest[entry]) continue;
    const plot = document.querySelector(`#saved-${entry}`);
    if (plot && !plot.evidence)
      await plotEvidence(plot, snapshot.evaluation, snapshot.display);
  }
}
async function evidenceMode(entry, mode) {
  const card = document.querySelector(`#chart-${entry}`);
  if (mode === "saved") {
    const s = state.snapshots[entry];
    document.querySelector(`#evidence-${entry}`).innerHTML = savedEvidence(
      entry,
      s,
    );
    delete state.latest[entry];
    document.querySelector(`#source-${entry}`).innerHTML = chartSource(
      s.evaluation,
      s,
    );
    document.querySelector(`#latest-status-${entry}`).textContent = "";
    await renderSavedCharts();
  } else {
    const status = document.querySelector(`#latest-status-${entry}`);
    status.textContent = "Evaluating Latest with the saved definition…";
    const result = await api(
      `/api/ideas/${key}/charts/${entry}/latest`,
      "POST",
      {},
    );
    if (result.unavailable) {
      status.textContent =
        "Latest unavailable: " +
        result.unavailable +
        ". Saved evidence retained.";
      return;
    }
    state.latest[entry] = result.evaluation;
    document.querySelector(`#evidence-${entry}`).innerHTML =
      `<div class="plot" id="latest-${entry}" role="img" aria-label="Latest chart"></div>`;
    document.querySelector(`#source-${entry}`).innerHTML = chartSource(
      result.evaluation,
      state.snapshots[entry],
    );
    await plotEvidence(
      document.querySelector(`#latest-${entry}`),
      result.evaluation,
      {...state.snapshots[entry].display, axis_ranges: {}},
    );
    const saved = state.snapshots[entry].evaluation;
    status.textContent = `Latest observations ${dateText(result.evaluation.observation_date)}; saved ${dateText(saved.observation_date)}. Uses the preserved definition.`;
  }
  card
    .querySelectorAll("[data-action=evidence-mode]")
    .forEach((b) => b.setAttribute("aria-pressed", b.dataset.mode === mode));
}
async function captureEvidence(entry) {
  const saved = state.snapshots[entry],
    latest = state.latest[entry];
  const plot = document.querySelector(latest ? `#latest-${entry}` : `#saved-${entry}`);
  const image = await chartPNG(plot);
  return api(`/api/ideas/${key}/charts/${entry}/export`, "POST", {
    evaluation_id: (latest || saved.evaluation).id,
    display: plot.evidence.display,
    image,
    mode: latest ? "latest" : "saved",
  });
}
async function exportEvidence(entry, copy) {
  await reuseBlob(await captureEvidence(entry), copy);
}
async function copyEvidenceData(entry) {
  const plot = document.querySelector(`#chart-${entry} .plot`);
  await captureEvidence(entry);
  await copyData(plot);
}
async function library() {
  state.catalogue = await api("/api/library");
  state.libraryTab = "analyses";
  state.draft = null;
  const edit = new URLSearchParams(location.search).get("edit");
  if (edit)
    state.draft = structuredClone(
      state.catalogue.analyses.find((a) => a.id === edit),
    );
  try { state.exploratory = JSON.parse(sessionStorage.getItem("exploratory-" + edit)); } catch { state.exploratory = null; }
  resetLibraryPreview();
  renderLibrary();
}
function seriesOptions(selected) {
  return librarySeriesChoices()
    .map(
      (s) =>
        `<option value="${s.id}" ${s.id === selected ? "selected" : ""}>${esc(s.name)} · ${esc(s.unit)}</option>`,
    )
    .join("");
}
function newDraft(kind) {
  return kind === "series"
    ? {
        id: crypto.randomUUID().replaceAll("-", ""),
        revision: 1,
        name: "",
        source: "bloomberg",
        instrument: "",
        field: "PX_LAST",
        catalog_name: "",
        path: null,
        params: {},
        unit: "bp",
        currency: "USD",
      }
    : {
        id: crypto.randomUUID().replaceAll("-", ""),
        revision: 1,
        name: "",
        calculation: "level",
        series_ids: [state.catalogue.series[0]?.id],
        monitored: false,
        settings: {
          history_years: 3,
          fit_years: 3,
          horizon: "week",
          upper_percentile: 95,
          move_threshold: null,
          material_change: null,
          calibration: "demo-native-v1",
        },
      };
}
function readLibraryDraft() {
  const f = document.querySelector("#library-form");
  if (!f) return;
  const data = Object.fromEntries(new FormData(f));
  if (state.libraryTab === "series") {
    state.draft = readSeriesDraft(f, state.draft);
  } else
    state.draft = {
      ...state.draft,
      name: data.name,
      calculation: data.calculation,
      series_ids:
        data.calculation === "level" ? [data.left] : [data.left, data.right],
      monitored: f.elements.monitored.checked,
      settings: {
        ...state.draft.settings,
        history_years: periodValue(data.history),
        fit_years: periodValue(data.fit),
        horizon: data.horizon,
        measure: data.measure,
        standardization: data.standardization || "none",
        zscore_threshold: data.z_threshold ? Number(data.z_threshold) : state.draft.settings.zscore_threshold ?? 2,
        upper_percentile: data.upper ? Number(data.upper) : state.draft.settings.upper_percentile ?? 95,
        move_threshold: data.move ? Number(data.move) : null,
        material_change: data.material ? Number(data.material) : null,
      },
    };
}
function field(label, name, value, type = "text", required = true) {
  return `<label>${label}<input name="${name}" value="${esc(value ?? "")}" type="${type}" ${type === "number" ? 'step="any"' : ""} ${required ? "required" : ""}></label>`;
}
function monitoringCheckbox(analysis) {
  const pending = state.monitoringPending?.has(analysis.id);
  return `<label class="monitor"><input type="checkbox" data-monitoring="${esc(analysis.id)}" aria-label="Include ${esc(analysis.name)} in monitoring" ${analysis.monitored ? "checked" : ""} ${pending ? "disabled" : ""}><span>${pending ? "Saving…" : analysis.monitored ? "Included" : "Not monitored"}</span></label>`;
}
async function saveMonitoring(control) {
  const id = control.dataset.monitoring,
    analysis = state.catalogue.analyses.find(a => a.id === id),
    previous = analysis.monitored;
  state.monitoringPending ||= new Set();
  state.monitoringPending.add(id);
  control.disabled = true;
  const label = control.nextElementSibling;
  label.textContent = "Saving…";
  try {
    const saved = await api(`/api/library/analyses/${encodeURIComponent(id)}/monitoring`, "PATCH", {monitored: control.checked});
    state.catalogue.analyses = state.catalogue.analyses.map(a => a.id === id ? saved : a);
    if (state.draft?.id === id && state.libraryTab === "analyses") {
      state.draft.monitored = saved.monitored;
      document.querySelector('#library-form [name="monitored"]').checked = saved.monitored;
    }
    label.textContent = saved.monitored ? "Included" : "Not monitored";
    notify(`${saved.name}: ${saved.monitored ? "included in" : "removed from"} monitoring.`);
  } catch (error) {
    control.checked = previous;
    label.textContent = previous ? "Included" : "Not monitored";
    throw error;
  } finally {
    state.monitoringPending.delete(id);
    control.disabled = false;
    // Tab changes can replace the control while its save is in flight.
    if (!control.isConnected && !state.draft) renderLibrary();
  }
}
function renderLibrary() {
  const tab = state.libraryTab;
  if (state.draft && document.querySelector("#library-workspace")) {
    replaceLibraryEditor();
    return;
  }
  main.innerHTML = `<h1>Library</h1><p class="intro">Data series and defined analyses. Saving here changes future evaluations; older evidence keeps its definition.</p><div class="toolbar">${button("Analyses", "library-tab", 'data-tab="analyses" aria-pressed="' + (tab === "analyses") + '"')}${button("Data series", "library-tab", 'data-tab="series" aria-pressed="' + (tab === "series") + '"')}${button(tab === "series" ? "Add data series" : "Add analysis", "library-new", 'class="primary"')}</div>${state.draft ? libraryWorkspace(libraryEditor()) : `<div class="table-region" role="region" aria-label="Library ${tab}" tabindex="0"><table><thead><tr><th>Name</th><th>${tab === "series" ? "Source / symbol" : "Calculation / inputs"}</th><th>${tab === "series" ? "Units / currency" : "Monitoring"}</th><th>Actions</th></tr></thead><tbody>${state.catalogue[tab].map((r) => `<tr><td>${esc(r.name)}</td><td>${tab === "series" ? `${esc(r.source)} / ${esc(r.instrument)}${r.field ? " / " + esc(r.field) : ""}` : `${esc(r.calculation)}<small>${r.series_ids.map((id) => esc(state.catalogue.series.find((s) => s.id === id)?.name)).join(" / ")}</small>`}</td><td>${tab === "series" ? `${esc(r.unit)}<small>${esc(r.currency)}</small>` : monitoringCheckbox(r)}</td><td><div class="library-actions">${button("Edit", "library-edit", `data-id="${r.id}"`)}${button("Delete", "library-delete", `class="quiet" data-id="${r.id}"`)}</div></td></tr>`).join("")}</tbody></table>${state.catalogue[tab].length ? "" : '<p class="empty">No entries. Add a data series, then define an analysis.</p>'}</div>`}`;
}
function libraryEditor(d = state.draft, kind = state.libraryTab) {
  const series = kind === "series", pair = d.calculation !== "level";
  if (series) {
    const providers = [["bloomberg", "Bloomberg"], ["macrobond", "Macrobond"], ["localfile", "Local file"], ["custom", "Other registered source"]];
    const legacy = !d.catalog_name && state.catalogue.series.some(s => s.id === d.id);
    if (legacy && !providers.some(([v]) => v === d.source)) providers.unshift([d.source, d.source]);
    const provider = providers.some(([v]) => v === d.source) ? d.source : "custom";
    const local = provider === "localfile", macro = provider === "macrobond", custom = provider === "custom";
    return `<section class="paper editor"><h2>${state.catalogue.series.some(s => s.id === d.id) ? "Edit" : "Add"} data series</h2><form id="library-form"><div class="fields">${field("Name", "name", d.name)}<label>Source<select name="provider" aria-label="Source">${providers.map(([v, label]) => `<option value="${esc(v)}" ${provider === v ? "selected" : ""}>${esc(label)}</option>`).join("")}</select></label>${custom ? field("Registered source name", "custom_source", d.source === "custom" ? "" : d.source) : ""}${field(local ? "Column name" : macro ? "Series symbol" : "Symbol / ticker", "instrument", d.instrument)}${!local && !macro ? field("Field", "field", d.field, "text", !custom) : ""}${local || custom ? field("File path (absolute)", "path", d.path, "text", local) : ""}${field("Units", "unit", d.unit)}${field("Currency", "currency", d.currency === "Not applicable" ? "" : d.currency, "text", false)}</div><details class="series-options"><summary>Catalogue name and additional details</summary><div class="fields">${field("Catalogue name (my_name)", "catalog_name", d.catalog_name, "text", false)}${field("Description", "description", d.description, "text", false)}</div>${custom ? `<label>Query parameters (JSON)<textarea name="query_params" spellcheck="false">${esc(JSON.stringify(d.params || {}, null, 2))}</textarea></label>` : `<input type="hidden" name="query_params" value="${esc(JSON.stringify(d.params || {}))}">`}<p class="meta">Catalogue name defaults to the name with underscores.</p></details><p class="meta">${legacy ? "Existing binding. Choose a provider and enter its symbol to move it into the Metapyle catalogue." : "Save writes a Metapyle catalogue entry. Symbols and fields use the provider’s exact identifiers."}${document.body.dataset.mode === "mock" ? " Demo observations remain limited to the existing fixtures." : ""}</p>${actions('<button class="primary" type="submit">Save data series</button>' + button("Cancel", "library-cancel"))}</form></section>`;
  }
  const input = (id) => librarySeriesChoices().find((s) => s.id === id);
  const left = input(d.series_ids[0]),
    right = input(d.series_ids[1]);
  const formula =
    d.calculation === "level"
      ? left?.name
      : d.calculation === "regression"
        ? `${left?.name || "y"} explained by ${right?.name || "x"}`
        : `${left?.name || "A"} ${d.calculation === "ratio" ? "÷" : "−"} ${right?.name || "B"}`;
  return `<section class="paper editor"><h2>${state.catalogue.analyses.some(a => a.id === d.id) ? "Edit analysis defaults" : "Add analysis"}</h2><p class="meta">Saved defaults apply when this Analysis opens and during monitoring. Earlier Idea evidence keeps its captured settings.</p>${state.exploratory && d.id === new URLSearchParams(location.search).get("edit") ? button("Use exploratory settings", "use-exploratory") : ""}<form id="library-form"><div class="fields">${field("Name", "name", d.name)}<label>Type / calculation<select name="calculation" id="calculation">${[
    ["level", "Standalone level"],
    ["ratio", "Pair ratio"],
    ["difference", "Pair difference"],
    ["regression", "Pair regression"],
  ]
    .map(
      ([v, l]) =>
        `<option value="${v}" ${d.calculation === v ? "selected" : ""}>${l}</option>`,
    )
    .join(
      "",
    )}</select></label><label>${pair ? (d.calculation === "regression" ? "Dependent series (y)" : "First input / numerator") : "Data series"}<select name="left" required>${seriesOptions(d.series_ids[0])}</select></label>${pair ? `<label>${d.calculation === "regression" ? "Explanatory series (x)" : "Second input / denominator"}<select name="right" required>${seriesOptions(d.series_ids[1] || librarySeriesChoices()[1]?.id)}</select></label>` : ""}<label>Reference history<select name="history">${periodChoices(d.settings.history_years).map((n) => `<option value="${n}" ${d.settings.history_years === n ? "selected" : ""}>${periodText(n)}</option>`).join("")}</select></label><label>Fitting window<select name="fit">${periodChoices(d.settings.fit_years).map((n) => `<option value="${n}" ${d.settings.fit_years === n ? "selected" : ""}>${periodText(n)}</option>`).join("")}</select></label><label>Measure<select name="measure">${[["level", "Level"], ["change", "Change"], ["return", "Percentage change"]].map(([v, label]) => `<option value="${v}" ${v === (d.settings.measure || "level") ? "selected" : ""}>${label}</option>`).join("")}</select></label><label>Frequency<select name="horizon">${["day", "week", "month"].map((v) => `<option ${d.settings.horizon === v ? "selected" : ""}>${v}</option>`).join("")}</select></label>${standardizationControls(d, true)}${d.settings.standardization === "zscore" ? "" : field("Upper percentile rule (lower tail symmetric)", "upper", d.settings.upper_percentile, "number")}${field("Move threshold (analysis units, optional)", "move", d.settings.move_threshold, "number", false)}${field("Material further move (analysis units, optional)", "material", d.settings.material_change, "number", false)}</div><h3>Risk adjustment defaults</h3>${riskEditor(d.settings, d.series_ids.map(id => input(id)).filter(Boolean))}${librarySeriesActions(d)}<p class="formula">${esc(formula)}</p><p class="meta">${[
    left,
    ...(pair ? [right] : []),
  ]
    .filter(Boolean)
    .map((s) => esc(inputLabel(s)))
    .join(
      "<br>",
    )}</p><label class="monitor"><input name="monitored" type="checkbox" ${d.monitored ? "checked" : ""}> Include in flag monitoring</label><p class="meta">Native-unit thresholds are explicitly configured; risk-adjusted thresholds require separate calibration.</p><div id="library-save-summary"></div>${actions(`<button class="primary" type="submit">${librarySaveLabel(d)}</button>` + button("Cancel", "library-cancel"))}</form></section>`;
}
document.addEventListener("change", async (event) => {
  try {
    const e = event.target;
    if (e.hasAttribute("data-monitoring")) {
      await saveMonitoring(e);
    } else if (e.closest("#library-form") && state.libraryTab === "series" && e.name === "provider") {
      readLibraryDraft();
      state.draft.field = e.value === "bloomberg" ? "PX_LAST" : null;
      state.draft.path = null;
      state.draft.params = {};
      renderLibrary();
    } else if (e.dataset.display) {
      delete state.display.axis_ranges;
      if (e.dataset.display === "view") state.display.hidden_traces = [];
      state.display[e.dataset.display] =
        e.dataset.display === "years" ? Number(e.value) : e.value;
      await plotEvidence(
        document.querySelector("#plot"),
        state.evaluation,
        state.display,
      );
      document.querySelector("#plot").nextElementSibling.outerHTML = evidenceDetails(state.evaluation, "", state.display);
    } else if (e.dataset.risk || e.hasAttribute("data-risk-customize")) {
      if (e.matches("input") && !e.checkValidity()) { e.reportValidity(); return; }
      const library = !!e.closest("#library-form");
      if (library) readLibraryDraft();
      const settings = structuredClone(library ? state.draft.settings : state.evaluation.definition.settings);
      if (e.hasAttribute("data-risk-customize")) {
        const count = library ? state.draft.series_ids.length : state.evaluation.definition.inputs.length;
        if (e.checked) settings.risk_overrides = Array.from({length: count}, () => structuredClone(settings.risk_adjustment || defaultRisk()));
        else { settings.risk_adjustment = settings.risk_overrides[0]; settings.risk_overrides = []; }
      } else {
        const name = e.dataset.risk;
        const risk = e.dataset.leg === "shared" ? (settings.risk_adjustment ||= defaultRisk()) : settings.risk_overrides[Number(e.dataset.leg)];
        risk[name] = name === "lookback_years" ? periodValue(e.value) : ["half_life", "confidence"].includes(name) ? Number(e.value) : name === "reference_id" ? e.value || null : e.value;
      }
      if (riskOptions(settings, 2).some(r => r.method !== "none") && (settings.measure || "level") === "level") {
        settings.measure = "change";
        if (!library) {
          state.display.view = settings.standardization === "zscore" ? "analysis" : "changes";
          state.display.hidden_traces = [];
        }
      }
      settings.move_threshold = settings.material_change = null;
      if (library) {
        state.draft.settings = settings;
        if (e.hasAttribute("data-risk-customize") || ["method", "weighting"].includes(e.dataset.risk)) renderLibrary();
        else {
          const form = document.querySelector("#library-form");
          form.elements.move.value = form.elements.material.value = "";
        }
      }
      else await previewSettings(settings);
    } else if (e.dataset.setting) {
      if (e.matches("input") && !e.checkValidity()) { e.reportValidity(); return; }
      const options = {...state.evaluation.definition.settings, [e.dataset.setting]: ["horizon", "measure", "standardization"].includes(e.dataset.setting) ? e.value : periodValue(e.value)};
      if (e.dataset.setting === "measure") {
        state.display.hidden_traces = [];
        options.move_threshold = options.material_change = null;
        if (e.value === "level") { options.risk_adjustment = defaultRisk(); options.risk_overrides = []; }
        if (state.evaluation.definition.calculation === "level" && e.value === "level") options.standardization = "none";
        state.display.view = e.value === "level" || options.standardization === "zscore" ? "analysis" : "changes";
      }
      if (e.dataset.setting === "standardization") {
        options.move_threshold = options.material_change = null;
        state.display.hidden_traces = [];
        state.display.view = "analysis";
      }
      await previewSettings(options);
    } else if (
      e.closest("#library-form") &&
      state.libraryTab === "analyses" &&
      ["calculation", "left", "right", "measure", "standardization"].includes(e.name)
    ) {
      readLibraryDraft();
      if (
        state.draft.calculation !== "level" &&
        state.draft.series_ids.length < 2
      )
        state.draft.series_ids.push(state.catalogue.series[1]?.id);
      if (e.name === "standardization") state.draft.settings.move_threshold = state.draft.settings.material_change = null;
      if (!supportsZScore(state.draft)) {
        if (state.draft.settings.standardization === "zscore") state.draft.settings.move_threshold = state.draft.settings.material_change = null;
        state.draft.settings.standardization = "none";
      }
      if (e.name === "measure") {
        state.draft.settings.move_threshold = state.draft.settings.material_change = null;
        if (e.value === "level") { state.draft.settings.risk_adjustment = defaultRisk(); state.draft.settings.risk_overrides = []; }
      }
      if (state.draft.settings.risk_overrides?.length && state.draft.settings.risk_overrides.length !== state.draft.series_ids.length) {
        state.draft.settings.risk_overrides = state.draft.series_ids.map((id, i) => state.draft.settings.risk_overrides[i] || structuredClone(state.draft.settings.risk_adjustment || defaultRisk()));
      }
      renderLibrary();
    }
  } catch (e) {
    notify(e.message);
  }
});
document.addEventListener("click", async (event) => {
  const b = event.target.closest("[data-action]");
  if (!b) return;
  const a = b.dataset.action;
  try {
    b.disabled = true;
    if (a === "risk-reset") await previewSettings(structuredClone(state.savedSettings));
    else if (a === "edit-defaults") {
      event.preventDefault();
      await state.previewPromise;
      sessionStorage.setItem("exploratory-" + key, JSON.stringify(state.evaluation.definition.settings));
      location.href = b.href;
    }
    else if (a === "use-exploratory") {
      readLibraryDraft();
      state.draft.settings = structuredClone(state.exploratory);
      renderLibrary();
    } else if (a === "scope") {
      state.list.scope = b.dataset.scope;
      persistContext();
      await loadRows();
    } else if (a === "refresh") {
      await api("/api/refresh", "POST", {});
      await loadRows();
      notify(
        "Refresh complete. Observation dates remain separate from retrieval times.",
      );
    } else if (a === "open-save") await openSave();
    else if (a === "cancel-save") {
      document.querySelector("#save-panel").hidden = true;
      document.querySelector("#workspace").classList.remove("saving");
      await plotEvidence(
        document.querySelector("#plot"),
        state.evaluation,
        state.display,
      );
    } else if (a === "chart-copy" || a === "chart-download") {
      await state.previewPromise;
      const png = await chartPNG(document.querySelector("#plot"));
      await reuseBlob(await (await fetch(png)).blob(), a === "chart-copy");
    } else if (a === "idea-scope") {
      state.ideaScope = b.dataset.scope;
      document
        .querySelectorAll("[data-action=idea-scope]")
        .forEach((x) => x.setAttribute("aria-pressed", x === b));
      await loadIdeas();
    } else if (a === "shortlist" || a === "archive") {
      await api(
        `/api/ideas/${key}`,
        "PATCH",
        a === "shortlist"
          ? { shortlisted: !state.idea.shortlisted }
          : { archived: !state.idea.archived },
      );
      await idea();
    } else if (a === "edit-chart-note") {
      const note = b.closest(".chart-note"),
        panel = note.querySelector(".chart-note-editor");
      panel.hidden = !panel.hidden;
      b.setAttribute("aria-expanded", !panel.hidden);
      if (panel.hidden) panel.querySelector("form").reset();
      else panel.querySelector("textarea").focus();
    } else if (a === "cancel-editor") {
      b.closest("form").reset();
      const note = b.closest(".chart-note");
      if (note) {
        note.querySelector(".chart-note-editor").hidden = true;
        const trigger = note.querySelector("[data-action=edit-chart-note]");
        trigger.setAttribute("aria-expanded", "false");
        trigger.focus();
      } else b.closest("details").open = false;
    } else if (a === "delete-chart-note") {
      await api(`/api/ideas/${key}/charts/${b.dataset.entry}`, "PATCH", {
        text: "",
      });
      await idea();
    } else if (a === "remove-chart") {
      await api(`/api/ideas/${key}/charts/${b.dataset.entry}`, "DELETE");
      await idea();
    } else if (a === "delete-idea-note") {
      await api(`/api/ideas/${key}/notes/${b.dataset.note}`, "DELETE");
      await idea();
    } else if (a === "evidence-mode")
      await evidenceMode(b.dataset.entry, b.dataset.mode);
    else if (a === "evidence-data") await copyEvidenceData(b.dataset.entry);
    else if (a === "evidence-copy" || a === "evidence-download")
      await exportEvidence(b.dataset.entry, a === "evidence-copy");
    else if (a === "library-tab") {
      state.libraryTab = b.dataset.tab;
      state.draft = null;
      state.returnDraft = null;
      renderLibrary();
    } else if (a === "library-new") {
      state.draft = newDraft(state.libraryTab);
      renderLibrary();
    } else if (a === "library-edit") {
      state.draft = structuredClone(
        state.catalogue[state.libraryTab].find((r) => r.id === b.dataset.id),
      );
      renderLibrary();
    } else if (a === "library-delete") {
      await api(`/api/library/${state.libraryTab}/${b.dataset.id}`, "DELETE");
      state.catalogue = await api("/api/library");
      renderLibrary();
    } else if (a === "library-cancel") {
      state.draft = null;
      renderLibrary();
    }
  } catch (e) {
    notify(e.message);
  } finally {
    b.disabled = false;
  }
});
document.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target,
    submit = form.querySelector("[type=submit]");
  try {
    submit.disabled = true;
    const data = Object.fromEntries(new FormData(form));
    if (form.id === "save-form") {
      await state.previewPromise;
      const image = await chartPNG(document.querySelector("#plot"));
      const idea = await api("/api/ideas", "POST", {
        ...data,
        idea_id: data.idea_id || null,
        evaluation_id: state.evaluation.id,
        display: state.display,
        image,
      });
      location.href = "/ideas/" + idea.id;
    } else if (form.dataset.form === "idea-edit") {
      await api(`/api/ideas/${key}`, "PATCH", data);
      await idea();
    } else if (form.dataset.form === "chart-note") {
      await api(`/api/ideas/${key}/charts/${data.entry_id}`, "PATCH", {
        text: data.text,
      });
      await idea();
    } else if (form.dataset.form === "idea-note") {
      await api(`/api/ideas/${key}/notes/${data.note_id}`, "PATCH", {
        text: data.text,
      });
      await idea();
    } else if (form.dataset.form === "add-idea-note") {
      await api(`/api/ideas/${key}/notes`, "POST", { text: data.text });
      await idea();
    }
  } catch (e) {
    notify(e.message);
  } finally {
    if (submit) submit.disabled = false;
  }
});
document.addEventListener("click", (event) => {
  if (page === "analyses" && event.target.closest("a")) persistContext();
});
window.addEventListener("pagehide", () => {
  if (page === "analyses") persistContext();
});
const navPage = ["chart", "analyses"].includes(page)
  ? "analyses"
  : ["idea", "ideas"].includes(page)
    ? "ideas"
    : "library";
document
  .querySelector(`nav a[href="/${navPage}"]`)
  .setAttribute("aria-current", "page");
({ analyses, chart, ideas, idea, library })[page]().catch((error) => {
  main.innerHTML = `<h1>Unable to load research</h1><p class="warning">${esc(error.message)}</p><p><a href="${location.pathname}">Retry</a></p>`;
});
