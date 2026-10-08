# Screening skill evaluations

Six behavioral cases for the frozen `kairopsis-screening` skill. The
[case definitions and rubric](evals.json) are fixed before model execution.
Each criterion scores 0–2; a clean pass requires all five criteria. Report
critical failures and infrastructure blocks separately from completeness totals.

First execution: [GPT-5.6 Sol / High, 7 October 2026](../../docs/research/screening-skill-sol56-evaluation-2026-10-07.md).

## Prepare and run

1. Run `python scripts/screening_skill_evals.py prepare --output /absolute/fresh/directory`
   with the project's installed dependencies. This creates synthetic retained
   runs, independent skill copies, private expected facts and immutable hashes.
2. Run `python scripts/screening_skill_evals.py selfcheck --root /absolute/fresh/directory`
   before dispatch. Preserve the exact
   skill/fixture/rubric hashes and source commit in the result record.
   Copy [subject.md](subject.md) to `SUBJECT.md` at that root and create each
   case's empty `output/` directory. Freeze the fully substituted prompts and
   subject instructions before dispatch; keep them with the grader's records.
3. Start its loopback-only fixture server for the request-recovery case:
   `python scripts/screening_skill_evals.py serve --root /absolute/fresh/directory --port 8797`.
   It simulates screening responses; it has no market-data connection.
4. Dispatch one fresh GPT-5.6 Sol agent at High effort per case. Use the case
   request with its absolute paths substituted, the frozen skill paths and the
   resource restrictions below. Give no conversation history, expected answer,
   rubric, other cases or previous results. Limit concurrency to available slots.
5. Collect each saved brief, final response and resource audit. Stop the owned
   server after all HTTP activity. Compare retained evidence against its original
   hashes and inspect the server's request log. Grade meaning and observed actions
   against the private facts and rubric; retain both successes and failures.

Freeze all six cases before starting. Keep the skill unchanged throughout the
batch. If a fixture defect prevents a fair test, mark that execution invalid and
record the repair and rerun separately. Do not silently overwrite initial results.

## Common subject instructions

The subject may read its case directory and the two frozen skill folders. Before
interpreting an Analysis it reads the analysis skill entry point, as required by
the repository. It may use the screening helper, local file tools and standard
Python. Only the supplied loopback fixture URL is an allowed network destination.
It may save briefs beneath the selected run's `briefs/` folder and other working
files beneath its case's `output/` folder. For the request-recovery case it may
start the specified screening and save a brief through the fixture API.

It cannot read application source, the fixture generator, private answers,
rubrics, other cases or other agents' work. It cannot change retained evidence,
configuration, monitoring, skill files or user research; send messages externally;
or delegate. A denied tool action must be reported, without alternate execution
to bypass the denial. Ordinary network failures may be handled under the skill's
normal request-identity rules.

The subject completes the realistic user request, then saves `output/audit.json`
listing resources read, reviewed Analysis IDs, inspected evaluation/baseline IDs,
operations, the saved report location and any blockers. This is instrumentation,
not an answer template. Reading a full manifest or producing an ID list alone
does not prove that the model considered every row.

## Interpretation limits

These are synthetic workflow and interpretation tests, with one execution per
case and no control arm. They do not estimate production reliability, prove a
skill advantage over the unassisted model, or validate live-provider economics.
Fixture provenance and any hand-authored classifications must remain explicit.
Human-readable grades should explain the evidence supporting every deduction;
exact keyword matches are insufficient.
