"""Build a compact Code-view transfer from an audited source distribution."""

import argparse
import base64
import hashlib
import io
import json
import lzma
from pathlib import Path
import re
import tarfile
import textwrap
import tomllib

from transfer_bootstrap import source_files


def build(archive_path: Path, output: Path) -> dict:
    archive_bytes = archive_path.read_bytes()
    # Preserve the exact sdist inventory; never collect a developer's workspace.
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
        metadata_members = [m for m in archive.getmembers()
                            if m.name.count("/") == 1 and m.name.endswith("/pyproject.toml")]
        if len(metadata_members) != 1:
            raise ValueError("Expected one source distribution")
        stream = archive.extractfile(metadata_members[0])
        if stream is None:
            raise ValueError("Missing project metadata")
        project = tomllib.loads(stream.read().decode("utf-8"))["project"]
        version = project["version"]
        if project["name"] != "kairopsis" or not re.fullmatch(r"[0-9]+(?:\.[0-9]+){2}", version):
            raise ValueError("Expected a Kairopsis release version")
        selected = {}
        reused = {}
        # Deployment resolves against the target's approved sources. Keep the
        # upstream lock in the full sdist, never in the compact transfer.
        root_files = {"README.md", "pyproject.toml", "CONTEXT.md", "AGENTS.md", ".python-version"}
        for member in archive.getmembers():
            name = member.name.partition("/")[2]
            if not member.isfile():
                if not member.isdir():
                    raise ValueError("Source distribution contains a non-regular entry")
                continue
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("Unreadable source file")
            data = stream.read()
            if name.startswith("src/kairopsis/static/vendor/"):
                reused[name] = hashlib.sha256(data).hexdigest()
            elif (name in root_files or name.startswith(("src/kairopsis/", "docs/agents/", "docs/adr/"))
                  or name in {"docs/runtime.md", "docs/risk-adjustment.md"}):
                selected[name] = data
        if not reused:
            raise ValueError("Missing browser libraries")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, data in sorted(selected.items()):
            info = tarfile.TarInfo(f"kairopsis-{version}/{name}")
            info.size = len(data)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
    payload = lzma.compress(buffer.getvalue(), preset=9)
    manifest = {"format": 1, "version": version, "file_count": len(selected),
                "contents": "deployment source; upstream lock, developer tests, scripts and datasets omitted",
                "reused_vendor_sha256": reused,
                "sdist_sha256": hashlib.sha256(archive_bytes).hexdigest(),
                "payload_sha256": hashlib.sha256(payload).hexdigest()}
    encoded = base64.b64encode(payload)
    source_files(encoded, manifest)
    template = Path(__file__).with_name("transfer_bootstrap.py").read_text(encoding="utf-8")
    content = template.replace(
        'MANIFEST = {}\nPAYLOAD = b""',
        "MANIFEST = " + repr(manifest) + '\nPAYLOAD = b"""\n'
        + "\n".join(textwrap.wrap(encoded.decode("ascii"), 120)) + '\n"""')
    if len(content.encode("utf-8")) > 500_000:
        raise ValueError("Transfer exceeds the 500 KB Code-view budget; split the payload before publishing")
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    return {**manifest, "transfer_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "transfer_bytes": output.stat().st_size}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.archive, args.output), indent=2))
