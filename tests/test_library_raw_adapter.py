from datetime import date, datetime, timezone
import json

import metapyle
import pandas as pd
import pytest

from kairopsis.config import Settings
from kairopsis.metapyle_adapter import MetapyleMarketData
from kairopsis.models import DataRequest, SeriesBinding


@pytest.mark.parametrize("source, field, column", [
    ("bloomberg", "PX_LAST", "EUR_TEST::PX_LAST"),
    ("gsquant", "spread::pricing", "EUR_TEST::spread::pricing"),
    ("macrobond", None, "EUR_TEST"),
    ("localfile", None, "EUR_TEST"),
])
def test_unsaved_binding_uses_raw_query_without_catalogue_or_cache_files(tmp_path, monkeypatch, source, field, column):
    settings = Settings(mode="live", workspace=tmp_path / "workspace", config_dir=tmp_path / "config",
        cache_dir=tmp_path / "cache", log_dir=tmp_path / "logs")
    calls = []

    class Client:
        def __init__(self, *, catalog, cache_enabled):
            assert catalog == [] and cache_enabled is False

        def get_raw(self, **kwargs):
            calls.append(kwargs)
            return pd.DataFrame({column: [10., 11.]},
                index=pd.to_datetime(["2026-09-29", "2026-09-30"]))

        def close(self):
            pass

    monkeypatch.setattr(metapyle, "Client", Client)
    binding = SeriesBinding(name="Unsaved", source=source, instrument="EUR_TEST", field=field,
        unit="bp", currency="EUR", params={"option": "value"})
    result = MetapyleMarketData(settings, lambda: datetime(2026, 9, 30, tzinfo=timezone.utc), ad_hoc=True).fetch(
        DataRequest(bindings=(binding,), start=date(2026, 9, 1), end=date(2026, 9, 30)))
    assert result.outcome == "unverified" and result.series[0].observations[-1].value == 11
    assert result.series[0].observations[-1].observed_on is None
    assert calls == [{"source": source, "symbol": "EUR_TEST", "field": field, "path": None,
        "params": {"option": "value"}, "start": "2026-09-01", "end": "2026-09-30", "use_cache": False}]
    assert not settings.workspace.exists() and not settings.cache_dir.exists()


@pytest.mark.parametrize("frame, code", [
    (pd.DataFrame({"OTHER": [999.]}, index=pd.to_datetime(["2026-09-30"])), "missing_field"),
    (pd.DataFrame({"EXAMPLE": [1., 2.]}, index=pd.to_datetime(["2026-09-30", "2026-09-30"])), "invalid_response"),
    (pd.DataFrame({"EXAMPLE": ["bad"]}, index=pd.to_datetime(["2026-09-30"])), "invalid_response"),
])
def test_raw_preview_never_substitutes_another_field_or_accepts_ambiguous_rows(tmp_path, monkeypatch, frame, code):
    class Client:
        def __init__(self, **kwargs): pass
        def get_raw(self, **kwargs): return frame
        def close(self): pass

    monkeypatch.setattr(metapyle, "Client", Client)
    binding = SeriesBinding(name="Draft", source="localfile", instrument="EXAMPLE", unit="bp", currency="EUR")
    settings = Settings(mode="live", workspace=tmp_path / "live", config_dir=tmp_path / "config",
        cache_dir=tmp_path / "cache", log_dir=tmp_path / "logs")
    result = MetapyleMarketData(settings, lambda: datetime(2026, 9, 30, tzinfo=timezone.utc), ad_hoc=True).fetch(
        DataRequest(bindings=(binding,), start=date(2026, 9, 1), end=date(2026, 9, 30)))
    assert result.outcome == "failed" and not result.series
    assert result.failures[0].code == code


def test_saved_legacy_alias_uses_mapping_but_new_and_edited_queries_use_draft_identifiers(tmp_path, monkeypatch):
    settings = Settings(mode="live", workspace=tmp_path / "live", config_dir=tmp_path / "config",
        cache_dir=tmp_path / "cache", log_dir=tmp_path / "logs")
    settings.config_dir.mkdir()
    saved = SeriesBinding(id="saved", name="Legacy", source="bloomberg", instrument="ALIAS", field="spread", unit="bp", currency="EUR")
    (settings.config_dir / "metapyle.json").write_text(json.dumps({"mappings": [{"source": "bloomberg",
        "instrument": "ALIAS", "field": "spread", "metapyle_source": "bloomberg", "symbol": "REAL_SYMBOL",
        "request_field": "PX_LAST", "value_column": "LEGACY_VALUE", "params": {"mapped": True}}]}))
    calls = []

    class Client:
        def __init__(self, **kwargs): pass
        def get_raw(self, source, symbol, start, end, **kwargs):
            calls.append((symbol, kwargs["params"]))
            column = "LEGACY_VALUE" if symbol == "REAL_SYMBOL" else f'{symbol}::{kwargs["field"]}'
            return pd.DataFrame({column: [42.]}, index=pd.to_datetime(["2026-09-30"]))
        def close(self): pass

    monkeypatch.setattr(metapyle, "Client", Client)
    provider = MetapyleMarketData(settings, lambda: datetime(2026, 9, 30, tzinfo=timezone.utc),
        ad_hoc=True, legacy_bindings=lambda: (saved,))
    drafts = (saved, saved.model_copy(update={"id": "new"}), saved.model_copy(update={"params": {"draft": True}}))
    result = provider.fetch(DataRequest(bindings=drafts, start=date(2026, 9, 1), end=date(2026, 9, 30)))
    assert len(result.series) == 3 and not result.failures
    assert calls == [("REAL_SYMBOL", {"mapped": True}), ("ALIAS", {}), ("ALIAS", {"draft": True})]
