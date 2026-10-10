"""Immutable Explore records and complete, portable, atomically published captures.

Explore's first persistent write upgrades the workspace marker 2→3. The exact
old marker is backed up; old Idea versions/Snapshots are never rewritten. Version2
binaries reject marker3 before reading Ideas. Interrupted unreferenced records
are safe to ignore; the sole Idea/current or exploration/current pointer commits.
"""
import base64
import csv
import hashlib
import io
import json
import zipfile
from datetime import datetime
from typing import Literal

from .exploration import workspace_fingerprint
from .exploration_models import ExplorationSnapshot, ViewResult, WorkspaceDefinition
from .models import ExplorationEntry, Idea, identity
from .repository import Repository, atomic_bytes, atomic_json, safe_id, validate_png


class ExplorationConflict(ValueError):
    pass


class ExplorationRepository:
    def __init__(self, repository: Repository):
        self.repository = repository

    def upgrade(self) -> None:
        # Caller holds repository transaction. Backup before marker publication.
        marker = self.repository.root / "workspace.json"
        content = marker.read_bytes()
        version = json.loads(content)["schema_version"]
        if version == 2:
            backup = self.repository.root / "workspace-schema2.json"
            if not backup.exists():
                atomic_bytes(backup, content)
            atomic_json(marker, {"schema_version": 3, "mode": self.repository.mode})
        elif version != 3:
            raise ValueError("Unsupported workspace version; existing evidence preserved")

    def save(self, workspace: WorkspaceDefinition, expected_version: str | None) -> WorkspaceDefinition:
        with self.repository.transaction():
            folder = self.repository.root / "explorations" / safe_id(workspace.id)
            pointer = folder / "current.json"
            current = json.loads(pointer.read_text())["version"] if pointer.exists() else None
            if current != expected_version:
                raise ExplorationConflict("Workspace changed during editing. Reload before saving; draft retained.")
            self.upgrade()
            saved = workspace.model_copy(update={"version": identity()})
            assert saved.version is not None
            atomic_json(folder / "versions" / saved.version / "workspace.json", saved.model_dump(mode="json"))
            atomic_json(pointer, {"version": saved.version})
            return saved

    def get(self, key: str) -> WorkspaceDefinition:
        folder = self.repository.root / "explorations" / safe_id(key)
        version = json.loads((folder / "current.json").read_text())["version"]
        return WorkspaceDefinition.model_validate_json((folder / "versions" / safe_id(version) / "workspace.json").read_text())

    def list_workspaces(self) -> list[WorkspaceDefinition]:
        return [self.get(p.parent.name) for p in sorted((self.repository.root / "explorations").glob("*/current.json"))]

    def begin_preview(self, workspace_id: str) -> str:
        token = identity()
        with self.repository.transaction():
            atomic_json(self.repository.root / "exploration-results" / "current" / f"{safe_id(workspace_id)}.json", {"token": token, "result_ids": []})
        return token

    def retain_results(self, results: list[ViewResult], workspace_id: str, token: str) -> None:
        # Preview retention does not need marker upgrade: legacy binaries never
        # inspect this directory. Capture/save gates the incompatible write.
        with self.repository.transaction():
            for result in results:
                path = self.repository.root / "exploration-results" / f"{safe_id(result.id)}.json"
                if path.exists():
                    raise ValueError("Result identity is immutable")
                atomic_json(path, result.model_dump(mode="json"))
                atomic_bytes(path.with_suffix(".sha256"), hashlib.sha256(path.read_bytes()).hexdigest().encode())
            pointer = self.repository.root / "exploration-results" / "current" / f"{safe_id(workspace_id)}.json"
            current = json.loads(pointer.read_text())
            if current["token"] == token:
                atomic_json(pointer, {"token": token, "result_ids": [r.id for r in results]})

    def get_result(self, key: str) -> ViewResult:
        path = self.repository.root / "exploration-results" / f"{safe_id(key)}.json"
        if hashlib.sha256(path.read_bytes()).hexdigest() != path.with_suffix(".sha256").read_text():
            raise ValueError("Preview evidence corrupt; preview again before capture")
        return ViewResult.model_validate_json(path.read_text())

    def capture(self, workspace: WorkspaceDefinition, result_ids: tuple[str, ...], images: dict[str, str], now: datetime,
                title: str, idea_id: str | None = None, role: Literal["supporting", "challenging", "contextual"] = "contextual") -> tuple[Idea, ExplorationSnapshot]:
        if not result_ids or len(set(result_ids)) != len(result_ids):
            raise ValueError("Choose one or more distinct current results")
        if set(images) != set(result_ids):
            raise ValueError("Provide exactly one rendered PNG for each selected result")
        results = tuple(self.get_result(key) for key in result_ids)
        pointer = self.repository.root / "exploration-results" / "current" / f"{safe_id(workspace.id)}.json"
        if not pointer.exists() or not set(result_ids) <= set(json.loads(pointer.read_text())["result_ids"]):
            raise ValueError("Preview superseded; preview again before capture")
        views = {v.id: v for v in workspace.views}
        for result in results:
            if now >= result.expires_at:
                raise ValueError("Preview expired; preview again before capture")
            if result.workspace_fingerprint != workspace_fingerprint(workspace) or result.view_id not in views or views[result.view_id] != result.view:
                raise ValueError("Draft changed after preview; preview again before capture")
        image_bytes = {}
        for key, encoded in images.items():
            try:
                content = base64.b64decode(encoded.removeprefix("data:image/png;base64,"), validate=True)
            except ValueError:
                raise ValueError("Invalid PNG encoding") from None
            validate_png(content)
            image_bytes[key] = content
        snapshot = ExplorationSnapshot(captured_at=now, workspace=workspace, results=results, role=role,
            images={key: hashlib.sha256(value).hexdigest() for key, value in image_bytes.items()})
        with self.repository.transaction():
            if not set(result_ids) <= set(json.loads(pointer.read_text())["result_ids"]):
                raise ValueError("Preview superseded; preview again before capture")
            idea = self.repository.get_idea(idea_id) if idea_id else Idea(title=title.strip() or workspace.name,
                thought=workspace.question, created_at=now, modified_at=now)
            self.upgrade()
            folder = self.repository.idea_folder(idea.id) / "explorations" / snapshot.id
            for key, content in image_bytes.items():
                atomic_bytes(folder / f"{key}.png", content)
            atomic_json(folder / "snapshot.json", snapshot.model_dump(mode="json"))
            notes = f"# {workspace.name}\n\nQuestion: {workspace.question}\n\n{workspace.notes}\n\nEvidence role: {role}\n\n"
            for result in results:
                notes += f"## {result.view.name}\n\n![Chart]({result.id}.png)\n\nAs of {result.as_of}; {len(result.rows)} retained, {len(result.excluded)} excluded.\n\n"
                notes += "\n".join(result.limitations) + "\n\n"
                stream = io.StringIO()
                writer = csv.writer(stream)
                writer.writerow(["retained", "row_id", "symbol", "date", "values", "actual_dates", "observed_on", "endpoints", "reasons"])
                for retained, rows in ((True, result.rows), (False, result.excluded)):
                    for row in rows:
                        values = row.model_dump(mode="json")
                        writer.writerow([retained, row.id, row.symbol, row.date, *[json.dumps(values[field], sort_keys=True) for field in ("values", "dates", "observed_on", "endpoints", "reasons")]])
                atomic_bytes(folder / f"{result.id}.csv", stream.getvalue().encode())
            atomic_bytes(folder / "notes.md", notes.encode())
            files = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in folder.iterdir() if path.is_file()}
            atomic_json(folder / "manifest.json", {"schema_version": 1, "kind": "exploration", "snapshot_id": snapshot.id, "files": files})
            self.get_capture(idea.id, snapshot.id)
            changed = idea.model_copy(update={"explorations": (*idea.explorations, ExplorationEntry(snapshot_id=snapshot.id, role=role)),
                "modified_at": now, "version": identity()})
            self.repository.save_idea(changed)
            return changed, snapshot

    def get_capture(self, idea_id: str, key: str) -> ExplorationSnapshot:
        folder = self.repository.idea_folder(idea_id) / "explorations" / safe_id(key)
        manifest = json.loads((folder / "manifest.json").read_text())
        if manifest.get("schema_version") != 1 or manifest.get("kind") != "exploration":
            raise ValueError("Unsupported exploration evidence version")
        for name, expected in manifest["files"].items():
            if name != "snapshot.json" and name != "notes.md" and not (name.endswith(".png") or name.endswith(".csv")):
                raise ValueError("Invalid evidence file")
            if "/" in name or "\\" in name or hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
                raise ValueError("Exploration evidence corrupt; restore from backup")
        snapshot = ExplorationSnapshot.model_validate_json((folder / "snapshot.json").read_text())
        expected_files = {"snapshot.json", "notes.md", *[f"{r.id}.{suffix}" for r in snapshot.results for suffix in ("csv", "png")]}
        if set(manifest["files"]) != expected_files:
            raise ValueError("Exploration manifest incomplete; restore from backup")
        if snapshot.id != key or set(snapshot.images) != {r.id for r in snapshot.results}:
            raise ValueError("Exploration manifest disagrees with capture")
        for key, expected in snapshot.images.items():
            if manifest["files"].get(f"{key}.png") != expected:
                raise ValueError("Exploration image hash disagrees with capture")
        return snapshot

    def export(self, idea_id: str, key: str) -> bytes:
        self.get_capture(idea_id, key)
        folder = self.repository.idea_folder(idea_id) / "explorations" / safe_id(key)
        manifest = json.loads((folder / "manifest.json").read_text())
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in [*manifest["files"], "manifest.json"]:
                archive.writestr(name, (folder / name).read_bytes())
        return stream.getvalue()
