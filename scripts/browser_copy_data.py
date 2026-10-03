"""Read-only clipboard checks against an existing Idea, with HTTP fixture responses."""
import argparse
import copy
import csv
import io
import json
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def journey(url: str, idea_id: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        endpoint = f"{url}/api/ideas/{idea_id}"
        original = context.request.get(endpoint).body()
        fixture = json.loads(original)
        entry = fixture["idea"]["charts"][0]["id"]
        snapshot = fixture["snapshots"][entry]
        evaluation = snapshot["evaluation"]
        evaluation["points"] = [
            {"date": (date(2026, 8, 31) + timedelta(days=i)).isoformat(),
             "value": 10.123456789 if i == 0 else None if i == 1 else 12.5,
             "inputs": [10.123456789 if i == 0 else None if i == 1 else 12.5],
             "observed_on": ["2026-08-30" if i == 0 else None if i == 1 else "2026-09-30"]}
            for i in range(31)
        ]
        # A point outside the displayed period must not be copied.
        evaluation["points"].insert(0, {"date": "2000-01-01", "value": 999,
                                       "inputs": [999], "observed_on": ["2000-01-01"]})
        latest = copy.deepcopy(evaluation)
        latest["id"] = "clipboard-latest"
        latest["points"] = [{"date": "2026-09-30", "value": 88.7654321,
                             "inputs": [88.7654321], "observed_on": ["2026-09-29"]}]
        pair_entry = fixture["idea"]["charts"][1]["id"]
        pair = fixture["snapshots"][pair_entry]["evaluation"]
        pair["definition"]["inputs"][0]["name"] = '=Agency\tMBS\n"demo"'
        pair["points"] = [{"date": "2026-09-30", "value": 40.375,
                           "inputs": [30.125, -10.25], "observed_on": ["2026-09-29", "2026-09-30"]}]
        page.route(endpoint, lambda route: route.fulfill(json=fixture))
        page.route(f"{endpoint}/charts/{entry}/latest",
                   lambda route: route.fulfill(json={"evaluation": latest}))
        captured = []
        failed_capture = [False]
        def capture(route):
            if failed_capture[0]:
                route.fulfill(status=500, json={"detail": "Snapshot capture failed"})
            else:
                captured.append(route.request.post_data_json)
                route.fulfill(body=b"captured-image", content_type="image/png")
        page.route(f"{endpoint}/charts/*/export", capture)
        for width in [1350, 390]:
            page.set_viewport_size({"width": width, "height": 986})
            page.goto(f"{url}/ideas/{idea_id}")
            page.wait_for_load_state("networkidle")
            card = page.locator(f"#chart-{entry}")
            card.locator(".plot .main-svg").first.wait_for()
            button = card.get_by_role("button", name="Copy data", exact=True)
            expect(button).to_be_visible(timeout=2000)
            button.click()
            expect(button).to_be_enabled()
            expect(page.locator("#message")).to_contain_text("Data copied")
            assert captured[-1]["evaluation_id"] == evaluation["id"]
            assert captured[-1]["mode"] == "saved"
            assert captured[-1]["display"] == snapshot["display"]
            text = page.evaluate("navigator.clipboard.readText()")
            rows = list(csv.reader(io.StringIO(text), delimiter="\t"))
            assert rows[0] == ["Chart date", "Calculated bp", "USD investment grade (bp)", "Source date"]
            assert len(rows) == 32, len(rows)
            assert rows[1] == ["2026-08-31", "10.123456789", "10.123456789", "2026-08-30"]
            assert rows[2] == ["2026-09-01", "", "", ""]
            assert rows[-1] == ["2026-09-30", "12.5", "12.5", "2026-09-30"]
            card.get_by_role("button", name="Latest data", exact=True).click()
            expect(card.get_by_role("button", name="Latest data", exact=True)).to_have_attribute("aria-pressed", "true")
            button.click()
            expect(button).to_be_enabled()
            expect(page.locator("#message")).to_contain_text("Data copied")
            rows = list(csv.reader(io.StringIO(page.evaluate("navigator.clipboard.readText()")), delimiter="\t"))
            assert captured[-1]["evaluation_id"] == "clipboard-latest"
            assert captured[-1]["mode"] == "latest"
            assert rows[1:] == [["2026-09-30", "88.7654321", "88.7654321", "2026-09-29"]]
            card.get_by_role("button", name="Saved evidence", exact=True).click()
            button.click()
            expect(button).to_be_enabled()
            expect(page.locator("#message")).to_contain_text("Data copied")
            assert page.evaluate("navigator.clipboard.readText()") == text
            pair_card = page.locator(f"#chart-{pair_entry}")
            pair_card.get_by_role("button", name="Copy data", exact=True).click()
            expect(pair_card.get_by_role("button", name="Copy data", exact=True)).to_be_enabled()
            expect(page.locator("#message")).to_contain_text("Data copied")
            rows = list(csv.reader(io.StringIO(page.evaluate("navigator.clipboard.readText()")), delimiter="\t"))
            assert rows[0] == ["Chart date", "Calculated bp", '\'=Agency\tMBS\n"demo" (bp)',
                               "Source date", "USD investment grade (bp)", "Source date"]
            assert rows[1] == ["2026-09-30", "40.375", "30.125", "2026-09-29", "-10.25", "2026-09-30"]
            # A failed durable capture must leave the clipboard untouched.
            page.evaluate("navigator.clipboard.writeText('Preserved clipboard')")
            failed_capture[0] = True
            button.click()
            expect(button).to_be_enabled()
            expect(page.locator("#message")).to_contain_text("Snapshot capture failed")
            assert page.evaluate("navigator.clipboard.readText()") == "Preserved clipboard"
            failed_capture[0] = False
            # Clipboard denial leaves the same usable data available as a TSV file.
            page.evaluate("Object.defineProperty(navigator.clipboard, 'writeText', {value: async () => {throw Error('Denied')}})")
            with page.expect_download() as event:
                button.click()
            expect(button).to_be_enabled()
            download = event.value
            assert download.suggested_filename == "kairopsis-data.tsv"
            path = output / f"fallback-{width}.tsv"
            download.save_as(path)
            assert path.read_text() == text
            expect(page.locator("#message")).to_contain_text("Data downloaded instead")
            page.screenshot(path=str(output / f"copy-data-{width}.png"), full_page=True)
        assert context.request.get(endpoint).body() == original
        assert not errors, errors
        browser.close()
    print(json.dumps({"passed": True, "widths": [1350, 390], "idea_unchanged": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--idea-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    journey(args.url, args.idea_id, args.output)
