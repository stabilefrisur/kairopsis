"""Calendar measurement intervals with explicit weekday baseline tolerance."""
from calendar import monthrange
from datetime import date, timedelta


def shift_years(day: date, years: int) -> date:
    return day.replace(year=day.year + years, day=min(day.day, monthrange(day.year + years, day.month)[1]))


def previous_session(day: date) -> date:
    day -= timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def expected_session(day: date) -> date:
    return day if day.weekday() < 5 else previous_session(day + timedelta(days=1))


def horizon_target(day: date, horizon: str) -> date:
    if horizon == "day":
        return previous_session(day)
    if horizon == "week":
        return day - timedelta(days=7)
    month, year = (day.month - 1, day.year) if day.month > 1 else (12, day.year - 1)
    return date(year, month, min(day.day, monthrange(year, month)[1]))
