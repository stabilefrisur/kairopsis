# Install from a text file

Keep the existing 0.1.0 installation until the upgrade is verified.
Open [kairopsis-0.2.2.py](kairopsis-0.2.2.py) in GitHub's **Code** tab. Click
inside the code, then press **Ctrl+A**, **Ctrl+C**. Paste into a local file named
`kairopsis-0.2.2.py`. Keep focus inside the code so page navigation and line
numbers are excluded. Expand collapsed code if needed. Save as UTF-8 and
preserve the `.py` extension. Raw access is unnecessary.

Save it outside the old version's replaceable source directory. If an existing
outer workspace contains versioned application source, use its transfer/download
area; keep that workspace open in the IDE. Otherwise create a writable transfer
folder, for example under Documents. Give the agent the file path and the existing
workspace path. The agent chooses the new version's source location after inspection.

The file is under 500 KB. Give your agent its path rather than its contents.
Checksum verification detects a partial copy. If the Code tab cannot expose
the complete file, report that limitation instead of running a partial copy.

In your local IDE's agent mode, paste this task and replace the file path:

```text
Install Kairopsis from the local transfer file:
<absolute path to kairopsis-0.2.2.py>

Inspect the existing workspace, setup records and launchers first. Distinguish
the application source/environment from any outer tooling project/environment;
preserve that outer workspace. Inspect only the first 200 lines of the transfer
file. Use approved Python 3.12 and pass --reuse-from with the old kairopsis
package directory (including src/kairopsis in vendored source when appropriate).
Run --check, then --extract with an explicit fresh version directory alongside
the old source. Read src/kairopsis/docs/agent-setup.md inside the extracted
directory and execute every applicable step, starting at step 1.

Install the patched replacement non-editably in its own application environment.
Preserve existing per-mode configuration, launcher safeguards and automation.
Register both bundled skills in the outer workspace's supported skills folder;
verify the IDE agent discovers them. Follow the bundled setup guide and preserve
existing customized skills when refreshing the version-matched copies.

An existing 0.1.0 installation may already work. Inspect its local change notes,
patches and upgrade automation, package routing, compatibility constraints,
working data provider, configuration, research and launchers. Reconcile local
adaptations using the bundled runbook; verify required behavior. Prepare and
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
