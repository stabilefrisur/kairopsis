"""Browser acceptance against scripts/run_csv_demo.py; no saved user edits."""
import argparse
from pathlib import Path
from time import perf_counter

from playwright.sync_api import sync_playwright


def run(url: str, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1569, 'height': 1035})
        errors, requests = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda r: requests.append(r.post_data_json) if r.url.endswith('/api/explore/preview') else None)
        page.goto(url + '/explore', wait_until='networkidle')
        page.wait_for_function("document.querySelectorAll('.explore-library-row').length === 74")
        assert page.locator('.explore-library-row').count() == 74
        assert page.locator('[name="workspace_as_of"]').input_value() == '2026-09-30'

        def current():
            page.wait_for_function("window.exploreWorkspace.status==='current' && !window.exploreWorkspace.previewInFlight", timeout=60000)

        def add(key):
            page.locator(f'[data-explore="add-item"][data-id="{key}"]').click()
            current()

        def chart(family):
            page.locator('[name="new_family"]').select_option(family)
            page.locator('[data-explore="add-view"]').click()
            current()

        def retrievals():
            return page.evaluate("Object.values(window.exploreWorkspace.results.get(window.exploreWorkspace.selected).input_evidence.bindings).map(x=>x.retrievals)")

        add('usd_ig_oas_bp')
        add('usd_hy_oas_bp')
        assert page.evaluate('window.exploreWorkspace.workspace.views.length') == 0
        chart('history')
        assert page.evaluate("[...window.exploreWorkspace.results.values()][0].statistics.traces.length") == 2
        before = retrievals()
        start = perf_counter()
        page.locator('#explore-view-form [name="family"]').select_option('distribution')
        current()
        assert retrievals() == before, 'Chart edit must reuse original retrievals'
        print(f'PASS: automatic initial loading and cached chart switch ({perf_counter()-start:.2f}s including debounce/render)')
        assert all(not request['refresh_data'] for request in requests)
        page.get_by_role('button', name='Refresh data', exact=True).click()
        current()
        assert requests[-1]['refresh_data'] is True
        assert retrievals() != before
        add('usd_ig_duration_years')
        add('usd_hy_duration_years')
        chart('scatter')
        rows = page.evaluate('window.exploreWorkspace.results.get(window.exploreWorkspace.selected).rows')
        assert len(rows) == 2
        assert {r['symbol'] for r in rows} == {'usd_ig', 'usd_hy'}
        assert all(set(r['values']) == {'oas_bp', 'spread_duration_years'} for r in rows)
        page.locator('[data-explore="new-analysis"]').click()
        form = page.locator('#explore-analysis-form')
        form.locator('[name="name"]').fill('CSV weekly IG changes')
        form.locator('[name="left"]').select_option('usd_ig_oas_bp')
        form.locator('[name="measure"]').select_option('change')
        form.locator('[name="horizon"]').select_option('week')
        page.locator('[data-explore="apply-analysis"]').click()
        current()
        chart('history')
        ids = page.evaluate('window.exploreWorkspace.workspace.collection.filter(i=>i.kind==="series").map(i=>i.id)')
        for key in ids:
            page.locator(f'#explore-view-form [name="measures"][value="{key}"]').uncheck()
        current()
        assert page.evaluate('window.exploreWorkspace.results.get(window.exploreWorkspace.selected).rows.some(r=>Object.values(r.values).some(v=>v!==null))')
        print('PASS: CSV symbol/field grouping, explicit refresh, local weekly-change Analysis')
        page.goto(url + '/explore/csv-demo', wait_until='networkidle')
        current()
        page.screenshot(path=str(output / 'csv-workspace.png'), full_page=True)
        page.set_viewport_size({'width': 1180, 'height': 900})
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
        page.screenshot(path=str(output / 'csv-laptop.png'), full_page=True)
        page.goto(url + '/library', wait_until='networkidle')
        page.get_by_role('button', name='Data series', exact=True).click()
        assert page.locator('tbody tr').count() == 74
        page.screenshot(path=str(output / 'csv-library.png'))
        assert not errors, errors
        print('PASS: all 74 Library series; desktop/laptop layout; no browser errors')
        browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, default=Path('/tmp/kairopsis-csv-review'))
    args = parser.parse_args()
    run(args.url.rstrip('/'), args.output)
