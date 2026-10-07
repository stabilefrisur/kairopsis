"""Metapyle alone retrieves live data; unknown upstream provenance stays unknown."""

from collections.abc import Callable
from datetime import date, datetime
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from .config import Settings
from .live_config import MetapyleMapping, load_live_configuration
from .models import DataFailure, DataRequest, DataResponse, Observation, SeriesBinding, SeriesResult
from .metapyle_catalogue import entries_for, validate_catalogue


class InvalidResponse(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


RAW_SOURCES = {"bloomberg", "gsquant", "localfile", "macrobond"}


def _raw_column(binding: SeriesBinding, mapping: MetapyleMapping | None) -> str:
    if binding.source in ("bloomberg", "gsquant"):
        if not binding.field:
            raise InvalidResponse("missing_field", "Choose the provider field to preview")
        return f"{binding.instrument}::{binding.field}"
    if binding.source in ("localfile", "macrobond"):
        return binding.instrument
    if mapping and (mapping.metapyle_source, mapping.symbol, mapping.request_field) == (
            binding.source, binding.instrument, binding.field):
        return mapping.value_column
    raise InvalidResponse("unresolved_field", "This registered source needs an explicit value-column mapping in private metapyle.json configuration")


def _observations(frame: Any, value_column: str, request: DataRequest, observed_on_column: str | None = None) -> tuple[Observation, ...]:
    if not isinstance(frame, pd.DataFrame) or not isinstance(frame.index, pd.DatetimeIndex):
        raise InvalidResponse("invalid_response", "Metapyle did not return a DataFrame with dated rows")
    if frame.columns.has_duplicates or frame.index.hasnans:
        raise InvalidResponse("invalid_response", "Metapyle returned duplicate fields or invalid row dates")
    if value_column not in frame.columns:
        raise InvalidResponse("missing_field", "Metapyle omitted the explicitly selected value field; no other column was substituted")
    observations = []
    days: set[date] = set()
    for stamp, row in frame.sort_index().iterrows():
        day = stamp.date()
        if not request.start <= day <= request.end:
            continue
        if day in days:
            raise InvalidResponse("invalid_response", "Multiple supplied rows share one calendar date; configure a daily field explicitly")
        days.add(day)
        value = row[value_column]
        observed = None
        if observed_on_column and observed_on_column in frame.columns:
            actual = row[observed_on_column]
            if isinstance(actual, (str, date, datetime)) and not pd.isna(actual):
                try:
                    parsed = pd.Timestamp(actual)
                    observed = None if pd.isna(parsed) else parsed.date()
                except (ValueError, TypeError, OverflowError):
                    pass
        try:
            value = None if pd.isna(value) else float(value)
        except (ValueError, TypeError, OverflowError):
            raise InvalidResponse("invalid_response", "The selected Metapyle field contains a nonnumeric value") from None
        observations.append(Observation(date=day, value=value, observed_on=observed))
    if not observations:
        raise InvalidResponse("no_data", "Metapyle returned no observations in the requested range")
    return tuple(observations)


class MetapyleMarketData:
    def __init__(self, settings: Settings, clock: Callable[[], datetime], *, ad_hoc: bool = False,
                 legacy_bindings: Callable[[], tuple[SeriesBinding, ...]] | None = None):
        self.settings, self.clock = settings, clock
        self.ad_hoc = ad_hoc
        self.legacy_bindings = legacy_bindings

    def fetch(self, request: DataRequest) -> DataResponse:
        attempted = self.clock()
        def failed(code: str, message: str) -> DataResponse:
            return DataResponse(mode="live", requested=tuple(item.id for item in request.bindings), series=(),
                attempted_at=attempted, completed_at=self.clock(), outcome="failed",
                failures=tuple(DataFailure(binding_id=item.id, code=code, message=message) for item in request.bindings))
        saved_legacy = {item.id: item for item in self.legacy_bindings()} if self.ad_hoc and self.legacy_bindings else {}
        def uses_legacy_mapping(item: SeriesBinding) -> bool:
            old = saved_legacy.get(item.id)
            return old is not None and old.catalog_name is None and all(getattr(item, key) == getattr(old, key)
                for key in ("source", "instrument", "field", "path", "params"))
        legacy = tuple(item for item in request.bindings if item.source not in RAW_SOURCES
            or uses_legacy_mapping(item) or not self.ad_hoc and item.catalog_name is None)
        mappings = {}
        if legacy:
            try:
                configuration = load_live_configuration(self.settings.config_dir)
                mappings = {(item.source, item.instrument, item.field): item for item in configuration.mappings}
            except (OSError, ValueError):
                pass  # Missing compatibility mappings fail only the old bindings.
        temporary = None if self.ad_hoc else TemporaryDirectory(prefix="kairopsis-query-")
        try:
            import metapyle
            if not self.ad_hoc:
                self.settings.cache_dir.mkdir(parents=True, exist_ok=True)
            direct = tuple(item for item in request.bindings if item.catalog_name is not None)
            catalog: Path | list = []
            if direct and not self.ad_hoc:
                # A mutable Library projection could change after matching it
                # and before Client loads it. Every request uses captured bindings.
                from metapyle.catalog import Catalog
                assert temporary is not None
                catalog = Path(temporary.name) / "metapyle.yaml"
                Catalog(entries_for(direct)).to_yaml(catalog)
                validate_catalogue(catalog)
            client = (metapyle.Client(catalog=[], cache_enabled=False) if self.ad_hoc else
                metapyle.Client(catalog=catalog, cache_path=str(self.settings.cache_dir / "metapyle-live.sqlite"), cache_enabled=False))
        except Exception as error:
            if temporary is not None:
                temporary.cleanup()
            return failed("metapyle_unavailable", f"Metapyle public Client API could not initialize ({type(error).__name__}). Check the installed dependency, private setup and cache directory; no alternate source was used.")
        series = []
        failures = []
        try:
            for binding in request.bindings:
                direct_binding = not self.ad_hoc and binding.catalog_name is not None
                mapping = mappings.get((binding.source, binding.instrument, binding.field or ""))
                raw_binding = self.ad_hoc and not uses_legacy_mapping(binding)
                if not direct_binding and not raw_binding and mapping is None:
                    failures.append(DataFailure(binding_id=binding.id, code="live_configuration" if not mappings else "unresolved_binding", message="Legacy binding has no matching private configuration. Edit this series in Library with its provider symbol, or restore its legacy metapyle.json configuration."))
                    continue
                params = dict(binding.params) if raw_binding else {}
                if not direct_binding and not raw_binding:
                    assert mapping is not None
                    try:
                        params = {**mapping.params, **{key: os.environ[name] for key, name in mapping.params_env.items()}}
                    except KeyError:
                        failures.append(DataFailure(binding_id=binding.id, code="missing_runtime_setting", message="A required private environment setting is missing"))
                        continue
                observed_on_column = mapping.observed_on_column if not direct_binding and mapping else None
                try:
                    if raw_binding:
                        value_column = _raw_column(binding, mapping)
                        if binding.path is not None and not Path(binding.path).is_absolute():
                            raise InvalidResponse("invalid_path", "Data file paths must be absolute")
                        frame = client.get_raw(source=binding.source, symbol=binding.instrument,
                            start=request.start.isoformat(), end=request.end.isoformat(), field=binding.field,
                            path=binding.path, params=params, use_cache=False)
                    elif direct_binding:
                        assert binding.catalog_name is not None
                        frame = client.get([binding.catalog_name], request.start.isoformat(), request.end.isoformat(), use_cache=False)
                        value_column = binding.catalog_name
                    else:
                        assert mapping is not None
                        frame = client.get_raw(mapping.metapyle_source, mapping.symbol, request.start.isoformat(), request.end.isoformat(),
                            field=mapping.request_field, path=mapping.path, params=params, use_cache=False)
                        value_column = mapping.value_column
                    observations = _observations(frame, value_column, request, observed_on_column)
                except InvalidResponse as error:
                    failures.append(DataFailure(binding_id=binding.id, code=error.code, message=str(error)))
                    continue
                except Exception as error:
                    failures.append(DataFailure(binding_id=binding.id, code="source_error", message=f"Metapyle retrieval failed ({type(error).__name__}); check private provider setup. No alternate source was used."))
                    continue
                native = "Native observation dates are unverified; row dates are not observation provenance."
                if observed_on_column:
                    unknown = sum(point.observed_on is None for point in observations)
                    native = ("Configured actual-observation column was absent; all native dates remain unknown." if observed_on_column not in frame.columns
                              else f"Actual dates use the explicitly configured upstream column; {unknown} of {len(observations)} rows have missing or invalid native dates and remain unknown.")
                series.append(SeriesResult(binding=binding, observations=observations,
                    provenance=("Metapyle ad-hoc raw API" if raw_binding else "Metapyle catalogue API" if direct_binding else "Legacy Metapyle raw API") + "; cache bypass requested. Upstream retrieval freshness is unverified. " + native))
        finally:
            try:
                client.close()
            except Exception:
                failures.extend(DataFailure(binding_id=item.id, code="metapyle_close_failed", message="Metapyle could not close its resources cleanly; retrieval remains unverified") for item in request.bindings)
            if temporary is not None:
                temporary.cleanup()
        return DataResponse(mode="live", requested=tuple(item.id for item in request.bindings), series=tuple(series), failures=tuple(failures),
                            attempted_at=attempted, completed_at=self.clock(), outcome="partial" if failures and series else "failed" if failures else "unverified")
