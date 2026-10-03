"""Exact-date metrics, input risk normalization and intercept OLS."""
from bisect import bisect_right
from datetime import date, datetime
from math import fsum, isfinite
from typing import cast
from .frequencies import expected_session, horizon_target, previous_session, shift_years
from .risk import transform_inputs
from .models import AdjustmentEstimate, DataRequest, DataResponse, Evaluation, Fit, MetricPoint, ResolvedDefinition


def condition_rules(definition: ResolvedDefinition, unit: str, percentile: float | None, change: float | None, eligible: bool) -> tuple[tuple[str, ...], tuple[str, ...]]:
    reasons, keys = [], []
    settings = definition.settings
    if eligible and percentile is not None and (percentile >= settings.upper_percentile or percentile <= 100 - settings.upper_percentile):
        reasons.append(f"Historical standing {percentile:.1f}th percentile / {settings.history_years}y")
        keys.append("upper" if percentile >= settings.upper_percentile else "lower")
    if eligible and change is not None and settings.move_threshold is not None and abs(change) >= settings.move_threshold:
        reasons.append(f"{change:+.2f} {unit} / {settings.horizon} meets configured {settings.move_threshold:g} {unit} rule")
        keys.append("move")
    return tuple(reasons), tuple(keys)


def regression(points: list[MetricPoint], current: date, definition: ResolvedDefinition, years: int) -> Fit | None:
    start = shift_years(current, -years)
    sample = [p for p in points if p.eligible and start <= p.date < current]
    if len(sample) < definition.settings.minimum_fit or (sample[0].date - start).days > 7 or (previous_session(current) - sample[-1].date).days > 7:
        return None
    xs = [cast(float, (p.transformed_inputs or p.inputs)[1]) for p in sample]
    ys = [cast(float, (p.transformed_inputs or p.inputs)[0]) for p in sample]
    xm, ym = fsum(xs) / len(xs), fsum(ys) / len(ys)
    xx = fsum((x - xm) ** 2 for x in xs)
    if not xx:
        return None
    slope = fsum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / xx
    intercept = ym - slope * xm
    yy = fsum((y - ym) ** 2 for y in ys)
    sse = fsum((y - intercept - slope * x) ** 2 for x, y in zip(xs, ys))
    if not all(isfinite(v) for v in (slope, intercept, sse, yy)):
        return None
    return Fit(slope=slope, intercept=intercept, r_squared=1-sse/yy if yy else None,
               sample_count=len(sample), start=sample[0].date, end=sample[-1].date, x_min=min(xs), x_max=max(xs))


def evaluate(definition: ResolvedDefinition, data: DataResponse, request: DataRequest, now: datetime) -> Evaluation:
    results = {s.binding.id: s for s in data.series}
    bindings = (*definition.inputs, *definition.references)
    if data.failures or any(b.id not in results for b in bindings):
        raise ValueError("Retrieval incomplete: " + "; ".join(f.message for f in data.failures))
    all_rows = {}
    for binding in bindings:
        result = results[binding.id]
        if result.binding != binding:
            raise ValueError("Provider returned a different resolved binding")
        dates = [p.date for p in result.observations]
        if len(dates) != len(set(dates)):
            raise ValueError("Duplicate daily observations")
        all_rows[binding.id] = {p.date: p for p in result.observations if request.start <= p.date <= request.end}
    rows = [all_rows[b.id] for b in definition.inputs]
    days = sorted(set().union(*(r.keys() for r in rows)))
    transformed: dict[date, tuple[float | None, ...]] = {}
    scales: dict[date, tuple[float | None, ...]] = {}
    starts: dict[date, tuple[date | None, ...]] = {}
    input_units = tuple(b.unit for b in definition.inputs)
    estimates: tuple[AdjustmentEstimate, ...] = ()
    if definition.settings.measure != "level":
        transformed, scales, starts, input_units, estimates = transform_inputs(definition, all_rows, days)
    method = definition.calculation
    if method == "difference" and input_units[0] != input_units[1]:
        raise ValueError("Difference requires matching units; no implicit conversion")
    unit = input_units[0]
    if method == "ratio":
        unit = "×" if unit == input_units[1] else f"{unit}/{input_units[1]}"
    points = []
    limits = []
    for day in days:
        inputs = tuple(r[day].value if day in r else None for r in rows)
        observed = tuple(r[day].observed_on if day in r else None for r in rows)
        measured = transformed.get(day, inputs)
        usable = all(v is not None for v in measured)
        eligible = usable and all(d == day for d in observed) and day.weekday() < 5
        value = None
        if usable:
            left = cast(float, measured[0])
            if method in ("level", "regression"):
                value = left
            elif method == "difference":
                value = left - cast(float, measured[1])
            elif measured[1]:
                value = left / cast(float, measured[1])
        if value is not None and not isfinite(value):
            value = None
        points.append(MetricPoint(date=day, value=value, inputs=inputs, observed_on=observed, eligible=eligible and value is not None,
            transformed_inputs=transformed.get(day, ()), risk_scales=scales.get(day, ()), period_start=starts.get(day, ())))
    fit = None
    sensitivity = []
    current_day = points[-1].date if points else None
    if method == "regression" and current_day:
        fit = regression(points, current_day, definition, definition.settings.fit_years)
        if not fit:
            limits.append("Fit unavailable: insufficient full-window history or constant explanatory input")
        else:
            limits.append("Residual history uses the current fit retrospectively; association is descriptive")
            x = (points[-1].transformed_inputs or points[-1].inputs)[1]
            if x is not None and not fit.x_min <= x <= fit.x_max:
                limits.append("Current explanatory input is outside fit range (extrapolation)")
            selected = (points[-1].transformed_inputs or points[-1].inputs)[0]
            for years in (1, 5):
                alternative = regression(points, current_day, definition, years)
                if not alternative:
                    sensitivity.append(f"{years}y comparison unavailable: insufficient fit history")
                elif selected is not None and x is not None:
                    a = selected - fit.intercept - fit.slope * x
                    b = selected - alternative.intercept - alternative.slope * x
                    if a * b < 0:
                        sensitivity.append(f"Residual direction changes under {years}y fit")
        points = [p.model_copy(update={"value": (cast(float, (p.transformed_inputs or p.inputs)[0]) - fit.intercept - fit.slope * cast(float, (p.transformed_inputs or p.inputs)[1]))
            if fit and all(v is not None for v in (p.transformed_inputs or p.inputs)) else None,
            "eligible": p.eligible and fit is not None}) for p in points]
    current = points[-1] if points else None
    for binding, estimate in zip(definition.inputs, estimates):
        if estimate.limitation:
            limits.append(f"{binding.name}: {estimate.limitation}")
    percentile = change = None
    change_start = None
    eligible = bool(current and current.eligible and current.date == expected_session(request.end))
    if not current or current.value is None:
        limits.append("Current calculation unavailable (missing input or zero denominator)")
    elif not current.eligible:
        limits.append("Missing, carried, unknown or mismatched native observations; excluded from findings")
    if current and current.date < expected_session(request.end):
        limits.append(f"Stale observations: latest row {current.date}; requested as of {request.end}")
    if data.outcome not in ("synthetic", "fresh"):
        eligible = False
        limits.append("Upstream retrieval freshness unverified; excluded from findings")
    if current and current.value is not None:
        value = current.value
        history = [p.value for p in points if p.eligible and p.value is not None and shift_years(current.date, -definition.settings.history_years) <= p.date < current.date]
        if len(history) >= definition.settings.minimum_history:
            percentile = 100 * (sum(v < value for v in history) + .5 * sum(v == value for v in history)) / len(history)
        else:
            eligible = False
            limits.append(f"Insufficient reference history: {len(history)}; require {definition.settings.minimum_history}")
        target = horizon_target(current.date, definition.settings.horizon)
        valid = [p for p in points if p.eligible and p.value is not None]
        idx = bisect_right([p.date for p in valid], target) - 1
        if definition.settings.measure != "level" and current.eligible:
            change = value
            change_start = min((d for d in current.period_start if d is not None), default=None)
        elif idx >= 0 and (target - valid[idx].date).days <= (0 if definition.settings.horizon == "day" else 3) and current.eligible:
            change = value - cast(float, valid[idx].value)
            change_start = valid[idx].date
        else:
            limits.append(f"{definition.settings.horizon.title()} change unavailable: missing eligible baseline")
    reasons, keys = condition_rules(definition, unit, percentile, change, eligible)
    return Evaluation(definition=definition, request=request, data=data, evaluated_at=now, points=tuple(points), unit=unit,
        input_units=input_units, adjustment_estimates=estimates,
        current=current.value if current else None, observation_date=current.date if current else None,
        input_dates=current.observed_on if current else (), percentile=percentile, change=change, change_start=change_start,
        eligible=eligible, limitations=tuple(limits), fit=fit, sensitivity=tuple(sensitivity), reasons=reasons, conditions=reasons, condition_keys=keys,
        finding="condition" if reasons else "quiet" if eligible else "unavailable")
