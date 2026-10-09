"""Throwaway Explore UI: three layouts, synthetic data, memory-only actions.

Run: .venv/bin/python scripts/explore_prototype.py
Normal Kairopsis never registers this route or its variant switcher.
"""
from pathlib import Path
import argparse

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn


def create_prototype_app():
    package = Path(__file__).resolve().parents[1] / "src" / "kairopsis"
    app = FastAPI(title="Kairopsis Explore prototype", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=package / "static"), name="static")
    templates = Jinja2Templates(directory=package / "templates")

    @app.get("/")
    def root():
        return RedirectResponse("/prototype/explore?variant=A")

    @app.get("/prototype/explore")
    def explore(request: Request):
        return templates.TemplateResponse(request=request, name="explore-prototype.html", context={})

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    uvicorn.run(create_prototype_app(), host="127.0.0.1", port=args.port)
