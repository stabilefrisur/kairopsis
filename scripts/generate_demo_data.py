"""Build the fixed CSV research fixture and a standard Metapyle catalogue.

Run from any directory. No market providers, credentials or app workspace needed.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
import hashlib
import json
from math import exp, sin
from pathlib import Path
import random

from metapyle.catalog import Catalog, CatalogEntry


START = date(2010, 1, 4)
END = date(2026, 9, 30)
SEED = 20261011
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "demo"


def build_dataset() -> tuple[list[date], dict[str, list[float | None]], list[dict]]:
    """Return weekday observations plus explicit supplied-series semantics."""
    days = []
    day = START
    while day <= END:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    count = len(days)
    rng = random.Random(SEED)
    data: dict[str, list[float | None]] = {}
    metadata: list[dict] = []

    def add(key, name, unit, currency, basis, description, values, *,
            kind="level", cadence="weekday", role="core"):
        data[key] = [None if value is None else round(value, 8) for value in values]
        metadata.append(dict(id=key, name=name, unit=unit, currency=currency,
            comparison_basis=basis, supplied_measure=kind, cadence=cadence,
            role=role, description="SYNTHETIC. " + description))

    # Shared factors create interpretable co-movement, with independent noise.
    # Dates describe invented episodes, not a reconstruction of historical markets.
    stress_dates = [date(2011, 8, 8), date(2016, 2, 11), date(2020, 3, 23),
                    date(2022, 9, 26), date(2026, 9, 24)]
    amplitudes = [65, 45, 170, 80, 65]
    credit, rate_factor, market, banks, euro, fx = [], [], [], [], [], []
    c = r = 0.0
    market_level, bank_level, euro_level, fx_level = 100.0, 7000.0, 250.0, 1.35
    for i, day in enumerate(days):
        pulse = sum(a * exp(-abs((day - event).days) / 45)
                    for a, event in zip(amplitudes, stress_dates))
        volatility = 1 + pulse / 60
        c = .965 * c + rng.gauss(0, 1.6 * volatility)
        r = .99 * r + rng.gauss(0, .018 * volatility)
        credit.append(105 + 15 * sin(i / 170) + pulse + c)
        rate_factor.append(2.5 + 1.2 * sin(i / 510) + r)
        shock = rng.gauss(0, .006 * volatility)
        bank_beta = 1.15 if day < date(2022, 1, 3) else 1.65
        if i:
            market_level *= exp(.00018 + shock)
            bank_level *= exp(.00013 + bank_beta * shock + rng.gauss(0, .003))
            euro_level *= exp(.00012 + .75 * shock + rng.gauss(0, .004))
            fx_level *= exp(-.000025 + rng.gauss(0, .003))
        market.append(market_level)
        banks.append(bank_level)
        euro.append(euro_level)
        fx.append(fx_level)

    credit_specs = [
        ("usd_ig_oas_bp", "USD IG OAS", "USD", "Treasury", 1, 0, 5.5, "investment grade, broad corporate"),
        ("usd_hy_oas_bp", "USD HY OAS", "USD", "Treasury", 2.7, 95, 3.5, "high yield, broad corporate"),
        ("usd_banks_oas_bp", "USD banks OAS", "USD", "Treasury", 1.2, 10, 4.5, "investment grade, banks"),
        ("usd_industrials_oas_bp", "USD industrials OAS", "USD", "Treasury", .9, 5, 6, "investment grade, industrials"),
        ("usd_broad_credit_oas_bp", "USD broad credit OAS", "USD", "Treasury", 1.4, 25, 5, "mixed ratings, broad credit risk reference"),
        ("usd_em_hy_oas_bp", "USD EM sovereign HY OAS", "USD", "Treasury", 3.2, 150, 6.5, "high yield, emerging sovereigns"),
        ("usd_mbs_oas_bp", "USD agency MBS OAS", "USD", "Treasury", .55, 20, 4, "agency mortgages, option-adjusted"),
        ("eur_ig_oas_bp", "EUR IG OAS", "EUR", "Bund", 1.05, 12, 5, "investment grade, broad corporate"),
        ("gbp_ig_oas_bp", "GBP IG OAS", "GBP", "Gilt", .85, 30, 6, "investment grade, broad corporate"),
    ]
    for key, name, currency, curve, beta, offset, duration, composition in credit_specs:
        values = [max(5, beta * x + offset + rng.gauss(0, 1.5)) for x in credit]
        add(key, name, "bp", currency, f"Native {currency} / {curve} OAS",
            f"{composition}; illustrative spread duration {duration:g} years. "
            "Different credit quality, composition and duration remain. No FX hedge or curve rebasing.", values)

    yields = {}
    for tenor, offset in [(2, -.35), (5, -.1), (10, .15)]:
        values = [r + offset + .08 * sin(i / (45 + tenor)) for i, r in enumerate(rate_factor)]
        yields[tenor] = values
        add(f"usd_{tenor}y_yield_pct", f"USD {tenor}Y yield", "%", "USD", f"Treasury, {tenor}-year tenor",
            "Yield quoted in percent: 1.0 means 1%, not a decimal return.", values)
    add("usd_10y_yield_bp", "USD 10Y yield in bp", "bp", "USD", "Treasury, 10-year tenor",
        "Upstream conversion: usd_10y_yield_pct multiplied by 100.", [x * 100 for x in data["usd_10y_yield_pct"]])
    add("usd_2s10s_bp", "USD 10Y minus 2Y", "bp", "USD", "Treasury curve slope",
        "Upstream shaping: (10Y yield percent minus 2Y yield percent) multiplied by 100.",
        [(a - b) * 100 for a, b in zip(data["usd_10y_yield_pct"], data["usd_2y_yield_pct"])])
    add("usd_ig_oas_pct", "USD IG OAS in percent", "%", "USD", "Native USD / Treasury OAS",
        "Same USD IG spread divided by 100. Convert observations before a bp difference.",
        [x / 100 for x in data["usd_ig_oas_bp"]])

    # These are illustrative price/carry dynamics, not bond valuation equations.
    for segment, duration, base in [("ig", 5.5, 100), ("hy", 3.5, 250)]:
        oas = data[f"usd_{segment}_oas_bp"]
        index = [float(base)]
        for i in range(1, count):
            carry = (yields[5][i-1] / 100 + oas[i-1] / 10000) / 252
            price = -duration * ((yields[5][i] - yields[5][i-1]) / 100 + (oas[i] - oas[i-1]) / 10000)
            index.append(index[-1] * exp(carry + price + rng.gauss(0, .0004)))
        add(f"usd_{segment}_tr", f"USD {segment.upper()} total return", "index", "USD", "USD, income reinvested, unhedged",
            f"Base {base} on {START}. Toy carry/duration model with fixed duration {duration}; "
            "no default losses, convexity or trading costs. Percentage change is synthetic index return.", index)
        add(f"usd_{segment}_duration_years", f"USD {segment.upper()} spread duration", "years", "USD", "Constant model sensitivity",
            "Fixed illustrative spread duration used in the toy credit total-return model.", [duration] * count)

    for key, name, currency, values, description in [
        ("usd_equity_tr", "USD broad equity total return", "USD", market, "Base 100; broad equity risk reference."),
        ("usd_banks_tr", "USD bank equity total return", "USD", banks, "Base 7000; return sensitivity rises from 1.15 to 1.65 on 2022-01-03."),
        ("eur_equity_tr", "EUR equity total return", "EUR", euro, "Base 250; native EUR returns."),
    ]:
        add(key, name, "index", currency, f"{currency}, income reinvested, unhedged",
            description + " Arbitrary raw bases are not relative value. Percentage change is index return.", values)
    price_index = [x * exp(-.00006 * i) for i, x in enumerate(market)]
    add("usd_equity_price", "USD broad equity price index", "index", "USD", "USD, income excluded",
        "Total-return path with a deterministic income factor removed. Percentage change is price return.", price_index)
    add("eurusd", "EURUSD spot", "USD/EUR", "USD", "USD paid for one EUR",
        "Quote direction fixed. Multiply EUR wealth by EURUSD for unhedged USD wealth; no hedge supplied.", fx)
    add("eur_equity_usd_tr", "EUR equity in USD", "index", "USD", "USD, income reinvested, unhedged FX conversion",
        "Upstream shaping: eur_equity_tr * eurusd / initial eurusd. Base 250; FX contributes to returns.",
        [x * f / data["eurusd"][0] for x, f in zip(data["eur_equity_tr"], data["eurusd"])])
    rebase_date = date(2015, 1, 2)
    base_pos = days.index(rebase_date)
    for key in ["usd_ig_tr", "usd_hy_tr", "usd_equity_tr", "usd_banks_tr", "eur_equity_usd_tr"]:
        add(key + "_100", key.replace("_", " ") + " rebased", "index", "USD", "USD wealth, common start 2015-01-02 = 100",
            f"Upstream shaping: 100 * {key}(t) / {key}(2015-01-02); earlier dates missing. "
            "Level comparisons describe growth since that date.",
            [None if i < base_pos else x / data[key][base_pos] * 100 for i, x in enumerate(data[key])], role="shaped")

    policy = []
    policy_value = 1.0
    for i in range(count):
        if i and i % 65 == 0:
            policy_value += .25 if (i // 65) % 16 < 8 else -.25
        policy.append(policy_value)
    deposit = [policy[0] * .65]
    for value in policy[1:]:
        deposit.append(deposit[-1] + .06 * (.65 * value - deposit[-1]))
    add("usd_policy_pct", "USD policy rate", "%", "USD", "Synthetic administered rate",
        "Quarter-point decisions every 65 weekday sessions; unchanged values between decisions are actual model levels. "
        "Most daily policy changes are zero; all-date change ratios are unsuitable event statistics.", policy)
    add("usd_deposit_pct", "USD deposit rate", "%", "USD", "Synthetic administered rate",
        "Partial, delayed pass-through: each session closes 6% of the gap to 65% of policy rate.", deposit)
    for key in ["usd_equity_tr", "usd_banks_tr"]:
        returns = []
        previous = None
        for i, day in enumerate(days):
            month_end = i == count - 1 or days[i+1].month != day.month
            returns.append(100 * (data[key][i] / previous - 1) if month_end and previous is not None else None)
            if month_end:
                previous = data[key][i]
        add(key + "_monthly_return_pct", key.replace("_", " ") + " monthly return", "%", "USD", "Non-overlapping month-end index returns",
            f"100 * ({key} at last weekday of month / previous month end - 1). "
            "Use Measure Level; blank between month ends. Sparse regression/freshness limits still apply.",
            returns, kind="precomputed return", cadence="month-end weekday", role="shaped")

    # Edge cases stay separate from the research universe. Never forward-fill them.
    ig = data["usd_ig_oas_bp"]
    add("edge_gapped_ig_bp", "Gapped IG spread", "bp", "USD", "Same USD IG OAS",
        "Missing every 37th session and 2026-08-10 through 2026-08-21; test exact-date alignment and missing baselines.",
        [None if i % 37 == 0 or date(2026, 8, 10) <= d <= date(2026, 8, 21) else x for i, (d, x) in enumerate(zip(days, ig))], role="edge")
    add("edge_stale_ig_bp", "Stopped IG spread", "bp", "USD", "Same USD IG OAS",
        "No values after 2026-09-11. Missing tail is not a zero move.",
        [x if d <= date(2026, 9, 11) else None for d, x in zip(days, ig)], role="edge")
    add("edge_short_ig_bp", "New IG spread series", "bp", "USD", "Same USD IG OAS",
        "Only the final 40 sessions; insufficient for the 500-observation reference floor and 60-sample risk floor.",
        [None if i < count - 40 else x for i, x in enumerate(ig)], role="edge")
    add("edge_constant_bp", "Constant spread", "bp", "USD", "Synthetic test constant",
        "Exactly 100 bp. Zero variance, unusable volatility divisor and constant regression predictor.", [100] * count, role="edge")
    add("edge_signed_yield_bp", "Yield crossing zero", "bp", "EUR", "Synthetic signed yield, no curve mapping",
        "Repeated negative/zero/positive baselines. Absolute changes retain meaning; ordinary percentage growth does not.",
        [(i % 101 - 50) / 2 for i in range(count)], role="edge")
    add("edge_denominator_bp", "Zero and tiny denominator", "bp", "USD", "Synthetic arithmetic fixture",
        "Repeats 0, 0.000001, -0.000001, 10, -10 bp. No economically valid all-date ratio distribution.",
        [[0, .000001, -.000001, 10, -10][i % 5] for i in range(count)], role="edge")
    add("edge_inverse_credit_bp", "Inverse credit sensitivity", "bp", "USD", "Synthetic inverse credit level",
        "1000 minus twice broad credit OAS. Stable negative beta to that reference is intentional, not a hedge.",
        [1000 - 2*x for x in data["usd_broad_credit_oas_bp"]], role="edge")
    add("edge_tiny_beta_bp", "Tiny credit sensitivity", "bp", "USD", "Synthetic small sensitivity",
        "100 plus 0.0001 times broad credit OAS. Numerically nonzero beta can be economically unusable as a divisor.",
        [100 + .0001*x for x in data["usd_broad_credit_oas_bp"]], role="edge")
    return days, data, metadata


def write_catalog(metadata: list[dict], csv_path: Path, target: Path) -> None:
    entries = {m["id"]: CatalogEntry(my_name=m["id"], source="localfile", symbol=m["id"],
        path=str(csv_path), unit=m["unit"], description=f'{m["name"]}. {m["comparison_basis"]}. {m["description"]}')
        for m in metadata}
    target.parent.mkdir(parents=True, exist_ok=True)
    Catalog(entries).to_yaml(target)
    # Keep persisted bytes stable on Windows as well as Linux.
    target.write_text(target.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    Catalog.from_yaml(target)  # Enforce the installed provider schema.


def generate(output: Path) -> dict:
    days, data, metadata = build_dataset()
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / "market.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["date", *data])
        for i, day in enumerate(days):
            writer.writerow([day.isoformat(), *("" if values[i] is None else f"{values[i]:.8f}" for values in data.values())])
    for m in metadata:
        present = [d for d, value in zip(days, data[m["id"]]) if value is not None]
        m.update(observations=len(present), first_date=str(present[0]), last_date=str(present[-1]))
    manifest = dict(schema_version=1, provenance="synthetic", seed=SEED,
        start=str(START), end=str(END), rows=len(days), series_count=len(data),
        observations=sum(m["observations"] for m in metadata),
        csv_sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        calendar="Monday-Friday only; no real exchange holidays or intraday timestamps",
        missing="Empty CSV cell means missing; never forward-filled",
        series=metadata)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    # Metapyle resolves relative data paths against process cwd, not catalogue dir.
    write_catalog(metadata, Path("market.csv"), output / "catalog.yaml")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT,
                        help="Write the fixed fixture here (default: tests/fixtures/demo)")
    parser.add_argument("--catalog-output", type=Path,
                        help="Only write a catalogue with absolute CSV paths, using an existing output-dir fixture")
    args = parser.parse_args()
    output = args.output_dir.expanduser().resolve()
    if args.catalog_output:
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        csv_path = output / "market.csv"
        if hashlib.sha256(csv_path.read_bytes()).hexdigest() != manifest["csv_sha256"]:
            parser.error("CSV does not match its manifest; regenerate the fixture first")
        write_catalog(manifest["series"], csv_path, args.catalog_output.expanduser().resolve())
        print(f"Catalogue: {args.catalog_output.resolve()}")
    else:
        manifest = generate(output)
        print(f'{manifest["series_count"]} series, {manifest["rows"]} dates, {manifest["observations"]} observations: {output}')


if __name__ == "__main__":
    main()
