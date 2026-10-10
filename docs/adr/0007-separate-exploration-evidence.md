# Keep exploration workspaces and evidence separate from Analysis snapshots

Implemented 10 October 2026. Explore retains explicit symbol/field associations
and full binding revisions around the existing one/two-input Analysis engine.
An immutable ViewResult owns its accepted/excluded sample, statistics and input
evidence; every chart and capture uses that result. Separate exploration entries
in Ideas avoid changing the meaning of legacy Analysis Snapshots.

The first persistent Explore workspace/capture write atomically upgrades the
workspace marker from 2 to 3, preserving its original bytes in
`workspace-schema2.json`. Legacy records are read unchanged and never migrated
in place. Schema2 binaries reject the new marker, protecting evidence they cannot
interpret. This trades downgrade convenience for explicit compatibility and
preservation. Complete version/capture files and hashes precede publication of
the current pointer; unpublished remnants remain harmless after interruption.
