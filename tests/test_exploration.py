"""Real application boundary: pinned queries, engine equivalence and portable evidence."""
import base64
import hashlib
import io
import json
import zipfile
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from kairopsis.analytics import evaluate
from kairopsis.exploration import Exploration, fingerprint
from kairopsis.exploration_models import CollectionItem, ViewDefinition, ViewSample, WorkspaceDefinition
from kairopsis.exploration_repository import ExplorationRepository
from kairopsis.models import AnalysisSettings, DataResponse, Observation, ResolvedDefinition, SeriesBinding, SeriesResult
from kairopsis.repository import Repository
from test_rebuild_http import NOW, PNG, client


class SuppliedData:
    def __init__(self):
        self.requests = []

    def fetch(self, request):
        self.requests.append(request)
        result = []
        for binding in request.bindings:
            symbol = int(binding.params.get("symbol", 0))
            offset = int(binding.params.get("offset", 0))
            field = binding.field
            observations = []
            for index in range(15):
                day = date(2026, 9, 10) + timedelta(days=index)
                if field == "duration" and symbol == 2 and index == 8:
                    continue
                value = float((index + 1) * (symbol + 1) + offset)
                if field == "duration":
                    value = float(7 + (index % 4) * (symbol + 1))
                if field == "gap":
                    value = float(index - 7)
                observations.append(Observation(date=day, value=value, observed_on=day if symbol != 2 else None))
            result.append(SeriesResult(binding=binding, observations=tuple(observations), provenance="Explicit deterministic supplied test data; symbol2 native dates unknown"))
        return DataResponse(mode="mock", requested=tuple(b.id for b in request.bindings), series=tuple(result),
            attempted_at=NOW, completed_at=NOW, outcome="synthetic")


def collection():
    return tuple(CollectionItem(id=f"c{s}-{field}", symbol=f"Symbol {s}", field=field,
        binding=SeriesBinding(id=f"b{s}-{field}", name=f"{s}/{field}", instrument=str(s), source="test",
            field=field, unit="bp" if field == "spread" else "years", currency="USD", params={"symbol": s}))
        for s in range(3) for field in ("spread", "duration"))


def workspace(family="history", **view_changes):
    items = collection()
    return WorkspaceDefinition(collection=items, as_of=date(2026, 9, 24), question="Does pricing reflect duration?", notes="Supplied basis under investigation.",
        views=(ViewDefinition(id="v1", family=family, measures=tuple(i.id for i in items), **view_changes),))


def test_contracts_reject_ambiguity_and_unknown_dependencies():
    w = workspace()
    assert WorkspaceDefinition.model_validate_json(w.model_dump_json()) == w
    with pytest.raises(ValidationError, match="Duplicate symbol/field"):
        w.model_copy(update={"collection": (*w.collection, w.collection[0].model_copy(update={"id": "other"}))}).model_validate(w.model_copy(update={"collection": (*w.collection, w.collection[0].model_copy(update={"id": "other"}))}).model_dump())
    with pytest.raises(ValidationError, match="exactly one"):
        CollectionItem(symbol="X", field="spread")
    with pytest.raises(ValidationError, match="existing collection"):
        WorkspaceDefinition(views=(ViewDefinition(measures=("missing",)),))
    with pytest.raises(ValidationError, match="explicit start"):
        ViewSample(interval_measure="return")


def test_preview_same_binding_id_different_revision_and_query_not_aliased(tmp_path):
    provider = SuppliedData()
    first = collection()[0]
    assert first.binding
    second = first.model_copy(update={"id": "c-revised", "field": "revised spread", "binding": first.binding.model_copy(update={"revision": 2, "params": {"symbol": 0, "offset": 100}})})
    w = WorkspaceDefinition(collection=(first, second), as_of=date(2026, 9, 24), views=(ViewDefinition(measures=(first.id, second.id)),))
    with client(tmp_path, provider) as http:
        response = http.post("/api/explore/preview", json={"workspace": w.model_dump(mode="json")})
        assert response.status_code == 200, response.text
        result = response.json()["resolved_results"][0]
        assert len(provider.requests) == 2
        assert result["rows"][-1]["values"] == {"spread": 15, "revised spread": 115}
        assert len(result["input_evidence"]["bindings"]) == 2


def test_engine_equivalence_asof_and_display_independence(tmp_path):
    provider = SuppliedData()
    item = collection()[0]
    assert item.binding
    definition = ResolvedDefinition(id="local", revision=1, name="Prior-only Zscore", calculation="level", inputs=(item.binding,),
        settings=AnalysisSettings(calculation_contract="input-pipeline-v2", standardization="zscore", minimum_history=3))
    calculated = item.model_copy(update={"kind": "analysis", "origin": "local", "binding": None, "analysis": definition})
    w = WorkspaceDefinition(collection=(calculated,), as_of=date(2026, 9, 22), views=(ViewDefinition(measures=(calculated.id,)),))
    with client(tmp_path, provider) as http:
        result = http.post("/api/explore/preview", json={"workspace": w.model_dump(mode="json")}).json()["resolved_results"][0]
        from kairopsis.models import Evaluation
        retained = Evaluation.model_validate(result["input_evidence"]["evaluations"][calculated.id])
        oracle = evaluate(definition, retained.data, retained.request, NOW)
        assert retained.points == oracle.points and retained.standardization_estimate == oracle.standardization_estimate
        assert all(o.date <= w.as_of for s in retained.data.series for o in s.observations)
        display = w.model_copy(update={"views": (w.views[0].model_copy(update={"display_start": date(2026, 9, 20)}),)})
        cropped = http.post("/api/explore/preview", json={"workspace": display.model_dump(mode="json")}).json()["resolved_results"][0]
        assert cropped["rows"] == result["rows"]
        assert cropped["statistics"] == result["statistics"]
        assert len(cropped["display_row_ids"]) < len(cropped["rows"])


def test_one_retained_sample_survives_chart_family_changes_and_drilldown(tmp_path):
    provider = SuppliedData()
    w = workspace("correlation", options={"correlation_orientation": "series"}, sample=ViewSample(members=("Symbol 0", "Symbol 1")))
    with client(tmp_path, provider) as http:
        original = http.post("/api/explore/preview", json={"workspace": w.model_dump(mode="json")}).json()["resolved_results"][0]
        assert all(r["symbol"] != "Symbol 2" for r in original["rows"])
        for family in ("heatmap", "scatter", "correlation"):
            changed = w.model_copy(update={"views": (w.views[0].model_copy(update={"family": family}),)})
            result = http.post("/api/explore/preview", json={"workspace": changed.model_dump(mode="json")}).json()["resolved_results"][0]
            assert {r["id"] for r in result["rows"]} == {r["id"] for r in original["rows"]}
            assert set(result["statistics"]["row_ids"]) == {r["id"] for r in result["rows"]}
        cell = original["statistics"]["cells"][1]
        drill = w.views[0].model_copy(update={"family": "scatter", "shape": "paired_date", "measures": ("c0-spread", "c1-spread"),
            "sample": ViewSample(row_ids=tuple(cell["row_ids"]), members=("Symbol 0", "Symbol 1"))})
        drilled = http.post("/api/explore/preview", json={"workspace": w.model_copy(update={"views": (drill,)}).model_dump(mode="json")}).json()["resolved_results"][0]
        assert len(drilled["rows"]) == cell["count"]


def test_nonpositive_interval_and_engine_percentage_base_unavailable(tmp_path):
    provider = SuppliedData()
    binding = SeriesBinding(id="gap", name="Supplied gap", instrument="gap", source="test", field="gap", unit="bp", currency="USD")
    item = CollectionItem(id="gap", symbol="Relationship", field="gap", binding=binding)
    w = WorkspaceDefinition(collection=(item,), as_of=date(2026, 9, 24), views=(ViewDefinition(family="ranking", shape="cross_section", measures=(item.id,),
        sample=ViewSample(interval_start=date(2026, 9, 14), interval_measure="return")),))
    with client(tmp_path, provider) as http:
        result = http.post("/api/explore/preview", json={"workspace": w.model_dump(mode="json")}).json()["resolved_results"][0]
        assert not result["rows"]
        assert any("nonpositive baseline" in reason for row in result["excluded"] for reason in row["reasons"])
        analysis = ResolvedDefinition(id="gap-percent", revision=1, name="Gap percent", calculation="level", inputs=(binding,),
            settings=AnalysisSettings(calculation_contract="input-pipeline-v2", measure="return"))
        calculated = item.model_copy(update={"kind": "analysis", "binding": None, "analysis": analysis})
        engine_w = WorkspaceDefinition(collection=(calculated,), as_of=w.as_of, views=(ViewDefinition(measures=(item.id,)),))
        result = http.post("/api/explore/preview", json={"workspace": engine_w.model_dump(mode="json")}).json()["resolved_results"][0]
        evaluation = result["input_evidence"]["evaluations"][item.id]
        assert all(p["value"] is None for p in evaluation["points"] if p["date"] <= "2026-09-17")


def test_backward_asof_actual_dates_and_unknown_native_dates_visible(tmp_path):
    with client(tmp_path, SuppliedData()) as http:
        w = workspace("scatter", shape="cross_section", sample=ViewSample(end=date(2026, 9, 18), date_policy="backward", maximum_age_days=1))
        result = http.post("/api/explore/preview", json={"workspace": w.model_dump(mode="json")}).json()["resolved_results"][0]
        row = next(r for r in result["rows"] if r["symbol"] == "Symbol 2")
        assert row["dates"]["duration"] == "2026-09-17"
        assert row["dates"]["spread"] == "2026-09-18"
        assert row["observed_on"]["spread"] is None
        assert any("Unknown native" in limitation for limitation in result["limitations"])


def capture_request(http, w):
    preview = http.post("/api/explore/preview", json={"workspace": w.model_dump(mode="json")})
    assert preview.status_code == 200, preview.text
    ids = [r["id"] for r in preview.json()["resolved_results"]]
    return {"workspace": w.model_dump(mode="json"), "result_ids": ids, "images": {key: PNG for key in ids}, "title": "Frozen research", "role": "challenging"}


def test_capture_preserves_question_offline_images_csv_definitions_after_library_delete(tmp_path):
    provider = SuppliedData()
    w = workspace("scatter")
    with client(tmp_path, provider) as http:
        legacy_marker = (tmp_path / "workspace/workspace.json").read_bytes()
        body = capture_request(http, w)
        fetch_count = len(provider.requests)
        response = http.post("/api/explore/captures", json=body)
        assert response.status_code == 200, response.text
        captured = response.json()
        idea, snap = captured["idea"]["id"], captured["snapshot"]["id"]
        assert len(provider.requests) == fetch_count
        assert captured["snapshot"]["workspace"]["question"] == w.question
        assert captured["idea"]["explorations"][0]["role"] == "challenging"
        assert json.loads((tmp_path / "workspace/workspace.json").read_text())["schema_version"] == 3
        assert (tmp_path / "workspace/workspace-schema2.json").read_bytes() == legacy_marker
        exported = http.get(f"/api/explore/captures/{idea}/{snap}/export").content
        files = zipfile.ZipFile(io.BytesIO(exported))
        manifest = json.loads(files.read("manifest.json"))
        for name, expected in manifest["files"].items():
            assert hashlib.sha256(files.read(name)).hexdigest() == expected
        assert w.question in files.read("notes.md").decode()
    class Offline:
        def fetch(self, request):
            raise AssertionError("Offline reopen/export must never fetch")
    with client(tmp_path, Offline()) as http:
        assert http.get(f"/api/explore/captures/{idea}/{snap}").json() == captured["snapshot"]
        assert http.get(f"/api/explore/captures/{idea}/{snap}/export").content == exported
        assert http.get(f"/api/ideas/{idea}").json()["exploration_snapshots"]


def test_version_conflict_and_stale_or_expired_capture_rejected(tmp_path):
    with client(tmp_path, SuppliedData()) as http:
        w = workspace()
        body = capture_request(http, w)
        save = http.post("/api/explore/workspaces", json={"workspace": w.model_dump(mode="json")})
        assert save.status_code == 200
        assert http.post("/api/explore/workspaces", json={"workspace": w.model_dump(mode="json")}).status_code == 409
        saved = save.json()
        assert http.get(f"/api/explore/workspaces/{w.id}").json()["workspace"] == saved
        edited = dict(body)
        edited["workspace"] = {**body["workspace"], "question": "Changed question"}
        assert http.post("/api/explore/captures", json=edited).status_code == 422
        repository = http.app.state.exploration_repository
        result_path = tmp_path / "workspace/exploration-results" / f"{body['result_ids'][0]}.json"
        result = repository.get_result(body["result_ids"][0]).model_copy(update={"expires_at": NOW - timedelta(seconds=1)})
        result_path.write_text(result.model_dump_json())
        assert http.post("/api/explore/captures", json=body).status_code == 422


def test_legacy_bytes_preserved_and_interrupted_publication_recovers(tmp_path, monkeypatch):
    import kairopsis.exploration_repository as module
    with client(tmp_path, SuppliedData()) as http:
        from test_rebuild_http import capture
        legacy_idea, _ = capture(http)
        old_path = tmp_path / "workspace/ideas" / legacy_idea["id"] / "versions" / legacy_idea["version"] / "idea.json"
        old_bytes = old_path.read_bytes()
        w = workspace()
        saved = http.post("/api/explore/workspaces", json={"workspace": w.model_dump(mode="json")}).json()
        actual_atomic = module.atomic_json
        def interrupt(path, payload):
            if path.name == "current.json":
                raise OSError("Interrupted commit")
            return actual_atomic(path, payload)
        monkeypatch.setattr(module, "atomic_json", interrupt)
        assert http.post("/api/explore/workspaces", json={"workspace": {**saved, "name": "Unpublished edit"}, "expected_version": saved["version"]}).status_code == 503
        assert old_path.read_bytes() == old_bytes
        assert http.get(f"/api/explore/workspaces/{w.id}").json()["workspace"] == saved
    reopened = Repository(tmp_path / "workspace", "mock")
    assert ExplorationRepository(reopened).get(w.id).name == w.name
    assert reopened.get_idea(legacy_idea["id"]).id == legacy_idea["id"]


def test_capture_manifest_completeness(tmp_path):
    with client(tmp_path, SuppliedData()) as http:
        captured = http.post("/api/explore/captures", json=capture_request(http, workspace())).json()
        idea, snap = captured["idea"]["id"], captured["snapshot"]["id"]
        path = tmp_path / "workspace/ideas" / idea / "explorations" / snap / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["files"].pop("notes.md")
        path.write_text(json.dumps(manifest))
        assert http.get(f"/api/explore/captures/{idea}/{snap}").status_code == 422


def test_open_explore_never_starts_screening(tmp_path):
    with client(tmp_path, SuppliedData()) as http:
        assert http.get("/explore").status_code == 200
        assert http.app.state.repository.read_json("refresh") is None


def test_empty_member_selection_and_unretained_fit_rows_rejected(tmp_path):
    with client(tmp_path, SuppliedData()) as http:
        w = workspace(sample=ViewSample(members=()))
        result = http.post("/api/explore/preview", json={"workspace": w.model_dump(mode="json")}).json()["resolved_results"][0]
        assert not result["rows"] and len(result["excluded"]) == 45
        payload = workspace("scatter").model_dump(mode="json")
        payload["views"][0]["options"]["fit_rows"] = [{"id": "fabricated", "values": {"spread": 10, "duration": 2}}]
        assert http.post("/api/explore/preview", json={"workspace": payload}).status_code == 422
        payload["views"][0]["options"] = {"axes": ["invented-field"]}
        assert http.post("/api/explore/preview", json={"workspace": payload}).status_code == 422


def test_superseded_preview_and_late_result_cannot_replace_latest(tmp_path):
    with client(tmp_path, SuppliedData()) as http:
        w = workspace()
        body = capture_request(http, w)
        assert http.post("/api/explore/preview", json={"workspace": w.model_dump(mode="json")}).status_code == 200
        assert http.post("/api/explore/captures", json=body).status_code == 422
        store = http.app.state.exploration_repository
        retained = store.get_result(body["result_ids"][0])
        token_old = store.begin_preview(w.id)
        token_new = store.begin_preview(w.id)
        current = retained.model_copy(update={"id": "new-current"})
        delayed = retained.model_copy(update={"id": "late-old"})
        store.retain_results([current], w.id, token_new)
        store.retain_results([delayed], w.id, token_old)
        pointer = tmp_path / "workspace/exploration-results/current" / f"{w.id}.json"
        assert json.loads(pointer.read_text())["result_ids"] == [current.id]


def test_partial_dependency_failure_preserves_independent_peers(tmp_path):
    from kairopsis.models import DataFailure
    class Partial(SuppliedData):
        def fetch(self, request):
            data = super().fetch(request)
            if request.bindings[0].instrument == "1":
                return data.model_copy(update={"series": (), "outcome": "failed", "failures": (DataFailure(binding_id=request.bindings[0].id, code="missing", message="Explicit fixture failure"),)})
            return data
    with client(tmp_path, Partial()) as http:
        result = http.post("/api/explore/preview", json={"workspace": workspace().model_dump(mode="json")}).json()["resolved_results"][0]
        assert {r["symbol"] for r in result["rows"]} == {"Symbol 0", "Symbol 2"}
        assert any("Explicit fixture failure" in text for text in result["limitations"])
        assert any(b["data"]["outcome"] == "failed" for b in result["input_evidence"]["bindings"].values())


def test_multi_view_capture_publication_failure_leaves_prior_idea_visible(tmp_path, monkeypatch):
    import kairopsis.repository as module
    with client(tmp_path, SuppliedData()) as http:
        w = workspace()
        first = http.post("/api/explore/captures", json=capture_request(http, w)).json()
        first_id = first["idea"]["id"]
        second = w.model_copy(update={"views": (*w.views, w.views[0].model_copy(update={"id": "v2", "family": "distribution", "options": {"axes": ["spread"]}}))})
        body = capture_request(http, second)
        body["idea_id"] = first_id
        atomic = module.atomic_json
        def interrupt(path, payload):
            if path.name == "current.json" and path.parent.name == first_id:
                raise OSError("Interrupted multi-view publication")
            atomic(path, payload)
        monkeypatch.setattr(module, "atomic_json", interrupt)
        assert http.post("/api/explore/captures", json=body).status_code == 503
        assert http.get(f"/api/ideas/{first_id}").json()["idea"] == first["idea"]
        assert len(http.get("/api/ideas").json()) == 1


def test_old_explicit_sample_requires_estimation_history_before_old_start(tmp_path):
    provider = SuppliedData()
    item = collection()[0]
    assert item.binding
    from kairopsis.models import RiskAdjustment
    definition = ResolvedDefinition(id="risk", revision=1, name="Risk", calculation="level", inputs=(item.binding,),
        settings=AnalysisSettings(calculation_contract="input-pipeline-v2", risk_adjustment=RiskAdjustment(method="volatility", lookback_years=3)))
    local = item.model_copy(update={"kind": "analysis", "binding": None, "analysis": definition})
    w = WorkspaceDefinition(collection=(local,), as_of=date(2026, 9, 24), views=(ViewDefinition(measures=(local.id,), sample=ViewSample(start=date(2010, 1, 1))),))
    with client(tmp_path, provider) as http:
        assert http.post("/api/explore/preview", json={"workspace": w.model_dump(mode="json")}).status_code == 200
        assert provider.requests[0].start < date(2007, 1, 1)


def test_interval_percentage_final_axis_units_and_original_endpoint_units(tmp_path):
    w = workspace("ranking", shape="cross_section", sample=ViewSample(interval_start=date(2026, 9, 10), interval_measure="return"))
    with client(tmp_path, SuppliedData()) as http:
        result = http.post("/api/explore/preview", json={"workspace": w.model_dump(mode="json")}).json()["resolved_results"][0]
        assert result["axis_units"] == {"spread": "%", "duration": "%"}
        assert result["statistics"]["paired_endpoints"][0]["unit"] == "bp"
        assert "%" in result["statistics"]["layout"]["yaxis"]["title"]


def test_legacy_only_idea_write_still_parses_in_actual_old_model(tmp_path):
    import subprocess
    import sys
    from types import ModuleType
    old = subprocess.run(["git", "show", "a2b6daa:src/kairopsis/models.py"], capture_output=True, text=True)
    if old.returncode:
        pytest.skip("Historical source baseline unavailable outside Git checkout")
    legacy = ModuleType("kairopsis._baseline_models")
    legacy.__package__ = "kairopsis"
    sys.modules[legacy.__name__] = legacy
    exec(compile(old.stdout, "baseline_models.py", "exec"), legacy.__dict__)
    with client(tmp_path) as http:
        from test_rebuild_http import capture
        idea, _ = capture(http)
        edited = http.patch(f"/api/ideas/{idea['id']}", json={"thought": "Still legacy-compatible"}).json()
        path = tmp_path / "workspace/ideas" / edited["id"] / "versions" / edited["version"] / "idea.json"
        content = path.read_text()
        assert "explorations" not in json.loads(content)
        assert legacy.Idea.model_validate_json(content).thought == "Still legacy-compatible"
        assert json.loads((tmp_path / "workspace/workspace.json").read_text())["schema_version"] == 2


def test_malformed_retained_analysis_dependencies_fail_validation_not_engine(tmp_path):
    item = collection()[0]
    definition = {"id": "bad-pair", "revision": 1, "name": "Malformed pair", "calculation": "difference",
        "inputs": [item.binding.model_dump(mode="json")], "settings": {"calculation_contract": "input-pipeline-v2"}}
    payload = workspace().model_dump(mode="json")
    payload["collection"][0] = {"id": item.id, "symbol": item.symbol, "field": item.field, "kind": "analysis", "analysis": definition}
    with client(tmp_path, SuppliedData()) as http:
        assert http.post("/api/explore/preview", json={"workspace": payload}).status_code == 422
        definition["calculation"] = "level"
        definition["settings"]["risk_adjustment"] = {"method": "beta", "reference_id": "unresolved"}
        assert http.post("/api/explore/preview", json={"workspace": payload}).status_code == 422


def test_explicit_histogram_edges_accepted_and_preserved(tmp_path):
    w = workspace("distribution", options={"axes": ["spread"], "distribution": "histogram", "bin_edges": [0, 10, 30, 50]})
    with client(tmp_path, SuppliedData()) as http:
        result = http.post("/api/explore/preview", json={"workspace": w.model_dump(mode="json")}).json()["resolved_results"][0]
        assert result["statistics"]["groups"][0]["edges"] == [0, 10, 30, 50]


def test_known_future_native_observation_cannot_enter_historical_calculation(tmp_path):
    class FutureNative(SuppliedData):
        def fetch(self, request):
            data = super().fetch(request)
            return data.model_copy(update={"series": tuple(s.model_copy(update={"observations": tuple(
                o.model_copy(update={"observed_on": date(2026, 9, 30)}) if o.date == date(2026, 9, 22) else o
                for o in s.observations)}) for s in data.series)})
    with client(tmp_path, FutureNative()) as http:
        w = workspace()
        w = w.model_copy(update={"as_of": date(2026, 9, 22)})
        result = http.post("/api/explore/preview", json={"workspace": w.model_dump(mode="json")}).json()["resolved_results"][0]
        assert all(row["date"] != "2026-09-22" for row in result["rows"])
        assert any("Native observation after as-of" in reason for row in result["excluded"] for reason in row["reasons"])
        assert any(o["value"] is not None and o["observed_on"] == "2026-09-30" for b in result["input_evidence"]["bindings"].values() for s in b["data"]["series"] for o in s["observations"])


def test_total_return_index_percentage_growth_retains_supplied_semantics(tmp_path):
    binding = SeriesBinding(id="total-return", name="Total return index", source="test", instrument="0", field="index", unit="index points",
        currency="USD", description="Supplied total-return index including reinvested income")
    definition = ResolvedDefinition(id="return", revision=1, name="Index return", calculation="level", inputs=(binding,),
        settings=AnalysisSettings(calculation_contract="input-pipeline-v2", measure="return"))
    item = CollectionItem(id="return", kind="analysis", symbol="Symbol0", field="Index return", analysis=definition)
    w = WorkspaceDefinition(collection=(item,), as_of=date(2026, 9, 24), views=(ViewDefinition(measures=(item.id,)),))
    with client(tmp_path, SuppliedData()) as http:
        captured = http.post("/api/explore/captures", json=capture_request(http, w)).json()["snapshot"]
        retained = captured["results"][0]["measures"][item.id]
        assert retained["unit"] == "%"
        assert "total-return index" in retained["meaning"]
        assert "spread" not in retained["meaning"].casefold()


def test_distribution_rejects_incomparable_unit_overlay(tmp_path):
    with client(tmp_path, SuppliedData()) as http:
        response = http.post("/api/explore/preview", json={"workspace": workspace("distribution").model_dump(mode="json")})
        assert response.status_code == 422
        assert "comparable units" in response.json()["detail"]


def test_numeric_encoding_resolves_unchecked_peer_fields_and_retains_each_definition(tmp_path):
    items = collection()
    encodings = tuple(CollectionItem(id=f"size-{symbol}", symbol=f"Symbol {symbol}", field="index", binding=SeriesBinding(
        id=f"index-{symbol}", name=f"Index {symbol}", source="test", instrument=str(symbol), field="index", unit="index points", currency="USD", params={"symbol": symbol})) for symbol in range(3))
    view = ViewDefinition(family="scatter", shape="cross_section", measures=tuple(i.id for i in items), size_by="size-0", color_by="index")
    w = WorkspaceDefinition(collection=(*items, *encodings), as_of=date(2026, 9, 24), views=(view,))
    with client(tmp_path, SuppliedData()) as http:
        result = http.post("/api/explore/preview", json={"workspace": w.model_dump(mode="json")}).json()["resolved_results"][0]
        assert [row["values"]["index"] for row in result["rows"]] == [15, 30, 45]
        assert result["statistics"]["sizing"]["invalid_rows"] == []
        assert result["statistics"]["size_legend"]["unit"] == "index points"
        assert {key for key in result["measures"] if key.startswith("size-")} == {"size-0", "size-1", "size-2"}
        assert all(row["bindings"]["index"] == f"size-{row['symbol'][-1]}" for row in result["rows"])
