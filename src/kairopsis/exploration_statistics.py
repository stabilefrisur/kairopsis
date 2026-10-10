"""Descriptive statistics over retained exploration rows; no retrieval or Analysis.

Each row has a unique ``id``, ``symbol``, ``date`` and ``values`` mapping.
Missing/nonfinite values never become zeros. Every summary retains contributing
row IDs; plot arrays are emitted here so the browser has no statistics path.

Conventions: OLS includes an intercept, equal observation weights, descriptive
R² (unavailable for constant y), and explicit fit/evaluation samples. Panel fits
require allow_pooled_fit. Pearson requires two nonconstant paired observations;
Spearman uses average tied ranks then Pearson. Common correlation uses complete
rows across every selected column; pairwise retains each cell's exact sample.
KDE is Gaussian, Scott bandwidth (unbiased weighted SD * effective n**(-1/5)),
with normalized equal-row/equal-member weights; fewer than three or constant
observations remain points. Positive bandwidth_multiplier scales the resolved
base bandwidth once (also for shared smoothing). A distribution's default marker
is its latest retained finite row by actual field date, bounded by optional as_of;
ties use row ID, and any explicit selection disables this default.
History preserves original units; incompatible/unknown units have independent
aligned y scales. Ranked interval comparisons preserve ranking values separately
from retained start/end levels, dates and original units; no endpoint recomputation.
Histograms are left-closed/right-open except the
final closed bin, with probability-density heights. Equal-row box quartiles
are Hyndman/Fan type 7; equal-member quartiles use weighted inverse CDF.
Tukey whiskers are observed extrema within 1.5 IQR fences. No inferential claims.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from math import ceil, exp, fsum, isfinite, pi, sqrt
from typing import Any


Row = Mapping[str, Any]


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if isfinite(value) else None


def _value(row: Row, axis: str) -> float | None:
    return _number(row.get("values", {}).get(axis))


def _finite_number(value: float | None) -> float:
    """Narrow a value only after its row has passed finite-value selection."""
    if value is None:
        raise ValueError("Unavailable value entered a finite statistical sample")
    return value


def _finite_value(row: Row, axis: str) -> float:
    return _finite_number(_value(row, axis))


def _ids(rows: Sequence[Row]) -> list[str]:
    return [str(row["id"]) for row in rows]


def _ranks(values: Sequence[float]) -> list[float]:
    ordered = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        for position in ordered[start:end]:
            ranks[position] = (start + 1 + end) / 2
        start = end
    return ranks


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) < 2:
        return None
    x_mean, y_mean = fsum(xs) / len(xs), fsum(ys) / len(ys)
    dx, dy = [x - x_mean for x in xs], [y - y_mean for y in ys]
    sx, sy = fsum(x * x for x in dx), fsum(y * y for y in dy)
    if sx == 0 or sy == 0:
        return None
    return max(-1.0, min(1.0, fsum(x * y for x, y in zip(dx, dy)) / sqrt(sx * sy)))


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _weights(rows: Sequence[Row], policy: str) -> list[float]:
    if not rows:
        return []
    if policy == "equal_row":
        return [1 / len(rows)] * len(rows)
    if policy != "equal_member":
        raise ValueError("weight_policy must be equal_row or equal_member")
    counts = Counter(str(row.get("symbol", "")) for row in rows)
    return [1 / (len(counts) * counts[str(row.get("symbol", ""))]) for row in rows]


def _weighted_quantile(values: Sequence[float], weights: Sequence[float], p: float) -> float:
    cumulative = 0.0
    for value, weight in sorted(zip(values, weights)):
        cumulative += weight
        if cumulative >= p:
            return value
    return max(values)


def _axes(rows: Sequence[Row], options: Mapping[str, Any]) -> list[str]:
    selected = options.get("axes") or options.get("measures")
    if selected:
        return list(dict.fromkeys(str(axis) for axis in selected))
    return list(dict.fromkeys(str(axis) for row in rows for axis in row.get("values", {})))


def _trace_rows(rows: Sequence[Row]) -> list[list[str]]:
    return [[str(row["id"]), str(row.get("symbol", "")), str(row.get("date", ""))] for row in rows]


def _axis_title(axis: str, options: Mapping[str, Any]) -> str:
    unit = options.get("units", {}).get(axis)
    return f"{axis} ({unit})" if unit else axis


def _attribute(row: Row, key: str) -> str:
    value = row.get("attributes", {}).get(key)
    if key == "symbol":
        value = row.get("symbol")
    return "Unknown" if value is None else str(value)


def _scatter_traces(rows: list[Row], x: str, y: str, options: dict[str, Any], result: dict[str, Any]) -> None:
    size_by = str(options.get("size_by") or "")
    sizes = {str(row["id"]): 9.0 for row in rows}
    if size_by and size_by != "none":
        valid = [row for row in rows if _value(row, size_by) is not None and _finite_value(row, size_by) >= 0]
        valid_ids = set(_ids(valid))
        invalid = [{"row_id": str(row["id"]), "reason": "Missing/nonfinite size" if _value(row, size_by) is None else "Negative size"}
            for row in rows if str(row["id"]) not in valid_ids]
        largest = max((_finite_value(row, size_by) for row in valid), default=0.0)
        if largest > 0:
            sizes.update({str(row["id"]): 30 * sqrt(_finite_value(row, size_by) / largest) for row in valid})
            result["size_legend"] = {"field": size_by, "unit": options.get("units", {}).get(size_by),
                "values": [largest / 9, largest * 4 / 9, largest], "sizes": [10, 20, 30],
                "formula": "diameter_px = 30 × sqrt(value / maximum)", "zero_policy": "zero-area"}
        else:
            result["limitations"].append("No positive marker sizes; constant size retained")
        result["sizing"] = {"field": size_by, "invalid_rows": invalid, "fallback_size_px": 9}
        if invalid:
            result["limitations"].append(f"{len(invalid)} missing/negative marker sizes use constant size")
    color_by, facet_by = str(options.get("color_by") or ""), str(options.get("facet_by") or "")
    numeric_color = bool(color_by and any(color_by in row.get("values", {}) for row in rows))
    color_values = [_finite_value(row, color_by) for row in rows if numeric_color and _value(row, color_by) is not None]
    groups: dict[tuple[str, str], list[Row]] = defaultdict(list)
    for row in rows:
        facet = _attribute(row, facet_by) if facet_by else "All"
        color = ("Numeric" if _value(row, color_by) is not None else "Missing colour") if numeric_color else (_attribute(row, color_by) if color_by else "Observations")
        groups[(facet, color)].append(row)
    facets = list(dict.fromkeys(facet for facet, _ in groups)) or ["All"]
    result["facets"] = [{"name": facet, "row_ids": _ids([row for (name, _), selected in groups.items() if name == facet for row in selected])}
        for facet in facets] if facet_by else []
    for (facet, color), sample in groups.items():
        index = facets.index(facet) + 1
        suffix = "" if index == 1 else str(index)
        marker: dict[str, Any] = {"size": [sizes[str(row["id"])] for row in sample], "sizemode": "diameter"}
        if numeric_color and color == "Numeric":
            marker.update(color=[_value(row, color_by) for row in sample], colorscale="Viridis", showscale=True,
                colorbar={"title": _axis_title(color_by, options)}, cmin=min(color_values), cmax=max(color_values))
        elif numeric_color:
            marker["color"] = "#999999"
        result["traces"].append({"type": "scatter", "mode": "markers", "name": color if not facet_by else f"{facet} · {color}",
            "x": [_value(row, x) for row in sample], "y": [_value(row, y) for row in sample],
            "xaxis": f"x{suffix}", "yaxis": f"y{suffix}", "customdata": _trace_rows(sample), "marker": marker})
        result["layout"][f"xaxis{suffix}"] = {"title": _axis_title(x, options)}
        result["layout"][f"yaxis{suffix}"] = {"title": _axis_title(y, options)}
    if facet_by:
        columns = min(2, len(facets))
        result["layout"]["grid"] = {"rows": ceil(len(facets) / columns), "columns": columns, "pattern": "independent"}
        result["algorithm"]["faceting"] = {"field": facet_by, "source": "supplied-attributes", "unknown": "explicit"}
    if numeric_color:
        missing = [str(row["id"]) for row in rows if _value(row, color_by) is None]
        result["colour"] = {"field": color_by, "unit": options.get("units", {}).get(color_by), "missing_row_ids": missing}
        if missing:
            result["limitations"].append(f"{len(missing)} missing colour values shown in grey")


def summarize(family: str, rows: Sequence[Row], options: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return JSON-ready evidence and Plotly traces from an already resolved sample.

    Options select axes, family form and explicit descriptive algorithms only.
    A separate ``fit_rows`` sample is permitted for scatter fitting; caller owns
    its provenance and selection. Input rows/options are never mutated.
    """
    options = dict(options or {})
    rows = list(rows)
    if len(set(_ids(rows))) != len(rows):
        raise ValueError("Retained row IDs must be unique")
    family = "ranked" if family in {"ranking", "rank"} else family
    axes = _axes(rows, options)
    result: dict[str, Any] = {"family": family, "row_ids": _ids(rows), "count": len(rows),
        "axes": axes, "traces": [], "layout": {}, "limitations": [], "algorithm": {}}
    implementations = {"history": _history, "scatter": _scatter, "ranked": _ranked,
        "distribution": _distribution, "heatmap": _heatmap, "correlation": _correlation}
    if family not in implementations:
        raise ValueError(f"Unsupported exploration chart family: {family}")
    if not axes:
        result["limitations"].append("No numeric measures selected")
        return result
    implementations[family](rows, axes, options, result)
    return result


def _history(rows: list[Row], axes: list[str], options: dict[str, Any], result: dict[str, Any]) -> None:
    groups: dict[tuple[str, str], list[Row]] = defaultdict(list)
    for row in rows:
        for axis in axes:
            if axis in row.get("values", {}):
                groups[(str(row.get("symbol", "")), axis)].append(row)
    requested_layout = options.get("history_layout", "overlay")
    if requested_layout not in {"overlay", "small_multiples"}:
        raise ValueError("History layout must be overlay or small_multiples")
    units = options.get("units", {})
    selected_axes = list(dict.fromkeys(axis for _, axis in groups))
    distinct_units = {units.get(axis) for axis in selected_axes}
    separated = len(selected_axes) > 1 and (len(distinct_units) > 1 or None in distinct_units)
    panels: dict[str, int] = {}
    for (symbol, axis), sample in groups.items():
        sample.sort(key=lambda row: str(row.get("date", "")))
        panel = f"{symbol} · {axis}" if requested_layout == "small_multiples" else (axis if separated else "All")
        panels.setdefault(panel, len(panels) + 1)
        index = panels[panel]
        suffix = "" if index == 1 else str(index)
        result["traces"].append({"type": "scatter", "mode": "lines+markers", "name": f"{symbol} · {_axis_title(axis, options)}",
            "x": [str(row.get("date", "")) for row in sample], "y": [_value(row, axis) for row in sample],
            "xaxis": f"x{suffix}", "yaxis": f"y{suffix}", "connectgaps": False, "customdata": _trace_rows(sample)})
        result["layout"][f"xaxis{suffix}"] = {"type": "date", **({"matches": "x"} if index > 1 else {})}
        result["layout"][f"yaxis{suffix}"] = {"title": _axis_title(axis, options) if separated or requested_layout == "small_multiples" else (units.get(axis) or "Original value (unit unknown)")}
    if len(panels) > 1:
        result["layout"]["grid"] = {"rows": len(panels), "columns": 1, "pattern": "independent"}
    if separated and requested_layout == "overlay":
        result["limitations"].append("Incompatible or unknown history units use independent aligned scales")
    result["algorithm"] = {"name": "retained-observations", "missing": "gaps", "weights": "none",
        "history_layout": "small_multiples" if len(panels) > 1 else requested_layout,
        "scale_policy": "independent-aligned" if len(panels) > 1 else "shared-original-units"}


def _scatter(rows: list[Row], axes: list[str], options: dict[str, Any], result: dict[str, Any]) -> None:
    if len(axes) < 2:
        result["limitations"].append("Scatter requires two measures")
        return
    x, y = str(options.get("x", axes[0])), str(options.get("y", axes[1]))
    accepted = [row for row in rows if _value(row, x) is not None and _value(row, y) is not None]
    result["paired_row_ids"] = _ids(accepted)
    _scatter_traces(accepted, x, y, options, result)
    if not accepted:
        result["layout"] = {"xaxis": {"title": _axis_title(x, options)}, "yaxis": {"title": _axis_title(y, options)}}
    if len(accepted) < len(rows):
        result["limitations"].append(f"{len(rows) - len(accepted)} rows lack a finite axis pair")
    if not options.get("descriptive_fit", options.get("fit", False)):
        return
    separate = "fit_rows" in options
    candidates = list(options["fit_rows"]) if separate else rows
    if len(set(_ids(candidates))) != len(candidates):
        raise ValueError("Fit row IDs must be unique")
    fitted = [row for row in candidates if _value(row, x) is not None and _value(row, y) is not None]
    fit: dict[str, Any] = {"algorithm": "ordinary-least-squares-with-intercept", "weights": "equal_row",
        "sample": "separate" if separate else "displayed", "row_ids": _ids(fitted), "count": len(fitted),
        "evaluation_row_ids": _ids(accepted), "slope": None, "intercept": None, "r_squared": None,
        "residuals": [], "units": {"x": options.get("units", {}).get(x), "y": options.get("units", {}).get(y)}}
    result["fit"] = fit
    if options.get("shape") == "panel" and not options.get("allow_pooled_fit", False):
        fit["unavailable_reason"] = "Panel fit requires explicit pooling"
    elif len(fitted) < 2:
        fit["unavailable_reason"] = "Fit requires at least two finite pairs"
    else:
        xs, ys = [_finite_value(row, x) for row in fitted], [_finite_value(row, y) for row in fitted]
        xm, ym = fsum(xs) / len(xs), fsum(ys) / len(ys)
        sxx = fsum((v - xm) ** 2 for v in xs)
        if sxx == 0:
            fit["unavailable_reason"] = "Explanatory measure is constant"
        else:
            slope = fsum((a - xm) * (b - ym) for a, b in zip(xs, ys)) / sxx
            intercept = ym - slope * xm
            total = fsum((v - ym) ** 2 for v in ys)
            error = fsum((b - intercept - slope * a) ** 2 for a, b in zip(xs, ys))
            fit_low, fit_high = min(xs), max(xs)
            fit.update(slope=slope, intercept=intercept, r_squared=None if total == 0 else max(0.0, 1 - error / total),
                equation=f"{y} = {intercept:.12g} + {slope:.12g} × {x}", x_range=[fit_low, fit_high])
            for row in accepted:
                xv, yv = _finite_value(row, x), _finite_value(row, y)
                predicted = intercept + slope * xv
                fit["residuals"].append({"row_id": str(row["id"]), "predicted": predicted,
                    "residual": yv - predicted, "extrapolation": xv < fit_low or xv > fit_high})
            evaluation_x = [_finite_value(row, x) for row in accepted]
            line_x = [min(xs + evaluation_x), max(xs + evaluation_x)]
            for index in range(max(1, len(result["facets"]))):
                suffix = "" if index == 0 else str(index + 1)
                result["traces"].append({"type": "scatter", "mode": "lines", "name": "Descriptive OLS fit",
                    "x": line_x, "y": [intercept + slope * value for value in line_x],
                    "xaxis": f"x{suffix}", "yaxis": f"y{suffix}", "showlegend": index == 0})
            if total == 0:
                result["limitations"].append("Constant dependent measure: R² unavailable")
    if "unavailable_reason" in fit:
        result["limitations"].append(fit["unavailable_reason"])
    result["algorithm"].update(name="descriptive-OLS", inference="none", facet_fit_policy="same-explicit-fit-sample")


def _ranked(rows: list[Row], axes: list[str], options: dict[str, Any], result: dict[str, Any]) -> None:
    axis = str(options.get("value", axes[0]))
    accepted = [row for row in rows if _value(row, axis) is not None]
    values = [_finite_value(row, axis) for row in accepted]
    ranks = _ranks([-value for value in values])
    ordered = sorted(zip(accepted, values, ranks), key=lambda entry: (-entry[1], str(entry[0]["id"])))
    result["ranks"] = [{"row_id": str(row["id"]), "symbol": str(row.get("symbol", "")),
        "date": str(row.get("date", "")), "value": value, "rank": rank} for row, value, rank in ordered]
    result["traces"] = [{"type": "bar", "name": f"Ranked {_axis_title(axis, options)}",
        "x": [str(row.get("symbol", "")) for row, _, _ in ordered], "y": [value for _, value, _ in ordered],
        "customdata": _trace_rows([row for row, _, _ in ordered])}]
    if len(axes) > 1:
        units = options.get("units", {})
        if units.get(axis) is not None and units.get(axis) == units.get(axes[1]):
            result["traces"].append({"type": "scatter", "mode": "markers", "name": _axis_title(axes[1], options),
                "x": [str(row.get("symbol", "")) for row, _, _ in ordered],
                "y": [_value(row, axes[1]) for row, _, _ in ordered],
                "customdata": _trace_rows([row for row, _, _ in ordered])})
        else:
            result["limitations"].append(f"{axes[1]} markers omitted: incompatible or unknown units for the ranking scale")
    result["algorithm"] = {"name": "descending-average-tied-rank", "missing": "excluded"}
    result["layout"]["yaxis"] = {"title": _axis_title(axis, options)}
    paired: list[dict[str, Any]] = []
    for row, value, rank in ordered:
        endpoint = row.get("endpoints", {}).get(axis, {})
        if "start_value" not in endpoint and "end_value" not in endpoint:
            continue
        binding = row.get("bindings", {}).get(axis)
        unit = options.get("endpoint_units", {}).get(axis, options.get("measure_metadata", {}).get(binding, {}).get("unit", options.get("units", {}).get(axis)))
        record = {"row_id": str(row["id"]), "symbol": str(row.get("symbol", "")), "ranked_value": value, "rank": rank,
            "start_value": _number(endpoint.get("start_value")), "end_value": _number(endpoint.get("end_value")),
            "start_date": endpoint.get("start_date"), "end_date": endpoint.get("end_date"), "unit": unit}
        paired.append(record)
    if paired:
        result["paired_endpoints"] = paired
        interval_label = {"change": "Interval change", "return": "Interval percentage change"}.get(str(options.get("interval_measure", "")), "Ranked interval result")
        result["traces"][0]["name"] = f"{interval_label} · {_axis_title(axis, options)}"
        result["layout"]["yaxis"]["title"] = f"{interval_label} · {_axis_title(axis, options)}"
        complete = [record for record in paired if record["start_value"] is not None and record["end_value"] is not None]
        endpoint_units = list(dict.fromkeys(record["unit"] for record in complete))
        if len(endpoint_units) > 1:
            result["limitations"].append("Paired endpoint units differ; records retained, common-scale markers unavailable")
        elif complete:
            for role in ("start", "end"):
                result["traces"].append({"type": "scatter", "mode": "markers", "name": f"Interval {role} ({endpoint_units[0] or 'unit unknown'})",
                    "x": [record["symbol"] for record in complete], "y": [record[f"{role}_value"] for record in complete],
                    "xaxis": "x2", "yaxis": "y2", "marker": {"symbol": "circle-open" if role == "start" else "circle", "size": 10},
                    "customdata": [[record["row_id"], record["symbol"], record[f"{role}_date"], role] for record in complete],
                    "hovertemplate": "%{customdata[1]}<br>%{customdata[3]}: %{y}<br>%{customdata[2]}<extra></extra>"})
            result["traces"].append({"type": "scatter", "mode": "lines", "name": "Retained interval endpoints", "showlegend": False,
                "x": [value for record in complete for value in (record["symbol"], record["symbol"], None)],
                "y": [value for record in complete for value in (record["start_value"], record["end_value"], None)],
                "xaxis": "x2", "yaxis": "y2", "connectgaps": False,
                "customdata": [[record["row_id"], record["symbol"]] for record in complete for _ in range(3)]})
            result["layout"].update(grid={"rows": 2, "columns": 1, "pattern": "independent"},
                xaxis2={"matches": "x"}, yaxis2={"title": f"Retained start / end levels ({endpoint_units[0] or 'unit unknown'})"})
        if len(complete) < len(paired):
            result["limitations"].append(f"{len(paired) - len(complete)} paired endpoint records unavailable")
        result["algorithm"]["paired_endpoint_policy"] = "retained-original-levels-and-dates-separate-from-ranking"


def _distribution(rows: list[Row], axes: list[str], options: dict[str, Any], result: dict[str, Any]) -> None:
    form = options.get("distribution", options.get("form", "kde"))
    if form not in {"kde", "histogram", "box"}:
        raise ValueError("Distribution must be kde, histogram or box")
    policy = options.get("weight_policy", "equal_row")
    if policy not in {"equal_row", "equal_member"}:
        raise ValueError("weight_policy must be equal_row or equal_member")
    group_by = options.get("group_by")
    samples: dict[tuple[str, str], list[Row]] = defaultdict(list)
    for row in rows:
        for axis in axes:
            if _value(row, axis) is not None:
                group = str(row.get(group_by, row.get("attributes", {}).get(group_by, "Unknown"))) if group_by else "All"
                samples[(axis, group)].append(row)
    result["groups"] = []
    result["algorithm"] = {"name": form, "weights": policy, "normalization": "probability-density" if form != "box" else "none"}
    shared = options.get("shared_bandwidth", False)
    if shared and form == "kde":
        selected_axes = {axis for axis, _ in samples}
        units = options.get("units", {})
        if len(selected_axes) > 1 and (None in {units.get(axis) for axis in selected_axes}
                or len({units.get(axis) for axis in selected_axes}) > 1):
            raise ValueError("Shared KDE bandwidth requires comparable known units")
        pooled_rows = [row for sample in samples.values() for row in sample]
        pooled_values = [_finite_value(row, axis) for (axis, _), sample in samples.items() for row in sample]
        if len(pooled_values) >= 3 and min(pooled_values) != max(pooled_values):
            bandwidth_rule = "explicit" if options.get("bandwidth") is not None else "Scott-pooled-sample"
            bandwidth = _number(options["bandwidth"]) if options.get("bandwidth") is not None else _scott_bandwidth(pooled_values, _weights(pooled_rows, policy))
            if bandwidth is None or bandwidth <= 0:
                raise ValueError("KDE bandwidth must be finite and positive")
            options = {**options, "bandwidth": bandwidth}
            multiplier = _number(options.get("bandwidth_multiplier", 1))
            if multiplier is None or multiplier <= 0:
                raise ValueError("KDE bandwidth_multiplier must be finite and positive")
            result["algorithm"].update(bandwidth_policy="shared", bandwidth=bandwidth * multiplier,
                base_bandwidth=bandwidth, bandwidth_multiplier=multiplier,
                bandwidth_row_ids=_ids(pooled_rows), bandwidth_rule=bandwidth_rule)
    for (axis, group), sample in samples.items():
        values = [_finite_value(row, axis) for row in sample]
        weights = _weights(sample, policy)
        data: dict[str, Any] = {"axis": axis, "group": group, "row_ids": _ids(sample), "count": len(sample),
            "values": values, "weights": weights, "weight_policy": policy}
        result["groups"].append(data)
        name = _axis_title(axis, options) if group == "All" else f"{_axis_title(axis, options)} · {group}"
        if form == "kde":
            _kde(values, weights, options, data)
            if data.get("unavailable_reason"):
                result["limitations"].append(f"{name}: {data['unavailable_reason']}")
                result["traces"].append({"type": "scatter", "mode": "markers", "name": name,
                    "x": values, "y": [0] * len(values), "customdata": _trace_rows(sample)})
            else:
                result["traces"].append({"type": "scatter", "mode": "lines", "name": name,
                    "x": data["x"], "y": data["density"]})
                if options.get("show_points", True):
                    result["traces"].append({"type": "scatter", "mode": "markers", "name": f"{name} observations",
                        "x": values, "y": [0] * len(values), "customdata": _trace_rows(sample)})
        elif form == "histogram":
            _histogram(values, weights, sample, options, data)
            result["traces"].append({"type": "bar", "name": name, "x": data["centers"],
                "y": data["density"], "width": data["widths"],
                "customdata": [[ids, count] for ids, count in zip(data["bin_row_ids"], data["counts"])]})
        else:
            quartile = (lambda p: _quantile(values, p)) if policy == "equal_row" else (lambda p: _weighted_quantile(values, weights, p))
            q1, median, q3 = [quartile(p) for p in (.25, .5, .75)]
            lower, upper = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
            inside = [value for value in values if lower <= value <= upper]
            outliers = [(row, value) for row, value in zip(sample, values) if value < lower or value > upper]
            data.update(q1=q1, median=median, q3=q3, lower_fence=lower, upper_fence=upper,
                lower_whisker=min(inside), upper_whisker=max(inside),
                quartile_rule="Hyndman-Fan-7" if policy == "equal_row" else "weighted-inverse-CDF",
                whisker_rule="Tukey-1.5-IQR-observed", outliers=[{"row_id": str(row["id"]), "value": value} for row, value in outliers])
            result["traces"].append({"type": "box", "name": name, "q1": [q1], "median": [median], "q3": [q3],
                "lowerfence": [min(inside)], "upperfence": [max(inside)], "boxpoints": False,
                "customdata": [[data["row_ids"], data["count"]]]})
            if outliers:
                result["traces"].append({"type": "scatter", "mode": "markers", "name": f"{name} outliers",
                    "x": [name] * len(outliers), "y": [value for _, value in outliers],
                    "customdata": _trace_rows([row for row, _ in outliers])})
        selected_value = _number(options.get("selected_value"))
        selected_id = options.get("selected_row_id")
        selected_row = next((row for row in sample if str(row["id"]) == str(selected_id)), None) if selected_id is not None else None
        selected_policy = "explicit"
        if "selected_value" not in options and "selected_row_id" not in options:
            def actual_date(row: Row) -> str:
                return str(row.get("dates", {}).get(axis) or row.get("date", ""))
            candidates = [row for row in sample if not options.get("as_of") or actual_date(row) <= str(options["as_of"])]
            selected_row = max(candidates, key=lambda row: (actual_date(row), str(row["id"]))) if candidates else None
            selected_policy = "latest-retained-finite-row"
        if selected_row is not None:
            selected_value = _value(selected_row, axis)
        if selected_value is not None:
            data["selected_value"] = selected_value
            data["selected_value_policy"] = selected_policy
            if selected_row is not None:
                data["selected_row_id"] = str(selected_row["id"])
                data["selected_date"] = str(selected_row.get("dates", {}).get(axis) or selected_row.get("date", ""))
            marker_label = "latest retained value" if selected_policy == "latest-retained-finite-row" else "selected value"
            marker: dict[str, Any] = {"type": "scatter", "mode": "markers", "name": f"{name} {marker_label}",
                "x": [name] if form == "box" else [selected_value], "y": [selected_value] if form == "box" else [0],
                "marker": {"symbol": "diamond", "size": 12}}
            if selected_row is not None:
                marker["customdata"] = [[str(selected_row["id"]), str(selected_row.get("symbol", "")), data["selected_date"]]]
                marker["hovertemplate"] = "%{customdata[1]}<br>%{customdata[2]}<br>Value: " + ("%{y}" if form == "box" else "%{x}") + "<extra></extra>"
            result["traces"].append(marker)
    if not samples:
        result["limitations"].append("No finite observations for distribution")


def _scott_bandwidth(values: list[float], weights: list[float]) -> float:
    effective_count = 1 / fsum(w * w for w in weights)
    mean = fsum(value * weight for value, weight in zip(values, weights))
    variance = fsum(weight * (value - mean) ** 2 for value, weight in zip(values, weights)) / (1 - fsum(w * w for w in weights))
    return sqrt(variance) * effective_count ** (-.2)


def _kde(values: list[float], weights: list[float], options: dict[str, Any], data: dict[str, Any]) -> None:
    data.update(kernel="Gaussian", bandwidth_rule="Scott-weighted-sample-SD", effective_count=1 / fsum(w * w for w in weights))
    multiplier = _number(options.get("bandwidth_multiplier", 1))
    if multiplier is None or multiplier <= 0:
        raise ValueError("KDE bandwidth_multiplier must be finite and positive")
    data["bandwidth_multiplier"] = multiplier
    if len(values) < 3 or min(values) == max(values):
        data["unavailable_reason"] = "KDE requires at least three nonconstant observations; retained as points"
        return
    bandwidth = options.get("bandwidth")
    if bandwidth is None:
        bandwidth = _scott_bandwidth(values, weights)
    else:
        bandwidth = _number(bandwidth)
        data["bandwidth_rule"] = "explicit"
    if bandwidth is None or bandwidth <= 0:
        raise ValueError("KDE bandwidth must be finite and positive")
    data["base_bandwidth"] = bandwidth
    bandwidth *= multiplier
    if not isfinite(bandwidth) or bandwidth <= 0:
        raise ValueError("Resolved KDE bandwidth must be finite and positive")
    points = int(options.get("grid_points", 128))
    if not 2 <= points <= 4096:
        raise ValueError("KDE grid_points must be between 2 and 4096")
    low, high = min(values) - 3 * bandwidth, max(values) + 3 * bandwidth
    grid = [low + (high - low) * i / (points - 1) for i in range(points)]
    data.update(bandwidth=bandwidth, x=grid, density=[fsum(weight * exp(-.5 * ((point - value) / bandwidth) ** 2)
        for value, weight in zip(values, weights)) / (bandwidth * sqrt(2 * pi)) for point in grid])


def _histogram(values: list[float], weights: list[float], sample: list[Row], options: dict[str, Any], data: dict[str, Any]) -> None:
    bins = options.get("bins", max(1, ceil(sqrt(len(values)))))
    if isinstance(bins, int) and not isinstance(bins, bool):
        if not 1 <= bins <= 4096:
            raise ValueError("Histogram bins must be between 1 and 4096")
        low, high = min(values), max(values)
        if low == high:
            low, high = low - .5, high + .5
        edges = [low + (high - low) * i / bins for i in range(bins + 1)]
    elif isinstance(bins, (list, tuple)):
        supplied_edges = [_number(edge) for edge in bins]
        if len(supplied_edges) < 2 or any(edge is None for edge in supplied_edges):
            raise ValueError("Histogram edges must be finite and strictly increasing")
        edges = [_finite_number(edge) for edge in supplied_edges]
        if any(a >= b for a, b in zip(edges, edges[1:])):
            raise ValueError("Histogram edges must be finite and strictly increasing")
        if min(values) < edges[0] or max(values) > edges[-1]:
            raise ValueError("Histogram edges must cover all retained values")
    else:
        raise ValueError("Histogram bins must be a count or explicit edges")
    counts, masses = [0] * (len(edges) - 1), [0.0] * (len(edges) - 1)
    members: list[list[str]] = [[] for _ in counts]
    for row, value, weight in zip(sample, values, weights):
        index = min(bisect_right(edges, value) - 1, len(counts) - 1)
        counts[index] += 1
        masses[index] += weight
        members[index].append(str(row["id"]))
    widths = [b - a for a, b in zip(edges, edges[1:])]
    data.update(edges=edges, counts=counts, masses=masses, widths=widths,
        centers=[(a + b) / 2 for a, b in zip(edges, edges[1:])], density=[mass / width for mass, width in zip(masses, widths)],
        bin_row_ids=members, edge_rule="left-closed; final-bin-right-closed", normalization="probability-density")


def _aggregate(values: list[float], method: str) -> float | None:
    if not values:
        return None
    if method == "mean":
        return fsum(values) / len(values)
    if method == "median":
        return _quantile(values, .5)
    if method == "sum":
        return fsum(values)
    if method == "last":
        return values[-1]
    raise ValueError("Aggregation must be mean, median, sum or last")


def _heatmap(rows: list[Row], axes: list[str], options: dict[str, Any], result: dict[str, Any]) -> None:
    orientation = options.get("heatmap_layout", options.get("orientation", "time"))
    orientation = {"symbols_dates": "time", "symbols_fields": "fields"}.get(orientation, orientation)
    if orientation not in {"time", "fields"}:
        raise ValueError("Heatmap layout must be time or fields")
    method = options.get("aggregation", "mean")
    if method not in {"mean", "median", "sum", "last"}:
        raise ValueError("Aggregation must be mean, median, sum or last")
    symbols = list(dict.fromkeys(str(row.get("symbol", "")) for row in rows))
    columns = sorted({str(row.get("date", "")) for row in rows}) if orientation == "time" else axes
    grouped: dict[tuple[str, str], list[Row]] = defaultdict(list)
    for row in rows:
        symbol = str(row.get("symbol", ""))
        for axis in axes[:1] if orientation == "time" else axes:
            if _value(row, axis) is not None:
                column = str(row.get("date", "")) if orientation == "time" else axis
                grouped[(symbol, column)].append(row)
    cells = []
    matrix = []
    for symbol in symbols:
        matrix_row = []
        for column in columns:
            axis = axes[0] if orientation == "time" else column
            sample = sorted(grouped.get((symbol, column), []), key=lambda row: str(row.get("date", "")))
            value = _aggregate([_finite_value(row, axis) for row in sample], method)
            cells.append({"symbol": symbol, "column": column, "value": value, "row_ids": _ids(sample), "count": len(sample)})
            matrix_row.append(value)
        matrix.append(matrix_row)
    result.update(symbols=symbols, columns=columns, z=matrix, cells=cells)
    units = options.get("units", {})
    distinct_units = {units.get(axis) for axis in axes}
    separate_scales = orientation == "fields" and len(columns) > 1 and (len(distinct_units) > 1 or None in distinct_units)
    result["algorithm"] = {"name": "retained-cell-aggregation", "aggregation": method,
        "scale_policy": "separate-columns" if separate_scales else "shared", "orientation": orientation}
    if separate_scales:
        for index, column in enumerate(columns):
            result["traces"].append({"type": "heatmap", "name": column, "x": [column], "y": symbols,
                "z": [[row[index]] for row in matrix], "showscale": False,
                "customdata": [[[cell["row_ids"], cell["count"], units.get(column)]] for cell in cells if cell["column"] == column]})
        result["limitations"].append("Field columns use independent colour scales; compare raw values in their own units")
    else:
        result["traces"] = [{"type": "heatmap", "x": columns, "y": symbols, "z": matrix,
            "customdata": [[[cell["row_ids"], cell["count"]] for cell in cells[index * len(columns):(index + 1) * len(columns)]]
                for index in range(len(symbols))]}]


def _correlation(rows: list[Row], axes: list[str], options: dict[str, Any], result: dict[str, Any]) -> None:
    orientation = options.get("correlation_orientation", options.get("orientation", "fields"))
    orientation = {"fields_across_symbols": "fields", "series_across_dates": "series"}.get(orientation, orientation)
    method = options.get("correlation_method", options.get("method", "pearson"))
    policy = options.get("correlation_sample", options.get("sample_policy", "common"))
    if orientation not in {"fields", "series"} or method not in {"pearson", "spearman"} or policy not in {"common", "pairwise"}:
        raise ValueError("Invalid correlation orientation, method or sample policy")
    observations: list[tuple[str, dict[str, float | None], dict[str, list[str]]]] = []
    if orientation == "fields":
        columns = axes
        for row in rows:
            observations.append((str(row["id"]), {axis: _value(row, axis) for axis in columns}, {axis: [str(row["id"])] for axis in columns}))
    else:
        axis = str(options.get("value", axes[0]))
        columns = list(dict.fromkeys(str(row.get("symbol", "")) for row in rows))
        by_date: dict[str, dict[str, Row]] = defaultdict(dict)
        for row in rows:
            symbol, date = str(row.get("symbol", "")), str(row.get("date", ""))
            if symbol in by_date[date]:
                raise ValueError("Series correlation requires one retained row per symbol/date")
            by_date[date][symbol] = row
        for date, members in sorted(by_date.items()):
            observations.append((date, {symbol: _value(members[symbol], axis) if symbol in members else None for symbol in columns},
                {symbol: [str(members[symbol]["id"])] if symbol in members else [] for symbol in columns}))
    common = [observation for observation in observations if all(observation[1].get(column) is not None for column in columns)]
    cells, matrix, counts = [], [], []
    for left in columns:
        matrix_row, count_row = [], []
        for right in columns:
            sample = common if policy == "common" else [observation for observation in observations
                if observation[1].get(left) is not None and observation[1].get(right) is not None]
            xs, ys = [_finite_number(observation[1][left]) for observation in sample], [_finite_number(observation[1][right]) for observation in sample]
            value = _pearson(_ranks(xs), _ranks(ys)) if method == "spearman" else _pearson(xs, ys)
            paired_rows: list[dict[str, Any]] = [{"sample_key": key, "x": values[left], "y": values[right],
                "row_ids": list(dict.fromkeys(ids[left] + ids[right]))} for key, values, ids in sample]
            cell = {"left": left, "right": right, "value": value, "count": len(sample),
                "row_ids": list(dict.fromkeys(row_id for pair in paired_rows for row_id in pair["row_ids"])),
                "sample_keys": [observation[0] for observation in sample], "pairs": paired_rows}
            if value is None:
                cell["unavailable_reason"] = "Fewer than two pairs" if len(sample) < 2 else "Constant input"
            cells.append(cell)
            matrix_row.append(value)
            count_row.append(len(sample))
        matrix.append(matrix_row)
        counts.append(count_row)
    result.update(columns=columns, z=matrix, counts=counts, cells=cells,
        common_sample_keys=[observation[0] for observation in common],
        common_row_ids=list(dict.fromkeys(row_id for _, _, ids in common for selected in ids.values() for row_id in selected)))
    result["algorithm"] = {"name": method, "orientation": orientation, "sample_policy": policy,
        "ties": "average-rank" if method == "spearman" else "not-applicable", "weights": "equal_row"}
    result["traces"] = [{"type": "heatmap", "x": columns, "y": columns, "z": matrix, "zmin": -1, "zmax": 1,
        "colorscale": "RdBu", "reversescale": True,
        "customdata": [[[cell["row_ids"], cell["count"]] for cell in cells[index * len(columns):(index + 1) * len(columns)]]
            for index in range(len(columns))]}]
    if any(cell["value"] is None for cell in cells):
        result["limitations"].append("Unavailable correlation cells have fewer than two pairs or constant inputs")
