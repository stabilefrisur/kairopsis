"""Catalogue management and retrieval through the public Metapyle API."""
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from metapyle.catalog import Catalog
import pytest

from kairopsis.app import create_app
from kairopsis.config import Settings
from kairopsis.metapyle_adapter import MetapyleMarketData
from kairopsis.models import DataRequest, SeriesBinding


NOW = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)


def settings(tmp_path):
    return Settings(mode="live", workspace=tmp_path / "workspace", config_dir=tmp_path / "config",
        cache_dir=tmp_path / "cache", log_dir=tmp_path / "logs")


def binding(tmp_path, **changes):
    return {"id": "test-series", "name": "Test spread", "catalog_name": "test_spread",
        "source": "localfile", "instrument": "SPREAD", "field": None,
        "path": str(tmp_path / "data.csv"), "params": {}, "unit": "bp", "currency": "USD",
        "basis": {"label": "USD / Treasury", "currency": "USD", "reference_curve": "Treasury", "adjustment": "None"},
        **changes}


def test_library_writes_edits_and_deletes_real_metapyle_catalogue(tmp_path):
    config = settings(tmp_path)
    app = create_app(config, clock=lambda: NOW)
    with TestClient(app) as http:
        first = binding(tmp_path, description="A provider series")
        assert http.post("/api/library/series", json=first).status_code == 200
        second = binding(tmp_path, id="second", catalog_name="second", source="localfile", instrument="SECOND_SPREAD",
            field=None, params={"date_column": "date"})
        assert http.post("/api/library/series", json=second).status_code == 200
        path = config.workspace / "metapyle.yaml"
        catalogue = Catalog.from_yaml(path)
        assert catalogue.list_names() == ["test_spread", "second"]
        assert catalogue.get("test_spread").symbol == "SPREAD"
        assert catalogue.get("test_spread").description == "A provider series"
        assert catalogue.get("second").params == second["params"]
        updated = {**first, "catalog_name": "renamed", "instrument": "NEW_SPREAD"}
        saved = http.post("/api/library/series", json=updated).json()
        assert saved["id"] == first["id"] and saved["revision"] == 2
        catalogue = Catalog.from_yaml(path)
        assert "test_spread" not in catalogue and catalogue.get("renamed").symbol == "NEW_SPREAD"
        assert http.delete("/api/library/series/test-series").status_code == 200
        catalogue = Catalog.from_yaml(path)
        assert catalogue.list_names() == ["second"] and catalogue.get("second").params == second["params"]
    with TestClient(create_app(config, clock=lambda: NOW)) as http:
        assert len(http.get("/api/library").json()["series"]) == 1
        assert Catalog.from_yaml(path).list_names() == ["second"]


@pytest.mark.parametrize("changes", [
    {"source": "bloomberg", "field": None, "path": None},
    {"source": "macrobond", "field": "PX_LAST", "path": None},
    {"path": None}, {"path": "relative.csv"}, {"source": "not-a-registered-source"},
    {"source": "bloomberg", "field": "", "path": None},
])
def test_invalid_provider_definitions_do_not_publish_partial_edits(tmp_path, changes):
    config = settings(tmp_path)
    with TestClient(create_app(config, clock=lambda: NOW)) as http:
        original = binding(tmp_path)
        assert http.post("/api/library/series", json=original).status_code == 200
        paths = [config.workspace / "catalogue.json", config.workspace / "metapyle.yaml"]
        before = [path.read_bytes() for path in paths]
        response = http.post("/api/library/series", json={**original, **changes})
        assert response.status_code == 422, response.text
        assert [path.read_bytes() for path in paths] == before


def test_unique_catalogue_names_and_dependency_delete_guard(tmp_path):
    config = settings(tmp_path)
    with TestClient(create_app(config, clock=lambda: NOW)) as http:
        first = binding(tmp_path)
        assert http.post("/api/library/series", json=first).status_code == 200
        assert http.post("/api/library/series", json={**first, "id": "another"}).status_code == 422
        analysis = {"id": "analysis", "name": "Investigate", "series_ids": [first["id"]]}
        assert http.post("/api/library/analyses", json=analysis).status_code == 200
        assert http.delete("/api/library/series/test-series").status_code == 422
        assert "test_spread" in Catalog.from_yaml(config.workspace / "metapyle.yaml")


def test_failed_metadata_write_rolls_back_yaml_and_startup_repairs_interrupted_projection(tmp_path, monkeypatch):
    config = settings(tmp_path)
    app = create_app(config, clock=lambda: NOW)
    with TestClient(app) as http:
        original = binding(tmp_path)
        assert http.post("/api/library/series", json=original).status_code == 200
        path = config.workspace / "metapyle.yaml"
        before = path.read_bytes()
        def fail(*args, **kwargs): raise OSError("simulated full disk")
        monkeypatch.setattr(app.state.repository, "write_json", fail)
        response = http.post("/api/library/series", json={**original, "instrument": "REPLACEMENT"})
        assert response.status_code == 503 and path.read_bytes() == before
        assert http.get("/api/library").json()["series"][0]["instrument"] == "SPREAD"
    path.write_text("[]\n")
    create_app(config, clock=lambda: NOW)
    assert path.read_bytes() == before


def test_get_by_catalogue_name_fetches_fresh_values_and_preserves_captured_binding(tmp_path):
    config = settings(tmp_path)
    original = binding(tmp_path)
    data = tmp_path / "data.csv"
    data.write_text("date,SPREAD,OTHER\n2026-10-01,100,200\n2026-10-02,101,202\n")
    with TestClient(create_app(config, clock=lambda: NOW)) as http:
        assert http.post("/api/library/series", json=original).status_code == 200
        definition = SeriesBinding.model_validate(http.get("/api/library").json()["series"][0])
        request = DataRequest(bindings=(definition,), start=date(2026, 10, 1), end=date(2026, 10, 2))
        provider = MetapyleMarketData(config, lambda: NOW)
        response = provider.fetch(request)
        assert response.outcome == "unverified" and not response.failures
        assert [point.value for point in response.series[0].observations] == [100, 101]
        assert all(point.observed_on is None for point in response.series[0].observations)
        assert "catalogue API" in response.series[0].provenance
        assert not config.config_dir.exists()  # No separate mapping file.
        data.write_text("date,SPREAD,OTHER\n2026-10-01,100,200\n2026-10-02,102,202\n")
        assert provider.fetch(request).series[0].observations[-1].value == 102
        assert http.post("/api/library/series", json={**original, "instrument": "OTHER"}).status_code == 200
        current = SeriesBinding.model_validate(http.get("/api/library").json()["series"][0])
        assert provider.fetch(request).series[0].observations[-1].value == 102
        current_request = DataRequest(bindings=(current,), start=request.start, end=request.end)
        assert provider.fetch(current_request).series[0].observations[-1].value == 202
        assert http.delete("/api/library/series/test-series").status_code == 200
        assert provider.fetch(request).series[0].observations[-1].value == 102


def test_missing_expected_column_never_substitutes_other_values(tmp_path, monkeypatch):
    import metapyle
    config = settings(tmp_path)
    with TestClient(create_app(config, clock=lambda: NOW)) as http:
        assert http.post("/api/library/series", json=binding(tmp_path)).status_code == 200
    import pandas as pd
    class Client:
        def __init__(self, catalog, *, cache_path=None, cache_enabled=True):
            assert str(catalog).endswith("metapyle.yaml") and not cache_enabled
        def get(self, names, start, end, *, use_cache):
            assert names == ["test_spread"] and use_cache is False
            return pd.DataFrame({"different_series": [999]}, index=pd.to_datetime(["2026-10-02"]))
        def close(self): pass
    monkeypatch.setattr(metapyle, "Client", Client)
    response = MetapyleMarketData(config, lambda: NOW).fetch(DataRequest(bindings=(SeriesBinding.model_validate(binding(tmp_path)),),
        start=date(2026, 10, 1), end=date(2026, 10, 2)))
    assert not response.series and response.failures[0].code == "missing_field"


def test_request_catalogue_is_frozen_before_client_initialization(tmp_path, monkeypatch):
    import metapyle
    from kairopsis.metapyle_catalogue import serialize_catalogue
    from kairopsis.repository import atomic_bytes

    config = settings(tmp_path)
    original = binding(tmp_path)
    (tmp_path / "data.csv").write_text("date,SPREAD,OTHER\n2026-10-01,100,200\n2026-10-02,101,202\n")
    with TestClient(create_app(config, clock=lambda: NOW)) as http:
        assert http.post("/api/library/series", json=original).status_code == 200
    actual_client = metapyle.Client
    managed = config.workspace / "metapyle.yaml"
    edited = serialize_catalogue((SeriesBinding.model_validate({**original, "instrument": "OTHER"}),))
    def racing_client(*, catalog, **options):
        # Simulate a Library edit between choosing YAML and Client loading it.
        atomic_bytes(managed, edited)
        assert catalog != managed
        return actual_client(catalog=catalog, **options)
    monkeypatch.setattr(metapyle, "Client", racing_client)
    response = MetapyleMarketData(config, lambda: NOW).fetch(DataRequest(
        bindings=(SeriesBinding.model_validate(original),), start=date(2026, 10, 1), end=date(2026, 10, 2)))
    assert not response.failures and response.series[0].observations[-1].value == 101
    assert Catalog.from_yaml(managed).get("test_spread").symbol == "OTHER"


def test_old_workspaces_and_snapshots_load_with_no_catalogue_fields(tmp_path):
    config = Settings(workspace=tmp_path / "mock")
    app = create_app(config, clock=lambda: NOW)
    with TestClient(app) as http:
        original = http.get("/api/library").json()["series"][0]
        for field in ("catalog_name", "path", "params", "description"):
            original.pop(field)
        parsed = SeriesBinding.model_validate(original)
        assert parsed.catalog_name is None
        assert http.post("/api/library/series", json=original).status_code == 200
        assert http.post("/api/analyses/eur-gbp/preview", json={}).status_code == 200
    assert Catalog.from_yaml(config.workspace / "metapyle.yaml").list_names() == []
