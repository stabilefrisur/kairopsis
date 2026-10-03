"""User-writable paths and launch settings; never infer paths from cwd."""

import argparse
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from platformdirs import user_cache_path, user_config_path, user_data_path, user_log_path


@dataclass(frozen=True)
class Settings:
    workspace: Path = field(default_factory=lambda: user_data_path("Kairopsis", appauthor=False) / "mock")
    config_dir: Path = field(default_factory=lambda: user_config_path("Kairopsis", appauthor=False))
    cache_dir: Path = field(default_factory=lambda: user_cache_path("Kairopsis", appauthor=False))
    log_dir: Path = field(default_factory=lambda: user_log_path("Kairopsis", appauthor=False))
    mode: Literal["mock", "live"] = "mock"
    host: str = "127.0.0.1"
    port: int = 8765
    timezone: str = "Europe/London"

    def __post_init__(self) -> None:
        package = Path(__file__).resolve().parent
        for name in ("workspace", "config_dir", "cache_dir", "log_dir"):
            path = Path(getattr(self, name)).expanduser()
            if not path.is_absolute():
                raise ValueError(f"{name} must be an absolute path, independent of the working directory")
            path = path.resolve()
            if path == package or package in path.parents:
                raise ValueError(f"{name} must be outside the installed package")
            object.__setattr__(self, name, path)
        if self.mode not in ("mock", "live"):
            raise ValueError("mode must be mock or live")
        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("timezone must be an available IANA timezone, for example Europe/London") from None


def load_settings(argv: list[str] | None = None) -> Settings:
    parser = argparse.ArgumentParser(description="Local Kairopsis research dashboard")
    parser.add_argument("--config", type=Path, help="Absolute path to an optional TOML configuration")
    parser.add_argument("--mode", choices=("mock", "live"))
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--timezone")
    for name in ("workspace", "config-dir", "cache-dir", "log-dir"):
        parser.add_argument(f"--{name}", type=Path)
    args = vars(parser.parse_args(argv))
    config = args.pop("config") or os.environ.get("KAIROPSIS_CONFIG")
    values: dict = {}
    if config:
        config_path = Path(config).expanduser()
        if not config_path.is_absolute():
            parser.error("--config must be an absolute path")
        with config_path.open("rb") as stream:
            values = tomllib.load(stream).get("kairopsis", {})
    for name in args:
        environment = os.environ.get(f"KAIROPSIS_{name.upper()}")
        if environment is not None:
            values[name] = int(environment) if name == "port" else environment
        if args[name] is not None:
            values[name] = args[name]
    if "workspace" not in values:
        values["workspace"] = user_data_path("Kairopsis", appauthor=False) / values.get("mode", "mock")
    try:
        return Settings(**values)
    except (TypeError, ValueError) as error:
        parser.error(str(error))
