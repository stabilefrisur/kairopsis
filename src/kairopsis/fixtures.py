"""Representative deterministic native observations, explicitly fabricated."""
from datetime import date, datetime, timedelta
from math import sin
from typing import Literal, cast

from .models import AnalysisDefinition, AnalysisSettings, ComparisonBasis, DataFailure, DataRequest, DataResponse, Observation, SeriesBinding, SeriesResult

MOCK_AS_OF = date(2026, 9, 30)


def series_fixture() -> tuple[SeriesBinding, ...]:
    specs = [("eur-ig", "EUR investment grade", "Synthetic demo", "EUR", "Bund", "bp"),
             ("gbp-ig", "GBP investment grade", "Synthetic demo", "GBP", "Gilt", "bp"),
             ("usd-ig", "USD investment grade", "Synthetic demo", "USD", "Treasury", "bp"),
             ("hy", "USD high yield", "Synthetic demo", "USD", "Treasury", "bp"),
             ("em-sovereign-hy", "EM sovereign high yield", "Synthetic demo", "USD", "Treasury", "bp"),
             ("mbs", "Agency MBS", "Synthetic demo", "USD", "Treasury", "bp"),
             ("rates", "Treasury yield", "Synthetic demo", "USD", "Treasury", "%")]
    return tuple(SeriesBinding(id=i, name=n, source=s, instrument=i, field="yield" if unit == "%" else "spread",
        unit=unit, currency=c, basis=ComparisonBasis(label=f"Native {c} / {curve}", currency=c,
            reference_curve=curve, adjustment="None; fabricated native-market observations"))
        for i, n, s, c, curve, unit in specs)


def analysis_fixture() -> tuple[AnalysisDefinition, ...]:
    return tuple(AnalysisDefinition(id=i, name=n, calculation=cast(Literal["level", "difference", "ratio", "regression"], method), series_ids=inputs, monitored=monitor,
        settings=AnalysisSettings(horizon="week", measure="change" if i == "ig-em-hy" else "level", move_threshold=threshold, material_change=material))
        for i, n, method, inputs, monitor, threshold, material in [
            ("eur-gbp", "EUR IG / GBP IG", "ratio", ("eur-ig", "gbp-ig"), True, .1, .02),
            ("high-yield", "USD high yield", "level", ("hy",), True, 20., 5.),
            ("mbs-ig", "Agency MBS − IG", "difference", ("mbs", "usd-ig"), True, 8., 3.),
            ("ig-rates", "IG spread vs Treasury yield", "regression", ("usd-ig", "rates"), True, 8., 3.),
            ("usd-ig", "USD investment grade", "level", ("usd-ig",), False, 15., 3.),
            ("ig-em-hy", "US IG / EM sovereign HY", "difference", ("usd-ig", "em-sovereign-hy"), False, None, None)])


def native_value(key: str, day: date) -> float:
    t = (day - date(2020, 1, 1)).days
    wave = sin(t / 71) + .4 * sin(t / 23)
    recent = max(0., min(1., (day - date(2026, 9, 10)).days / 20))
    values = {"eur-ig": 100 + 12 * wave + 30 * recent,
              "gbp-ig": 105 + 10 * sin(t / 85),
              "rates": 3.7 + .7 * wave,
              "usd-ig": 90 + 15 * wave + 6 * sin(t / 15),
              "hy": 370 + 28 * wave + 85 * recent,
              "mbs": 117 + 15 * wave + 6 * sin(t / 15) + 20 * recent}
    values["em-sovereign-hy"] = 470 + 3.6 * (values["usd-ig"] - 90) + 20 * sin(t/4.3) + 38 * sin(t/53)
    return round(values[key], 6)


class MockMarketData:
    def __init__(self, clock):
        self.clock = clock

    def fetch(self, request: DataRequest) -> DataResponse:
        series = []
        failures = []
        allowed = {(s.source, s.instrument, s.field) for s in series_fixture()}
        for binding in request.bindings:
            if (binding.source, binding.instrument, binding.field) not in allowed:
                failures.append(DataFailure(binding_id=binding.id, code="unresolved_binding", message="No deterministic fixture for this source/instrument/field"))
                continue
            observations = []
            day = request.start
            while day <= min(request.end, MOCK_AS_OF):
                if day.weekday() < 5:
                    observations.append(Observation(date=day, observed_on=day, value=native_value(binding.instrument, day)))
                day += timedelta(days=1)
            series.append(SeriesResult(binding=binding, observations=tuple(observations), provenance="Fabricated native-market fixture; no live provider data"))
        return DataResponse(mode="mock", requested=tuple(b.id for b in request.bindings), series=tuple(series),
            failures=tuple(failures), attempted_at=self.clock(), completed_at=self.clock(),
            outcome="partial" if failures else "synthetic")
