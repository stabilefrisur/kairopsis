/* Shared analytical controls: local draft -> explicit preview/save -> captured evidence. */
function activeAnalysis(draft) {
  const settings = structuredClone(draft.settings);
  const activeRisk = risk => {
    if (!risk || risk.method === "none") return {method: "none"};
    const result = {...risk};
    if (risk.method !== "volatility") { delete result.weighting; delete result.half_life; }
    else if (risk.weighting !== "exponential") delete result.half_life;
    if (!["var", "es"].includes(risk.method)) { delete result.confidence; delete result.downside; }
    return result;
  };
  settings.risk_adjustment = activeRisk(settings.risk_adjustment);
  if (settings.risk_overrides?.length) settings.risk_overrides = settings.risk_overrides.map(activeRisk);
  return {...draft, series_ids: draft.series_ids.slice(0, draft.calculation === "level" ? 1 : 2), settings};
}
function analysisFromEvaluation(e) {
  const d = e.definition;
  return {id: d.id, revision: d.revision, name: d.name, calculation: d.calculation,
    economic_rationale: d.economic_rationale || "",
    series_ids: d.inputs.map(s => s.id), monitored: state.catalogue.analyses.find(a => a.id === d.id)?.monitored || false,
    settings: structuredClone(d.settings)};
}
function formulaSignature(d) {
  const s = d.settings;
  return JSON.stringify([d.calculation, d.series_ids, s.measure || "level", s.horizon, s.standardization || "none",
    riskOptions(s, d.series_ids.length).map(r => r.method === "none" ? ["none"] :
      [r.method, r.reference_id, r.estimation_measure || null, r.lookback_years,
        ...(r.method === "volatility" ? [r.weighting, r.weighting === "exponential" ? r.half_life : null] : []),
        ...(["var", "es"].includes(r.method) ? [r.confidence, r.downside] : [])])]);
}
function readAnalysisControls(form, d) {
  const previous = formulaSignature(d), s = d.settings;
  const value = name => form.elements.namedItem(name)?.value;
  const memo = (state.controlMemory ||= {})[d.id] ||= {};
  if (value("name") != null) d.name = value("name");
  if (value("economic_rationale") != null) d.economic_rationale = value("economic_rationale");
  if (d.calculation !== "level") memo.pairCalculation = d.calculation;
  if (value("right")) memo.right = value("right");
  if (s.risk_overrides?.length > 1) memo.overrides = structuredClone(s.risk_overrides);
  const pair = value("analysis_type") === "pair";
  d.calculation = pair ? value("calculation") || memo.pairCalculation || "difference" : "level";
  if (pair) memo.pairCalculation = d.calculation;
  d.series_ids = [value("left") || d.series_ids[0], ...(pair ? [memo.right || librarySeriesChoices().find(b => b.id !== (value("left") || d.series_ids[0]))?.id] : [])];
  for (const [name, field] of [["measure", "measure"], ["horizon", "horizon"], ["standardization", "standardization"]]) {
    if (value(name) != null) s[field] = value(name);
  }
  for (const [name, field] of [["history", "history_years"], ["fit", "fit_years"]]) {
    if (value(name) != null) s[field] = periodValue(value(name));
  }
  for (const [name, field] of [["z_threshold", "zscore_threshold"], ["upper", "upper_percentile"], ["move", "move_threshold"], ["material", "material_change"]]) {
    if (value(name) != null) s[field] = value(name) === "" ? null : Number(value(name));
  }
  if (form.elements.monitored) d.monitored = form.elements.monitored.checked;
  const checkbox = form.querySelector("[data-risk-customize]");
  const customized = checkbox ? checkbox.checked : !!s.risk_overrides?.length;
  if (customized) s.risk_overrides = d.series_ids.map((_, i) => structuredClone(s.risk_overrides?.[i] || memo.overrides?.[i] || s.risk_adjustment || defaultRisk()));
  else if (s.risk_overrides?.length) { s.risk_adjustment = structuredClone(s.risk_overrides[0]); s.risk_overrides = []; }
  form.querySelectorAll("[data-risk]").forEach(control => {
    const r = control.dataset.leg === "shared" ? (s.risk_adjustment ||= defaultRisk()) : s.risk_overrides[Number(control.dataset.leg)];
    if (!r) return;
    const name = control.dataset.risk;
    r[name] = name === "lookback_years" ? periodValue(control.value) : ["confidence", "half_life"].includes(name) ? Number(control.value) :
      ["reference_id", "estimation_measure"].includes(name) ? control.value || null : control.value;
  });
  const risks = riskOptions(s, d.series_ids.length);
  if (risks.some(r => r.method !== "none" && ((s.measure || "level") === "level" || r.estimation_measure)) ||
      s.standardization === "zscore" && (d.calculation === "ratio" || d.calculation === "level" && (s.measure || "level") === "level"))
    s.calculation_contract = "input-pipeline-v2";
  if (previous !== formulaSignature(d)) {
    s.move_threshold = s.material_change = null;
    state.thresholdNotice = "Calculation changed. Optional move/materiality thresholds cleared; reconsider them in the resulting units.";
    for (const name of ["move", "material"]) if (form.elements[name]) form.elements[name].value = "";
  }
  return d;
}
function analysisControls(d, estimates = []) {
  const s = d.settings, pair = d.calculation !== "level";
  const select = (label, name, selected, values) => `<label>${label}<select name="${name}" data-analysis-control="${name}">${values.map(([v, label]) => `<option value="${esc(v)}" ${String(selected) === String(v) ? "selected" : ""}>${esc(label)}</option>`).join("")}</select></label>`;
  const periods = (label, name, selected) => select(label, name, selected, periodChoices(selected).map(n => [n, periodText(n)]));
  const input = (label, name, id) => `<label>${label}<select name="${name}" data-analysis-control="${name}" required>${seriesOptions(id)}</select></label>`;
  const roles = d.calculation === "ratio" ? ["Numerator", "Denominator"] : d.calculation === "regression" ? ["Dependent series (y)", "Explanatory series (x)"] : ["First input", "Second input"];
  const bindings = d.series_ids.map(id => librarySeriesChoices().find(b => b.id === id) || {id, name: "Choose a series"});
  return `<div class="analysis-controls"><fieldset><legend>Inputs</legend><div class="fields">${select("Type", "analysis_type", pair ? "pair" : "standalone", [["standalone", "Standalone"], ["pair", "Pair"]])}${input(pair ? roles[0] : "Data series", "left", d.series_ids[0])}${pair ? input(roles[1], "right", d.series_ids[1]) : ""}</div></fieldset>
    <fieldset><legend>Measure</legend><div class="fields">${select("Input measure", "measure", s.measure || "level", [["level", "Level"], ["change", "Absolute change"], ["return", "Percentage change"]])}${select("Frequency", "horizon", s.horizon, [["day", "Daily"], ["week", "Weekly"], ["month", "Monthly"]])}</div></fieldset>
    <fieldset><legend>Scale inputs</legend>${riskEditor(s, bindings, estimates)}<p class="meta">Estimates exclude the current Frequency interval. Level numerators remain levels. Sparse tail estimates need economic scrutiny; self-beta equals one when defined.</p></fieldset>
    ${pair ? `<fieldset><legend>Compare</legend><div class="fields">${select("Calculation", "calculation", d.calculation, [["difference", "Difference"], ["ratio", "Ratio"], ["regression", "Regression residual"]])}${d.calculation === "regression" ? periods("Fitting window", "fit", s.fit_years) : ""}</div>${d.calculation === "ratio" ? '<p class="meta">Signed and near-zero denominators can dominate ratios. A shared common divisor cancels. Ratios of changes describe relative moves.</p>' : ""}</fieldset>` : ""}
    <fieldset><legend>Historical context</legend><div class="fields">${periods("Reference history", "history", s.history_years)}${select("Output scale", "standardization", s.standardization || "none", [["none", "Original units"], ["zscore", "Z-score"]])}</div><p class="meta">Original units are those of the completed, possibly scaled calculation. Z-score follows comparison; it does not establish stationarity or mean reversion.</p></fieldset>
    <p class="formula">${esc(analysisFormula(d, bindings))}</p><p class="meta">${esc(analysisInterpretation(d))}</p>
    <details class="monitoring-controls"><summary>Monitoring · ${d.monitored ? "enabled" : "disabled"}</summary><label class="monitor"><input name="monitored" type="checkbox" ${d.monitored ? "checked" : ""}> Include in flag monitoring</label><div class="fields">${s.standardization === "zscore" ? field("Z-score threshold (±)", "z_threshold", s.zscore_threshold ?? 2, "number") : field("Upper percentile rule (lower tail symmetric)", "upper", s.upper_percentile ?? 95, "number")}${field("Move threshold (analysis units, optional)", "move", s.move_threshold, "number", false)}${field("Material further move (analysis units, optional)", "material", s.material_change, "number", false)}</div><p class="meta threshold-notice">${esc(state.thresholdNotice || "Thresholds require separate calibration. Save explicitly to change Library defaults.")}</p></details></div>`;
}
function replaceInvestigationControls() {
  const form = document.querySelector("#investigation-form"), focused = document.activeElement;
  const open = form.querySelector("details")?.open;
  const selector = focused.dataset.risk ? `[data-risk="${focused.dataset.risk}"][data-leg="${focused.dataset.leg}"]` : focused.name ? `[name="${CSS.escape(focused.name)}"]` : focused.hasAttribute("data-risk-customize") ? "[data-risk-customize]" : null;
  form.innerHTML = analysisControls(state.analysisDraft, state.previewCurrent ? state.evaluation.adjustment_estimates : []);
  if (form.querySelector("details")) form.querySelector("details").open = open || false;
  if (selector) form.querySelector(selector)?.focus({preventScroll: true});
}
document.addEventListener("input", event => {
  if (!event.target.closest("#investigation-form")) return;
  readAnalysisControls(event.target.form, state.analysisDraft);
  state.previewSequence = (state.previewSequence || 0) + 1;
  state.previewCurrent = false;
  document.querySelector("#investigation-status").textContent = "Draft changed. Chart and details belong to the previous definition; Preview to update.";
});
document.addEventListener("change", async event => {
  const control = event.target, form = control.closest("#library-form, #investigation-form");
  if (!form || !control.closest(".analysis-controls")) return;
  event.stopImmediatePropagation();
  try {
    if (form.id === "library-form") { readLibraryDraft(); outdatedLibraryPreview(); replaceLibraryEditor(); }
    else {
      readAnalysisControls(form, state.analysisDraft);
      state.previewCurrent = false;
      replaceInvestigationControls();
      await previewSettings(state.analysisDraft.settings);
    }
  } catch (error) { notify(error.message); }
});
