from datetime import datetime, timezone
import os

from fastapi.testclient import TestClient

from kairopsis.app import create_app
from kairopsis.config import Settings


NOW = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)


def client(tmp_path, **kwargs):
    return TestClient(create_app(Settings(workspace=tmp_path / "workspace", config_dir=tmp_path / "config",
        cache_dir=tmp_path / "cache", log_dir=tmp_path / "logs"), clock=lambda: NOW, **kwargs))


def test_raw_series_can_be_previewed_without_saving_or_requiring_analysis_history(tmp_path):
    with client(tmp_path) as http:
        before = http.get("/api/library").json()
        draft = {**before["series"][0], "id": "unsaved-series", "name": "Unsaved EUR"}
        result = http.post("/api/library/series/preview", json={"series": draft, "period": .25})
        assert result.status_code == 200, result.text
        preview = result.json()
        assert preview["request"]["start"] == "2026-06-30"
        assert preview["data"]["series"][0]["binding"]["name"] == "Unsaved EUR"
        assert preview["data"]["series"][0]["observations"][-1]["date"] == "2026-09-30"
        assert http.get("/api/library").json() == before
        assert http.get("/api/ideas").json() == []


def test_analysis_preview_resolves_staged_inputs_and_risk_references_without_retaining_evaluation(tmp_path):
    with client(tmp_path) as http:
        before = http.get("/api/library").json()
        series = {s["id"]: s for s in before["series"]}
        draft = {**series["usd-ig"], "id": "new-input", "name": "Draft USD"}
        reference = {**series["em-sovereign-hy"], "id": "new-reference", "name": "Draft reference"}
        analysis = next(a for a in before["analyses"] if a["id"] == "ig-em-hy")
        analysis = {**analysis, "id": "new-analysis", "series_ids": [draft["id"], "em-sovereign-hy"],
            "settings": {**analysis["settings"], "history_years": 1, "standardization": "zscore",
                "risk_adjustment": {"method": "volatility", "reference_id": reference["id"], "lookback_years": 2}}}
        response = http.post("/api/library/analyses/preview", json={"analysis": analysis,
            "series_drafts": [draft, reference], "period": 20})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["definition"]["inputs"][0]["name"] == "Draft USD"
        assert result["definition"]["references"][0]["name"] == "Draft reference"
        assert result["definition"]["settings"]["history_years"] == 1
        assert result["request"]["start"] == "2004-08-26"
        assert result["points"] and result["standardization_estimate"]["sample_count"] > 0
        assert http.get(f'/api/evaluations/{result["id"]}').status_code == 404
        assert http.get("/api/library").json() == before
        assert http.get("/api/ideas").json() == []
        # Investigation previews remain retained for subsequent Idea capture.
        retained = http.post("/api/analyses/usd-ig/preview", json={}).json()
        assert http.get(f'/api/evaluations/{retained["id"]}').status_code == 200


def test_bundle_saves_retained_series_and_analysis_once_and_rejects_stale_updates(tmp_path):
    with client(tmp_path) as http:
        before = http.get("/api/library").json()
        analysis = next(a for a in before["analyses"] if a["id"] == "usd-ig")
        changed = next(s for s in before["series"] if s["id"] == "usd-ig")
        changed = {**changed, "name": "Renamed USD"}
        unused = {**changed, "id": "unused", "name": "Unused draft"}
        body = {"analysis": {**analysis, "name": "Saved together"}, "series_drafts": [changed, unused]}
        saved = http.post("/api/library/analyses/bundle", json=body)
        assert saved.status_code == 200, saved.text
        after = http.get("/api/library").json()
        assert saved.json()["analysis"]["revision"] == analysis["revision"] + 1
        assert [s["name"] for s in saved.json()["series"]] == ["Renamed USD"]
        assert not any(s["id"] == "unused" for s in after["series"])
        for old in before["analyses"]:
            new = next(a for a in after["analyses"] if a["id"] == old["id"])
            assert new["revision"] == old["revision"] + (1 if "usd-ig" in old["series_ids"] else 0)
        assert http.post("/api/library/analyses/bundle", json=body).status_code == 409
        assert http.get("/api/library").json() == after


def test_invalid_bundle_never_partially_saves_staged_series(tmp_path):
    with client(tmp_path) as http:
        before = http.get("/api/library").json()
        analysis = next(a for a in before["analyses"] if a["id"] == "mbs-ig")
        series = {s["id"]: s for s in before["series"]}
        invalid = {**series["usd-ig"], "unit": "%"}
        result = http.post("/api/library/analyses/bundle", json={"analysis": analysis, "series_drafts": [invalid]})
        assert result.status_code == 422
        assert http.get("/api/library").json() == before


def test_live_localfile_preview_ignores_save_only_name_and_changes_no_workspace_files(tmp_path):
    data = tmp_path / "sample.csv"
    data.write_text("date,EXAMPLE\n2026-09-29,10\n2026-09-30,11\n")
    settings = Settings(mode="live", workspace=tmp_path / "live", config_dir=tmp_path / "config",
        cache_dir=tmp_path / "cache", log_dir=tmp_path / "logs")
    with TestClient(create_app(settings, clock=lambda: NOW)) as http:
        before = {str(p): p.read_bytes() for p in settings.workspace.rglob("*") if p.is_file()}
        result = http.post("/api/library/series/preview", json={"series": {"name": "Draft", "source": "localfile",
            "instrument": "EXAMPLE", "path": str(data), "unit": "bp", "currency": "EUR", "catalog_name": "not valid yet"}, "period": .25})
        assert result.status_code == 200, result.text
        assert result.json()["data"]["series"][0]["observations"][-1]["value"] == 11
        assert {str(p): p.read_bytes() for p in settings.workspace.rglob("*") if p.is_file()} == before
        assert not settings.cache_dir.exists()


def test_bundle_publication_failure_restores_catalogue_projection(tmp_path, monkeypatch):
    with client(tmp_path) as http:
        before = http.get("/api/library").json()
        path = tmp_path / "workspace" / "metapyle.yaml"
        original_yaml = path.read_bytes()
        analysis = before["analyses"][0]
        series = before["series"][0]
        replace = os.replace

        def fail_catalogue(source, destination):
            if str(destination).endswith("catalogue.json"):
                raise OSError("test disk failure")
            replace(source, destination)

        monkeypatch.setattr(os, "replace", fail_catalogue)
        result = http.post("/api/library/analyses/bundle", json={"analysis": {**analysis, "name": "Not saved"},
            "series_drafts": [{**series, "name": "Not saved either"}]})
        assert result.status_code == 503
        assert http.get("/api/library").json() == before
        assert path.read_bytes() == original_yaml


def test_bundle_does_not_recreate_an_analysis_deleted_during_editing(tmp_path):
    with client(tmp_path) as http:
        analysis = http.get("/api/library").json()["analyses"][0]
        assert http.delete(f'/api/library/analyses/{analysis["id"]}').status_code == 200
        result = http.post("/api/library/analyses/bundle", json={"analysis": analysis,
            "base_revisions": {"analyses": {analysis["id"]: analysis["revision"]}}})
        assert result.status_code == 409
        assert not any(a["id"] == analysis["id"] for a in http.get("/api/library").json()["analyses"])
