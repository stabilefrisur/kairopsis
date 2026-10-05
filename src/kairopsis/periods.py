"""Calendar estimation periods, preserving legacy numeric year settings."""
from calendar import monthrange
from datetime import date, timedelta
from typing import Annotated, Iterable, Literal

from pydantic import AfterValidator

# Metapyle requires a start date. Stay inside pandas' nanosecond date range.
AVAILABLE_START = date(1677, 9, 22)


def validate_period(value: int | float | Literal["all"]) -> int | float | Literal["all"]:
    if value != "all" and not (value in (.25, .5) or 1 <= value <= 30 and value == int(value)):
        raise ValueError("Choose 3 months, 6 months, 1–30 whole years or all available history")
    return value


Period = Annotated[int | float | Literal["all"], AfterValidator(validate_period)]


def period_start(day: date, period: Period) -> date:
    if period == "all":
        return AVAILABLE_START
    months = day.year * 12 + day.month - 1 - round(period * 12)
    year, month = divmod(months, 12)
    return date(year, month + 1, min(day.day, monthrange(year, month + 1)[1]))


def period_label(period: Period) -> str:
    if period == "all":
        return "Longest available history"
    return f"{round(period * 12)} months" if period < 1 else f"{period:g} {'year' if period == 1 else 'years'}"


def retrieval_start(end: date, periods: Iterable[Period], risk_periods: Iterable[Period], measured: bool) -> date:
    periods, risk_periods = tuple(periods), tuple(risk_periods)
    if "all" in (*periods, *risk_periods):
        return AVAILABLE_START
    start = min(period_start(end, period) for period in periods)
    if risk_periods:
        start = min(period_start(start, period) for period in risk_periods)
    return start - timedelta(days=35 if measured else 0)
