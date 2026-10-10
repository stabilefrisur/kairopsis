"""Exercise production Explore against an isolated, running mock app.

Usage: .venv/bin/python scripts/explore-ui-acceptance.py --url http://127.0.0.1:8767
Requires development-only Playwright and its Chromium browser. Creates test
workspaces/Ideas in the supplied mock repository; use a disposable workspace.
"""
import argparse
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import sync_playwright


def run(url: str, screenshots: Path) -> None:
    screenshots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url.rstrip("/") + "/explore")
        page.wait_for_load_state("networkidle")
        assert page.locator("body").get_attribute("data-mode") == "mock", "Use an isolated mock app"
        page.locator('[name="workspace_name"]').fill("Explore acceptance " + uuid4().hex[:8])
        for identifier in ["usd-ig", "hy", "mbs"]:
            page.locator(f'[data-explore="add-item"][data-kind="series"][data-id="{identifier}"]').click()
        for family in ["history", "scatter", "ranking", "distribution", "heatmap", "correlation"]:
            page.locator('[name="new_family"]').select_option(family)
            page.locator('[data-explore="add-view"]').click()
        page.locator(".explore-research summary").click()
        page.locator("#explore-question").fill("Which credit series moved most?")
        page.locator("#explore-notes").fill("Compare the retained dates; inspect missing observations.")

        def preview() -> None:
            page.locator('[data-explore="preview"]').click()
            page.wait_for_function("window.exploreWorkspace.status !== 'previewing'")
            assert page.evaluate("window.exploreWorkspace.status") == "current", page.locator("#message").inner_text()
            page.wait_for_function("[...document.querySelectorAll('.plot')].filter(p=>p.offsetParent!==null).every(p=>p.data?.length || p.querySelector('.empty'))")

        preview()
        assert page.evaluate("[...window.exploreWorkspace.results.values()].every(r=>r.statistics.traces.length)")
        assert page.evaluate("window.exploreWorkspace.results.size") == 6
        # First preview must match the untouched Distribution inspector defaults.
        distribution_groups = page.evaluate("[...window.exploreWorkspace.results.values()].find(r=>r.view.family==='distribution').statistics.groups")
        assert {group["group"] for group in distribution_groups} == {"usd-ig", "hy", "mbs"}, distribution_groups
        assert len(distribution_groups) == 3
        assert all(group["weight_policy"] == "equal_row" for group in distribution_groups)
        print("PASS: new three-symbol Distribution retains three equal-row groups")
        # Inspect actual bundled Plotly titles, not only the input layout.
        scatter_titles = page.evaluate("""() => {
          const state=window.exploreWorkspace, view=state.workspace.views.find(v=>v.family==='scatter');
          const layout=document.querySelector('#explore-plot-'+view.id)._fullLayout;
          return [layout.xaxis.title.text,layout.yaxis.title.text];
        }""")
        assert all("bp" in title and "Click to enter" not in title for title in scatter_titles), scatter_titles
        print("PASS: six production chart families")
        page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
        page.set_viewport_size({"width": 1200, "height": 900})
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.screenshot(path=str(screenshots / "laptop.png"), full_page=True)

        # Actual chart click retains the matrix cell's exact paired sample.
        matrix = page.locator('.explore-view.selected .plot')
        matrix.scroll_into_view_if_needed()
        point = matrix.evaluate("""plot => {
          const state = window.exploreWorkspace, result = state.results.get(state.selected);
          const cell = result.statistics.cells.find(cell=>cell.left!==cell.right);
          const rect = plot.getBoundingClientRect(), layout = plot._fullLayout;
          return {x:rect.x+layout.xaxis._offset+layout.xaxis.d2p(cell.left),
            y:rect.y+layout.yaxis._offset+layout.yaxis.d2p(cell.right)};
        }""")
        page.mouse.click(point["x"], point["y"])
        page.wait_for_function("window.exploreWorkspace.workspace.views.length===7")
        assert page.evaluate("window.exploreWorkspace.workspace.views.at(-1).sample.row_ids.length > 0")
        preview()
        old_count = page.evaluate("window.exploreWorkspace.results.get(window.exploreWorkspace.selected).rows.length")
        selected = page.locator(".explore-view.selected")
        selected.locator("details").filter(has=page.locator('summary')).first.locator("summary").click()
        selected.locator('[data-explore="exclude-row"]').first.click()
        preview()
        assert page.evaluate("window.exploreWorkspace.results.get(window.exploreWorkspace.selected).rows.length") == old_count - 1
        page.locator('#explore-view-form [name="family"]').select_option("correlation")
        preview()
        assert page.evaluate("window.exploreWorkspace.results.get(window.exploreWorkspace.selected).rows.length") == old_count - 1

        # Empty member selection stays empty across preview.
        page.locator('#explore-view-form summary').filter(has_text="Filter symbols").click()
        while page.locator('#explore-view-form [name="members"]:checked').count():
            page.locator('#explore-view-form [name="members"]:checked').first.uncheck()
        assert page.evaluate("window.exploreWorkspace.workspace.views.at(-1).sample.members") == []
        preview()
        assert page.evaluate("window.exploreWorkspace.results.get(window.exploreWorkspace.selected).rows.length") == 0
        for index in range(page.locator('#explore-view-form [name="members"]').count()):
            page.locator('#explore-view-form [name="members"]').nth(index).check()
        preview()

        print("PASS: actual correlation drilldown, sample exclusion and empty selection")

        # Shared Analysis controls resolve an independent local calculation.
        page.locator('[data-explore="new-analysis"]').click()
        page.locator('#explore-analysis-form [name="name"]').fill("Local weekly changes")
        page.locator('#explore-analysis-form [name="measure"]').select_option("change")
        page.locator('#explore-analysis-form [data-risk="method"]').select_option("volatility")
        page.locator('#explore-analysis-form [data-risk="weighting"]').select_option("exponential")
        page.locator('#explore-analysis-form [data-risk="half_life"]').fill("42")
        page.locator('[data-explore="apply-analysis"]').click()
        page.wait_for_function("window.exploreWorkspace.workspace.collection.length===4")
        assert page.locator("#explore-dialog").get_attribute("open") is None
        assert page.evaluate("window.exploreWorkspace.workspace.collection.at(-1).analysis.settings.risk_adjustment.half_life") == 42
        page.locator('[name="new_family"]').select_option("history")
        page.locator('[data-explore="add-view"]').click()
        page.locator('[data-explore="save"]').click()
        page.wait_for_function("window.exploreWorkspace.workspace.version!==null")
        preview()
        assert page.evaluate("window.exploreWorkspace.results.get(window.exploreWorkspace.selected).rows.some(row=>row.symbol==='Local weekly changes' && Object.values(row.values).some(value=>value!==null))")
        # Percentage ranking keeps % on the result axis and bp on raw endpoints.
        ranking_id = page.evaluate("window.exploreWorkspace.workspace.views.find(v=>v.family==='ranking').id")
        page.locator(f'[data-explore="select"][data-id="{ranking_id}"]').first.click()
        interval_start = page.evaluate("[...window.exploreWorkspace.results.values()].find(r=>r.view.family==='history').rows[0].date")
        page.locator('#explore-view-form [name="interval_start"]').fill(interval_start)
        page.locator('#explore-view-form [name="interval_measure"]').select_option("return")
        preview()
        interval_titles = page.locator(f'#explore-plot-{ranking_id}').evaluate("plot=>[plot._fullLayout.yaxis.title.text,plot._fullLayout.yaxis2.title.text]")
        assert "%" in interval_titles[0] and "bp" in interval_titles[1], interval_titles
        print("PASS: shared controls applied on first click; local Analysis evaluated in a view")
        page.locator('[data-explore="capture"]').click()
        page.wait_for_url("**/explore/captures/**", timeout=60000)
        page.wait_for_load_state("networkidle")
        assert page.locator("#explore-question").input_value() == "Which credit series moved most?"
        assert page.locator("#explore-notes").input_value().startswith("Compare the retained dates")
        assert page.locator('a[download]').count() == 8
        page.wait_for_function("""() => {
          const state=window.exploreWorkspace, view=state.workspace.views.find(v=>v.family==='ranking');
          return document.querySelector('#explore-plot-'+view.id)?._fullLayout?.yaxis2;
        }""")
        frozen_titles = page.evaluate("""() => {
          const state=window.exploreWorkspace, view=state.workspace.views.find(v=>v.family==='ranking');
          const layout=document.querySelector('#explore-plot-'+view.id)._fullLayout;
          return [layout.yaxis.title.text,layout.yaxis2.title.text];
        }""")
        assert "%" in frozen_titles[0] and "bp" in frozen_titles[1], frozen_titles

        # Frozen reopen never queries Library or live observations.
        requests: list[str] = []
        page.on("request", lambda request: requests.append(request.url))
        page.reload(wait_until="networkidle")
        assert not any("/api/explore/library" in request or "/api/explore/preview" in request for request in requests)
        assert page.locator("#explore-status").inner_text().startswith("Captured evidence")
        assert not errors, errors
        print("PASS: workspace save, eight-view capture, frozen offline reopen, original PNG links, layouts")
        print("Captured evidence:", page.url)
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Running isolated mock app URL")
    parser.add_argument("--screenshots", type=Path, default=Path("/tmp/kairopsis-explore-ui"))
    arguments = parser.parse_args()
    run(arguments.url, arguments.screenshots)
