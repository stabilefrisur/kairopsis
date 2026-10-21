# Install from a text file

Keep the existing 0.1.0 installation until the upgrade is verified.
Open [kairopsis-0.2.2.py](kairopsis-0.2.2.py) in GitHub's **Code** tab and copy
the complete code into a local file named `kairopsis-0.2.2.py`. Expand collapsed
code if needed; exclude line numbers and page navigation. Save as UTF-8 and
preserve the `.py` extension. Raw access is unnecessary.

The file is under 500 KB. Give your agent its path rather than its contents.
Checksum verification detects a partial copy. If the Code tab cannot expose
the complete file, report that limitation instead of running a partial copy.

In your local IDE's agent mode, paste this task and replace the file path:

```text
Install Kairopsis from the local transfer file:
<absolute path to kairopsis-0.2.2.py>

Use the existing Kairopsis installation's Python 3.12 and approved package
tooling. Inspect only the first 200 lines of the transfer file, run it with
--check, then --extract into a fresh
per-user source directory. Read src/kairopsis/docs/agent-setup.md inside that
directory and execute every applicable step, starting at step 1. If using
another Python, locate the old kairopsis package and pass --reuse-from with
that package directory on both transfer commands.

An existing 0.1.0 installation may already work. Inspect it for package routing,
the working data provider, configuration, research and launchers. Prepare and
verify its replacement before switching the launcher; preserve research and a
recoverable backup. You own all technical work through a tested launcher, stop
method and handoff. Ask only for information or permissions you cannot discover.

Keep environment details, identities, credentials, logs, local changes and
research private. Never put them in web searches, public issues, repositories
or uploads. Use only the established package mirror/private sources. Report
exact blockers locally; do not silently change dependency pins or providers.
```

The bundle carries all current application code, guides, skills and build
metadata. It reuses only unchanged browser libraries from the old installation,
after checking every file's SHA-256. It copies no old application code,
configuration or research. Developer tests, scripts and sample datasets remain
in the full source distribution. It contains no interpreter or Python
dependencies. Extraction makes no network requests.
The embedded checksum detects payload corruption; it is not a digital signature.
Obtain the file from the intended repository revision.

The bundled [agent setup runbook](../src/kairopsis/docs/agent-setup.md) owns all
installation steps. The agent uses caches and approved package sources for
dependencies; an earlier successful installation does not prove that every new
requirement is available. Target checks establish actual installation success.
