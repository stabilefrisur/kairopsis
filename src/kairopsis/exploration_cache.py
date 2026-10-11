"""Bounded, process-local observation snapshots for interactive exploration.

Refresh replaces a workspace snapshot atomically. Ordinary edits reuse observations;
extending coverage retrieves only missing intervals and preserves existing values.
Provider outcomes/native dates remain intact, including unverified provenance.
"""
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from threading import RLock
from typing import Any

from .models import DataRequest, DataResponse, SeriesResult, identity


@dataclass
class WorkspaceCache:
    segments: dict[str, list[tuple[DataRequest, DataResponse]]] = field(default_factory=dict)
    versions: dict[str, str] = field(default_factory=dict)
    views: OrderedDict[str, Any] = field(default_factory=OrderedDict)
    analyses: OrderedDict[str, Any] = field(default_factory=OrderedDict)
    refreshed: bool = False

    def load(self, key: str, request: DataRequest, fetch) -> DataResponse:
        segments = self.segments.get(key, [])
        missing = []
        cursor = request.start
        for old_request, _ in sorted(segments, key=lambda s: s[0].start):
            if old_request.end < cursor:
                continue
            if old_request.start > request.end:
                break
            if old_request.start > cursor:
                missing.append((cursor, old_request.start - timedelta(days=1)))
            cursor = max(cursor, old_request.end + timedelta(days=1))
        if cursor <= request.end:
            missing.append((cursor, request.end))
        additions = []
        for start, end in missing:
            query = request.model_copy(update={"start": start, "end": end, "freshness": "require_fresh"})
            data = fetch(query)
            if data.failures or not data.series or data.outcome in ("failed", "partial"):
                # Never cache failures or substitute older values as a successful refresh.
                self.versions[key] = identity()
                if self.refreshed:
                    raise ValueError("Could not refresh all series. Previous data kept; retry Refresh data.")
                return data
            additions.append((query, data))
        if additions:
            segments = sorted([*segments, *additions], key=lambda s: s[0].start)
            self.segments[key] = segments
            self.versions[key] = identity()
        relevant = [(q, d) for q, d in segments if q.start <= request.end and q.end >= request.start]
        first = relevant[0][1]
        observations = tuple(o for q, d in relevant for s in d.series for o in s.observations
                             if max(request.start, q.start) <= o.date <= min(request.end, q.end))
        provenance = " | ".join(dict.fromkeys(s.provenance for _, d in relevant for s in d.series))
        outcomes = {d.outcome for _, d in relevant}
        outcome = next(iter(outcomes)) if len(outcomes) == 1 else "unverified"
        return first.model_copy(update={
            "series": (SeriesResult(binding=request.bindings[0], observations=observations, provenance=provenance),),
            "attempted_at": min(d.attempted_at for _, d in relevant),
            "completed_at": max(d.completed_at for _, d in relevant), "outcome": outcome})

    def retrievals(self, key: str) -> list[dict]:
        return [{"request": q.model_dump(mode="json"), "attempted_at": d.attempted_at.isoformat(),
                 "completed_at": d.completed_at.isoformat(), "outcome": d.outcome}
                for q, d in self.segments.get(key, [])]

    @staticmethod
    def remember(cache: OrderedDict, key: str, value: Any, limit: int = 32) -> None:
        cache[key] = value
        cache.move_to_end(key)
        while len(cache) > limit:
            cache.popitem(last=False)


class ExplorationCache:
    def __init__(self, maximum_workspaces: int = 8):
        self.maximum_workspaces = maximum_workspaces
        self.workspaces: OrderedDict[str, WorkspaceCache] = OrderedDict()
        self.lock = RLock()

    @contextmanager
    def session(self, workspace_id: str, refresh: bool = False):
        # Local application: serialize snapshot mutation and calculations, avoiding
        # duplicate concurrent loads or a refresh interleaving with an older edit.
        with self.lock:
            cache = WorkspaceCache(refreshed=True) if refresh else self.workspaces.get(workspace_id, WorkspaceCache())
            yield cache
            cache.refreshed = False
            self.workspaces[workspace_id] = cache
            self.workspaces.move_to_end(workspace_id)
            while len(self.workspaces) > self.maximum_workspaces:
                self.workspaces.popitem(last=False)
