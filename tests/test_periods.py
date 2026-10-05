from datetime import date, timedelta
from statistics import stdev

import pytest
from pydantic import ValidationError

from kairopsis.analytics import evaluate
from kairopsis.models import AnalysisSettings, DataRequest, DataResponse, Observation, ResolvedDefinition, SeriesResult
from kairopsis.periods import AVAILABLE_START, period_start
from kairopsis.risk import measured_moves, estimate
from test_rebuild_analytics import NOW, binding
from test_rebuild_http import client, PNG
from test_risk_adjustment import example


def test_month_windows_clamp_leap_dates_and_reject_unsupported_periods():
    assert period_start(date(2024, 5, 31), .25) == date(2024, 2, 29)
    assert period_start(date(2025, 8, 31), .5) == date(2025, 2, 28)
    for invalid in (0, .1, 1.5, 31, "maximum"):
        with pytest.raises(ValidationError):
            AnalysisSettings(history_years=invalid)


def test_three_month_percentile_excludes_earlier_history_and_current():
    b = binding()
    dates = [date(2026, 6, 29), date(2026, 6, 30), date(2026, 7, 1), date(2026, 9, 29), date(2026, 9, 30)]
    data = DataResponse(mode="mock", requested=(b.id,), attempted_at=NOW, completed_at=NOW, outcome="synthetic",
        series=(SeriesResult(binding=b, provenance="Window boundary example", observations=tuple(
            Observation(date=d, observed_on=d, value=v) for d, v in zip(dates, [100, 1, 3, 5, 3]))),))
    definition = ResolvedDefinition(id="example", name="Example", revision=1, calculation="level", inputs=(b,),
        settings=AnalysisSettings(history_years=.25, minimum_history=3))
    request = DataRequest(bindings=(b,), start=dates[0], end=dates[-1])
    assert evaluate(definition, data, request, NOW).percentile == 50
    definition = definition.model_copy(update={"settings": definition.settings.model_copy(update={"history_years": "all"})})
    assert evaluate(definition, data, request, NOW).percentile == 37.5


def test_longest_regression_uses_common_native_history_without_full_fixed_window():
    inputs = (binding(), binding("b"))
    dates = [date(2026, 7, 1) + timedelta(days=i) for i in range(92) if (date(2026, 7, 1) + timedelta(days=i)).weekday() < 5]
    definition = ResolvedDefinition(id="pair", name="Pair", revision=1, calculation="regression", inputs=inputs,
        settings=AnalysisSettings(history_years="all", fit_years="all", minimum_history=3))
    data = DataResponse(mode="mock", requested=("a", "b"), attempted_at=NOW, completed_at=NOW, outcome="synthetic",
        series=tuple(SeriesResult(binding=b, provenance="y = 10 + 2x", observations=tuple(
            Observation(date=d, observed_on=d, value=10 + 2*(i % 19) + (8 if d == dates[-1] else 0) if b.id == "a" else i % 19)
            for i, d in enumerate(dates) if b.id == "a" or d >= date(2026, 8, 3))) for b in inputs))
    request = DataRequest(bindings=inputs, start=AVAILABLE_START, end=dates[-1])
    result = evaluate(definition, data, request, NOW)
    assert result.fit.start == date(2026, 8, 3)
    assert result.fit.sample_count == len(data.series[1].observations) - 1
    assert result.fit.slope == 2 and result.fit.intercept == 10
    assert result.current == 8 and result.percentile == 100 and result.eligible


@pytest.mark.parametrize("method,weighting", [("volatility", "equal"), ("volatility", "exponential"), ("beta", "equal"), ("var", "equal"), ("es", "equal")])
def test_longest_risk_estimates_use_common_moves_and_exclude_measured_interval(method, weighting):
    original = example("week", method=method, reference="a" if method == "beta" else None)
    settings = original.definition.settings.model_copy(update={"risk_adjustment": original.definition.settings.risk_adjustment.model_copy(update={"lookback_years": "all", "weighting": weighting})})
    definition = original.definition.model_copy(update={"settings": settings})
    right = original.data.series[1].model_copy(update={"observations": original.data.series[1].observations[100:]})
    data = original.data.model_copy(update={"series": (original.data.series[0], right)})
    result = evaluate(definition, data, original.request, NOW)
    moves = [measured_moves({o.date: o for o in series.observations}, "week", "change") for series in data.series]
    cutoff = min(result.points[-1].period_start)
    expected = sorted(d for d in set(moves[0]) & set(moves[1]) if d <= cutoff)
    assert all(r.sample_count == len(expected) and r.start == expected[0] and r.end == expected[-1] for r in result.adjustment_estimates)
    ages = [float(sum((d + timedelta(days=i)).weekday() < 5 for i in range(1, (cutoff - d).days + 1))) for d in expected]
    reference = [moves[0][d].value for d in expected]
    expected_scale = estimate(reference, reference if method == "beta" else [], ages, settings.risk_adjustment)
    assert result.adjustment_estimates[0].scale == pytest.approx(expected_scale)
    if method == "volatility" and weighting == "equal":
        assert result.adjustment_estimates[0].scale == pytest.approx(stdev(reference))
    assert result.adjustment_estimates[1].scale == pytest.approx(3 * result.adjustment_estimates[0].scale)


@pytest.mark.parametrize("history,fit,risk", [("all", .5, .25), (.25, "all", .5), (.5, .25, "all")])
def test_month_and_available_periods_survive_library_snapshot_and_restart(tmp_path, history, fit, risk):
    from kairopsis.fixtures import MockMarketData

    class BoundedProvider:
        def __init__(self):
            self.requests = []

        def fetch(self, request):
            self.requests.append(request)
            return MockMarketData(lambda: NOW).fetch(request.model_copy(update={"start": request.end - timedelta(days=150)}))

    provider = BoundedProvider()
    options = {"history_years": history, "fit_years": fit, "measure": "change",
        "risk_adjustment": {"method": "volatility", "lookback_years": risk}}
    with client(tmp_path, provider) as http:
        before = http.get("/api/library").json()
        response = http.post("/api/analyses/ig-em-hy/preview", json=options)
        assert response.status_code == 200, response.text
        evaluation = response.json()
        assert provider.requests[-1].start == AVAILABLE_START
        assert all(r["scale"] is not None for r in evaluation["adjustment_estimates"])
        assert http.get("/api/library").json() == before
        original = next(a for a in before["analyses"] if a["id"] == "ig-em-hy")
        assert http.post("/api/library/analyses", json={**original, "settings": {**original["settings"], **options}}).status_code == 200
        captured = http.post("/api/ideas", json={"evaluation_id": evaluation["id"], "display": {"years": 1}, "image": PNG, "title": "Period evidence"})
        assert captured.status_code == 200, captured.text
        idea = captured.json()
    with client(tmp_path, provider) as http:
        definition = next(a for a in http.get("/api/library").json()["analyses"] if a["id"] == "ig-em-hy")
        snapshot = http.get(f"/api/ideas/{idea['id']}").json()["snapshots"][idea["charts"][0]["id"]]
        for settings in (definition["settings"], snapshot["evaluation"]["definition"]["settings"]):
            assert settings["history_years"] == history and settings["fit_years"] == fit
            assert settings["risk_adjustment"]["lookback_years"] == risk
