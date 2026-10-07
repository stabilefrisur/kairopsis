"""HTTP workflows use real retained bundles, with no external providers."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import os
import shutil
from threading import Event, Lock
from time import monotonic, sleep

import pytest

from kairopsis.models import AnalysisDefinition, DataFailure, DataResponse, Observation, SeriesResult
from test_rebuild_http import NOW, capture, client


class SmallProvider:
    def __init__(self):
        self.calls = 0
        self.active = 0
        self.maximum = 0
        self.lock = Lock()
        self.entered, self.release = Event(), Event()
        self.block = False
        self.outcome = "synthetic"
        self.fail = False
        self.fail_ids: set[str] = set()
        self.stale = False

    def fetch(self, request):
        with self.lock:
            self.calls += 1
            self.active += 1
            self.maximum = max(self.maximum, self.active)
        try:
            if self.block:
                self.entered.set()
                assert self.release.wait(10), "Test provider not released"
            series = []
            for index, binding in enumerate(request.bindings):
                observations = tuple(Observation(date=day, observed_on=day,
                    value=100 + index * 50 + n % 9) for n in range(140)
                    if (day := request.end - timedelta(days=139 - n + (20 if self.stale else 0))).weekday() < 5)
                if not self.fail and binding.id not in self.fail_ids:
                    series.append(SeriesResult(binding=binding, observations=observations, provenance="Small synthetic sample"))
            failures = tuple(DataFailure(binding_id=b.id, code="test_offline", message="Synthetic retrieval failure")
                for b in request.bindings if self.fail or b.id in self.fail_ids)
            return DataResponse(mode="mock", requested=tuple(b.id for b in request.bindings),
                series=tuple(series), attempted_at=NOW, completed_at=NOW,
                outcome="partial" if failures and series else "failed" if failures else self.outcome,
                failures=failures)
        finally:
            with self.lock:
                self.active -= 1


def completed(http, run_id):
    deadline = monotonic() + 15
    while monotonic() < deadline:
        run = http.get(f"/api/screenings/{run_id}").json()
        if run["status"] != "running":
            assert run["status"] == "completed", run
            return run
        sleep(.01)
    pytest.fail("Screening did not finish")


def test_manual_agent_daily_retention_reads_and_unique_briefs(tmp_path):
    provider = SmallProvider()
    with client(tmp_path, provider) as http:
        assert http.get("/api/screenings").json() == {"runs": []}
        assert provider.calls == 0
        http.post("/api/analyses/usd-ig/preview", json={})
        assert http.get("/api/screenings").json() == {"runs": []}
        refresh = http.post("/api/refresh").json()
        manual = completed(http, refresh["screening_run_id"])
        assert manual["trigger"] == "manual" and manual["path"] == refresh["screening_path"]
        manifest = manual["manifest"]
        assert manifest["universe_count"] == len(http.get("/api/library").json()["analyses"])
        assert manifest["monitored_count"] == sum(r["monitored"] for r in manifest["rows"])
        before = provider.calls
        for row in manifest["rows"]:
            detail = http.get(f"/api/screenings/{manual['run_id']}/evaluations/{row['evaluation_id']}")
            assert detail.status_code == 200
            assert detail.json()["definition"]["id"] == row["analysis_id"]
        assert http.get(f"/api/screenings/{manual['run_id']}/evaluations/not-retained").status_code == 404
        for invalid in (0, 101):
            assert http.get("/api/screenings", params={"limit": invalid}).status_code == 422
        reports = [http.post(f"/api/screenings/{manual['run_id']}/briefs", json={"markdown": text}).json()
            for text in ("# First\n\nAs of retained evidence.", "# Second")]
        assert reports[0]["brief_id"] != reports[1]["brief_id"]
        for report in reports:
            assert http.get(f"/api/screenings/{manual['run_id']}/briefs/{report['brief_id']}").json() == report
        assert http.post(f"/api/screenings/{manual['run_id']}/briefs", json={"markdown": "  "}).status_code == 422
        assert provider.calls == before
        assert http.post("/api/screenings", json={"request_id": "../bad"}).status_code == 422
        agent = http.post("/api/screenings", json={"request_id": "request-1"})
        assert agent.status_code == 202
        run = completed(http, agent.json()["run_id"])
        calls = provider.calls
        assert http.post("/api/screenings", json={"request_id": "request-1"}).json()["run_id"] == run["run_id"]
        assert provider.calls == calls
        assert run["trigger"] == "agent"
        state = http.app.state.repository.read_json("refresh")
        state["day"] = "2026-09-29"
        http.app.state.repository.write_json("refresh", state)
        http.app.state.research.first_open()
        deadline = monotonic() + 15
        while http.app.state.research.running and monotonic() < deadline:
            sleep(.01)
        runs = http.get("/api/screenings").json()["runs"]
        assert len(runs) == 3 and any(r["trigger"] == "daily" and r["status"] == "completed" for r in runs)
        http.app.state.research.first_open()
        assert len(http.get("/api/screenings").json()["runs"]) == 3
    with client(tmp_path, provider) as reopened:
        assert reopened.post("/api/screenings", json={"request_id": "request-1"}).json()["run_id"] == run["run_id"]
        assert reopened.get(f"/api/screenings/{manual['run_id']}/briefs/{reports[0]['brief_id']}").json() == reports[0]


def test_concurrent_requests_freeze_catalogue_monitoring_rationale_and_idea_refs(tmp_path):
    provider = SmallProvider()
    with client(tmp_path, provider) as http:
        idea, _ = capture(http)
        original = http.get("/api/library").json()
        provider.block = True
        first = http.post("/api/screenings", json={"request_id": "freeze"}).json()
        assert first["status"] == "running" and provider.entered.wait(5)
        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(pool.map(lambda _: http.post("/api/screenings", json={"request_id": "freeze"}).json(), range(4)))
        assert {r["run_id"] for r in responses} == {first["run_id"]}
        second = http.post("/api/screenings", json={"request_id": "after-edit"}).json()
        assert second["run_id"] != first["run_id"]
        analysis = next(a for a in original["analyses"] if a["id"] == "usd-ig")
        assert http.post("/api/library/analyses", json={**analysis, "economic_rationale": "Changed question"}).status_code == 200
        http.patch("/api/library/analyses/usd-ig/monitoring", json={"monitored": True})
        http.patch(f"/api/ideas/{idea['id']}", json={"title": "Changed title"})
        http.delete(f"/api/ideas/{idea['id']}/charts/{idea['charts'][0]['id']}")
        binding = next(s for s in original["series"] if s["id"] == "usd-ig")
        http.post("/api/library/series", json={**binding, "name": "Changed input"})
        provider.release.set()
        old_run, new_run = completed(http, first["run_id"]), completed(http, second["run_id"])
        old_row = next(r for r in old_run["manifest"]["rows"] if r["analysis_id"] == "usd-ig")
        new_row = next(r for r in new_run["manifest"]["rows"] if r["analysis_id"] == "usd-ig")
        assert old_row["economic_rationale"] == analysis["economic_rationale"] and not old_row["monitored"]
        assert old_row["inputs"][0]["name"] == binding["name"]
        assert old_row["idea_refs"] == [{"id": idea["id"], "title": idea["title"], "version": idea["version"],
            "chart_ids": [idea["charts"][0]["id"]]}]
        assert new_row["economic_rationale"] == "Changed question" and new_row["monitored"]
        assert new_row["inputs"][0]["name"] == "Changed input" and not new_row["idea_refs"]
        assert provider.maximum == 1


def test_failed_attempts_retained_values_unverified_and_portability(tmp_path):
    provider = SmallProvider()
    with client(tmp_path / "source", provider) as http:
        initial = http.post("/api/refresh").json()
        provider.fail = True
        failure = http.post("/api/refresh").json()
        run = completed(http, failure["screening_run_id"])
        counts = run["manifest"]["coverage"]["all"]
        assert counts["failed"] == counts["retained"] == counts["total"]
        assert counts["eligible"] == counts["flagged"] == counts["evaluated"] == 0
        for row in run["manifest"]["rows"]:
            assert row["status"] == "retained" and row["provider"]["outcome"] == "failed"
            assert row["retained_evaluation_id"] == initial["results"][row["analysis_id"]]
            attempt = json.loads((tmp_path / "source/workspace/screenings" / run["run_id"] / row["attempt_ref"]).read_text())
            assert attempt["data"]["failures"] and attempt["definition"]["id"] == row["analysis_id"]
        provider.fail, provider.outcome = False, "unverified"
        unverified = completed(http, http.post("/api/refresh").json()["screening_run_id"])
        assert unverified["manifest"]["coverage"]["all"]["eligible"] == 0
        assert unverified["manifest"]["coverage"]["all"]["evaluated"] == counts["total"]
        assert all(r["provider"]["outcome"] == "unverified" for r in unverified["manifest"]["rows"])
        baseline_ids = {r["baseline_id"] for r in unverified["manifest"]["rows"]}
        assert baseline_ids <= set(unverified["manifest"]["evidence"])
    with client(tmp_path / "copy", provider) as copied:
        source = tmp_path / "source/workspace/screenings" / unverified["run_id"]
        destination = tmp_path / "copy/workspace/screenings" / unverified["run_id"]
        shutil.copytree(source, destination)
        shutil.rmtree(tmp_path / "source")
        before = provider.calls
        historical = completed(copied, unverified["run_id"])
        assert historical["manifest"] == unverified["manifest"]
        assert historical["path"] == str(destination)
        for evidence_id in historical["manifest"]["evidence"]:
            assert copied.get(f"/api/screenings/{unverified['run_id']}/evaluations/{evidence_id}").status_code == 200
        assert provider.calls == before


@pytest.mark.parametrize("target", ["manifest.json", "refresh.json"])
def test_publication_failure_preserves_pointer_and_finished_runs(tmp_path, monkeypatch, target):
    provider = SmallProvider()
    with client(tmp_path, provider) as http:
        previous = http.post("/api/refresh").json()
        replace = os.replace
        def fail(source, destination):
            if destination.name == target:
                raise OSError("Injected publication failure")
            replace(source, destination)
        monkeypatch.setattr(os, "replace", fail)
        response = http.post("/api/refresh")
        assert response.status_code == 503
        assert http.app.state.repository.read_json("refresh") == previous
        runs = http.get("/api/screenings").json()["runs"]
        assert sorted(r["status"] for r in runs) == ["completed", "failed"]
        failed = next(r for r in runs if r["status"] == "failed")
        assert not (tmp_path / "workspace/screenings" / failed["run_id"] / "manifest.json").exists()
        assert http.post(f"/api/screenings/{failed['run_id']}/briefs", json={"markdown": "Incomplete"}).status_code == 422


def test_restart_marks_unfinished_request_interrupted_and_preserves_identity(tmp_path):
    provider = SmallProvider()
    with client(tmp_path, provider) as http:
        status, _ = http.app.state.research.screenings.create("agent", "interrupted-request", NOW)
    with client(tmp_path, provider) as http:
        run = http.get(f"/api/screenings/{status['run_id']}").json()
        assert run["status"] == "interrupted"
        duplicate = http.post("/api/screenings", json={"request_id": "interrupted-request"}).json()
        assert duplicate["run_id"] == run["run_id"] and duplicate["status"] == "interrupted"
        assert provider.calls == 0


@pytest.mark.parametrize("monitored", [False, True])
def test_hundreds_of_rows_are_compact_and_cover_all_or_none_monitored(tmp_path, monitored):
    provider = SmallProvider()
    with client(tmp_path, provider) as http:
        repository = http.app.state.repository
        records = http.get("/api/library").json()
        records["analyses"] = [AnalysisDefinition(id=f"analysis-{n:03}", name=f"Synthetic {n}",
            series_ids=("usd-ig",), monitored=monitored).model_dump(mode="json") for n in range(300)]
        with repository.transaction():
            repository.write_json("catalogue", records)
        run = completed(http, http.post("/api/refresh").json()["screening_run_id"])
        manifest = run["manifest"]
        assert manifest["universe_count"] == 300 and manifest["monitored_count"] == (300 if monitored else 0)
        assert manifest["coverage"]["all"]["evaluated"] == 300
        assert provider.calls == 300
        assert len(json.dumps(manifest).encode()) < 900_000
        assert all("points" not in row and "data" not in row and "observations" not in row for row in manifest["rows"])


def test_total_failure_without_history_and_empty_universe_still_complete(tmp_path):
    provider = SmallProvider()
    provider.fail = True
    with client(tmp_path, provider) as http:
        run = completed(http, http.post("/api/refresh").json()["screening_run_id"])
        assert all(r["status"] == "failed" and r["evaluation_id"] is None for r in run["manifest"]["rows"])
        assert not run["manifest"]["evidence"]
        repository = http.app.state.repository
        records = http.get("/api/library").json()
        records["analyses"] = []
        with repository.transaction():
            repository.write_json("catalogue", records)
        empty = completed(http, http.post("/api/refresh").json()["screening_run_id"])
        assert empty["manifest"]["universe_count"] == 0 and empty["manifest"]["rows"] == []


def test_quiet_cached_stale_and_partial_coverage_keep_their_actual_states(tmp_path):
    provider = SmallProvider()
    with client(tmp_path, provider) as http:
        first = completed(http, http.post("/api/refresh").json()["screening_run_id"])
        quiet = next(r for r in first["manifest"]["rows"] if r["analysis_id"] == "usd-ig")
        assert quiet["finding"] == "quiet" and quiet["eligible"] and not quiet["flagged"]
        provider.outcome = "cache"
        cached = completed(http, http.post("/api/refresh").json()["screening_run_id"])
        counts = cached["manifest"]["coverage"]["all"]
        assert counts["provider_outcomes"]["cache"] == counts["total"] and counts["eligible"] == 0
        provider.outcome, provider.stale = "synthetic", True
        stale = completed(http, http.post("/api/refresh").json()["screening_run_id"])
        assert stale["manifest"]["coverage"]["all"]["eligible"] == 0
        assert all(any("Stale" in reason for reason in r["limitations"]) for r in stale["manifest"]["rows"])
        provider.stale, provider.fail_ids = False, {"usd-ig"}
        partial = completed(http, http.post("/api/refresh").json()["screening_run_id"])
        counts = partial["manifest"]["coverage"]["all"]
        assert 0 < counts["failed"] < counts["total"] and counts["provider_outcomes"]["partial"] > 0
        assert counts["retained"] == counts["failed"]


def test_detail_ids_and_symlinks_cannot_escape_run(tmp_path):
    provider = SmallProvider()
    with client(tmp_path, provider) as http:
        run = completed(http, http.post("/api/refresh").json()["screening_run_id"])
        store = http.app.state.research.screenings
        for invalid in ("..", "bad/path", "bad\\path", "a" * 129):
            with pytest.raises(ValueError):
                store.get(invalid)
            with pytest.raises(ValueError):
                store.brief(run["run_id"], invalid)
        folder = tmp_path / "workspace/screenings" / run["run_id"]
        outside = tmp_path / "outside"
        outside.mkdir()
        (folder / "briefs").symlink_to(outside, target_is_directory=True)
        assert http.post(f"/api/screenings/{run['run_id']}/briefs", json={"markdown": "Escaped"}).status_code == 422
        assert list(outside.iterdir()) == []


def test_provider_exception_is_redacted_and_async_publication_failure_stops_polling(tmp_path, monkeypatch):
    class ExplodingProvider:
        def fetch(self, request):
            raise RuntimeError("PRIVATE_TOKEN=should-never-appear")
    with client(tmp_path, ExplodingProvider()) as http:
        run = completed(http, http.post("/api/screenings", json={"request_id": "provider-error"}).json()["run_id"])
        assert "PRIVATE_TOKEN" not in json.dumps(run)
        assert run["manifest"]["coverage"]["all"]["provider_outcomes"]["exception"] == run["manifest"]["universe_count"]
        replace = os.replace
        def fail(source, destination):
            if destination.name == "manifest.json":
                raise OSError("Cannot publish")
            replace(source, destination)
        monkeypatch.setattr(os, "replace", fail)
        job = http.post("/api/screenings", json={"request_id": "publication-error"}).json()
        deadline = monotonic() + 10
        while monotonic() < deadline:
            status = http.get(f"/api/screenings/{job['run_id']}").json()
            if status["status"] != "running":
                break
            sleep(.01)
        assert status["status"] == "failed"
        assert http.post("/api/screenings", json={"request_id": "publication-error"}).json()["run_id"] == job["run_id"]


def test_repeated_refreshes_retain_only_actual_comparison_and_original_bytes(tmp_path):
    provider = SmallProvider()
    with client(tmp_path, provider) as http:
        for _ in range(5):
            run = completed(http, http.post("/api/refresh").json()["screening_run_id"])
            manifest = run["manifest"]
            assert len(manifest["evidence"]) <= 2 * manifest["universe_count"]
            folder = tmp_path / "workspace/screenings" / run["run_id"]
            for row in manifest["rows"]:
                detail = http.get(f"/api/screenings/{run['run_id']}/evaluations/{row['evaluation_id']}").json()
                assert detail["baseline_id"] == row["baseline_id"]
                if row["baseline_ref"]:
                    assert (folder / row["baseline_ref"]).exists()
            for evaluation_id, relative in manifest["evidence"].items():
                assert (folder / relative).read_bytes() == (tmp_path / "workspace/evaluations" / (evaluation_id + ".json")).read_bytes()
        provider.fail = True
        retained = completed(http, http.post("/api/refresh").json()["screening_run_id"])
        assert len(retained["manifest"]["evidence"]) <= 2 * retained["manifest"]["universe_count"]
        for row in retained["manifest"]["rows"]:
            detail = http.get(f"/api/screenings/{retained['run_id']}/evaluations/{row['evaluation_id']}").json()
            assert row["baseline_id"] == detail["baseline_id"] and row["baseline_id"] != row["evaluation_id"]


@pytest.mark.parametrize("filename", ["status.json", "manifest.json"])
def test_status_and_manifest_symlinks_never_read_outside_json(tmp_path, filename):
    provider = SmallProvider()
    outside = tmp_path / "outside.json"
    outside.write_text('{"private": "outside-only"}')
    with client(tmp_path, provider) as http:
        if filename == "manifest.json":
            run_id = http.post("/api/refresh").json()["screening_run_id"]
        else:
            run_id = http.app.state.research.screenings.create("agent", "reserved", NOW)[0]["run_id"]
        path = tmp_path / "workspace/screenings" / run_id / filename
        path.unlink()
        path.symlink_to(outside)
        response = http.get(f"/api/screenings/{run_id}")
        assert response.status_code == 422 and "outside-only" not in response.text
        assert http.get("/api/screenings").status_code == 422
        if filename == "status.json":
            assert http.post("/api/screenings", json={"request_id": "different"}).status_code == 422
    if filename == "status.json":
        with pytest.raises(ValueError, match="Record path outside"):
            client(tmp_path, provider)
    assert outside.read_text() == '{"private": "outside-only"}'


def test_failed_status_write_still_ends_polling_and_restart_marks_interrupted(tmp_path, monkeypatch):
    provider = SmallProvider()
    provider.block = True
    with client(tmp_path, provider) as http:
        job = http.post("/api/screenings", json={"request_id": "full-disk"}).json()
        assert provider.entered.wait(5)
        replace = os.replace
        def fail(source, destination):
            if destination.name in ("manifest.json", "status.json"):
                raise OSError("Injected full disk")
            replace(source, destination)
        monkeypatch.setattr(os, "replace", fail)
        provider.release.set()
        deadline = monotonic() + 10
        while monotonic() < deadline:
            status = http.get(f"/api/screenings/{job['run_id']}").json()
            if status["status"] != "running":
                break
            sleep(.01)
        assert status["status"] == "failed"
        assert http.post("/api/screenings", json={"request_id": "full-disk"}).json()["status"] == "failed"
        assert not (tmp_path / "workspace/refresh.json").exists()
        monkeypatch.setattr(os, "replace", replace)
    with client(tmp_path, provider) as reopened:
        assert reopened.get(f"/api/screenings/{job['run_id']}").json()["status"] == "interrupted"
