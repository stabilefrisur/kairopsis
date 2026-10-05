"""Resolved evaluations and dated refresh publication, independent of UI/storage schemas."""
from collections.abc import Callable
from datetime import datetime
from threading import Lock, Thread
from typing import Protocol
from zoneinfo import ZoneInfo

from .analytics import evaluate
from .periods import Period, period_start, retrieval_start
from .catalogue import Catalogue
from .evaluation_comparison import compare
from .fixtures import MOCK_AS_OF
from .models import AnalysisDefinition, AnalysisSettings, DataRequest, DataResponse, Evaluation, ResolvedDefinition, SeriesBinding, identity
from .repository import Repository


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
        end = MOCK_AS_OF if self.repository.mode == "mock" else self.clock().astimezone(self.timezone).date()
        start = retrieval_start(end, (definition.settings.history_years, definition.settings.fit_years, 5, display_period),
            (r.lookback_years for r in definition.settings.adjustments(len(definition.inputs)) if r.method != "none"),
            definition.settings.measure != "level")
        request = DataRequest(bindings=(*definition.inputs, *definition.references),
            start=start, end=end)
        data = provider.fetch(request)
        if data.mode != self.repository.mode:
            raise ValueError("Provider mode does not match workspace")
        return evaluate(definition, data, request, self.clock())

    def preview_analysis(self, analysis: AnalysisDefinition, drafts: tuple[SeriesBinding, ...], period: Period) -> Evaluation:
        return self.compute(self.catalogue.resolve_draft(analysis, drafts), self.preview_provider, period)

    def preview(self, key: str, settings: dict) -> Evaluation:
        definition = self.catalogue.resolve(key)
        options = AnalysisSettings.model_validate({**definition.settings.model_dump(), **settings})
        return self.evaluate(self.catalogue.resolve(key, options))

    def refresh(self, manual: bool = True) -> dict:
        with self.refresh_lock:
            self.running = True
            try:
                state = self.repository.read_json("refresh", {"results": {}, "failures": {}})
                now = self.clock()
                day = now.astimezone(self.timezone).date().isoformat()
                if not manual and state.get("day") == day:
                    return state
                results, failures = dict(state["results"]), {}
                active = {a["id"] for a in self.catalogue.records()["analyses"]}
                results = {k: v for k, v in results.items() if k in active}
                for key in sorted(active):
                    try:
                        current = self.evaluate(self.catalogue.resolve(key))
                        previous = self.repository.get_evaluation(results[key]) if key in results else None
                        current = compare(current, previous).model_copy(update={"id": identity()})
                        self.repository.save_evaluation(current)
                        results[key] = current.id
                    except (OSError, ValueError) as error:
                        failures[key] = str(error)
                    except Exception as error:
                        # External provider details may include secrets. Expose type only.
                        failures[key] = f"Retrieval failed ({type(error).__name__}); retained dated evidence"
                state = {"day": day, "attempted_at": now.isoformat(), "completed_at": self.clock().isoformat(),
                         "results": results, "failures": failures}
                with self.repository.transaction():
                    self.repository.write_json("refresh", state)
                return state
            finally:
                self.running = False

    def first_open(self) -> None:
        state = self.repository.read_json("refresh", {})
        day = self.clock().astimezone(self.timezone).date().isoformat()
        if state.get("day") != day and not self.running:
            self.running = True
            Thread(target=self.refresh, kwargs={"manual": False}, daemon=True).start()

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
                    saved.definition.settings.measure != "level")
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
