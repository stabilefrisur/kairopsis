"""Resolved evaluations and dated refresh publication, independent of UI/storage schemas."""
from collections.abc import Callable
from datetime import datetime
from threading import Lock, Thread
from typing import Protocol
from zoneinfo import ZoneInfo

from .analytics import evaluate
from .periods import Period, period_start, retrieval_start
from .catalogue import Catalogue, resolve_definition
from .evaluation_comparison import compare
from .fixtures import MOCK_AS_OF
from .models import AnalysisDefinition, AnalysisSettings, DataRequest, DataResponse, Evaluation, ResolvedDefinition, SeriesBinding, identity
from .repository import Repository
from .screenings import Screenings, coverage


class MarketData(Protocol):
    def fetch(self, request: DataRequest) -> DataResponse: ...


class Research:
    def __init__(self, repository: Repository, catalogue: Catalogue, provider: MarketData,
                 clock: Callable[[], datetime], timezone: str, preview_provider: MarketData | None = None):
        self.repository, self.catalogue, self.provider, self.clock = repository, catalogue, provider, clock
        self.preview_provider = preview_provider or provider
        self.timezone = ZoneInfo(timezone)
        self.refresh_lock = Lock()
        self.running = False
        self.screenings = Screenings(repository, timezone)

    def preview_series(self, binding: SeriesBinding, period: Period) -> dict:
        end = MOCK_AS_OF if self.repository.mode == "mock" else self.clock().astimezone(self.timezone).date()
        request = DataRequest(bindings=(binding,), start=period_start(end, period), end=end)
        data = self.preview_provider.fetch(request)
        if data.mode != self.repository.mode:
            raise ValueError("Provider mode does not match workspace")
        return {"request": request, "data": data}

    def evaluate(self, definition: ResolvedDefinition) -> Evaluation:
        result = self.compute(definition, self.provider)
        self.repository.save_evaluation(result)
        return result

    def compute(self, definition: ResolvedDefinition, provider: MarketData, display_period: Period = 5) -> Evaluation:
        request, data = self.retrieve(definition, provider, display_period)
        return evaluate(definition, data, request, self.clock())

    def retrieve(self, definition: ResolvedDefinition, provider: MarketData, display_period: Period = 5) -> tuple[DataRequest, DataResponse]:
        end = MOCK_AS_OF if self.repository.mode == "mock" else self.clock().astimezone(self.timezone).date()
        start = retrieval_start(end, (definition.settings.history_years, definition.settings.fit_years, 5, display_period),
            (r.lookback_years for r in definition.settings.adjustments(len(definition.inputs)) if r.method != "none"),
            definition.settings.needs_moves(len(definition.inputs)))
        request = DataRequest(bindings=(*definition.inputs, *definition.references),
            start=start, end=end)
        data = provider.fetch(request)
        if data.mode != self.repository.mode:
            raise ValueError("Provider mode does not match workspace")
        return request, data

    def preview_analysis(self, analysis: AnalysisDefinition, drafts: tuple[SeriesBinding, ...], period: Period) -> Evaluation:
        return self.compute(self.catalogue.resolve_draft(analysis, drafts), self.preview_provider, period)

    def preview(self, key: str, settings: dict) -> Evaluation:
        definition = self.catalogue.resolve(key)
        if "analysis" in settings:
            draft = AnalysisDefinition.model_validate(settings["analysis"])
            if draft.id != key or draft.revision != definition.revision:
                raise ValueError("Preview must retain this Analysis identity and current revision")
            resolved = self.catalogue.resolve_draft(draft, ())
            result = self.compute(resolved, self.preview_provider)
            self.repository.save_evaluation(result)
            return result
        options = AnalysisSettings.model_validate({**definition.settings.model_dump(), **settings})
        return self.evaluate(self.catalogue.resolve(key, options))

    def start_screening(self, request_id: str) -> dict:
        status, created = self.screenings.create("agent", request_id, self.clock())
        if created:
            self.running = True
            Thread(target=self._background_refresh, kwargs={"run_id": status["run_id"]}, daemon=True).start()
        return status

    def _background_refresh(self, **options) -> None:
        try:
            self.refresh(**options)
        except Exception:
            # Durable failed status is set by refresh; do not expose provider details.
            pass

    def refresh(self, manual: bool = True, run_id: str | None = None) -> dict:
        with self.refresh_lock:
            self.running = True
            try:
                state = self.repository.read_json("refresh", {"results": {}, "failures": {}})
                now = self.clock()
                day = now.astimezone(self.timezone).date().isoformat()
                if not manual and state.get("day") == day:
                    return state
                if run_id is None:
                    run_id = self.screenings.create("manual" if manual else "daily", None, now)[0]["run_id"]
                # Freeze all research context in one short transaction. No provider
                # retrieval holds this lock; edits become inputs to a later run.
                with self.repository.transaction():
                    records = self.catalogue.records()
                    series = {s["id"]: SeriesBinding.model_validate(s) for s in records["series"]}
                    analyses = [AnalysisDefinition.model_validate(a) for a in records["analyses"]]
                    definitions = {a.id: resolve_definition(a, series) for a in analyses}
                    idea_refs: dict[str, list[dict]] = {}
                    for idea in self.repository.list_ideas():
                        matching: dict[str, list[str]] = {}
                        for chart in idea.charts:
                            key = self.repository.get_snapshot(idea.id, chart.snapshot_id).evaluation.definition.id
                            matching.setdefault(key, []).append(chart.id)
                        for key, chart_ids in matching.items():
                            idea_refs.setdefault(key, []).append({"id": idea.id, "title": idea.title,
                                "version": idea.version, "chart_ids": chart_ids})
                results, failures = dict(state["results"]), {}
                active = set(definitions)
                results = {k: v for k, v in results.items() if k in active}
                rows: list[dict] = []
                evidence: dict[str, str] = {}
                membership = {a.id: a.monitored for a in analyses}
                for key in sorted(active):
                    definition = definitions[key]
                    previous = self.repository.get_evaluation(results[key]) if key in results else None
                    request, data, current = None, None, None
                    attempted = self.clock().isoformat()
                    try:
                        request, data = self.retrieve(definition, self.provider)
                        current = evaluate(definition, data, request, self.clock())
                        current = compare(current, previous).model_copy(update={"id": identity()})
                        self.repository.save_evaluation(current)
                        results[key] = current.id
                    except (OSError, ValueError) as error:
                        failures[key] = str(error)
                    except Exception as error:
                        # External provider details may include secrets. Expose type only.
                        failures[key] = f"Retrieval failed ({type(error).__name__}); retained dated evidence"
                    rows.append(self.screenings.capture_row(run_id, definition, membership[key], idea_refs.get(key, []),
                        current, previous, failures.get(key), request, data, attempted, self.clock().isoformat(), evidence))
                state = {"day": day, "attempted_at": now.isoformat(), "completed_at": self.clock().isoformat(),
                         "results": results, "failures": failures, "screening_run_id": run_id,
                         "screening_path": str(self.screenings.folder(run_id).resolve())}
                metadata = self.screenings.get(run_id)
                manifest = {**{k: v for k, v in metadata.items() if k not in ("path", "manifest_path")},
                    "status": "completed", "attempted_at": now.isoformat(), "completed_at": state["completed_at"],
                    "universe_count": len(rows), "monitored_count": sum(membership.values()),
                    "coverage": coverage(rows), "rows": rows, "evidence": evidence}
                self.screenings.publish(run_id, manifest, state)
                return state
            except Exception:
                if run_id is not None:
                    self.screenings.fail(run_id, self.clock())
                raise
            finally:
                self.running = False

    def first_open(self) -> None:
        state = self.repository.read_json("refresh", {})
        day = self.clock().astimezone(self.timezone).date().isoformat()
        if state.get("day") != day and not self.running:
            self.running = True
            Thread(target=self._background_refresh, kwargs={"manual": False}, daemon=True).start()

    def rows(self, scope: str, query: str, kind: str) -> dict:
        state = self.repository.read_json("refresh", {"results": {}, "failures": {}})
        rows = []
        for analysis in self.catalogue.records()["analyses"]:
            name = analysis["name"]
            definition = self.catalogue.resolve(analysis["id"])
            text = " ".join([name, *[f"{s.name} {s.source} {s.field}" for s in definition.inputs]])
            analysis_type = "standalone" if definition.calculation == "level" else "pair"
            if query.casefold() not in text.casefold() or kind not in ("all", analysis_type):
                continue
            evaluation = self.repository.get_evaluation(state["results"][analysis["id"]]) if analysis["id"] in state["results"] else None
            failure = state["failures"].get(analysis["id"])
            compatible = bool(evaluation and evaluation.definition == definition)
            flagged = bool(analysis["monitored"] and compatible and evaluation and evaluation.eligible and evaluation.reasons and
                           evaluation.finding in ("condition", "new", "changed") and not failure)
            if scope == "flagged" and not flagged:
                continue
            summary = evaluation.model_dump(mode="json", exclude={"points", "data", "request"}) if evaluation else None
            rows.append({"analysis": analysis, "evaluation": summary,
                         "failure": failure, "compatible": compatible, "flagged": flagged})
        order = {"new": 0, "changed": 1, "condition": 2}
        rows.sort(key=lambda r: (order.get(r["evaluation"]["finding"], 3) if r["evaluation"] and r["flagged"] else 4,
                                r["analysis"]["name"].casefold(), r["analysis"]["id"]))
        return {"rows": rows, "refresh": {**state, "running": self.running}}

    def idea_changes(self, idea) -> list[dict]:
        state = self.repository.read_json("refresh", {"results": {}, "failures": {}})
        active = {a["id"] for a in self.catalogue.records()["analyses"]}
        changes = []
        for entry in idea.charts:
            saved = self.repository.get_snapshot(idea.id, entry.snapshot_id).evaluation
            key = saved.definition.id
            if key not in active or key not in state["results"] or key in state["failures"]:
                continue
            latest = self.repository.get_evaluation(state["results"][key])
            if latest.definition != self.catalogue.resolve(key):
                # A retained pre-edit refresh is not a later change to new evidence.
                continue
            if latest.definition.revision == saved.definition.revision and latest.definition.inputs == saved.definition.inputs and latest.definition.references == saved.definition.references:
                # Apply saved exploratory choices to retained raw inputs, never
                # silently substitute the catalogue's reference/fit settings.
                required_start = retrieval_start(latest.request.end,
                    (saved.definition.settings.history_years, saved.definition.settings.fit_years),
                    (r.lookback_years for r in saved.definition.settings.adjustments(len(saved.definition.inputs)) if r.method != "none"),
                    saved.definition.settings.needs_moves(len(saved.definition.inputs)))
                if latest.request.start > required_start:
                    continue
                required = {b.id for b in (*saved.definition.inputs, *saved.definition.references)}
                if not required <= {s.binding.id for s in latest.data.series}:
                    continue
                latest = evaluate(saved.definition, latest.data, latest.request, latest.evaluated_at)
            result = compare(latest, saved)
            if result.finding in ("new", "changed", "correction", "incompatible"):
                changes.append({"chart_id": entry.id, "name": saved.definition.name,
                    "since": str(saved.observation_date), "to": str(latest.observation_date),
                    "finding": result.finding, "reasons": list(result.reasons or result.limitations[-1:])})
        return changes
