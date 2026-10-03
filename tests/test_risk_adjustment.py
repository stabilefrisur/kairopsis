from datetime import date, timedelta
from copy import deepcopy
from math import sqrt

import pytest

from kairopsis.analytics import evaluate
from kairopsis.models import AnalysisSettings, DataRequest, DataResponse, Observation, ResolvedDefinition, RiskAdjustment, SeriesResult
from kairopsis.risk import estimate, measured_moves
from test_rebuild_analytics import NOW, binding
from test_rebuild_http import PNG, client


@pytest.mark.parametrize("options,expected", [
    ({"method": "volatility"}, sqrt(5/3)),
    ({"method": "beta"}, 3.),
    ({"method": "var", "confidence": 75}, 3.),
    ({"method": "es", "confidence": 62.5}, 11/3),
    ({"method": "var", "confidence": 75, "downside": "decrease"}, -2.),
])
def test_estimators_against_hand_worked_examples(options, expected):
    actual = estimate([1., 2., 3., 4.], [5., 8., 11., 14.], [3., 2., 1., 0.], RiskAdjustment(**options))
    # Nonpositive downside estimates cannot serve as risk divisors.
    assert actual is None if expected < 0 else actual == pytest.approx(expected)


def test_exponential_variance_uses_normalized_weights_and_sample_correction():
    # Weights 1/4, 1/2, 1 -> mean 2; numerator 5/2, correction 1.
    result = estimate([0., 1., 3.], [], [2., 1., 0.], RiskAdjustment(method="volatility", weighting="exponential", half_life=1))
    assert result == pytest.approx(sqrt(5/2))


def test_constant_reference_zero_beta_and_negative_beta():
    assert estimate([2., 2., 2.], [1., 2., 3.], [2., 1., 0.], RiskAdjustment(method="beta")) is None
    assert estimate([1., 2., 3.], [2., 2., 2.], [2., 1., 0.], RiskAdjustment(method="beta")) is None
    assert estimate([1., 2., 3.], [-1., -2., -3.], [2., 1., 0.], RiskAdjustment(method="beta")) == -1
    assert estimate([2., 2., 2.], [], [2., 1., 0.], RiskAdjustment(method="volatility")) is None


def example(frequency="day", method="beta", reference="a", shock=0., overrides=()):
    inputs = (binding(), binding("b"))
    refs = (binding("c"),) if reference == "c" else ()
    settings = AnalysisSettings(measure="change", horizon=frequency, minimum_history=3,
        risk_adjustment=RiskAdjustment(method=method, reference_id=reference, minimum_samples=3, lookback_years=1), risk_overrides=overrides)
    definition = ResolvedDefinition(id="pair", revision=1, name="Pair", calculation="difference", inputs=inputs, references=refs, settings=settings)
    days = []
    day = date(2025, 1, 1)
    while day <= date(2026, 9, 30):
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    values = [100.]
    for i in range(1, len(days)):
        values.append(values[-1] + [1., -2., 3., -1.][i % 4])
    series = []
    for b in (*inputs, *refs):
        factor = 3 if b.id == "b" else 2 if b.id == "c" else 1
        series.append(SeriesResult(binding=b, provenance="y = 3x + 20", observations=tuple(
            Observation(date=d, observed_on=d, value=factor*v+20+(shock if d == days[-1] and b.id == "b" else 0)) for d, v in zip(days, values))))
    response = DataResponse(mode="mock", requested=tuple(b.id for b in (*inputs, *refs)), series=tuple(series), attempted_at=NOW, completed_at=NOW, outcome="synthetic")
    return evaluate(definition, response, DataRequest(bindings=(*inputs, *refs), start=days[0], end=days[-1]), NOW)


@pytest.mark.parametrize("frequency", ["day", "week", "month"])
def test_shared_beta_reference_preserves_self_and_normalizes_other_leg(frequency):
    result = example(frequency)
    assert [r.scale for r in result.adjustment_estimates] == pytest.approx([1., 3.])
    assert result.points[-1].transformed_inputs[0] == pytest.approx(result.points[-1].transformed_inputs[1])
    assert result.current == pytest.approx(0.)
    assert result.input_units == ("bp", "bp")
    assert all(r.end <= min(result.points[-1].period_start) for r in result.adjustment_estimates)


def test_measured_shock_does_not_enter_current_beta_or_volatility_estimate():
    baseline = example("month")
    shock = example("month", shock=300.)
    assert shock.adjustment_estimates == baseline.adjustment_estimates
    assert shock.current == pytest.approx(baseline.current - 100.)
    baseline = example("week", method="volatility", reference=None)
    shock = example("week", method="volatility", reference=None, shock=300.)
    assert shock.adjustment_estimates == baseline.adjustment_estimates


def test_external_reference_beta_and_mixed_units_rejected_for_difference():
    result = example(reference="c")
    assert [r.scale for r in result.adjustment_estimates] == pytest.approx([.5, 1.5])
    assert result.current == pytest.approx(0.)
    with pytest.raises(ValueError, match="matching units"):
        example(overrides=(RiskAdjustment(method="beta", reference_id="a", minimum_samples=3), RiskAdjustment(method="volatility", minimum_samples=3)))


@pytest.mark.parametrize("method", ["volatility", "var", "es"])
def test_self_risk_scales_put_proportional_changes_on_the_same_basis(method):
    result = example(method=method, reference=None)
    assert result.current == pytest.approx(0.)
    assert result.adjustment_estimates[1].scale == pytest.approx(3 * result.adjustment_estimates[0].scale)
    assert result.unit == "risk units"


def test_insufficient_and_stale_reference_estimates_are_unavailable():
    result = example(reference="c")
    settings = result.definition.settings.model_copy(update={"risk_adjustment": RiskAdjustment(method="beta", reference_id="c", minimum_samples=10000)})
    insufficient = evaluate(result.definition.model_copy(update={"settings": settings}), result.data, result.request, NOW)
    assert insufficient.current is None and not insufficient.eligible
    assert "Insufficient estimation" in " ".join(insufficient.limitations)
    reference = result.data.series[-1]
    old = reference.model_copy(update={"observations": tuple(p for p in reference.observations if p.date < date(2026, 6, 1))})
    data = result.data.model_copy(update={"series": (*result.data.series[:-1], old)})
    stale = evaluate(result.definition, data, result.request, NOW)
    assert stale.current is None and not stale.eligible
    assert "Estimation history is stale" in " ".join(stale.limitations)


def test_month_frequency_calendar_baseline_and_no_carried_or_zero_return_baseline():
    dates = [date(2026, 2, 27), date(2026, 3, 31)]
    rows = {d: Observation(date=d, observed_on=d, value=v) for d, v in zip(dates, [100., 120.])}
    assert measured_moves(rows, "month", "return")[dates[-1]].value == pytest.approx(20.)
    rows[dates[0]] = Observation(date=dates[0], observed_on=date(2026, 2, 26), value=100.)
    assert not measured_moves(rows, "month", "change")
    rows[dates[0]] = Observation(date=dates[0], observed_on=dates[0], value=0.)
    assert not measured_moves(rows, "month", "return")


def test_library_defaults_external_dependencies_restart_and_frozen_latest(tmp_path):
    with client(tmp_path) as http:
        original = http.get("/api/library").json()
        http.post("/api/refresh")
        options = {"measure": "change", "horizon": "month", "risk_adjustment": {"method": "beta", "reference_id": "hy"}}
        response = http.post("/api/analyses/usd-ig/preview", json=options)
        assert response.status_code == 200, response.text
        evaluation = response.json()
        assert evaluation["definition"]["references"][0]["id"] == "hy"
        assert http.get("/api/library").json() == original
        idea = http.post("/api/ideas", json={"evaluation_id": evaluation["id"], "image": PNG, "title": "Risk evidence", "display": {"view": "changes"}}).json()
        entry = idea["charts"][0]
        record = next(a for a in original["analyses"] if a["id"] == "usd-ig")
        record["settings"] = deepcopy(evaluation["definition"]["settings"])
        assert http.post("/api/library/analyses", json=record).status_code == 200
        record["settings"]["risk_adjustment"]["method"] = "volatility"
        assert http.post("/api/library/analyses", json=record).status_code == 200
        assert http.delete("/api/library/series/hy").status_code == 422
        series = next(s for s in original["series"] if s["id"] == "hy")
        series["name"] = "Updated reference name"
        http.post("/api/library/series", json=series)
        revised = next(a for a in http.get("/api/library").json()["analyses"] if a["id"] == "usd-ig")
        assert revised["revision"] == 4
        assert http.get(f"/api/ideas/{idea['id']}").json()["changes"] == []
        assert http.post("/api/analyses/usd-ig/preview", json={"risk_adjustment": {"method": "beta", "reference_id": "missing"}}).status_code == 422
        pair = next(a for a in original["analyses"] if a["id"] == "ig-em-hy")
        pair["settings"]["measure"] = "change"
        pair["settings"]["risk_overrides"] = [{"method": "beta"}, {"method": "volatility"}]
        assert http.post("/api/library/analyses", json=pair).status_code == 422
    with client(tmp_path) as reopened:
        default = reopened.post("/api/analyses/usd-ig/preview", json={}).json()
        assert default["definition"]["settings"]["risk_adjustment"]["method"] == "volatility"
        saved = reopened.get(f"/api/ideas/{idea['id']}").json()["snapshots"][entry["id"]]
        assert saved["evaluation"] == evaluation
        latest = reopened.post(f"/api/ideas/{idea['id']}/charts/{entry['id']}/latest").json()["evaluation"]
        assert latest["definition"] == evaluation["definition"]
        assert latest["points"] == evaluation["points"]


def test_level_defaults_remain_backward_compatible_and_invalid_configuration_rejected():
    assert AnalysisSettings().measure == "level"
    with pytest.raises(ValueError, match="requires changes"):
        AnalysisSettings(risk_adjustment=RiskAdjustment(method="volatility"))
    with pytest.raises(ValueError):
        RiskAdjustment(confidence=100)
