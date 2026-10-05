"""Portable authoritative records; atomic pointers publish complete versions."""
import csv
import hashlib
import io
import json
import os
import re
import struct
import zlib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from importlib import import_module
from tempfile import NamedTemporaryFile
from threading import RLock
from typing import Any, Literal

from .models import ChartEntry, DisplaySettings, Evaluation, Idea, Snapshot, identity


def safe_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("Invalid record identity")
    return value


def atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def atomic_json(path: Path, content: Any) -> None:
    atomic_bytes(path, (json.dumps(content, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode())


def validate_png(image: bytes) -> None:
    if not image.startswith(b"\x89PNG\r\n\x1a\n") or len(image) > 12_000_000:
        raise ValueError("Provide a PNG chart under 12 MB")
    offset = 8
    kinds: list[bytes] = []
    while offset + 12 <= len(image):
        length = int.from_bytes(image[offset:offset+4], "big")
        chunk = image[offset+4:offset+8+length]
        end = offset + 12 + length
        if end > len(image) or zlib.crc32(chunk) != int.from_bytes(image[end-4:end], "big"):
            raise ValueError("Incomplete or corrupt PNG chart")
        kind = chunk[:4]
        if not kinds:
            if kind != b"IHDR" or length != 13:
                raise ValueError("PNG header missing")
            width, height = struct.unpack(">II", chunk[4:12])
            if not (0 < width <= 6000 and 0 < height <= 6000):
                raise ValueError("PNG dimensions outside supported bounds")
        kinds.append(kind)
        offset = end
        if kind == b"IEND":
            if length or offset != len(image) or b"IDAT" not in kinds:
                raise ValueError("Invalid PNG ending")
            return
    raise ValueError("Incomplete PNG chart")


class Repository:
    def __init__(self, root: Path, mode: str):
        self.root, self.mode = root, mode
        self._lock = RLock()
        root.mkdir(parents=True, exist_ok=True)
        marker = root / "workspace.json"
        if marker.exists():
            metadata = json.loads(marker.read_text())
            if metadata != {"schema_version": 2, "mode": mode}:
                raise ValueError("Unsupported workspace or different mode; preserved existing content. Choose a separate empty workspace.")
        else:
            if any(root.iterdir()):
                raise ValueError("Unmarked nonempty workspace; existing content preserved. Choose an empty directory.")
            atomic_json(marker, {"schema_version": 2, "mode": mode})

    @contextmanager
    def transaction(self) -> Iterator[None]:
        # Reuse the verified OS-lock pattern, independently of legacy models.
        with self._lock, (self.root / ".write.lock").open("a+b") as stream:
            if os.name == "nt":
                msvcrt = import_module("msvcrt")
                stream.seek(0, os.SEEK_END)
                if not stream.tell():
                    stream.write(b"0")
                    stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "nt":
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def read_json(self, name: str, default: Any = None) -> Any:
        path = self.root / (safe_id(name) + ".json")
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

    def write_json(self, name: str, content: Any) -> None:
        atomic_json(self.root / (safe_id(name) + ".json"), content)

    def save_evaluation(self, evaluation: Evaluation) -> None:
        path = self.root / "evaluations" / (safe_id(evaluation.id) + ".json")
        if path.exists():
            if self.get_evaluation(evaluation.id) != evaluation:
                raise ValueError("Immutable evaluation already exists")
            return
        atomic_json(path, evaluation.model_dump(mode="json"))

    def get_evaluation(self, key: str) -> Evaluation:
        return Evaluation.model_validate_json((self.root / "evaluations" / (safe_id(key) + ".json")).read_text(encoding="utf-8"))

    def idea_folder(self, key: str) -> Path:
        return self.root / "ideas" / safe_id(key)

    def idea_version(self, key: str, version: str) -> Idea:
        return Idea.model_validate_json((self.idea_folder(key) / "versions" / safe_id(version) / "idea.json").read_text(encoding="utf-8"))

    def get_idea(self, key: str) -> Idea:
        pointer = json.loads((self.idea_folder(key) / "current.json").read_text(encoding="utf-8"))
        return self.idea_version(key, pointer["version"])

    def list_ideas(self) -> list[Idea]:
        # No index is required for this single-user collection. Invalid committed
        # records raise an actionable error instead of silently hiding evidence.
        paths = sorted((self.root / "ideas").glob("*/current.json"))
        return sorted((self.get_idea(p.parent.name) for p in paths), key=lambda i: i.modified_at, reverse=True)

    def save_idea(self, idea: Idea) -> None:
        folder = self.idea_folder(idea.id)
        version = folder / "versions" / safe_id(idea.version)
        if version.exists():
            raise ValueError("Idea version already exists; committed content is immutable")
        # All files land before the sole publication pointer. A failed pointer
        # update leaves the previous committed version readable after restart.
        for chart in idea.charts:
            self.get_snapshot(idea.id, chart.snapshot_id)
        atomic_json(version / "idea.json", idea.model_dump(mode="json"))
        markdown = f"# {idea.title}\n\n{idea.thought}\n\n"
        for chart in idea.charts:
            snapshot = self.get_snapshot(idea.id, chart.snapshot_id)
            markdown += f"## {snapshot.evaluation.definition.name}\n\n![Chart](../../snapshots/{chart.snapshot_id}/image.png)\n\n{chart.note}\n\n"
        markdown += "## Idea notes\n\n" + "\n\n".join(f"{n.text}\n\nCreated {n.created_at.isoformat()}" for n in idea.notes)
        atomic_bytes(version / "notes.md", markdown.encode())
        atomic_json(folder / "current.json", {"version": idea.version})

    def update_idea(self, key: str, changes: dict, now: datetime, expected_version: str | None = None) -> Idea:
        def update(idea: Idea) -> Idea:
            if expected_version is not None and idea.version != expected_version:
                raise ValueError("Idea changed during editing. Reload before retrying; earlier evidence retained.")
            return Idea.model_validate({**idea.model_dump(), **changes})
        return self.modify_idea(key, update, now)

    def modify_idea(self, key: str, mutation: Callable[[Idea], Idea], now: datetime) -> Idea:
        with self.transaction():
            idea = self.get_idea(key)
            changed = mutation(idea).model_copy(update={"id": idea.id, "created_at": idea.created_at,
                "modified_at": now, "version": identity()})
            self.save_idea(changed)
            return changed

    def capture(self, idea_id: str, evaluation: Evaluation, display: DisplaySettings,
                image: bytes, mode: Literal["saved", "latest", "investigation"], now: datetime) -> Snapshot:
        validate_png(image)
        snapshot = Snapshot(evaluation=evaluation, display=display, captured_at=now, mode=mode,
                            image_sha256=hashlib.sha256(image).hexdigest())
        folder = self.idea_folder(idea_id) / "snapshots" / snapshot.id
        atomic_bytes(folder / "image.png", image)
        data = io.StringIO()
        writer = csv.writer(data)
        measured = evaluation.definition.settings.measure != "level"
        standardized = evaluation.standardization_estimate is not None
        extra_headers = [label for i in range(len(evaluation.definition.inputs)) for label in
            (f"measured_input_{i+1}", f"measured_unit_{i+1}", f"risk_scale_{i+1}", f"change_start_{i+1}")] if measured else []
        writer.writerow(["date", "value", "unit", *[f"input_{i+1}" for i in range(len(evaluation.definition.inputs))],
                         *[f"observed_on_{i+1}" for i in range(len(evaluation.definition.inputs))], *extra_headers, *(["unstandardized_value", "unstandardized_unit"] if standardized else [])])
        for p in evaluation.points:
            extra = [value for i in range(len(p.inputs)) for value in
                (p.transformed_inputs[i], evaluation.input_units[i], p.risk_scales[i], p.period_start[i])] if measured else []
            writer.writerow([p.date, p.value, evaluation.unit, *p.inputs, *p.observed_on, *extra,
                *([p.unstandardized_value, evaluation.standardization_estimate.unit] if evaluation.standardization_estimate else [])])
        atomic_bytes(folder / "data.csv", data.getvalue().encode())
        atomic_json(folder / "snapshot.json", snapshot.model_dump(mode="json"))
        return snapshot

    def get_snapshot(self, idea_id: str, key: str) -> Snapshot:
        folder = self.idea_folder(idea_id) / "snapshots" / safe_id(key)
        snapshot = Snapshot.model_validate_json((folder / "snapshot.json").read_text(encoding="utf-8"))
        if hashlib.sha256((folder / "image.png").read_bytes()).hexdigest() != snapshot.image_sha256:
            raise ValueError("Saved chart image is corrupt; restore evidence from backup")
        return snapshot

    def snapshot_image(self, idea_id: str, key: str) -> bytes:
        self.get_snapshot(idea_id, key)
        return (self.idea_folder(idea_id) / "snapshots" / safe_id(key) / "image.png").read_bytes()

    def add_chart(self, evaluation: Evaluation, display: DisplaySettings, image: bytes, now: datetime,
                  title: str = "", thought: str = "", idea_id: str | None = None, note: str = "") -> Idea:
        with self.transaction():
            idea = self.get_idea(idea_id) if idea_id else Idea(title=title.strip(), thought=thought, created_at=now, modified_at=now)
            snapshot = self.capture(idea.id, evaluation, display, image, "investigation", now)
            changed = idea.model_copy(update={"charts": (*idea.charts, ChartEntry(snapshot_id=snapshot.id, note=note)),
                "modified_at": now, "version": identity()})
            self.save_idea(changed)
            return changed
