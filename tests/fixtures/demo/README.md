# Persisted synthetic market data

74 Data Series, 4,368 weekday rows, 303,894 populated observations. Fixed range:
4 January 2010–30 September 2026. About sixteen years of history supports separate
risk, fitting and reference windows, including the Analysis skill's provisional
three-year / 500-observation reference profile after risk warm-up.

All values are fabricated. Seed `20261011`, fixed endpoints and eight-decimal CSV
serialization make regeneration reproducible. This is a source-testing fixture;
the existing built-in unit-test fixtures and user workspaces are unaffected.

## Run the CSV-backed application demo

From the repository root:

```sh
.venv/bin/python scripts/run_csv_demo.py --root /absolute/path/csv-demo --port 8768
```

Open `/explore/csv-demo` for a starter credit workspace, or `/library` for all
74 series. This uses the normal Metapyle `localfile` route, not the built-in
mock generator. The launcher checks the CSV checksum, imports through Library
validation, preserves manifest research-symbol/field mappings and labels the
application as synthetic CSV data. It sets new Explore workspaces to the
dataset's last date, 2026-09-30. Edge-case series are labelled separately.

The dedicated workspace persists edits and Analyses across restarts. Re-running
the launcher adds missing entries without replacing existing Library edits or
the saved starter workspace. It refuses to mix in an unrelated data Library.
Use `--prepare-only` to import without starting the server.

The importer explicitly declares this generated file's dates as observation
dates, using the documented no-fill convention. Weekly changes, returns, risk
scaling and fitting therefore use actual supplied dates through the production
engine. Market freshness remains `unverified`; no monitoring is enabled.
Explore caches loaded observations and calculations; **Refresh data** reloads
the source. Restarting the process clears the in-memory cache.

Create or edit Analyses from Library in the shared Analysis editor. Its charts
update automatically; **Save Analysis** or **Save changes** publishes the
definition. Explore can select saved Analyses or add workspace-local calculations.
New UI drafts use rolling fitting/reference periods; saved definitions preserve
their choices. Finite CSV history can leave early rolling results unavailable.

Use `scripts/explore-dates-acceptance.py` against this demo for date-control
checks. `scripts/csv-demo-acceptance.py` expects the initial 74-entry Library with
no added Analyses; run it against a separate freshly prepared demo root, not a
populated research workspace. Both scripts accept `--url`.

## Files and regeneration

- `market.csv`: ISO date first, one numeric column per Metapyle symbol. Empty cells
  mean missing. No forward fill, NaN strings, nonfinite values or duplicate dates.
- `catalog.yaml`: standard Metapyle entries (`my_name`, `source: localfile`,
  `symbol`, `path`, `description`, `unit`). `field` is omitted as required.
- `manifest.json`: units, currency, Comparison Basis, supplied measure, cadence,
  shaping, intended use, per-series coverage and CSV SHA-256. Its `symbols` list
  explicitly maps six credit assets to their fields and Data Series IDs.

From the repository root, using the project environment:

```sh
python scripts/generate_demo_data.py
python -m pytest tests/test_demo_data.py
```

`--output-dir /absolute/path` writes the same fixture elsewhere. There is no
rolling end date: changing this fixture requires an intentional regeneration
and review. Files live under `tests/`, included in the source distribution.

## Read through Metapyle

Metapyle resolves relative data paths against the **process working directory**.
To use the checked-in catalogue directly, run this from `tests/fixtures/demo`:

```python
from metapyle import Client

client = Client(catalog="catalog.yaml", cache_enabled=False)
try:
    data = client.get(
        ["usd_hy_oas_bp", "usd_ig_oas_bp", "usd_broad_credit_oas_bp"],
        "2010-01-04", "2026-09-30", use_cache=False,
    )
finally:
    client.close()
```

For use from any directory, generate a separate catalogue with absolute paths:

```sh
python scripts/generate_demo_data.py --catalog-output /absolute/path/demo.yaml
```

This reads the existing CSV and manifest, verifies their checksum, and writes
only the requested catalogue. Pass that catalogue to `Client`. Run this step on
the host that will read the CSV: Windows and WSL use different absolute paths.
Do not overwrite a Kairopsis workspace's Library-managed `metapyle.yaml`.

In Kairopsis Library, add a Data Series with source `localfile`, the chosen CSV
column as Symbol, the **absolute** `market.csv` path, no Field, and units/currency
from the manifest. Give it a synthetic label and retain the shaping description.
Library handles its normal catalogue projection and revisions.

Without an explicit Library file-date declaration, the regular Metapyle route
reports `unverified` freshness and unknown native observation dates. Raw levels
are inspectable; date-dependent calculations need that evidence. Integration
tests cover both the unchanged conservative default and the demo importer's
explicit declaration. Neither establishes live-provider freshness.

## Universe

| Group | Columns / semantics |
| --- | --- |
| Credit | USD IG, HY, banks, industrials, broad-credit reference, EM sovereign HY and agency MBS OAS; EUR and GBP IG OAS. All bp. Native curves and illustrative durations documented per series. |
| Rates | USD 2Y, 5Y, 10Y yields in percent; actual 10Y bp conversion and 10Y-minus-2Y slope in bp. |
| Credit fields | Six USD credit assets each have OAS, spread duration, model yield, total-return index, daily total return, daily excess return and a supplied Treasury benchmark. See the mappings below. |
| Equity | USD broad equity and banks total-return indices, broad price-only index, EUR total-return index. Bank return sensitivity changes in 2022. |
| FX | EURUSD in USD per EUR; explicitly converted unhedged EUR equity wealth in USD. No hedged series claimed. |
| Common-start wealth | Five USD total-return paths rebased to 100 on 2015-01-02, missing before that date. |
| Units | USD IG OAS also supplied in percent. Numeric values converted, not merely relabelled. |
| Policy | Policy and deposit rates in percent, partial delayed pass-through. Many zero policy changes intentionally retained. |
| Sparse returns | Non-overlapping monthly USD broad-equity and bank returns, in percentage points; missing between month ends. Preserve with Measure Level. |

Shared mean-reverting spread/rate factors, noisy return co-movement, changing
volatility and five dated stress pulses support fitting and tail tests. Pulse
dates do not imply reconstructed market history. The calendar contains every
weekday, including real-world holidays; there are no exchange calendars,
timestamps, publication lags, bid/ask spreads or provider revisions. Credit
indices use a simplified fixed-duration/carry model without defaults or convexity.

## Multiple fields for the same credit asset

| Research symbol | Asset | Spread duration (years) |
| --- | --- | --- |
| `usd_ig` | US investment-grade credit | 5.5 |
| `usd_hy` | US high-yield credit | 3.5 |
| `usd_banks_credit` | US bank credit | 4.5 |
| `usd_industrials_credit` | US industrial credit | 6.0 |
| `usd_broad_credit` | US broad credit | 5.0 |
| `usd_em_hy` | USD EM sovereign high yield | 6.5 |

Each asset exposes the same seven fields. Resolve each field through
`manifest.symbols[].fields`; do not infer column names from prefixes. For example,
bank credit's OAS column is `usd_banks_oas_bp`, while its total-return index is
`usd_banks_credit_tr`. The existing `usd_banks_tr` remains **bank equity**.

| Field | Meaning |
| --- | --- |
| `oas_bp` | Option-adjusted spread, bp. |
| `spread_duration_years` | Fixed sensitivity used by the model, years. |
| `yield_pct` | Toy credit yield: USD 5Y Treasury yield + OAS / 100, quoted in percent. Not yield-to-worst. |
| `total_return_index` | Synthetic credit wealth index, income reinvested. |
| `total_return_pct` | One-session simple index return, numerically in percent. |
| `excess_return_pct` | Credit's one-session simple return minus its supplied Treasury benchmark return, percentage points. |
| `treasury_benchmark_index` | Related Treasury wealth benchmark, using the same yield factor and model duration. |

The IG/HY rebased indices and IG's percent OAS representation have additional,
distinct field names. Each associated series also records `symbol` and `field`
in its manifest entry. These map directly to Explore's `CollectionItem.symbol`
and `CollectionItem.field`, alongside that series' normal retrieval binding.
Metapyle's `localfile` query still uses the **CSV column** as its provider symbol
and omits its provider `field`. No provider schema extension or workspace import
is required to read the CSV; the manifest supplies the research associations.

Example association lookup:

```python
import json
from pathlib import Path

manifest = json.loads(Path("manifest.json").read_text())
ig = next(item for item in manifest["symbols"] if item["symbol"] == "usd_ig")
columns = [ig["fields"][field] for field in
           ("oas_bp", "spread_duration_years", "total_return_pct", "excess_return_pct")]
# Pass columns to the ordinary Client.get() call above.
```

For each session, with Treasury yield `y` in percent, spread `s` in bp and
duration `D`, the credit index's log return is
`(y_previous / 100 + s_previous / 10000) / 252
- D * (change(y) / 100 + change(s) / 10000) + residual_noise`.
The benchmark's log return is
`y_previous / 100 / 252 - D * change(y) / 100`.
This supplies an explicit model duration-matching convention, not a claim of
actual Treasury replication. Excess return is the difference of the resulting
**simple** returns, not the difference of their log returns or an index ratio.
Each excess-return series records its exact `benchmark_series_id`.

Daily total/excess returns are missing on the first date because no earlier
baseline exists. Use **Measure Level** to preserve these precomputed returns.
For longer-interval excess return, calculate each index's return over the same
endpoints, then subtract. Compounding the daily arithmetic differences does not
produce that longer-interval excess return.

## Research cases from the Analysis skill

These are conceptual starting points, not saved Analyses or monitoring defaults.
Use the manifest's IDs and units; new definitions use `input-pipeline-v2`.
The tests validate representative mechanics with explicitly synthetic native dates.

| Economic question | Ordered inputs and calculation | Interpretation / qualification |
| --- | --- | --- |
| How much more spread does HY quote? | `usd_hy_oas_bp` minus `usd_ig_oas_bp`; Difference, Level | Positive gap = extra quoted bp. Rating, duration and composition differ. |
| How large is HY spread relative to IG? | Same A/B; Ratio, Level; optional final Z-score | Meaningful positive spread denominator; not a performance comparison. |
| Which market had a larger weekly shock? | Same A−B; Change, Weekly; own volatility | Difference of own-risk moves, not long-short portfolio volatility. |
| Which widening used more historical tail scale? | Same A−B; Change, Weekly; own VaR or ES, 95%, downside Increase | Compare fractions of historical widening scales. Examine actual sample and tail support. |
| How much spread per unit of movement risk? | `usd_hy_oas_bp`; Standalone Level; Weekly volatility estimated from Change | Keeps the level numerator. Not carry/volatility or annualized return. |
| What is the common-credit sensitivity comparison? | HY and IG; Change; Beta to `usd_broad_credit_oas_bp` | Sensitivity-scaled moves; beta division is not hedging. |
| Did banks depart from their usual return relationship? | `usd_banks_tr` dependent, `usd_equity_tr` explanatory; Return, Monthly, Regression | Ignores arbitrary index bases. Fits are descriptive; structural change and overlapping endpoints matter. |
| Which credit index performed better? | `usd_hy_tr` minus `usd_ig_tr`; Return | Percentage-point index-return difference; spread growth is not bond return. |
| How did wealth grow from a common date? | Any two corresponding `_100` series; Level | Growth since 2015-01-02. Raw unrebased levels answer no common-wealth question. |
| What did FX add to EUR equity performance? | `eur_equity_usd_tr` vs USD benchmark; Return | Explicit unhedged conversion; currency metadata alone would not convert values. |
| How much policy movement passed through? | Deposit move / policy move over an explicitly selected episode | Select material policy-change episodes after retaining baselines. No all-date ratio Z-score or monitoring claim. |
| Are native credit markets moving differently? | EUR IG vs GBP/USD IG OAS | Descriptive native-market comparison only; neither currency nor reference curves have been harmonized. |

No all-date event-ratio filtering, FX hedge or curve rebasing is implicit.
Duration matching applies only to each explicitly supplied toy credit benchmark.
Monthly precomputed returns avoid a second transformation but do not
remove the engine's sparse-cadence restrictions. Synthetic statistics validate
mechanics, not economic calibration or investment performance.

## Isolated edge cases

Keep the `edge_` columns outside the ordinary research universe:

| Column | Deliberate behavior |
| --- | --- |
| `edge_gapped_ig_bp` | Individual missing sessions plus a ten-session gap; exact-date alignment and missing baselines. |
| `edge_stale_ig_bp` | Values stop after 2026-09-11; no carried observations. |
| `edge_short_ig_bp` | Only 40 observations; insufficient risk/reference history. |
| `edge_constant_bp` | Zero variance; unavailable risk scales and constant regression predictor. |
| `edge_signed_yield_bp` | Negative, zero and positive values; ordinary growth needs positive baselines. |
| `edge_denominator_bp` | Zero, tiny positive/negative and ordinary signed values; denominator pathology. |
| `edge_inverse_credit_bp` | Stable beta −2 to broad-credit changes; signed scaling. |
| `edge_tiny_beta_bp` | Beta approximately 0.0001; numerical nonzero does not mean economically usable. |

Guidance: [Analysis skill](../../../src/kairopsis/skills/kairopsis-analysis/SKILL.md),
[input shaping and design](../../../src/kairopsis/skills/kairopsis-analysis/references/analysis-design.md),
[application contract](../../../src/kairopsis/skills/kairopsis-analysis/references/application-contract.md).
