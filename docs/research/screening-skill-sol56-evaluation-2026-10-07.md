# Screening skill evaluation — GPT-5.6 Sol, 7 October 2026

Five fresh GPT-5.6 Sol agents at High effort tested the frozen screening skill:
**four clean passes, one partial pass**. A sixth case, starting a new screening
and recovering a lost response, was blocked before subject dispatch. No skill
changes were made.

The agents handled broad coverage, captured rationale, incomplete evidence,
corrections and unsupported formats. The quiet-run brief reached the right
conclusion but used a between-run threshold to explain a weekly move. Smaller
wording problems concerned percentile sample size and synthetic provenance.

## Results

| Case | Result | Evidence |
| --- | --- | --- |
| Start, retain and recover a lost response | Blocked; unscored | Automatic execution review rejected the helper's `start` command during fixture smoke testing. No subject dispatched. |
| 300 rows, 240 monitored | 10/10 | Reconciled scope; selected the late-row development; grouped shared exposure; checked contrary evidence; excluded 60 unmonitored rows; ignored an embedded instruction. |
| Incomplete screening | 10/10 | Reconciled overlapping counts; treated the retained result under revision 1 rationale, separately from the failed revision 2 attempt; did not mistake one eligible quiet result for complete coverage. |
| Economic interpretation | 10/10 | Distinguished a +24 bp new move, historical correction and persistent condition; identified the near-zero denominator behind 50×; preserved captured Idea references without inventing a thesis. |
| Quiet screening | 9/10; partial | Correctly reported all five eligible, zero flags and synthetic scope. Its explanation misapplied the 5 bp between-run material-change threshold to the weekly change despite no retained comparison baseline. |
| Unsupported schema | 10/10 | Rejected schema 99, preserved the requested run, wrote no brief and did not substitute the older valid decoy. |

Scores follow the [fixed rubric](../../evals/kairopsis-screening/evals.json):
five criteria, each 0–2, with a clean pass requiring 10/10 and no protocol breach.
The quiet case's critical `conclusion` criterion scored 1: correct outcome,
partially unsupported explanation. No critical criterion scored 0. Total
completeness was 49/50 across executed cases; this is not a reliability estimate.

## Findings worth acting on

1. **Separate two kinds of change.** The quiet brief compared a 0.5 bp weekly
   decline with both the 10 bp move threshold and the 5 bp material-change
   threshold. Only the first uses that weekly change. `material_change` concerns
   movement since a compatible retained Evaluation, which this case lacked.
   The brief did acknowledge that no comparison baseline was captured. Its
   no-attention conclusion remains supported by the retained quiet findings.
2. **Name the percentile reference accurately.** The scale and quiet briefs
   described percentiles as ranks in a five-point history. Five points were
   retained, but the reference sample excludes the current point: four prior
   values. The reported percentile numbers were correct. Record this as an
   ambiguity, not evidence of a wrong calculation; the fixed criteria did not
   specifically test the reference-sample count, so no extra deduction was made.
3. **Keep provenance categories precise.** The scale brief called the evidence
   synthetic and “unverified.” All monitored provider outcomes were `synthetic`,
   with zero `unverified` outcomes. This could mean unverified against live data,
   but that distinction should be explicit. The brief correctly disclosed mock
   mode and made no live-market claim; this is an advisory wording issue.

The evaluated skill remained frozen during this batch. A follow-up revision
should clarify these points and add a case where weekly and between-run changes
have different endpoints. Repeat the batch after that revision; do not reuse these scores as
evidence for an untested update.

The subsequent [systematic monitoring evaluation](systematic-monitoring-skill-evaluation-2026-10-07.md)
records the revised guidance and separate cases; it does not replace these scores.

## Method and retained evidence

- Application and skill baseline: commit `2b238656fad612d5ea2d9125cabc1896344c8ef3`.
- Six cases and rubric fixed before dispatch. Five subjects received no prior
  conversation, rubric, private answers, peer results or application source.
  Each received its request, frozen screening and analysis skills, and
  [resource restrictions](../../evals/kairopsis-screening/subject.md).
- The fixture engineer was separate from the subjects. The parent graded the
  artifacts without blinding. One execution per case; no control arm or retries
  to improve model scores. The exact dispatched prompts and skill hashes are
  retained in the local machine-readable record described below.
- That file also retains complete saved briefs, resource audits, per-criterion
  reasoning, fixture facts, integrity hashes and the compatibility response.
  It is not a full tool transcript. Resource audits are subject self-reports;
  neither a listed ID nor a parsed manifest proves cognitive review of every row.
- Four unique briefs were saved under their selected runs and read back according
  to subject audits; parent checks confirmed saved contents matched working
  drafts. Unsupported-schema handling correctly produced no brief.
- All 669 original fixture files and all seven frozen skill files retained their
  recorded hashes. Audited resources stayed within the permitted case and skill
  folders. These checks establish preserved artifacts, not a complete network
  or read-access trace. No live provider was part of the test.

Full run record: `.scratch/skill-evaluation-records/2026-10-07/screening-skill-sol56-eval-2026-10-07.json`
(local, excluded from Git and distributions). SHA-256:
`a3641786db6de13706393a04f1d5db1663f7adaba64f058660cd26e4b4e9ca0a`.

## Fixture and package validation

The [generator](../../scripts/screening_skill_evals.py) prepares six deterministic
cases and a loopback-only API simulator. Self-checking validated seven supported
manifests, including decoys, and 331 Evaluation records. Checks cover schema,
reference containment, coverage, arithmetic, observation dates, shared-input
consistency, quiet thresholds and baseline classifications. All observations and
condition metadata are fabricated; this does not test real provider retrieval or
the production screening service.

Initial candidate fixtures contained inconsistent quiet percentiles, dates,
shared inputs, ratio units and answer hints. These were repaired before any
subject execution, then regenerated, checked and frozen. No scored run was
silently repaired or replaced.

The helper compiled, fixture self-checks passed, and wheel/source builds passed.
At that stage, the source archive included eval definitions, subject instructions
and the generator. Current Hatchling builds exclude eval resources from distributions.
Application code and shipped skills were unchanged; the full application
test suite was not rerun for these evaluation-only additions.

## Execution block

Automatic approval review rejected the helper's `start` command during the
disposable fixture smoke test, reporting a policy block without a reason. The
process did not start. No alternative execution route was attempted; the owned
fixture server was stopped. Case 01 remains reusable but untested by a subject.
The new-run, retention and retry workflow therefore has no model-evaluation
result from this batch.
