"""Portable refresh bundles, durable request identities and local brief versions."""
from __future__ import annotations

import json
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from threading import RLock
from typing import Any

from .models import DataRequest, DataResponse, Evaluation, ResolvedDefinition, identity
from .repository import Repository, atomic_bytes, atomic_json, safe_id


class Screenings:
    def __init__(self, repository: Repository, timezone: str):
        self.repository, self.timezone = repository, timezone
        self.root = repository.root / "screenings"
        self.lock = RLock()
        self._terminal_status: dict[str, dict] = {}
        # One server per workspace. A prior process cannot still finish these jobs.
        for path in self.root.glob("*/status.json"):
            status = self._status(path.parent.name)
            if status["status"] == "running" and not self._path(path.parent.name, "manifest.json").exists():
                atomic_json(self._path(path.parent.name, "status.json"), {**status, "status": "interrupted",
                    "error": "Refresh interrupted before complete publication"})

    def folder(self, run_id: str) -> Path:
        folder = self.root / safe_id(run_id)
        if not folder.resolve().is_relative_to(self.root.resolve()):
            raise ValueError("Screening path outside workspace")
        return folder

    def _status(self, run_id: str) -> dict:
        path = self._path(run_id, "status.json")
        return json.loads(path.read_text(encoding="utf-8"))

    def _path(self, run_id: str, relative: str) -> Path:
        folder = self.folder(run_id)
        path = folder / relative
        if not path.resolve().is_relative_to(folder.resolve()):
            raise ValueError("Record path outside screening")
        return path

    def create(self, trigger: str, request_id: str | None, now: datetime) -> tuple[dict, bool]:
        with self.lock:
            if request_id is not None:
                safe_id(request_id)
                for path in self.root.glob("*/status.json"):
                    status = self._status(path.parent.name)
                    if status.get("request_id") == request_id:
                        return self.get(status["run_id"]), False
            run_id = identity()
            folder = self.folder(run_id)
            status = {"schema_version": 1, "run_id": run_id, "request_id": request_id,
                "trigger": trigger, "status": "running", "mode": self.repository.mode,
                "timezone": self.timezone, "application_version": version("kairopsis"),
                "attempted_at": now.isoformat(), "completed_at": None,
                "path": str(folder.resolve()), "manifest_path": str((folder / "manifest.json").resolve()),
                "error": None}
            atomic_json(self._path(run_id, "status.json"), status)
            return status, True

    def get(self, run_id: str) -> dict:
        with self.lock:
            folder = self.folder(run_id)
            manifest_path = self._path(run_id, "manifest.json")
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest.get("schema_version") != 1 or manifest.get("status") != "completed" or manifest.get("run_id") != run_id:
                    raise ValueError("Unsupported or incomplete screening manifest")
                keys = ("schema_version", "run_id", "request_id", "trigger", "status", "mode", "timezone",
                    "application_version", "attempted_at", "completed_at", "error")
                return {**{key: manifest[key] for key in keys}, "path": str(folder.resolve()),
                    "manifest_path": str(manifest_path.resolve()), "manifest": manifest}
            status = self._status(run_id)
            return self._terminal_status.get(run_id, status)

    def listing(self, limit: int) -> dict:
        if not 1 <= limit <= 100:
            raise ValueError("Screening limit must be between 1 and 100")
        with self.lock:
            folders = {p.parent.name for pattern in ("*/status.json", "*/manifest.json") for p in self.root.glob(pattern)}
            runs = [self.get(key) for key in folders]
            runs.sort(key=lambda run: (run["attempted_at"], run["run_id"]), reverse=True)
            return {"runs": [{k: v for k, v in run.items() if k != "manifest"} for run in runs[:limit]]}

    def fail(self, run_id: str, now: datetime) -> None:
        with self.lock:
            # Complete bundles are immutable; failures before publication have no manifest.
            status = self._status(run_id)
            failed = {**status, "status": "failed", "completed_at": now.isoformat(),
                "error": "Refresh could not be retained/published; previous dashboard evidence preserved"}
            # A full disk may prevent even failure bookkeeping. End polling in
            # this process; the original running record is interrupted on restart.
            self._terminal_status[run_id] = failed
            atomic_json(self._path(run_id, "status.json"), failed)

    def write(self, run_id: str, relative: str, content: Any) -> str:
        path = self._path(run_id, relative)
        atomic_json(path, content)
        return relative

    def retain(self, run_id: str, evaluation: Evaluation, evidence: dict[str, str]) -> str:
        # Preserve original bytes. Export the baseline actually used for this
        # row, not the whole history of prior comparisons. Deeper baseline_id
        # values remain historical metadata unless indexed in manifest.evidence.
        if evaluation.id not in evidence:
            relative = f"evaluations/{safe_id(evaluation.id)}.json"
            destination = self._path(run_id, relative)
            atomic_bytes(destination, (self.repository.root / "evaluations" / (evaluation.id + ".json")).read_bytes())
            evidence[evaluation.id] = relative
        return evidence[evaluation.id]

    def capture_row(self, run_id: str, definition: ResolvedDefinition, monitored: bool, idea_refs: list[dict],
                    current: Evaluation | None, previous: Evaluation | None, failure: str | None,
                    request: DataRequest | None, data: DataResponse | None, attempted: str, completed: str,
                    evidence: dict[str, str]) -> dict:
        key = safe_id(definition.id)
        retained = previous if failure else None
        displayed = retained if failure else current
        comparison = self.repository.get_evaluation(retained.baseline_id) if retained and retained.baseline_id else previous if not failure else None
        detail = self.retain(run_id, displayed, evidence) if displayed else None
        baseline = self.retain(run_id, comparison, evidence) if comparison else None
        definition_path = self.write(run_id, f"definitions/{key}.json", definition.model_dump(mode="json"))
        attempt_path = None
        if failure:
            attempt_path = self.write(run_id, f"attempts/{key}.json", {
                "definition": definition.model_dump(mode="json"), "failure": failure,
                "request": request.model_dump(mode="json") if request else None,
                "data": data.model_dump(mode="json") if data else None})
        provider = {"outcome": data.outcome if data else "exception",
            "attempted_at": data.attempted_at.isoformat() if data else attempted,
            "completed_at": data.completed_at.isoformat() if data else completed}
        summary = displayed.model_dump(mode="json", include={"current", "unit", "change", "change_start",
            "observation_date", "input_dates", "percentile", "finding", "reasons", "conditions", "condition_keys",
            "eligible", "limitations", "evaluated_at", "input_units", "sensitivity"}) if displayed else {}
        eligible = bool(current and current.eligible and not failure)
        flagged = bool(monitored and eligible and current and current.reasons and
            current.finding in ("condition", "new", "changed"))
        return {**summary, "analysis_id": key, "revision": definition.revision, "name": definition.name,
            "economic_rationale": definition.economic_rationale, "monitored": monitored,
            "inputs": [s.model_dump(mode="json", include={"id", "revision", "name", "unit", "currency", "basis"}) for s in definition.inputs],
            "status": "retained" if retained else "failed" if failure else "evaluated", "failure": failure,
            "retained": retained is not None, "eligible": eligible, "flagged": flagged,
            "finding": displayed.finding if displayed else "unavailable", "limitations": list(displayed.limitations) if displayed else [],
            "provider": provider, "evaluation_id": displayed.id if displayed else None,
            "current_evaluation_id": current.id if current and not failure else None,
            "retained_evaluation_id": retained.id if retained else None,
            "baseline_id": comparison.id if comparison else None,
            "detail_ref": detail, "baseline_ref": baseline, "definition_ref": definition_path,
            "attempt_ref": attempt_path, "idea_refs": idea_refs}

    def publish(self, run_id: str, manifest: dict, refresh: dict) -> None:
        with self.lock, self.repository.transaction():
            path = self._path(run_id, "manifest.json")
            atomic_json(path, manifest)
            try:
                self.repository.write_json("refresh", refresh)
            except Exception:
                path.unlink()
                raise

    def evaluation(self, run_id: str, evaluation_id: str) -> Evaluation:
        run = self.get(run_id)
        if run["status"] != "completed":
            raise ValueError("Screening is not completed")
        safe_id(evaluation_id)
        relative = run["manifest"]["evidence"].get(evaluation_id)
        if relative != f"evaluations/{evaluation_id}.json":
            raise FileNotFoundError("Evaluation is not retained in this screening")
        path = self._path(run_id, relative)
        return Evaluation.model_validate_json(path.read_text(encoding="utf-8"))

    def save_brief(self, run_id: str, markdown: str, now: datetime) -> dict:
        if not markdown.strip() or len(markdown) > 50000 or "\x00" in markdown:
            raise ValueError("Provide nonempty Markdown under 50000 characters without NUL")
        if self.get(run_id)["status"] != "completed":
            raise ValueError("Briefs require a completed screening")
        brief_id = identity()
        path = self._path(run_id, f"briefs/{brief_id}.md")
        metadata_path = self._path(run_id, f"briefs/{brief_id}.json")
        atomic_bytes(path, markdown.encode("utf-8"))
        metadata = {"brief_id": brief_id, "run_id": run_id, "created_at": now.isoformat()}
        atomic_json(metadata_path, metadata)
        return {**metadata, "path": str(path.resolve()), "markdown": markdown}

    def brief(self, run_id: str, brief_id: str) -> dict:
        if self.get(run_id)["status"] != "completed":
            raise ValueError("Briefs require a completed screening")
        safe_id(brief_id)
        path = self._path(run_id, f"briefs/{brief_id}.md")
        metadata_path = self._path(run_id, f"briefs/{brief_id}.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        return {**metadata, "path": str(path.resolve()), "markdown": path.read_text(encoding="utf-8")}


def coverage(rows: list[dict]) -> dict:
    def counts(selected: list[dict]) -> dict:
        return {"total": len(selected), "evaluated": sum(r["status"] == "evaluated" for r in selected),
            "failed": sum(r["failure"] is not None for r in selected),
            "retained": sum(r["retained"] for r in selected), "eligible": sum(r["eligible"] for r in selected),
            "flagged": sum(r["flagged"] for r in selected),
            "quiet": sum(r["status"] == "evaluated" and r["finding"] == "quiet" for r in selected),
            "provider_outcomes": {outcome: sum(r["provider"]["outcome"] == outcome for r in selected)
                for outcome in ("synthetic", "fresh", "cache", "partial", "failed", "unverified", "exception")}}
    return {"all": counts(rows), "monitored": counts([r for r in rows if r["monitored"]])}
