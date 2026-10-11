"""Browser acceptance for the unified editor; use an isolated CSV demo workspace."""
import argparse
from pathlib import Path
from time import monotonic
from playwright.sync_api import sync_playwright, expect


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://127.0.0.1:8770')
parser.add_argument('--output', type=Path, default=Path('.scratch/editor-review'))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width':1569, 'height':1035})
    page.set_default_timeout(30000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('dialog', lambda dialog: dialog.accept())
    def ready():
        expect(page.locator('#investigation-status')).to_have_text('Chart up to date.')
    def value(expression):
        return page.evaluate(expression)
    page.goto(args.url + '/library')
    page.wait_for_load_state('networkidle')
    page.locator('[data-action="library-new"]').click()
    expect(page).to_have_url(args.url + '/analyses/new')
    ready()
    assert value('state.analysisDraft.settings.reference_mode') == 'rolling'
    page.locator('[name=name]').fill('Reference editor acceptance')
    page.locator('[name=economic_rationale]').fill('Compare credit compensation with its own history.')
    page.locator('[name=standardization]').select_option('zscore')
    ready()
    expect(page.locator('#analysis-save-status')).to_have_text('Unsaved changes')
    assert value('state.evaluation.points.at(-1).reference_estimate.sample_count') > 60
    rolling = value('state.evaluation.points.slice(-300).map(p => p.value)')
    page.locator('[name=reference_mode]').select_option('current')
    ready()
    assert rolling != value('state.evaluation.points.slice(-300).map(p => p.value)')
    page.locator('[name=reference_mode]').select_option('fixed')
    page.locator('[name=reference_start]').fill('2018-01-01')
    page.locator('[name=reference_end]').fill('2020-12-31')
    page.locator('[name=reference_end]').press('Tab')
    ready()
    assert value('state.evaluation.standardization_estimate.start') == '2018-01-01'
    assert value('state.evaluation.standardization_estimate.end') == '2020-12-31'
    page.locator('[data-action=analysis-save]').click()
    expect(page.locator('#analysis-save-status')).to_have_text('Saved')
    ready()
    url = page.url
    saved_id = url.rsplit('/', 1)[1]
    revision = value('state.savedAnalysis.revision')
    # Discard returns to the saved definition, including name and rationale.
    page.locator('[name=name]').fill('Discard this name')
    page.locator('[name=reference_mode]').select_option('rolling')
    ready()
    page.locator('[data-action=analysis-discard]').click()
    ready()
    expect(page.locator('[name=name]')).to_have_value('Reference editor acceptance')
    expect(page.locator('[name=reference_mode]')).to_have_value('fixed')
    # The old Library URL opens the identical editor.
    page.goto(args.url + '/library?edit=' + saved_id)
    ready()
    expect(page).to_have_url(url)
    expect(page.locator('[name=economic_rationale]')).to_have_value('Compare credit compensation with its own history.')
    # Direct save failure retains edits and enables retry.
    page.route('**/api/library/analyses/bundle', lambda route: route.fulfill(status=409,
        content_type='application/json', body='{"detail":"Definition changed in another editor"}'))
    page.locator('[name=name]').fill('Preserved after conflict')
    ready()
    page.locator('[data-action=analysis-save]').click()
    expect(page.locator('#message')).to_contain_text('Your edits are still here')
    expect(page.locator('[name=name]')).to_have_value('Preserved after conflict')
    expect(page.locator('#analysis-save-status')).to_have_text('Unsaved changes')
    assert value('state.savedAnalysis.revision') == revision
    page.unroute('**/api/library/analyses/bundle')
    page.locator('[data-action=analysis-save]').click()
    expect(page.locator('#analysis-save-status')).to_have_text('Saved')
    ready()
    # Failed preview keeps the old chart visibly qualified; Retry recovers.
    page.route('**/api/library/analyses/preview', lambda route: route.fulfill(status=503,
        content_type='application/json', body='{"detail":"Temporary data failure"}'))
    page.locator('[name=reference_mode]').select_option('rolling')
    expect(page.locator('#investigation-status')).to_contain_text('Update failed')
    expect(page.locator('[data-action=open-save]')).to_be_disabled()
    page.unroute('**/api/library/analyses/preview')
    page.locator('[data-action=investigation-preview]').click()
    ready()
    # An older response cannot overwrite the latest selection.
    delayed = []
    def delay_first(route):
        if not delayed:
            response = route.fetch()
            delayed.append((route, response))
        else:
            route.continue_()
    page.route('**/api/library/analyses/preview', delay_first)
    page.locator('[name=history]').select_option('1')
    for _ in range(60):
        if delayed: break
        page.wait_for_timeout(100)
    assert delayed
    page.locator('[name=history]').select_option('5')
    ready()
    delayed[0][0].fulfill(response=delayed[0][1])
    page.wait_for_timeout(250)
    assert value('state.evaluation.definition.settings.history_years') == 5
    page.unroute('**/api/library/analyses/preview')
    # Shared inline-series edits save atomically with the Analysis.
    page.locator('[data-action=stage-series]').first.click()
    expect(page.locator('#library-series-dialog')).to_be_visible()
    page.locator('#staged-series-form [name=name]').fill('USD IG OAS review label')
    page.locator('#staged-series-form [type=submit]').click()
    ready()
    expect(page.locator('#analysis-series-summary')).to_contain_text('USD IG OAS review label')
    page.locator('[data-action=analysis-save]').click()
    expect(page.locator('#analysis-save-status')).to_have_text('Saved')
    ready()
    # Capturing a draft into an Idea does not overwrite the saved Analysis.
    page.locator('[name=name]').fill('Captured draft only')
    ready()
    page.locator('[data-action=open-save]').click()
    page.locator('#save-form [name=title]').fill('Editor evidence acceptance')
    page.locator('#save-form [type=submit]').click()
    page.wait_for_url('**/ideas/*')
    library = page.request.get(args.url + '/api/library').json()
    assert next(a for a in library['analyses'] if a['id'] == saved_id)['name'] == 'Preserved after conflict'
    page.goto(url)
    ready()
    # Regression fitting has its own timing, independent of output reference.
    page.goto(args.url + '/analyses/new')
    ready()
    page.locator('[name=name]').fill('Rolling regression acceptance')
    page.locator('[name=analysis_type]').select_option('pair')
    page.locator('[name=left]').select_option('usd_hy_oas_bp')
    page.locator('[name=right]').select_option('usd_ig_oas_bp')
    started = monotonic()
    page.locator('[name=calculation]').select_option('regression')
    ready()
    print(f'Rolling regression chart ready in {monotonic()-started:.2f}s', flush=True)
    expect(page.locator('[name=fit_mode]')).to_have_value('rolling')
    expect(page.locator('[name=reference_mode]')).not_to_be_visible()
    rolling = value('state.evaluation.points.slice(-300).map(p => p.value)')
    assert value('state.evaluation.points.at(-1).fit_estimate.end < state.evaluation.observation_date')
    page.locator('[name=fit_mode]').select_option('current')
    ready()
    assert rolling != value('state.evaluation.points.slice(-300).map(p => p.value)')
    page.locator('[name=standardization]').select_option('zscore')
    ready()
    expect(page.locator('.reference-help')).to_contain_text('current fit throughout')
    page.locator('[name=fit_mode]').select_option('rolling')
    ready()
    expect(page.locator('.reference-help')).not_to_contain_text('current fit throughout')
    assert value('state.evaluation.points.at(-1).reference_estimate !== null')
    page.locator('[name=fit]').select_option('all')
    ready()
    expect(page.locator('.fit-help')).to_contain_text('expands over time')
    page.locator('[name=fit]').select_option('3')
    ready()
    page.locator('[data-action=analysis-save]').click()
    expect(page.locator('#analysis-save-status')).to_have_text('Saved')
    ready()
    page.reload()
    ready()
    expect(page.locator('[name=fit_mode]')).to_have_value('rolling')
    page.locator('[data-display=view]').select_option('scatter')
    page.wait_for_function('document.querySelector("#plot").data.some(t => t.name === "Latest fit")')
    assert value('document.querySelector("#plot").data[0].x.length > 0')
    page.locator('[data-display=view]').select_option('analysis')
    page.wait_for_function('document.querySelector("#plot").data.length === 1')
    # Copied data include the fitted evidence for each displayed residual.
    copied = page.evaluate('''async () => {
        let text;
        navigator.clipboard.writeText = async value => { text = value; };
        await copyData(document.querySelector('#plot'));
        return text;
    }''')
    assert 'Fit intercept\tFit slope\tFit R²\tFit count\tFit start\tFit end' in copied
    page.evaluate('scrollTo(0, 0)')
    page.screenshot(path=str(args.output/'desktop.png'), full_page=True)
    for width, height in [(1200, 850), (760, 1000)]:
        page.set_viewport_size({'width':width, 'height':height})
        page.wait_for_function('document.documentElement.scrollWidth <= innerWidth')
        assert value('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(args.output/f'viewport-{width}.png'), full_page=True)
    assert not errors, errors
    print('PASS: shared editor, three references, rolling/As-of regression, automatic updates, save/discard, conflict, retry, response ordering, staged series, independent capture, copied fit evidence, layouts; no JS errors.')
    browser.close()
