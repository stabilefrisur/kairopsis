"""One supported three-destination application; all evidence passes real persistence."""
import base64
import hashlib
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .catalogue import Catalogue
from .config import Settings
from .fixtures import MockMarketData
from .metapyle_adapter import MetapyleMarketData
from .models import AnalysisDefinition, DisplaySettings, SeriesBinding
from .repository import Repository
from .service import MarketData, Research


class CaptureRequest(BaseModel):
    evaluation_id: str
    display: DisplaySettings = Field(default_factory=DisplaySettings)
    image: str = Field(max_length=16_000_000)
    title: str = Field(default="", max_length=200)
    thought: str = Field(default="", max_length=50000)
    idea_id: str | None = None
    note: str = Field(default="", max_length=50000)
    mode: Literal["saved", "latest", "investigation"] = "investigation"

    def png(self) -> bytes:
        try:
            return base64.b64decode(self.image.removeprefix("data:image/png;base64,"), validate=True)
        except ValueError:
            raise ValueError("Invalid PNG encoding") from None


class IdeaEdit(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    thought: str | None = Field(default=None, max_length=50000)
    shortlisted: bool | None = None
    archived: bool | None = None


class NoteEdit(BaseModel):
    text: str = Field(max_length=50000)


class MonitoringEdit(BaseModel):
    monitored: bool = Field(strict=True)


def create_app(settings: Settings | None = None, market_data: MarketData | None = None,
               clock: Callable[[], datetime] | None = None) -> FastAPI:
    settings = settings or Settings()
    clock = clock or (lambda: datetime.now(timezone.utc))
    repository = Repository(settings.workspace, settings.mode)
    catalogue = Catalogue(repository)
    provider = market_data or (MockMarketData(clock) if settings.mode == "mock" else MetapyleMarketData(settings, clock))
    research = Research(repository, catalogue, provider, clock, settings.timezone)
    app = FastAPI(title="Kairopsis", docs_url=None, redoc_url=None)
    app.state.repository, app.state.research = repository, research
    app.state.settings = settings
    package = Path(__file__).resolve().parent
    templates = Jinja2Templates(directory=package / "templates")
    app.mount("/static", StaticFiles(directory=package / "static"), name="static")

    def asset_url(name: str) -> str:
        version = hashlib.sha256((package / "static" / name).read_bytes()).hexdigest()[:16]
        return f"/static/{name}?v={version}"

    templates.env.globals["asset_url"] = asset_url

    @app.exception_handler(FileNotFoundError)
    async def missing(request: Request, error: FileNotFoundError):
        return JSONResponse(status_code=404, content={"detail": "Record not found; existing evidence preserved"})

    @app.exception_handler(ValueError)
    async def invalid(request: Request, error: ValueError):
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.exception_handler(OSError)
    async def write_failed(request: Request, error: OSError):
        return JSONResponse(status_code=503, content={"detail": "Evidence could not be read/saved. Check writable workspace and free disk space; retry. Export is incomplete."})

    def page(request, name):
        research.first_open()
        return templates.TemplateResponse(request=request, name="app.html", context={"page": name, "mode": settings.mode})

    @app.get("/", response_class=HTMLResponse)
    def root():
        return RedirectResponse("/analyses")

    @app.get("/analyses", response_class=HTMLResponse)
    def analyses_page(request: Request):
        return page(request, "analyses")

    @app.get("/analyses/{key}", response_class=HTMLResponse)
    def chart_page(request: Request, key: str):
        catalogue.resolve(key)
        return page(request, "chart")

    @app.get("/ideas", response_class=HTMLResponse)
    def ideas_page(request: Request):
        return page(request, "ideas")

    @app.get("/ideas/{key}", response_class=HTMLResponse)
    def idea_page(request: Request, key: str):
        repository.get_idea(key)
        return page(request, "idea")

    @app.get("/library", response_class=HTMLResponse)
    def library_page(request: Request):
        return page(request, "library")

    @app.get("/api/analyses")
    def rows(scope: Literal["all", "flagged"] = "flagged", q: str = "", kind: Literal["all", "standalone", "pair"] = "all"):
        research.first_open()
        return research.rows(scope, q, kind)

    @app.post("/api/refresh")
    def refresh():
        return research.refresh()

    @app.get("/api/library")
    def library():
        return catalogue.records()

    @app.post("/api/library/series")
    def save_series(record: SeriesBinding):
        return catalogue.save("series", record)

    @app.post("/api/library/analyses")
    def save_analysis(record: AnalysisDefinition):
        return catalogue.save("analyses", record)

    @app.patch("/api/library/analyses/{key}/monitoring")
    def edit_monitoring(key: str, options: MonitoringEdit):
        return catalogue.set_monitoring(key, options.monitored)

    @app.delete("/api/library/{kind}/{key}")
    def delete_catalogue(kind: Literal["series", "analyses"], key: str):
        catalogue.delete(kind, key)
        return {"ok": True}

    @app.post("/api/analyses/{key}/preview")
    def preview(key: str, options: dict):
        return research.preview(key, options)

    @app.get("/api/evaluations/{key}")
    def evaluation(key: str):
        return repository.get_evaluation(key)

    @app.post("/api/ideas")
    def add_chart(body: CaptureRequest):
        evaluation = repository.get_evaluation(body.evaluation_id)
        return repository.add_chart(evaluation, body.display, body.png(), clock(), body.title, body.thought, body.idea_id, body.note)

    @app.get("/api/ideas")
    def ideas(q: str = "", scope: Literal["active", "shortlist", "archived"] = "active"):
        found = []
        for idea in repository.list_ideas():
            text = " ".join([idea.title, idea.thought, *[n.text for n in idea.notes], *[c.note for c in idea.charts]])
            if q.casefold() not in text.casefold():
                continue
            if idea.archived != (scope == "archived") or (scope == "shortlist" and not idea.shortlisted):
                continue
            found.append({"idea": idea.model_dump(mode="json"), "changes": research.idea_changes(idea)})
        return found

    @app.get("/api/ideas/{key}")
    def idea(key: str):
        result = repository.get_idea(key)
        return {"idea": result.model_dump(mode="json"), "snapshots": {c.id: repository.get_snapshot(key, c.snapshot_id).model_dump(mode="json") for c in result.charts},
                "changes": research.idea_changes(result)}

    @app.patch("/api/ideas/{key}")
    def edit_idea(key: str, body: IdeaEdit):
        return repository.update_idea(key, body.model_dump(exclude_none=True), clock())

    @app.post("/api/ideas/{key}/notes")
    def add_note(key: str, body: NoteEdit):
        now = clock()
        return repository.modify_idea(key, lambda idea: idea.add_note(body.text, now), now)

    @app.patch("/api/ideas/{key}/notes/{note_id}")
    def edit_note(key: str, note_id: str, body: NoteEdit):
        now = clock()
        return repository.modify_idea(key, lambda idea: idea.change_note(note_id, body.text, now), now)

    @app.delete("/api/ideas/{key}/notes/{note_id}")
    def delete_note(key: str, note_id: str):
        now = clock()
        return repository.modify_idea(key, lambda idea: idea.change_note(note_id, None, now), now)

    @app.patch("/api/ideas/{key}/charts/{entry_id}")
    def chart_note(key: str, entry_id: str, body: NoteEdit):
        now = clock()
        return repository.modify_idea(key, lambda idea: idea.annotate_chart(entry_id, body.text, now), now)

    @app.delete("/api/ideas/{key}/charts/{entry_id}")
    def remove_chart(key: str, entry_id: str):
        return repository.modify_idea(key, lambda idea: idea.remove_chart(entry_id), clock())

    def chart_snapshot(key, entry_id):
        result = repository.get_idea(key)
        entry = next((c for c in result.charts if c.id == entry_id), None)
        if not entry:
            raise FileNotFoundError()
        return repository.get_snapshot(key, entry.snapshot_id)

    @app.post("/api/ideas/{key}/charts/{entry_id}/latest")
    def latest(key: str, entry_id: str):
        saved = chart_snapshot(key, entry_id)
        try:
            return {"evaluation": research.evaluate(saved.evaluation.definition)}
        except (ValueError, OSError) as error:
            return {"unavailable": str(error)}

    @app.get("/api/ideas/{key}/snapshots/{snapshot_id}/image")
    def image(key: str, snapshot_id: str):
        return Response(repository.snapshot_image(key, snapshot_id), media_type="image/png")

    @app.post("/api/ideas/{key}/charts/{entry_id}/export")
    def export(key: str, entry_id: str, body: CaptureRequest):
        saved = chart_snapshot(key, entry_id)
        evaluation = saved.evaluation if body.mode == "saved" else repository.get_evaluation(body.evaluation_id)
        if body.mode == "saved" and body.evaluation_id != saved.evaluation.id:
            raise ValueError("Export must match displayed saved evidence")
        if (body.mode == "saved" and evaluation.id != saved.evaluation.id) or (body.mode == "latest" and evaluation.definition != saved.evaluation.definition) or body.mode == "investigation":
            raise ValueError("Export must match displayed saved evidence or its preserved Latest definition")
        if (body.display.years, body.display.view) != (saved.display.years, saved.display.view):
            raise ValueError("Export must preserve displayed settings")
        png = body.png()
        with repository.transaction():
            snapshot = repository.capture(key, evaluation, body.display, png, body.mode, clock())
        return Response(png, media_type="image/png", headers={"X-Snapshot-ID": snapshot.id,
            "Content-Disposition": 'attachment; filename="kairopsis-chart.png"'})

    return app
