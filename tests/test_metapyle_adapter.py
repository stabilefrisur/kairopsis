from datetime import date, datetime, timezone
import json

import metapyle
import pandas as pd
import pytest

from kairopsis.config import Settings
from kairopsis.metapyle_adapter import MetapyleMarketData
from kairopsis.models import DataRequest
from kairopsis.fixtures import series_fixture


def configured(tmp_path, **mapping_changes):
    settings = Settings(mode="live", workspace=tmp_path / "live", config_dir=tmp_path / "config",
                        cache_dir=tmp_path / "cache", log_dir=tmp_path / "logs")
    settings.config_dir.mkdir()
    bindings = series_fixture()[:2]
    mappings = [{"source": leg.source, "instrument": leg.instrument, "field": leg.field,
                 "metapyle_source": "public-test-fixture", "symbol": leg.instrument,
                 "request_field": "SPREAD", "value_column": "SPREAD", **mapping_changes} for leg in bindings]
    (settings.config_dir / "metapyle.json").write_text(json.dumps({"schema_version": 1, "mappings": mappings}))
    return settings, bindings


def clock():
    return datetime(2026, 9, 27, 12, tzinfo=timezone.utc)


def test_fresh_request_bypasses_public_cache_without_inventing_freshness_or_native_dates(tmp_path, monkeypatch):
    settings, bindings = configured(tmp_path)
    calls = []
    class Client:
        def __init__(self, catalog, *, cache_path=None, cache_enabled=True):
            assert catalog == [] and cache_enabled is False
        def get_raw(self, source, symbol, start, end=None, *, field=None, path=None, params=None, use_cache=True):
            calls.append((source, symbol, start, end, field, use_cache))
            return pd.DataFrame({"SPREAD": [100., 101.]}, index=pd.to_datetime(["2026-09-24", "2026-09-25"]))
        def close(self):
            pass
    monkeypatch.setattr(metapyle, "Client", Client)
    request = DataRequest(bindings=bindings, start=date(2026, 9, 1), end=date(2026, 9, 27), freshness="require_fresh")
    result = MetapyleMarketData(settings, clock).fetch(request)
    assert result.mode == "live" and result.outcome == "unverified"
    assert result.requested == tuple(leg.id for leg in bindings)
    assert [item.observations[-1].value for item in result.series] == [101., 101.]
    assert all(point.observed_on is None for item in result.series for point in item.observations)
    assert all("freshness" in item.provenance.lower() and "unverified" in item.provenance.lower() for item in result.series)
    assert not result.failures
    assert all(call[-1] is False for call in calls)
    assert result.attempted_at == result.completed_at == clock()


def test_native_column_and_missing_field_are_independent_without_secret_leaks(tmp_path, monkeypatch):
    settings, bindings = configured(tmp_path, observed_on_column="ACTUAL", params_env={"token": "KAIROPSIS_TEST_TOKEN"})
    monkeypatch.setenv("KAIROPSIS_TEST_TOKEN", "private-test-secret")
    class Client:
        def __init__(self, *args, **kwargs): pass
        def get_raw(self, source, symbol, *args, **kwargs):
            assert kwargs["params"]["token"] == "private-test-secret"
            if symbol == bindings[1].instrument:
                return pd.DataFrame({"WRONG_FIELD": [999.]}, index=pd.to_datetime(["2026-09-25"]))
            return pd.DataFrame({"SPREAD": [100., 100., float("nan")], "ACTUAL": ["2026-09-23", "2026-09-23", None]},
                index=pd.to_datetime(["2026-09-23", "2026-09-24", "2026-09-25"]))
        def close(self): pass
    monkeypatch.setattr(metapyle, "Client", Client)
    result = MetapyleMarketData(settings, clock).fetch(DataRequest(bindings=bindings, start=date(2026, 9, 1), end=date(2026, 9, 27), freshness="require_fresh"))
    assert result.outcome == "partial" and len(result.series) == 1
    assert [item.observed_on for item in result.series[0].observations] == [date(2026,9,23), date(2026,9,23), None]
    assert result.series[0].observations[-1].value is None
    assert result.failures[0].binding_id == bindings[1].id and result.failures[0].code == "missing_field"
    assert "private-test-secret" not in result.model_dump_json()


def test_missing_configuration_and_public_api_failure_remain_explicit_live_failures(tmp_path, monkeypatch):
    settings, bindings = configured(tmp_path)
    request = DataRequest(bindings=bindings, start=date(2026,9,1), end=date(2026,9,27), freshness="require_fresh")
    configuration = settings.config_dir / "metapyle.json"
    original = configuration.read_bytes()
    configuration.unlink()
    result = MetapyleMarketData(settings, clock).fetch(request)
    assert result.mode == "live" and result.outcome == "failed" and not result.series
    assert len(result.failures) == 2 and all(item.code == "live_configuration" for item in result.failures)
    configuration.write_bytes(original)
    class Client:
        def __init__(self, *args, **kwargs):
            raise TypeError("private-token=do-not-persist unsupported custom client")
    monkeypatch.setattr(metapyle, "Client", Client)
    result = MetapyleMarketData(settings, clock).fetch(request)
    assert result.outcome == "failed" and len(result.failures) == 2
    assert all(item.code == "metapyle_unavailable" for item in result.failures)
    assert "do-not-persist" not in result.model_dump_json()


@pytest.mark.parametrize("frame, code", [
    (pd.DataFrame({"SPREAD": [1,2]}, index=pd.to_datetime(["2026-09-25", "2026-09-25"])), "invalid_response"),
    (pd.DataFrame({"SPREAD": [1]}, index=[0]), "invalid_response"),
    (pd.DataFrame({"SPREAD": [1]}, index=pd.to_datetime([None])), "invalid_response"),
    (pd.DataFrame({"SPREAD": ["not numeric"]}, index=pd.to_datetime(["2026-09-25"])), "invalid_response"),
    (pd.DataFrame({"SPREAD": [1]}, index=pd.to_datetime(["2025-01-01"])), "no_data"),
])
def test_ambiguous_or_missing_raw_observations_are_not_silently_normalized(tmp_path, monkeypatch, frame, code):
    settings, bindings = configured(tmp_path)
    class Client:
        def __init__(self, *args, **kwargs): pass
        def get_raw(self, *args, **kwargs): return frame
        def close(self): pass
    monkeypatch.setattr(metapyle, "Client", Client)
    result = MetapyleMarketData(settings, clock).fetch(DataRequest(bindings=bindings, start=date(2026,9,1), end=date(2026,9,27)))
    assert result.outcome == "failed" and not result.series
    assert len(result.failures) == 2 and all(item.code == code for item in result.failures)


def test_public_metapyle_localfile_bypasses_old_values_without_provenance_assumptions(tmp_path):
    data = tmp_path / "public-synthetic.csv"
    data.write_text("date,EXAMPLE\n2026-09-24,10\n2026-09-25,11\n")
    settings, bindings = configured(tmp_path, metapyle_source="localfile", symbol="EXAMPLE", request_field=None,
                                    path=str(data), value_column="EXAMPLE")
    request = DataRequest(bindings=bindings, start=date(2026,9,1), end=date(2026,9,27), freshness="require_fresh")
    first = MetapyleMarketData(settings, clock).fetch(request)
    assert first.outcome == "unverified" and first.series[0].observations[-1].value == 11
    data.write_text("date,EXAMPLE\n2026-09-24,10\n2026-09-25,12\n")
    second = MetapyleMarketData(settings, clock).fetch(request)
    assert second.outcome == "unverified" and second.series[0].observations[-1].value == 12
    assert second.series[0].observations[-1].observed_on is None


def test_source_exception_preserves_other_leg_and_never_exposes_private_exception_text(tmp_path, monkeypatch):
    settings, bindings = configured(tmp_path)
    class Client:
        def __init__(self, *args, **kwargs): pass
        def get_raw(self, source, symbol, *args, **kwargs):
            if symbol == bindings[1].instrument:
                raise RuntimeError("Credentials private-password at https://private.invalid/token")
            frame = pd.DataFrame({"SPREAD": [42.]}, index=pd.to_datetime(["2026-09-25"]))
            frame.attrs["fresh"] = True  # Unspecified attrs are not an upstream freshness contract.
            return frame
        def close(self): pass
    monkeypatch.setattr(metapyle, "Client", Client)
    result = MetapyleMarketData(settings, clock).fetch(DataRequest(bindings=bindings, start=date(2026,9,1), end=date(2026,9,27)))
    assert result.outcome == "partial" and result.series[0].observations[-1].value == 42
    assert result.failures[0].code == "source_error"
    assert "private-password" not in result.model_dump_json() and "private.invalid" not in result.model_dump_json()


def test_invalid_or_absent_actual_date_metadata_stays_unknown_and_chart_readable(tmp_path, monkeypatch):
    settings, bindings = configured(tmp_path, observed_on_column="ACTUAL")
    class Client:
        def __init__(self, *args, **kwargs): pass
        def get_raw(self, source, symbol, *args, **kwargs):
            values = {"SPREAD": [40., 41.]}
            if symbol == bindings[0].instrument:
                values["ACTUAL"] = ["NaT", "not-a-date"]
            return pd.DataFrame(values, index=pd.to_datetime(["2026-09-24", "2026-09-25"]))
        def close(self): pass
    monkeypatch.setattr(metapyle, "Client", Client)
    result = MetapyleMarketData(settings, clock).fetch(DataRequest(bindings=bindings, start=date(2026,9,1), end=date(2026,9,27)))
    assert result.outcome == "unverified" and len(result.series) == 2
    assert all(point.observed_on is None for series in result.series for point in series.observations)
    assert all(series.observations[-1].value == 41 for series in result.series)
    assert "2 of 2" in result.series[0].provenance
    assert "column was absent" in result.series[1].provenance


def test_timezone_aware_rows_and_native_metadata_keep_the_supplied_calendar_day(tmp_path, monkeypatch):
    settings, bindings = configured(tmp_path, observed_on_column="ACTUAL")
    class Client:
        def __init__(self, *args, **kwargs): pass
        def get_raw(self, *args, **kwargs):
            return pd.DataFrame({"SPREAD": [10.], "ACTUAL": ["2026-09-25T00:30:00+14:00"]},
                                index=pd.to_datetime(["2026-09-25T00:30:00+14:00"]))
        def close(self): pass
    monkeypatch.setattr(metapyle, "Client", Client)
    result = MetapyleMarketData(settings, clock).fetch(DataRequest(bindings=bindings, start=date(2026,9,25), end=date(2026,9,25)))
    assert result.outcome == "unverified"
    assert all(item.observations[0].date == item.observations[0].observed_on == date(2026,9,25) for item in result.series)
