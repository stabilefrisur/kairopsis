#!/usr/bin/env python3
"""Kairopsis deployment source transfer. Python 3.12+; no network access.

Agent: inspect the existing workspace before choosing a fresh NEW_DIRECTORY.
Preserve its outer tooling project/environment. Run --check, then --extract.
Read NEW_DIRECTORY/src/kairopsis/docs/agent-setup.md and complete its steps.
Run with the existing installation's Python, or pass --reuse-from PACKAGE_DIR.
PACKAGE_DIR may be src/kairopsis inside vendored source. Install non-editably
in a separate application environment as described in the bundled guide.
Only unchanged, checksum-verified browser libraries come from that installation.
The encoded payload is data: keep it in this file, outside the chat context.
With no arguments, extract beside this file into kairopsis-VERSION.
"""

import argparse
import base64
import binascii
import hashlib
import importlib.util
import io
import json
import lzma
from pathlib import Path, PurePosixPath
import sys
import tarfile
import tomllib


def source_files(payload: bytes, manifest: dict) -> dict[str, bytes]:
    """Validate the entire payload and Windows-safe inventory before writing."""
    try:
        compressed = base64.b64decode(b"".join(payload.split()), validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Incomplete or damaged text; copy the complete Code file again") from exc
    if hashlib.sha256(compressed).hexdigest() != manifest["payload_sha256"]:
        raise ValueError("Payload checksum mismatch; copy the complete Code file again")
    decoder = lzma.LZMADecompressor()
    raw = decoder.decompress(compressed, max_length=64 * 1024 * 1024 + 1)
    if len(raw) > 64 * 1024 * 1024 or not decoder.eof or decoder.unused_data:
        raise ValueError("Invalid or oversized source archive")
    files = {}
    names = set()
    reserved = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(10)),
                *(f"lpt{i}" for i in range(10))}
    prefix = f"kairopsis-{manifest['version']}"
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        for member in archive.getmembers():
            parts = member.name.split("/")
            if member.isdir() and parts[-1] == "":
                parts.pop()
            if (not parts or parts[0] != prefix or any(
                    not p or p in {".", ".."} or p.endswith((" ", "."))
                    or any(c in p for c in '\\:<>"|?*') or any(ord(c) < 32 for c in p)
                    or p.split(".")[0].casefold() in reserved for p in parts)):
                raise ValueError("Unsafe source archive path")
            key = "/".join(parts).casefold()
            if key in names:
                raise ValueError("Duplicate source archive path")
            names.add(key)
            if member.isdir():
                continue
            if not member.isfile() or len(parts) < 2:
                raise ValueError("Source archive must contain only regular files and directories")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("Unreadable source archive member")
            files[str(PurePosixPath(*parts[1:]))] = stream.read()
    # Detect file/directory collisions before any destination is created.
    file_names = {name.casefold() for name in files}
    for name in file_names:
        if any(str(parent) in file_names for parent in PurePosixPath(name).parents):
            raise ValueError("Source archive file/directory collision")
    required = {"pyproject.toml", "uv.lock", "AGENTS.md", "CONTEXT.md",
                "src/kairopsis/docs/agent-setup.md"}
    if not required <= files.keys():
        raise ValueError("Incomplete source workspace")
    metadata = tomllib.loads(files["pyproject.toml"].decode("utf-8"))["project"]
    if metadata["name"] != "kairopsis" or metadata["version"] != manifest["version"]:
        raise ValueError("Source version does not match transfer metadata")
    if len(files) != manifest["file_count"]:
        raise ValueError("Source inventory does not match transfer metadata")
    return files


def reused_files(manifest: dict, package_directory: Path | None) -> dict[str, bytes]:
    """Reuse only exact public vendor bytes, never old application code or state."""
    if package_directory is None:
        spec = importlib.util.find_spec("kairopsis")
        if spec is not None and spec.origin is not None:
            package_directory = Path(spec.origin).parent
    if package_directory is None:
        raise ValueError("Existing Kairopsis package not found; use its Python or --reuse-from PACKAGE_DIR")
    files = {}
    for name, expected in manifest["reused_vendor_sha256"].items():
        if not name.startswith("src/kairopsis/static/vendor/"):
            raise ValueError("Invalid reused vendor path")
        leaf = name.removeprefix("src/kairopsis/static/vendor/")
        if not leaf or any(c in leaf for c in '/\\:') or leaf in {".", ".."}:
            raise ValueError("Invalid reused vendor filename")
        candidate = package_directory / "static" / "vendor" / leaf
        if not candidate.is_file():
            raise ValueError(f"Missing browser library: {leaf}; retain/recover the 0.1.0 installation")
        data = candidate.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"Browser library checksum mismatch: {leaf}; use a verified 0.1.0 package")
        files[name] = data
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--check", action="store_true", help="verify payload; write nothing")
    actions.add_argument("--extract", type=Path, metavar="NEW_DIRECTORY")
    parser.add_argument("--reuse-from", type=Path, metavar="PACKAGE_DIR",
                        help="existing kairopsis package directory (auto-detected with its Python)")
    args = parser.parse_args()
    if sys.version_info < (3, 12):
        parser.error("Python 3.12 or later is required")
    try:
        files = source_files(PAYLOAD, MANIFEST)
        reused = reused_files(MANIFEST, args.reuse_from)
        if files.keys() & reused.keys():
            raise ValueError("Payload and reused files overlap")
        files.update(reused)
        if args.check:
            print(json.dumps(MANIFEST, indent=2))
            print("Verified. No files written; no network access.")
            return 0
        destination = args.extract or Path(__file__).resolve().parent / f"kairopsis-{MANIFEST['version']}"
        destination = destination.absolute()
        # Exclusive creation also rejects empty directories and symbolic links.
        destination.mkdir(parents=True, exist_ok=False)
        for name, data in files.items():
            target = destination.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(data)
        (destination / "transfer-manifest.json").write_text(
            json.dumps(MANIFEST, indent=2) + "\n", encoding="utf-8")
        print(f"Source extracted: {destination}")
        print(f"Agent: read {destination / 'src/kairopsis/docs/agent-setup.md'}")
        print("Continue at step 1. Existing installations and research were not changed.")
        print("Developer tests and sample datasets are available separately in the full source distribution.")
        return 0
    except (OSError, ValueError, KeyError, lzma.LZMAError, tarfile.TarError) as exc:
        print(f"Transfer failed: {exc}", file=sys.stderr)
        print("Existing installations remain unchanged. Use a fresh destination on retry.", file=sys.stderr)
        return 1


# Replaced by build_transfer.py; this template is not a release bundle.
MANIFEST = {}
PAYLOAD = b""

if __name__ == "__main__":
    raise SystemExit(main())
