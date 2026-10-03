"""Metapyle alone retrieves live data; unknown upstream provenance stays unknown."""

from collections.abc import Callable
from datetime import date, datetime
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from .config import Settings
from .live_config import load_live_configuration
from .models import DataFailure, DataRequest, DataResponse, Observation, SeriesResult
from .metapyle_catalogue import entries_for, matches_catalogue, validate_catalogue


class InvalidResponse(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


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
    def __init__(self, settings: Settings, clock: Callable[[], datetime]):
        self.settings, self.clock = settings, clock

    def fetch(self, request: DataRequest) -> DataResponse:
        attempted = self.clock()
        def failed(code: str, message: str) -> DataResponse:
            return DataResponse(mode="live", requested=tuple(item.id for item in request.bindings), series=(),
                attempted_at=attempted, completed_at=self.clock(), outcome="failed",
                failures=tuple(DataFailure(binding_id=item.id, code=code, message=message) for item in request.bindings))
        legacy = tuple(item for item in request.bindings if item.catalog_name is None)
        mappings = {}
        if legacy:
            try:
                configuration = load_live_configuration(self.settings.config_dir)
                mappings = {(item.source, item.instrument, item.field): item for item in configuration.mappings}
            except (OSError, ValueError):
                pass  # Missing compatibility mappings fail only the old bindings.
        temporary = TemporaryDirectory(prefix="kairopsis-query-")
        try:
            import metapyle
            self.settings.cache_dir.mkdir(parents=True, exist_ok=True)
            direct = tuple(item for item in request.bindings if item.catalog_name is not None)
            catalog: Path | list = []
            if direct:
                managed = self.settings.workspace / "metapyle.yaml"
                if managed.exists() and matches_catalogue(managed, direct):
                    catalog = managed
                else:
                    # Latest for an old Snapshot queries its captured binding,
                    # even after the active catalogue is edited or deleted.
                    from metapyle.catalog import Catalog
                    catalog = Path(temporary.name) / "captured.yaml"
                    Catalog(entries_for(direct)).to_yaml(catalog)
                    validate_catalogue(catalog)
            client = metapyle.Client(catalog=catalog, cache_path=str(self.settings.cache_dir / "metapyle-live.sqlite"), cache_enabled=False)
        except Exception as error:
            temporary.cleanup()
            return failed("metapyle_unavailable", f"Metapyle public Client API could not initialize ({type(error).__name__}). Check the installed dependency, private setup and cache directory; no alternate source was used.")
        series = []
        failures = []
        try:
            for binding in request.bindings:
                direct_binding = binding.catalog_name is not None
                mapping = mappings.get((binding.source, binding.instrument, binding.field or ""))
                if not direct_binding and mapping is None:
                    failures.append(DataFailure(binding_id=binding.id, code="live_configuration" if not mappings else "unresolved_binding", message="Legacy binding has no matching private configuration. Edit this series in Library with its provider symbol, or restore its legacy metapyle.json configuration."))
                    continue
                params = {}
                if not direct_binding:
                    assert mapping is not None
                    try:
                        params = {**mapping.params, **{key: os.environ[name] for key, name in mapping.params_env.items()}}
                    except KeyError:
                        failures.append(DataFailure(binding_id=binding.id, code="missing_runtime_setting", message="A required private environment setting is missing"))
                        continue
                observed_on_column = mapping.observed_on_column if not direct_binding and mapping else None
                try:
                    if direct_binding:
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
                    provenance=("Metapyle catalogue API" if direct_binding else "Legacy Metapyle raw API") + "; cache bypass requested. Upstream retrieval freshness is unverified. " + native))
        finally:
            try:
                client.close()
            except Exception:
                failures.extend(DataFailure(binding_id=item.id, code="metapyle_close_failed", message="Metapyle could not close its resources cleanly; retrieval remains unverified") for item in request.bindings)
            temporary.cleanup()
        return DataResponse(mode="live", requested=tuple(item.id for item in request.bindings), series=tuple(series), failures=tuple(failures),
                            attempted_at=attempted, completed_at=self.clock(), outcome="partial" if failures and series else "failed" if failures else "unverified")
