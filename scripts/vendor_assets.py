"""Maintainer-only asset preparation; never called at installation/startup."""

import hashlib
import io
import json
from pathlib import Path
import tarfile
from urllib.request import urlopen

destination = Path(__file__).resolve().parents[1] / "src/kairopsis/static/vendor"
destination.mkdir(parents=True, exist_ok=True)
packages = {
    "ag-grid-community": ("34.3.1", {
        "dist/ag-grid-community.min.js": "ag-grid-community.min.js",
        "styles/ag-grid.css": "ag-grid.css",
        "styles/ag-theme-quartz.css": "ag-theme-quartz.css",
        "LICENSE.txt": "AG-GRID-LICENSE.txt",
    }),
    "plotly.js-dist-min": ("3.1.0", {
        "plotly.min.js": "plotly.min.js",
        "LICENSE": "PLOTLY-LICENSE.txt",
    }),
}
manifest = []
for package, (version, files) in packages.items():
    url = f"https://registry.npmjs.org/{package}/-/{package}-{version}.tgz"
    archive = urlopen(url).read()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for source, name in files.items():
            member = tar.extractfile(f"package/{source}")
            if member is None:
                raise ValueError(f"Missing required asset {source}")
            contents = member.read()
            (destination / name).write_bytes(contents)
            manifest.append({"package": package, "version": version, "file": name,
                             "source": url, "sha256": hashlib.sha256(contents).hexdigest()})
(destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"Vendored {len(manifest)} assets with licences and SHA-256 hashes")
