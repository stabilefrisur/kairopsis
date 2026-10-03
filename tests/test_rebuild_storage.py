from datetime import datetime, timezone

import pytest

from kairopsis.repository import Repository
from kairopsis.models import Idea


NOW = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)


def test_idea_commits_survive_restart_and_retain_previous_versions(tmp_path):
    repository = Repository(tmp_path / "evidence", "mock")
    idea = Idea(title="An unfinished question", created_at=NOW, modified_at=NOW)
    repository.save_idea(idea)
    assert Repository(tmp_path / "evidence", "mock").get_idea(idea.id) == idea
    edited = repository.update_idea(idea.id, {"thought": "A tentative view"}, NOW)
    reopened = Repository(tmp_path / "evidence", "mock")
    assert reopened.get_idea(idea.id) == edited
    assert reopened.idea_version(idea.id, idea.version) == idea


def test_existing_nonempty_workspace_is_preserved(tmp_path):
    (tmp_path / "authored.md").write_text("Keep this")
    with pytest.raises(ValueError, match="nonempty"):
        Repository(tmp_path, "mock")
    assert (tmp_path / "authored.md").read_text() == "Keep this"


def test_failed_commit_pointer_keeps_previous_idea_visible(tmp_path, monkeypatch):
    import os
    repository = Repository(tmp_path / "evidence", "mock")
    idea = Idea(title="Original", created_at=NOW, modified_at=NOW)
    repository.save_idea(idea)
    replace = os.replace
    def fail_pointer(source, target):
        if target.name == "current.json":
            raise OSError("Injected disk failure")
        replace(source, target)
    monkeypatch.setattr(os, "replace", fail_pointer)
    with pytest.raises(OSError, match="disk failure"):
        repository.update_idea(idea.id, {"title": "Incomplete"}, NOW)
    assert Repository(repository.root, "mock").get_idea(idea.id) == idea
