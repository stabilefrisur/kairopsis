"""Real persistent journey against an isolated running source/installed app."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from playwright.sync_api import sync_playwright, expect


def journey(url: str, output: Path) -> dict:
    idea_title = "Rebuild acceptance question " + uuid4().hex[:8]
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 850}, accept_downloads=True,
                                      permissions=["clipboard-read", "clipboard-write"])
        external = []
        def guard(route):
            if urlsplit(route.request.url).hostname not in ("127.0.0.1", "localhost", "::1", None):
                external.append(route.request.url)
                route.abort()
            else:
                route.continue_()
        context.route("**/*", guard)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url + "/analyses")
        page.wait_for_load_state("networkidle")
        # A first opening may still be refreshing; search must reach All.
        page.get_by_label("Search analyses").fill("USD investment grade")
        page.get_by_role("link", name="USD investment grade", exact=True).click()
        page.wait_for_selector("#plot .main-svg")
        expect(page.get_by_role("combobox", name="Display range")).to_have_value("3")
        page.get_by_role("combobox", name="Reference history").select_option("1")
        page.wait_for_selector("#plot .main-svg")
        expect(page.get_by_role("combobox", name="Display range")).to_have_value("3")
        page.get_by_role("link", name="Analyses", exact=True).click()
        expect(page.get_by_label("Search analyses")).to_have_value("USD investment grade")
        expect(page.get_by_role("button", name="All", exact=True)).to_have_attribute("aria-pressed", "true")
        page.get_by_role("link", name="USD investment grade", exact=True).click()
        page.wait_for_selector("#plot .main-svg")
        page.get_by_role("combobox", name="Reference history").select_option("1")
        page.wait_for_selector("#plot .main-svg")
        page.get_by_role("button", name="Save to Idea", exact=True).focus()
        page.keyboard.press("Enter")
        page.get_by_label("Title", exact=True).fill(idea_title)
        bounds = page.locator("#plot").bounding_box(), page.locator("#save-panel").bounding_box()
        assert bounds[0]["x"] + bounds[0]["width"] <= bounds[1]["x"]
        page.screenshot(path=str(output / "save-desktop.png"), full_page=True)
        page.get_by_role("button", name="Save chart", exact=True).click()
        page.wait_for_url("**/ideas/*")
        page.wait_for_selector(".saved-plot .main-svg")
        idea_url = page.url
        idea_id = idea_url.rsplit("/", 1)[1]
        data = context.request.get(url + "/api/ideas/" + idea_id).json()
        first = data["idea"]["charts"][0]
        snapshot = data["snapshots"][first["id"]]
        assert snapshot["evaluation"]["definition"]["settings"]["history_years"] == 1
        assert snapshot["display"]["years"] == 3
        original_image = context.request.get(url + f"/api/ideas/{idea_id}/snapshots/{snapshot['id']}/image").body()
        (output / "captured.png").write_bytes(original_image)
        assert hashlib.sha256(original_image).hexdigest() == snapshot["image_sha256"]
        page.locator(".saved-chart").get_by_role("button", name="Add note", exact=True).click()
        page.locator(".saved-chart textarea").fill("First chart note")
        page.locator(".saved-chart").get_by_role("button", name="Save changes").click()
        expect(page.locator(".saved-chart .prose")).to_have_text("First chart note")
        annotation = page.locator(".saved-chart .chart-note")
        annotation.get_by_role("button", name="Edit", exact=True).click()
        annotation.get_by_label("Note text").fill("Edited chart note")
        annotation.get_by_role("button", name="Save changes").click()
        expect(annotation.locator(".prose")).to_have_text("Edited chart note")
        annotation.get_by_role("button", name="Delete", exact=True).click()
        expect(annotation.locator(".prose")).to_have_count(0)
        annotation.get_by_role("button", name="Add note", exact=True).click()
        annotation.get_by_label("Note text").fill("First chart note")
        annotation.get_by_role("button", name="Save changes").click()
        expect(annotation.locator(".prose")).to_have_text("First chart note")
        page.get_by_role("link", name="Add another chart").click()
        page.get_by_role("link", name="USD investment grade", exact=True).click()
        page.wait_for_selector("#plot .main-svg")
        page.get_by_role("button", name="Save to Idea", exact=True).click()
        page.get_by_label("Chart note (optional)").fill("Second chart note")
        page.get_by_role("button", name="Save chart", exact=True).click()
        page.wait_for_url(idea_url)
        expect(page.locator(".saved-chart")).to_have_count(2)
        expect(page.locator(".saved-chart .prose")).to_have_text(["First chart note", "Second chart note"])
        for text in ("First dated note", "Second dated note"):
            page.locator("summary", has_text="Add Idea note").click()
            form = page.locator('[data-form="add-idea-note"]')
            form.get_by_label("Note text").fill(text)
            form.get_by_role("button", name="Save note").click()
            expect(page.locator("p.prose", has_text=text)).to_be_visible()
        expect(page.locator(".note-actions time")).to_have_count(2)
        note = page.locator(".note-actions").first
        before = note.locator("time").inner_text()
        note.locator("summary").click()
        note.get_by_label("Note text").fill("Edited dated note")
        note.get_by_role("button", name="Save changes").click()
        expect(page.locator("p.prose", has_text="Edited dated note")).to_be_visible()
        assert page.locator(".note-actions time").first.inner_text() == before
        page.locator(".note-actions").last.get_by_role("button", name="Delete", exact=True).click()
        expect(page.locator(".note-actions time")).to_have_count(1)
        page.get_by_role("button", name="Shortlist", exact=True).click()
        expect(page.get_by_role("button", name="Remove from shortlist")).to_be_visible()
        page.get_by_role("button", name="Archive", exact=True).click()
        expect(page.get_by_role("button", name="Restore", exact=True)).to_be_visible()
        page.get_by_role("link", name="Add another chart").click()
        page.get_by_role("link", name="USD investment grade", exact=True).click()
        page.wait_for_selector("#plot .main-svg")
        page.get_by_role("button", name="Save to Idea", exact=True).click()
        expect(page.get_by_label("Destination", exact=True)).to_have_value(idea_id)
        page.goto(idea_url)
        expect(page.get_by_role("button", name="Restore", exact=True)).to_be_visible()
        page.get_by_role("link", name="Ideas", exact=True).click()
        page.get_by_role("button", name="Archived", exact=True).click()
        page.get_by_label("Search Ideas").fill(idea_title)
        page.get_by_role("link", name=idea_title).click()
        page.get_by_role("button", name="Restore", exact=True).click()
        expect(page.get_by_role("button", name="Remove from shortlist")).to_be_visible()
        card = page.locator(".saved-chart").first
        with page.expect_download() as downloading:
            card.get_by_role("button", name="Download chart", exact=True).click()
        saved_path = output / "saved-export.png"
        downloading.value.save_as(str(saved_path))
        assert saved_path.read_bytes() == original_image
        card.get_by_role("button", name="Latest data", exact=True).click()
        page.wait_for_selector('[id^="latest-"] .main-svg')
        with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/export")) as capture:
            card.get_by_role("button", name="Copy data", exact=True).click()
        expect(card.get_by_role("button", name="Copy data", exact=True)).to_be_enabled()
        expect(page.locator("#message")).to_contain_text("Data copied")
        copied = page.evaluate("navigator.clipboard.readText()")
        assert copied.startswith("Chart date\tCalculated bp\tUSD investment grade (bp)\tSource date\n")
        assert len(copied.splitlines()) > 30
        capture_id = capture.value.headers["x-snapshot-id"]
        assert capture.value.request.post_data_json["mode"] == "latest"
        assert capture.value.request.post_data_json["display"] == snapshot["display"]
        captured_image_url = url + f"/api/ideas/{idea_id}/snapshots/{capture_id}/image"
        captured_png = base64.b64decode(capture.value.request.post_data_json["image"].split(",", 1)[1])
        assert context.request.get(captured_image_url).body() == captured_png
        assert context.request.get(url + f"/api/ideas/{idea_id}/snapshots/{snapshot['id']}/image").body() == original_image
        page.reload()
        page.wait_for_selector(".saved-plot .main-svg")
        assert context.request.get(captured_image_url).body() == captured_png
        card.get_by_role("button", name="Latest data", exact=True).click()
        page.wait_for_selector('[id^="latest-"] .main-svg')
        with page.expect_download() as downloading:
            card.get_by_role("button", name="Download chart", exact=True).click()
        downloading.value.save_as(str(output / "latest-export.png"))
        # Force clipboard denial; the captured PNG must still be downloadable.
        page.evaluate("() => { navigator.clipboard.write = async () => { throw new Error('Denied by test'); }; }")
        with page.expect_download():
            card.get_by_role("button", name="Copy chart", exact=True).click()
        expect(page.get_by_text("Clipboard unavailable. Chart downloaded instead.")).to_be_visible()
        card.get_by_role("button", name="Remove chart", exact=True).click()
        expect(page.locator(".saved-chart")).to_have_count(1)
        expect(page.locator(".saved-chart .prose")).to_have_text("Second chart note")
        page.screenshot(path=str(output / "idea-desktop.png"), full_page=True)
        # Library dependency protection and inline creation preserve the draft.
        page.get_by_role("link", name="Library", exact=True).click()
        page.get_by_role("button", name="Data series", exact=True).click()
        row = page.locator("tr", has=page.get_by_text("USD investment grade", exact=True))
        row.get_by_role("button", name="Delete", exact=True).click()
        expect(page.locator("#message")).to_contain_text("Used by")
        page.get_by_role("button", name="Analyses", exact=True).click()
        page.get_by_role("button", name="Add analysis", exact=True).click()
        draft_name = "Draft kept across inline series " + uuid4().hex[:8]
        page.get_by_label("Name", exact=True).fill(draft_name)
        page.get_by_role("button", name="Add missing data series").click()
        page.get_by_role("combobox", name="Source", exact=True).select_option("bloomberg")
        for label, value in [("Name", "Extra catalogue series"), ("Symbol / ticker", "SPX Index"),
                             ("Field", "PX_LAST")]:
            page.get_by_label(label, exact=True).fill(value)
        page.get_by_role("button", name="Save data series", exact=True).click()
        expect(page.get_by_label("Name", exact=True)).to_have_value(draft_name)
        page.get_by_role("button", name="Save analysis", exact=True).click()
        expect(page.get_by_text(draft_name, exact=True)).to_be_visible()
        # Editing fractional ratio thresholds must remain a usable CRUD action.
        ratio_row=page.locator("tr",has=page.get_by_text("EUR IG / GBP IG",exact=True))
        ratio_row.get_by_role("button",name="Edit",exact=True).click()
        page.get_by_role("button",name="Save analysis",exact=True).click()
        expect(page.get_by_text("EUR IG / GBP IG",exact=True)).to_be_visible()
        # User/provider metadata must remain text in metrics and saved evidence.
        unit = '<img data-unit-injection src=x onerror="window.unitInjected=true">'
        created = context.request.post(url+"/api/library/series",data={"name":"Metadata escaping example", "source":"Synthetic demo", "instrument":"usd-ig", "field":"spread", "unit":unit, "currency":"EUR", "basis":{"label":"Native", "currency":"EUR", "reference_curve":"ExportCurveCheck", "adjustment":"None"}}).json()
        analysis=context.request.post(url+"/api/library/analyses",data={"name":"Metadata escaping analysis", "calculation":"level", "series_ids":[created["id"]]}).json()
        page.goto(url+"/analyses/"+analysis["id"])
        page.wait_for_selector("#plot .main-svg")
        assert page.locator('img[data-unit-injection]').count()==0 and not page.evaluate("window.unitInjected || false")
        assert page.evaluate("number(1,'<b>unit</b>')")=="1.00 &lt;b&gt;unit&lt;/b&gt;"
        disclosure=page.locator(".evidence-details > details")
        disclosure.locator("summary").click()
        expect(disclosure).to_contain_text("ExportCurveCheck")
        expect(disclosure.locator("dd").filter(has_text="EUR").first).to_be_visible()
        assert page.evaluate("document.querySelector('#plot').layout.xaxis.fixedrange === true && document.querySelector('#plot').layout.legend.itemclick === false")
        # Narrow layouts keep actions and chart labels available, including save.
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(url + "/analyses/usd-ig")
        page.wait_for_selector("#plot .main-svg")
        page.get_by_role("button", name="Save to Idea", exact=True).click()
        page.locator("#save-panel").wait_for(state="visible")
        chart_box, save_box = page.locator("#plot").bounding_box(), page.locator("#save-panel").bounding_box()
        assert save_box["y"] >= chart_box["y"] + chart_box["height"]
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(output / "save-mobile.png"), full_page=True)
        page.goto(idea_url)
        page.wait_for_selector(".saved-chart")
        page.screenshot(path=str(output / "idea-mobile.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        # Empty results are honest; no filler rows.
        page.goto(url + "/analyses")
        page.get_by_label("Search analyses").fill("no-such-analysis")
        expect(page.get_by_text("No matching analyses. Choose All, clear search or broaden the type filter.")).to_be_visible()
        assert not errors and not external, {"errors": errors, "external": external}
        evidence = {"idea_id": idea_id, "initial_snapshot_id": snapshot["id"], "initial_image_sha256": snapshot["image_sha256"],
                    "script_errors": errors, "external_requests": external, "checks": "search/settings/save, duplicate charts, notes, archive/restore, PNG saved/latest/copy fallback, Library dependencies/inline series, keyboard save, desktop/mobile and empty results"}
        (output / "browser-result.json").write_text(json.dumps(evidence, indent=2))
        browser.close()
        return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8879")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(journey(args.url, args.output), indent=2))
