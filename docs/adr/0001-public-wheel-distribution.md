# Deploy from published upstream source snapshots

The deployment route is a release source snapshot extracted into a local Windows
source workspace. When the configured mirror lacks the release, transfer the
deployment subset of that source distribution in a self-extracting Python text
file viewed in GitHub's Code tab. It carries application code, guides and skills;
unchanged browser libraries are reused from an existing installation only after
hash verification. Developer tests and datasets stay in the full source archive
to keep the copyable file small. The extractor verifies the payload and libraries,
writes only to a new directory and performs no downloads or installation.
This allows private dependency routing to reuse the existing data-access
distribution while preserving the public `metapyle` import boundary. Local
adaptations, source overrides and the resulting environment lock remain private.

Ship prepared browser assets and the human/agent guides in both distribution
artifacts. The source archive also includes tests, scripts and technical docs.
Installation requires neither GitHub cloning, administrator rights nor Node.js.
Resolve dependencies through the configured mirror and private sources during
setup; launch the installed executable without runtime dependency resolution.

Configuration, credentials and research belong outside the source and installed
package. The single agent setup runbook handles an existing installation, private
dependency routing, research backup, verification and launcher replacement. It
discovers target-specific values locally and keeps them out of public artifacts.
Release-artifact verification remains a separate maintainer activity.
