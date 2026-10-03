"""Rolling input normalization. Estimates never include the measured interval."""
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import date
from math import ceil, floor, fsum, isfinite, sqrt
from typing import cast

from .frequencies import horizon_target, shift_years
from .models import AdjustmentEstimate, Observation, ResolvedDefinition, RiskAdjustment


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


def transform_inputs(definition: ResolvedDefinition, rows: dict[str, dict[date, Observation]], days: list[date]) -> tuple[
    dict[date, tuple[float | None, ...]], dict[date, tuple[float | None, ...]],
    dict[date, tuple[date | None, ...]], tuple[str, ...], tuple[AdjustmentEstimate, ...]]:
    settings = definition.settings
    bindings = {b.id: b for b in (*definition.inputs, *definition.references)}
    moves = {key: measured_moves(value, settings.horizon, settings.measure) for key, value in rows.items()}
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
        legs.append((binding, reference, options, target_moves, ref_moves, sample_days))
    for day in days:
        values, divisors, baselines, current_estimates = [], [], [], []
        for binding, reference, options, target_moves, ref_moves, sample_days in legs:
            move = target_moves.get(day)
            cutoff = move.start if move else horizon_target(day, settings.horizon)
            start = shift_years(cutoff, -options.lookback_years)
            selected = sample_days[bisect_left(sample_days, start):bisect_right(sample_days, cutoff)]
            if options.method == "beta":
                selected = [d for d in selected if target_moves[d].start == ref_moves[d].start]
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
                    if options.method == "beta" and binding.id == reference.id:
                        scale = 1. if any(ref_moves[d].value != ref_moves[selected[0]].value for d in selected) else None
                    else:
                        ages = [float((cutoff-d).days // 7 * 5 + sum((d.weekday()+i) % 7 < 5 for i in range(1, (cutoff-d).days % 7 + 1))) for d in selected] if options.method == "volatility" and options.weighting == "exponential" else [0.] * len(selected)
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
