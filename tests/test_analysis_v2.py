"""Observable v2 results and persisted definitions, beside unchanged v1 fixtures."""
from copy import deepcopy
from datetime import date, timedelta
from itertools import product
import json
from math import cos, sin, sqrt

import pytest

from kairopsis.analytics import evaluate
from kairopsis.catalogue import resolve_definition
from kairopsis.evaluation_comparison import compare
from kairopsis.models import AnalysisDefinition, AnalysisSettings, DataRequest, DataResponse, Observation, ResolvedDefinition, RiskAdjustment, SeriesResult
from kairopsis.risk import estimate, measured_moves
from test_rebuild_analytics import NOW, binding
from test_rebuild_http import PNG, client


def result(values, *, calculation="level", measure="level", method="none", basis=None,
           standardization="none", reference=None, units=None, horizon="day", lookback="all", overrides=(), weighting="equal"):
    days = []
    day = date(2026, 1, 1)
    while len(days) < max(map(len, values)):
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    bindings = tuple(binding(chr(97+i), (units or ["bp"] * len(values))[i]) for i in range(len(values)))
    count = 1 if calculation == "level" else 2
    risk = RiskAdjustment(method=method, reference_id=reference, estimation_measure=basis, minimum_samples=3, lookback_years=lookback, weighting=weighting)
    settings = AnalysisSettings(calculation_contract="input-pipeline-v2", measure=measure, horizon=horizon,
        standardization=standardization, minimum_history=3, minimum_fit=3, fit_years="all", risk_adjustment=risk, risk_overrides=overrides)
    definition = ResolvedDefinition(id="v2", revision=1, name="v2", calculation=calculation,
        inputs=bindings[:count], references=bindings[count:], settings=settings)
    data = DataResponse(mode="mock", requested=tuple(b.id for b in bindings), attempted_at=NOW, completed_at=NOW, outcome="synthetic",
        series=tuple(SeriesResult(binding=b, provenance="Hand-verifiable", observations=tuple(Observation(date=d, observed_on=d, value=v)
            for d, v in zip(days, supplied))) for b, supplied in zip(bindings, values)))
    return evaluate(definition, data, DataRequest(bindings=bindings, start=days[0], end=days[-1]), NOW)


MATRIX = list(product(("level", "difference", "ratio", "regression"), ("level", "change", "return"),
    ("none", "volatility", "beta", "var", "es"), ("none", "zscore")))


@pytest.mark.parametrize("calculation,measure,method,standardization", MATRIX)
def test_all_120_v2_combinations_evaluate_and_roundtrip(calculation, measure, method, standardization):
    values = [[150 + .15*i + 7*sin(i*.39) + .015*i*cos(i*.21) for i in range(140)],
        [100 + .18*i + 4*cos(i*.33) + .01*i*sin(i*.17) for i in range(140)]]
    actual = result(values[:1] if calculation == "level" else values, calculation=calculation, measure=measure,
        method=method, standardization=standardization, reference="a")
    assert actual.current is not None and actual.eligible, actual.limitations
    payload = AnalysisDefinition(id="v2", name="v2", calculation=calculation, series_ids=tuple(b.id for b in actual.definition.inputs), settings=actual.definition.settings)
    restored = AnalysisDefinition.model_validate_json(payload.model_dump_json())
    assert restored == payload
    assert resolve_definition(restored, {b.id: b for b in actual.definition.inputs}).settings == actual.definition.settings
    assert type(actual).model_validate_json(actual.model_dump_json()).points == actual.points


@pytest.mark.parametrize("calculation,values", [("level", [[1, 2, 3, 5]]), ("ratio", [[2, 4, 6, 10], [2, 2, 2, 2]])])
def test_level_and_level_ratio_zscore_hand_reference(calculation, values):
    actual = result(values, calculation=calculation, standardization="zscore")
    assert actual.current == 3
    assert actual.standardization_estimate.mean == 2
    assert actual.standardization_estimate.standard_deviation == 1
    assert actual.points[-1].unstandardized_value == 5


def test_ratio_of_changes_excludes_zero_denominator_and_retains_sign():
    actual = result([[10, 12, 15, 19, 29, 30], [10, 11, 11, 13, 14, 16]], calculation="ratio", measure="change", standardization="zscore")
    assert actual.points[2].value is None and not actual.points[2].eligible
    assert actual.standardization_estimate.sample_count == 3
    assert actual.points[-1].unstandardized_value == .5
    assert "Zero denominator" in " ".join(actual.limitations)
    signed = result([[10, 12, 15, 19, 29, 30], [10, 11, 11, 13, 14, 13]], calculation="ratio", measure="change")
    assert signed.current == -1


@pytest.mark.parametrize("method,basis", list(product(("volatility", "beta", "var", "es"), ("change", "return"))))
def test_level_keeps_numerator_and_prior_only_cutoff_for_each_estimator(method, basis):
    values = [100 + i*.2 + 5*sin(i*.6) for i in range(100)]
    actual = result([values], method=method, basis=basis, horizon="week")
    changed = result([[*values[:-1], values[-1] + 1000]], method=method, basis=basis, horizon="week")
    assert actual.current is not None
    assert actual.adjustment_estimates == changed.adjustment_estimates
    assert actual.points[-1].transformed_inputs[0] == pytest.approx(values[-1] / actual.adjustment_estimates[0].scale)
    assert actual.points[-1].period_start == (None,)
    assert actual.adjustment_estimates[0].end <= actual.adjustment_estimates[0].cutoff
    assert actual.adjustment_estimates[0].estimation_measure == basis


def test_reference_only_level_estimator_does_not_need_target_change_baseline():
    actual = result([[None]*19 + [450], [100 + i*.2 + 4*sin(i) for i in range(20)]], method="volatility", reference="b", lookback=1)
    assert actual.current is not None
    assert actual.adjustment_estimates[0].sample_count == 18
    assert actual.points[-1].inputs[0] == 450


@pytest.mark.parametrize("measure,basis,unit", [("level", "change", "risk units"), ("level", "return", "bp/%"),
    ("change", "return", "bp/%"), ("return", "change", "%/bp")])
def test_composite_units_and_percentage_point_scale(measure, basis, unit):
    values = [100 + i*.2 + 4*sin(i*.8) for i in range(30)]
    actual = result([values], method="volatility", measure=measure, basis=basis)
    assert actual.unit == unit
    moves = measured_moves({p.date: p for p in actual.data.series[0].observations}, "day", basis)
    cutoff = actual.adjustment_estimates[0].cutoff
    sample = [move.value for d, move in moves.items() if d <= cutoff]
    divisor = estimate(sample, [], [0.]*len(sample), actual.definition.settings.risk_adjustment)
    assert actual.adjustment_estimates[0].scale == pytest.approx(divisor)
    numerator = values[-1] if measure == "level" else values[-1]-values[-2] if measure == "change" else 100*(values[-1]/values[-2]-1)
    assert actual.current == pytest.approx(numerator/divisor)


@pytest.mark.parametrize("values,method,measure,basis,units,expected,unit", [
    ([[450]*5, [100,70,70,100,100]], "volatility", "level", "change", ["bp","bp"], 15, "risk units"),
    ([[450]*5, [100,95,95,99.75,100]], "volatility", "level", "return", ["bp","bp"], 90, "bp/%"),
    ([[430,430,430,430,450], [100,95,95,99.75,100]], "volatility", "change", "return", ["bp","bp"], 4, "bp/%"),
    ([[100,100,100,100,102], [100,90,90,100,100]], "volatility", "return", "change", ["bp","bp"], .2, "%/bp"),
    ([[450,405,405,445.5,450], [100,95,95,99.75,100]], "beta", "level", "return", ["bp","point"], 225, "bp"),
    ([[450,430,430,450,450], [100,90,90,100,100]], "beta", "level", "change", ["bp","point"], 225, "point"),
])
def test_six_specification_unit_examples(values, method, measure, basis, units, expected, unit):
    actual = result(values, method=method, measure=measure, basis=basis, units=units, reference="b", lookback=1)
    assert actual.current == pytest.approx(expected)
    assert actual.unit == unit


@pytest.mark.parametrize("method,weighting,basis", [(method, weighting, basis) for method, weighting in
    [("volatility","equal"),("volatility","exponential"),("beta","equal"),("var","equal"),("es","equal")]
    for basis in ["change", "return"]])
def test_v2_optimized_and_direct_estimates_agree(method, weighting, basis):
    a = [200 + i*.2 + 4*sin(i*.8) for i in range(100)]
    b = [100 + i*.1 + 3*cos(i*.7) for i in range(100)]
    fast = result([a,b], method=method, basis=basis, reference="b", weighting=weighting)
    direct = result([a,b], method=method, basis=basis, reference="b", weighting=weighting, lookback=1)
    assert fast.current == pytest.approx(direct.current)
    assert fast.adjustment_estimates[0].scale == pytest.approx(direct.adjustment_estimates[0].scale)
    assert fast.adjustment_estimates[0].sample_dates == direct.adjustment_estimates[0].sample_dates


def test_v2_unavailable_scales_sparse_stale_constant_fit_and_nonfinite_inputs():
    for method in ["volatility", "beta", "var", "es"]:
        constant = result([[100]*30], method=method)
        assert constant.current is None and "Risk scale unavailable" in " ".join(constant.limitations)
    sparse = result([[100,101,102,103]], method="volatility")
    assert sparse.current is None and "Insufficient estimation history" in " ".join(sparse.limitations)
    regression = result([[100+i for i in range(30)], [1]*30], calculation="regression")
    assert regression.current is None and "constant explanatory" in " ".join(regression.limitations)
    original = result([[100 + i*.2 + sin(i) for i in range(50)], [200 + i*.4 + cos(i) for i in range(50)]], method="volatility", reference="b", lookback=1)
    old_reference = original.data.series[1].model_copy(update={"observations": original.data.series[1].observations[:-10]})
    stale = evaluate(original.definition, original.data.model_copy(update={"series": (original.data.series[0], old_reference)}), original.request, NOW)
    assert stale.current is None and "stale" in " ".join(stale.limitations)
    nonfinite = result([[100,101,102,103,float("inf")]])
    assert nonfinite.current is None and not nonfinite.eligible


def test_beta_unit_cancellation_negative_beta_and_self_invariance():
    reference = [100 + i*.2 + 4*sin(i*.8) for i in range(30)]
    target = [500 - 2*x for x in reference]
    actual = result([target, reference], method="beta", reference="b", basis="change", units=["bp", "point"])
    assert actual.unit == "point" and actual.adjustment_estimates[0].scale == pytest.approx(-2)
    assert actual.current == pytest.approx(target[-1]/-2)
    self_beta = result([reference], method="beta", basis="return")
    assert self_beta.unit == "bp" and self_beta.current == pytest.approx(reference[-1])
    assert self_beta.adjustment_estimates[0].scale == pytest.approx(1)


def test_common_divisor_cancellation_and_mixed_dimensionless_difference():
    a = [100 + i*.2 + 4*sin(i*.8) for i in range(50)]
    b = [70 + i*.3 + 3*cos(i*.7) for i in range(50)]
    plain = result([a,b], calculation="ratio")
    scaled = result([a,b], calculation="ratio", method="volatility", reference="a")
    assert scaled.current == pytest.approx(plain.current) and scaled.unit == "×"
    overrides = (RiskAdjustment(method="volatility", minimum_samples=3, lookback_years="all"),
        RiskAdjustment(method="es", minimum_samples=3, lookback_years="all"))
    mixed = result([a,b], calculation="difference", overrides=overrides)
    assert mixed.current is not None and mixed.unit == "risk units"
    with pytest.raises(ValueError, match="matching units"):
        result([a,b], calculation="difference", overrides=(RiskAdjustment(method="none"), overrides[1]))


def test_follow_and_explicit_basis_survive_numerator_changes_and_override_roundtrip():
    values = [100 + i*.2 + 4*sin(i*.8) for i in range(40)]
    follow_level = result([values], method="volatility")
    follow_return = result([values], method="volatility", measure="return")
    explicit_level = result([values], method="volatility", basis="return")
    assert follow_level.adjustment_estimates[0].estimation_measure == "change"
    assert follow_return.adjustment_estimates[0].estimation_measure == explicit_level.adjustment_estimates[0].estimation_measure == "return"
    assert explicit_level.adjustment_estimates[0].scale == pytest.approx(follow_return.adjustment_estimates[0].scale)
    options = AnalysisSettings(calculation_contract="input-pipeline-v2", risk_overrides=(RiskAdjustment(method="volatility", estimation_measure="return"), RiskAdjustment(method="beta", estimation_measure="change")))
    assert AnalysisSettings.model_validate_json(options.model_dump_json()) == options


def test_legacy_default_and_contract_changes_are_incompatible():
    actual = result([[1,2,3,5]])
    legacy = actual.definition.model_copy(update={"settings": AnalysisSettings(minimum_history=3)})
    old = evaluate(legacy, actual.data, actual.request, NOW)
    assert old.current == actual.current and old.unit == actual.unit
    assert AnalysisSettings.model_validate({"measure": "level"}).calculation_contract == "input-pipeline-v1"
    assert compare(actual, old).finding == "incompatible"
    with pytest.raises(ValueError, match="calculation_contract"):
        AnalysisSettings(calculation_contract="future")


def test_v2_http_full_draft_preview_save_restart_snapshot_and_retained_latest(tmp_path):
    with client(tmp_path) as http:
        original = http.get("/api/library").json()
        draft = deepcopy(next(a for a in original["analyses"] if a["id"] == "usd-ig"))
        draft["settings"].update(calculation_contract="input-pipeline-v2", measure="level", horizon="week",
            standardization="zscore", risk_adjustment={"method": "volatility", "reference_id": "hy", "estimation_measure": "return", "lookback_years": 7})
        response = http.post("/api/library/analyses/preview", json={"analysis": draft, "period": .25})
        assert response.status_code == 200, response.text
        library = response.json()
        investigation = http.post("/api/analyses/usd-ig/preview", json={"analysis": draft}).json()
        assert investigation["current"] == pytest.approx(library["current"])
        assert investigation["definition"] == library["definition"]
        assert library["request"]["start"] <= "2014-08-26"
        assert library["standardization_estimate"]["unit"] == "bp/%"
        assert http.get("/api/library").json() == original
        idea = http.post("/api/ideas", json={"evaluation_id": investigation["id"], "image": PNG, "title": "v2", "display": {"view": "changes"}}).json()
        assert http.post("/api/library/analyses", json=draft).status_code == 200
        draft["settings"]["risk_adjustment"]["estimation_measure"] = "change"
        assert http.post("/api/library/analyses", json=draft).status_code == 200
    with client(tmp_path) as http:
        entry = idea["charts"][0]
        saved = http.get(f"/api/ideas/{idea['id']}").json()["snapshots"][entry["id"]]["evaluation"]
        assert saved == investigation
        latest = http.post(f"/api/ideas/{idea['id']}/charts/{entry['id']}/latest").json()["evaluation"]
        assert latest["definition"] == investigation["definition"] and latest["current"] == investigation["current"]
    csv = next((tmp_path/"workspace").rglob("data.csv")).read_text()
    assert "estimation_measure_1" in csv and "bp/%" in csv and "input-pipeline-v2" in csv


def test_old_files_without_new_fields_survive_restart_latest_and_export(tmp_path):
    with client(tmp_path) as http:
        evaluation = http.post("/api/analyses/eur-gbp/preview", json={}).json()
        idea = http.post("/api/ideas", json={"evaluation_id": evaluation["id"], "image": PNG, "title": "old", "display": {}}).json()
    folder = next((tmp_path/"workspace").rglob("snapshot.json")).parent
    paths = [folder/"snapshot.json", tmp_path/"workspace"/"evaluations"/(evaluation["id"]+".json")]
    for path in paths:
        payload = json.loads(path.read_text())
        saved = payload["evaluation"] if "evaluation" in payload else payload
        settings = saved["definition"]["settings"]
        settings.pop("calculation_contract")
        settings["risk_adjustment"].pop("estimation_measure")
        path.write_text(json.dumps(payload))
    original_files = {path: path.read_bytes() for path in [*paths, folder/"data.csv", folder/"image.png"]}
    with client(tmp_path) as http:
        entry = idea["charts"][0]
        saved = http.get(f"/api/ideas/{idea['id']}").json()["snapshots"][entry["id"]]["evaluation"]
        assert saved["definition"]["settings"]["calculation_contract"] == "input-pipeline-v1"
        assert saved["points"] == evaluation["points"] and saved["unit"] == evaluation["unit"]
        latest = http.post(f"/api/ideas/{idea['id']}/charts/{entry['id']}/latest").json()["evaluation"]
        assert latest["definition"] == saved["definition"] and latest["points"] == saved["points"]
        response = http.post(f"/api/ideas/{idea['id']}/charts/{entry['id']}/export", json={"evaluation_id": evaluation["id"], "image": PNG, "display": {}, "mode": "saved"})
        assert response.status_code == 200 and response.content
    assert all(path.read_bytes() == content for path, content in original_files.items())


def test_per_input_v2_basis_persists_independently_via_http(tmp_path):
    with client(tmp_path) as http:
        draft = deepcopy(next(a for a in http.get("/api/library").json()["analyses"] if a["id"] == "ig-em-hy"))
        draft["calculation"] = "regression"
        draft["settings"].update(calculation_contract="input-pipeline-v2", measure="level", fit_years=1,
            risk_overrides=[{"method": "volatility", "estimation_measure": "change"}, {"method": "beta", "estimation_measure": "return", "reference_id": "hy"}])
        response = http.post("/api/library/analyses", json=draft)
        assert response.status_code == 200, response.text
    with client(tmp_path) as http:
        actual = http.post("/api/analyses/ig-em-hy/preview", json={}).json()
        assert actual["current"] is not None
        assert [r["estimation_measure"] for r in actual["adjustment_estimates"]] == ["change", "return"]
        assert actual["input_units"] == ["risk units", "bp"]
