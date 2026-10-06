"""Real Chromium checks for shared Analysis controls against an isolated demo."""
import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from playwright.async_api import async_playwright, expect


async def journey(url: str, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 1000})
        page = await context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(url + "/library")
        await page.wait_for_load_state("networkidle")
        await page.get_by_role("button", name="Add analysis", exact=True).click()
        await page.get_by_label("Name", exact=True).fill("Controls acceptance " + uuid4().hex[:6])
        await page.get_by_role("combobox", name="Data series", exact=True).select_option("hy")
        await page.get_by_role("combobox", name="Method", exact=True).select_option("volatility")
        await expect(page.get_by_role("combobox", name="Input measure")).to_have_value("level")
        await page.get_by_role("combobox", name="Estimate risk from").select_option("return")
        await page.get_by_role("button", name="Preview", exact=True).click()
        await expect(page.locator("#library-preview-status")).to_contain_text("Preview current", timeout=30000)
        await expect(page.locator(".formula")).to_contain_text("level / SD of prior weekly")
        await page.screenshot(path=str(output / "level-volatility.png"), full_page=True)
        assert await page.evaluate("state.libraryPreview.result.unit") == "bp/%"
        await page.locator(".monitoring-controls summary").click()
        await page.get_by_label("Include in flag monitoring", exact=True).check()
        await page.get_by_label("Move threshold (analysis units, optional)").fill("8")
        await page.get_by_label("Material further move (analysis units, optional)").fill("2")
        await page.get_by_role("combobox", name="Input measure").select_option("return")
        await expect(page.get_by_role("combobox", name="Estimate risk from")).to_have_value("return")
        await expect(page.get_by_label("Move threshold (analysis units, optional)")).to_have_value("")
        await expect(page.get_by_label("Include in flag monitoring", exact=True)).to_be_checked()
        await page.get_by_role("combobox", name="Input measure").select_option("level")
        await page.get_by_role("combobox", name="Type", exact=True).select_option("pair")
        await expect(page.get_by_role("combobox", name="Calculation", exact=True)).to_have_value("difference")
        await page.get_by_role("combobox", name="Calculation", exact=True).select_option("ratio")
        await page.get_by_role("combobox", name="Denominator", exact=True).select_option("usd-ig")
        await page.get_by_role("combobox", name="Output scale", exact=True).select_option("zscore")
        await page.get_by_role("combobox", name="Type", exact=True).select_option("standalone")
        await expect(page.get_by_role("combobox", name="Output scale", exact=True)).to_have_value("zscore")
        await page.get_by_role("combobox", name="Type", exact=True).select_option("pair")
        await expect(page.get_by_role("combobox", name="Calculation", exact=True)).to_have_value("ratio")
        await expect(page.get_by_role("combobox", name="Denominator", exact=True)).to_have_value("usd-ig")
        await page.get_by_role("button", name="Preview", exact=True).focus()
        await page.keyboard.press("Enter")
        await expect(page.locator("#library-preview-status")).to_contain_text("Preview current", timeout=30000)
        assert await page.evaluate("state.libraryPreview.result.unit") == "σ"
        await page.screenshot(path=str(output / "ratio-zscore.png"), full_page=True)
        library_formula = await page.evaluate("analysisFormula(state.libraryPreview.result.definition)")
        draft_id = await page.evaluate("state.draft.id")
        await page.get_by_role("button", name="Save analysis", exact=True).click()
        await expect(page.locator("#library-form")).to_have_count(0)
        await page.goto(url + "/analyses/" + draft_id)
        await page.wait_for_selector("#plot .main-svg")
        await expect(page.get_by_role("combobox", name="Input measure")).to_have_value("level")
        await expect(page.get_by_role("combobox", name="Output scale", exact=True)).to_have_value("zscore")
        assert await page.evaluate("analysisFormula(state.evaluation.definition)") == library_formula
        assert await page.evaluate("state.evaluation.unit") == "σ"
        # Last response wins, even when the first request finishes later.
        intercepted = 0
        async def delayed(route):
            nonlocal intercepted
            intercepted += 1
            if intercepted == 1:
                await asyncio.sleep(1.5)
            await route.fulfill(response=await route.fetch())
        await page.route("**/api/analyses/*/preview", delayed)
        await page.get_by_role("combobox", name="Input measure").select_option("change")
        await page.get_by_role("combobox", name="Input measure").select_option("return")
        await page.wait_for_function("state.previewCurrent && state.evaluation.definition.settings.measure === 'return'")
        await asyncio.sleep(2)
        assert await page.evaluate("state.evaluation.definition.settings.measure") == "return"
        await page.unroute("**/api/analyses/*/preview", delayed)
        await page.get_by_role("combobox", name="Calculation", exact=True).select_option("regression")
        await page.wait_for_function("state.previewCurrent && state.evaluation.definition.calculation === 'regression'")
        await page.get_by_label("Customize per series").check()
        await page.wait_for_function("state.previewCurrent && state.evaluation.definition.settings.risk_overrides.length === 2")
        first, second = page.locator('[data-risk="estimation_measure"][data-leg="0"]'), page.locator('[data-risk="estimation_measure"][data-leg="1"]')
        await first.select_option("change")
        await page.wait_for_function("state.previewCurrent && state.evaluation.definition.settings.risk_overrides[0].estimation_measure === 'change'")
        await second.select_option("return")
        await page.wait_for_function("state.previewCurrent")
        await expect(first).to_have_value("change")
        await expect(second).to_have_value("return")
        await page.locator('[data-risk="weighting"][data-leg="0"]').select_option("exponential")
        await page.wait_for_function("state.previewCurrent")
        half = page.locator('[data-risk="half_life"][data-leg="0"]')
        await half.fill("77")
        await half.press("Tab")
        await page.wait_for_function("state.previewCurrent && state.evaluation.definition.settings.risk_overrides[0].half_life === 77")
        await expect(half).to_have_value("77")
        await page.screenshot(path=str(output / "regression-overrides.png"), full_page=True)
        # Repeated type changes preserve both overrides and the second series.
        await page.get_by_role("combobox", name="Type", exact=True).select_option("standalone")
        await page.wait_for_function("state.previewCurrent && state.evaluation.definition.calculation === 'level'")
        await page.get_by_role("combobox", name="Type", exact=True).select_option("pair")
        await page.wait_for_function("state.previewCurrent && state.evaluation.definition.calculation === 'regression'")
        await expect(first).to_have_value("change")
        await expect(second).to_have_value("return")
        # Invalid reference query retains a clearly identified old chart and complete draft.
        bad = await context.request.post(url + "/api/library/series", data={"id": "invalid-controls-" + uuid4().hex[:6], "name": "Unavailable demo input", "source": "Synthetic demo", "instrument": "unknown", "field": "spread", "unit": "bp", "currency": "USD"})
        bad_id = (await bad.json())["id"]
        await page.reload()
        await page.wait_for_selector("#plot .main-svg")
        await page.get_by_role("combobox", name="Numerator", exact=True).select_option(bad_id)
        await expect(page.locator("#investigation-status")).to_contain_text("Preview failed", timeout=30000)
        await expect(page.locator("#investigation-status")).to_contain_text("previous definition")
        await expect(page.get_by_role("combobox", name="Numerator", exact=True)).to_have_value(bad_id)
        await page.screenshot(path=str(output / "invalid-input.png"), full_page=True)
        # Omitted contract stays v1 through a name edit; choosing a new feature promotes the draft.
        legacy_response = await context.request.post(url + "/api/library/analyses", data={
            "name": "Legacy controls " + uuid4().hex[:6], "calculation": "level", "series_ids": ["usd-ig"]})
        legacy = await legacy_response.json()
        await page.goto(url + "/library?edit=" + legacy["id"])
        await page.get_by_label("Name", exact=True).fill("Legacy name edit " + uuid4().hex[:6])
        assert await page.evaluate("state.draft.settings.calculation_contract") == "input-pipeline-v1"
        await page.get_by_role("combobox", name="Method", exact=True).select_option("volatility")
        await expect(page.get_by_role("combobox", name="Input measure")).to_have_value("level")
        assert await page.evaluate("state.draft.settings.calculation_contract") == "input-pipeline-v2"
        await page.get_by_role("button", name="Preview", exact=True).click()
        await expect(page.locator("#library-preview-status")).to_contain_text("Preview current", timeout=30000)
        await page.get_by_role("button", name="Save defaults", exact=True).click()
        await page.wait_for_url("**/analyses/" + legacy["id"])
        await page.wait_for_selector("#plot .main-svg")
        assert await page.evaluate("state.evaluation.definition.settings.calculation_contract") == "input-pipeline-v2"
        assert not errors, errors
        summary = {"analysis_id": draft_id, "script_errors": errors,
            "checks": ["shared formula/units", "level volatility without measure mutation", "ratio Z-score save/reopen",
                "keyboard preview", "monitor threshold clearing", "explicit basis persistence", "per-input regression",
                "arity restoration", "half-life editing", "delayed response suppression", "invalid data retains previous chart",
                "legacy name edit preserves v1", "v2 feature promotion save/reopen"]}
        (output / "result.json").write_text(json.dumps(summary, indent=2))
        await browser.close()
        return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8896")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(journey(args.url, args.output)), indent=2))
