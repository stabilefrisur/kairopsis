# Retained screening contract

Contract: schema version 1. Check the selected app's `/openapi.json`; development
version strings alone do not establish installed capability. This skill uses
the interface below, without importing Kairopsis or accessing providers itself.

## Routes and lifecycle

Identifiers: 1–128 ASCII letters, digits, `_` or `-`. Use returned identities.

| Operation | Route / body | Result |
| --- | --- | --- |
| Start or recover same request | `POST /api/screenings`, `{"request_id":"<durable caller ID>"}` | 202, stable run status; same request ID returns same run |
| List retained runs | `GET /api/screenings?limit=20` | `{"runs":[status,…]}`; limit 1–100, default 20, newest attempts first |
| Read exact run | `GET /api/screenings/{run_id}` | Status; includes `manifest` when completed |
| Read retained evaluation/baseline | `GET /api/screenings/{run_id}/evaluations/{evaluation_id}` | Full Evaluation retained in that run |
| Save new brief | `POST /api/screenings/{run_id}/briefs`, `{"markdown":"…"}` | 201, brief record; new identity each write |
| Read brief | `GET /api/screenings/{run_id}/briefs/{brief_id}` | Same brief record |

GETs do not refresh. Start evaluates all saved Analyses, freezing definitions,
resolved Data Series, monitoring membership, comparison IDs and Idea references
at the start. Manual/daily refreshes also retain runs; previews do not. Reviewing
a run uses its captured universe, independent of subsequent workspace edits.

Status fields: `schema_version`, `run_id`, `request_id` (nullable for non-agent
triggers), `trigger` (`agent`, `manual` or `daily`), `status`, `mode` (`mock` or
`live`), `timezone`, `application_version`, `attempted_at`, `completed_at`,
`path`, `manifest_path`, `error`. Times include timezone offsets; completion time
is null while running.

- `running`: processing/retention not yet finished. Poll the pinned run.
- `completed`: the complete manifest and referenced evidence were published.
  Source failures can coexist with this state.
- `failed`: processing/publication failed; prior completed runs remain usable.
- `interrupted`: an unfinished earlier process was identified on restart.

Stop polling on a terminal state. A timeout or lost connection is uncertainty,
not permission to start another request. Reuse the original request ID/state;
once the run ID is known, resume GETs for that run. A brief POST has no caller
idempotency key: an uncertain brief write can produce another version on retry.
Use returned brief IDs/paths for readback; inspect the run's `briefs/` directory
when available before repeating an uncertain write.

## Portable folder and manifest

Runs live under `workspace/screenings/<run_id>/`. For copied folders, the selected
folder is the root: relative references remain authoritative; original absolute
status paths may point to the former machine. `status.json` identifies unfinished
runs. `manifest.json` is the completed publication marker; partial evidence
files alone cannot establish completion. Require supported schema, completed
state and the pinned ID where one was supplied.

Manifest fields include the status identity/times, `universe_count`,
`monitored_count`, `coverage`, `rows` and `evidence`. `evidence` maps every retained
evaluation ID to its relative `evaluations/<evaluation_id>.json` file. Each row
retains its displayed evaluation and the immediate baseline used for that
comparison. A deeper `baseline_id` inside a copied baseline is historical
metadata unless also present in `evidence`; use the row's `baseline_ref` and
the evidence index. This bounds copies across repeated runs. Original evaluation
bytes remain unchanged. Rows contain relative `definition_ref`
and `attempt_ref` plus evaluation references. Read only contained relative
paths; check resolved paths remain within the chosen run, including symlinks.
Missing referenced files make that claim unverified, even if a damaged copied
manifest says completed. Keep report writes under `briefs/`.

`coverage.all` and `coverage.monitored` each contain `total`, `evaluated`,
`failed`, `retained`, `eligible`, `flagged`, `quiet` and `provider_outcomes`.
Outcome counts cover `synthetic`, `fresh`, `cache`, `partial`, `failed`,
`unverified` and `exception`. These are overlapping dimensions: retained rows
can also count as failed, and eligibility/quiet are not provider-success counts.
Read all monitored rows and check totals, including a zero-monitored run.

### Compact rows

| Fields | Meaning |
| --- | --- |
| `analysis_id`, `revision`, `name`, `economic_rationale`, `monitored` | Captured Analysis identity, question and membership |
| `inputs` | Ordered input records: `id`, `revision`, `name`, `unit`, `currency`, `basis` |
| `status`, `failure`, `retained` | `evaluated`, `retained` or `failed`; attempted failure differs from displayed older evidence |
| `eligible`, `flagged` | Current eligibility and eligible attention flag; retained older rows have both false |
| `finding`, `reasons`, `conditions`, `condition_keys` | App's existing classification, novelty reasons and configured conditions |
| `current`, `unit`, `input_units`, `change`, `change_start`, `percentile` | Displayed metrics and actual change start; absent metrics are valid for failed rows with no older evidence |
| `observation_date`, `input_dates`, `evaluated_at` | Actual displayed evidence dates; each Analysis/input has its own dates |
| `limitations`, `sensitivity` | Freshness, estimation, mathematical or interpretation qualifications |
| `provider` | New attempt's `outcome`, `attempted_at`, `completed_at`; not provenance of a displayed retained value |
| `evaluation_id`, `current_evaluation_id`, `retained_evaluation_id`, `baseline_id` | Displayed, new, older retained and comparison identities; IDs may be null |
| `detail_ref`, `baseline_ref`, `definition_ref`, `attempt_ref` | Run-relative current/displayed evidence, baseline, captured definition and failed/partial attempt evidence |
| `idea_refs` | Captured Idea `id`, `title`, `version`, `chart_ids`; a related-work reference, not a captured thesis |

Full Evaluation contains `definition` (settings, captured rationale and resolved
inputs), `request`, `data` (observations, provenance, outcomes/failures/times),
`points`, `fit`, `adjustment_estimates`, `standardization_estimate`, metrics and
finding fields. Points retain actual input dates, change endpoints, transformed
inputs and risk scales. Failed attempt files contain `definition`, `request`,
`data` and `failure`; a failed attempt may have no Evaluation. Refer to full
evidence only as needed for selected themes and challenges, rather than loading
every full history into the summary review.

For `retained` rows, the row's name/revision/rationale/inputs describe the newly
attempted definition, while displayed metrics and `detail_ref` belong to the
older Evaluation. Interpret those metrics using that older `definition`,
rationale and dates; keep the attempted definition as separate context. The
row's `baseline_id` and `baseline_ref` identify the baseline used by that older
displayed Evaluation, when present. Neither record is fresh evidence of the
failed attempt.

## Interpretation cautions

- **Eligibility:** use the retained app decision. Unverified retrieval, stale
  observations, cache/partial outcomes and previous retained values cannot be
  promoted to current eligible Flags. Fresh retrieval does not create a common
  market as-of date. Mock/synthetic findings demonstrate calculations, not live
  market developments. Read actual per-input provenance and limitations.
- **Novelty:** `new` and `changed` carry the app's reasons for eligible native
  observation developments. `condition` records a condition without a compatible
  baseline. `unchanged` is persistent, `quiet` has no current condition,
  `correction` denotes corrected/backfilled history, `incompatible` changed
  definition/method/mode, and `unavailable` an ineligible/unavailable result.
  Retained rows keep their older classification: it never establishes novelty
  in the failed current attempt. Conditions can remain visible without novelty.
- **Change:** with Measure Level, `change` is the completed result's difference
  over Frequency using its actual endpoints. With Measure Change or Percentage
  change, it is the current measured result, not necessarily acceleration.
  Compare the retained baseline only under the captured compatible definition;
  baseline comparison and Frequency change are different comparisons.
- **Materiality:** percentiles and Z-scores describe historical rarity under
  captured reference samples. Interpret economic size in the output units and
  Comparison Basis. Pair input order controls sign. Scaling/reference changes,
  small or signed ratio denominators, refits and standardization can dominate
  apparent movement. Inspect relevant estimates and strongest contrary evidence.
- **Research:** captured rationale is a hypothesis, not proof. Descriptive
  regression does not establish causality, a hedge or a strategy backtest;
  overlapping Frequency samples and shared inputs do not provide independent
  corroboration. Claims about external causes need separately supplied evidence.
  Idea references alone cannot establish their historical thesis or conviction.

## Portable helper

Run with Python 3.9 or later from any working directory. Replace `SKILL` with
this copied skill folder's absolute path; `STATE` is a new durable local JSON
path for one user request. It requires only the standard library.

```text
python SKILL/scripts/screening.py start --base-url http://127.0.0.1:8000 --state STATE
python SKILL/scripts/screening.py status --state STATE --wait 30
python SKILL/scripts/screening.py list --base-url http://127.0.0.1:8000 --limit 20
python SKILL/scripts/screening.py read --base-url http://127.0.0.1:8000 --run-id RUN
python SKILL/scripts/screening.py evidence --base-url http://127.0.0.1:8000 --run-id RUN --evaluation-id EVALUATION
python SKILL/scripts/screening.py brief --base-url http://127.0.0.1:8000 --run-id RUN --markdown DRAFT.md
python SKILL/scripts/screening.py read --folder COPIED_RUN --run-id RUN
python SKILL/scripts/screening.py evidence --folder COPIED_RUN --evaluation-id EVALUATION
python SKILL/scripts/screening.py brief --folder COPIED_RUN --markdown DRAFT.md
```

`start` persists its request ID before the first network call. Repeating it
with the same state GETs the pinned run if known, or resubmits the same request
ID to recover an uncertain response. It rejects changing the target URL. `status`
waits at most 45 seconds plus one bounded HTTP call, then returns the actual
state, including running. Each HTTP call has a 15-second timeout. Existing-run
commands perform GETs/local reads only; `brief` creates a new report and verifies
its content by readback. Offline brief files are unique and never replace
evidence. The helper enforces identity/schema/containment basics; the agent still
must check coverage, evidence completeness and interpretation.
