"""Standardize the completed analysis using its current prior-history reference."""
from math import fsum, isfinite, sqrt

from .models import AnalysisSettings, MetricPoint, StandardizationEstimate
from .periods import period_start


def standardize(points: list[MetricPoint], settings: AnalysisSettings, unit: str) -> tuple[list[MetricPoint], StandardizationEstimate]:
    current = points[-1].date if points else None
    sample = [p for p in points if current and p.eligible and p.value is not None and
        period_start(current, settings.history_years) <= p.date < current]
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
    estimate = StandardizationEstimate(mean=mean, standard_deviation=deviation, sample_count=len(sample),
        start=sample[0].date if sample else None, end=sample[-1].date if sample else None, unit=unit, limitation=limitation)
    transformed = []
    for point in points:
        value = (point.value - mean) / deviation if point.value is not None and mean is not None and deviation is not None else None
        value = value if value is not None and isfinite(value) else None
        transformed.append(point.model_copy(update={"unstandardized_value": point.value, "value": value,
            "eligible": point.eligible and value is not None}))
    return transformed, estimate
