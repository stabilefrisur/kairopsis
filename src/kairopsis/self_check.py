"""Installed-package smoke checks using temporary mock data and in-process HTTP."""

import asyncio
import base64
from datetime import datetime, timezone
from html.parser import HTMLParser
from importlib.metadata import version
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
import zlib

from starlette.types import ASGIApp, Message


class CheckFailed(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailed(message)


class Assets(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: set[str] = set()

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in {"src", "href"} and value and value.startswith("/static/"):
                self.urls.add(value)


async def request(app: ASGIApp, method: str, url: str, body: dict | None = None) -> bytes:
    """Exercise the real ASGI routes without a socket or optional test client."""
    target = urlsplit(url)
    payload = json.dumps(body).encode() if body is not None else b""
    messages: list[Message] = []
    delivered = False

    async def receive() -> Message:
        nonlocal delivered
        if not delivered:
            delivered = True
            return {"type": "http.request", "body": payload, "more_body": False}
        await asyncio.Event().wait()
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        messages.append(message)

    scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
             "http_version": "1.1", "method": method, "scheme": "http",
             "path": target.path, "raw_path": target.path.encode(),
             "query_string": target.query.encode(), "root_path": "",
             "headers": [(b"host", b"127.0.0.1"), (b"content-type", b"application/json")],
             "client": ("127.0.0.1", 0), "server": ("127.0.0.1", 0)}
    await asyncio.wait_for(app(scope, receive, send), timeout=30)
    statuses = [m["status"] for m in messages if m["type"] == "http.response.start"]
    require(statuses == [200], f"{method} {target.path}: expected HTTP 200, got {statuses}")
    return b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")


def sample_png() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        content = kind + data
        return struct.pack(">I", len(data)) + content + struct.pack(">I", zlib.crc32(content))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\0\xff\xff\xff")) + chunk(b"IEND", b""))


async def check(root: Path, completed: list[str]) -> None:
    from .app import create_app
    from .config import Settings

    # Never load user configuration or inherit KAIROPSIS_* paths/mode.
    settings = Settings(workspace=root / "workspace", config_dir=root / "config",
                        cache_dir=root / "cache", log_dir=root / "logs",
                        mode="mock", timezone="UTC")
    clock = lambda: datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
    app = create_app(settings, clock=clock)
    package = Path(__file__).resolve().parent
    resources = ("docs/agent-setup.md", "docs/human-guide.md", "docs/explore.md",
                 "skills/kairopsis-analysis/SKILL.md", "skills/kairopsis-screening/SKILL.md")
    for resource in resources:
        require((package / resource).is_file(), f"Missing packaged resource: {resource}")
    completed.append("bundled guides and skills")

    async with app.router.lifespan_context(app):
        # Finish the initial refresh synchronously so opening a page cannot
        # leave a background writer racing temporary-directory cleanup.
        await request(app, "POST", "/api/refresh")
        completed.append("mock refresh")
        assets = Assets()
        for path in ("/analyses", "/explore", "/ideas", "/library", "/analyses/usd-ig"):
            html = await request(app, "GET", path)
            require(b"<html" in html.lower(), f"{path}: missing HTML page")
            assets.feed(html.decode())
        completed.append("mock pages")
        require(bool(assets.urls), "Pages reference no local assets")
        for url in sorted(assets.urls):
            require(bool(await request(app, "GET", url)), f"Empty asset: {url}")
        completed.append("page assets")

        library = await request(app, "GET", "/api/library")
        evaluation = json.loads(await request(app, "POST", "/api/analyses/usd-ig/preview",
                                             {"history_years": 1}))
        require(evaluation["data"]["outcome"] == "synthetic", "Expected mock observations")
        require(evaluation["current"] is not None and evaluation["eligible"],
                "Mock preview produced no eligible current value")
        require(await request(app, "GET", "/api/library") == library,
                "Preview changed saved Library definitions")
        completed.append("mock calculation and preview isolation")

        png = sample_png()
        image = "data:image/png;base64," + base64.b64encode(png).decode()
        display = {"years": 1, "view": "analysis"}
        idea = json.loads(await request(app, "POST", "/api/ideas", {
            "evaluation_id": evaluation["id"], "display": display, "image": image,
            "title": "Installation self-check"}))
        idea_path = f"/api/ideas/{idea['id']}"
        saved = json.loads(await request(app, "GET", idea_path))
        completed.append("evidence save")

    reopened = create_app(settings, clock=clock)
    async with reopened.router.lifespan_context(reopened):
        retained = json.loads(await request(reopened, "GET", idea_path))
        require(retained["idea"] == saved["idea"] and retained["snapshots"] == saved["snapshots"],
                "Saved evidence changed after reopening the application")
        chart = idea["charts"][0]
        exported = await request(reopened, "POST", f"{idea_path}/charts/{chart['id']}/export", {
            "evaluation_id": evaluation["id"], "display": display, "image": image, "mode": "saved"})
        require(exported == png, "Export did not preserve the supplied image")
        completed.append("evidence reopen and export")


def main() -> int:
    completed: list[str] = []
    report = {"status": "failed", "checks": completed, "live_data_checked": False,
              "package": str(Path(__file__).resolve().parent)}
    try:
        report["version"] = version("kairopsis")
        with TemporaryDirectory(prefix="kairopsis-self-check-") as directory:
            asyncio.run(check(Path(directory).resolve(), completed))
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        print(json.dumps(report, indent=2))
        return 1
    report["status"] = "passed"
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    import argparse
    argparse.ArgumentParser(description=__doc__).parse_args()
    raise SystemExit(main())
