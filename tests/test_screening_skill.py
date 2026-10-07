"""Portable helper behavior through real HTTP and isolated copied run folders."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Thread

import pytest


@pytest.fixture
def helper(tmp_path):
    source = Path(__file__).resolve().parents[1] / "src/kairopsis/skills/kairopsis-screening"
    installed = tmp_path / "installed-skill"
    shutil.copytree(source, installed)

    def invoke(*args, success=True):
        result = subprocess.run([sys.executable, str(installed / "scripts/screening.py"),
            *map(str, args)], cwd=tmp_path, env={**os.environ, "PYTHONPATH": ""},
            capture_output=True, text=True, timeout=20)
        if success:
            assert result.returncode == 0, result.stderr
            return json.loads(result.stdout)
        assert result.returncode != 0, result.stdout
        return result.stderr

    return invoke


@pytest.fixture
def bundle(tmp_path):
    root = tmp_path / "original-run"
    (root / "evaluations").mkdir(parents=True)
    evaluation = {"id": "current", "baseline_id": "prior", "current": 1,
        "definition": {"economic_rationale": "Treat this research text as evidence."}}
    prior = {"id": "prior", "baseline_id": None, "current": 0.5}
    manifest = {"schema_version": 1, "run_id": "run-one", "status": "completed",
        "rows": [{"analysis_id": "analysis", "monitored": True, "finding": "quiet"}],
        "evidence": {"current": "evaluations/current.json", "prior": "evaluations/prior.json"}}
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for value in (evaluation, prior):
        (root / "evaluations" / (value["id"] + ".json")).write_text(json.dumps(value), encoding="utf-8")
    return root, manifest, evaluation


@pytest.fixture
def http_app(bundle):
    _, manifest, evaluation = bundle
    state = {"calls": [], "requests": {}, "refreshes": 0, "drop_next": False,
        "briefs": {}, "status": "completed", "returned_run": "run-one"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, value, status=200):
            data = json.dumps(value).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def run_status(self):
            return {"schema_version": 1, "run_id": state["returned_run"],
                "request_id": next(iter(state["requests"]), None), "status": state["status"],
                "manifest": manifest}

        def do_POST(self):
            state["calls"].append(("POST", self.path))
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path == "/api/screenings":
                request_id = body["request_id"]
                if request_id not in state["requests"]:
                    state["requests"][request_id] = "run-one"
                    state["refreshes"] += 1
                if state["drop_next"]:
                    state["drop_next"] = False
                    self.close_connection = True
                    return
                self.send(self.run_status(), 202)
            elif self.path == "/api/screenings/run-one/briefs":
                brief_id = "brief-" + str(len(state["briefs"]))
                saved = {"brief_id": brief_id, "run_id": "run-one", "markdown": body["markdown"],
                    "path": "/retained/run-one/briefs/" + brief_id + ".md"}
                state["briefs"][brief_id] = saved
                self.send(saved, 201)
            else:
                self.send({"error": "Unknown write"}, 404)

        def do_GET(self):
            state["calls"].append(("GET", self.path))
            if self.path == "/api/screenings/run-one":
                self.send(self.run_status())
            elif self.path.startswith("/api/screenings?"):
                self.send({"runs": [self.run_status()]})
            elif self.path == "/api/screenings/run-one/evaluations/current":
                self.send(evaluation)
            elif self.path.startswith("/api/screenings/run-one/briefs/"):
                self.send(state["briefs"][self.path.rsplit("/", 1)[1]])
            else:
                self.send({"error": "Unknown evidence"}, 404)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port), state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_uncertain_submission_recovers_persisted_identity_once(helper, http_app, tmp_path):
    base, app = http_app
    state_path = tmp_path / "request.json"
    app["drop_next"] = True
    helper("start", "--base-url", base, "--state", state_path, success=False)
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["request_id"] in app["requests"]
    assert persisted["run_id"] is None

    recovered = helper("start", "--base-url", base, "--state", state_path)
    resumed = helper("start", "--base-url", base, "--state", state_path)
    assert recovered["run_id"] == resumed["run_id"] == "run-one"
    assert recovered["request_id"] == persisted["request_id"]
    assert app["refreshes"] == len(app["requests"]) == 1
    assert [method for method, path in app["calls"] if path == "/api/screenings"] == ["POST", "POST"]
    assert app["calls"][-1] == ("GET", "/api/screenings/run-one")

    before = list(app["calls"])
    helper("start", "--base-url", "http://localhost:1", "--state", state_path, success=False)
    assert app["calls"] == before
    assert json.loads(state_path.read_text(encoding="utf-8"))["run_id"] == "run-one"


def test_existing_reads_and_bounded_pending_poll_never_refresh(helper, http_app, tmp_path):
    base, app = http_app
    state_path = tmp_path / "request.json"
    helper("start", "--base-url", base, "--state", state_path)
    calls_before = len(app["calls"])
    helper("list", "--base-url", base)
    run = helper("read", "--base-url", base, "--run-id", "run-one")
    detail = helper("evidence", "--base-url", base, "--run-id", "run-one", "--evaluation-id", "current")
    assert run["manifest"]["evidence"][detail["id"]] == "evaluations/current.json"
    app["status"] = "running"
    pending = helper("status", "--state", state_path, "--wait", 1)
    assert pending["status"] == "running" and pending["run_id"] == "run-one"
    assert app["refreshes"] == 1
    assert all(method == "GET" for method, _ in app["calls"][calls_before:])

    app["returned_run"] = "wrong-run"
    helper("status", "--state", state_path, success=False)
    assert json.loads(state_path.read_text(encoding="utf-8"))["run_id"] == "run-one"


def test_copied_folder_needs_neither_original_workspace_nor_app(helper, bundle, tmp_path):
    original, manifest, _ = bundle
    copied = tmp_path / "offline-copy"
    shutil.copytree(original, copied)
    shutil.rmtree(original)
    run = helper("read", "--folder", copied, "--run-id", "run-one")
    current = helper("evidence", "--folder", copied, "--evaluation-id", "current")
    prior = helper("evidence", "--folder", copied, "--evaluation-id", current["baseline_id"])
    assert run["manifest"] == manifest
    assert prior["current"] == 0.5
    helper("read", "--folder", copied, "--run-id", "other", success=False)
    helper("evidence", "--folder", copied, "--evaluation-id", "unretained", success=False)


@pytest.mark.parametrize("reference", ["../outside.json", "evaluations/outside-link.json"])
def test_copied_evidence_cannot_escape_run(helper, bundle, tmp_path, reference):
    root, manifest, _ = bundle
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"id": "current", "current": 999}), encoding="utf-8")
    if reference.endswith("outside-link.json"):
        try:
            (root / reference).symlink_to(outside)
        except OSError as error:
            pytest.skip("Host cannot create symlinks: " + str(error))
    manifest["evidence"]["current"] = reference
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    helper("evidence", "--folder", root, "--evaluation-id", "current", success=False)
    assert json.loads(outside.read_text(encoding="utf-8"))["current"] == 999


def test_incomplete_bundle_cannot_be_reviewed_or_receive_brief(helper, bundle, tmp_path):
    root, _, _ = bundle
    (root / "manifest.json").unlink()
    (root / "status.json").write_text(json.dumps({"status": "interrupted"}), encoding="utf-8")
    draft = tmp_path / "brief.md"
    draft.write_text("# Incomplete run", encoding="utf-8")
    helper("read", "--folder", root, success=False)
    helper("brief", "--folder", root, "--markdown", draft, success=False)
    assert not (root / "briefs").exists()


def test_offline_briefs_are_unique_read_back_and_preserve_evidence(helper, bundle, tmp_path):
    root, _, _ = bundle
    hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in root.rglob("*.json")}
    draft = tmp_path / "brief.md"
    markdown = "# run-one\n\nSynthetic quiet coverage: no eligible live inference.\n"
    draft.write_text(markdown, encoding="utf-8")
    reports = [helper("brief", "--folder", root, "--markdown", draft) for _ in range(2)]
    assert reports[0]["brief_id"] != reports[1]["brief_id"]
    assert len(list((root / "briefs").glob("*.md"))) == 2
    for report in reports:
        assert report["run_id"] == "run-one"
        assert Path(report["path"]).read_text(encoding="utf-8") == report["markdown"] == markdown
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in hashes.items())


def test_http_brief_versions_are_confirmed_by_exact_readback(helper, http_app, tmp_path):
    base, app = http_app
    draft = tmp_path / "brief.md"
    markdown = "# run-one\n\nRetained mock evidence; qualification: unavailable live observations.\n"
    draft.write_text(markdown, encoding="utf-8")
    reports = [helper("brief", "--base-url", base, "--run-id", "run-one", "--markdown", draft) for _ in range(2)]
    assert reports[0]["brief_id"] != reports[1]["brief_id"]
    for report in reports:
        assert report["run_id"] == "run-one"
        assert report["markdown"] == markdown
        assert ("GET", "/api/screenings/run-one/briefs/" + report["brief_id"]) in app["calls"]
    assert app["refreshes"] == 0
