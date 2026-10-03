"""Prepare, then verify an installed Windows Python 3.12 wheel offline.

Preparation may install dependencies/browser binaries. Runtime tests use Python
and browser loopback guards, outside the checkout; these are not an OS firewall.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request


def run(command, cwd: Path, env=None) -> str:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if completed.returncode:
        raise RuntimeError(completed.stdout)
    return completed.stdout


def get_json(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)


def main(wheel: Path, output: Path) -> None:
    if sys.platform != "win32":
        raise RuntimeError("This harness requires Windows")
    if output.exists():
        raise RuntimeError("Choose a new output directory; existing acceptance work is preserved")
    output.mkdir(parents=True)
    source = Path(__file__).resolve().parents[2]
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv required for preparation")
    print("Preparing clean Windows Python 3.12 environment", flush=True)
    run([uv, "venv", "--python", "3.12.9", str(output / "venv")], output)
    python = output / "venv/Scripts/python.exe"
    run([uv, "pip", "install", "--python", str(python), str(wheel.resolve())], output)
    runtime_dependencies = run([uv, "pip", "freeze", "--python", str(python)], output)
    (output / "runtime-dependencies.txt").write_text(runtime_dependencies)
    run([uv, "pip", "install", "--python", str(python), "pytest==8.4.2", "httpx==0.28.1", "playwright==1.55.0"], output)
    # This preparation step runs before simulated offline restrictions.
    run([str(python), "-m", "playwright", "install", "chromium"], output)
    tested_dependencies = run([uv, "pip", "freeze", "--python", str(python)], output)
    (output / "tested-dependencies.txt").write_text(tested_dependencies)
    shutil.copytree(source / "tests", output / "tests", ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    shutil.copy(source / "scripts/browser_acceptance.py", output / "browser_acceptance.py")
    shutil.copytree(source / "scripts/acceptance/loopback_guard", output / "guard", ignore=shutil.ignore_patterns("__pycache__"))
    env = {**os.environ, "PYTHONPATH": str(output / "guard"), "KAIROPSIS_NETWORK_AUDIT": str(output / "network.jsonl")}
    for name in list(env):
        if name.startswith("KAIROPSIS_") and name != "KAIROPSIS_NETWORK_AUDIT":
            env.pop(name)
    probe = run([str(python), "-c", "import kairopsis,sys,urllib.request,urllib.error,os; print(sys.version); print(kairopsis.__file__); assert os.environ.get('KAIROPSIS_LOOPBACK_GUARD_ACTIVE') == '1';\ntry: urllib.request.urlopen('https://example.com',timeout=1)\nexcept (PermissionError,urllib.error.URLError) as error:\n assert isinstance(error,PermissionError) or isinstance(error.reason,PermissionError); print('external connection blocked')\nelse: raise AssertionError('guard failed')"], output, env)
    if str(output / "venv").casefold() not in probe.casefold():
        raise RuntimeError("Package did not import from the installed environment")
    print("Installed package confirmed; running isolated tests with loopback guard", flush=True)
    test_output = run([str(python), "-m", "pytest", str(output / "tests"), "-q"], output, env)
    (output / "tests.txt").write_text(test_output)
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    command = [str(output / "venv/Scripts/kairopsis.exe"), "--mode", "mock", "--port", str(port),
        "--workspace", str(output / "workspace"), "--config-dir", str(output / "config"),
        "--cache-dir", str(output / "cache"), "--log-dir", str(output / "logs")]
    process = None
    server_log = (output / "server.txt").open("w")
    def start():
        process = subprocess.Popen(command, cwd=output, env=env, stdout=server_log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Installed server failed; inspect server.txt")
            try:
                get_json(url + "/api/library")
                return process
            except (OSError, ValueError):
                time.sleep(.2)
        process.terminate()
        process.wait(timeout=10)
        raise RuntimeError("Installed server startup timed out")
    try:
        process = start()
        print("Running browser journey on installed wheel", flush=True)
        browser_output = run([str(python), str(output / "browser_acceptance.py"), "--url", url,
                              "--output", str(output / "browser")], output, env)
        browser = json.loads(browser_output)
        process.terminate()
        process.wait(timeout=10)
        process = start()
        idea = get_json(url + "/api/ideas/" + browser["idea_id"])
        assert len(idea["idea"]["charts"]) == 1
        assert idea["idea"]["shortlisted"] and not idea["idea"]["archived"]
        assert idea["idea"]["notes"][0]["text"] == "Edited dated note"
        with urllib.request.urlopen(url + f"/api/ideas/{browser['idea_id']}/snapshots/{browser['initial_snapshot_id']}/image") as response:
            assert hashlib.sha256(response.read()).hexdigest() == browser["initial_image_sha256"]
        record = {"platform": sys.platform, "python_probe": probe, "wheel": wheel.name,
            "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(), "runtime_dependencies": runtime_dependencies.splitlines(),
            "tested_dependencies": tested_dependencies.splitlines(),
            "test_result": test_output, "browser": browser, "restart": "passed; exact original Snapshot and notes/shortlist survived",
            "restriction": "Python audit hook and Playwright network guards; loopback only; not OS firewall or provider-environment evidence",
            "passed": True}
        (output / "result.json").write_text(json.dumps(record, indent=2))
        print(json.dumps(record, indent=2))
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        server_log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    main(args.wheel.resolve(), args.output.resolve())
