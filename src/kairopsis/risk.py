"""Rolling input normalization. Estimates never include the measured interval."""
from bisect import bisect_left, bisect_right, insort
from dataclasses import dataclass
from datetime import date
from math import ceil, floor, fsum, isfinite, sqrt
from typing import cast

from .frequencies import horizon_target
from .periods import period_start
from .models import AdjustmentEstimate, Observation, ResolvedDefinition, RiskAdjustment
from .units import Unit, transformed_unit


@dataclass(frozen=True)
class Move:
    start: date
    value: float


def adjusted_unit(target: str, reference: str, method: str, measure: str) -> str:
    if measure == "return":
        target = reference = "%"
    if method not in ("none", "beta") and target != reference:
        raise ValueError("Volatility and downside normalization require matching target/reference units; choose percentage changes or a compatible reference")
    return reference if method == "beta" else "risk units" if method != "none" else target


def measured_moves(rows: dict[date, Observation], frequency: str, measure: str) -> dict[date, Move]:
    valid = {d: p for d, p in rows.items() if d.weekday() < 5 and p.observed_on == d and p.value is not None}
    days = sorted(valid)
    moves = {}
    for day in days:
        target = horizon_target(day, frequency)
        index = bisect_right(days, target) - 1
        if index < 0 or (target - days[index]).days > (0 if frequency == "day" else 3):
            continue
        start = days[index]
        baseline, current = cast(float, valid[start].value), cast(float, valid[day].value)
        if measure == "return" and baseline <= 0:
            continue
        value = current - baseline if measure == "change" else 100 * (current / baseline - 1)
        if isfinite(value):
            moves[day] = Move(start, value)
    return moves


def estimate(values: list[float], targets: list[float], ages: list[float], options: RiskAdjustment) -> float | None:
    """Equal-weight sample SD; normalized weighted SD; intercept OLS; empirical tails."""
    if options.method == "beta":
        xm, ym = fsum(values) / len(values), fsum(targets) / len(targets)
        xx = fsum((x-xm)**2 for x in values)
        scale = fsum((x-xm)*(y-ym) for x, y in zip(values, targets)) / xx if xx else 0
    elif options.method == "volatility":
        newest = min(ages)
        weights = [2 ** (-(age-newest) / options.half_life) for age in ages] if options.weighting == "exponential" else [1.] * len(values)
        total = fsum(weights)
        mean = fsum(w*v for w, v in zip(weights, values)) / total
        correction = total - fsum(w*w for w in weights) / total
        scale = sqrt(fsum(w*(v-mean)**2 for w, v in zip(weights, values)) / correction) if correction > 0 else 0
    else:
        losses = sorted(v if options.downside == "increase" else -v for v in values)
        if options.method == "var":
            # Inverse empirical CDF, with an explicit convention for ties.
            scale = losses[ceil(options.confidence / 100 * len(losses)) - 1]
        else:
            tail = (1-options.confidence / 100) * len(losses)
            whole = floor(tail)
            ordered = list(reversed(losses))
            scale = (fsum(ordered[:whole]) + (tail-whole)*ordered[whole]) / tail
    if not isfinite(scale) or abs(scale) < 1e-12 or (options.method != "beta" and scale <= 0):
        return None
    return scale


def _session_distance(start: date, end: date) -> int:
    elapsed = (end - start).days
    return elapsed // 7 * 5 + sum((start.weekday() + i) % 7 < 5 for i in range(1, elapsed % 7 + 1))


def _expanding_scales(days: list[date], reference: dict[date, Move], target: dict[date, Move],
                      options: RiskAdjustment) -> list[float | None] | None:
    """Growing history uses online moments or ordered tails, rather than repeated fits."""
    if options.lookback_years != "all" or options.method == "none":
        return None
    result: list[float | None] = [None]
    xm = ym = xx = xy = total = squared_weights = 0.
    losses: list[float] = []
    previous = None
    for count, day in enumerate(days, 1):
        x = reference[day].value
        if options.method == "beta":
            y = target[day].value
            dx, dy = x - xm, y - ym
            xm += dx / count
            ym += dy / count
            xx += dx * (x - xm)
            xy += dx * (y - ym)
            scale = xy / xx if xx > 0 else 0.
        elif options.method == "volatility":
            decay = 2 ** (-_session_distance(previous, day) / options.half_life) if previous and options.weighting == "exponential" else 1.
            total *= decay
            squared_weights *= decay ** 2
            xx *= decay
            total += 1.
            squared_weights += 1.
            dx = x - xm
            xm += dx / total
            xx += dx * (x - xm)
            correction = total - squared_weights / total
            scale = sqrt(max(0., xx) / correction) if correction > 0 else 0.
        else:
            insort(losses, x if options.downside == "increase" else -x)
            if options.method == "var":
                scale = losses[ceil(options.confidence / 100 * count) - 1]
            else:
                tail = (1 - options.confidence / 100) * count
                whole = floor(tail)
                scale = (fsum(losses[-whole:]) if whole else 0.) + (tail - whole) * losses[-whole - 1]
                scale /= tail
        previous = day
        result.append(scale if isfinite(scale) and abs(scale) >= 1e-12 and
            (options.method == "beta" or scale > 0) else None)
    return result


def _legacy_transform_inputs(definition: ResolvedDefinition, rows: dict[str, dict[date, Observation]], days: list[date]) -> tuple[
    dict[date, tuple[float | None, ...]], dict[date, tuple[float | None, ...]],
    dict[date, tuple[date | None, ...]], tuple[str, ...], tuple[AdjustmentEstimate, ...]]:
    settings = definition.settings
    bindings = {b.id: b for b in (*definition.inputs, *definition.references)}
    moves = {key: measured_moves(value, settings.horizon, settings.measure) for key, value in rows.items()}
    common_days = set.intersection(*(set(moves[b.id]) for b in definition.inputs))
    transformed: dict[date, tuple[float | None, ...]] = {}
    scales: dict[date, tuple[float | None, ...]] = {}
    starts: dict[date, tuple[date | None, ...]] = {}
    units = []
    estimates = []
    legs = []
    for binding, options in zip(definition.inputs, settings.adjustments(len(definition.inputs))):
        reference = binding if options.method == "none" else bindings.get(options.reference_id or binding.id)
        if not reference:
            raise ValueError("Missing resolved risk reference")
        units.append(adjusted_unit(binding.unit, reference.unit, options.method, settings.measure))
        target_moves, ref_moves = moves[binding.id], moves[reference.id]
        sample_days = sorted(set(target_moves) & set(ref_moves) if options.method == "beta" else ref_moves)
        if options.method == "beta":
            sample_days = [d for d in sample_days if target_moves[d].start == ref_moves[d].start]
        if options.lookback_years == "all":
            sample_days = [d for d in sample_days if d in common_days]
        expanding = _expanding_scales(sample_days, ref_moves, target_moves, options)
        legs.append((binding, reference, options, target_moves, ref_moves, sample_days, expanding))
    for day in days:
        values, divisors, baselines, current_estimates = [], [], [], []
        for binding, reference, options, target_moves, ref_moves, sample_days, expanding in legs:
            move = target_moves.get(day)
            cutoff = move.start if move else horizon_target(day, settings.horizon)
            start = period_start(cutoff, options.lookback_years)
            selected = sample_days[bisect_left(sample_days, start):bisect_right(sample_days, cutoff)]
            scale: float | None = 1.
            limitation: str | None = None
            if options.method != "none":
                if len(selected) < options.minimum_samples:
                    scale = None
                    limitation = f"Insufficient estimation history: {len(selected)} observations; require {options.minimum_samples}"
                elif (cutoff-selected[-1]).days > 7:
                    scale = None
                    limitation = "Estimation history is stale at the measured interval's start"
                else:
                    # Half-life is in weekday sessions, independent of the move Frequency.
                    if expanding is not None:
                        scale = expanding[len(selected)]
                    elif options.method == "beta" and binding.id == reference.id:
                        scale = 1. if any(ref_moves[d].value != ref_moves[selected[0]].value for d in selected) else None
                    else:
                        ages = [float(_session_distance(d, cutoff)) for d in selected] if options.method == "volatility" and options.weighting == "exponential" else [0.] * len(selected)
                        scale = estimate([ref_moves[d].value for d in selected],
                            [target_moves[d].value for d in selected] if options.method == "beta" else [], ages, options)
                    if scale is None:
                        limitation = "Risk scale unavailable: zero/near-zero beta, constant reference or nonpositive downside estimate"
            value = move.value / scale if move and scale is not None else None
            values.append(value if value is not None and isfinite(value) else None)
            divisors.append(scale)
            baselines.append(move.start if move else None)
            current_estimates.append(AdjustmentEstimate(reference_id=reference.id, scale=scale, sample_count=len(selected),
                start=selected[0] if selected else None, end=selected[-1] if selected else None,
                limitation=limitation or ("Measured change unavailable: missing eligible baseline or nonpositive return baseline" if not move else None)))
        transformed[day], scales[day], starts[day] = tuple(values), tuple(divisors), tuple(baselines)
        estimates = current_estimates
    return transformed, scales, starts, tuple(units), tuple(estimates)


def input_unit_expressions(definition: ResolvedDefinition) -> tuple[Unit, ...]:
    settings = definition.settings
    bindings = {b.id: b for b in (*definition.inputs, *definition.references)}
    units = []
    for binding, options in zip(definition.inputs, settings.adjustments(len(definition.inputs))):
        reference = binding if options.method == "none" else bindings.get(options.reference_id or binding.id)
        if reference is None:
            raise ValueError("Missing resolved risk reference")
        numerator = "%" if settings.measure == "return" else binding.unit
        basis = settings.estimation_basis(options)
        target_unit = "%" if basis == "return" else binding.unit
        reference_unit = "%" if basis == "return" else reference.unit
        units.append(transformed_unit(numerator, target_unit, reference_unit, options.method))
    return tuple(units)


def transform_inputs(definition: ResolvedDefinition, rows: dict[str, dict[date, Observation]], days: list[date]) -> tuple[
    dict[date, tuple[float | None, ...]], dict[date, tuple[float | None, ...]],
    dict[date, tuple[date | None, ...]], tuple[str, ...], tuple[AdjustmentEstimate, ...]]:
    if definition.settings.calculation_contract == "input-pipeline-v1":
        return _legacy_transform_inputs(definition, rows, days)
    settings = definition.settings
    bindings = {b.id: b for b in (*definition.inputs, *definition.references)}
    # Numerators and estimation moves have separate eligibility and baselines.
    numerators = {b.id: measured_moves(rows[b.id], settings.horizon, settings.measure)
        for b in definition.inputs} if settings.measure != "level" else {
        b.id: {d: Move(d, cast(float, p.value)) for d, p in rows[b.id].items()
            if d.weekday() < 5 and p.observed_on == d and p.value is not None}
        for b in definition.inputs}
    common_days = set.intersection(*(set(numerators[b.id]) for b in definition.inputs))
    move_cache: dict[tuple[str, str], dict[date, Move]] = {}
    def moves(key: str, basis: str) -> dict[date, Move]:
        if (key, basis) not in move_cache:
            move_cache[key, basis] = measured_moves(rows[key], settings.horizon, basis)
        return move_cache[key, basis]
    legs = []
    for binding, options in zip(definition.inputs, settings.adjustments(len(definition.inputs))):
        reference = binding if options.method == "none" else bindings.get(options.reference_id or binding.id)
        if reference is None:
            raise ValueError("Missing resolved risk reference")
        basis = settings.estimation_basis(options)
        target_moves = moves(binding.id, basis) if options.method == "beta" else {}
        ref_moves = moves(reference.id, basis) if options.method != "none" else {}
        sample_days = sorted(set(target_moves) & set(ref_moves) if options.method == "beta" else ref_moves)
        if options.method == "beta":
            sample_days = [d for d in sample_days if target_moves[d].start == ref_moves[d].start]
        if options.lookback_years == "all":
            sample_days = [d for d in sample_days if d in common_days]
        legs.append((binding, reference, options, basis, target_moves, ref_moves, sample_days,
            _expanding_scales(sample_days, ref_moves, target_moves, options)))
    transformed, scales, starts = {}, {}, {}
    estimates = []
    for day in days:
        values, divisors, baselines, current_estimates = [], [], [], []
        for binding, reference, options, basis, target_moves, ref_moves, sample_days, expanding in legs:
            numerator = numerators[binding.id].get(day)
            cutoff = numerator.start if numerator and settings.measure != "level" else horizon_target(day, settings.horizon)
            start = period_start(cutoff, options.lookback_years)
            selected = sample_days[bisect_left(sample_days, start):bisect_right(sample_days, cutoff)]
            scale: float | None = 1.
            limitation = None
            if options.method != "none":
                if len(selected) < options.minimum_samples:
                    scale = None
                    limitation = f"Insufficient estimation history: {len(selected)} observations; require {options.minimum_samples}"
                elif (cutoff - selected[-1]).days > 7:
                    scale = None
                    limitation = "Estimation history is stale at the measured interval's start"
                else:
                    if expanding is not None:
                        scale = expanding[len(selected)]
                    else:
                        ages = [float(_session_distance(d, cutoff)) for d in selected] if options.method == "volatility" and options.weighting == "exponential" else [0.] * len(selected)
                        scale = estimate([ref_moves[d].value for d in selected],
                            [target_moves[d].value for d in selected] if options.method == "beta" else [], ages, options)
                    if scale is None:
                        limitation = "Risk scale unavailable: zero/near-zero beta, constant reference or nonpositive downside estimate"
            value = numerator.value / scale if numerator and scale is not None else None
            values.append(value if value is not None and isfinite(value) else None)
            divisors.append(scale)
            baselines.append(numerator.start if numerator and settings.measure != "level" else None)
            current_estimates.append(AdjustmentEstimate(reference_id=reference.id, scale=scale,
                sample_count=len(selected), start=selected[0] if selected else None, end=selected[-1] if selected else None,
                estimation_measure=basis if options.method != "none" else None, cutoff=cutoff if options.method != "none" else None,
                sample_dates=tuple(selected),
                limitation=limitation or ("Input numerator unavailable: missing native observation or eligible measurement baseline" if not numerator else None)))
        transformed[day], scales[day], starts[day] = tuple(values), tuple(divisors), tuple(baselines)
        estimates = current_estimates
    return transformed, scales, starts, tuple(u.label() for u in input_unit_expressions(definition)), tuple(estimates)
