"""Focused real-browser rationale journey; run against an isolated mock workspace."""
import argparse
import json
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright


RATIONALE = "Why compensation diverges <b>across markets</b>.\n\nLiquidity may explain it. <script>window.rationaleExecuted = true</script>"
REVISED = "A revised Library hypothesis.\n\nAlternative: changing composition."


def journey(url: str, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url + "/library?edit=usd-ig")
        page.wait_for_load_state("networkidle")
        rationale = page.get_by_label("Economic rationale", exact=True)
        expect(rationale).to_have_value("")
        rationale.fill(RATIONALE)
        page.get_by_role("combobox", name="Input measure", exact=True).select_option("change")
        expect(rationale).to_have_value(RATIONALE)
        page.get_by_role("combobox", name="Input measure", exact=True).select_option("level")
        page.locator('[data-action="stage-series"]').first.click()
        dialog = page.locator("#library-series-dialog")
        dialog.get_by_label("Name", exact=True).fill("Staged USD rationale input")
        dialog.get_by_role("button", name="Apply series", exact=True).click()
        expect(rationale).to_have_value(RATIONALE)
        page.get_by_role("button", name="Preview", exact=True).click()
        expect(page.locator("#library-preview-status")).to_contain_text("Preview current", timeout=30000)
        page.locator("#library-preview-details summary").click()
        captured = page.locator("#library-preview-details .economic-rationale")
        expect(captured).to_have_text(RATIONALE)
        assert captured.locator("b, script").count() == 0
        assert page.evaluate("window.rationaleExecuted") is None
        assert captured.evaluate("el => getComputedStyle(el).whiteSpace") == "pre-wrap"
        rationale.fill(REVISED)
        expect(page.locator("#library-preview-status")).to_contain_text("Outdated")
        expect(captured).to_have_text(RATIONALE)
        page.screenshot(path=str(output / "outdated-rationale.png"), full_page=True)

        # An actual failed HTTP preview retains draft and prior captured details.
        def failed_preview(route):
            route.fulfill(status=422, content_type="application/json", body=json.dumps({"detail": "Acceptance preview failure"}))
        page.route("**/api/library/analyses/preview", failed_preview)
        page.get_by_role("button", name="Preview", exact=True).click()
        expect(page.locator("#library-preview-status")).to_contain_text("Preview failed")
        expect(rationale).to_have_value(REVISED)
        expect(captured).to_have_text(RATIONALE)
        page.unroute("**/api/library/analyses/preview", failed_preview)
        rationale.fill(RATIONALE)
        page.get_by_role("button", name="Preview", exact=True).click()
        expect(page.locator("#library-preview-status")).to_contain_text("Preview current", timeout=30000)
        page.get_by_role("button", name="Save analysis and 1 series", exact=True).click()
        page.wait_for_url(url + "/analyses/usd-ig")
        page.wait_for_selector("#plot .main-svg")
        page.locator(".evidence-details summary").click()
        expect(page.locator(".economic-rationale")).to_have_text(RATIONALE)
        page.get_by_role("button", name="Save to Idea", exact=True).click()
        page.get_by_label("Title", exact=True).fill("Rationale acceptance " + uuid4().hex[:6])
        page.get_by_role("button", name="Save chart", exact=True).click()
        page.wait_for_url("**/ideas/*")
        idea_url = page.url
        page.wait_for_selector(".saved-plot .main-svg")
        page.locator(".evidence-details summary").click()
        expect(page.locator(".economic-rationale")).to_have_text(RATIONALE)

        page.goto(url + "/analyses/usd-ig")
        page.wait_for_load_state("networkidle")
        page.get_by_role("combobox", name="Reference history", exact=True).select_option("1")
        page.wait_for_function("state.previewCurrent && state.evaluation.definition.settings.history_years === 1")
        assert page.evaluate("state.evaluation.definition.economic_rationale") == RATIONALE
        page.get_by_role("link", name="Edit defaults in Library", exact=True).click()
        page.wait_for_load_state("networkidle")
        expect(rationale).to_have_value(RATIONALE)
        rationale.fill(REVISED)
        page.get_by_role("button", name="Use exploratory settings", exact=True).click()
        expect(rationale).to_have_value(REVISED)
        expect(page.get_by_role("combobox", name="Reference history", exact=True)).to_have_value("1")
        def failed_save(route):
            route.fulfill(status=422, content_type="application/json", body=json.dumps({"detail": "Acceptance save validation failure"}))
        page.route("**/api/library/analyses/bundle", failed_save)
        page.get_by_role("button", name="Save defaults", exact=True).click()
        expect(page.locator("#message")).to_contain_text("Acceptance save validation failure")
        expect(rationale).to_have_value(REVISED)
        expect(page.get_by_role("button", name="Save defaults", exact=True)).to_be_enabled()
        page.unroute("**/api/library/analyses/bundle", failed_save)
        page.get_by_role("button", name="Preview", exact=True).click()
        expect(page.locator("#library-preview-status")).to_contain_text("Preview current", timeout=30000)
        page.get_by_role("button", name="Save defaults", exact=True).click()
        page.wait_for_url(url + "/analyses/usd-ig")
        page.wait_for_selector("#plot .main-svg")
        assert page.evaluate("state.evaluation.definition.economic_rationale") == REVISED
        page.goto(idea_url)
        page.wait_for_selector(".saved-plot .main-svg")
        page.locator(".evidence-details summary").click()
        expect(page.locator(".economic-rationale")).to_have_text(RATIONALE)
        page.get_by_role("button", name="Latest data", exact=True).click()
        page.wait_for_selector('[id^="latest-"] .main-svg')
        page.locator(".evidence-details summary").click()
        expect(page.locator(".economic-rationale")).to_have_text(RATIONALE)
        page.screenshot(path=str(output / "retained-latest-rationale.png"), full_page=True)
        page.goto(url + "/library?edit=usd-ig")
        page.wait_for_load_state("networkidle")
        expect(rationale).to_have_value(REVISED)
        rationale.fill("Discard this unsaved rationale")
        page.get_by_role("button", name="Cancel", exact=True).click()
        page.goto(url + "/library?edit=usd-ig")
        page.wait_for_load_state("networkidle")
        expect(rationale).to_have_value(REVISED)
        page.goto(url + "/analyses/eur-gbp")
        page.wait_for_load_state("networkidle")
        page.locator(".evidence-details summary").click()
        expect(page.locator(".economic-rationale")).to_have_text("No economic rationale recorded")
        assert not errors, errors
        result = {"idea_url": idea_url, "script_errors": errors, "checks": ["multiline literal rendering", "controls and staged-input draft retention", "outdated captured preview", "preview and save failure retention", "save/reopen", "exploratory transfer preserves Library draft", "saved and Latest evidence retains earlier rationale", "cancel discards draft", "empty evidence state"]}
        (output / "browser-result.json").write_text(json.dumps(result, indent=2))
        browser.close()
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(journey(args.url.rstrip("/"), args.output), indent=2))
