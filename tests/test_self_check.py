"""Installed smoke checks must isolate research and report real failures."""

import json
import socket
from tempfile import TemporaryDirectory

import pytest
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

from kairopsis import self_check
from kairopsis.config import load_settings
from kairopsis.repository import Repository


def test_cli_check_ignores_live_environment_and_removes_its_temporary_state(tmp_path, monkeypatch, capsys):
    existing = tmp_path / "existing research"
    existing.mkdir()
    sentinel = existing / "keep.json"
    sentinel.write_bytes(b"existing research")
    monkeypatch.setenv("KAIROPSIS_MODE", "live")
    monkeypatch.setenv("KAIROPSIS_WORKSPACE", str(existing))
    monkeypatch.setenv("KAIROPSIS_CONFIG", str(existing / "missing.toml"))
    monkeypatch.setenv("KAIROPSIS_PORT", "not a port")
    monkeypatch.setattr(self_check, "TemporaryDirectory",
                        lambda **kwargs: TemporaryDirectory(dir=tmp_path, **kwargs))

    def forbidden(*args, **kwargs):
        pytest.fail("Self-check attempted network or live access")

    import kairopsis.app
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(kairopsis.app, "MetapyleMarketData", forbidden)
    with pytest.raises(SystemExit) as stopped:
        load_settings(["--self-check"])
    assert stopped.value.code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "passed" and not report["live_data_checked"]
    assert "evidence reopen and export" in report["checks"]
    assert list(tmp_path.iterdir()) == [existing]
    assert list(existing.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"existing research"


@pytest.mark.parametrize("fault", ["asset", "save"])
def test_check_fails_on_broken_installed_assets_or_persistence(fault, monkeypatch, capsys):
    if fault == "asset":
        async def broken_asset(*args, **kwargs):
            return Response(status_code=404)
        monkeypatch.setattr(StaticFiles, "get_response", broken_asset)
    else:
        def broken_save(*args, **kwargs):
            raise OSError("Simulated write failure")
        monkeypatch.setattr(Repository, "add_chart", broken_save)
    assert self_check.main() == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "failed"
    assert "expected HTTP 200" in report["error"]
    assert "evidence reopen and export" not in report["checks"]


def test_self_check_rejects_launch_options_instead_of_using_a_real_workspace(tmp_path, monkeypatch):
    def forbidden():
        pytest.fail("Checks must not start with ambiguous launch settings")
    monkeypatch.setattr(self_check, "main", forbidden)
    with pytest.raises(SystemExit) as stopped:
        load_settings(["--self-check", "--workspace", str(tmp_path)])
    assert stopped.value.code == 2
    assert list(tmp_path.iterdir()) == []
