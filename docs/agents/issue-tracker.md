# Issue tracker: Local Markdown

Issues and specs live as Markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`.
- Specs live at `.scratch/<feature-slug>/spec.md`.
- Each implementation ticket has its own file:
  `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`.
- Record triage state as a `Status:` line near the top of each issue.
  Use the role strings in `triage-labels.md`.
- Append comments and conversation history under `## Comments`.

## Publishing and fetching

When a skill says "publish to the issue tracker", create the
appropriate file under `.scratch/<feature-slug>/`, creating
directories as needed.

When a skill says "fetch the relevant ticket", read the referenced
file. Resolve issue numbers within the relevant feature directory.

## Wayfinding operations

- Map: `.scratch/<effort>/map.md`, with Notes, Decisions-so-far,
  and Fog sections.
- Child ticket: `.scratch/<effort>/issues/NN-<slug>.md`, numbered
  from `01`, with the question in the body.
- Type: record `research`, `prototype`, `grilling`, or `task`
  in a `Type:` line.
- Status: use `open`, `claimed`, or `resolved` for wayfinding tickets.
- Blocking: record dependencies as `Blocked by: NN, NN`.
  A ticket is unblocked when all listed tickets are resolved.
- Frontier: select the lowest-numbered open, unblocked,
  unclaimed ticket.
- Claim: save `Status: claimed` before starting work.
- Resolve: append the answer under `## Answer`, set
  `Status: resolved`, and add a gist and link to the map's
  Decisions-so-far section.
