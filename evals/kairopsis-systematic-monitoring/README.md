# Systematic monitoring behavior evals

Three independent cases cover bulk setup, insufficient/sparse history, and
retained interpretation. [Fixed grading criteria](rubric.json) belong to the
grader; subjects receive only their REQUEST.md, artifacts and frozen skills.
The original Screening suite and 2026-10-07 reports remain historical evidence.

Execution record: [GPT-5.6 Sol / High, 7 October 2026](../../docs/research/systematic-monitoring-skill-evaluation-2026-10-07.md).

Prepare with the repository environment:

```sh
python scripts/systematic_monitoring_evals.py prepare --output /absolute/fresh/directory
python scripts/systematic_monitoring_evals.py selfcheck --root /absolute/fresh/directory
```

Preparation refuses an existing output directory. It copies both skills, creates
model-valid payloads and engine-generated Evaluations, freezes resource hashes,
and places rubric/truth under `private/`. No network or provider access occurs.
All observations are fabricated; some records simulate distinct live provider
outcomes. Run selfcheck before dispatch and after collection. Output/brief files
are excluded from evidence hashes. The fixture generator is grader-only.

Dispatch one fresh independent subject per case, with no conversation history,
rubric, answers, generator, source or peer results. Give `SUBJECT.md`, the exact
case REQUEST.md and absolute frozen skill paths. Freeze those dispatch messages
before execution; keep their hashes, model/effort, source commit and frozen
resource hashes with results. The parent owns dispatch and grading.

Grade observable decisions and saved artifacts against `private/rubric.json`
and `private/truth.json`, using 0/1/2 for absent-or-wrong/partial/complete per
criterion. Clean pass requires every criterion complete. Report invalid fixtures,
infrastructure blocks and critical failures separately; preserve failed initial
executions if repairing/rerunning. Keyword matches do not establish correctness.
These evals assess workflow/interpretation, not economic or statistical
calibration, live provider behavior or a production reliability estimate.
