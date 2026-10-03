from datetime import date, timedelta

from kairopsis.analytics import evaluate
from kairopsis.evaluation_comparison import compare
from kairopsis.models import AnalysisSettings, DataFailure, DataRequest, DataResponse, Observation, ResolvedDefinition, SeriesResult
from kairopsis.fixtures import MockMarketData
from test_rebuild_analytics import binding, NOW
from test_rebuild_http import client


def example(values, as_of=None, carried=False, settings=None):
    dates = [date(2026, 9, 21) + timedelta(days=i) for i in range(10)
             if (date(2026, 9, 21) + timedelta(days=i)).weekday() < 5][:len(values)]
    series = binding()
    definition = ResolvedDefinition(id="example", name="Example", revision=1, calculation="level", inputs=(series,),
        settings=settings or AnalysisSettings(minimum_history=3, upper_percentile=80, material_change=2))
    response = DataResponse(mode="mock", requested=(series.id,), attempted_at=NOW, completed_at=NOW, outcome="synthetic",
        series=(SeriesResult(binding=series, provenance="Hand-worked", observations=tuple(Observation(date=d, value=v,
            observed_on=d-timedelta(days=1) if carried and d==dates[-1] else d) for d,v in zip(dates, values))),))
    request = DataRequest(bindings=(series,), start=dates[0], end=as_of or dates[-1])
    return evaluate(definition, response, request, NOW)


def test_new_unchanged_material_moves_and_corrections_have_honest_reasons():
    baseline = example([1, 2, 3, 2])
    assert baseline.finding == "quiet"
    new = compare(example([1, 2, 3, 2, 10]), baseline)
    assert new.finding == "new" and "Entered" in new.reasons[0]
    unchanged = compare(example([1, 2, 3, 2, 10, 10]), new)
    assert unchanged.finding == "unchanged" and not unchanged.reasons
    later_unchanged = compare(example([1, 2, 3, 2, 10, 10, 10]), unchanged)
    assert later_unchanged.finding == "unchanged" and not later_unchanged.reasons
    changed = compare(example([1, 2, 3, 2, 10, 15]), new)
    assert changed.finding == "changed" and "+5.00 bp" in changed.reasons[0]
    corrected = compare(example([1, 2, 9, 2, 10, 15]), new)
    assert corrected.finding == "correction" and not corrected.reasons
    assert "corrected" in corrected.limitations[-1]
    reset = compare(example([1, 2, 3, 2, 10], settings=AnalysisSettings(minimum_history=3, upper_percentile=90)), baseline)
    assert reset.finding == "incompatible" and not reset.reasons


def test_first_condition_insufficient_stale_and_carried_observations():
    assert compare(example([1, 2, 3, 10]), None).finding == "condition"
    assert not example([1, 2, 10]).eligible
    stale = example([1, 2, 3, 10], as_of=date(2026, 9, 30))
    assert not stale.eligible and any("Stale" in x for x in stale.limitations)
    carried = example([1, 2, 3, 10], carried=True)
    assert not carried.eligible and not carried.conditions


def test_new_move_trigger_is_found_even_when_a_level_extreme_already_exists():
    settings = AnalysisSettings(minimum_history=3, upper_percentile=80, move_threshold=4, material_change=99)
    previous = example([1, 2, 3, 9, 10], settings=settings)
    current = compare(example([1, 2, 3, 9, 10, 15], settings=settings), previous)
    assert current.finding == "new" and len(current.conditions) == 2


def test_partial_refresh_retains_dated_result_and_suppresses_fresh_findings(tmp_path):
    class PartialProvider:
        failed = False
        def fetch(self, request):
            result = MockMarketData(lambda: NOW).fetch(request)
            if self.failed and any(s.id == "hy" for s in request.bindings):
                return result.model_copy(update={"series": (), "outcome": "failed", "failures": (
                    DataFailure(binding_id="hy", code="offline", message="Synthetic failure"),)})
            return result
    provider = PartialProvider()
    with client(tmp_path, provider) as http:
        initial = http.post("/api/refresh").json()
        old_id = initial["results"]["high-yield"]
        old = http.get(f"/api/evaluations/{old_id}").json()
        provider.failed = True
        failure = http.post("/api/refresh").json()
        assert failure["results"]["high-yield"] == old_id
        assert "high-yield" in failure["failures"]
        rows = http.get("/api/analyses?scope=all").json()["rows"]
        retained = next(r for r in rows if r["analysis"]["id"] == "high-yield")
        assert retained["evaluation"]["observation_date"] == old["observation_date"]
        assert not retained["flagged"] and retained["failure"]
        assert http.get("/api/analyses?scope=flagged").json()["rows"] == []
