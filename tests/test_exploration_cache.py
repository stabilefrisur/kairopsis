"""Workspace edits reuse observations; only refresh and new coverage retrieve."""
from datetime import date

from kairopsis.exploration_models import ViewDefinition
from test_exploration import SuppliedData, workspace
from test_rebuild_http import client


def preview(http, w, refresh=False):
    response = http.post('/api/explore/preview', json={'workspace': w.model_dump(mode='json'), 'refresh_data': refresh})
    assert response.status_code == 200, response.text
    return response.json()


def test_edits_additions_and_refresh_have_distinct_retrievals(tmp_path):
    data = SuppliedData()
    w = workspace()
    first = w.model_copy(update={'collection': w.collection[:2], 'views': ()})
    with client(tmp_path, data) as http:
        preview(http, first)
        assert len(data.requests) == 2
        view = ViewDefinition(id='history', measures=tuple(i.id for i in first.collection))
        first = first.model_copy(update={'views': (view,)})
        preview(http, first)
        assert len(data.requests) == 2, 'Adding a chart must reuse the loaded collection'
        changed = first.model_copy(update={'views': (view.model_copy(update={'name': 'New title', 'family': 'distribution', 'options': {'axes': ['spread']}}),)})
        preview(http, changed)
        assert len(data.requests) == 2
        preview(http, w)
        assert len(data.requests) == 6, 'Only four added bindings require retrieval'
        preview(http, w, refresh=True)
        assert len(data.requests) == 12


def test_coverage_extension_only_fetches_missing_dates(tmp_path):
    data = SuppliedData()
    w = workspace().model_copy(update={'views': ()})
    with client(tmp_path, data) as http:
        preview(http, w)
        boundary = data.requests[0].start
        later = w.model_copy(update={'as_of': date(2026, 9, 25)})
        preview(http, later)
        assert len(data.requests) == 12
        assert all(r.start == r.end == date(2026, 9, 25) for r in data.requests[6:])
        earlier = w.model_copy(update={'as_of': date(2026, 9, 23)})
        preview(http, earlier)
        assert all(r.end < boundary for r in data.requests[12:])


def test_workspaces_are_isolated_and_evicted_snapshots_reload(tmp_path):
    from kairopsis.exploration_cache import ExplorationCache
    data, w = SuppliedData(), workspace()
    with client(tmp_path, data) as http:
        http.app.state.exploration.cache = ExplorationCache(maximum_workspaces=1)
        preview(http, w)
        preview(http, w.model_copy(update={'id': 'second-workspace'}))
        assert len(data.requests) == 12
        preview(http, w)
        assert len(data.requests) == 18


def test_unchanged_charts_skip_statistics_and_keep_fresh_capture_identity(tmp_path, monkeypatch):
    import kairopsis.exploration_statistics as statistics
    original = statistics.summarize
    calls = []
    def summarize(*args, **kwargs):
        calls.append(args[0])
        return original(*args, **kwargs)
    monkeypatch.setattr(statistics, 'summarize', summarize)
    w = workspace()
    with client(tmp_path, SuppliedData()) as http:
        one = preview(http, w)['resolved_results'][0]
        renamed = w.model_copy(update={'name': 'Another question', 'views': (w.views[0].model_copy(update={'name': 'Renamed chart'}),)})
        two = preview(http, renamed)['resolved_results'][0]
        assert len(calls) == 1
        assert one['id'] != two['id']
        assert one['rows'] == two['rows'] and one['statistics'] == two['statistics']
        assert two['view']['name'] == 'Renamed chart'
        assert one['workspace_fingerprint'] != two['workspace_fingerprint']


def test_failed_refresh_preserves_snapshot_and_retry_reloads(tmp_path):
    class Provider(SuppliedData):
        fail = False
        offset = 0
        def fetch(self, request):
            data = super().fetch(request)
            if self.fail:
                raise RuntimeError('Provider unavailable')
            return data.model_copy(update={'series': tuple(s.model_copy(update={
                'observations': tuple(o.model_copy(update={'value': o.value + self.offset}) for o in s.observations)
            }) for s in data.series)})
    provider = Provider()
    w = workspace()
    with client(tmp_path, provider) as http:
        original = preview(http, w)['resolved_results'][0]
        provider.fail = True
        response = http.post('/api/explore/preview', json={'workspace': w.model_dump(mode='json'), 'refresh_data': True})
        assert response.status_code == 422
        provider.fail = False
        provider.offset = 100
        old = preview(http, w)['resolved_results'][0]
        assert old['rows'] == original['rows'], 'Failed refresh cannot poison the prior snapshot'
        new = preview(http, w, refresh=True)['resolved_results'][0]
        assert new['rows'] != old['rows']


def test_failed_collection_preload_is_reported_and_retried(tmp_path):
    class Offline(SuppliedData):
        def fetch(self, request):
            raise RuntimeError('Unavailable')
    w = workspace().model_copy(update={'views': ()})
    with client(tmp_path, Offline()) as http:
        response = http.post('/api/explore/preview', json={'workspace': w.model_dump(mode='json')})
        assert response.status_code == 422
        assert 'Could not load' in response.json()['detail']


def test_engine_outputs_reused_across_chart_types(tmp_path, monkeypatch):
    import kairopsis.exploration as exploration
    from kairopsis.models import ResolvedDefinition, AnalysisSettings
    original, calls = exploration.evaluate, []
    def evaluate(*args):
        calls.append(args[0].id)
        return original(*args)
    monkeypatch.setattr(exploration, 'evaluate', evaluate)
    w = workspace()
    item = w.collection[0]
    definition = ResolvedDefinition(id='a', revision=1, name='Weekly changes', calculation='level', inputs=(item.binding,),
        settings=AnalysisSettings(calculation_contract='input-pipeline-v2', measure='change', horizon='week'))
    item = item.model_copy(update={'kind': 'analysis', 'binding': None, 'analysis': definition})
    view = ViewDefinition(measures=(item.id,))
    w = w.model_copy(update={'collection': (item,), 'views': (view,)})
    with client(tmp_path, SuppliedData()) as http:
        preview(http, w)
        preview(http, w.model_copy(update={'views': (view.model_copy(update={'family': 'distribution'}),)}))
        assert calls == ['a']
        preview(http, w, refresh=True)
        assert calls == ['a', 'a']
