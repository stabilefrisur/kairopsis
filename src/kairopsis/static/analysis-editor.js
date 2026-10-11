/* One Analysis editor for Library creation, editing and monitoring investigation. */
function editorFormFields() {
  const d = state.analysisDraft;
  return `${field("Name", "name", d.name)}<label>Economic rationale<textarea name="economic_rationale" maxlength="10000" rows="3">${esc(d.economic_rationale || "")}</textarea></label><p class="meta">What are you investigating, and why?</p>${analysisControls(d)}${librarySeriesActions(d)}<div id="analysis-series-summary"></div>`;
}
function renderRiskPanel() {
  document.querySelector("#risk-panel").innerHTML = `<h2>Analysis settings</h2><form id="investigation-form">${editorFormFields()}</form>`;
}
function editorDirty() {
  return !state.savedAnalysis || retainedDrafts(state.analysisDraft).length > 0 ||
    JSON.stringify(activeAnalysis(state.analysisDraft)) !== JSON.stringify(activeAnalysis(state.savedAnalysis));
}
function updateEditorState() {
  const dirty = editorDirty();
  document.querySelector("#analysis-save-status").textContent = state.editorSaving ? "Saving…" : dirty ? "Unsaved changes" : "Saved";
  document.querySelector('[data-action="analysis-save"]').disabled = state.editorSaving || !dirty;
  document.querySelector('[data-action="analysis-discard"]').disabled = state.editorSaving || !dirty;
  document.querySelector('[data-action="open-save"]').disabled = state.editorSaving || !state.previewCurrent;
  const drafts = retainedDrafts(state.analysisDraft);
  const box = document.querySelector("#analysis-series-summary");
  if (box) box.textContent = drafts.length ? `Save will also ${drafts.some(s => state.catalogue.series.some(old => old.id === s.id)) ? "update" : "add"} ${drafts.map(s => s.name).join(", ")}. Series updates apply to other Analyses using them.` : "";
}
function scheduleAnalysisPreview() {
  clearTimeout(state.editorTimer);
  state.previewSequence = (state.previewSequence || 0) + 1;
  state.previewCurrent = false;
  document.querySelector("#investigation-status").textContent = "Updating chart…";
  updateEditorState();
  state.editorTimer = setTimeout(() => previewSettings().catch(error => notify(error.message)), 350);
}
async function previewSettings() {
  clearTimeout(state.editorTimer);
  const form = document.querySelector("#investigation-form");
  if (!form.checkValidity()) {
    document.querySelector("#investigation-status").textContent = "Complete the highlighted settings to update the chart.";
    return;
  }
  const draft = activeAnalysis(state.analysisDraft), sequence = state.previewSequence = (state.previewSequence || 0) + 1;
  state.previewCurrent = false;
  updateEditorState();
  document.querySelector("#investigation-status").textContent = "Updating chart…";
  const promise = (async () => {
    try {
      const evaluation = await api("/api/library/analyses/preview", "POST", {analysis: draft,
        series_drafts: retainedDrafts(draft).map(previewBinding), period: state.display.years, retain: true});
      if (sequence !== state.previewSequence) return;
      state.evaluation = evaluation;
      if (!hasTransformedInputs(evaluation) && state.display.view === "changes" || evaluation.definition.calculation !== "regression" && state.display.view === "scatter") state.display.view = "analysis";
      delete state.display.axis_ranges;
      document.querySelector("#analysis-chart-title").textContent = evaluation.definition.name;
      document.querySelector("#analysis-metrics").innerHTML = metrics(evaluation);
      document.querySelector("#investigation-controls").innerHTML = chartControls(evaluation, state.display);
      document.querySelector("#analysis-evidence").innerHTML = evidenceDetails(evaluation, "", state.display);
      // Serialize Plotly mutations; a newer result always renders last.
      state.editorPlot = (state.editorPlot || Promise.resolve()).catch(() => {}).then(async () => {
        if (sequence === state.previewSequence) await plotEvidence(document.querySelector("#plot"), evaluation, state.display);
      });
      await state.editorPlot;
      if (sequence !== state.previewSequence) return;
      state.previewCurrent = true;
      document.querySelector("#investigation-status").textContent = evaluation.current == null ? `Calculation unavailable. ${evaluation.limitations.join(" ")}` : "Chart up to date.";
      updateEditorState();
    } catch (error) {
      if (sequence === state.previewSequence) {
        document.querySelector("#investigation-status").textContent = `Update failed: ${error.message}. Any displayed chart belongs to the previous settings. Use Retry chart.`;
        let retry = document.querySelector('[data-action="investigation-preview"]');
        if (!retry) {
          document.querySelector("#investigation-controls").insertAdjacentHTML("beforeend", button("Retry chart", "investigation-preview"));
          retry = document.querySelector('[data-action="investigation-preview"]');
        }
        retry.hidden = false;
        updateEditorState();
      }
    }
  })();
  state.previewPromise = promise;
  try { await promise; } finally { if (state.previewPromise === promise) state.previewPromise = null; }
}
async function chart() {
  state.catalogue = await api("/api/library");
  state.libraryTab = "analyses";
  state.stagedSeries = {};
  state.display = {years: 3, view: "analysis"};
  state.savedAnalysis = key === "new" ? null : structuredClone(state.catalogue.analyses.find(a => a.id === key));
  state.analysisDraft = structuredClone(state.savedAnalysis || {...newDraft("analyses"), name: "New analysis"});
  // Carry drafts created by the former Analysis -> Library handoff.
  try {
    const carried = JSON.parse(sessionStorage.getItem("exploratory-" + key));
    if (carried?.id === key && carried.revision === state.analysisDraft.revision) state.analysisDraft = carried;
  } catch { /* An invalid browser draft cannot replace the saved definition. */ }
  state.editorInitial = structuredClone(state.analysisDraft);
  state.draft = state.analysisDraft;
  renderChart();
  await previewSettings();
}
function renderChart() {
  main.innerHTML = `<div class="analysis-editor-header"><div><h1>${state.savedAnalysis ? "Edit Analysis" : "Create Analysis"}</h1><span id="analysis-save-status" role="status"></span></div>${actions(button(state.savedAnalysis ? "Save changes" : "Save Analysis", "analysis-save", 'class="primary"') + button("Discard changes", "analysis-discard") + '<a href="/library">Library</a>')}</div><div class="workspace analysis-workspace" id="workspace"><aside id="risk-panel" class="paper"></aside><div class="analysis-chart-column"><section class="paper"><div class="chart-heading"><h2 id="analysis-chart-title">${esc(state.analysisDraft.name)}</h2>${actions(button("Save to Idea", "open-save") + button("Copy chart", "chart-copy") + button("Download chart", "chart-download"))}</div><div id="analysis-metrics"></div><div id="investigation-controls"><p id="investigation-status" role="status">Loading chart…</p></div><div class="plot" id="plot" role="img" aria-label="Analysis chart"></div><div id="analysis-evidence"></div></section><aside id="save-panel" class="paper save-panel" hidden></aside></div></div>`;
  renderRiskPanel();
  updateEditorState();
}
async function saveAnalysisChanges() {
  const form = document.querySelector("#investigation-form");
  if (!form.reportValidity()) return;
  readAnalysisControls(form, state.analysisDraft);
  const draft = activeAnalysis(state.analysisDraft), drafts = retainedDrafts(draft);
  state.editorSaving = true;
  clearTimeout(state.editorTimer);
  state.previewSequence++;
  state.previewCurrent = false;
  const controls = [...form.querySelectorAll("input, select, textarea, button")];
  controls.forEach(c => c.disabled = true);
  updateEditorState();
  try {
    const result = await api("/api/library/analyses/bundle", "POST", {analysis: draft, series_drafts: drafts.map(seriesForSave),
      base_revisions: {analyses: state.savedAnalysis ? {[draft.id]: state.savedAnalysis.revision} : {},
        series: Object.fromEntries(drafts.flatMap(s => {
          const saved = state.catalogue.series.find(old => old.id === s.id);
          return saved ? [[s.id, saved.revision]] : [];
        }))}});
    state.catalogue.analyses = [...state.catalogue.analyses.filter(a => a.id !== result.analysis.id), result.analysis];
    for (const series of result.series) state.catalogue.series = [...state.catalogue.series.filter(s => s.id !== series.id), series];
    state.savedAnalysis = structuredClone(result.analysis);
    state.analysisDraft = structuredClone(result.analysis);
    state.draft = state.analysisDraft;
    state.stagedSeries = {};
    sessionStorage.removeItem("exploratory-" + draft.id);
    history.replaceState(null, "", "/analyses/" + encodeURIComponent(draft.id));
    document.querySelector('[data-action="analysis-save"]').textContent = "Save changes";
    document.querySelector(".analysis-editor-header h1").textContent = "Edit Analysis";
    renderRiskPanel();
    notify("Analysis saved. Earlier Idea evidence is unchanged.");
  } catch (error) {
    notify(`Could not save: ${error.message}. Your edits are still here.`);
  } finally {
    state.editorSaving = false;
    controls.forEach(c => c.disabled = false);
    updateEditorState();
    await previewSettings();
  }
}
async function discardAnalysisChanges() {
  clearTimeout(state.editorTimer);
  state.previewSequence++;
  state.analysisDraft = structuredClone(state.savedAnalysis || state.editorInitial);
  state.draft = state.analysisDraft;
  state.stagedSeries = {};
  state.thresholdNotice = "";
  sessionStorage.removeItem("exploratory-" + state.analysisDraft.id);
  renderRiskPanel();
  await previewSettings();
}
window.addEventListener("beforeunload", event => {
  if (page === "chart" && !state.editorLeaving && state.analysisDraft && editorDirty()) { event.preventDefault(); event.returnValue = ""; }
});
