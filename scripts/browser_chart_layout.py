"""Read-only browser regression for titles and legends, including PNG capture."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def check_layout(bounds: dict) -> None:
    title, legend = bounds["title"], bounds["legend"]
    assert title and legend, "Expected chart title and legend"
    assert title["bottom"] + 8 <= legend["top"], bounds
    assert legend["bottom"] <= bounds["plot_top"], bounds


def journey(url: str, output: Path) -> list[dict]:
    output.mkdir(parents=True, exist_ok=True)
    results = []
    geometry = """element => {
      const box = selector => {
        const r = element.querySelector(selector)?.getBoundingClientRect();
        return r ? {top:r.top, bottom:r.bottom, left:r.left, right:r.right} : null;
      };
      return {title:box('.gtitle'), legend:box('.legend'),
        plot_top:element.querySelector('.nsewdrag').getBoundingClientRect().top};
    }"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(accept_downloads=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        for width, height in [(1350, 986), (390, 844)]:
            page.set_viewport_size({"width": width, "height": height})
            for analysis, view in [("usd-ig", "underlying"), ("eur-gbp", "underlying"), ("ig-rates", "scatter")]:
                page.goto(f"{url}/analyses/{analysis}")
                page.wait_for_load_state("networkidle")
                if analysis == "usd-ig":
                    # Reproduce the exact controls in the owner's report.
                    page.get_by_role("combobox", name="Display range").select_option("5")
                    page.get_by_role("combobox", name="Reference history").select_option("1")
                    page.wait_for_load_state("networkidle")
                    page.get_by_role("combobox", name="Move horizon").select_option("month")
                    page.wait_for_load_state("networkidle")
                page.get_by_role("combobox", name="Chart view").select_option(view)
                page.wait_for_function("document.querySelector('#plot')?.layout?.showlegend === true")
                # Finish SVG rendering before measuring the visible elements.
                page.locator("#plot .legend").wait_for()
                bounds = page.locator("#plot").evaluate(geometry)
                check_layout(bounds)
                name = f"{analysis}-{view}-{width}"
                page.screenshot(path=str(output / f"{name}.png"), full_page=True)
                # Inspect the same offscreen figure that supplies the real PNG.
                page.evaluate("""() => {
                  const measure = """ + geometry + """;
                  const toImage = Plotly.toImage;
                  Plotly.toImage = async function(element, options) {
                    window.exportBounds = measure(element);
                    return toImage.call(this, element, options);
                  };
                }""")
                with page.expect_download() as download:
                    page.get_by_role("button", name="Download chart", exact=True).click()
                download.value.save_as(str(output / f"{name}-export.png"))
                export_bounds = page.evaluate("window.exportBounds")
                check_layout(export_bounds)
                results.append({"case": name, "chart": bounds, "export": export_bounds})
        assert not errors, errors
        browser.close()
    (output / "result.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(journey(args.url, args.output), indent=2))
