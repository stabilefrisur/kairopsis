from datetime import date, datetime, timedelta, timezone

from kairopsis.analytics import evaluate
from kairopsis.models import AnalysisSettings, DataRequest, DataResponse, Observation, ResolvedDefinition, SeriesBinding, SeriesResult


NOW = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)


def binding(identity="a", unit="bp"):
    return SeriesBinding(id=identity, name=identity, source="Synthetic", instrument=identity,
                         field="spread", unit=unit, currency="USD",
                         basis={"label": "Native USD", "currency": "USD", "reference_curve": "Treasury", "adjustment": "None"})


def evaluated(values, right=None, calculation="level", settings=None):
    inputs = (binding(),) if right is None else (binding(), binding("b"))
    definition = ResolvedDefinition(id="example", name="Example", revision=1, calculation=calculation,
                                    inputs=inputs, settings=settings or AnalysisSettings(minimum_history=3))
    dates = [date(2026, 9, 21) + timedelta(days=i) for i in range(len(values))]
    response = DataResponse(mode="mock", requested=tuple(x.id for x in inputs),
        attempted_at=NOW, completed_at=NOW, outcome="synthetic", series=tuple(
            SeriesResult(binding=series, provenance="Fabricated", observations=tuple(
                Observation(date=d, observed_on=d, value=v) for d, v in zip(dates, data)))
            for series, data in zip(inputs, [values, right] if right is not None else [values])))
    return evaluate(definition, response, DataRequest(bindings=inputs, start=dates[0], end=dates[-1]), NOW)


def test_current_is_excluded_from_midrank_reference_and_daily_move_uses_expected_session():
    result = evaluated([1, 2, 2, 3, 2])
    assert result.current == 2
    assert result.percentile == 50
    assert result.change == -1
    assert result.eligible


def test_zero_denominator_is_missing_and_difference_is_ordered():
    ratio = evaluated([10, 12, 14, 16], [2, 3, 7, 0], "ratio")
    assert [p.value for p in ratio.points] == [5, 4, 2, None]
    assert ratio.current is None and not ratio.eligible
    difference = evaluated([10, 12, 14, 16], [2, 3, 7, 4], "difference")
    assert difference.current == 12


def test_ols_excludes_current_and_reproduces_independent_linear_example():
    inputs = (binding(), binding("b", "%"))
    settings = AnalysisSettings(fit_years=1, minimum_history=3)
    definition = ResolvedDefinition(id="fit", name="Fit", revision=1, calculation="regression", inputs=inputs, settings=settings)
    dates = []
    d = date(2025, 9, 30)
    while d <= date(2026, 9, 30):
        if d.weekday() < 5:
            dates.append(d)
        d += timedelta(days=1)
    xs = [float(i % 19) for i in range(len(dates))]
    ys = [10 + 2*x for x in xs]
    ys[-1] += 8
    response = DataResponse(mode="mock", requested=("a", "b"), attempted_at=NOW, completed_at=NOW, outcome="synthetic",
        series=tuple(SeriesResult(binding=s, provenance="Hand-worked y = 10 + 2x", observations=tuple(
            Observation(date=d, value=v, observed_on=d) for d, v in zip(dates, values)))
            for s, values in zip(inputs, [ys, xs])))
    result = evaluate(definition, response, DataRequest(bindings=inputs, start=dates[0], end=dates[-1]), NOW)
    assert result.fit.slope == 2 and result.fit.intercept == 10
    assert result.fit.r_squared == 1 and result.current == 8
    assert result.fit.end < result.observation_date


def test_regression_new_threshold_uses_prior_fit_and_refit_alone_stays_quiet():
    from kairopsis.evaluation_comparison import compare
    inputs = (binding(), binding("b", "%"))
    definition = ResolvedDefinition(id="fit", name="Fit", revision=1, calculation="regression", inputs=inputs,
                                    settings=AnalysisSettings(fit_years=1, minimum_history=3))
    dates = [date(2025,9,30)+timedelta(days=i) for i in range(366) if (date(2025,9,30)+timedelta(days=i)).weekday()<5]
    def sample(residual):
        xs = [float(i % 19) for i in range(len(dates))]
        ys = [10+2*x for x in xs]
        ys[-1] += residual
        data = DataResponse(mode="mock", requested=("a","b"), attempted_at=NOW, completed_at=NOW, outcome="synthetic",
            series=tuple(SeriesResult(binding=s,provenance="Linear fixture",observations=tuple(Observation(date=d,observed_on=d,value=v)
                for d,v in zip(dates,values))) for s,values in zip(inputs,[ys,xs])))
        request = DataRequest(bindings=inputs,start=dates[0],end=dates[-1])
        return evaluate(definition,data,request,NOW)
    def advance(previous, bump):
        day = date(2026,10,1)
        series = tuple(s.model_copy(update={"observations": (*s.observations,Observation(date=day,observed_on=day,
            value=s.observations[-1].value+(bump if i==0 else 0)))}) for i,s in enumerate(previous.data.series))
        return evaluate(definition,previous.data.model_copy(update={"series":series}),previous.request.model_copy(update={"end":day}),NOW)
    quiet = sample(0)
    new = compare(advance(quiet,8),quiet)
    assert new.finding == "new" and "prior fit held fixed" in new.reasons[-1]
    extreme = sample(8)
    same = compare(advance(extreme,0),extreme)
    assert same.fit != extreme.fit
    assert same.finding == "unchanged" and not same.reasons
