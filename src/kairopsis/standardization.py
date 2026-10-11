"""Standardize completed results against an as-of, rolling or calendar reference."""
from bisect import bisect_left, bisect_right
from datetime import date
from math import fsum, isfinite, sqrt

from .models import AnalysisSettings, MetricPoint, StandardizationEstimate
from .references import reference_bounds


def estimate(sample: list[MetricPoint], settings: AnalysisSettings, unit: str) -> StandardizationEstimate:
    mean = deviation = None
    limitation = None
    if len(sample) < settings.minimum_history:
        limitation = f"Z-score unavailable: {len(sample)} prior common observations; require {settings.minimum_history}"
    else:
        values = [p.value for p in sample if p.value is not None]
        mean = fsum(values) / len(values)
        deviation = sqrt(fsum((value - mean) ** 2 for value in values) / (len(values) - 1))
        if not isfinite(mean) or not isfinite(deviation) or deviation <= 1e-12:
            deviation = None
            limitation = "Z-score unavailable: reference standard deviation is zero or near zero"
    return StandardizationEstimate(mean=mean, standard_deviation=deviation, sample_count=len(sample),
        start=sample[0].date if sample else None, end=sample[-1].date if sample else None, unit=unit, limitation=limitation)


def standardize(points: list[MetricPoint], settings: AnalysisSettings, unit: str) -> tuple[list[MetricPoint], StandardizationEstimate]:
    eligible = [p for p in points if p.eligible and p.value is not None]
    dates = [p.date for p in eligible]
    def reference(day: date) -> StandardizationEstimate:
        start, end = reference_bounds(settings, day)
        if end >= day:
            return StandardizationEstimate(unit=unit, limitation="Fixed reference must end before the latest observation")
        return estimate(eligible[bisect_left(dates, start):bisect_right(dates, end)], settings, unit)
    current = reference(points[-1].date) if points else estimate([], settings, unit)
    transformed = []
    for point in points:
        ref = reference(point.date) if settings.reference_mode == "rolling" else current
        mean, deviation = ref.mean, ref.standard_deviation
        value = (point.value - mean) / deviation if point.value is not None and mean is not None and deviation is not None else None
        value = value if value is not None and isfinite(value) else None
        transformed.append(point.model_copy(update={"unstandardized_value": point.value, "value": value,
            "eligible": point.eligible and value is not None,
            "reference_estimate": ref if settings.reference_mode == "rolling" else None}))
    return transformed, current
