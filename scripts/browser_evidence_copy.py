"""Read-only checks for concise chart footnotes and understandable disclosure."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def journey(url: str, output: Path, idea_id: str | None) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1350, "height": 986})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        original = None
        if idea_id:
            idea = page.request.get(f"{url}/api/ideas/{idea_id}").json()
            snapshot = next(iter(idea["snapshots"].values()))
            image_url = f"{url}/api/ideas/{idea_id}/snapshots/{snapshot['id']}/image"
            original = page.request.get(image_url).body()
        for width in [1350, 390]:
            page.set_viewport_size({"width": width, "height": 986})
            page.goto(f"{url}/analyses/usd-ig")
            page.wait_for_load_state("networkidle")
            footnote = page.locator(".chart-footnote")
            expect(footnote).to_contain_text("Demo data")
            expect(footnote).to_contain_text("Treasury")
            text = footnote.inner_text()
            assert "native" not in text.lower() and "calibration" not in text.lower(), text
            details = page.locator(".evidence-details > details")
            expect(details).not_to_have_attribute("open", "")
            details.locator("summary").click()
            expect(details).to_contain_text("Source observation date")
            expect(details).to_contain_text("Reference history")
            expect(details).to_contain_text("Instrument")
            assert "Native" not in details.inner_text()
            expect(details.locator("dd").filter(has_text="Treasury").first).to_be_visible()
            page.screenshot(path=str(output / f"disclosure-{width}.png"), full_page=True)
            png = page.evaluate("chartPNG(document.querySelector('#plot'))")
            (output / f"export-{width}.png").write_bytes(base64.b64decode(png.split(",", 1)[1]))
            if idea_id:
                page.goto(f"{url}/ideas/{idea_id}")
                page.wait_for_load_state("networkidle")
                page.locator(".saved-plot .main-svg").first.wait_for()
                expect(page.locator(".chart-footnote").first).to_contain_text("Demo data")
                # The owner receives the simplified view without a new observation.
                observed = page.locator(".saved-plot").first.evaluate("el => el.evidence.evaluation.observation_date")
                assert observed == snapshot["evaluation"]["observation_date"]
                expect(page.get_by_role("link", name="Download original saved image", include_hidden=True).first).to_be_attached()
                card = page.locator(".saved-chart").first
                note = card.locator(".chart-note")
                plot_box, note_box, footer_box = (locator.bounding_box() for locator in
                    [card.locator(".plot"), note, card.locator(".evidence-details")])
                assert plot_box["y"] + plot_box["height"] <= note_box["y"] < footer_box["y"]
                expect(card.locator(":scope > footer.chart-source")).to_be_attached()
                assert card.evaluate("el => el.lastElementChild.matches('footer.chart-source')")
                if note.locator(".prose").count():
                    text_box = note.locator(".prose").bounding_box()
                    edit_box = note.get_by_role("button", name="Edit", exact=True).bounding_box()
                    delete_box = note.get_by_role("button", name="Delete", exact=True).bounding_box()
                    assert abs(edit_box["y"] - delete_box["y"]) < 2
                    assert text_box["y"] <= edit_box["y"] < text_box["y"] + 32
                    note.get_by_role("button", name="Edit", exact=True).click()
                    expect(note.get_by_label("Note text")).to_be_visible()
                    note.get_by_label("Note text").fill("Unsaved layout check")
                    for mode in ["Latest data", "Saved evidence"]:
                        card.get_by_role("button", name=mode, exact=True).click()
                        expect(card.get_by_role("button", name=mode, exact=True)).to_have_attribute("aria-pressed", "true")
                        expect(note.get_by_label("Note text")).to_have_value("Unsaved layout check")
                        assert card.evaluate("el => el.lastElementChild.matches('footer.chart-source')")
                    note.get_by_role("button", name="Cancel", exact=True).click()
                    expect(note.get_by_label("Note text")).not_to_be_visible()
                    expect(note.get_by_role("button", name="Edit", exact=True)).to_be_focused()
                page.screenshot(path=str(output / f"saved-{width}.png"), full_page=True)
        if original is not None:
            assert hashlib.sha256(page.request.get(image_url).body()).digest() == hashlib.sha256(original).digest()
        assert not errors, errors
        browser.close()
    print(json.dumps({"passed": True, "widths": [1350, 390], "original_image_unchanged": idea_id is not None}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--idea-id")
    args = parser.parse_args()
    journey(args.url, args.output, args.idea_id)
