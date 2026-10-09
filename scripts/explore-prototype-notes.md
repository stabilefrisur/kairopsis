# Explore UI prototype

Question: which workspace layout best supports comparing exposures, challenging
a Relative Value View, and capturing evidence? Three layouts, one synthetic
collection and shared in-memory investigation state.

Branch: `codex/explore-workspace-prototype`. Built by GPT-6.1 Sol at high effort;
independently explored and reviewed by the parent agent, 2026-10-09.

## Review verdict

**Prefer A / Workbench as the default.** Its collection, simultaneous charts and
selected-view editor support comparison without losing context. Retain B / Focus
as a way to concentrate on one chart. C / Research sheet is useful for writing up
evidence; its notes should inform the design, without imposing a narrative on
free exploration. These are proposed directions, pending user review.

The prototype validates six chart families, multiple fields per exposure,
cross-sectional/history/panel mappings, separate global date and history, explicit
per-view pins, highlight versus filter, and frozen evidence capture. Before real
implementation, map the remaining [research use cases](../docs/research/relative-value-exploration-workspace.md)
to controls and data contracts; the prototype does not settle every workflow.

Browser review exercised 26 interaction checks plus independent sample arithmetic
and layout checks. Real chart clicks, KDE/histogram/box changes, paired correlation
drilldowns, snapshot immutability and layout state continuity passed. All 64
temporal Pearson coefficients and the cross-sectional field matrix matched
independent calculations. No browser runtime errors or network writes observed.

Review corrections: unclipped desktop title; visible Focus view switching;
compact Research sheet intro; laptop editor beside charts; expanded editors
retained through changes; correlation evidence preserves its complete sample,
excluded dates and transformation inputs. Desktop/laptop are the intended review
surfaces; narrow screens stack without horizontal overflow, but phone ergonomics
remain unvalidated. Synthetic fixture only; no production integration.

## Run

Run from the repository root:

```bash
.venv/bin/python scripts/explore_prototype.py
```

Open `http://127.0.0.1:8766/prototype/explore?variant=A`.
Use `--port 8767` to choose another port. Existing FastAPI/Jinja/Plotly only.
Normal Kairopsis does not register this route, runner or switcher. No real app
repository/provider is constructed. No APIs, local storage or research writes.

## Layouts

- **A / Workbench**: reusable collection left, simultaneous comparison canvas,
  selected-view settings right. Best for examining several forms of evidence.
- **B / Focus**: dominant chart with view filmstrip and adjacent settings;
  collection folded above. Best for deliberate work on one view.
- **C / Research sheet**: working question, vertically ordered sections, research
  notes and inline settings. Best for writing an argument around evidence.

The bottom switcher updates `?variant=A/B/C`; left/right keyboard arrows cycle
outside editable controls and dialogs. Layout changes preserve the entire
workspace. Refresh resets it. Collapsible state inspector and
`window.explorePrototype` expose definitions, samples and synthetic inputs.

## Design direction

Keep Kairopsis's existing Segoe UI/Calibri typography and blue/slate visual shell.
White `#ffffff` paper; `#f3f5f8` canvas; `#203047` text; `#627185` secondary text;
`#255cc5` selected views; `#147b86` MBS exposure. Colour identifies exposures and
groups, rather than decorating independent cards. Plots carry the information
hierarchy; local samples, observation counts and formulas qualify the evidence.
Structural differences live in layout, not palette changes.

## Working coverage

Eight USD credit exposures, four numeric fields each, 157 deterministic weekly
dates from 2023-10-06 through 2026-10-02. EM HY deliberately misses every 13th
observation. Fixed classifications and membership; synthetic current-universe
history. Derived spread-minus-US-IG field stands in for a saved Pair Analysis
output; no real Analysis is read or revised.

Six rendered chart families: multi-exposure history; exposure/date/panel scatter;
ranked comparisons; KDE with histogram/box alternatives; exposure-week heatmap;
correlation across exposures over dates or fields across exposures. Field and
axis transformations calculate from the same numeric inputs. Descriptive linear
scatter fit optional. Gaussian KDE uses Silverman bandwidth × adjustable factor;
tiny/constant samples stay points. Correlation is Pearson with common complete
observations; drilling a cell retains the matrix sample. No inference claims.

Global exact as-of and history are distinct. Weekly change uses the previous
calendar week, including its raw observation outside the display window.
Percentage change is proportional field change; not automatically an investment
return. Rebase anchors the first exact date in the window, and is unavailable
when that anchor is missing/zero. Z-score uses available values in that exposure's
selected history. Changes retain original field units. No forward filling.

Collection inclusion changes collection-based views. Linked highlight identifies exposures
and dates without removing peers. Explicit filter changes the sample and says so.
Temporal scatter has explicit X/Y exposures, independent of collection inclusion.
Per-view pinned date/history enable comparisons. Add, duplicate, move earlier,
full-width (Workbench), maximise and remove act in memory.

Snapshot simulation retains frozen chart image, all input/plotted observations,
settings, source/basis, collection, selection, local/global context, notes and
supporting/challenging/context role. Inspect captured evidence after changing the
workspace to verify it stays frozen. No real Idea save or persistence.

## Deliberately deferred

Provider integration, real saved Analysis import, typed binding association,
multi-view persistent investigations, editable relationship/composite builders,
weights, frequency choices, regimes/events, rolling estimates, residual views,
Spearman, curves and econometric modelling. No misleading inactive controls for
these. This is a comparison prototype, not full RV01–RV22 coverage or production
rollout. Browser interaction review replaces a committed automated test suite.
