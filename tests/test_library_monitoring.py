from fastapi.testclient import TestClient

from kairopsis.app import create_app
from kairopsis.config import Settings


def client(tmp_path):
    return TestClient(create_app(Settings(workspace=tmp_path / "workspace",
        config_dir=tmp_path / "config", cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs")))


def test_monitoring_changes_preserve_results_and_survive_restart(tmp_path):
    with client(tmp_path) as http:
        http.post("/api/refresh")
        before = http.get("/api/library").json()
        flagged = http.get("/api/analyses?scope=flagged").json()["rows"]
        assert flagged
        key = flagged[0]["analysis"]["id"]
        original = next(a for a in before["analyses"] if a["id"] == key)
        for monitored in (False, True, False):
            response = http.patch(f"/api/library/analyses/{key}/monitoring",
                json={"monitored": monitored})
            assert response.status_code == 200, response.text
            assert response.json() == {**original, "monitored": monitored}
            after = http.get("/api/library").json()
            assert after == {**before, "analyses": [
                {**a, "monitored": monitored} if a["id"] == key else a
                for a in before["analyses"]]}
            rows = http.get("/api/analyses?scope=all").json()["rows"]
            row = next(r for r in rows if r["analysis"]["id"] == key)
            assert row["compatible"]
            assert row["evaluation"] == flagged[0]["evaluation"]
            flagged_ids = {r["analysis"]["id"] for r in
                http.get("/api/analyses?scope=flagged").json()["rows"]}
            assert (key in flagged_ids) == monitored
    with client(tmp_path) as http:
        assert http.get("/api/library").json() == after


def test_monitoring_rejects_missing_analysis_and_invalid_values(tmp_path):
    with client(tmp_path) as http:
        before = http.get("/api/library").json()
        assert http.patch("/api/library/analyses/missing/monitoring",
            json={"monitored": True}).status_code == 404
        for body in ({}, {"monitored": None}, {"monitored": "false"}):
            assert http.patch("/api/library/analyses/usd-ig/monitoring",
                json=body).status_code == 422
        assert http.get("/api/library").json() == before
