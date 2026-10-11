"""Persisted research data: real CSV retrieval, shaping and analytical coverage."""
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

import metapyle
from metapyle.catalog import Catalog
import pandas as pd
import pytest

from kairopsis.analytics import evaluate
from kairopsis.config import Settings
from kairopsis.exploration_models import CollectionItem
from kairopsis.metapyle_adapter import MetapyleMarketData
from kairopsis.models import (AnalysisSettings, DataRequest, DataResponse, Observation,
    ResolvedDefinition, RiskAdjustment, SeriesBinding, SeriesResult)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "demo"
GENERATOR = ROOT / "scripts" / "generate_demo_data.py"
NOW = datetime(2026, 9, 30, 20, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def manifest():
    return json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def frame():
    return pd.read_csv(FIXTURE / "market.csv", index_col=0, parse_dates=True)


def binding(meta):
    return SeriesBinding(id=meta["id"], name=meta["name"], unit=meta["unit"],
        currency=meta["currency"], source="localfile", instrument=meta["id"],
        catalog_name=meta["id"], path=str(FIXTURE / "market.csv"),
        description=meta["description"])


def test_fixture_regenerates_byte_for_byte(tmp_path, manifest):
    builder = runpy.run_path(str(GENERATOR))
    builder["generate"](tmp_path)
    for name in ("market.csv", "manifest.json", "catalog.yaml"):
        assert (tmp_path / name).read_bytes() == (FIXTURE / name).read_bytes(), name
    assert hashlib.sha256((FIXTURE / "market.csv").read_bytes()).hexdigest() == manifest["csv_sha256"]


def test_inventory_dates_and_missingness(frame, manifest):
    assert list(frame) == [m["id"] for m in manifest["series"]]
    assert frame.shape == (4368, 74)
    assert frame.notna().sum().sum() == manifest["observations"] == 303894
    assert frame.index.is_monotonic_increasing and frame.index.is_unique
    assert all(frame.index.weekday < 5)
    assert str(frame.index[0].date()) == manifest["start"]
    assert str(frame.index[-1].date()) == manifest["end"]
    assert not frame.isin([float("inf"), float("-inf")]).any().any()
    for meta in manifest["series"]:
        observed = frame[meta["id"]].dropna()
        assert len(observed) == meta["observations"]
        assert str(observed.index[0].date()) == meta["first_date"]
        assert str(observed.index[-1].date()) == meta["last_date"]
        assert meta["description"].startswith("SYNTHETIC.")
        if meta["role"] == "core":
            assert len(observed) == len(frame)


def test_credit_fields_have_explicit_reusable_symbol_associations(manifest):
    metadata = {m["id"]: m for m in manifest["series"]}
    expected = {"usd_ig", "usd_hy", "usd_banks_credit", "usd_industrials_credit", "usd_broad_credit", "usd_em_hy"}
    assert {s["symbol"] for s in manifest["symbols"]} == expected
    required = {"oas_bp": "bp", "spread_duration_years": "years", "yield_pct": "%",
        "total_return_index": "index", "total_return_pct": "%", "excess_return_pct": "%",
        "treasury_benchmark_index": "index"}
    collection = []
    for symbol in manifest["symbols"]:
        assert required.keys() <= symbol["fields"].keys()
        for field, key in symbol["fields"].items():
            meta = metadata[key]
            assert meta["symbol"] == symbol["symbol"] and meta["field"] == field
            assert meta["currency"] == symbol["currency"] == "USD"
            if field in required:
                assert meta["unit"] == required[field]
            collection.append(CollectionItem(id=key, symbol=symbol["symbol"], field=field,
                origin="local", binding=binding(meta), semantics=meta["description"]))
    assert len(collection) == len({item.binding.id for item in collection}) == 45
    assert len({(item.symbol, item.field) for item in collection}) == len(collection)
    assert all(item.binding.field is None for item in collection)  # localfile has no query field.
    assert all(item.binding.instrument != "usd_banks_tr" for item in collection)  # Equity stays distinct.
    assert {m["id"] for m in metadata.values() if "symbol" in m} == {item.binding.id for item in collection}


@pytest.mark.parametrize("symbol", ["usd_ig", "usd_hy", "usd_banks_credit", "usd_industrials_credit", "usd_broad_credit", "usd_em_hy"])
def test_credit_fields_reconcile_to_their_spread_and_benchmark(frame, manifest, symbol):
    fields = next(s["fields"] for s in manifest["symbols"] if s["symbol"] == symbol)
    metadata = {m["id"]: m for m in manifest["series"]}
    actual_yield = frame[fields["yield_pct"]]
    expected_yield = frame.usd_5y_yield_pct + frame[fields["oas_bp"]] / 100
    assert actual_yield.tolist() == pytest.approx(expected_yield.tolist(), rel=0, abs=1e-8)
    duration = frame[fields["spread_duration_years"]]
    assert (duration > 0).all()
    credit = frame[fields["total_return_index"]]
    treasury = frame[fields["treasury_benchmark_index"]]
    assert (credit > 0).all() and (treasury > 0).all() and treasury.iloc[0] == 100
    total_return = frame[fields["total_return_pct"]]
    excess_return = frame[fields["excess_return_pct"]]
    expected_total = credit.pct_change(fill_method=None) * 100
    expected_excess = expected_total - treasury.pct_change(fill_method=None) * 100
    assert total_return.isna().sum() == excess_return.isna().sum() == 1
    assert pd.isna(total_return.iloc[0]) and pd.isna(excess_return.iloc[0])
    assert total_return.iloc[1:].tolist() == pytest.approx(expected_total.iloc[1:].tolist(), rel=0, abs=1e-8)
    assert excess_return.iloc[1:].tolist() == pytest.approx(expected_excess.iloc[1:].tolist(), rel=0, abs=1e-8)
    for field in ("total_return_pct", "excess_return_pct"):
        assert metadata[fields[field]]["supplied_measure"] == "precomputed return"
    assert metadata[fields["excess_return_pct"]]["benchmark_series_id"] == fields["treasury_benchmark_index"]
    # Independently check the benchmark convention and credit carry/price linkage.
    import numpy as np
    rates = frame.usd_5y_yield_pct
    expected_treasury_log = rates.shift() / 100 / 252 - duration * rates.diff() / 100
    observed_treasury_log = np.log(treasury / treasury.shift())
    assert observed_treasury_log.iloc[1:].tolist() == pytest.approx(expected_treasury_log.iloc[1:].tolist(), rel=0, abs=1e-8)
    credit_log = np.log(credit / credit.shift())
    model_credit_log = expected_yield.shift() / 100 / 252 - duration * (rates.diff() / 100 + frame[fields["oas_bp"]].diff() / 10000)
    residual = (credit_log - model_credit_log).dropna()
    assert residual.std() == pytest.approx(.0004, rel=.1)
    assert abs(residual.mean()) < .00003


def test_standard_metapyle_catalogue_reads_csv_without_filling(frame, monkeypatch):
    monkeypatch.chdir(FIXTURE)  # Standard Metapyle relative-path semantics.
    catalog = Catalog.from_yaml(FIXTURE / "catalog.yaml")
    for name in frame.columns:
        entry = catalog.get(name)
        assert entry.source == "localfile" and entry.symbol == name
        assert entry.path == "market.csv" and entry.field is None
    client = metapyle.Client(catalog=FIXTURE / "catalog.yaml", cache_enabled=False)
    try:
        fetched = client.get(list(frame.columns), "2010-01-04", "2026-09-30", use_cache=False)
        subset = client.get(["usd_hy_oas_bp", "edge_gapped_ig_bp"], "2026-08-07", "2026-08-24", use_cache=False)
    finally:
        client.close()
    expected = frame.tz_localize("UTC")  # Metapyle normalizes the index to UTC.
    pd.testing.assert_frame_equal(fetched, expected, check_names=False, check_freq=False)
    pd.testing.assert_frame_equal(subset, expected.loc["2026-08-07":"2026-08-24", subset.columns], check_names=False, check_freq=False)
    assert subset.loc["2026-08-10":"2026-08-21", "edge_gapped_ig_bp"].isna().all()


def test_absolute_catalogue_can_be_loaded_from_another_directory(tmp_path, frame):
    catalog = tmp_path / "relocated.yaml"
    subprocess.run([sys.executable, str(GENERATOR), "--catalog-output", str(catalog)], cwd=tmp_path, check=True, capture_output=True)
    client = metapyle.Client(catalog=catalog, cache_enabled=False)
    try:
        fetched = client.get(["usd_ig_oas_bp"], "2026-09-30", "2026-09-30", use_cache=False)
    finally:
        client.close()
    assert fetched.iloc[0, 0] == frame.loc["2026-09-30", "usd_ig_oas_bp"]
    assert Catalog.from_yaml(catalog).get("usd_ig_oas_bp").path == str(FIXTURE / "market.csv")


def test_kairopsis_catalogue_route_preserves_unverified_provenance(tmp_path, frame, manifest):
    wanted = ["usd_ig_oas_bp", "usd_hy_oas_bp", "edge_stale_ig_bp"]
    bindings = tuple(binding(m) for m in manifest["series"] if m["id"] in wanted)
    settings = Settings(mode="live", workspace=tmp_path / "workspace", config_dir=tmp_path / "config",
        cache_dir=tmp_path / "cache", log_dir=tmp_path / "logs")
    request = DataRequest(bindings=bindings, start=date(2026, 9, 1), end=date(2026, 9, 30))
    response = MetapyleMarketData(settings, lambda: NOW).fetch(request)
    assert not response.failures and response.outcome == "unverified"
    assert all(p.observed_on is None for s in response.series for p in s.observations)
    for series in response.series:
        expected = frame.loc["2026-09-30", series.binding.id]
        assert series.observations[-1].value == (None if pd.isna(expected) else expected)
    definition = ResolvedDefinition(id="demo", revision=1, name="Demo IG", calculation="level",
        inputs=(bindings[0],), settings=AnalysisSettings(calculation_contract="input-pipeline-v2"))
    actual = evaluate(definition, response, request, NOW)
    assert actual.current is not None and not actual.eligible
    assert "freshness unverified" in " ".join(actual.limitations)


def test_explicit_units_fx_rebasing_and_return_shaping(frame):
    assert frame.usd_10y_yield_bp.tolist() == pytest.approx((frame.usd_10y_yield_pct * 100).tolist(), rel=0, abs=1e-6)
    assert frame.usd_ig_oas_bp.tolist() == pytest.approx((frame.usd_ig_oas_pct * 100).tolist(), rel=0, abs=1e-6)
    assert frame.usd_2s10s_bp.tolist() == pytest.approx(((frame.usd_10y_yield_pct - frame.usd_2y_yield_pct) * 100).tolist(), rel=0, abs=1e-6)
    expected = frame.eur_equity_tr * frame.eurusd / frame.eurusd.iloc[0]
    assert frame.eur_equity_usd_tr.tolist() == pytest.approx(expected.tolist(), rel=0, abs=1e-7)
    for key in [name for name in frame if name.endswith("_100")]:
        assert frame.loc[:"2015-01-01", key].isna().all()
        assert frame.loc["2015-01-02", key] == 100
        native = frame.loc["2015-01-02":, key[:-4]]
        assert frame.loc["2015-01-02":, key].tolist() == pytest.approx((100 * native / native.iloc[0]).tolist(), rel=0, abs=1e-7)
    for key in ["usd_equity_tr", "usd_banks_tr"]:
        expected = frame[key].resample("BME").last().pct_change(fill_method=None).dropna() * 100
        actual = frame[key + "_monthly_return_pct"].dropna()
        assert actual.index.equals(expected.index)
        assert actual.tolist() == pytest.approx(expected.tolist(), rel=0, abs=1e-7)


@pytest.fixture(scope="module")
def synthetic_results(frame, manifest):
    # Explicit fixture knowledge supplies dates ONLY for offline engine tests.
    # The regular Metapyle adapter above must never infer these native dates.
    results = {}
    for meta in manifest["series"]:
        b = binding(meta)
        observations = tuple(Observation(date=d.date(), observed_on=d.date(), value=float(v))
            for d, v in frame.loc["2021-01-01":, b.id].dropna().items())
        results[b.id] = SeriesResult(binding=b, observations=observations,
            provenance="Synthetic CSV fixture with generator-defined dates, offline engine test only")
    return results


def analyse(results, names, *, calculation="level", measure="level", method="none", reference=None,
            horizon="week", standardization="none"):
    inputs = tuple(results[name].binding for name in names)
    references = (results[reference].binding,) if reference and reference not in names else ()
    risk = RiskAdjustment(method=method, reference_id=reference, estimation_measure="change" if measure == "level" else None,
        lookback_years=1, minimum_samples=60, confidence=95, downside="increase")
    definition = ResolvedDefinition(id="demo", revision=1, name="CSV engine verification", calculation=calculation,
        inputs=inputs, references=references,
        settings=AnalysisSettings(calculation_contract="input-pipeline-v2", measure=measure, horizon=horizon,
            standardization=standardization, risk_adjustment=risk, history_years=3, minimum_history=500,
            fit_years=3, upper_percentile=99, zscore_threshold=3))
    bindings = (*inputs, *references)
    request = DataRequest(bindings=bindings, start=date(2021, 1, 1), end=NOW.date())
    data = DataResponse(mode="mock", outcome="synthetic", requested=tuple(b.id for b in bindings),
        series=tuple(results[b.id] for b in bindings), attempted_at=NOW, completed_at=NOW)
    return evaluate(definition, data, request, NOW)


@pytest.mark.parametrize("method", ["none", "volatility", "beta", "var", "es"])
def test_credit_comparison_has_adequate_history_for_risk_methods(synthetic_results, method):
    reference = "usd_broad_credit_oas_bp" if method == "beta" else None
    actual = analyse(synthetic_results, ["usd_hy_oas_bp", "usd_ig_oas_bp"],
        calculation="difference", measure="change", method=method, reference=reference)
    assert actual.current is not None and actual.eligible, actual.limitations
    assert actual.percentile is not None
    for estimate in actual.adjustment_estimates:
        if method == "none":
            assert estimate.scale == 1
        else:
            assert estimate.sample_count >= 200 and estimate.scale > 0
            assert estimate.end <= estimate.cutoff < NOW.date()


def test_level_gap_ratio_and_adjusted_level_trace_to_raw_inputs(frame, synthetic_results):
    a, b = "usd_hy_oas_bp", "usd_ig_oas_bp"
    gap = analyse(synthetic_results, [a, b], calculation="difference")
    ratio = analyse(synthetic_results, [a, b], calculation="ratio", standardization="zscore")
    level = analyse(synthetic_results, [a], method="volatility")
    assert gap.current == pytest.approx(frame[a].iloc[-1] - frame[b].iloc[-1])
    assert ratio.eligible and ratio.standardization_estimate.sample_count >= 500
    assert ratio.points[-1].unstandardized_value == pytest.approx(frame[a].iloc[-1] / frame[b].iloc[-1])
    assert level.eligible and level.current == pytest.approx(frame[a].iloc[-1] / level.adjustment_estimates[0].scale)


def test_bank_return_regression_uses_returns_not_arbitrary_index_bases(synthetic_results):
    actual = analyse(synthetic_results, ["usd_banks_tr", "usd_equity_tr"], calculation="regression", measure="return", horizon="month")
    assert actual.eligible and actual.fit.sample_count >= 500, actual.limitations
    assert actual.fit.end < NOW.date()
    latest = actual.points[-1]
    y, x = latest.transformed_inputs
    assert actual.current == pytest.approx(y - (actual.fit.intercept + actual.fit.slope * x))


def test_precomputed_credit_excess_returns_keep_their_supplied_measure(frame, synthetic_results):
    actual = analyse(synthetic_results, ["usd_ig_excess_return_pct", "usd_hy_excess_return_pct"], calculation="difference")
    assert actual.eligible and actual.unit == "%", actual.limitations
    assert actual.current == pytest.approx(frame.usd_ig_excess_return_pct.iloc[-1] - frame.usd_hy_excess_return_pct.iloc[-1])


def test_edge_cases_remain_missing_or_unavailable(frame, synthetic_results):
    assert frame.edge_short_ig_bp.notna().sum() == 40
    assert frame.loc["2026-09-14":, "edge_stale_ig_bp"].isna().all()
    assert (frame.edge_signed_yield_bp < 0).any() and (frame.edge_signed_yield_bp == 0).any()
    assert (frame.edge_denominator_bp.abs() == .000001).any()
    for key, method in [("edge_short_ig_bp", "volatility"), ("edge_constant_bp", "volatility"), ("edge_stale_ig_bp", "none")]:
        actual = analyse(synthetic_results, [key], method=method)
        assert not actual.eligible, (key, actual.limitations)
    monthly = analyse(synthetic_results, ["usd_banks_tr_monthly_return_pct", "usd_equity_tr_monthly_return_pct"], calculation="regression")
    assert monthly.current is None and not monthly.eligible
    assert "Fit unavailable" in " ".join(monthly.limitations)
    inverse = analyse(synthetic_results, ["edge_inverse_credit_bp"], measure="change", method="beta", reference="usd_broad_credit_oas_bp")
    tiny = analyse(synthetic_results, ["edge_tiny_beta_bp"], measure="change", method="beta", reference="usd_broad_credit_oas_bp")
    assert inverse.adjustment_estimates[0].scale == pytest.approx(-2, abs=1e-6)
    assert tiny.adjustment_estimates[0].scale == pytest.approx(.0001, abs=1e-6)
