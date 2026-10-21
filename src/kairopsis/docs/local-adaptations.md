# Preserve local adaptations during an upgrade

Use this branch of the [setup runbook](agent-setup.md) when the existing
installation has local patches, metadata changes or upgrade automation. Keep
all discovered details, patches and comparison results in private records.
Installing a clean old version is unnecessary when the transfer's browser-library
checks pass; those checks do not depend on old Python source or build metadata.

## Inventory before changing the installation

Read local change notes and upgrade instructions; inspect the actual patches,
modified source, project metadata, lockfile and launchers. Summaries identify
intent but cannot establish the complete change. Back up these inputs and record
the old interpreter, provider revision and dependency versions.

For a workspace wrapping vendored source, distinguish the durable workspace from
the replaceable version directory. Preserve the outer tooling project/environment
and its launch/configuration/backup automation. Treat private patch files as the
authored changes: re-derive them for the new pristine snapshot, verify clean
application to a separate copy, and retain versioned old/new patches for rollback.
Record actual source and import paths; a source tarball and a non-editable app
wheel can coexist without making the app a dependency of the outer project.

For every adaptation, record its purpose, affected files, expected behavior,
replacement disposition and verification result. Classify it as already upstream,
still required, obsolete with evidence, or unresolved. Include dependency/build
changes, runtime changes and surrounding launch/configuration automation.

If an existing upgrade command assumes a new package is available from a mirror,
adapt its acquisition stage to the verified transfer. Retain its applicable
patching, backup and acceptance stages. Inspect the command before invoking it.

**Done:** every local change is accounted for and recoverable; required behavior
and the means of checking it are explicit.

## Re-derive changes against the new source

Keep the extracted source snapshot pristine in a private backup. Make the smallest
necessary changes in the replacement source, preserving new upstream behavior.
Check context even when an old patch applies cleanly. Copying an old module or
entire project configuration over its replacement can discard unrelated fixes.
Apply patches before the non-editable install. If a patch changes afterward,
rebuild/reinstall as described in setup step 5 and compare installed bytes before
testing; editing vendored source alone does not update the running wheel.

Retain validated package constraints and private routing as described in setup
step 4. A renamed provider's distribution metadata and its import namespace both
matter. Keep the existing backend when it already satisfies the local need.
Cosmetic metadata differences do not require functional patches.

For runtime changes, read the current implementation and relevant bundled skills
and runtime documentation. Define focused regression checks from each patch's
intended behavior before changing it. Preserve new request/configuration handling,
error reporting and resource cleanup. Record assumptions requiring provider
evidence; an old patch's successful execution does not validate those assumptions.

**Done:** each required change has a narrowly scoped replacement and regression
checks; superseded changes are dropped with evidence. Unresolved requirements
remain blockers to switching the working installation.

## Verify behavior before cutover

Use separate copies of the research workspace for old and new versions. Compare
equivalent requests with fixed inputs or retained observations where possible;
changing live data is not itself a regression. Keep test code and evidence private.
The transfer omits the upstream developer test suite, so create focused local
checks and exercise the application's API/UI rather than assuming tests shipped.

For an adapter or findings change, check returned values, observation dates,
provenance, eligibility and affected findings, including Current, Change and
Standing where applicable. Cover successful retrieval, missing/partial data,
failures, stale observations and legacy bindings. Confirm documented provider
dates take precedence over inferred dates. Cache bypass alone establishes neither
native observation dates nor freshness; keep any provider-specific inference
scoped to evidence and preserve conservative behavior elsewhere.

Use the Analysis skill before selecting calculation settings or interpreting
findings. Preserve stale-data and eligibility safeguards. Check other behavior
the old patch did not target, including captured request definitions and local
file handling. Record unavailable checks as unverified.

**Done:** required behavior and failure safeguards pass against the replacement;
every adaptation has evidence or an explicit unresolved blocker. Resume the
setup runbook's research checks and launcher cutover only when required checks pass.
