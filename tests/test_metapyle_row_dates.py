"""Retrieval success and observation age are independent parts of eligibility."""
from datetime import date, datetime, timezone

import metapyle
import pandas as pd
import pytest

from kairopsis.analytics import evaluate
from kairopsis.config import Settings
from kairopsis.metapyle_adapter import MetapyleMarketData, _observations
from kairopsis.models import AnalysisSettings, DataRequest, ResolvedDefinition, SeriesBinding


NOW = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
DAYS = pd.to_datetime(["2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25"])


def settings(tmp_path):
    return Settings(mode="live", workspace=tmp_path / "live", config_dir=tmp_path / "config",
        cache_dir=tmp_path / "cache", log_dir=tmp_path / "logs")


def binding(identity="test"):
    return SeriesBinding(id=identity, name=identity, source="macrobond", instrument=identity,
        catalog_name=identity, unit="bp", currency="USD")


@pytest.mark.parametrize("ad_hoc", [False, True])
@pytest.mark.parametrize("state", ["current", "stale", "missing"])
def test_market_row_dates_enable_findings_but_never_disguise_old_or_missing_data(tmp_path, monkeypatch, ad_hoc, state):
    class Client:
        def __init__(self, *, catalog, cache_enabled, **kwargs):
            assert cache_enabled is False

        def get(self, names, start, end, *, use_cache, frequency=None, unified=False):
            assert use_cache is False and frequency is None and unified is False
            return pd.DataFrame({names[0]: [10., 11., 12., 13., float("nan") if state == "missing" else 20.]}, index=DAYS)

        def get_raw(self, *, source, symbol, start, end, **kwargs):
            assert kwargs["use_cache"] is False and "frequency" not in kwargs
            return self.get([symbol], start, end, use_cache=False)

        def close(self):
            pass

    monkeypatch.setattr(metapyle, "Client", Client)
    series = binding()
    request = DataRequest(bindings=(series,), start=date(2026, 9, 21),
        end=date(2026, 9, 28) if state == "stale" else date(2026, 9, 25))
    data = MetapyleMarketData(settings(tmp_path), lambda: NOW, ad_hoc=ad_hoc).fetch(request)
    assert data.outcome == "fresh" and not data.failures
    assert all(point.observed_on == point.date if point.value is not None else point.observed_on is None
        for point in data.series[0].observations)
    assert "Unaligned Metapyle row dates" in data.series[0].provenance
    result = evaluate(ResolvedDefinition(id="analysis", name="Analysis", revision=1, calculation="level",
        inputs=(series,), settings=AnalysisSettings(minimum_history=3, history_years="all")), data, request, NOW)
    if state == "current":
        assert result.eligible and result.finding == "condition"
        assert (result.current, result.change, result.percentile) == (20., 7., 100.)
        assert result.input_dates == (date(2026, 9, 25),)
    else:
        assert not result.eligible and result.finding == "unavailable" and not result.conditions
        assert any(("Stale observations" if state == "stale" else "missing input") in reason for reason in result.limitations)


@pytest.mark.parametrize("failure", ["one", "all", "close"])
def test_catalogue_errors_keep_partial_or_failed_outcomes(tmp_path, monkeypatch, failure):
    class Client:
        def __init__(self, **kwargs): pass
        def get(self, names, *args, **kwargs):
            if failure == "all" or failure == "one" and names == ["second"]:
                raise RuntimeError("private-provider-detail")
            return pd.DataFrame({names[0]: [10., 11., 12., 13., 20.]}, index=DAYS)
        def close(self):
            if failure == "close":
                raise RuntimeError("private-close-detail")

    monkeypatch.setattr(metapyle, "Client", Client)
    data = MetapyleMarketData(settings(tmp_path), lambda: NOW).fetch(DataRequest(
        bindings=(binding(), binding("second")), start=date(2026, 9, 21), end=date(2026, 9, 25)))
    assert data.outcome == ("failed" if failure == "all" else "partial")
    assert len(data.failures) == (1 if failure == "one" else 2)
    assert "private-" not in data.model_dump_json()


@pytest.mark.parametrize("include_column", [False, True])
def test_explicit_dates_override_row_dates_including_carried_missing_and_invalid_dates(include_column):
    values = {"value": [10., 10., 12., 13., 20.]}
    if include_column:
        values["actual"] = ["2026-09-21", "2026-09-21", None, "invalid", "2026-09-25"]
    request = DataRequest(bindings=(binding(),), start=date(2026, 9, 21), end=date(2026, 9, 25))
    points = _observations(pd.DataFrame(values, index=DAYS), "value", request, "actual", row_date_is_observation=True)
    expected = [date(2026, 9, 21), date(2026, 9, 21), None, None, date(2026, 9, 25)] if include_column else [None] * 5
    assert [point.observed_on for point in points] == expected


def test_empty_request_is_not_a_successful_retrieval(tmp_path, monkeypatch):
    class Client:
        def __init__(self, **kwargs): pass
        def close(self): pass
    monkeypatch.setattr(metapyle, "Client", Client)
    data = MetapyleMarketData(settings(tmp_path), lambda: NOW).fetch(
        DataRequest(bindings=(), start=date(2026, 9, 21), end=date(2026, 9, 25)))
    assert data.outcome == "unverified" and not data.series


@pytest.mark.parametrize("ad_hoc", [False, True])
def test_real_metapyle_client_preserves_sparse_rows_without_alignment(tmp_path, monkeypatch, ad_hoc):
    from metapyle.sources.macrobond import MacrobondSource

    def fetch(self, requests, start, end, **kwargs):
        assert not kwargs.get("unified")
        assert len(requests) == 1
        # Deliberately missing a weekday: the client must not fill the gap.
        return pd.DataFrame({requests[0].symbol: [10., 12., 13., 20.]}, index=DAYS.delete(1))

    monkeypatch.setattr(MacrobondSource, "fetch", fetch)
    data = MetapyleMarketData(settings(tmp_path), lambda: NOW, ad_hoc=ad_hoc).fetch(
        DataRequest(bindings=(binding(),), start=date(2026, 9, 21), end=date(2026, 9, 25)))
    assert data.outcome == "fresh" and not data.failures
    assert [(p.date, p.observed_on, p.value) for p in data.series[0].observations] == [
        (day.date(), day.date(), value) for day, value in zip(DAYS.delete(1), [10., 12., 13., 20.])]
