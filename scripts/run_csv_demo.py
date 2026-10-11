"""Launch the CSV-backed Explore demo through the normal Metapyle adapter.

Usage: python scripts/run_csv_demo.py --root /absolute/demo-directory --port 8768
Imports all manifest series through Library validation. Existing user edits and
saved evidence survive restarts. Uses a separate live-provider workspace, never
the built-in mock generator. All observations remain explicitly synthetic.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path

from kairopsis.app import create_app
from kairopsis.config import Settings
from kairopsis.exploration_models import CollectionItem, ViewDefinition, WorkspaceDefinition
from kairopsis.models import ComparisonBasis, SeriesBinding


FIXTURE = Path(__file__).resolve().parents[1] / 'tests' / 'fixtures' / 'demo'


def prepare(root: Path, fixture: Path = FIXTURE, port: int = 8768):
    root, fixture = root.resolve(), fixture.resolve()
    manifest = json.loads((fixture / 'manifest.json').read_text())
    csv = fixture / 'market.csv'
    if hashlib.sha256(csv.read_bytes()).hexdigest() != manifest['csv_sha256']:
        raise ValueError('CSV checksum differs from its manifest. Regenerate/review the dataset first.')
    settings = Settings(mode='live', workspace=root / 'workspace', config_dir=root / 'config',
        cache_dir=root / 'cache', log_dir=root / 'logs', port=port,
        data_label=f"CSV demo · Synthetic data · through {manifest['end']}", exploration_as_of=manifest['end'])
    app = create_app(settings)
    catalogue = app.state.research.catalogue
    records = catalogue.records()
    expected_ids = {meta['id'] for meta in manifest['series']}
    if any(s['id'] not in expected_ids or s['source'] != 'localfile' or s['path'] != str(csv) for s in records['series']):
        raise ValueError('Use a separate CSV demo directory; this Library contains other data.')
    existing = {s['id']: s for s in records['series']}
    for meta in manifest['series']:
        if meta['id'] in existing:
            continue  # Restart is not permission to overwrite a user's Library edits.
        description = (f"{meta['description']} Supplied measure: {meta['supplied_measure']}; cadence: {meta['cadence']}. "
            f"CSV manifest SHA-256: {manifest['csv_sha256']}. Generated row dates are observation dates; no forward fill.")
        binding = SeriesBinding(id=meta['id'], name=('[Edge case] ' if meta['role'] == 'edge' else '') + meta['name'],
            source='localfile', instrument=meta['id'], catalog_name=meta['id'], path=str(csv), field=None,
            unit=meta['unit'], currency=meta['currency'], description=description,
            research_symbol=meta.get('symbol'), research_field=meta.get('field'), localfile_date_role='observation',
            basis=ComparisonBasis(label=meta['comparison_basis'], currency=meta['currency'],
                reference_curve=meta['comparison_basis'], adjustment='As supplied in the documented synthetic CSV; no implicit conversion'))
        catalogue.save('series', binding)
    store = app.state.exploration_repository
    try:
        store.get('csv-demo')
    except FileNotFoundError:
        saved = {s['id']: SeriesBinding.model_validate(s) for s in catalogue.records()['series']}
        collection = tuple(CollectionItem(id=key, binding=saved[key], symbol=symbol['symbol'], field=field,
            semantics=saved[key].description or 'Synthetic') for symbol in manifest['symbols']
            for field, key in symbol['fields'].items() if field in ('oas_bp', 'spread_duration_years'))
        spread_ids = tuple(i.id for i in collection if i.field == 'oas_bp')
        views = (
            ViewDefinition(id='credit-history', name='Credit spreads', measures=spread_ids, options={'axes': ['oas_bp']}),
            ViewDefinition(id='credit-scatter', name='Spread and duration', family='scatter', shape='cross_section',
                measures=tuple(i.id for i in collection), options={'axes': ['spread_duration_years', 'oas_bp'],
                    'x': 'spread_duration_years', 'y': 'oas_bp'}, color_by='symbol'))
        store.save(WorkspaceDefinition(id='csv-demo', name='CSV exploration', collection=collection, views=views,
            as_of=date.fromisoformat(manifest['end']), notes='Fabricated CSV data for exploration. All 74 series are available in Library.'), None)
    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, default=FIXTURE)
    parser.add_argument('--port', type=int, default=8768)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    application = prepare(args.root, args.fixture, args.port)
    print(f"CSV Library: {len(application.state.research.catalogue.records()['series'])} series. "
          f"Explore: http://127.0.0.1:{args.port}/explore/csv-demo", flush=True)
    if not args.prepare_only:
        import uvicorn
        uvicorn.run(application, host='127.0.0.1', port=args.port)
