# Systematic monitoring skill evaluation — 7 October 2026

GPT-6.1 Sol at High implemented the guidance. Three fresh GPT-5.6 Sol agents at
High tested frozen copies: **two clean passes, one partial; 29/30 completeness;
no critical failures**. The partial result omitted an overlap explanation; it
correctly reported insufficient history and made no false independence claim.

## Implemented guidance

Unspecified systematic setup defaults to inclusive 1st/99th percentile tails,
three-year reference, 500 eligible prior observations and null bespoke movement
rules. Explicit Z-score monitoring uses absolute Z=3 unless the user chooses
another cutoff. Manual exceptions and explicit analytical choices take precedence.
These are provisional setup profiles, not certified calibration or app defaults.

Both skills clarify Frequency movement versus compatible-Evaluation material
change, prior percentile samples and provenance categories. Screening remains a
separate portable workflow. Runtime watch bands, re-arming and universe-wide
historical calibration remain follow-ups.

## Results

| Case | Score | Observed behavior |
| --- | --- | --- |
| Bulk setup | 10/10 | Three native-unit definitions received percentile defaults; Z-score definitions retained cutoffs 3 and 4. Entire manual exception preserved. All six emitted definitions validate. |
| Insufficient/sparse history | 9/10 | Kept 500 floor; reported 149 scaled and 178 manual priors as insufficient; preserved manual monitoring and weekly/risk/monthly choices. Monthly policy remained unresolved. Omitted the weekly-overlap explanation required by the cadence criterion. |
| Retained interpretation | 10/10 | Separated +8 bp weekly from +1 bp since prior Evaluation; preserved unchanged classification; avoided no-baseline materiality claims; counted four priors from five points; distinguished synthetic/unverified/cache/partial evidence. Saved/read back an exact-run brief. |

The sparse-history `cadence` criterion scored 1/2; all others scored 2/2. Its
monthly-cadence handling was correct. Daily endpoints of weekly changes overlap,
so counts do not establish independent sample support. The skill already states
this; no extra instruction or coached rerun was added after grading.

## Method and evidence

The [three-case suite](../../evals/kairopsis-systematic-monitoring/README.md) and
rubric were fixed before dispatch. Subjects received realistic requests, raw
artifacts and frozen skills without conversation history, source, rubric, answers
or peer results. One offline execution per case; no control arm. Parent grading
was not blinded.

The local machine-readable run record retains exact prompts, rubric, facts,
hashes, complete saved outputs, audits and criterion reasoning. It is not a full
tool transcript. Audits are self-reports; hashes establish artifact preservation,
not complete read/network behavior.

Full run record: `.scratch/skill-evaluation-records/2026-10-07/systematic-monitoring-skill-eval-2026-10-07.json`
(local, excluded from Git and distributions). SHA-256:
`015e4efdde5d5ce191d03a6ad2755f3dd2993a5d5825992c53d8d313b3757b5e`.

Application baseline: `2b238656fad612d5ea2d9125cabc1896344c8ef3`. Updated working-tree
skills are identified by their frozen hashes. All 38 resources remained unchanged;
source skills still match. Parent validated nine Analysis payloads, exact equality
of two manual exceptions, preservation of requested settings, and byte-identical
saved-brief/draft contents.

A constant-gap fixture was corrected before dispatch. Final fixtures use the
real engine for comparisons, percentiles and ineligible previews. All observations
are fabricated, including explicitly simulated live-mode outcomes. Historical
screening evals and frozen evidence were preserved.

## Verification and limits

25 targeted tests passed; both skill validators and 115 portable file/anchor links
passed. Wheel/source builds and resource inventory passed. Fixture checks validate
seven retained and two preview Evaluations, supported preset/manual payloads,
inclusive boundaries, active-rule semantics and the intended endpoint distinction.
Application code was unchanged; the full application suite was not rerun.

These are setup and interpretation checks, not statistical calibration, live
provider verification or a production reliability estimate. Cases differ from
the prior screening batch, so this is not a paired improvement experiment.
Universe-wide point-in-time calibration remains necessary.
