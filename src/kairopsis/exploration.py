"""One resolved data bundle → engine outputs → retained rows → statistics.

No screening/monitoring publication occurs here. Query reuse is keyed by the
entire binding including revision; each engine gets its own identity projection.
"""
import hashlib
import json
from datetime import date, timedelta
from typing import Any, Literal, cast

from .analytics import evaluate
from .exploration_models import CollectionItem, SampleRow, ViewDefinition, ViewResult, WorkspaceDefinition
from .fixtures import MOCK_AS_OF
from .models import DataFailure, DataRequest, DataResponse, SeriesBinding, SeriesResult, identity
from .periods import period_start
from .references import analysis_start
from .service import Research
from .exploration_cache import ExplorationCache, WorkspaceCache


def fingerprint(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def workspace_fingerprint(workspace: WorkspaceDefinition) -> str:
    # Persistence version/layout are bookkeeping; all authored research context is
    # captured and must match. Saving after preview does not invalidate evidence.
    return fingerprint(workspace.model_dump(mode="json", exclude={"version", "layout"}))


def bindings(item: CollectionItem) -> tuple[SeriesBinding, ...]:
    if item.binding:
        return (item.binding,)
    assert item.analysis is not None
    return (*item.analysis.inputs, *item.analysis.references)


def meaning(item: CollectionItem) -> str:
    if item.analysis:
        measure = item.analysis.settings.measure
        calculation = item.analysis.calculation
        source = item.semantics if item.semantics != "unknown" else "; ".join(b.description or "Input semantics unspecified" for b in item.analysis.inputs)
        if measure == "return":
            return f"{calculation}: percentage change of supplied input values (positive baseline required). {source}"
        if measure == "change":
            return f"{calculation}: absolute input changes. {source}"
        return f"{calculation}: supplied input levels. {source}"
    assert item.binding is not None
    return item.semantics if item.semantics != "unknown" else item.binding.description or "Supplied numeric level; economic/return semantics unspecified"


class Exploration:
    def __init__(self, research: Research):
        self.research = research
        self.cache = ExplorationCache()

    def preview(self, workspace: WorkspaceDefinition, refresh_data: bool = False) -> dict:
        with self.cache.session(workspace.id, refresh_data) as cache:
            return self._preview(workspace, cache)

    def _preview(self, workspace: WorkspaceDefinition, cache: WorkspaceCache) -> dict:
        from .exploration_statistics import summarize

        research = self.research
        now = research.clock()
        default_end = workspace.as_of or (MOCK_AS_OF if research.repository.mode == "mock" else now.astimezone(research.timezone).date())
        ends = [v.as_of or default_end for v in workspace.views] or [default_end]
        # Retrieval extent never depends on display zoom. All sample histories,
        # baseline and engine estimation windows are resolved together.
        start = period_start(min(ends), 5)
        for view, end in zip(workspace.views, ends):
            for explicit in (view.sample.start, view.sample.interval_start):
                if explicit:
                    start = min(start, explicit - timedelta(days=view.sample.maximum_age_days))
            for item in workspace.collection:
                if item.analysis:
                    d = item.analysis
                    start = min(start, analysis_start(end, d.settings, len(d.inputs), (5,), calculation=d.calculation))
                    if view.sample.start:
                        start = min(start, analysis_start(view.sample.start, d.settings, len(d.inputs), (), calculation=d.calculation))
        bundle: dict[str, DataResponse] = {}
        requests: dict[str, DataRequest] = {}
        for item in workspace.collection:
            for binding in bindings(item):
                key = fingerprint(binding)
                if key in bundle:
                    continue
                request = DataRequest(bindings=(binding,), start=start, end=max(ends),
                    freshness="require_fresh" if cache.refreshed else "prefer_cache")
                try:
                    def fetch(query):
                        data = research.preview_provider.fetch(query)
                        if data.mode != research.repository.mode:
                            raise ValueError("Provider mode does not match workspace")
                        if any(s.binding != binding for s in data.series):
                            raise ValueError("Provider returned a different resolved binding")
                        if len(data.series) > 1:
                            raise ValueError("Provider returned multiple series for one binding")
                        for series in data.series:
                            dates = [o.date for o in series.observations]
                            if len(set(dates)) != len(dates):
                                raise ValueError("Duplicate daily observations")
                        return data
                    data = cache.load(key, request, fetch)
                    bundle[key] = data
                    requests[key] = request
                except Exception as error:
                    if cache.refreshed:
                        raise ValueError("Could not refresh all series. Previous data kept; retry Refresh data.") from error
                    from .models import DataFailure
                    bundle[key] = DataResponse(mode=cast(Literal["mock", "live"], research.repository.mode), requested=(binding.id,), series=(), attempted_at=now,
                        completed_at=now, outcome="failed", failures=(DataFailure(binding_id=binding.id, code="retrieval_failed",
                        message=str(error) if isinstance(error, ValueError) else f"Retrieval failed ({type(error).__name__})"),))
                    requests[key] = request
                    cache.versions[key] = identity()
        if not workspace.views and any(data.failures for data in bundle.values()):
            raise ValueError("Could not load all selected series. Check their source details, then retry Refresh data.")
        results = []
        for view, end in zip(workspace.views, ends):
            axis_items = [i for i in workspace.collection if i.id in view.measures]
            included_symbols = {i.symbol for i in axis_items}
            size_item = next((i for i in workspace.collection if i.id == view.size_by), None)
            color_item = next((i for i in workspace.collection if i.id == view.color_by), None)
            encoding_fields = {field for field in (size_item.field if size_item else None, color_item.field if color_item else view.color_by)
                if field and any(i.field == field for i in workspace.collection)}
            # Encodings are dependencies, independently of axis selections. A
            # Size by item chooses its semantic field for every included symbol;
            # paired-date marks retain explicitly identified item values.
            selected = [i for i in workspace.collection if i.id in view.measures or i.id in (view.size_by, view.color_by) or
                i.symbol in included_symbols and i.field in encoding_fields]
            view_key = fingerprint([view.model_dump(mode="json", exclude={"id", "name", "width", "highlight", "display_start", "display_end", "pinned"}),
                [i.model_dump(mode="json") for i in selected], [a.model_dump(mode="json") for a in workspace.attributes],
                str(start), str(end), [cache.versions[fingerprint(b)] for i in selected for b in bindings(i)]])
            cached = cache.views.get(view_key)
            if cached is not None:
                display_ids = tuple(r.id for r in cached.rows if (not view.display_start or r.date >= view.display_start) and (not view.display_end or r.date <= view.display_end))
                results.append(cached.model_copy(update={"id": identity(), "view_id": view.id, "view": view,
                    "definition_fingerprint": fingerprint(view), "workspace_fingerprint": workspace_fingerprint(workspace),
                    "created_at": now, "expires_at": now + timedelta(hours=24), "display_row_ids": display_ids}))
                continue
            values: dict[str, dict[date, dict[str, Any]]] = {}
            metadata: dict[str, dict[str, Any]] = {}
            evidence: dict[str, Any] = {"bindings": {}, "evaluations": {}}
            limits: list[str] = []
            for item in selected:
                series_data: list[SeriesResult] = []
                failures: list[DataFailure] = []
                outcomes = []
                for binding in bindings(item):
                    key = fingerprint(binding)
                    data = bundle[key]
                    filtered = data.model_copy(update={"series": tuple(s.model_copy(update={"observations": tuple(o for o in s.observations if start <= o.date <= end)}) for s in data.series)})
                    evidence["bindings"][key] = {"request": requests[key].model_copy(update={"end": end}).model_dump(mode="json"), "data": filtered.model_dump(mode="json"),
                        "retrievals": cache.retrievals(key)}
                    # Raw source evidence remains untouched above. A known
                    # native observation after the cutoff cannot be consumed by
                    # a historical calculation, even if its row is dated earlier.
                    series_data.extend(s.model_copy(update={"observations": tuple(
                        o.model_copy(update={"value": None, "value_issue": "Native observation after as-of cutoff"})
                        if o.observed_on and o.observed_on > end else o for o in s.observations)}) for s in filtered.series)
                    failures.extend(filtered.failures)
                    outcomes.append(filtered.outcome)
                output: dict[date, dict[str, Any]] = {}
                unit = item.binding.unit if item.binding else "unavailable"
                if item.binding:
                    for series in series_data:
                        for o in series.observations:
                            output[o.date] = {"value": o.value, "observed_on": o.observed_on, "endpoints": {}, "reason": o.value_issue}
                elif not failures:
                    assert item.analysis is not None
                    try:
                        request = DataRequest(bindings=bindings(item), start=start, end=end)
                        data = DataResponse(mode=cast(Literal["mock", "live"], research.repository.mode), requested=tuple(b.id for b in bindings(item)), series=tuple(series_data),
                            attempted_at=now, completed_at=now, outcome="synthetic" if research.repository.mode == "mock" else "unverified")
                        analysis_key = fingerprint([item.analysis.model_dump(mode="json"), str(start), str(end), [cache.versions[fingerprint(b)] for b in bindings(item)]])
                        evaluation = cache.analyses.get(analysis_key)
                        if evaluation is None:
                            evaluation = evaluate(item.analysis, data, request, now)
                            cache.remember(cache.analyses, analysis_key, evaluation)
                        unit = evaluation.unit
                        evidence["evaluations"][item.id] = evaluation.model_dump(mode="json")
                        limits.extend(f"{item.symbol}/{item.field}: {limitation}" for limitation in evaluation.limitations)
                        for metric in evaluation.points:
                            output[metric.date] = {"value": metric.value, "observed_on": metric.date if all(d == metric.date for d in metric.observed_on) else None,
                                "endpoints": {"inputs": list(metric.inputs), "transformed_inputs": list(metric.transformed_inputs),
                                    "risk_scales": list(metric.risk_scales), "period_start": [str(d) if d else None for d in metric.period_start],
                                    "input_observed_on": [str(d) if d else None for d in metric.observed_on]},
                                "reason": "Calculation unavailable; inspect engine evidence" if metric.value is None else None}
                    except ValueError as error:
                        limits.append(f"{item.symbol}/{item.field}: {error}")
                limits.extend(f"{item.symbol}/{item.field}: {f.message}" for f in failures)
                metadata[item.id] = {"symbol": item.symbol, "field": item.field, "unit": unit, "meaning": meaning(item),
                    "kind": item.kind, "origin": item.origin, "outcomes": outcomes, "definition": item.model_dump(mode="json")}
                values[item.id] = output
            available_axes = tuple(view.measures) if view.shape == "paired_date" else tuple(dict.fromkeys(i.field for i in selected if i.id in view.measures))
            requested_axes = view.options.get("axes")
            axes = tuple(axis for axis in requested_axes if axis in available_axes) if requested_axes else available_axes
            if not axes:
                axes = available_axes
            if view.shape == "paired_date":
                groups = {" / ".join(i.symbol for i in selected if i.id in view.measures): selected}
            else:
                groups = {symbol: [i for i in selected if i.symbol == symbol] for symbol in dict.fromkeys(i.symbol for i in axis_items)}
            accepted: list[SampleRow] = []
            excluded: list[SampleRow] = []
            for symbol, items in groups.items():
                days = [view.sample.end or end] if view.shape == "cross_section" else sorted(set().union(*(values[i.id] for i in items)))
                # Missing dependencies still materialize a candidate at the cutoff.
                if not days:
                    days = [view.sample.end or end]
                for day in days:
                    if day > end:
                        continue
                    row_values, dates, observed, row_bindings, endpoints = {}, {}, {}, {}, {}
                    reasons = []
                    for item in items:
                        axis = item.id if view.shape == "paired_date" else item.field
                        point_day, point = choose(values[item.id], day, view)
                        value = point.get("value") if point else None
                        if point and point.get("reason"):
                            reasons.append(f"{axis}: {point['reason']}")
                        endpoint = dict(point.get("endpoints", {})) if point else {}
                        if view.sample.interval_measure != "level":
                            assert view.sample.interval_start is not None
                            baseline_day, baseline = choose(values[item.id], view.sample.interval_start, view)
                            base = baseline.get("value") if baseline else None
                            endpoint.update({"start_requested": str(view.sample.interval_start), "start_date": str(baseline_day) if baseline_day else None,
                                "start_value": base, "end_date": str(point_day) if point_day else None, "end_value": value})
                            if value is None or base is None:
                                value = None
                                reasons.append(f"{axis}: interval endpoint missing")
                            elif view.sample.interval_measure == "return" and base <= 0:
                                value = None
                                reasons.append(f"{axis}: Percentage change unavailable: nonpositive baseline")
                            else:
                                value = value - base if view.sample.interval_measure == "change" else 100 * (value / base - 1)
                        row_values[axis], dates[axis], observed[axis] = value, point_day, point.get("observed_on") if point else None
                        row_bindings[axis], endpoints[axis] = item.id, endpoint
                    row_id = fingerprint(["row", symbol, str(day)])
                    source_ids = tuple(dict.fromkeys(fingerprint(["row", item.symbol, str(day)]) for item in items if item.id in view.measures))
                    exclusion = []
                    if view.sample.start and day < view.sample.start or view.sample.end and day > view.sample.end:
                        exclusion.append("Outside selected sample dates")
                    member_ids = {i.symbol for i in items if i.id in view.measures} if view.shape == "paired_date" else {symbol}
                    if view.sample.members is not None and not member_ids <= set(view.sample.members):
                        exclusion.append("Symbol excluded by sample")
                    if view.sample.row_ids and row_id not in view.sample.row_ids and not all(key in view.sample.row_ids for key in source_ids):
                        exclusion.append("Outside retained drilldown sample")
                    if row_id in view.sample.excluded_row_ids or any(key in view.sample.excluded_row_ids for key in source_ids):
                        exclusion.append("Observation explicitly excluded")
                    for rule in view.sample.filters:
                        val = row_values.get(rule.field)
                        if val is None or rule.minimum is not None and val < rule.minimum or rule.maximum is not None and val > rule.maximum:
                            exclusion.append(f"Numeric filter: {rule.field}")
                    if not any(row_values.get(axis) is not None for axis in axes):
                        exclusion.append("All selected measures unavailable")
                    if view.family == "scatter" and any(row_values.get(axis) is None for axis in axes[:2]):
                        exclusion.append("Paired scatter requires both axes")
                    attrs = {a.name: a.value for a in workspace.attributes if a.symbol == symbol and (not a.effective_start or day >= a.effective_start) and (not a.effective_end or day <= a.effective_end)}
                    row = SampleRow(id=row_id, symbol=symbol, date=day, values=row_values, dates=dates, observed_on=observed,
                        bindings=row_bindings, endpoints=endpoints, attributes=attrs, reasons=tuple([*reasons, *exclusion]), source_row_ids=source_ids)
                    (excluded if exclusion else accepted).append(row)
            units: dict[str, str] = {}
            for item in selected:
                axis = item.id if view.shape == "paired_date" else item.field
                unit = "%" if view.sample.interval_measure == "return" else metadata[item.id]["unit"]
                if axis in units and units[axis] != unit:
                    limits.append(f"{axis}: mixed units cannot share one field scale")
                    raise ValueError(f"{view.name}: associate different units with distinct fields")
                units[axis] = unit
            if view.family == "distribution" and len({units[axis] for axis in axes}) > 1:
                raise ValueError(f"{view.name}: select one field or comparable units for a distribution overlay")
            options = {**view.options, "axes": list(axes), "units": units, "shape": view.shape,
                "as_of": str(end), "interval_measure": view.sample.interval_measure,
                "measure_metadata": metadata, "size_by": next((i.id if view.shape == "paired_date" else i.field for i in selected if i.id == view.size_by), None),
                "color_by": (color_item.id if view.shape == "paired_date" else color_item.field) if color_item else view.color_by, "facet_by": view.facet_by}
            if "bin_edges" in options:
                options["bins"] = options["bin_edges"]
            if view.family == "correlation" and options.get("correlation_sample", options.get("sample_policy", "common")) == "common":
                orientation = options.get("correlation_orientation", options.get("orientation", "fields"))
                if orientation in ("fields", "fields_across_symbols"):
                    common_ids = {r.id for r in accepted if all(r.values.get(axis) is not None for axis in axes)}
                else:
                    axis = options.get("value", axes[0])
                    members = {r.symbol for r in accepted}
                    by_day: dict[date, set[str]] = {}
                    for row in accepted:
                        if row.values.get(axis) is not None:
                            by_day.setdefault(row.date, set()).add(row.symbol)
                    complete_days = {day for day, present in by_day.items() if present == members}
                    common_ids = {r.id for r in accepted if r.date in complete_days}
                excluded.extend(r.model_copy(update={"reasons": (*r.reasons, "Incomplete common correlation sample")}) for r in accepted if r.id not in common_ids)
                accepted = [r for r in accepted if r.id in common_ids]
            stats = summarize(view.family, [row.model_dump(mode="json") for row in accepted], options)
            if any(d is None for row in accepted for d in row.observed_on.values()):
                limits.append("Unknown native observation dates: descriptive inspection only; engine estimation rules unchanged")
            if any(a.effective_start is None and a.effective_end is None for a in workspace.attributes):
                limits.append("Static supplied classifications applied to history; historical membership unverified")
            display_ids = tuple(r.id for r in accepted if (not view.display_start or r.date >= view.display_start) and (not view.display_end or r.date <= view.display_end))
            results.append(ViewResult(view_id=view.id, workspace_id=workspace.id, definition_fingerprint=fingerprint(view), workspace_fingerprint=workspace_fingerprint(workspace),
                data_fingerprint=fingerprint(evidence), created_at=now, expires_at=now + timedelta(hours=24), as_of=end, view=view,
                rows=tuple(accepted), excluded=tuple(excluded), measures=metadata, axes=axes, axis_units=units, statistics=stats,
                input_evidence=evidence, limitations=tuple(dict.fromkeys(limits)), display_row_ids=display_ids))
            cache.remember(cache.views, view_key, results[-1])
        return {"workspace": workspace, "resolved_results": results, "fingerprint": workspace_fingerprint(workspace)}


def choose(points: dict[date, dict[str, Any]], day: date, view: ViewDefinition) -> tuple[date | None, dict[str, Any] | None]:
    if day in points:
        return day, points[day]
    if view.sample.date_policy == "backward":
        eligible = [d for d in points if d <= day and (day - d).days <= view.sample.maximum_age_days]
        if eligible:
            selected = max(eligible)
            return selected, points[selected]
    return None, None
