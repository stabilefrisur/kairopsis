"""Verify dashboard refresh retains the same evidence exposed to screening agents."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def journey(url: str, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 850})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url + "/analyses")
        page.wait_for_load_state("networkidle")
        page.wait_for_function("""async () => {
            const response = await fetch('/api/analyses?scope=all');
            const data = await response.json();
            return !data.refresh.running && !!data.refresh.screening_run_id;
        }""")
        initial = page.request.get(url + "/api/analyses?scope=all").json()
        first_id = initial["refresh"]["screening_run_id"]
        first = page.request.get(url + "/api/screenings/" + first_id).json()
        assert first["status"] == "completed" and first["trigger"] == "daily"
        with page.expect_response(lambda response: urlsplit(response.url).path == "/api/refresh"
                                  and response.request.method == "POST") as refreshed:
            page.get_by_role("button", name="Refresh", exact=True).click()
        response = refreshed.value
        assert response.ok, response.text()
        state = response.json()
        run_id = state["screening_run_id"]
        assert run_id != first_id
        run = page.request.get(url + "/api/screenings/" + run_id).json()
        assert run["status"] == "completed" and run["trigger"] == "manual"
        manifest = run["manifest"]
        assert manifest["universe_count"] == len(initial["rows"])
        for row in manifest["rows"]:
            assert row["evaluation_id"] == state["results"][row["analysis_id"]]
            detail = page.request.get(url + f"/api/screenings/{run_id}/evaluations/{row['evaluation_id']}")
            assert detail.ok and detail.json()["id"] == row["evaluation_id"]
        page.get_by_label("Search analyses").fill("USD investment grade")
        expect(page.get_by_role("link", name="USD investment grade", exact=True)).to_be_visible()
        page.screenshot(path=str(output / "retained-refresh.png"), full_page=True)
        after = page.request.get(url + "/api/analyses?scope=all").json()
        assert after["refresh"]["screening_run_id"] == run_id
        assert not errors, errors
        browser.close()
    return {"daily_run": first_id, "manual_run": run_id, "analyses": manifest["universe_count"],
            "coverage": manifest["coverage"], "console_errors": errors, "passed": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = journey(args.url.rstrip("/"), args.output)
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
