"""Exercise copied installers, reuse verification and extraction boundaries."""

import base64
import hashlib
import io
import lzma
from pathlib import Path
import runpy
import subprocess
import sys
import tarfile

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
bootstrap = runpy.run_path(str(SCRIPTS / "transfer_bootstrap.py"))


def archive_bytes(files, extra=None, mode="w"):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode=mode) as archive:
        for name, data in files.items():
            member = tarfile.TarInfo(f"kairopsis-0.2.2/{name}")
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
        if extra is not None:
            archive.addfile(extra)
    return buffer.getvalue()


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    build = runpy.run_path(str(SCRIPTS / "build_transfer.py"))["build"]
    files = {"pyproject.toml": b'[project]\nname="kairopsis"\nversion="0.2.2"\n',
             "uv.lock": b"version = 1\n", "AGENTS.md": b"Agent guidance\n",
             "CONTEXT.md": b"Domain\n", "src/kairopsis/docs/agent-setup.md": b"Setup\n",
             "src/kairopsis/__init__.py": b"# new application\n",
             "src/kairopsis/static/vendor/library.js": b"// unchanged library\n",
             "tests/fixtures/demo/market.csv": b"synthetic\n",
             ".scratch/private.txt": b"must remain excluded\n"}
    archive = tmp_path / "kairopsis-0.2.2.tar.gz"
    archive.write_bytes(archive_bytes(files, mode="w:gz"))
    output = tmp_path / "copied installer.py"
    manifest = build(archive, output)
    package = tmp_path / "old installation" / "kairopsis"
    (package / "static/vendor").mkdir(parents=True)
    (package / "static/vendor/library.js").write_bytes(files["src/kairopsis/static/vendor/library.js"])
    (package / "__init__.py").write_bytes(b"# old application\n")
    return output, package, files, manifest


def run_bundle(bundle, *args):
    output, package, _, _ = bundle
    return subprocess.run([sys.executable, "-I", str(output), "--reuse-from", str(package), *map(str, args)],
                          capture_output=True, text=True)


def test_copy_extract_preserves_old_installation_and_exact_application_bytes(bundle, tmp_path):
    destination = tmp_path / "new installation with spaces"
    result = run_bundle(bundle, "--extract", destination)
    assert result.returncode == 0, result.stderr
    output, package, files, manifest = bundle
    for name, data in files.items():
        if name.startswith("src/"):
            assert (destination / name).read_bytes() == data
    assert not (destination / "tests").exists()
    assert not (destination / ".scratch").exists()
    assert (package / "__init__.py").read_bytes() == b"# old application\n"
    assert (destination / "transfer-manifest.json").is_file()
    assert manifest["transfer_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()


def test_check_has_no_writes_and_accepts_utf8_bom_crlf(bundle, tmp_path):
    output = bundle[0]
    output.write_bytes(b"\xef\xbb\xbf" + output.read_bytes().replace(b"\n", b"\r\n"))
    before = sorted(str(p) for p in tmp_path.rglob("*"))
    result = run_bundle(bundle, "--check")
    assert result.returncode == 0, result.stderr
    assert "Verified" in result.stdout
    assert sorted(str(p) for p in tmp_path.rglob("*")) == before


def test_existing_destination_is_never_overwritten(bundle, tmp_path):
    destination = tmp_path / "existing"
    destination.mkdir()
    result = run_bundle(bundle, "--extract", destination)
    assert result.returncode != 0
    assert list(destination.iterdir()) == []


def test_changed_browser_library_stops_before_extraction(bundle, tmp_path):
    (bundle[1] / "static/vendor/library.js").write_bytes(b"changed")
    destination = tmp_path / "new"
    result = run_bundle(bundle, "--extract", destination)
    assert result.returncode != 0
    assert "Browser library checksum mismatch" in result.stderr
    assert not destination.exists()


def test_auto_discovery_does_not_import_old_application(bundle, tmp_path):
    output, package, _, _ = bundle
    (package / "__init__.py").write_text('raise RuntimeError("old application must not be imported")\n')
    command = ("import sys,runpy; sys.path.insert(0,sys.argv[1]); "
               "sys.argv=sys.argv[2:]; runpy.run_path(sys.argv[0],run_name='__main__')")
    result = subprocess.run([sys.executable, "-I", "-c", command, str(package.parent),
                             str(output), "--check"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_missing_browser_library_does_not_write_destination(bundle, tmp_path):
    (bundle[1] / "static/vendor/library.js").unlink()
    destination = tmp_path / "new"
    result = run_bundle(bundle, "--extract", destination)
    assert result.returncode != 0
    assert "Missing browser library" in result.stderr
    assert not destination.exists()


def test_existing_directory_link_is_not_followed(bundle, tmp_path):
    target = tmp_path / "research"
    target.mkdir()
    sentinel = target / "keep.txt"
    sentinel.write_text("retained research")
    destination = tmp_path / "destination-link"
    destination.symlink_to(target, target_is_directory=True)
    result = run_bundle(bundle, "--extract", destination)
    assert result.returncode != 0
    assert list(target.iterdir()) == [sentinel]
    assert sentinel.read_text() == "retained research"


def test_damaged_payload_stops_before_extraction(bundle, tmp_path):
    output = bundle[0]
    text = output.read_text()
    marker = 'PAYLOAD = b"""\n'
    start = text.index(marker) + len(marker)
    output.write_text(text[:start] + ("A" if text[start] != "A" else "B") + text[start + 1:])
    destination = tmp_path / "new"
    result = run_bundle(bundle, "--extract", destination)
    assert result.returncode != 0
    assert "Payload checksum mismatch" in result.stderr
    assert not destination.exists()


@pytest.mark.parametrize("name", ["../escape", "C:/escape", "src/../escape", "src/CON.txt",
                                 "src/file:stream", "src/bad\\path", "src/trailing."])
def test_unsafe_archive_paths_are_rejected(name):
    raw = archive_bytes({name: b"unsafe"})
    compressed = lzma.compress(raw)
    manifest = {"version": "0.2.2", "payload_sha256": hashlib.sha256(compressed).hexdigest()}
    with pytest.raises(ValueError, match="Unsafe source archive path"):
        bootstrap["source_files"](base64.b64encode(compressed), manifest)


def test_symbolic_link_in_archive_is_rejected():
    link = tarfile.TarInfo("kairopsis-0.2.2/src/link")
    link.type = tarfile.SYMTYPE
    link.linkname = "../../elsewhere"
    compressed = lzma.compress(archive_bytes({}, extra=link))
    manifest = {"version": "0.2.2", "payload_sha256": hashlib.sha256(compressed).hexdigest()}
    with pytest.raises(ValueError, match="only regular files"):
        bootstrap["source_files"](base64.b64encode(compressed), manifest)
