"""Exercise production Explore against an isolated, running mock app.

Usage: .venv/bin/python scripts/explore-ui-acceptance.py --url http://127.0.0.1:8767
Requires development-only Playwright and its Chromium browser. Creates test
workspaces/Ideas in the supplied mock repository; use a disposable workspace.
"""
import argparse
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4

from playwright.sync_api import sync_playwright


def verify_fork(page, url: str) -> None:
    """A frozen capture remains immutable while a fork restores authoring choices."""
    capture_url = page.url
    parts = capture_url.rstrip("/").split("/")
    snapshot_url = url.rstrip("/") + "/api/explore/captures/" + "/".join(parts[-2:])
    with urlopen(snapshot_url) as response:
        original_hash = sha256(response.read()).hexdigest()
    retained_workspace = page.evaluate("window.exploreWorkspace.workspace")
    requests: list[str] = []
    page.on("request", lambda request: requests.append(request.url))
    page.route("**/api/ideas", lambda route: route.fulfill(status=503, json={"detail": "Authoring metadata unavailable"}))
    page.locator('[data-explore="fork"]').click()
    page.wait_for_function("document.querySelector('#message').textContent==='Authoring metadata unavailable'")
    assert page.url == capture_url
    assert page.evaluate("window.exploreWorkspace.capture.id") == parts[-1]
    assert page.evaluate("window.exploreWorkspace.workspace") == retained_workspace
    assert not any("/api/explore/preview" in request for request in requests)
    page.unroute("**/api/ideas")
    page.locator('[data-explore="fork"]').click()
    page.wait_for_function("window.exploreWorkspace.capture===null")
    assert page.url == url.rstrip("/") + "/explore"
    fork = page.evaluate("window.exploreWorkspace.workspace")
    assert fork["id"] != retained_workspace["id"] and fork["version"] is None
    assert fork["collection"] == retained_workspace["collection"]
    assert fork["question"] == retained_workspace["question"] and fork["notes"] == retained_workspace["notes"]
    assert page.locator('[data-explore="add-item"][data-kind="analysis"]').count() > 0
    assert page.locator('[name="saved_workspace"] option').count() > 1
    page.locator('[data-explore="add-item"][data-kind="series"][data-id="eur-ig"]').click()
    assert page.evaluate("window.exploreWorkspace.workspace.collection.at(-1).binding.id") == "eur-ig"
    page.locator('[name="new_family"]').select_option("history")
    page.locator('[data-explore="add-view"]').click()
    page.wait_for_function("window.exploreWorkspace.status === 'current' && !window.exploreWorkspace.previewInFlight", timeout=60000)
    assert page.evaluate("window.exploreWorkspace.status") == "current", page.locator("#message").inner_text()
    assert page.evaluate("window.exploreWorkspace.results.get(window.exploreWorkspace.selected).rows.some(row=>row.symbol==='eur-ig')")
    page.locator('[data-explore="select-save"]').click()
    page.locator('[data-explore="capture-dialog"]').click()
    assert page.locator('#explore-capture-idea option').count() > 1
    page.locator('[data-explore="capture"]').click()
    page.wait_for_url("**/explore/captures/**", timeout=60000)
    page.wait_for_load_state("networkidle")
    assert page.url != capture_url
    assert page.evaluate("window.exploreWorkspace.workspace.collection.some(item=>item.binding?.id==='eur-ig')")
    with urlopen(snapshot_url) as response:
        assert sha256(response.read()).hexdigest() == original_hash
    print("PASS: fork metadata failure preserves evidence; retry restores Library/Analysis/workspace/Idea choices, adds binding, previews and captures immutable fork")


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
        page.locator("#explore-notes").press("Tab")

        def preview() -> None:
            page.wait_for_function("window.exploreWorkspace.status === 'current' && !window.exploreWorkspace.previewInFlight", timeout=60000)
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
        distribution_id = page.evaluate("window.exploreWorkspace.workspace.views.find(v=>v.family==='distribution').id")

        def distribution_geometry() -> dict:
            geometry = page.locator(f'#explore-plot-{distribution_id}').evaluate("""plot => ({
              width:plot._fullLayout._size.w,height:plot._fullLayout._size.h,
              legends:plot._fullData.filter(trace=>trace.showlegend).length,
              orientation:plot._fullLayout.legend.orientation,
              grouped:plot._fullData.every(trace=>trace.legendgroup),
            })""")
            assert geometry["width"] > 200 and geometry["height"] > 100, geometry
            assert geometry["legends"] == 3 and geometry["orientation"] == "h" and geometry["grouped"], geometry
            return geometry

        distribution_geometry()
        # Inspect actual bundled Plotly titles, not only the input layout.
        scatter_titles = page.evaluate("""() => {
          const state=window.exploreWorkspace, view=state.workspace.views.find(v=>v.family==='scatter');
          const layout=document.querySelector('#explore-plot-'+view.id)._fullLayout;
          return [layout.xaxis.title.text,layout.yaxis.title.text];
        }""")
        assert all("bp" in title and "Click to enter" not in title for title in scatter_titles), scatter_titles
        print("PASS: six production chart families")
        page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
        page.set_viewport_size({"width": 1180, "height": 900})
        page.wait_for_function(f"document.querySelector('#explore-plot-{distribution_id}')._fullLayout.width > 500")
        distribution_geometry()
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.screenshot(path=str(screenshots / "laptop.png"), full_page=True)
        page.locator(f'[data-view="{distribution_id}"] [data-explore="focus-view"]').click()
        page.wait_for_function(f"document.querySelector('#explore-plot-{distribution_id}')._fullLayout.height > 500")
        assert distribution_geometry()["width"] > 500
        page.screenshot(path=str(screenshots / "distribution-focus.png"), full_page=True)
        page.get_by_role("button", name="Back to overview", exact=True).click()
        correlation_id = page.evaluate("window.exploreWorkspace.workspace.views.find(v=>v.family==='correlation').id")
        page.locator(f'[data-explore="select"][data-id="{correlation_id}"]').first.click()
        page.wait_for_function(f"document.querySelector('#explore-plot-{correlation_id}')._fullLayout")
        print("PASS: readable Distribution at 1440/1180 and Focus; three grouped legend entries")

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
        selected.locator("summary").filter(has_text="Observations ·").click()
        selected.locator('[data-explore="exclude-row"]').first.click()
        preview()
        assert page.evaluate("window.exploreWorkspace.results.get(window.exploreWorkspace.selected).rows.length") == old_count - 1
        page.locator('#explore-view-form [name="family"]').select_option("correlation")
        preview()
        assert page.evaluate("window.exploreWorkspace.results.get(window.exploreWorkspace.selected).rows.length") == old_count - 1

        # Empty member selection stays empty across preview.
        page.locator('#explore-view-form summary').filter(has_text="Filter observations").click()
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
        page.locator('#explore-view-form [name="interval_measure"]').select_option("return")
        page.locator('#explore-view-form [name="interval_start"]').fill(interval_start)
        preview()
        interval_titles = page.locator(f'#explore-plot-{ranking_id}').evaluate("plot=>[plot._fullLayout.yaxis.title.text,plot._fullLayout.yaxis2.title.text]")
        assert "%" in interval_titles[0] and "bp" in interval_titles[1], interval_titles
        print("PASS: shared controls applied on first click; local Analysis evaluated in a view")
        page.locator('[data-explore="select-save"]').click()
        page.locator('[data-explore="capture-dialog"]').click()
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
        distribution_geometry()
        image_url = page.locator(f'[data-view="{distribution_id}"] a[download]').get_attribute("href")
        image_response = page.request.get(url.rstrip("/") + image_url)
        assert image_response.ok
        image_bytes = image_response.body()
        assert image_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        assert (int.from_bytes(image_bytes[16:20], "big"), int.from_bytes(image_bytes[20:24], "big")) == (1400, 850)
        (screenshots / "distribution-captured.png").write_bytes(image_bytes)

        # Frozen reopen never queries Library or live observations.
        requests: list[str] = []
        page.on("request", lambda request: requests.append(request.url))
        page.reload(wait_until="networkidle")
        assert not any("/api/explore/library" in request or "/api/explore/preview" in request for request in requests)
        assert page.locator("#explore-status").inner_text() == "Saved chart evidence"
        assert not errors, errors
        print("PASS: workspace save, eight-view capture, frozen offline reopen, original PNG links, layouts")
        print("Captured evidence:", page.url)
        verify_fork(page, url)
        assert not errors, errors
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Running isolated mock app URL")
    parser.add_argument("--screenshots", type=Path, default=Path("/tmp/kairopsis-explore-ui"))
    arguments = parser.parse_args()
    run(arguments.url, arguments.screenshots)
