"""The demo uses Library, Metapyle CSV retrieval and the production engine."""
from pathlib import Path
import runpy

from fastapi.testclient import TestClient
import pytest

from kairopsis.models import AnalysisDefinition, AnalysisSettings, SeriesBinding


prepare = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts' / 'run_csv_demo.py'))['prepare']


def test_csv_import_dates_grouping_and_actual_analysis(tmp_path):
    app = prepare(tmp_path)
    with TestClient(app) as http:
        library = http.get('/api/library').json()
        assert len(library['series']) == 74 and library['analyses'] == []
        assert all(s['source'] == 'localfile' and s['field'] is None for s in library['series'])
        series = {s['id']: s for s in library['series']}
        assert series['usd_ig_oas_bp']['research_symbol'] == series['usd_ig_duration_years']['research_symbol'] == 'usd_ig'
        assert series['usd_ig_duration_years']['research_field'] == 'spread_duration_years'
        assert all(s['localfile_date_role'] == 'observation' for s in series.values())
        raw = http.post('/api/library/series/preview', json={'series': series['edge_gapped_ig_bp'], 'period': 3})
        assert raw.status_code == 200, raw.text
        data = raw.json()['data']
        points = data['series'][0]['observations']
        assert data['outcome'] == 'unverified', 'Date declaration is not a claim of market freshness'
        assert all(p['observed_on'] == p['date'] if p['value'] is not None else p['observed_on'] is None for p in points)
        assert all(p['value'] is None for p in points if '2026-08-10' <= p['date'] <= '2026-08-21')
        analysis = AnalysisDefinition(id='csv-weekly', name='CSV weekly spread change', calculation='level',
            series_ids=('usd_ig_oas_bp',), monitored=False,
            economic_rationale='Inspect weekly repricing in the synthetic USD IG spread, measured in bp. Demo mechanics only.',
            settings=AnalysisSettings(calculation_contract='input-pipeline-v2', measure='change', horizon='week'))
        result = http.post('/api/library/analyses/preview', json={'analysis': analysis.model_dump(mode='json'), 'period': 3})
        assert result.status_code == 200, result.text
        evaluation = result.json()
        assert any(p['value'] is not None for p in evaluation['points'])
        # Trace the last weekly change to the actual file, through Metapyle again.
        levels = http.post('/api/library/series/preview', json={'series': series['usd_ig_oas_bp'], 'period': 3}).json()['data']['series'][0]['observations']
        values = {p['date']: p['value'] for p in levels}
        latest = next(p for p in reversed(evaluation['points']) if p['value'] is not None)
        assert latest['date'] == '2026-09-30'
        assert latest['value'] == pytest.approx(values['2026-09-30'] - values['2026-09-23'])
        saved = http.post('/api/library/analyses', json=analysis.model_dump(mode='json'))
        assert saved.status_code == 200 and saved.json()['monitored'] is False
        workspace = http.get('/api/explore/workspaces/csv-demo').json()['workspace']
        assert workspace['as_of'] == '2026-09-30'
        result = http.post('/api/explore/preview', json={'workspace': workspace}).json()
        assert len(result['resolved_results'][1]['rows']) == 6
        assert all(set(row['values']) == {'oas_bp', 'spread_duration_years'} for row in result['resolved_results'][1]['rows'])
    # Rerunning imports preserves saved work instead of resetting Library.
    assert len(prepare(tmp_path).state.research.catalogue.records()['analyses']) == 1


def test_date_declaration_defaults_unknown_and_is_localfile_only():
    binding = SeriesBinding(name='Provider series', source='bloomberg', instrument='X', field='PX_LAST', unit='index', currency='USD')
    assert binding.localfile_date_role == 'unknown'
    with pytest.raises(ValueError, match='localfile'):
        SeriesBinding.model_validate({**binding.model_dump(), 'localfile_date_role': 'observation'})
    with pytest.raises(ValueError, match='both'):
        SeriesBinding.model_validate({**binding.model_dump(), 'research_symbol': 'credit'})
