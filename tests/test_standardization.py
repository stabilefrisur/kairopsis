from datetime import date, timedelta
from math import sqrt

import pytest
from pydantic import ValidationError

from kairopsis.analytics import evaluate
from kairopsis.evaluation_comparison import compare
from kairopsis.models import AnalysisDefinition, AnalysisSettings, DataRequest, DataResponse, Observation, ResolvedDefinition, SeriesResult
from test_rebuild_analytics import NOW, binding, evaluated
from test_rebuild_http import client, PNG


def calculation(dates, values, right, method, settings):
    inputs = (binding(), binding("b"))
    definition = ResolvedDefinition(id="example", revision=1, name="Example", calculation=method, inputs=inputs, settings=settings)
    data = DataResponse(mode="mock", requested=("a", "b"), attempted_at=NOW, completed_at=NOW, outcome="synthetic",
        series=tuple(SeriesResult(binding=b, provenance="Hand-worked example", observations=tuple(
            Observation(date=d, observed_on=d, value=v) for d, v in zip(dates, series))) for b, series in zip(inputs, (values, right))))
    return evaluate(definition, data, DataRequest(bindings=inputs, start=dates[0], end=dates[-1]), NOW)


@pytest.mark.parametrize("measure,values", [("change", [100, 101, 103, 106, 111]),
    ("return", [100, 101, 103.02, 106.1106, 111.41613])])
def test_standalone_zscore_uses_measured_changes_and_excludes_current(measure, values):
    result = evaluated(values, settings=AnalysisSettings(measure=measure, standardization="zscore", minimum_history=3))
    reference = result.standardization_estimate
    assert reference.mean == pytest.approx(2) and reference.standard_deviation == pytest.approx(1)
    assert reference.sample_count == 3 and reference.end < result.observation_date
    assert result.current == pytest.approx(3) and result.change == pytest.approx(3)
    assert result.unit == "σ" and result.condition_keys == ("upper",)
    assert result.points[-1].unstandardized_value == pytest.approx(5)
    assert result.points[-1].inputs == (values[-1],)


def test_difference_standardizes_the_gap_not_the_individual_legs():
    dates = [date(2026, 9, 21) + timedelta(days=i) for i in range(4)]
    result = calculation(dates, [90, 100, 110, 140], [48, 50, 52, 70], "difference",
        AnalysisSettings(standardization="zscore", minimum_history=3))
    assert result.standardization_estimate.mean == 50
    assert result.standardization_estimate.standard_deviation == 8
    assert result.current == 2.5  # z(A) - z(B) would be -6.
    assert [p.unstandardized_value for p in result.points] == [42, 50, 58, 70]
    assert result.percentile == 100 and result.condition_keys == ("upper",)
    shifted = calculation(dates, [90, 100, 110, 50], [48, 50, 52, 70], "difference", result.definition.settings)
    assert shifted.standardization_estimate == result.standardization_estimate
    assert shifted.current == -8.75 and shifted.condition_keys == ("lower",)


def test_carried_pair_observation_does_not_enter_the_common_reference():
    dates = [date(2026, 9, 21) + timedelta(days=i) for i in range(5)]
    original = calculation(dates, [90, 10000, 100, 110, 140], [48, 1, 50, 52, 70], "difference",
        AnalysisSettings(standardization="zscore", minimum_history=3))
    right = original.data.series[1]
    observations = list(right.observations)
    observations[1] = observations[1].model_copy(update={"observed_on": dates[0]})
    data = original.data.model_copy(update={"series": (original.data.series[0], right.model_copy(update={"observations": tuple(observations)}))})
    result = evaluate(original.definition, data, original.request, NOW)
    assert result.standardization_estimate.sample_count == 3
    assert result.standardization_estimate.mean == 50 and result.current == 2.5
    assert not result.points[1].eligible


def test_regression_residual_is_standardized_after_the_current_prior_only_fit():
    dates = [date(2026, 9, 21) + timedelta(days=i) for i in (0, 1, 2, 3, 4, 7)]
    xs = [-2, -1, 0, 1, 2, 0]
    ys = [10 + 2*x + noise for x, noise in zip(xs, [1, -2, 2, -2, 1, 5])]
    result = calculation(dates, ys, xs, "regression", AnalysisSettings(standardization="zscore", fit_years="all", minimum_fit=3, minimum_history=3))
    assert result.fit.slope == 2 and result.fit.intercept == 10
    assert result.points[-1].unstandardized_value == 5
    assert result.standardization_estimate.mean == 0
    assert result.standardization_estimate.standard_deviation == sqrt(3.5)
    assert result.current == pytest.approx(5 / sqrt(3.5))
    assert result.fit.end < result.observation_date


def test_constant_and_short_reference_are_explicitly_unavailable():
    dates = [date(2026, 9, 21) + timedelta(days=i) for i in range(4)]
    settings = AnalysisSettings(standardization="zscore", minimum_history=3)
    constant = calculation(dates, [10, 11, 12, 13], [0, 1, 2, 3], "difference", settings)
    assert constant.current is None and not constant.eligible and not constant.reasons
    assert any("standard deviation is zero" in text for text in constant.limitations)
    short = calculation(dates[:3], [10, 12, 15], [0, 1, 2], "difference", settings)
    assert short.current is None and any("2 prior common observations" in text for text in short.limitations)


@pytest.mark.parametrize("method,measure", [("ratio", "level"), ("ratio", "change"), ("level", "level")])
def test_unsupported_zscore_definitions_rejected(method, measure):
    with pytest.raises(ValidationError, match="Z-scores require"):
        AnalysisDefinition(name="Example", calculation=method, series_ids=("a",) if method == "level" else ("a", "b"),
            settings=AnalysisSettings(standardization="zscore", measure=measure))


def test_reference_roll_alone_is_quiet_but_a_native_gap_move_can_cross_threshold():
    dates = [date(2026, 6, 30), date(2026, 9, 25), date(2026, 9, 28), date(2026, 9, 29), date(2026, 9, 30)]
    settings = AnalysisSettings(standardization="zscore", history_years=.25, minimum_history=3, zscore_threshold=1)
    baseline = calculation(dates, [100, 0, 0, 0, 2], [0] * 5, "difference", settings)
    assert not baseline.conditions
    new_dates = [*dates, date(2026, 10, 1)]
    unchanged = calculation(new_dates, [100, 0, 0, 0, 2, 2], [0] * 6, "difference", settings)
    assert unchanged.current == 1.5 and unchanged.conditions
    assert compare(unchanged, baseline).finding == "quiet"
    moved = calculation(new_dates, [100, 0, 0, 0, 2, 100], [0] * 6, "difference", settings)
    result = compare(moved, baseline)
    assert result.finding == "new" and "prior Z-score reference held fixed" in result.reasons[-1]


def test_zscore_defaults_evidence_and_unstandardized_csv_survive_restart(tmp_path):
    options = {"standardization": "zscore", "measure": "change", "history_years": .5, "zscore_threshold": 2.5}
    with client(tmp_path) as http:
        before = http.get("/api/library").json()
        response = http.post("/api/analyses/usd-ig/preview", json=options)
        assert response.status_code == 200, response.text
        evaluation = response.json()
        assert evaluation["unit"] == "σ" and evaluation["current"] is not None
        assert http.get("/api/library").json() == before
        original = next(a for a in before["analyses"] if a["id"] == "usd-ig")
        assert http.post("/api/library/analyses", json={**original, "settings": {**original["settings"], **options}}).status_code == 200
        response = http.post("/api/ideas", json={"evaluation_id": evaluation["id"], "display": {"years": 1}, "image": PNG, "title": "Z-score evidence"})
        assert response.status_code == 200, response.text
        idea = response.json()
    with client(tmp_path) as http:
        definition = next(a for a in http.get("/api/library").json()["analyses"] if a["id"] == "usd-ig")
        saved = http.get(f"/api/ideas/{idea['id']}").json()["snapshots"][idea["charts"][0]["id"]]["evaluation"]
        assert definition["settings"]["standardization"] == "zscore" and definition["settings"]["zscore_threshold"] == 2.5
        assert saved["standardization_estimate"] == evaluation["standardization_estimate"]
        assert saved["points"] == evaluation["points"]
    csv = next((tmp_path / "workspace").rglob("data.csv")).read_text()
    assert "unstandardized_value,unstandardized_unit" in csv and "σ" in csv
