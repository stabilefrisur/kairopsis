"""Native observation continuity, explicit causes and deterministic finding classes."""
from math import isclose
from typing import cast
from .analytics import condition_rules
from .periods import period_start
from .models import Evaluation, MetricPoint


def compare(current: Evaluation, baseline: Evaluation | None) -> Evaluation:
    if baseline is None:
        return current
    changes = {"baseline_id": baseline.id}
    if current.definition != baseline.definition or current.method != baseline.method or current.data.mode != baseline.data.mode:
        return current.model_copy(update={**changes, "finding": "incompatible", "reasons": (),
            "limitations": (*current.limitations, "Definition/method changed; no compatible market baseline")})
    if not current.eligible:
        return current.model_copy(update={**changes, "finding": "unavailable", "reasons": ()})
    if not baseline.eligible:
        return current.model_copy(update={**changes,
            "limitations": (*current.limitations, "No valid eligible baseline; current condition only")})
    old = {(s.binding.id, p.date): (p.value, p.observed_on) for s in baseline.data.series for p in s.observations}
    new = {(s.binding.id, p.date): (p.value, p.observed_on) for s in current.data.series for p in s.observations}
    start = max(current.request.start, baseline.request.start)
    end = min(current.request.end, baseline.request.end)
    revised = any(old.get(k) != new.get(k) for k in old.keys() | new.keys() if start <= k[1] <= end)
    if revised:
        return current.model_copy(update={**changes, "finding": "correction", "reasons": (),
            "limitations": (*current.limitations, "Historical observations corrected/backfilled; not a new market development")})
    later = current.observation_date is not None and baseline.observation_date is not None and current.observation_date > baseline.observation_date
    if not later:
        return current.model_copy(update={**changes, "finding": "unchanged" if current.conditions else "quiet", "reasons": ()})
    delta = None if current.current is None or baseline.current is None else current.current - baseline.current
    # Rolling refits do not establish novelty. Hold the saved fit fixed when
    # checking the new inputs; report both causes beside the displayed fit.
    reasons = current.conditions
    added = set(current.condition_keys) - set(baseline.condition_keys)
    crossed = bool(added - ({"move"} if baseline.change is None else set()))
    if current.standardization_estimate and baseline.standardization_estimate:
        reference = baseline.standardization_estimate
        if reference.mean is not None and reference.standard_deviation:
            def prior_frame(point: MetricPoint) -> float | None:
                values = point.transformed_inputs or point.inputs
                raw = point.unstandardized_value
                if baseline.fit and all(v is not None for v in values):
                    raw = cast(float, values[0]) - baseline.fit.intercept - baseline.fit.slope * cast(float, values[1])
                return (raw - cast(float, reference.mean)) / cast(float, reference.standard_deviation) if raw is not None else None
            fixed = prior_frame(current.points[-1])
            z_values = {point.date: prior_frame(point) for point in current.points if point.eligible}
            delta = fixed - baseline.current if fixed is not None and baseline.current is not None else None
            fixed_baseline = z_values.get(current.change_start) if current.change_start else None
            change = fixed if current.definition.settings.measure != "level" else fixed - fixed_baseline if fixed is not None and fixed_baseline is not None else None
            fixed_reasons, fixed_keys = condition_rules(current.definition, current.unit, None, change, current.eligible, fixed)
            held = "prior fit and Z-score reference held fixed" if baseline.fit else "prior Z-score reference held fixed"
            reasons = tuple(reason + f" ({held})" for reason in fixed_reasons)
            added = set(fixed_keys) - set(baseline.condition_keys)
            crossed = bool(added - ({"move"} if baseline.change is None else set()))
    elif current.fit and baseline.fit:
        p = current.points[-1]
        inputs = p.transformed_inputs or p.inputs
        if all(v is not None for v in inputs) and baseline.current is not None:
            fixed = cast(float, inputs[0]) - baseline.fit.intercept - baseline.fit.slope * cast(float, inputs[1])
            delta = fixed - baseline.current
            fixed_values = {point.date: cast(float, (point.transformed_inputs or point.inputs)[0]) - baseline.fit.intercept - baseline.fit.slope * cast(float, (point.transformed_inputs or point.inputs)[1])
                for point in current.points if point.eligible and all(v is not None for v in (point.transformed_inputs or point.inputs))}
            history = [value for day, value in fixed_values.items() if current.observation_date and
                period_start(current.observation_date, current.definition.settings.history_years) <= day < current.observation_date]
            percentile = (100 * (sum(v < fixed for v in history) + .5 * sum(v == fixed for v in history)) / len(history)) if len(history) >= current.definition.settings.minimum_history else None
            change = fixed if current.definition.settings.measure != "level" else fixed - fixed_values[current.change_start] if current.change_start in fixed_values else None
            fixed_reasons, fixed_keys = condition_rules(current.definition, current.unit, percentile, change, current.eligible)
            reasons = tuple(reason + " (prior fit held fixed)" for reason in fixed_reasons)
            added = set(fixed_keys) - set(baseline.condition_keys)
            crossed = bool(added - ({"move"} if baseline.change is None else set()))
    material = current.definition.settings.material_change
    significant = material is not None and delta is not None and abs(delta) >= material and not isclose(delta, 0, abs_tol=1e-12)
    if crossed:
        finding = "new"
        reasons = ("Entered configured threshold on new native observations", *reasons)
    elif significant and reasons:
        finding = "changed"
        reasons = (f"Material native move {delta:+.2f} {current.unit} since {baseline.observation_date}" +
            (" holding prior fit fixed" if baseline.fit else ""), *reasons)
    else:
        finding = "unchanged" if reasons else "quiet"
        reasons = ()
    return current.model_copy(update={**changes, "finding": finding, "reasons": reasons})
