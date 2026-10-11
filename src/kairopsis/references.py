"""Reference sample boundaries shared by scoring, ranking and retrieval."""
from datetime import date, timedelta
from typing import Iterable

from .models import AnalysisSettings
from .periods import AVAILABLE_START, Period, period_label, period_start


def reference_bounds(settings: AnalysisSettings, current: date) -> tuple[date, date]:
    """Inclusive dates; every reference excludes the evaluation's current point."""
    if settings.reference_mode == "fixed":
        assert settings.reference_start is not None and settings.reference_end is not None
        return settings.reference_start, settings.reference_end
    return period_start(current, settings.history_years), current - timedelta(days=1)


def reference_label(settings: AnalysisSettings) -> str:
    if settings.reference_mode == "fixed":
        return f"Fixed dates {settings.reference_start} to {settings.reference_end}"
    return f"{period_label(settings.history_years)} / {'rolling window' if settings.reference_mode == 'rolling' else 'as-of window'}"


def analysis_start(end: date, settings: AnalysisSettings, count: int, periods: Iterable[Period], *, calculation: str = "level") -> date:
    start = min(period_start(end, p) for p in (*periods, settings.history_years, settings.fit_years))
    if settings.reference_mode == "rolling" and settings.standardization == "zscore":
        start = AVAILABLE_START if start == AVAILABLE_START else period_start(start, settings.history_years)
    if settings.reference_mode == "fixed" and settings.reference_start:
        start = min(start, settings.reference_start)
    if calculation == "regression" and settings.fit_mode == "rolling":
        start = AVAILABLE_START if start == AVAILABLE_START else period_start(start, settings.fit_years)
    risk_periods = [r.lookback_years for r in settings.adjustments(count) if r.method != "none"]
    if start == AVAILABLE_START or "all" in risk_periods:
        return AVAILABLE_START
    if risk_periods:
        start = min(period_start(start, p) for p in risk_periods)
    return start - timedelta(days=35 if settings.needs_moves(count) else 0)
