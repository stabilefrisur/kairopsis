from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from kairopsis.models import AnalysisSettings
from kairopsis.analytics import evaluate
from kairopsis.references import analysis_start
from kairopsis.evaluation_comparison import compare
from test_standardization import calculation
from test_library_previews import client
from test_rebuild_http import PNG
from test_rebuild_analytics import NOW


def result(dates, values, **options):
    return calculation(dates, values, [0] * len(values), "difference", AnalysisSettings(
        minimum_history=3, standardization="zscore", **options))


def test_rolling_uses_only_each_dates_prior_sample_and_preserves_past_scores():
    dates = [date(2026, 9, 21) + timedelta(days=i) for i in (0, 1, 2, 3, 4, 7)]
    rolling = result(dates, [1, 2, 3, 8, 4, 100], reference_mode="rolling")
    assert [p.value for p in rolling.points[:3]] == [None] * 3
    assert rolling.points[3].value == 6  # (8 - 2) / 1; 8 excluded from the sample.
    assert rolling.points[3].reference_estimate.sample_count == 3
    assert rolling.points[3].reference_estimate.end == dates[2]
    prefix = result(dates[:5], [1, 2, 3, 8, 4], reference_mode="rolling")
    assert rolling.points[:5] == prefix.points
    assert rolling.standardization_estimate == rolling.points[-1].reference_estimate
    # Rank unstandardized values, not differently standardized historical scores.
    assert rolling.percentile == 100 and rolling.eligible


def test_rolling_calendar_window_and_native_eligibility():
    dates = [date(2026, 6, 29), date(2026, 6, 30), date(2026, 9, 25), date(2026, 9, 28), date(2026, 9, 30)]
    rolling = result(dates, [10000, 1, 2, 3, 8], reference_mode="rolling", history_years=.25)
    assert rolling.current == 6
    assert rolling.standardization_estimate.start == date(2026, 6, 30)
    assert rolling.standardization_estimate.sample_count == 3


def test_fixed_reference_is_inclusive_and_survives_later_observations():
    dates = [date(2026, 9, 21) + timedelta(days=i) for i in (0, 1, 2, 3, 4, 7)]
    options = dict(reference_mode="fixed", reference_start=dates[0], reference_end=dates[2])
    fixed = result(dates, [1, 2, 3, 8, 4, 100], **options)
    assert fixed.current == 98 and fixed.points[3].value == 6
    assert fixed.standardization_estimate.mean == 2
    assert fixed.standardization_estimate.standard_deviation == 1
    assert fixed.standardization_estimate.sample_count == 3
    prefix = result(dates[:5], [1, 2, 3, 8, 4], **options)
    assert fixed.points[:5] == prefix.points
    assert fixed.percentile == 100


def test_fixed_original_units_changes_rank_without_changing_chart_values():
    dates = [date(2026, 9, 21) + timedelta(days=i) for i in (0, 1, 2, 3, 4, 7)]
    values = [1, 2, 3, 50, 100, 4]
    original = calculation(dates, values, [0] * 6, "difference", AnalysisSettings(minimum_history=3))
    fixed = calculation(dates, values, [0] * 6, "difference", AnalysisSettings(minimum_history=3,
        reference_mode="fixed", reference_start=dates[0], reference_end=dates[2]))
    assert fixed.points == original.points
    assert fixed.percentile == 100 and original.percentile == 60


@pytest.mark.parametrize("standardization", ["none", "zscore"])
def test_fixed_period_including_current_or_future_is_unavailable(standardization):
    dates = [date(2026, 9, 21) + timedelta(days=i) for i in range(4)]
    evaluation = calculation(dates, [1, 2, 3, 8], [0]*4, "difference", AnalysisSettings(
        minimum_history=3, standardization=standardization, reference_mode="fixed",
        reference_start=dates[0], reference_end=dates[-1]))
    assert not evaluation.eligible and evaluation.percentile is None
    assert any("must end before" in text for text in evaluation.limitations)


def test_reference_validation_and_legacy_default():
    assert AnalysisSettings().reference_mode == "current"
    for fields in ({"reference_mode": "fixed"}, {"reference_mode": "rolling", "reference_start": "2020-01-01"},
                   {"reference_mode": "fixed", "reference_start": "2021-01-01", "reference_end": "2020-01-01"}):
        with pytest.raises(ValidationError):
            AnalysisSettings(**fields)


def test_rolling_excludes_carried_values_and_handles_constant_samples():
    dates = [date(2026, 9, 21) + timedelta(days=i) for i in (0, 1, 2, 3, 4)]
    original = result(dates, [1, 10000, 2, 3, 8], reference_mode="rolling")
    left = original.data.series[0]
    rows = list(left.observations)
    rows[1] = rows[1].model_copy(update={'observed_on': dates[0]})
    data = original.data.model_copy(update={'series': (left.model_copy(update={'observations': tuple(rows)}), original.data.series[1])})
    carried = evaluate(original.definition, data, original.request, NOW)
    assert carried.current == 6 and carried.standardization_estimate.sample_count == 3
    assert not carried.points[1].eligible
    constant = result(dates, [1, 1, 1, 1, 8], reference_mode="rolling")
    assert constant.current is None and not constant.eligible
    assert 'zero or near zero' in constant.standardization_estimate.limitation


def test_rolling_and_fixed_retrieval_include_reference_and_risk_warmup():
    settings = AnalysisSettings(reference_mode="rolling", standardization="zscore", history_years=3,
        risk_adjustment={"method": "volatility", "lookback_years": 2}, measure="change")
    assert analysis_start(date(2026, 9, 30), settings, 2, (5,)) == date(2016, 9, 30) - timedelta(days=35)
    fixed = AnalysisSettings(reference_mode="fixed", reference_start=date(2000, 1, 1), reference_end=date(2002, 1, 1))
    assert analysis_start(date(2026, 9, 30), fixed, 1, (5,)) == date(2000, 1, 1)


def test_rolling_reference_drift_does_not_create_a_new_market_flag():
    dates = [date(2026, 6, 30), date(2026, 9, 25), date(2026, 9, 28), date(2026, 9, 29), date(2026, 9, 30)]
    options = dict(reference_mode="rolling", history_years=.25, zscore_threshold=1)
    baseline = result(dates, [100, 0, 0, 0, 2], **options)
    latest = result([*dates, date(2026, 10, 1)], [100, 0, 0, 0, 2, 2], **options)
    assert latest.conditions and compare(latest, baseline).finding == "quiet"


def test_unified_routes_draft_capture_save_and_reference_evidence(tmp_path):
    with client(tmp_path) as http:
        before = http.get('/api/library').json()
        original = next(a for a in before['analyses'] if a['id'] == 'usd-ig')
        assert http.get('/analyses/new').status_code == 200
        assert http.get('/library?edit=usd-ig', follow_redirects=False).headers['location'] == '/analyses/usd-ig'
        draft = {**original, 'name': 'Draft rolling', 'settings': {**original['settings'],
            'measure': 'change', 'standardization': 'zscore', 'reference_mode': 'rolling'}}
        preview = http.post('/api/library/analyses/preview', json={'analysis': draft, 'retain': True}).json()
        assert http.get('/api/library').json() == before
        assert http.get(f'/api/evaluations/{preview["id"]}').status_code == 200
        capture = http.post('/api/ideas', json={'evaluation_id': preview['id'], 'display': {'years': 1}, 'image': PNG, 'title': 'Rolling evidence'})
        assert capture.status_code == 200, capture.text
        saved = http.post('/api/library/analyses/bundle', json={'analysis': draft, 'series_drafts': [],
            'base_revisions': {'analyses': {'usd-ig': original['revision']}, 'series': {}}})
        assert saved.status_code == 200, saved.text
        assert saved.json()['analysis']['revision'] == original['revision'] + 1
    with client(tmp_path) as http:
        retained = http.get(f'/api/evaluations/{preview["id"]}').json()
        assert retained['points'] == preview['points']
        assert retained['points'][-1]['reference_estimate']['end'] < retained['observation_date']
    csv = next((tmp_path / 'workspace').rglob('data.csv')).read_text()
    assert 'reference_mean,reference_sd,reference_count,reference_start,reference_end' in csv
