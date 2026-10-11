import csv
from datetime import date, timedelta
from math import sin

import pytest
from pydantic import ValidationError

from kairopsis.analytics import evaluate, regression
from kairopsis.evaluation_comparison import compare
from kairopsis.models import AnalysisSettings, MetricPoint
from kairopsis.periods import period_start
from kairopsis.references import analysis_start
from test_standardization import calculation
from test_rebuild_analytics import NOW
from test_library_previews import client
from test_rebuild_http import PNG


def days(count):
    start = date(2025, 1, 1)
    return [start + timedelta(days=i) for i in range(count * 2) if (start + timedelta(days=i)).weekday() < 5][:count]


def residual(dates, ys, xs, **options):
    return calculation(dates, ys, xs, "regression", AnalysisSettings(
        fit_mode="rolling", fit_years=options.pop("fit_years", "all"), minimum_fit=3, minimum_history=3, **options))


def test_rolling_residual_hand_fit_excludes_current_and_future():
    dates, xs, ys = days(7), [1, 2, 3, 4, 5, 6, 7], [3, 5, 7, 13, 11, 16, 20]
    full = residual(dates, ys, xs)
    assert [p.value for p in full.points[:3]] == [None] * 3
    p = full.points[3]
    assert p.value == pytest.approx(4)  # 13 - (1 + 2*4), using only the first 3 rows.
    assert p.fit_estimate.slope == 2 and p.fit_estimate.intercept == 1
    assert p.fit_estimate.end == dates[2] and p.fit_estimate.sample_count == 3
    prefix = residual(dates[:5], ys[:5], xs[:5])
    assert full.points[:5] == prefix.points
    shocked = residual(dates, [*ys[:-1], 10000], xs)
    assert full.points[:-1] == shocked.points[:-1]
    assert full.fit == shocked.fit == full.points[-1].fit_estimate
    assert any("prior-only fit" in text for text in full.limitations)


@pytest.mark.parametrize("years", [.25, "all"])
def test_rolling_matches_independent_ols_at_each_date_with_gaps_and_large_levels(years):
    dates = days(150)
    xs = [1e9 + sin(i*.43) for i in range(150)]
    ys = [3*x + sin(i*.78) for i, x in enumerate(xs)]
    ys[83] = None
    result = residual(dates, ys, xs, fit_years=years)
    input_points = [MetricPoint(date=d, value=y, inputs=(y, x), observed_on=(d, d), eligible=y is not None)
                    for d, y, x in zip(dates, ys, xs)]
    for point in result.points[65::7]:
        expected = regression(input_points, point.date, result.definition, years)
        actual = point.fit_estimate
        assert (actual is None) == (expected is None)
        if expected:
            assert actual.slope == pytest.approx(expected.slope, abs=1e-10)
            assert actual.intercept == pytest.approx(expected.intercept, abs=.01)
            assert actual.sample_count == expected.sample_count
            assert (actual.start, actual.end) == (expected.start, expected.end)
            assert actual.end < point.date
            # The legacy oracle subtracts fitted billion-unit levels when
            # computing SSE; allow its cancellation error in the comparison.
            assert actual.r_squared == pytest.approx(expected.r_squared, abs=1e-7)
    assert result.fit.start >= period_start(dates[-1], years)
    assert not result.points[83].eligible


def test_fit_eligibility_coverage_staleness_and_constant_input():
    dates = days(100)
    short = residual(dates[:12], list(range(12)), list(range(12)), fit_years=.25)
    assert all(p.value is None for p in short.points)  # Full calendar window required.
    constant = residual(dates, list(range(100)), [5]*100)
    assert constant.fit is None and constant.current is None
    original = residual(dates, [2*i + sin(i) for i in range(100)], list(range(100)))
    rows = list(original.data.series[0].observations)
    rows[20] = rows[20].model_copy(update={"observed_on": dates[19], "value": 10000})
    for i in range(88, 99):
        rows[i] = rows[i].model_copy(update={"value": None})
    data = original.data.model_copy(update={"series": (
        original.data.series[0].model_copy(update={"observations": tuple(rows)}), original.data.series[1])})
    actual = evaluate(original.definition, data, original.request, NOW)
    assert actual.points[21].fit_estimate.sample_count == 20  # Carried row excluded.
    assert actual.fit is None and actual.current is None  # Last prior sample stale.
    assert actual.points[80].value is not None  # Latest failure retains earlier fits.


def test_rolling_fit_and_rolling_zscore_preserve_past_results():
    dates = days(35)
    xs = [20 + sin(i) for i in range(35)]
    ys = [3*x + sin(i*.7) for i, x in enumerate(xs)]
    options = dict(standardization="zscore", reference_mode="rolling")
    full = residual(dates, ys, xs, **options)
    prefix = residual(dates[:25], ys[:25], xs[:25], **options)
    assert full.points[:25] == prefix.points
    assert full.points[-1].fit_estimate.end < dates[-1]
    assert full.points[-1].reference_estimate.end < dates[-1]
    assert full.current is not None and full.eligible


def test_current_fit_remains_default_and_rolling_warmup_composes_with_references_and_risk():
    assert AnalysisSettings().fit_mode == "current"
    with pytest.raises(ValidationError):
        AnalysisSettings(fit_mode="fixed")
    settings = AnalysisSettings(fit_mode="rolling", fit_years=3, standardization="zscore",
        reference_mode="rolling", history_years=2, measure="change", risk_adjustment={"method": "volatility", "lookback_years": 1})
    # Five displayed years + two reference + three fit + one risk + move baseline.
    assert analysis_start(date(2026, 9, 30), settings, 2, (5,), calculation="regression") == date(2015, 8, 26)
    assert analysis_start(date(2026, 9, 30), settings, 2, (5,)) == date(2018, 8, 26)
    fixed = settings.model_copy(update={"reference_mode": "fixed", "reference_start": date(2000, 1, 1), "reference_end": date(2001, 1, 1)})
    assert analysis_start(date(2026, 9, 30), fixed, 2, (5,), calculation="regression") == date(1995, 11, 27)


def test_refitting_without_new_input_move_does_not_create_repeat_flag():
    dates = days(101)
    xs = [i % 19 for i in range(100)]
    ys = [10 + 2*x for x in xs]
    ys[-1] += 8
    old = residual(dates[:100], ys, xs, material_change=.01)
    new = residual(dates, [*ys, ys[-1]], [*xs, xs[-1]], material_change=.01)
    assert old.fit != new.fit and old.current != new.current
    checked = compare(new, old)
    assert checked.finding == "unchanged" and not checked.reasons


def test_rolling_fit_persists_through_library_preview_capture_and_restart(tmp_path):
    with client(tmp_path) as http:
        catalogue = http.get('/api/library').json()
        original = next(a for a in catalogue['analyses'] if len(a['series_ids']) == 2)
        draft = {**original, 'calculation': 'regression', 'settings': {**original['settings'],
            'fit_mode': 'rolling', 'fit_years': 1}}
        response = http.post('/api/library/analyses/preview', json={'analysis': draft, 'retain': True})
        assert response.status_code == 200, response.text
        preview = response.json()
        assert preview['fit'] == preview['points'][-1]['fit_estimate']
        assert preview['fit']['end'] < preview['observation_date']
        captured = http.post('/api/ideas', json={'evaluation_id': preview['id'], 'display': {'years': 1}, 'image': PNG, 'title': 'Rolling fit'})
        assert captured.status_code == 200, captured.text
        saved = http.post('/api/library/analyses/bundle', json={'analysis': draft, 'series_drafts': [],
            'base_revisions': {'analyses': {original['id']: original['revision']}, 'series': {}}})
        assert saved.status_code == 200, saved.text
    with client(tmp_path) as http:
        retained = http.get(f'/api/evaluations/{preview["id"]}').json()
        assert retained['points'] == preview['points']
        stored = next(a for a in http.get('/api/library').json()['analyses'] if a['id'] == original['id'])
        assert stored['settings']['fit_mode'] == 'rolling'
    with next((tmp_path / 'workspace').rglob('data.csv')).open() as data:
        rows = list(csv.DictReader(data))
    assert float(rows[-1]['fit_slope']) == preview['fit']['slope']
    assert rows[-1]['fit_end'] == preview['fit']['end']
