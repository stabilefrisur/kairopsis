from datetime import datetime, timezone
import base64
import os
import struct
import zlib
import shutil
import re
from urllib.parse import parse_qs, urlsplit
import pytest

from fastapi.testclient import TestClient

from kairopsis.app import create_app
from kairopsis.config import Settings


NOW = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)


def test_pages_version_local_ui_assets_and_keep_urls_stable_until_update(tmp_path):
    def assets(html):
        return re.findall(r'(?:src|href)="(/static/(?:research\.(?:js|css)|charts\.js|icon\.svg)[^"]*)"', html)
    with client(tmp_path) as http:
        urls = assets(http.get("/analyses").text)
        assert len(urls) == 4
        for url in urls:
            assert parse_qs(urlsplit(url).query).get("v"), url
            assert http.get(url).status_code == 200
        assert assets(http.get("/library").text) == urls


def client(tmp_path, provider=None):
    return TestClient(create_app(Settings(workspace=tmp_path / "workspace", config_dir=tmp_path / "config",
        cache_dir=tmp_path / "cache", log_dir=tmp_path / "logs"), market_data=provider, clock=lambda: NOW))


def test_search_finds_unmonitored_analysis_and_preview_does_not_mutate_library(tmp_path):
    with client(tmp_path) as http:
        http.post("/api/refresh")
        rows = http.get("/api/analyses", params={"q": "USD investment grade", "scope": "all"}).json()["rows"]
        assert any(r["analysis"]["id"] == "usd-ig" and not r["analysis"]["monitored"] for r in rows)
        original = http.get("/api/library").json()
        preview = http.post("/api/analyses/usd-ig/preview", json={"history_years": 1, "horizon": "month"}).json()
        assert preview["definition"]["settings"]["history_years"] == 1
        assert http.get("/api/library").json() == original
        assert http.get("/analyses/usd-ig").status_code == 200
        assert http.get("/catch-up").status_code == 404


def png_fixture():
    def chunk(kind, data):
        content = kind + data
        return struct.pack(">I", len(data)) + content + struct.pack(">I", zlib.crc32(content))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"\0\xff\xff\xff")) + chunk(b"IEND", b"")


PNG = "data:image/png;base64," + base64.b64encode(png_fixture()).decode()


def capture(http, idea_id=None, title="An unfinished question", note=""):
    evaluation = http.post("/api/analyses/usd-ig/preview", json={"history_years": 1}).json()
    body = {"evaluation_id": evaluation["id"], "display": {"years": 3, "view": "analysis"},
            "image": PNG, "idea_id": idea_id, "title": title, "note": note}
    response = http.post("/api/ideas", json=body)
    assert response.status_code == 200, response.text
    return response.json(), evaluation


def test_restart_notes_duplicate_charts_archive_and_catalogue_deletion_preserve_evidence(tmp_path):
    with client(tmp_path) as http:
        first, evaluation = capture(http)
        idea_id = first["id"]
        second, _ = capture(http, idea_id=idea_id, note="Chart-specific comment")
        assert len(second["charts"]) == 2
        assert [c["note"] for c in second["charts"]] == ["", "Chart-specific comment"]
        saved = http.get(f"/api/ideas/{idea_id}").json()["snapshots"]
        first_entry, second_entry = second["charts"]
        for text in ("First note", "Second note"):
            response = http.post(f"/api/ideas/{idea_id}/notes", json={"text": text})
            assert response.status_code == 200
        notes = response.json()["notes"]
        edited = http.patch(f"/api/ideas/{idea_id}/notes/{notes[0]['id']}", json={"text": "Edited note"}).json()
        assert edited["notes"][0]["created_at"] == notes[0]["created_at"]
        assert edited["notes"][0]["modified_at"] is not None
        http.delete(f"/api/ideas/{idea_id}/notes/{notes[1]['id']}")
        http.patch(f"/api/ideas/{idea_id}", json={"shortlisted": True, "archived": True})
        assert http.get("/api/ideas?scope=shortlist").json() == []
        assert http.get("/api/ideas?scope=archived&q=unfinished").json()[0]["idea"]["shortlisted"]
        http.patch(f"/api/ideas/{idea_id}", json={"archived": False})
        assert len(http.get("/api/ideas?scope=shortlist").json()) == 1
        dependency = http.delete("/api/library/series/usd-ig")
        assert dependency.status_code == 422 and "Used by" in dependency.text
        http.delete("/api/library/analyses/usd-ig")
        assert http.post(f"/api/ideas/{idea_id}/charts/{first_entry['id']}/latest").json()["evaluation"]["definition"] == evaluation["definition"]
        for entry in second["charts"]:
            http.delete(f"/api/ideas/{idea_id}/charts/{entry['id']}")
    with client(tmp_path) as reopened:
        result = reopened.get(f"/api/ideas/{idea_id}").json()
        assert result["idea"]["charts"] == [] and result["idea"]["shortlisted"]
        assert result["idea"]["notes"][0]["text"] == "Edited note"
        for snapshot in saved.values():
            response = reopened.get(f"/api/ideas/{idea_id}/snapshots/{snapshot['id']}/image")
            assert response.status_code == 200 and response.content == base64.b64decode(PNG.split(',')[1])


def test_export_records_exact_evidence_and_write_failure_is_actionable(tmp_path, monkeypatch):
    with client(tmp_path) as http:
        idea, evaluation = capture(http)
        entry = idea["charts"][0]
        saved = http.get(f"/api/ideas/{idea['id']}").json()["snapshots"][entry["id"]]
        body = {"evaluation_id": evaluation["id"], "display": saved["display"], "image": PNG, "mode": "saved"}
        path = f"/api/ideas/{idea['id']}/charts/{entry['id']}/export"
        response = http.post(path, json=body)
        assert response.status_code == 200 and response.headers["X-Snapshot-ID"] != saved["id"]
        snapshot_id = response.headers["X-Snapshot-ID"]
        assert http.get(f"/api/ideas/{idea['id']}/snapshots/{snapshot_id}/image").content == response.content
        replace = os.replace
        def failure(source, target):
            if target.name == "snapshot.json":
                raise OSError("Injected capture failure")
            replace(source, target)
        monkeypatch.setattr(os, "replace", failure)
        response = http.post(path, json=body)
        assert response.status_code == 503 and "Export is incomplete" in response.text
        assert http.get(f"/api/ideas/{idea['id']}").json()["snapshots"][entry["id"]] == saved


def test_binding_edit_advances_resolved_definition_without_mutating_saved_latest(tmp_path):
    with client(tmp_path) as http:
        idea, evaluation = capture(http)
        entry = idea["charts"][0]
        library = http.get("/api/library").json()
        series = next(s for s in library["series"] if s["id"] == "usd-ig")
        series["field"] = "unconfigured-field"
        assert http.post("/api/library/series", json=series).status_code == 200
        revised = http.get("/api/library").json()
        assert next(a for a in revised["analyses"] if a["id"] == "usd-ig")["revision"] == 2
        assert http.post("/api/analyses/usd-ig/preview", json={}).status_code == 422
        latest = http.post(f"/api/ideas/{idea['id']}/charts/{entry['id']}/latest").json()["evaluation"]
        assert latest["definition"] == evaluation["definition"]
        assert latest["definition"]["inputs"][0]["field"] == "spread"


def test_portable_idea_folder_reopens_and_exports_without_original_workspace(tmp_path):
    with client(tmp_path / "source") as http:
        idea, evaluation = capture(http)
        entry = idea["charts"][0]
        snapshot = http.get(f"/api/ideas/{idea['id']}").json()["snapshots"][entry["id"]]
    with client(tmp_path / "destination") as reopened:
        shutil.copytree(tmp_path / "source/workspace/ideas" / idea["id"], tmp_path / "destination/workspace/ideas" / idea["id"])
        assert reopened.get(f"/api/ideas/{idea['id']}").json()["idea"] == idea
        response = reopened.post(f"/api/ideas/{idea['id']}/charts/{entry['id']}/export", json={
            "evaluation_id": evaluation["id"], "display": snapshot["display"], "image": PNG, "mode": "saved"})
        assert response.status_code == 200


def test_provisional_saved_settings_do_not_create_false_definition_change_summary(tmp_path):
    with client(tmp_path) as http:
        http.post("/api/refresh")
        idea, _ = capture(http)
        assert http.get(f"/api/ideas/{idea['id']}").json()["changes"] == []


def test_legend_selection_and_scales_survive_capture_export_and_restart(tmp_path):
    display = {"years": 3, "view": "underlying", "hidden_traces": [1],
               "axis_ranges": {"xaxis": ["2023-09-30", "2026-09-30"],
                               "yaxis": [0, 200], "yaxis2": [0, 1000]}}
    with client(tmp_path) as http:
        evaluation = http.post("/api/analyses/ig-em-hy/preview", json={}).json()
        response = http.post("/api/ideas", json={"evaluation_id": evaluation["id"],
                             "image": PNG, "title": "Legend selection", "display": display})
        assert response.status_code == 200, response.text
        idea = response.json()
        entry = idea["charts"][0]
        original = http.get(f"/api/ideas/{idea['id']}").json()["snapshots"][entry["id"]]
        assert original["display"]["hidden_traces"] == [1]
        assert original["display"]["axis_ranges"] == display["axis_ranges"]
        alternate = {**display, "hidden_traces": [0]}
        exported = http.post(f"/api/ideas/{idea['id']}/charts/{entry['id']}/export",
            json={"evaluation_id": evaluation["id"], "image": PNG,
                  "mode": "saved", "display": alternate})
        assert exported.status_code == 200, exported.text
        export_id = exported.headers["X-Snapshot-ID"]
        wrong_view = http.post(f"/api/ideas/{idea['id']}/charts/{entry['id']}/export",
            json={"evaluation_id": evaluation["id"], "image": PNG, "mode": "saved",
                  "display": {**display, "view": "analysis"}})
        assert wrong_view.status_code == 422
    with client(tmp_path) as reopened:
        result = reopened.get(f"/api/ideas/{idea['id']}").json()
        assert result["snapshots"][entry["id"]] == original
        exported_record = reopened.app.state.repository.get_snapshot(idea["id"], export_id)
        assert exported_record.display.hidden_traces == (0,)
        assert exported_record.display.model_dump(mode="json")["axis_ranges"] == display["axis_ranges"]
        assert exported_record.evaluation == reopened.app.state.repository.get_snapshot(idea["id"], original["id"]).evaluation


def test_older_display_settings_default_to_all_series_and_automatic_scales():
    from kairopsis.models import DisplaySettings
    from pydantic import ValidationError
    older = DisplaySettings.model_validate({"years": 3, "view": "changes"})
    assert older.hidden_traces == () and older.axis_ranges == {}
    for invalid in ({"hidden_traces": [-1]}, {"hidden_traces": [2]},
                    {"axis_ranges": {"zaxis": [0, 1]}}, {"axis_ranges": {"yaxis": [0]}}):
        with pytest.raises(ValidationError):
            DisplaySettings.model_validate(invalid)
