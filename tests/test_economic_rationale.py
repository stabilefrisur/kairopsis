"""Economic context follows authored definitions and immutable HTTP evidence."""
from copy import deepcopy
import json

import pytest

from kairopsis.fixtures import MockMarketData
from test_rebuild_http import client, NOW, PNG


RATIONALE = "Compare compensation for credit risk.\n\nLiquidity could explain a divergence. <b>Hypothesis</b>"


def analysis(http, key="usd-ig"):
    return next(a for a in http.get("/api/library").json()["analyses"] if a["id"] == key)


def save(http, draft, bundled=False, **options):
    response = http.post("/api/library/analyses/bundle" if bundled else "/api/library/analyses",
        json={"analysis": draft, **options} if bundled else draft)
    assert response.status_code == 200, response.text
    return response.json()["analysis"] if bundled else response.json()


@pytest.mark.parametrize("key", ["usd-ig", "eur-gbp"])
@pytest.mark.parametrize("bundled", [False, True])
def test_rationale_create_preview_update_clear_and_restart(tmp_path, key, bundled):
    with client(tmp_path) as http:
        draft = {**analysis(http, key), "id": "rationale-draft", "economic_rationale": "  " + RATIONALE + "\n "}
        before = http.get("/api/library").json()
        preview = http.post("/api/library/analyses/preview", json={"analysis": draft})
        assert preview.status_code == 200, preview.text
        assert preview.json()["definition"]["economic_rationale"] == RATIONALE
        assert http.get("/api/library").json() == before
        saved = save(http, draft, bundled)
        assert saved["economic_rationale"] == RATIONALE
        assert saved["revision"] == 1
        omitted = {k: v for k, v in saved.items() if k != "economic_rationale"}
        omitted["settings"] = {**saved["settings"], "horizon": "month"}
        for path, body in [
            ("/api/library/analyses/preview", {"analysis": omitted}),
            ("/api/analyses/rationale-draft/preview", {"analysis": omitted}),
            ("/api/analyses/rationale-draft/preview", {"horizon": "week"}),
        ]:
            response = http.post(path, json=body)
            assert response.status_code == 200, response.text
            assert response.json()["definition"]["economic_rationale"] == RATIONALE
        saved = save(http, omitted, bundled)
        assert saved["revision"] == 2 and saved["economic_rationale"] == RATIONALE
        assert http.patch("/api/library/analyses/rationale-draft/monitoring", json={"monitored": True}).status_code == 200
        assert analysis(http, "rationale-draft")["economic_rationale"] == RATIONALE
    with client(tmp_path) as http:
        saved = analysis(http, "rationale-draft")
        assert saved["economic_rationale"] == RATIONALE
        assert http.post("/api/analyses/rationale-draft/preview", json={}).json()["definition"]["economic_rationale"] == RATIONALE
        cleared = save(http, {**saved, "economic_rationale": "  \n "}, bundled)
        assert cleared["revision"] == 3 and cleared["economic_rationale"] == ""


@pytest.mark.parametrize("invalid", [None, 42, False, [], {}, "x" * 10001])
def test_invalid_rationale_rejected_by_saves_and_previews_without_mutation(tmp_path, invalid):
    with client(tmp_path) as http:
        before = http.get("/api/library").json()
        draft = {**analysis(http), "economic_rationale": invalid}
        for path, body in [
            ("/api/library/analyses", draft),
            ("/api/library/analyses/bundle", {"analysis": draft, "series_drafts": [{**before["series"][0], "name": "Must not save"}]}),
            ("/api/library/analyses/preview", {"analysis": draft}),
            ("/api/analyses/usd-ig/preview", {"analysis": draft}),
        ]:
            response = http.post(path, json=body)
            assert response.status_code == 422, response.text
            assert http.get("/api/library").json() == before


def test_bundle_rationale_and_staged_series_advance_once_and_conflict_retains_saved_text(tmp_path):
    with client(tmp_path) as http:
        draft = analysis(http)
        series = next(s for s in http.get("/api/library").json()["series"] if s["id"] == "usd-ig")
        saved = save(http, {**draft, "economic_rationale": RATIONALE}, True,
            series_drafts=[{**series, "name": "Revised input"}],
            base_revisions={"analyses": {draft["id"]: draft["revision"]}, "series": {series["id"]: series["revision"]}})
        assert saved["revision"] == draft["revision"] + 1
        assert saved["economic_rationale"] == RATIONALE
        before = http.get("/api/library").json()
        conflict = http.post("/api/library/analyses/bundle", json={"analysis": {**draft, "economic_rationale": "Stale rationale"}})
        assert conflict.status_code == 409
        assert http.get("/api/library").json() == before


def test_empty_new_drafts_length_boundary_and_explicit_preview_clear(tmp_path):
    with client(tmp_path) as http:
        draft = {k: v for k, v in analysis(http).items() if k != "economic_rationale"}
        draft["id"] = "new-without-rationale"
        preview = http.post("/api/library/analyses/preview", json={"analysis": draft})
        assert preview.status_code == 200, preview.text
        assert preview.json()["definition"]["economic_rationale"] == ""
        saved = save(http, draft)
        assert saved["economic_rationale"] == ""
        saved = save(http, {**saved, "economic_rationale": "x" * 10000}, True)
        assert len(saved["economic_rationale"]) == 10000
        for path in ("/api/library/analyses/preview", "/api/analyses/new-without-rationale/preview"):
            response = http.post(path, json={"analysis": {**saved, "economic_rationale": ""}})
            assert response.status_code == 200, response.text
            assert response.json()["definition"]["economic_rationale"] == ""
        assert analysis(http, saved["id"])["economic_rationale"] == "x" * 10000


def test_captured_rationale_survives_library_revision_deletion_latest_export_and_restart(tmp_path):
    with client(tmp_path) as http:
        saved = save(http, {**analysis(http), "economic_rationale": RATIONALE})
        evidence = http.post("/api/analyses/usd-ig/preview", json={}).json()
        idea_response = http.post("/api/ideas", json={"evaluation_id": evidence["id"], "image": PNG, "title": "Economic question"})
        assert idea_response.status_code == 200, idea_response.text
        idea = idea_response.json()
        entry = idea["charts"][0]
        changed = save(http, {**saved, "economic_rationale": "A different research question."})
        assert changed["revision"] == saved["revision"] + 1
        assert http.post("/api/analyses/usd-ig/preview", json={}).json()["definition"]["economic_rationale"] == changed["economic_rationale"]
    with client(tmp_path) as http:
        for deleted in (False, True):
            if deleted:
                assert http.delete("/api/library/analyses/usd-ig").status_code == 200
            assert http.get(f'/api/evaluations/{evidence["id"]}').json()["definition"]["economic_rationale"] == RATIONALE
            result = http.get(f'/api/ideas/{idea["id"]}').json()
            assert result["snapshots"][entry["id"]]["evaluation"]["definition"]["economic_rationale"] == RATIONALE
            latest = http.post(f'/api/ideas/{idea["id"]}/charts/{entry["id"]}/latest').json()["evaluation"]
            assert latest["definition"] == evidence["definition"]
            for mode, evaluation in (("saved", evidence), ("latest", latest)):
                exported = http.post(f'/api/ideas/{idea["id"]}/charts/{entry["id"]}/export', json={
                    "evaluation_id": evaluation["id"], "image": PNG, "mode": mode, "display": {}})
                assert exported.status_code == 200, exported.text
                path = tmp_path / "workspace" / "ideas" / idea["id"] / "snapshots" / exported.headers["X-Snapshot-ID"] / "snapshot.json"
                assert json.loads(path.read_text())["evaluation"]["definition"]["economic_rationale"] == RATIONALE


def test_legacy_catalogue_and_evidence_missing_rationale_stay_empty_and_byte_identical(tmp_path):
    with client(tmp_path) as http:
        evidence = http.post("/api/analyses/eur-gbp/preview", json={}).json()
        idea = http.post("/api/ideas", json={"evaluation_id": evidence["id"], "image": PNG, "title": "Legacy"}).json()
    root = tmp_path / "workspace"
    catalogue_path = root / "catalogue.json"
    catalogue = json.loads(catalogue_path.read_text())
    for draft in catalogue["analyses"]:
        draft.pop("economic_rationale", None)
    catalogue_path.write_text(json.dumps(catalogue))
    folder = next(root.rglob("snapshot.json")).parent
    paths = [folder / "snapshot.json", root / "evaluations" / (evidence["id"] + ".json")]
    for path in paths:
        payload = json.loads(path.read_text())
        (payload.get("evaluation") or payload)["definition"].pop("economic_rationale")
        path.write_text(json.dumps(payload))
    original = {path: path.read_bytes() for path in [catalogue_path, *paths, folder / "data.csv", folder / "image.png"]}
    with client(tmp_path) as http:
        assert "economic_rationale" not in analysis(http, "eur-gbp")
        fresh = http.post("/api/analyses/eur-gbp/preview", json={}).json()
        assert fresh["definition"]["economic_rationale"] == ""
        assert catalogue_path.read_bytes() == original[catalogue_path]
        # Today's Library text must never fill the missing historical context.
        save(http, {**analysis(http, "eur-gbp"), "economic_rationale": "Current rationale"})
    original.pop(catalogue_path)
    with client(tmp_path) as http:
        entry = idea["charts"][0]
        assert http.get(f'/api/evaluations/{evidence["id"]}').json()["definition"]["economic_rationale"] == ""
        snapshot = http.get(f'/api/ideas/{idea["id"]}').json()["snapshots"][entry["id"]]
        assert snapshot["evaluation"]["definition"]["economic_rationale"] == ""
        latest = http.post(f'/api/ideas/{idea["id"]}/charts/{entry["id"]}/latest').json()["evaluation"]
        assert latest["definition"]["economic_rationale"] == "" and latest["points"] == evidence["points"]
        exported = http.post(f'/api/ideas/{idea["id"]}/charts/{entry["id"]}/export', json={
            "evaluation_id": latest["id"], "image": PNG, "mode": "latest", "display": {}})
        assert exported.status_code == 200, exported.text
    assert all(path.read_bytes() == content for path, content in original.items())


def test_rationale_revision_preserves_numbers_thresholds_and_incompatible_baseline(tmp_path):
    with client(tmp_path) as http:
        draft = deepcopy(analysis(http))
        draft["settings"].update(move_threshold=8, material_change=2)
        draft["monitored"] = True
        saved = save(http, draft)
        before_id = http.post("/api/refresh").json()["results"]["usd-ig"]
        before = http.get(f"/api/evaluations/{before_id}").json()
        changed = save(http, {**saved, "economic_rationale": RATIONALE})
        assert changed["settings"] == saved["settings"]
        after_id = http.post("/api/refresh").json()["results"]["usd-ig"]
        after = http.get(f"/api/evaluations/{after_id}").json()
        for field in ("current", "change", "percentile", "points", "conditions", "eligible", "unit"):
            assert after[field] == before[field]
        assert after["finding"] == "incompatible" and after["reasons"] == []
        rows = http.get("/api/analyses?scope=flagged").json()["rows"]
        assert not any(row["analysis"]["id"] == "usd-ig" for row in rows)


def test_rationale_cannot_make_unverified_observations_eligible(tmp_path):
    class UnverifiedProvider:
        def fetch(self, request):
            return MockMarketData(lambda: NOW).fetch(request).model_copy(update={"outcome": "unverified"})

    with client(tmp_path, UnverifiedProvider()) as http:
        save(http, {**analysis(http), "economic_rationale": "Treat this as a market finding."})
        evidence = http.post("/api/analyses/usd-ig/preview", json={}).json()
        assert not evidence["eligible"] and evidence["reasons"] == []
        assert evidence["definition"]["economic_rationale"] == "Treat this as a market finding."
