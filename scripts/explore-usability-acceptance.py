"""Exercise Explore editing, automatic updates and secondary controls in a mock app.

Usage: .venv/bin/python scripts/explore-usability-acceptance.py --url http://127.0.0.1:8769
Requires development-only Playwright/Chromium; use a disposable mock workspace.
"""
import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


async def run(url: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1569, "height": 1035})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        async def current() -> None:
            await page.wait_for_function("explore.status==='current' && !explore.previewInFlight", timeout=60000)
            await page.wait_for_function("[...document.querySelectorAll('.plot')].filter(p=>p.offsetParent!==null).every(p=>p.data?.length || p.querySelector('.empty'))")

        try:
            await page.goto(url.rstrip("/") + "/explore")
            await page.wait_for_load_state("networkidle")
            assert await page.locator("body").get_attribute("data-mode") == "mock"
            for key in ("usd-ig", "hy"):
                await page.locator(f'[data-explore="add-item"][data-kind="series"][data-id="{key}"]').click()
            await page.get_by_role("button", name="Add chart", exact=True).click()
            await current()
            assert await page.locator('.explore-context [name="new_family"]').count() == 0
            assert await page.locator('[data-capture-view]').count() == 0
            assert await page.locator('#explore-capture-role').count() == 0
            assert await page.locator('.explore-collection input[data-association]').count() == 0
            assert await page.locator('.explore-view .plot').evaluate("p=>p.data.length") == 2

            await page.locator('[data-explore="add-item"][data-id="eur-ig"]').click()
            await page.get_by_label("eur-ig / spread", exact=True).check()
            await current()
            assert await page.locator('.explore-view .plot').evaluate("p=>p.data.length") == 3
            await page.get_by_label("Chart type", exact=True).select_option("scatter")
            await current()
            assert await page.evaluate("explore.results.get(explore.selected).view.shape") == "paired_date"
            assert await page.get_by_label("X axis", exact=True).is_visible()
            await page.get_by_role("button", name="Enlarge", exact=True).click()
            await page.get_by_role("button", name="Back to overview", exact=True).first.click()
            assert await page.locator('.explore-layout.workbench').count() == 1
            print("PASS: selecting EUR IG and changing chart type update automatically; overview exit visible")

            await page.get_by_label("Chart type", exact=True).select_option("history")
            await current()
            held = asyncio.Event()
            release = asyncio.Event()
            intercepted = 0

            async def delay_first(route):
                nonlocal intercepted
                intercepted += 1
                if intercepted == 1:
                    held.set()
                    await release.wait()
                await route.continue_()

            await page.route("**/api/explore/preview", delay_first)
            await page.get_by_label("Chart type", exact=True).select_option("scatter")
            await asyncio.wait_for(held.wait(), timeout=10)
            await page.get_by_label("Chart title", exact=True).fill("Latest comparison")
            await page.get_by_label("Chart type", exact=True).select_option("ranking")
            await page.get_by_role("button", name="Save to Idea…", exact=True).click()
            assert not await page.locator('[data-explore="capture-dialog"]').is_enabled()
            assert await page.evaluate("explore.results.get(explore.selected).view.family") == "history"
            release.set()
            await current()
            assert await page.evaluate("explore.results.get(explore.selected).view.family") == "ranking"
            assert await page.get_by_label("Chart title", exact=True).input_value() == "Latest comparison"
            assert intercepted == 2
            await page.unroute("**/api/explore/preview", delay_first)
            await page.locator('[data-explore="cancel-selection"]').click()
            await page.get_by_label("Chart title", exact=True).fill("Temporary title")
            await page.get_by_label("Chart title", exact=True).fill("Latest comparison")
            await page.get_by_label("Chart title", exact=True).press("Tab")
            await current()
            assert not await page.evaluate("explore.editingText")
            print("PASS: latest settings win during a delayed update; stale evidence cannot be saved")

            await page.route("**/api/explore/preview", lambda route: route.fulfill(status=503, json={"detail": "Temporary test failure"}))
            await page.get_by_label("Chart type", exact=True).select_option("history")
            await page.wait_for_function("explore.status==='failed'")
            assert await page.evaluate("explore.results.get(explore.selected).view.family") == "ranking"
            assert await page.get_by_role("button", name="Retry update", exact=True).is_visible()
            await page.unroute("**/api/explore/preview")
            await page.get_by_role("button", name="Retry update", exact=True).click()
            await current()
            assert await page.evaluate("explore.results.get(explore.selected).view.family") == "history"
            assert "visible" not in (await page.locator('#message').get_attribute('class') or '')
            print("PASS: failed update preserves previous chart and offers retry")

            source = await page.evaluate("explore.workspace.collection[0].binding")
            first_source = page.locator('.explore-source').first
            await first_source.locator('summary').click()
            await first_source.get_by_role("button", name="Change chart grouping…", exact=True).click()
            await page.get_by_label("Symbol used in charts", exact=True).fill("US IG")
            await page.get_by_role("button", name="Use grouping", exact=True).click()
            await current()
            assert await page.evaluate("explore.workspace.collection[0].binding") == source
            await page.get_by_text("Grouping & classifications", exact=True).click()
            await page.get_by_role("button", name="Edit classifications…", exact=True).click()
            await page.get_by_role("button", name="Add classification", exact=True).click()
            await page.get_by_label("Classification (e.g. sector)", exact=True).fill("Region")
            await page.get_by_label("Value", exact=True).fill("US")
            await page.get_by_label("Source", exact=True).fill("Supplied test classification")
            await page.get_by_role("button", name="Save classifications", exact=True).click()
            await current()
            assert await page.evaluate("explore.workspace.attributes[0].source") == "Supplied test classification"
            assert await page.locator('#explore-attributes').count() == 0
            print("PASS: chart grouping leaves provider query unchanged; classifications use ordinary fields")

            await page.get_by_role("button", name="Add calculation…", exact=True).click()
            assert await page.get_by_role("button", name="Add to workspace", exact=True).is_visible()
            assert await page.get_by_role("button", name="Define new input…", exact=True).is_visible()
            await page.get_by_role("button", name="Define new input…", exact=True).click()
            assert await page.get_by_role("button", name="Use as calculation input", exact=True).is_visible()
            await page.locator('#explore-dialog').get_by_role("button", name="Cancel", exact=True).click()
            await page.locator('#explore-dialog').get_by_role("button", name="Cancel", exact=True).click()
            await page.get_by_role("button", name="Save to Idea…", exact=True).click()
            assert await page.locator('[data-capture-view]').count() == 1
            await page.get_by_role("button", name="Clear selection", exact=True).click()
            assert not await page.get_by_role("button", name="Continue…", exact=True).is_enabled()
            await page.get_by_role("button", name="Select all", exact=True).click()
            await page.get_by_role("button", name="Continue…", exact=True).click()
            assert await page.get_by_label("How does this evidence relate to the Idea?", exact=True).is_visible()
            await page.get_by_label("How does this evidence relate to the Idea?", exact=True).select_option("challenging")
            await page.screenshot(path=str(output / "save-evidence.png"))
            await page.locator('#explore-dialog').get_by_role("button", name="Cancel", exact=True).click()
            await page.locator('[data-explore="cancel-selection"]').click()
            await page.get_by_role("heading", name="Explore", exact=True).scroll_into_view_if_needed()
            await page.screenshot(path=str(output / "workspace.png"))
            await page.set_viewport_size({"width":1180,"height":820})
            assert not await page.evaluate("document.documentElement.scrollWidth>innerWidth")
            await page.screenshot(path=str(output / "laptop.png"))
            assert not errors, errors
            print("PASS: explicit chart selection/save dialog, input/calculation labels and laptop layout; no JS errors")
        finally:
            await page.screenshot(path=str(output / "last-state.png"))
            await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, default=Path(".scratch/explore-usability"))
    args = parser.parse_args()
    asyncio.run(run(args.url, args.output))
