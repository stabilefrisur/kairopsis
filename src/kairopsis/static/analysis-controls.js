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
  if (settings.reference_mode !== "fixed") { settings.reference_start = null; settings.reference_end = null; }
  settings.risk_adjustment = activeRisk(settings.risk_adjustment);
  if (settings.risk_overrides?.length) settings.risk_overrides = settings.risk_overrides.map(activeRisk);
  return {...draft, series_ids: draft.series_ids.slice(0, draft.calculation === "level" ? 1 : 2), settings};
}
function analysisControlContext(context) {
  return context || {series: librarySeriesChoices(), analyses: state.catalogue.analyses,
    memory: state.controlMemory ||= {}, notice: text => { state.thresholdNotice = text; },
    thresholdNotice: state.thresholdNotice || "", monitoring: true};
}
function analysisFromEvaluation(e, context) {
  const ctx = analysisControlContext(context);
  const d = e.definition;
  return {id: d.id, revision: d.revision, name: d.name, calculation: d.calculation,
    economic_rationale: d.economic_rationale || "",
    series_ids: d.inputs.map(s => s.id), monitored: ctx.analyses.find(a => a.id === d.id)?.monitored || false,
    settings: structuredClone(d.settings)};
}
function formulaSignature(d) {
  const s = d.settings;
  return JSON.stringify([d.calculation, d.series_ids, s.measure || "level", s.horizon, s.standardization || "none",
    ...(d.calculation === "regression" ? [s.fit_mode || "current", s.fit_years] : []),
    ...(s.standardization === "zscore" ? [s.reference_mode || "current", s.history_years, s.reference_start, s.reference_end] : []),
    riskOptions(s, d.series_ids.length).map(r => r.method === "none" ? ["none"] :
      [r.method, r.reference_id, r.estimation_measure || null, r.lookback_years,
        ...(r.method === "volatility" ? [r.weighting, r.weighting === "exponential" ? r.half_life : null] : []),
        ...(["var", "es"].includes(r.method) ? [r.confidence, r.downside] : [])])]);
}
function readAnalysisControls(form, d, context) {
  const ctx = analysisControlContext(context);
  const previous = formulaSignature(d), s = d.settings;
  const value = name => form.elements.namedItem(name)?.value;
  const memo = ctx.memory[d.id] ||= {};
  if (value("name") != null) d.name = value("name");
  if (value("economic_rationale") != null) d.economic_rationale = value("economic_rationale");
  if (d.calculation !== "level") memo.pairCalculation = d.calculation;
  if (value("right")) memo.right = value("right");
  if (s.risk_overrides?.length > 1) memo.overrides = structuredClone(s.risk_overrides);
  const pair = value("analysis_type") === "pair";
  d.calculation = pair ? value("calculation") || memo.pairCalculation || "difference" : "level";
  if (pair) memo.pairCalculation = d.calculation;
  d.series_ids = [value("left") || d.series_ids[0], ...(pair ? [memo.right || ctx.series.find(b => b.id !== (value("left") || d.series_ids[0]))?.id] : [])];
  for (const [name, field] of [["measure", "measure"], ["horizon", "horizon"], ["standardization", "standardization"], ["reference_mode", "reference_mode"], ["fit_mode", "fit_mode"]]) {
    if (value(name) != null) s[field] = value(name);
  }
  for (const [name, field] of [["history", "history_years"], ["fit", "fit_years"]]) {
    if (value(name) != null) s[field] = periodValue(value(name));
  }
  for (const name of ["reference_start", "reference_end"]) {
    if (value(name)) memo[name] = value(name);
    s[name] = s.reference_mode === "fixed" ? value(name) ?? memo[name] ?? null : null;
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
    ctx.notice("Calculation changed. Optional move/materiality thresholds cleared; reconsider them in the resulting units.");
    for (const name of ["move", "material"]) if (form.elements[name]) form.elements[name].value = "";
  }
  return d;
}
function analysisControls(d, estimates = [], context) {
  const ctx = analysisControlContext(context);
  const s = d.settings, pair = d.calculation !== "level";
  const select = (label, name, selected, values) => `<label>${label}<select name="${name}" data-analysis-control="${name}">${values.map(([v, label]) => `<option value="${esc(v)}" ${String(selected) === String(v) ? "selected" : ""}>${esc(label)}</option>`).join("")}</select></label>`;
  const periods = (label, name, selected) => select(label, name, selected, periodChoices(selected).map(n => [n, periodText(n)]));
  const input = (label, name, id) => `<label>${label}<select name="${name}" data-analysis-control="${name}" required>${seriesOptions(id, ctx.series)}</select></label>`;
  const roles = d.calculation === "ratio" ? ["Numerator", "Denominator"] : d.calculation === "regression" ? ["Dependent series (y)", "Explanatory series (x)"] : ["First input", "Second input"];
  const bindings = d.series_ids.map(id => ctx.series.find(b => b.id === id) || {id, name: "Choose a series"});
  const zscore = s.standardization === "zscore";
  const referenceFields = `<div class="fields">${select("Reference period", "reference_mode", s.reference_mode || "current", [["current", "As-of window"], ["rolling", "Rolling window"], ["fixed", "Fixed dates"]])}${s.reference_mode === "fixed" ? field("Reference start", "reference_start", s.reference_start, "date") + field("Reference end", "reference_end", s.reference_end, "date") : periods("Reference history", "history", s.history_years)}</div>`;
  const incompleteReference = s.reference_mode === "fixed" && (!s.reference_start || !s.reference_end || s.reference_start > s.reference_end);
  const referenceHelp = s.reference_mode === "fixed" ? "Both dates included; end before the latest observation." : "Uses the preceding history at the latest observation, excluding that observation.";
  const zscoreHelp = s.reference_mode === "fixed" ? "One calendar period supplies the mean and SD for every chart point. Both dates included; end before the latest observation." : s.reference_mode === "rolling" ? "Each Z-score uses the preceding window at that date, excluding that observation. Early points need enough prior history." : "One window ending before the latest observation supplies the mean and SD for the entire chart. This window advances on later evaluations.";
  return `<div class="analysis-controls"><fieldset><legend>Inputs</legend><div class="fields">${select("Type", "analysis_type", pair ? "pair" : "standalone", [["standalone", "Standalone"], ["pair", "Pair"]])}${input(pair ? roles[0] : "Data series", "left", d.series_ids[0])}${pair ? input(roles[1], "right", d.series_ids[1]) : ""}</div></fieldset>
    <fieldset><legend>Measure</legend><div class="fields">${select("Input measure", "measure", s.measure || "level", [["level", "Level"], ["change", "Change"], ["return", "Percentage change"]])}${select("Frequency", "horizon", s.horizon, [["day", "Daily"], ["week", "Weekly"], ["month", "Monthly"]])}</div></fieldset>
    <fieldset><legend>Scale inputs</legend>${riskEditor(s, bindings, estimates, ctx.series)}<p class="meta">Estimates exclude the current Frequency interval. Level numerators remain levels. Sparse tail estimates need economic scrutiny; self-beta equals one when defined.</p></fieldset>
    ${pair ? `<fieldset><legend>Compare</legend><div class="fields">${select("Calculation", "calculation", d.calculation, [["difference", "Difference"], ["ratio", "Ratio"], ["regression", "Regression residual"]])}${d.calculation === "regression" ? select("Fitting period", "fit_mode", s.fit_mode || "current", [["current", "As-of window"], ["rolling", "Rolling window"]]) + periods("Fitting history", "fit", s.fit_years) : ""}</div>${d.calculation === "regression" ? `<p class="meta fit-help">${s.fit_mode === "rolling" ? "Each residual uses a fit estimated from earlier observations at that date. " + (s.fit_years === "all" ? "Longest available history expands over time." : "The selected history rolls forward with each date.") + " Early points need enough fitting history." : "One fit, estimated before the latest observation, applies throughout the chart. Historical residuals use today's relationship."} Fitting and Z-score reference periods are independent.</p>` : d.calculation === "ratio" ? '<p class="meta">Signed and near-zero denominators can dominate ratios. A shared common divisor cancels. Ratios of changes describe relative moves.</p>' : ""}</fieldset>` : ""}
    <fieldset><legend>Output</legend>${select("Output scale", "standardization", s.standardization || "none", [["none", "Original units"], ["zscore", "Z-score"]])}${zscore ? `${referenceFields}<p class="meta reference-help">${zscoreHelp} Percentile ranks the latest unstandardized result within its reference sample.${d.calculation === "regression" && s.fit_mode !== "rolling" ? " Regression residuals still use the current fit throughout; rolling Z-scores do not make this a historical backtest." : ""}</p><p class="meta">Z-score does not establish mean reversion.</p>` : `<p class="meta">Original units retain any input scaling.</p><details class="percentile-reference" ${incompleteReference ? "open" : ""}><summary>Percentile reference</summary><p class="meta reference-help">Controls percentile and monitoring; chart values stay unchanged. ${referenceHelp}</p>${referenceFields}</details>`}</fieldset>
    <p class="formula">${esc(analysisFormula(d, bindings))}</p><p class="meta">${esc(analysisInterpretation(d))}</p>
    ${ctx.monitoring === false ? '<p class="meta">Local calculation. Library publication and monitoring require explicit Library actions.</p>' : `<details class="monitoring-controls"><summary>Monitoring · ${d.monitored ? "enabled" : "disabled"}</summary><label class="monitor"><input name="monitored" type="checkbox" ${d.monitored ? "checked" : ""}> Include in flag monitoring</label><div class="fields">${s.standardization === "zscore" ? field("Z-score threshold (±)", "z_threshold", s.zscore_threshold ?? 2, "number") : field("Upper percentile rule (lower tail symmetric)", "upper", s.upper_percentile ?? 95, "number")}${field("Flag move at or above (optional)", "move", s.move_threshold, "number", false) + `<p class="meta">Absolute ${s.measure === "level" || !s.measure ? "change in the result over the selected Frequency" : "current calculated change/return result"}. Uses output units${s.standardization === "zscore" ? " (σ)" : ""}. Blank disables this rule.</p>`}${field("Flag again after a change of (optional)", "material", s.material_change, "number", false) + `<p class="meta">Minimum change, in either direction, since the comparison evaluation while a flag remains active. Uses output units${s.standardization === "zscore" ? " (σ)" : ""}; previous fit/Z-score reference held fixed. Blank disables repeat-change flags.</p>`}</div><p class="meta threshold-notice">${esc(ctx.thresholdNotice || "Thresholds require separate calibration. Save explicitly to change Library defaults.")}</p></details>`}</div>`;
}
function replaceInvestigationControls() {
  const form = document.querySelector("#investigation-form"), focused = document.activeElement;
  const open = analysisDisclosureState(form);
  const selector = focused.dataset.risk ? `[data-risk="${focused.dataset.risk}"][data-leg="${focused.dataset.leg}"]` : focused.name ? `[name="${CSS.escape(focused.name)}"]` : focused.hasAttribute("data-risk-customize") ? "[data-risk-customize]" : null;
  form.innerHTML = editorFormFields();
  restoreAnalysisDisclosures(form, open);
  if (selector) form.querySelector(selector)?.focus({preventScroll: true});
}
function analysisDisclosureState(root) {
  return new Map([...(root?.querySelectorAll(".analysis-controls details") || [])].map(d => [d.className, d.open]));
}
function restoreAnalysisDisclosures(root, open) {
  root.querySelectorAll(".analysis-controls details").forEach(d => { if (open.get(d.className)) d.open = true; });
}
document.addEventListener("input", event => {
  if (!event.target.closest("#investigation-form")) return;
  readAnalysisControls(event.target.form, state.analysisDraft);
  scheduleAnalysisPreview();
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
      scheduleAnalysisPreview();
    }
  } catch (error) { notify(error.message); }
});
