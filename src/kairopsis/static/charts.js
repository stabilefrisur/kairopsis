const periodText = value => value === "all" ? "Longest available history" : value < 1 ? `${Math.round(value * 12)} months` : `${value} ${value === 1 ? "year" : "years"}`;
const periodValue = value => value === "all" ? "all" : Number(value);
/* Evidence rendering and image capture share the same resolved evaluation. */
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const number = (value, unit = "", signed = false) =>
  value == null
    ? "Unavailable"
    : `${signed && value >= 0 ? "+" : ""}${value !== 0 && Math.abs(value) < .005 ? Number(value).toExponential(3) : Number(value).toFixed(2)} ${esc(unit)}`;
const dateText = (date) =>
  date
    ? new Date(date.slice(0, 10) + "T12:00:00Z").toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      })
    : "Unknown";
const stamp = (value) =>
  new Date(value).toLocaleString("en-GB", {
    timeZone: "Europe/London",
    dateStyle: "medium",
    timeStyle: "short",
  });
const inputLabel = (s) =>
  `${s.name} · Source: ${s.source} · Symbol: ${s.instrument}${s.field ? " · Field: " + s.field : ""} · Units: ${s.unit} · Currency: ${s.currency}${s.basis ? " · Reference curve: " + s.basis.reference_curve : ""}`;
const comparisonLabel = (s) => (s.basis?.label || "").replace(/^Native\s+/i, "");
const adjustmentText = (s) =>
  s.basis?.adjustment === "None; fabricated native-market observations"
    ? "No currency or reference-curve adjustment"
    : s.basis?.adjustment || "";
const readableQuality = (text) =>
  text
    .replace(/native-unit/gi, "measurement-unit")
    .replace(/native[- ]market/gi, "original-market")
    .replace(/native[- ]dates?/gi, "source observation date")
    .replace(/native observation/gi, "source observation");
const riskMethodNames = {none: "None", volatility: "Volatility", beta: "Beta to reference", var: "Value at Risk (VaR)", es: "Expected Shortfall (CVaR)"};
function hasTransformedInputs(e) {
  return e.definition.settings.measure !== "level" || (e.adjustment_estimates || []).length > 0;
}
function effectiveRiskMeasure(settings, risk) {
  return risk.estimation_measure || (settings.measure === "return" ? "return" : "change");
}
function analysisFormula(d, inputs = d.inputs) {
  const s = d.settings, frequency = {day: "daily", week: "weekly", month: "monthly"}[s.horizon];
  const bindings = [...(inputs || []), ...(d.references || []), ...(typeof state !== "undefined" ? state.catalogue?.series || [] : [])];
  const legs = (inputs || []).map((b, i) => {
    let text = `${b.name} ${s.measure === "return" ? `${frequency} percentage change` : s.measure === "change" ? `${frequency} absolute change` : "level"}`;
    const r = s.risk_overrides?.[i] || s.risk_adjustment;
    if (r && r.method !== "none") {
      const ref = bindings.find(b => b.id === (r.reference_id || (inputs || [])[i]?.id))?.name || "this series";
      const basis = effectiveRiskMeasure(s, r) === "return" ? "percentage changes" : "absolute changes";
      const estimator = r.method === "volatility" ? `${r.weighting === "exponential" ? "exponentially weighted " : ""}SD` : r.method === "beta" ? "signed beta" : riskMethodNames[r.method];
      text += ` / ${estimator} of prior ${frequency} ${ref} ${basis} (${periodText(r.lookback_years)})`;
    }
    return text;
  });
  let text = d.calculation === "level" ? legs[0] : d.calculation === "regression" ? `Residual of (${legs[0]}) fitted on (${legs[1]})` : `(${legs[0]}) ${d.calculation === "ratio" ? "÷" : "−"} (${legs[1]})`;
  if (d.calculation === "ratio" && s.measure !== "level") text = "Ratio of changes: " + text;
  return s.standardization === "zscore" ? `Z-score of ${text}; ${periodText(s.history_years)} prior result reference` : text;
}
function analysisInterpretation(d) {
  if (d.settings.standardization === "zscore") return "Positive Z-score: the completed result exceeds its prior reference mean. Inspect the unstandardized magnitude and inputs; historical distance alone does not establish attractiveness.";
  return d.calculation === "regression" ? "Positive residual: first input exceeds its fitted relationship with the second. Association is descriptive." :
    d.calculation === "difference" ? "Positive result: first transformed input exceeds the second; assess economic comparability." :
    d.calculation === "ratio" ? "Relative magnitude of the numerator and signed denominator; sign alone does not establish attractiveness." :
    "Magnitude of this input under the selected measure and scaling; compare with its prior history.";
}
function riskDescription(e) {
  const settings = e.definition.settings;
  if (!hasTransformedInputs(e)) return [];
  const bindings = [...e.definition.inputs, ...(e.definition.references || [])];
  return e.definition.inputs.map((s, i) => {
    const r = settings.risk_overrides?.[i] || settings.risk_adjustment;
    const ref = bindings.find(b => b.id === r?.reference_id) || s;
    return `${s.name}: ${settings.measure === "level" ? "level numerator" : settings.horizon + (settings.measure === "return" ? " percentage change" : " absolute change")} · ${riskMethodNames[r?.method || "none"]}${r && r.method !== "none" ? ` / ${ref.name}; estimate from ${settings.horizon} ${effectiveRiskMeasure(settings, r) === "return" ? "percentage" : "absolute"} changes` : ""} · ${(e.input_units || [])[i] || s.unit}`;
  });
}
function chartFootnote(e, display = null) {
  const inputs = e.definition.inputs;
  const sources = inputs.map((s, i) =>
    `${s.source} · ${s.currency}${s.basis ? " / " + s.basis.reference_curve : ""}${s.basis && s.basis.currency !== s.currency ? " · Comparison currency: " + s.basis.currency : ""} · ${dateText(e.input_dates[i])}`,
  );
  const lines = new Set(sources).size === 1
    ? [sources[0]]
    : sources.map((source, i) => `${inputs[i].name}: ${source}`);
  if (e.data.mode === "mock") lines[0] = "Demo data · " + lines[0];
  const settings = e.definition.settings;
  if (hasTransformedInputs(e) && display?.view !== "underlying") {
    const frequency = {day: "Daily", week: "Weekly", month: "Monthly"}[settings.horizon];
    const bindings = [...inputs, ...(e.definition.references || [])];
    const adjustments = inputs.map((s, i) => {
      const r = settings.risk_overrides?.[i] || settings.risk_adjustment;
      if (!r || r.method === "none") return "Unadjusted";
      const ref = r.reference_id ? bindings.find(b => b.id === r.reference_id)?.name || s.name : "own series";
      return r.method === "beta" ? `Beta to ${ref}` : `${riskMethodNames[r.method]} / ${ref}`;
    });
    const adjustment = new Set(adjustments).size === 1
      ? adjustments[0]
      : adjustments.map((text, i) => `${inputs[i].name}: ${text}`).join("; ");
    lines.push(`${settings.measure === "level" ? "Level numerator" : frequency + (settings.measure === "return" ? " percentage changes" : " changes")} · ${adjustment}`);
    if (settings.calculation_contract === "input-pipeline-v2") lines.push(...riskDescription(e));
  }
  if (e.fit && display?.view !== "underlying")
    lines.push(
      `Regression fit: ${dateText(e.fit.start)}–${dateText(e.fit.end)}`,
    );
  if (settings.standardization === "zscore" && display?.view !== "underlying" && display?.view !== "changes" && display?.view !== "scatter")
    lines.push(`Z-score · ${periodText(settings.history_years)} prior reference`);
  return lines;
}
function detailList(items) {
  return `<dl class="chart-detail-list">${items.map(([label, value]) => `<dt>${esc(label)}</dt><dd>${esc(value)}</dd>`).join("")}</dl>`;
}
function sourceDetailsHTML(bindings, data, inputDates = []) {
  return bindings
    .map(
      (s, i) =>
        `<h3 class="disclosure-heading">${esc(s.name)}</h3>${detailList([
          ["Source", s.source],
          ["Instrument", s.instrument],
          ["Measure", s.field],
          ["Units", s.unit],
          ["Series currency", s.currency],
          ...(s.basis ? [
          ["Reference curve", s.basis.reference_curve],
          ...(comparisonLabel(s) !==
          `${s.currency} / ${s.basis.reference_curve}`
            ? [["Comparison basis", comparisonLabel(s)]]
            : []),
          ...(s.basis.currency !== s.currency
            ? [["Comparison currency", s.basis.currency]]
            : []),
          ["Adjustment", adjustmentText(s)],
          ] : []),
          ["Source observation date", dateText(inputDates[i] || data.series.find(row => row.binding.id === s.id)?.observations.at(-1)?.observed_on)],
        ])}`,
    )
    .join("");
}
function evidenceDetails(e, originalImage = "", display = null) {
  const settings = e.definition.settings;
  const sourceDetails = sourceDetailsHTML([...e.definition.inputs, ...(e.definition.references || [])], e.data, e.input_dates);
  const fitDetails = e.fit
    ? `<h3 class="disclosure-heading">Regression fit</h3>${detailList([
        [
          "Equation",
          `y = ${e.fit.intercept.toFixed(4)} + ${e.fit.slope.toFixed(4)}x`,
        ],
        ["R²", e.fit.r_squared?.toFixed(3) ?? "Unavailable"],
        ["Observations used", e.fit.sample_count],
        ["Fitted period", `${dateText(e.fit.start)}–${dateText(e.fit.end)}`],
      ])}`
    : "";
  const z = e.standardization_estimate;
  const standardizationDetails = z ? `<h3 class="disclosure-heading">Z-score reference</h3>${detailList([
    ["Mean", number(z.mean, z.unit)], ["Sample standard deviation", number(z.standard_deviation, z.unit)],
    ["Observations used", z.sample_count], ["Reference period", `${dateText(z.start)}–${dateText(z.end)}`],
    ["Chart baseline", "Current reference applied throughout; latest observation excluded"],
  ])}` : "";
  const rows = e.points
    .slice(-30)
    .map(
      (p) =>
        `<tr><td>${dateText(p.date)}</td><td>${number(p.value)}</td>${z ? `<td>${number(p.unstandardized_value)}</td>` : ""}${p.inputs.map((v, i) => `<td>${number(v)}</td><td>${dateText(p.observed_on[i])}</td>${hasTransformedInputs(e) ? `<td>${number(p.transformed_inputs[i], e.input_units[i])}</td><td>${number(p.risk_scales[i])}</td><td>${dateText(p.period_start[i])}</td>` : ""}`).join("")}</tr>`,
    )
    .join("");
  return `<div class="evidence-details"><p class="meta chart-footnote">${chartFootnote(e, display).map(esc).join("<br>")}</p><details><summary>Source and chart details</summary>${sourceDetails}<h3 class="disclosure-heading">Chart settings</h3>${detailList(
    [
      [
        "Calculation",
        {
          level: "Standalone",
          difference: "First series minus second series",
          ratio: "First series divided by second series",
          regression: "Regression residual",
        }[e.definition.calculation],
      ],
      ...(display
        ? [
            ["Displayed period", periodText(display.years)],
            [
              "Chart view",
              {
                analysis: "Analysis",
                underlying: "Underlying series",
                scatter: "Regression scatter",
                changes: "Measured / adjusted series",
              }[display.view],
            ],
          ]
        : []),
      ["Reference history", `${periodText(settings.history_years)}`],
      ["Formula", analysisFormula(e.definition)],
      ["Output units", e.unit],
      ["Calculation contract", settings.calculation_contract || "input-pipeline-v1"],
      ...(settings.standardization === "zscore" ? [["Standardization", "Z-score of completed analysis"], ["Z-score threshold", `±${settings.zscore_threshold}`]] : []),
      ["Frequency", settings.horizon],
      ["Measure", {level: "Level", change: "Change", return: "Percentage change"}[settings.measure || "level"]],
      ...riskDescription(e).map(text => ["Risk adjustment", text]),
      ...(e.adjustment_estimates || []).flatMap((r, i) => {
        const options = settings.risk_overrides?.[i] || settings.risk_adjustment;
        return options?.method !== "none" ? [["Estimation basis", `${r.estimation_measure || effectiveRiskMeasure(settings, options)}; cutoff ${dateText(r.cutoff)}`], ["Estimation settings", `${periodText(options.lookback_years)}; ${options.method === "volatility" ? options.weighting + (options.weighting === "exponential" ? "; half-life " + options.half_life + " sessions" : "") : ["var", "es"].includes(options.method) ? options.confidence + "% confidence; downside " + options.downside : "intercept OLS"}`], ["Estimated scale", `${r.scale ?? "Unavailable"}; ${r.sample_count} observations; ${dateText(r.start)}–${dateText(r.end)}`]] : [];
      }),
      ...(e.definition.calculation === "regression"
        ? [["Fitting window", `${periodText(settings.fit_years)}`]]
        : []),
    ],
  )}${fitDetails}${standardizationDetails}<h3 class="disclosure-heading">Data and quality</h3>${detailList(
    [
      ["Retrieved", stamp(e.data.completed_at)],
      ["Evaluated through", dateText(e.request.end)],
    ],
  )}<p class="meta">${e.data.mode === "mock" ? "Synthetic demo data; no live provider connection. Flag thresholds are illustrative; risk-adjusted monitoring thresholds require calibration." : esc(e.data.series.map((s) => readableQuality(s.provenance)).join(" / "))}</p>${[...e.limitations, ...e.sensitivity].map((x) => `<p class="meta">${esc(readableQuality(x))}</p>`).join("")}<p class="meta">Source observation date means the date the value was observed. It can differ from the date shown on the chart.</p>${originalImage ? `<p class="meta"><a href="${esc(originalImage)}" download="kairopsis-original.png">Download original saved image</a></p>` : ""}<div class="table-region" role="region" aria-label="Underlying observations" tabindex="0"><table><thead><tr><th>Chart date</th><th>Calculated ${esc(e.unit)}</th>${z ? `<th>Before standardization (${esc(z.unit)})</th>` : ""}${e.definition.inputs.map((s, i) => `<th>${esc(s.name)} (${esc(s.unit)})</th><th>Source date</th>${hasTransformedInputs(e) ? `<th>Transformed (${esc(e.input_units[i])})</th><th>Risk scale</th><th>Measurement start</th>` : ""}`).join("")}</tr></thead><tbody>${rows}</tbody></table></div></details></div>`;
}
function displayedPoints(e, display) {
  return e.points.filter(p => p.date >= displayStart(e.observation_date || e.request.end, display.years));
}
function displayStart(end, period) {
  if (period === "all") return "1677-09-22";
  const start = new Date(end + "T12:00:00Z"), day = start.getUTCDate();
  start.setUTCDate(1);
  start.setUTCMonth(start.getUTCMonth() - Math.round(period * 12));
  const lastDay = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 0)).getUTCDate();
  start.setUTCDate(Math.min(day, lastDay));
  return start.toISOString().slice(0, 10);
}
async function copyData(element) {
  const { evaluation: e, display } = element.evidence;
  const headers = [
    "Chart date",
    `Calculated ${e.unit}`,
    ...(e.standardization_estimate ? [`Before standardization (${e.standardization_estimate.unit})`] : []),
    ...e.definition.inputs.flatMap((s) => [
      `${s.name} (${s.unit})`,
      "Source date",
    ]),
    ...(hasTransformedInputs(e) ? e.definition.inputs.flatMap((s, i) => [`Measured / adjusted ${s.name} (${e.input_units[i]})`, "Risk scale", "Change start"]) : []),
  ];
  const rows = displayedPoints(e, display).map((p) => [
    p.date,
    p.value,
    ...(e.standardization_estimate ? [p.unstandardized_value] : []),
    ...p.inputs.flatMap((value, i) => [value, p.observed_on[i]]),
    ...(hasTransformedInputs(e) ? e.definition.inputs.flatMap((s, i) => [p.transformed_inputs[i], p.risk_scales[i], p.period_start[i]]) : []),
  ]);
  const cell = (value) => {
    const text = String(value ?? "");
    return /[\t\r\n"]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  const text = [
    headers.map((label) => (/^[=+@-]/.test(label) ? "'" + label : label)),
    ...rows,
  ]
    .map((row) => row.map(cell).join("\t"))
    .join("\n");
  try {
    await navigator.clipboard.writeText(text);
    notify("Data copied. Paste into a spreadsheet to keep the columns.");
  } catch {
    downloadBlob(
      new Blob([text], { type: "text/tab-separated-values;charset=utf-8" }),
      "kairopsis-data.tsv",
    );
    notify("Clipboard unavailable. Data downloaded instead.");
  }
}
async function plotEvidence(element, e, display, exporting = false) {
  element.evidence = { evaluation: e, display: structuredClone(display) };
  const points = displayedPoints(e, display);
  const traces = [];
  let xTitle = "",
    yTitle =
      e.definition.calculation === "regression"
        ? `Residual (${e.unit})`
        : e.unit;
  const measured = p => p.transformed_inputs?.length ? p.transformed_inputs : p.inputs;
  const inputUnits = e.input_units?.length ? e.input_units : e.definition.inputs.map(s => s.unit);
  if (display.view === "scatter" && e.definition.calculation === "regression") {
    const p = points.filter((p) => p.eligible && measured(p).every((v) => v != null));
    traces.push({
      x: p.map((p) => measured(p)[1]),
      y: p.map((p) => measured(p)[0]),
      mode: "markers",
      type: "scatter",
      name: "Aligned observations",
      marker: { size: 5, color: "#255cc5" },
    });
    if (e.fit)
      traces.push({
        x: [e.fit.x_min, e.fit.x_max],
        y: [
          e.fit.intercept + e.fit.slope * e.fit.x_min,
          e.fit.intercept + e.fit.slope * e.fit.x_max,
        ],
        mode: "lines",
        name: "Selected fit",
        line: { color: "#9180a8" },
      });
    xTitle = `${e.definition.inputs[1].name} (${inputUnits[1]})`;
    yTitle = `${e.definition.inputs[0].name} (${inputUnits[0]})`;
  } else if (["underlying", "changes"].includes(display.view)) {
    e.definition.inputs.forEach((s, i) =>
      traces.push({
        x: points.map((p) => p.date),
        y: points.map((p) => display.view === "changes" ? (p.transformed_inputs || [])[i] : p.inputs[i]),
        type: "scatter",
        mode: "lines",
        name: `${s.name} (${display.view === "changes" ? inputUnits[i] : s.unit})`,
        yaxis: i && (display.view === "underlying" || inputUnits[0] !== inputUnits[1]) ? "y2" : "y",
        line: { width: 2, color: i ? "#9180a8" : "#255cc5" },
      }),
    );
    yTitle = display.view === "changes" ? inputUnits[0] : `${e.definition.inputs[0].name} (${e.definition.inputs[0].unit})`;
  } else
    traces.push({
      x: points.map((p) => p.date),
      y: points.map((p) => p.value),
      type: "scatter",
      mode: "lines",
      name: e.definition.name,
      line: { width: 2, color: "#255cc5" },
      connectgaps: false,
    });
  const info = chartFootnote(e, display);
  const layout = chartLayout(e.definition.name, xTitle, yTitle, display, info, exporting, e.definition.inputs.length);
  if (display.view === "analysis" && e.definition.settings.standardization === "zscore") {
    const threshold = e.definition.settings.zscore_threshold;
    layout.shapes = [-threshold, threshold].map(value => ({type: "line", xref: "paper", x0: 0, x1: 1, yref: "y", y0: value, y1: value, line: {color: "#9180a8", width: 1, dash: "dash"}}));
  }
  if ((display.view === "underlying" || display.view === "changes" && inputUnits[0] !== inputUnits[1]) && e.definition.inputs.length > 1)
    layout.yaxis2 = {
      title: {
        text: `${esc(e.definition.inputs[1].name)} (${esc(display.view === "changes" ? inputUnits[1] : e.definition.inputs[1].unit)})`,
      },
      overlaying: "y",
      side: "right",
      showgrid: false,
      automargin: true,
      fixedrange: true,
    };
  await renderPlot(element, traces, layout, display, exporting);
}
function chartLayout(name, xTitle, yTitle, display, info, exporting, inputCount) {
  return {
    title: {
      text: esc(name),
      font: { size: 20 },
      x: 0.06,
      y: 0.98,
      yanchor: "top",
    },
    font: {
      family: "Segoe UI,Arial,sans-serif",
      color: "#203047",
      size: exporting ? 16 : 13,
    },
    paper_bgcolor: "#fff",
    plot_bgcolor: "#fff",
    margin: {
      t: display.view === "analysis" ? 60 : 110,
      l: 80,
      r:
        ["underlying", "changes"].includes(display.view) && inputCount > 1
          ? 110
          : 30,
      b: exporting ? 140 + (info.length - 1) * 20 : 70,
    },
    xaxis: {
      title: { text: esc(xTitle) },
      gridcolor: "#e6ecf4",
      automargin: true,
      fixedrange: true,
    },
    yaxis: {
      title: { text: esc(yTitle) },
      gridcolor: "#e6ecf4",
      automargin: true,
      fixedrange: true,
    },
    showlegend: display.view !== "analysis",
    legend: {
      orientation: "h",
      y: 1.02,
      yanchor: "bottom",
      itemclick: exporting ? false : "toggle",
      itemdoubleclick: exporting ? false : "toggleothers",
    },
    dragmode: false,
    annotations: exporting
      ? [
          {
            text: info.map(esc).join("<br>"),
            xref: "paper",
            yref: "paper",
            x: 0,
            y: 0,
            yshift: -75,
            xanchor: "left",
            yanchor: "top",
            showarrow: false,
            align: "left",
            font: { size: 14, color: "#627185" },
          },
        ]
      : [],
  };
}
async function renderPlot(element, traces, layout, display, exporting = false) {
  element.removeAllListeners?.("plotly_restyle");
  await Plotly.newPlot(element, traces, layout, {
    responsive: true,
    displayModeBar: false,
    doubleClick: false,
    scrollZoom: false,
  });
  // Establish ranges with every trace present, then lock them before hiding any.
  // The captured ranges also preserve the same scale in PNGs and reopened evidence.
  const ranges = {}, updates = {};
  for (const axis of ["xaxis", "yaxis", "yaxis2"]) {
    if (!element._fullLayout[axis]) continue;
    ranges[axis] = [...(display.axis_ranges?.[axis] || element._fullLayout[axis].range)];
    updates[`${axis}.range`] = ranges[axis];
    updates[`${axis}.autorange`] = false;
  }
  element.evidence.display.axis_ranges = ranges;
  await Plotly.relayout(element, updates);
  const hidden = display.hidden_traces || [];
  await Plotly.restyle(element, {visible: traces.map((_, i) => hidden.includes(i) ? "legendonly" : true)});
  const rememberDisplay = () => {
    element.evidence.display.hidden_traces = element.data.flatMap((trace, i) => trace.visible === "legendonly" ? [i] : []);
    if (!exporting) element.dispatchEvent(new CustomEvent("chart-display-change", {
      bubbles: true, detail: structuredClone(element.evidence.display),
    }));
  };
  rememberDisplay();
  if (!exporting) element.on("plotly_restyle", rememberDisplay);
}
async function chartPNG(element) {
  const exportPlot = document.createElement("div");
  exportPlot.style.cssText =
    "position:fixed;left:-10000px;width:1500px;height:900px";
  document.body.append(exportPlot);
  try {
    await plotEvidence(
      exportPlot,
      element.evidence.evaluation,
      element.evidence.display,
      true,
    );
    return await Plotly.toImage(exportPlot, {
      format: "png",
      width: 1500,
      height: 900,
      scale: 1,
    });
  } finally {
    Plotly.purge(exportPlot);
    exportPlot.remove();
  }
}
async function plotSeries(element, preview, display) {
  const row = preview.data.series[0];
  const points = row.observations.filter(p => p.date >= displayStart(preview.request.end, display.years));
  element.evidence = {series: preview, display: structuredClone(display)};
  const traces = [{x: points.map(p => p.date), y: points.map(p => p.value), type: "scatter", mode: "lines",
    name: row.binding.name, line: {width: 2, color: "#255cc5"}, connectgaps: false}];
  await renderPlot(element, traces, chartLayout(row.binding.name, "", row.binding.unit,
    {...display, view: "analysis"}, [], false, 1), display);
}
function seriesPreviewDetails(preview, display) {
  const data = preview.data, row = data.series[0], binding = row.binding;
  const points = row.observations.filter(p => p.date >= displayStart(preview.request.end, display.years));
  const footnote = `${data.mode === "mock" ? "Demo data · " : ""}${binding.source} · ${binding.currency} · ${dateText(row.observations.at(-1)?.observed_on)}`;
  return `<div class="evidence-details"><p class="meta chart-footnote">${esc(footnote)}</p><details><summary>Source and chart details</summary>${sourceDetailsHTML([binding], data)}${detailList([
    ["Displayed period", periodText(display.years)], ["Retrieved", stamp(data.completed_at)],
    ["Requested through", dateText(preview.request.end)], ["Query range", `${dateText(preview.request.start)}–${dateText(preview.request.end)}`],
  ])}<p class="meta">${esc(readableQuality(row.provenance))}</p>${data.failures.map(f => `<p class="warning">${esc(f.message)}</p>`).join("")}<p class="meta">Source observation dates can differ from chart dates; unknown dates remain unknown.</p><div class="table-region" role="region" aria-label="Underlying observations" tabindex="0"><table><thead><tr><th>Chart date</th><th>${esc(binding.name)} (${esc(binding.unit)})</th><th>Source date</th></tr></thead><tbody>${points.slice(-30).map(p => `<tr><td>${dateText(p.date)}</td><td>${number(p.value)}</td><td>${dateText(p.observed_on)}</td></tr>`).join("")}</tbody></table></div></details></div>`;
}
function downloadBlob(blob, name = "kairopsis-chart.png") {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
async function reuseBlob(blob, copy) {
  if (!copy) {
    downloadBlob(blob);
    return;
  }
  try {
    await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
    notify("Chart copied. Exact displayed evidence retained.");
  } catch {
    downloadBlob(blob);
    notify("Clipboard unavailable. Chart downloaded instead.");
  }
}
