"""Private runtime mappings for the public Metapyle raw-request API."""

from pathlib import Path
from typing import Literal

from pydantic import Field, JsonValue, model_validator

from .models import Record


class MetapyleMapping(Record):
    source: str = Field(min_length=1)
    instrument: str = Field(min_length=1)
    field: str = Field(min_length=1)
    metapyle_source: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    request_field: str | None = None
    value_column: str = Field(min_length=1)
    observed_on_column: str | None = None
    path: str | None = None
    params: dict[str, JsonValue] = Field(default_factory=dict)
    params_env: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def distinct_columns(self) -> "MetapyleMapping":
        if self.value_column == self.observed_on_column:
            raise ValueError("Value and actual-observation columns must differ")
        if self.path is not None and not Path(self.path).is_absolute():
            raise ValueError("Private data paths must be absolute")
        return self


class MetapyleConfiguration(Record):
    schema_version: Literal[1] = 1
    mappings: tuple[MetapyleMapping, ...]

    @model_validator(mode="after")
    def unique_bindings(self) -> "MetapyleConfiguration":
        keys = [(item.source, item.instrument, item.field) for item in self.mappings]
        if len(keys) != len(set(keys)):
            raise ValueError("Configure one Metapyle mapping per concrete binding")
        return self


def load_live_configuration(config_dir: Path) -> MetapyleConfiguration:
    return MetapyleConfiguration.model_validate_json((config_dir / "metapyle.json").read_text(encoding="utf-8"))
