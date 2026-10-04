# Deploy from published upstream source snapshots

The deployment route is a published PyPI source archive obtained through the
configured package mirror and extracted into a local Windows source workspace.
This allows private dependency routing to reuse the existing data-access
distribution while preserving the public `metapyle` import boundary. Local
adaptations, source overrides and the resulting environment lock remain private.

Ship prepared browser assets and the human/agent guides in both distribution
artifacts. The source archive also includes tests, scripts and technical docs.
Installation requires neither GitHub cloning, administrator rights nor Node.js.
Resolve dependencies through the configured mirror and private sources during
setup; launch the installed executable without runtime dependency resolution.

Configuration, credentials and research belong outside the source and installed
package. The single agent setup runbook specifies this target and deployment
route; release-artifact verification remains a separate maintainer activity.
