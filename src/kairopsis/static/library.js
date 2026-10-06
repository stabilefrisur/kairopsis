/* Library drafts and ad-hoc evidence live in memory until an explicit Save. */
function librarySeriesChoices() {
  const choices = new Map(state.catalogue.series.map(s => [s.id, s]));
  if (page === "library") Object.values(state.stagedSeries || {}).forEach(s => choices.set(s.id, s));
  return [...choices.values()];
}
function resetLibraryPreview() {
  state.stagedSeries = {};
  state.libraryPreview = {sequence: (state.libraryPreview?.sequence || 0) + 1, period: 3, view: "analysis", result: null};
  const workspace = document.querySelector("#library-workspace");
  if (workspace) { Plotly.purge(workspace.querySelector(".plot")); workspace.remove(); }
}
function readSeriesDraft(form, draft) {
  const data = Object.fromEntries(new FormData(form));
  const provider = data.provider || draft.source;
  const source = provider === "custom" ? data.custom_source : provider;
  const legacy = !["bloomberg", "gsquant", "macrobond", "localfile", "custom"].includes(provider);
  let query;
  try { query = JSON.parse(data.query_params || "{}"); }
  catch { throw Error("Query parameters must be a JSON object."); }
  if (!query || Array.isArray(query) || typeof query !== "object") throw Error("Query parameters must be a JSON object.");
  return {...draft, name: data.name, source, instrument: data.instrument,
    field: ["macrobond", "localfile"].includes(source) ? null : data.field?.trim() || null,
    unit: data.unit, currency: data.currency?.trim() || "Not applicable", catalog_name: legacy ? null : data.catalog_name?.trim() || "",
    path: data.path?.trim() || null, params: query, description: data.description?.trim() || null};
}
function seriesForSave(series) {
  return {...series, catalog_name: series.catalog_name === null ? null : series.catalog_name ||
    series.name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 128) || "series_" + series.id};
}
function previewBinding(series) {
  return {...series, catalog_name: null};
}
function retainedSeries(draft) {
  return new Set([...draft.series_ids, ...riskOptions(draft.settings, draft.series_ids.length)
    .filter(r => r.method !== "none" && r.reference_id).map(r => r.reference_id)]);
}
function retainedDrafts(draft = state.draft) {
  const retained = retainedSeries(draft);
  return Object.values(state.stagedSeries || {}).filter(s => retained.has(s.id));
}
function librarySaveLabel(draft) {
  const count = retainedDrafts(draft).length;
  return count ? `Save analysis and ${count} series` :
    state.catalogue.analyses.some(a => a.id === draft.id) ? "Save defaults" : "Save analysis";
}
function librarySeriesActions(draft) {
  const retained = retainedSeries(draft);
  return `<div class="actions library-series-actions">${button("Add data series", "inline-series", 'class="quiet"')}${librarySeriesChoices().filter(s => retained.has(s.id)).map(s => button(`Edit ${esc(s.name)}`, "stage-series", `class="quiet" data-id="${esc(s.id)}"`)).join("")}</div>`;
}
function libraryWorkspace(editor) {
  return `<div class="library-workspace" id="library-workspace"><div id="library-editor">${editor}</div><section class="paper library-preview" aria-label="Draft chart preview"><h2>Preview</h2><div class="controls library-preview-controls"><label>Display range<select id="library-period">${periodChoices(3).map(n => `<option value="${n}" ${n === 3 ? "selected" : ""}>${periodText(n)}</option>`).join("")}</select></label><label>Chart view<select id="library-view">${libraryViewOptions()}</select></label>${button("Preview", "library-preview", 'class="primary"')}</div><p id="library-preview-status" class="status" role="status" aria-live="polite">Choose settings, then Preview. Nothing is saved.</p><div id="library-plot" class="plot" role="img" aria-label="Unsaved draft chart preview"><p class="empty">Preview this draft to inspect its observations.</p></div><div id="library-preview-details"></div></section></div>`;
}
function libraryViewOptions() {
  if (state.libraryTab === "series") return '<option value="analysis">Data series</option>';
  const definition = state.libraryPreview.result?.definition || state.draft;
  return '<option value="analysis">Analysis</option><option value="underlying">Underlying series</option>' +
    (definition.settings.measure && definition.settings.measure !== "level" || riskOptions(definition.settings, definition.series_ids?.length || definition.inputs?.length || 1).some(r => r.method !== "none") ? '<option value="changes">Measured / adjusted series</option>' : "") +
    (definition.calculation === "regression" ? '<option value="scatter">Regression scatter</option>' : "");
}
function restoreLibraryFocus(container, focused) {
  if (!focused) return;
  const selector = focused.dataset.risk ? `[data-risk="${focused.dataset.risk}"][data-leg="${focused.dataset.leg}"]` :
    focused.hasAttribute("data-risk-customize") ? "[data-risk-customize]" : focused.name ? `[name="${CSS.escape(focused.name)}"]` : null;
  if (selector) container.querySelector(selector)?.focus({preventScroll: true});
}
function replaceLibraryEditor() {
  const container = document.querySelector("#library-editor"), focused = document.activeElement;
  const open = [...container.querySelectorAll("details")].map(d => d.open);
  container.innerHTML = libraryEditor();
  container.querySelectorAll("details").forEach((d, i) => d.open = open[i] || false);
  updateLibrarySummary();
  restoreLibraryFocus(container, focused);
}
function updateLibrarySummary() {
  const box = document.querySelector("#library-save-summary");
  if (!box || state.libraryTab !== "analyses") return;
  const drafts = retainedDrafts(), ids = new Set(drafts.map(s => s.id));
  const affected = state.catalogue.analyses.filter(a => a.id !== state.draft.id && [...retainedSeries(a)].some(id => ids.has(id)));
  box.innerHTML = drafts.length ? `<p class="meta">Save together: ${drafts.map(s => `${state.catalogue.series.some(old => old.id === s.id) ? "update" : "add"} ${esc(s.name)}`).join("; ")}.${affected.length ? ` Future evaluations also change for: ${affected.map(a => esc(a.name)).join(", ")}.` : ""}</p>` : "";
  document.querySelector('#library-form [type="submit"]').textContent = librarySaveLabel(state.draft);
}
function libraryStatus(text) {
  const box = document.querySelector("#library-preview-status");
  if (box) box.textContent = text;
}
function outdatedLibraryPreview() {
  if (!state.libraryPreview) return;
  state.libraryPreview.sequence++;
  state.libraryPreview.loading = false;
  const button = document.querySelector('[data-action="library-preview"]');
  if (button) button.disabled = false;
  libraryStatus(state.libraryPreview.result ? "Outdated. Settings changed; Preview to update. Chart details show the previous preview." : "Draft changed. Preview to inspect it; nothing is saved.");
}
async function renderLibraryChart() {
  const preview = state.libraryPreview, result = preview.result;
  if (!result) return;
  const display = {years: preview.previewPeriod, view: preview.view};
  const plot = document.querySelector("#library-plot");
  plot.querySelector(".empty")?.remove();
  if (result.definition) await plotEvidence(plot, result, display);
  else await plotSeries(plot, result, display);
  document.querySelector("#library-preview-details").innerHTML = result.definition ? evidenceDetails(result, "", display) : seriesPreviewDetails(result, display);
  plot.setAttribute("aria-label", `Preview of ${result.definition?.name || result.data.series[0].binding.name}, ${periodText(preview.previewPeriod)}`);
}
async function previewLibrary() {
  const form = document.querySelector("#library-form");
  if (!form.reportValidity()) return;
  readLibraryDraft();
  const preview = state.libraryPreview, sequence = ++preview.sequence;
  const period = preview.period;
  const series = state.libraryTab === "series";
  const body = series ? {series: previewBinding(state.draft), period} :
    {analysis: activeAnalysis(state.draft), series_drafts: retainedDrafts().map(previewBinding), period};
  preview.loading = true;
  libraryStatus("Fetching and calculating this draft…");
  try {
    const result = await api(`/api/library/${series ? "series" : "analyses"}/preview`, "POST", body);
    if (preview !== state.libraryPreview || sequence !== preview.sequence) return;
    if (!result.data.series.length || !result.data.series.some(s => s.observations.some(p => p.value != null)))
      throw Error(result.data.failures.map(f => f.message).join("; ") || "No observations returned for this query and period.");
    preview.result = result;
    preview.previewPeriod = period;
    const view = document.querySelector("#library-view");
    view.innerHTML = libraryViewOptions();
    if (series || ![...view.options].some(o => o.value === preview.view)) preview.view = "analysis";
    view.value = preview.view;
    await renderLibraryChart();
    if (preview !== state.libraryPreview || sequence !== preview.sequence) return;
    if (result.definition && !result.points.some(p => p.value != null)) {
      const limitation = result.limitations.slice(0, 2).map(readableQuality).join(" ");
      libraryStatus(`Analysis unavailable. ${limitation} Choose Underlying series or Preview each input to inspect observations. Check Source and chart details; nothing is saved.`);
    } else libraryStatus(result.data.failures.length ? "Preview incomplete. Check Source and chart details; nothing is saved." : "Preview current. Nothing is saved.");
  } catch (error) {
    if (preview === state.libraryPreview && sequence === preview.sequence)
      libraryStatus(`Preview failed: ${error.message}${preview.result ? " Outdated chart retained; retry Preview." : " Correct the query and retry."}`);
  } finally {
    if (preview === state.libraryPreview && sequence === preview.sequence) preview.loading = false;
  }
}
function stageDestinationOptions(draft) {
  const choices = [["left", "First input"], ...(draft.calculation !== "level" ? [["right", "Second input"]] : []),
    ...(draft.settings.risk_overrides?.length ? draft.series_ids.map((id, i) => [`reference-${i}`, `Risk reference for input ${i + 1}`]) : [["reference-shared", "Risk reference"]])];
  return choices.map(([value, label]) => `<option value="${value}">${label}</option>`).join("");
}
function renderStagedSeries() {
  const staged = state.stagedEditor, dialog = document.querySelector("#library-series-dialog");
  const focused = document.activeElement;
  const previousChart = dialog.querySelector("#staged-chart-area");
  dialog.innerHTML = libraryEditor(staged.draft, "series").replace('id="library-form"', 'id="staged-series-form"')
    .replace("Save data series", "Apply series").replace('data-action="library-cancel"', 'data-action="stage-cancel"');
  dialog.querySelector("h2").id = "staged-series-title";
  const form = dialog.querySelector("form");
  if (!staged.existing) form.insertAdjacentHTML("afterbegin", `<label>Use for<select name="destination">${stageDestinationOptions(state.draft)}</select></label>`);
  form.querySelector(".actions").insertAdjacentHTML("beforebegin", `<p class="meta">Apply stages this Series. It is saved together with the Analysis.</p>${button("Preview series", "stage-preview")}<div id="staged-chart-area"><p id="staged-preview-status" role="status"></p><div id="staged-plot" class="plot" role="img" aria-label="Staged Series preview" hidden></div><div id="staged-preview-details"></div></div>`);
  if (previousChart) {
    dialog.querySelector("#staged-chart-area").replaceWith(previousChart);
    previousChart.querySelector("[role=status]").textContent = "Outdated. Preview this Series again after editing.";
  }
  if (!staged.existing) form.elements.destination.value = staged.destination;
  restoreLibraryFocus(dialog, focused);
}
function openStagedSeries(id = null) {
  readLibraryDraft();
  const selected = id ? librarySeriesChoices().find(s => s.id === id) : newDraft("series");
  state.stagedEditor = {draft: structuredClone(selected), existing: !!id, sequence: 0,
    destination: state.draft.calculation === "level" ? "left" : "right", opener: document.activeElement};
  const dialog = document.createElement("dialog");
  dialog.id = "library-series-dialog";
  dialog.className = "library-series-dialog";
  dialog.setAttribute("aria-labelledby", "staged-series-title");
  document.body.append(dialog);
  renderStagedSeries();
  dialog.addEventListener("close", () => {
    const opener = state.stagedEditor?.opener;
    state.stagedEditor = null;
    Plotly.purge(dialog.querySelector(".plot"));
    dialog.remove();
    if (opener?.isConnected) opener.focus();
  });
  dialog.showModal();
}
async function previewStagedSeries() {
  const staged = state.stagedEditor, form = document.querySelector("#staged-series-form");
  if (!form.reportValidity()) return;
  staged.draft = readSeriesDraft(form, staged.draft);
  const sequence = ++staged.sequence;
  document.querySelector("#staged-preview-status").textContent = "Fetching this Series…";
  try {
    const result = await api("/api/library/series/preview", "POST", {series: previewBinding(staged.draft), period: 3});
    if (state.stagedEditor !== staged || sequence !== staged.sequence) return;
    if (!result.data.series.some(s => s.observations.some(p => p.value != null))) throw Error(result.data.failures.map(f => f.message).join("; ") || "No observations in this period.");
    const plot = document.querySelector("#staged-plot");
    plot.hidden = false;
    await plotSeries(plot, result, {years: 3, view: "analysis"});
    if (state.stagedEditor !== staged || sequence !== staged.sequence) return;
    document.querySelector("#staged-preview-details").innerHTML = seriesPreviewDetails(result, {years: 3});
    document.querySelector("#staged-preview-status").textContent = "Preview current. Apply to stage; nothing is saved.";
  } catch (error) {
    if (state.stagedEditor === staged && sequence === staged.sequence) document.querySelector("#staged-preview-status").textContent = `Preview failed: ${error.message}`;
  }
}
function applyStagedSeries(form) {
  const staged = state.stagedEditor;
  staged.draft = readSeriesDraft(form, staged.draft);
  const saved = state.catalogue.series.find(s => s.id === staged.draft.id);
  if (saved && JSON.stringify(saved) === JSON.stringify({...saved, ...staged.draft})) delete state.stagedSeries[staged.draft.id];
  else state.stagedSeries[staged.draft.id] = staged.draft;
  if (!staged.existing) {
    const destination = form.elements.destination.value;
    if (destination.startsWith("reference-")) {
      const index = destination.split("-")[1];
      const risk = index === "shared" ? (state.draft.settings.risk_adjustment ||= defaultRisk()) : state.draft.settings.risk_overrides[Number(index)];
      risk.reference_id = staged.draft.id;
    } else state.draft.series_ids[destination === "left" ? 0 : 1] = staged.draft.id;
  }
  document.querySelector("#library-series-dialog").close();
  outdatedLibraryPreview();
  replaceLibraryEditor();
  document.querySelector("#library-form [name=left]")?.focus({preventScroll: true});
}
async function saveLibraryDraft(form) {
  readLibraryDraft();
  const series = state.libraryTab === "series", draft = series ? structuredClone(state.draft) : activeAnalysis(state.draft);
  const controls = [...form.querySelectorAll("input, select, textarea, button")];
  state.librarySaving = true;
  controls.forEach(c => c.disabled = true);
  try {
    const old = state.catalogue.analyses.find(a => a.id === draft.id);
    const drafts = series ? [] : retainedDrafts(draft);
    const baseRevisions = {analyses: old ? {[old.id]: old.revision} : {},
      series: Object.fromEntries(drafts.flatMap(s => {
        const original = state.catalogue.series.find(saved => saved.id === s.id);
        return original ? [[original.id, original.revision]] : [];
      }))};
    const response = series ? await api("/api/library/series", "POST", seriesForSave(draft)) :
      await api("/api/library/analyses/bundle", "POST", {analysis: draft, series_drafts: drafts.map(seriesForSave), base_revisions: baseRevisions});
    const saved = series ? response : response.analysis;
    state.catalogue = await api("/api/library");
    if (!series && saved.id === new URLSearchParams(location.search).get("edit")) {
      sessionStorage.removeItem("exploratory-" + saved.id);
      location.href = "/analyses/" + encodeURIComponent(saved.id);
      return;
    }
    state.draft = null;
    resetLibraryPreview();
    renderLibrary();
    notify("Saved. Future evaluations use these defaults; earlier evidence keeps its definition.");
  } finally { state.librarySaving = false; controls.forEach(c => c.disabled = false); }
}
document.addEventListener("input", event => {
  if (page !== "library") return;
  if (event.target.closest("#library-form")) {
    outdatedLibraryPreview();
    try { readLibraryDraft(); updateLibrarySummary(); } catch { /* Keep incomplete text editable. */ }
  } else if (event.target.closest("#staged-series-form")) {
    state.stagedEditor.sequence++;
    document.querySelector("#staged-preview-status").textContent = "Outdated. Preview this Series again after editing.";
  }
});
document.addEventListener("change", async event => {
  if (page !== "library") return;
  const control = event.target;
  try {
    if (control.id === "library-period") {
      state.libraryPreview.period = periodValue(control.value);
      outdatedLibraryPreview();
    } else if (control.id === "library-view") {
      state.libraryPreview.view = control.value;
      await renderLibraryChart();
    } else if (control.closest("#staged-series-form")) {
      event.stopPropagation();
      const staged = state.stagedEditor;
      staged.sequence++;
      staged.draft = readSeriesDraft(control.form, staged.draft);
      if (control.name === "destination") staged.destination = control.value;
      if (control.name === "provider") {
        staged.draft.field = ["bloomberg", "gsquant"].includes(control.value) ? "PX_LAST" : null;
        staged.draft.path = null;
        staged.draft.params = {};
        renderStagedSeries();
      }
    } else if (control.closest("#library-form")) {
      outdatedLibraryPreview();
      readLibraryDraft();
      updateLibrarySummary();
    }
  } catch (error) { notify(error.message); }
}, true);
document.addEventListener("click", async event => {
  if (page !== "library") return;
  const control = event.target.closest("[data-action]");
  if (!control) return;
  const action = control.dataset.action;
  if (state.librarySaving && action.startsWith("library-")) { event.stopPropagation(); return; }
  if (["library-tab", "library-new", "library-edit", "library-cancel"].includes(action)) { resetLibraryPreview(); return; }
  if (action === "use-exploratory") { outdatedLibraryPreview(); return; }
  if (!["library-preview", "inline-series", "stage-series", "stage-preview", "stage-cancel"].includes(action)) return;
  event.stopPropagation();
  control.disabled = true;
  try {
    if (action === "library-preview") await previewLibrary();
    else if (action === "inline-series" || action === "stage-series") openStagedSeries(control.dataset.id);
    else if (action === "stage-preview") await previewStagedSeries();
    else document.querySelector("#library-series-dialog").close();
  } catch (error) { notify(error.message); }
  finally { control.disabled = false; }
}, true);
document.addEventListener("submit", async event => {
  if (page !== "library" || !["library-form", "staged-series-form"].includes(event.target.id)) return;
  event.preventDefault();
  event.stopPropagation();
  try {
    if (event.target.id === "staged-series-form") applyStagedSeries(event.target);
    else await saveLibraryDraft(event.target);
  } catch (error) { notify(error.message); }
}, true);
