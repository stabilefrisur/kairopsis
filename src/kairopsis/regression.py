"""Prior-only rolling intercept OLS, with a retained fit for each chart date."""
from bisect import bisect_left
from math import isfinite

import pandas as pd  # type: ignore[import-untyped]

from .frequencies import previous_session
from .models import AnalysisSettings, Fit, MetricPoint
from .periods import period_start


def rolling_fits(points: list[MetricPoint], settings: AnalysisSettings) -> list[Fit | None]:
    sample = [p for p in points if p.eligible]
    dates = [p.date for p in sample]
    # Array slices keep long daily histories responsive while recalculating
    # centered moments in each window, without drifting incremental estimates.
    values = pd.DataFrame([(p.transformed_inputs or p.inputs) for p in sample], columns=["y", "x"], dtype=float).to_numpy()
    fits: list[Fit | None] = []
    for point in points:
        start = period_start(point.date, settings.fit_years)
        left, right = bisect_left(dates, start), bisect_left(dates, point.date)
        if (right - left < settings.minimum_fit
                or settings.fit_years != "all" and (dates[left] - start).days > 7
                or (previous_session(point.date) - dates[right - 1]).days > 7):
            fits.append(None)
            continue
        ys, xs = values[left:right, 0], values[left:right, 1]
        # Subtract a nearby anchor before averaging large levels with small moves.
        x0, y0 = float(xs[0]), float(ys[0])
        dx, dy = xs - x0, ys - y0
        xm, ym = float(dx.mean()), float(dy.mean())
        cx, cy = dx - xm, dy - ym
        xx, yy = float((cx * cx).sum()), float((cy * cy).sum())
        if not xx:
            fits.append(None)
            continue
        slope = float((cx * cy).sum()) / xx
        intercept = (y0 + ym) - slope * (x0 + xm)
        residuals = cy - slope * cx
        sse = float((residuals * residuals).sum())
        if not all(isfinite(v) for v in (slope, intercept, xx, yy, sse)):
            fits.append(None)
            continue
        fits.append(Fit(slope=slope, intercept=intercept, r_squared=1-sse/yy if yy else None,
            sample_count=right-left, start=dates[left], end=dates[right-1], x_min=float(xs.min()), x_max=float(xs.max())))
    return fits
