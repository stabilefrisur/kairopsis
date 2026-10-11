"""Check chart-specific dates against the CSV demo without saving workspace edits."""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://127.0.0.1:8768')
parser.add_argument('--output', type=Path, default=Path('.scratch/explore-date-review'))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width':1569, 'height':1035})
    errors, requests = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda r: requests.append(r.post_data_json) if r.url.endswith('/api/explore/preview') else None)
    before = page.request.get(args.url + '/api/library').json()
    page.goto(args.url + '/explore', wait_until='networkidle')
    def value(js):
        return page.evaluate(js)
    def current():
        page.wait_for_function("explore.status === 'current' && !explore.previewInFlight", timeout=60000)
    def choose(name, option):
        page.locator(f'#explore-view-form [name={name}]').select_option(option)
    def fill(name, date):
        field = page.locator(f'[name={name}]')
        field.fill(date)
        field.press('Tab')
    for key in ['usd_ig_oas_bp', 'usd_hy_oas_bp']:
        page.locator(f'[data-explore=add-item][data-id={key}]').click()
        current()
    page.locator('[name=new_family]').select_option('ranking')
    page.locator('[data-explore=add-view]').click()
    current()
    form = page.locator('#explore-view-form')
    expect(form.locator('[name=start]')).to_have_count(0)
    expect(form.locator('[name=end]')).to_have_count(0)
    expect(form.locator('[name=as_of]')).to_have_count(0)
    expect(form.locator('[name=pinned]')).to_have_count(0)
    expect(form.locator('[name=interval_start]')).to_have_count(0)
    expect(form.locator('[name=date_source]')).to_have_value('workspace')
    expect(form.locator('.explore-dates')).to_contain_text('Uses 30 Sept 2026')
    assert value('explore.results.get(explore.selected).rows.length') == 2
    page.screenshot(path=str(args.output/'ranking-level.png'), full_page=True)
    # A requested change needs two dates. No invalid request leaves the browser.
    count = len(requests)
    choose('interval_measure', 'return')
    expect(form.locator('.explore-date-problem')).to_contain_text('Choose a From date')
    page.wait_for_timeout(300)  # Longer than automatic preview debounce.
    assert len(requests) == count
    fill('interval_start', '2026-09-01')
    current()
    rows = value('explore.results.get(explore.selected).rows')
    for row in rows:
        endpoints = row['endpoints']['oas_bp']
        expected = 100*(endpoints['end_value']/endpoints['start_value']-1)
        assert abs(row['values']['oas_bp']-expected) < 1e-9
    page.screenshot(path=str(args.output/'ranking-change.png'), full_page=True)
    choose('interval_measure', 'change')
    current()
    for row in value('explore.results.get(explore.selected).rows'):
        endpoints = row['endpoints']['oas_bp']
        assert abs(row['values']['oas_bp'] - (endpoints['end_value'] - endpoints['start_value'])) < 1e-9
    # One chart can keep its date while the workspace date moves.
    choose('date_source', 'chart')
    current()
    expect(form.locator('[name=chart_date]')).to_have_value('2026-09-30')
    fill('workspace_as_of', '2026-09-29')
    current()
    assert value('explore.results.get(explore.selected).as_of') == '2026-09-30'
    choose('date_source', 'workspace')
    current()
    assert value('explore.results.get(explore.selected).as_of') == '2026-09-29'
    assert value('exploreCurrentView().sample.end') is None
    # Inverted periods remain editable and do not post invalid definitions.
    count = len(requests)
    fill('interval_start', '2026-10-01')
    expect(form.locator('.explore-date-problem')).to_contain_text('on or before')
    page.wait_for_timeout(300)
    assert len(requests) == count
    choose('interval_measure', 'level')
    current()
    assert value('exploreCurrentView().sample.interval_start') is None
    # Missing dates are an explicit bounded choice, never an automatic fill.
    choose('date_source', 'chart')
    fill('chart_date', '2026-09-27')  # Sunday.
    current()
    assert value('explore.results.get(explore.selected).rows.length') == 0
    expect(page.locator('.explore-view .empty')).to_contain_text('27 Sept 2026')
    form.get_by_text('Missing dates', exact=True).click()
    choose('date_policy', 'backward')
    current()
    expect(form.locator('[name=maximum_age_days]')).to_have_value('7')
    assert value('explore.results.get(explore.selected).rows.every(r => r.dates.oas_bp === "2026-09-25")')
    # History shows a period. Changing display zoom keeps the calculation sample.
    choose('family', 'history')
    current()
    expect(form.locator('[name=start]')).to_be_visible()
    expect(form.locator('[name=interval_start]')).to_have_count(0)
    fill('start', '2026-08-01')
    current()
    dates = value('explore.results.get(explore.selected).rows.map(r => r.date)')
    assert dates and min(dates) >= '2026-08-01' and max(dates) <= '2026-09-27'
    form.get_by_text('Zoom chart', exact=True).click()
    fill('display_start', '2026-09-01')
    current()
    assert value('explore.results.get(explore.selected).rows.map(r => r.date)') == dates
    # Existing explicit sample ends stay visible and survive unrelated edits.
    page.evaluate("exploreCurrentView().sample.end = '2026-09-21'; exploreRender()")
    expect(form.locator('[name=chart_date]')).to_have_value('2026-09-21')
    fill('name', 'History with retained end')
    current()
    assert value('exploreCurrentView().sample.end') == '2026-09-21'
    fill('chart_date', '2026-09-22')
    current()
    assert value('exploreCurrentView().as_of') == '2026-09-22'
    assert value('exploreCurrentView().sample.end') is None
    page.screenshot(path=str(args.output/'history.png'), full_page=True)
    assert not value('document.documentElement.scrollWidth > innerWidth')
    assert page.request.get(args.url + '/api/library').json() == before
    assert not errors, errors
    print('PASS: relevant date fields, signed/percentage endpoints, required dates, workspace/custom dates, missing-date policy, history/zoom separation, legacy date preservation; Library unchanged; no JS errors.')
    browser.close()
