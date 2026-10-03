# Domain docs

## Layout and reading rules

This repo uses a single-context layout:

- `CONTEXT.md` at the repo root holds domain terminology.
- `docs/adr/` holds architectural decision records.

Before exploring the codebase, read `CONTEXT.md` and the ADRs
relevant to the area being explored.

If these files do not exist, proceed silently. The domain-modeling
skill creates them when terms or decisions are resolved.

## Vocabulary

Use the terms defined in `CONTEXT.md` when naming domain concepts
in issues, proposals, hypotheses, and tests.

If a needed concept is absent, reconsider whether it belongs in
the domain or note the gap for domain-modeling.

## Decision conflicts

If a proposal contradicts an existing ADR, name that ADR and
explain why the decision should be reconsidered.
