"""Relative-value idea generation powered by metapyle."""


def main() -> None:
    """Launch the installed application without runtime dependency resolution."""
    import logging
    from logging.handlers import RotatingFileHandler

    import uvicorn

    from .app import create_app
    from .config import load_settings

    settings = load_settings()
    for path in (settings.config_dir, settings.cache_dir, settings.log_dir):
        path.mkdir(parents=True, exist_ok=True)
    logging.getLogger("kairopsis").addHandler(RotatingFileHandler(
        settings.log_dir / "kairopsis.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8"
    ))
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)
