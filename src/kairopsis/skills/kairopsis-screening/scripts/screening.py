#!/usr/bin/env python3
"""Portable, run-pinned screening access; Python standard library only."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("Invalid identifier")
    return value


def base_url(value):
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Supply the selected app's http(s) base URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Base URL must omit credentials, query and fragment")
    return value.rstrip("/")


def read_json(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def write_new_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def http(base, route, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(base + route, data=data,
                      headers={"Accept": "application/json", "Content-Type": "application/json"})
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def check_status(value, run_id=None, request_id=None):
    if value.get("schema_version") != 1:
        raise ValueError("Unsupported screening schema")
    identifier(value.get("run_id"))
    if run_id is not None and value["run_id"] != run_id:
        raise ValueError("Returned run differs from pinned run")
    if request_id is not None and value.get("request_id") != request_id:
        raise ValueError("Returned request differs from persisted request")
    if value.get("status") not in ("running", "completed", "failed", "interrupted"):
        raise ValueError("Unknown run state")
    return value


def check_manifest(value, run_id=None):
    check_status(value, run_id)
    if value["status"] != "completed":
        raise ValueError("Run is not completed")
    if not isinstance(value.get("rows"), list):
        raise ValueError("Manifest rows missing")
    return value


def load_state(path):
    value = read_json(path)
    base_url(value["base_url"])
    identifier(value["request_id"])
    if value.get("run_id") is not None:
        identifier(value["run_id"])
    return value


def save_state(path, value):
    # Replace one state file, never any retained run/evidence file.
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    write_new_json(temporary, value)
    temporary.replace(path)


def start(args):
    path = Path(args.state).resolve()
    base = base_url(args.base_url)
    if not path.exists():
        write_new_json(path, {"base_url": base, "request_id": uuid4().hex,
                              "created_at": datetime.now(timezone.utc).isoformat(), "run_id": None})
    state = load_state(path)
    if state["base_url"] != base:
        raise ValueError("State belongs to another app; preserve its original target")
    if state.get("run_id"):
        result = http(base, "/api/screenings/" + state["run_id"])
    else:
        result = http(base, "/api/screenings", {"request_id": state["request_id"]})
    check_status(result, state.get("run_id"), state["request_id"])
    state["run_id"] = result["run_id"]
    save_state(path, state)
    return {"state_path": str(path), **result}


def status(args):
    state = load_state(args.state)
    if not state.get("run_id"):
        raise ValueError("Uncertain submission: resume start with this same state")
    deadline = time.monotonic() + args.wait
    while True:
        result = check_status(http(state["base_url"], "/api/screenings/" + state["run_id"]),
                              state["run_id"], state["request_id"])
        if result["status"] != "running" or time.monotonic() >= deadline:
            return {"state_path": str(Path(args.state).resolve()), **result}
        time.sleep(min(2, max(0, deadline - time.monotonic())))


def local_run(folder):
    root = Path(folder).resolve(strict=True)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        status_path = root / "status.json"
        state = read_json(contained_path(root, "status.json")) if status_path.is_file() else {"status": "incomplete"}
        raise ValueError("No completed manifest; local state: " + str(state.get("status")))
    return root, check_manifest(read_json(contained_path(root, "manifest.json")))


def read_run(args):
    if args.folder:
        root, manifest = local_run(args.folder)
        if args.run_id:
            check_manifest(manifest, identifier(args.run_id))
        return {"folder": str(root), "manifest": manifest}
    result = check_status(http(base_url(args.base_url), "/api/screenings/" + identifier(args.run_id)),
                          args.run_id)
    if result["status"] == "completed":
        check_manifest(result.get("manifest", {}), args.run_id)
    return result


def contained_path(root, reference):
    if not isinstance(reference, str) or not reference or Path(reference).is_absolute():
        raise ValueError("Evidence reference must be a relative path")
    path = (root / reference).resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError("Evidence reference leaves the run folder")
    return path


def evidence(args):
    key = identifier(args.evaluation_id)
    if args.folder:
        root, manifest = local_run(args.folder)
        if args.run_id:
            check_manifest(manifest, identifier(args.run_id))
        reference = manifest.get("evidence", {}).get(key)
        if reference is None:
            raise ValueError("Evaluation is not retained in this run")
        value = read_json(contained_path(root, reference))
    else:
        value = http(base_url(args.base_url), "/api/screenings/" + identifier(args.run_id)
                     + "/evaluations/" + key)
    if value.get("id") != key:
        raise ValueError("Returned evaluation differs from pinned evaluation")
    return value


def brief(args):
    markdown = Path(args.markdown).read_text(encoding="utf-8")
    if not markdown.strip() or len(markdown) > 50000 or "\x00" in markdown:
        raise ValueError("Brief must contain 1–50000 characters without NUL")
    if args.folder:
        root, manifest = local_run(args.folder)
        if args.run_id:
            check_manifest(manifest, identifier(args.run_id))
        directory = root / "briefs"
        directory.mkdir(exist_ok=True)
        if not directory.resolve().is_relative_to(root):
            raise ValueError("Brief directory leaves the run folder")
        key = uuid4().hex
        path = directory / (key + ".md")
        with path.open("x", encoding="utf-8") as stream:
            stream.write(markdown)
        if path.read_text(encoding="utf-8") != markdown:
            raise ValueError("Brief readback differs")
        return {"brief_id": key, "run_id": manifest["run_id"], "path": str(path), "markdown": markdown}
    base, run_id = base_url(args.base_url), identifier(args.run_id)
    result = http(base, "/api/screenings/" + run_id + "/briefs", {"markdown": markdown})
    if result.get("run_id") != run_id:
        raise ValueError("Brief belongs to another run")
    key = identifier(result.get("brief_id"))
    saved = http(base, "/api/screenings/" + run_id + "/briefs/" + key)
    if saved.get("run_id") != run_id or saved.get("brief_id") != key or saved.get("markdown") != markdown:
        raise ValueError("Brief readback differs")
    return saved


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    submit = commands.add_parser("start", help="Submit once, or resume the persisted request")
    submit.add_argument("--base-url", required=True)
    submit.add_argument("--state", required=True, help="Unique state file for this user request")
    submit.set_defaults(action=start)
    poll = commands.add_parser("status", help="Read/poll the exact persisted run")
    poll.add_argument("--state", required=True)
    poll.add_argument("--wait", type=int, choices=range(0, 46), default=0, metavar="0..45")
    poll.set_defaults(action=status)
    listing = commands.add_parser("list", help="Read-only bounded listing")
    listing.add_argument("--base-url", required=True)
    listing.add_argument("--limit", type=int, choices=range(1, 101), default=20, metavar="1..100")
    listing.set_defaults(action=lambda args: http(base_url(args.base_url), "/api/screenings?limit=" + str(args.limit)))
    for name, action in (("read", read_run), ("evidence", evidence), ("brief", brief)):
        command = commands.add_parser(name)
        target = command.add_mutually_exclusive_group(required=True)
        target.add_argument("--base-url")
        target.add_argument("--folder")
        command.add_argument("--run-id", help="Required for HTTP; optional identity check for a folder")
        if name == "evidence":
            command.add_argument("--evaluation-id", required=True)
        if name == "brief":
            command.add_argument("--markdown", required=True)
        command.set_defaults(action=action)
    return result


def main():
    args = parser().parse_args()
    try:
        value = args.action(args)
        print(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
