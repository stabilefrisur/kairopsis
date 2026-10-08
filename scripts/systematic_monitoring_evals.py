#!/usr/bin/env python3
"""Prepare three offline monitoring behavior cases; grader-only fixture mechanics."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kairopsis.analytics import condition_rules, evaluate  # noqa: E402
from kairopsis.evaluation_comparison import compare  # noqa: E402
from kairopsis.models import (  # noqa: E402
    AnalysisDefinition, AnalysisSettings, DataRequest, DataResponse, Evaluation,
    Observation, ResolvedDefinition, SeriesBinding, SeriesResult,
)
from kairopsis.screenings import coverage  # noqa: E402

SUITE = ROOT / "evals/kairopsis-systematic-monitoring"
AS_OF = date(2026, 9, 30)
NOW = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
DEFAULT = dict(calculation_contract="input-pipeline-v2", history_years=3,
               minimum_history=500, upper_percentile=99, standardization="none",
               move_threshold=None, material_change=None, calibration="configured-native-v1")


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def binding(key: str, unit: str = "bp", cadence: str = "Daily native observations") -> SeriesBinding:
    return SeriesBinding(id=key, name=key.replace("-", " "), source="Offline fabricated fixture",
        instrument=key, field="value", unit=unit, currency="USD",
        basis=dict(label="Fixture USD comparison", currency="USD", reference_curve="Fixture curve",
                   adjustment="No conversion; fabricated observations"), description=cadence)


def days(count: int) -> list[date]:
    result, day = [], AS_OF
    while len(result) < count:
        if day.weekday() < 5:
            result.append(day)
        day -= timedelta(days=1)
    return list(reversed(result))


def run_eval(definition: ResolvedDefinition, dates: list[date], values: list[list[float]],
             identity: str, outcome: str = "synthetic", carried: int | None = None) -> Evaluation:
    captured_at = datetime.combine(dates[-1], NOW.timetz())
    data = DataResponse(mode="mock" if outcome == "synthetic" else "live",
        outcome=outcome, requested=tuple(b.id for b in definition.inputs), attempted_at=captured_at,
        completed_at=captured_at, series=tuple(SeriesResult(binding=b,
            provenance="Fabricated offline fixture" if outcome == "synthetic" else f"Offline simulated {outcome} provider record",
            observations=tuple(Observation(date=d, observed_on=dates[index - 1] if index == carried else d, value=v)
                               for index, (d, v) in enumerate(zip(dates, series))))
            for b, series in zip(definition.inputs, values)))
    result = evaluate(definition, data, DataRequest(bindings=definition.inputs, start=dates[0], end=dates[-1]), captured_at)
    return result.model_copy(update={"id": identity})


def resolved(key: str, inputs: tuple[SeriesBinding, ...], settings: AnalysisSettings,
             calculation: str = "level") -> ResolvedDefinition:
    return ResolvedDefinition(id=key, revision=1, name=key.replace("-", " "), inputs=inputs,
        calculation=calculation, settings=settings,
        economic_rationale="Examine quoted compensation or repricing; composition and liquidity can explain differences.")


def request(case: Path, text: str) -> None:
    case.mkdir(parents=True)
    (case / "output").mkdir()
    (case / "REQUEST.md").write_text(text.strip() + "\n", encoding="utf-8")


def make_bulk(root: Path) -> dict:
    case = root / "cases/01-bulk"
    request(case, """Set up systematic monitoring for the definitions in setup.json. Use shared
defaults for unspecified monitoring choices. Preserve the saved Manual gap exception
in existing.json exactly; it belongs to this universe. Return offline draft payloads
and a concise setup record under output/. Include the preserved exception in the
record. Assess readiness from supplied catalogue/history; no app writes requested.
All observations are fabricated for this offline exercise.""")
    inputs = [binding(key) for key in ("hy", "ig", "agency")]
    history = days(650)
    write(case / "catalogue.json", inputs_to_json(inputs))
    write(case / "history.json", {b.id: [dict(date=d.isoformat(), observed_on=d.isoformat(), value=100 + k * 40 + (i * (k + 1)) % 19)
        for i, d in enumerate(history)] for k, b in enumerate(inputs)})
    setup = [
        dict(id="hy-level", name="HY compensation", calculation="level", series_ids=["hy"],
             settings=dict(measure="level", horizon="day")),
        dict(id="hy-ig-gap", name="HY versus IG", calculation="difference", series_ids=["hy", "ig"],
             settings=dict(measure="level", horizon="week")),
        dict(id="agency-weekly", name="Agency weekly repricing", calculation="level", series_ids=["agency"],
             settings=dict(measure="change", horizon="week")),
        dict(id="gap-z", name="Gap unusualness", calculation="difference", series_ids=["hy", "ig"],
             settings=dict(measure="level", horizon="month", standardization="zscore")),
        dict(id="hy-z-four", name="HY unusualness", calculation="level", series_ids=["hy"],
             settings=dict(measure="level", horizon="day", standardization="zscore", zscore_threshold=4)),
    ]
    write(case / "setup.json", setup)
    custom = AnalysisDefinition(id="manual-gap", name="Manual gap exception", calculation="difference",
        series_ids=("hy", "ig"), monitored=True, economic_rationale="Compare HY compensation with IG; credit mix matters.",
        settings=AnalysisSettings(calculation_contract="input-pipeline-v2", horizon="week", history_years=6,
            minimum_history=60, upper_percentile=92, move_threshold=5, material_change=2))
    write(case / "existing.json", custom)
    return dict(default_ids=["hy-level", "hy-ig-gap", "agency-weekly"], zscore_ids={"gap-z": 3, "hy-z-four": 4},
                preserved_definition=custom.model_dump(mode="json"), observation_rows=650,
                native_prior_count=649, weekly_change_prior_count=644)


def inputs_to_json(inputs: list[SeriesBinding]) -> list[dict]:
    return [b.model_dump(mode="json") for b in inputs]


def make_history(root: Path) -> dict:
    case = root / "cases/02-history"
    request(case, """Set up systematic monitoring for setup.json using the supplied catalogue and
histories. Assess readiness and preserve the analytical choices there. existing.json
is my Short manual monitor: keep its custom settings and monitoring enabled.
Return offline draft payloads and a concise readiness record under output/.
No app writes requested. All observations and preview records are fabricated.""")
    daily, monthly = binding("short-daily"), binding("monthly-native", cadence="Native monthly observations only; no daily carry")
    history = days(180)
    monthly_days = [date(year, month, 28) for year in range(2023, 2027) for month in range(1, 13)
                    if date(year, month, 28) <= AS_OF]
    write(case / "catalogue.json", inputs_to_json([daily, monthly]))
    write(case / "history.json", {daily.id: [dict(date=d.isoformat(), observed_on=(history[i - 1] if i == 30 else d).isoformat(), value=100 + i % 17)
        for i, d in enumerate(history)], monthly.id: [dict(date=d.isoformat(), observed_on=d.isoformat(), value=200 + i % 13)
        for i, d in enumerate(monthly_days)]})
    settings = dict(measure="change", horizon="week", fit_years=6, risk_adjustment=dict(method="volatility",
        estimation_measure="change", lookback_years=1, minimum_samples=20, weighting="equal"))
    write(case / "setup.json", [dict(id="weekly-scaled", name="Weekly spread repricing", calculation="level",
        series_ids=[daily.id], settings=settings), dict(id="monthly-level", name="Monthly compensation",
        calculation="level", series_ids=[monthly.id], settings=dict(measure="level", horizon="month"))])
    custom = AnalysisDefinition(id="short-manual", name="Short manual monitor", series_ids=(daily.id,), monitored=True,
        settings=AnalysisSettings(calculation_contract="input-pipeline-v2", history_years=6, horizon="week",
            minimum_history=500, upper_percentile=92, move_threshold=5, material_change=2))
    write(case / "existing.json", custom)
    preview_settings = AnalysisSettings(**(DEFAULT | settings))
    preview = run_eval(resolved("weekly-scaled", (daily,), preview_settings), history,
                       [[100 + i % 17 for i in range(len(history))]], "preview-weekly-scaled", carried=30)
    write(case / "previews/weekly-scaled.json", preview)
    manual = run_eval(resolved(custom.id, (daily,), custom.settings), history,
                      [[100 + i % 17 for i in range(len(history))]], "preview-short-manual", carried=30)
    write(case / "previews/short-manual.json", manual)
    return dict(preserved_definition=custom.model_dump(mode="json"), raw_rows=180,
                eligible_prior_count=sum(p.eligible and p.value is not None for p in preview.points[:-1]),
                preview_eligible=preview.eligible, manual_eligible=manual.eligible,
                monthly_rows=len(monthly_days), monthly_latest=monthly_days[-1].isoformat())


def compact(value: Evaluation, baseline: Evaluation | None = None, *, retained: bool = False) -> dict:
    shown = value.model_dump(mode="json")
    fields = ("evaluated_at", "current", "unit", "input_units", "change", "change_start", "percentile",
              "observation_date", "input_dates", "limitations", "sensitivity", "finding", "reasons", "conditions", "condition_keys")
    return {k: shown[k] for k in fields} | dict(analysis_id=value.definition.id, revision=1,
        name=value.definition.name, economic_rationale=value.definition.economic_rationale, monitored=True,
        inputs=[b.model_dump(mode="json", include={"id", "revision", "name", "unit", "currency", "basis"}) for b in value.definition.inputs],
        status="retained" if retained else "evaluated", failure="Simulated partial retrieval; older evidence displayed" if retained else None,
        retained=retained, eligible=value.eligible and not retained,
        flagged=value.eligible and not retained and bool(value.reasons) and value.finding in ("condition", "new", "changed"),
        provider=dict(outcome="partial" if retained else value.data.outcome, attempted_at=NOW.isoformat(), completed_at=NOW.isoformat()),
        evaluation_id=value.id, current_evaluation_id=None if retained else value.id,
        retained_evaluation_id=value.id if retained else None, baseline_id=baseline.id if baseline else None,
        detail_ref=f"evaluations/{value.id}.json", baseline_ref=f"evaluations/{baseline.id}.json" if baseline else None,
        definition_ref=f"definitions/{value.definition.id}.json", attempt_ref=f"attempts/{value.definition.id}.json" if retained else None,
        idea_refs=[])


def make_retained(root: Path) -> dict:
    case = root / "cases/03-retained"
    request(case, """Review run monitoring-endpoints in run/ and save a concise investor brief there.
Explain what the configured thresholds and comparisons establish for Weekly gap,
including the retained prior evaluation, and what Quiet first review establishes.
For Small sample explain the historical standing and sample support. Account for
every monitored row and its source limitations. All files are fabricated offline
artifacts, including simulated live provider records. Do not refresh or reconfigure.""")
    manual = AnalysisSettings(calculation_contract="input-pipeline-v2", history_years=3,
        minimum_history=3, horizon="week", move_threshold=5, material_change=5, upper_percentile=99)
    inputs = (binding("gap-a"), binding("gap-b"))
    definition = resolved("weekly-gap", inputs, manual, "difference")
    dates = [date(2026, 9, n) for n in (21, 22, 23, 24, 25, 28, 29, 30)]
    gaps = [100, 100, 100, 102, 103, 106, 107, 108]
    base = run_eval(definition, dates[:-1], [[g + 50 for g in gaps[:-1]], [50] * 7], "weekly-prior")
    current = compare(run_eval(definition, dates, [[g + 50 for g in gaps], [50] * 8], "weekly-current"), base)
    small_days = days(5)
    local = AnalysisSettings(calculation_contract="input-pipeline-v2", minimum_history=3, upper_percentile=99)
    small = run_eval(resolved("small-sample", (binding("small"),), local), small_days, [[90, 95, 92, 93, 110]], "small-current")
    quiet = run_eval(resolved("quiet-first-review", (binding("quiet"),), local), small_days, [[1, 2, 3, 4, 2.5]], "quiet-current")
    unverified = run_eval(resolved("unverified-source", (binding("unverified"),), local), small_days, [[1, 2, 3, 4, 5]], "unverified-current", outcome="unverified")
    cache = run_eval(resolved("cache-source", (binding("cached"),), local), small_days, [[1, 2, 3, 4, 5]], "cache-current", outcome="cache")
    old_dates = [d - timedelta(days=7) for d in small_days]
    older = run_eval(resolved("partial-attempt", (binding("partial"),), local), old_dates, [[10, 11, 12, 13, 20]], "partial-older")
    rows = [compact(current, base), compact(small), compact(quiet), compact(unverified), compact(cache), compact(older, retained=True)]
    evaluations = [current, base, small, quiet, unverified, cache, older]
    run = case / "run"
    for value in evaluations:
        write(run / f"evaluations/{value.id}.json", value)
        write(run / f"definitions/{value.definition.id}.json", value.definition)
    partial_data = DataResponse(mode="live", outcome="partial", requested=("partial",), series=(),
        attempted_at=NOW, completed_at=NOW, failures=(dict(binding_id="partial", code="fixture-partial",
            message="Fabricated partial retrieval attempt; no usable observations"),))
    write(run / "attempts/partial-attempt.json", dict(definition=older.definition.model_dump(mode="json"),
        request=older.request.model_copy(update={"end": AS_OF}).model_dump(mode="json"),
        data=partial_data.model_dump(mode="json"), failure="Simulated partial retrieval"))
    manifest = dict(schema_version=1, run_id="monitoring-endpoints", request_id=None, trigger="manual",
        status="completed", mode="mock", timezone="Europe/London", application_version="offline-fixture",
        attempted_at=NOW.isoformat(), completed_at=NOW.isoformat(), error=None,
        universe_count=len(rows), monitored_count=len(rows), rows=rows, coverage=coverage(rows),
        evidence={e.id: f"evaluations/{e.id}.json" for e in evaluations})
    write(run / "manifest.json", manifest)
    return dict(weekly_change=current.change, frequency_start=current.change_start.isoformat(),
        prior_delta=current.current - base.current, baseline_date=base.observation_date.isoformat(),
        finding=current.finding, condition_keys=current.condition_keys, small_prior_count=len(small.points) - 1,
        small_percentile=small.percentile, quiet_finding=quiet.finding, monitored=len(rows),
        provider_outcomes=manifest["coverage"]["monitored"]["provider_outcomes"])


def hashes(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for branch in ("skills", "cases", "private") for p in sorted((root / branch).rglob("*"))
        if p.is_file() and "output" not in p.relative_to(root).parts and "briefs" not in p.relative_to(root).parts}


def prepare(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=False)
    for name in ("kairopsis-analysis", "kairopsis-screening"):
        shutil.copytree(ROOT / "src/kairopsis/skills" / name, root / "skills" / name,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
    shutil.copyfile(SUITE / "subject.md", root / "SUBJECT.md")
    truth = {"01-bulk": make_bulk(root), "02-history": make_history(root), "03-retained": make_retained(root)}
    write(root / "private/truth.json", truth)
    shutil.copyfile(SUITE / "rubric.json", root / "private/rubric.json")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    frozen = hashes(root)
    frozen["SUBJECT.md"] = hashlib.sha256((root / "SUBJECT.md").read_bytes()).hexdigest()
    write(root / "freeze.json", dict(source_commit=commit, resources=frozen,
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        note="Working-tree skills frozen by content; no subject execution or statistical calibration"))
    selfcheck(root)


def selfcheck(root: Path) -> None:
    frozen = json.loads((root / "freeze.json").read_text())["resources"]
    assert all(hashlib.sha256((root / path).read_bytes()).hexdigest() == digest for path, digest in frozen.items()), "Frozen resource changed"
    for path in (root / "cases").rglob("existing.json"):
        AnalysisDefinition.model_validate_json(path.read_text())
    for path in (root / "cases").rglob("*.json"):
        if path.parent.name in ("evaluations", "previews"):
            Evaluation.model_validate_json(path.read_text())
        elif path.parent.name == "definitions":
            ResolvedDefinition.model_validate_json(path.read_text())
        elif path.parent.name == "attempts":
            attempt = json.loads(path.read_text())
            ResolvedDefinition.model_validate(attempt["definition"])
            DataRequest.model_validate(attempt["request"])
            DataResponse.model_validate(attempt["data"])
    # Verify decisive semantics through the application, not prose matching.
    reference = resolved("check", (binding("check"),), AnalysisSettings(**DEFAULT))
    for rank in (1, 99):
        assert condition_rules(reference, "bp", rank, 0, True)[1]
    assert not condition_rules(reference, "bp", 50, 1000, True)[1]
    zref = reference.model_copy(update={"settings": AnalysisSettings(**(DEFAULT | dict(standardization="zscore", zscore_threshold=3)))})
    for value in (-3, 3):
        assert condition_rules(zref, "σ", 50, 0, True, value)[1]
    assert not condition_rules(zref, "σ", 100, 0, True, 2.9)[1]
    truth = json.loads((root / "private/truth.json").read_text())
    facts = truth["03-retained"]
    assert facts["weekly_change"] == 8 and facts["prior_delta"] == 1 and facts["finding"] == "unchanged"
    assert "move" in facts["condition_keys"] and facts["small_prior_count"] == 4 and facts["small_percentile"] == 100
    assert facts["quiet_finding"] == "quiet" and facts["monitored"] == 6
    assert not truth["02-history"]["preview_eligible"] and not truth["02-history"]["manual_eligible"]
    # Validate representative emitted profiles and the preserved exceptions.
    for folder in ("01-bulk", "02-history"):
        for spec in json.loads((root / f"cases/{folder}/setup.json").read_text()):
            selected = DEFAULT | spec["settings"]
            if selected["standardization"] == "zscore":
                selected.setdefault("zscore_threshold", 3)
            AnalysisDefinition.model_validate(spec | dict(settings=selected))
    print(json.dumps(dict(passed=True, cases=3, frozen_resources=len(frozen), retained_evaluations=7,
                         preview_evaluations=2, subjects_run=False)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare").add_argument("--output", type=Path, required=True)
    sub.add_parser("selfcheck").add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.output.resolve())
    else:
        selfcheck(args.root.resolve())
