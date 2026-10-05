"""Small active catalogue. Binding changes advance affected resolved definitions."""
from .fixtures import analysis_fixture, series_fixture
from .models import AnalysisDefinition, AnalysisSettings, ResolvedDefinition, SeriesBinding
from .repository import Repository
from .risk import adjusted_unit
from .metapyle_catalogue import publish_catalogue
from .repository import atomic_bytes


class CatalogueConflict(ValueError):
    pass


class Catalogue:
    def __init__(self, repository: Repository):
        self.repository = repository
        with repository.transaction():
            if repository.read_json("catalogue") is None:
                repository.write_json("catalogue", {
                    "series": [s.model_dump(mode="json") for s in series_fixture()] if repository.mode == "mock" else [],
                    "analyses": [a.model_dump(mode="json") for a in analysis_fixture()] if repository.mode == "mock" else []})
            self._publish(self.records())

    @property
    def metapyle_path(self):
        return self.repository.root / "metapyle.yaml"

    def _publish(self, records: dict) -> None:
        publish_catalogue(self.metapyle_path, tuple(SeriesBinding.model_validate(s) for s in records["series"]))

    def _commit(self, records: dict) -> None:
        # JSON publishes metadata/analyses together. YAML is a recoverable
        # projection, restored on a failed commit and rebuilt at startup.
        previous = self.metapyle_path.read_bytes()
        self._publish(records)
        try:
            self.repository.write_json("catalogue", records)
        except OSError:
            atomic_bytes(self.metapyle_path, previous)
            raise

    def records(self) -> dict:
        return self.repository.read_json("catalogue")

    def resolve(self, key: str, settings: AnalysisSettings | None = None) -> ResolvedDefinition:
        records = self.records()
        analysis = next((AnalysisDefinition.model_validate(a) for a in records["analyses"] if a["id"] == key), None)
        if not analysis:
            raise FileNotFoundError("Analysis not found")
        series = {s["id"]: SeriesBinding.model_validate(s) for s in records["series"]}
        if settings is not None:
            analysis = AnalysisDefinition.model_validate({**analysis.model_dump(), "settings": settings})
        return resolve_definition(analysis, series)

    def resolve_draft(self, analysis: AnalysisDefinition, drafts: tuple[SeriesBinding, ...]) -> ResolvedDefinition:
        series = {s["id"]: SeriesBinding.model_validate(s) for s in self.records()["series"]}
        if len({s.id for s in drafts}) != len(drafts):
            raise ValueError("Stage each data series only once")
        series.update({s.id: s for s in drafts})
        return resolve_definition(analysis, series)

    def save_bundle(self, analysis: AnalysisDefinition, drafts: tuple[SeriesBinding, ...],
                    base_revisions: dict[str, dict[str, int]] | None = None) -> dict:
        with self.repository.transaction():
            records = self.records()
            if len({s.id for s in drafts}) != len(drafts):
                raise ValueError("Stage each data series only once")
            retained = set(analysis.series_ids) | risk_references(analysis)
            for kind, expected in (base_revisions or {}).items():
                if kind not in ("series", "analyses"):
                    raise ValueError("Unknown catalogue record kind")
                current = {r["id"]: r["revision"] for r in records[kind]}
                for key, revision in expected.items():
                    if (kind == "series" and key in retained or kind == "analyses" and key == analysis.id) and current.get(key) != revision:
                        raise CatalogueConflict("A record changed or was deleted since editing began. Reload the saved entry before saving; your draft has been retained.")
            saved_series = {s["id"]: s for s in records["series"]}
            old_analysis = next((a for a in records["analyses"] if a["id"] == analysis.id), None)
            if old_analysis and old_analysis["revision"] != analysis.revision:
                raise CatalogueConflict("Analysis changed since editing began. Reload its saved defaults before saving.")
            changed: dict[str, dict] = {}
            for draft in drafts:
                if draft.id not in retained:
                    continue
                old = saved_series.get(draft.id)
                if old and old["revision"] != draft.revision:
                    raise CatalogueConflict("An input series changed since editing began. Reload it before saving.")
                value = draft.model_dump(mode="json")
                if old == value:
                    continue
                value["revision"] = old["revision"] + 1 if old else 1
                changed[draft.id] = value
            saved_series.update(changed)
            series = {key: SeriesBinding.model_validate(value) for key, value in saved_series.items()}
            values = {a["id"]: a for a in records["analyses"]}
            values[analysis.id] = analysis.model_dump(mode="json")
            for key, value in values.items():
                definition = AnalysisDefinition.model_validate(value)
                affected = key == analysis.id or bool(set(changed) & (set(definition.series_ids) | risk_references(definition)))
                if affected:
                    resolve_definition(definition, series)
                    old = next((a for a in records["analyses"] if a["id"] == key), None)
                    value["revision"] = old["revision"] + 1 if old else 1
            records = {"series": list(saved_series.values()), "analyses": list(values.values())}
            self._commit(records)
            return {"analysis": values[analysis.id], "series": list(changed.values())}

    def save(self, kind: str, record: SeriesBinding | AnalysisDefinition) -> dict:
        with self.repository.transaction():
            records = self.records()
            old = next((r for r in records[kind] if r["id"] == record.id), None)
            value = record.model_dump(mode="json")
            value["revision"] = old["revision"] + 1 if old else 1
            if kind == "analyses":
                definition = AnalysisDefinition.model_validate(value)
                resolve_definition(definition, {s["id"]: SeriesBinding.model_validate(s) for s in records["series"]})
            elif old:
                records["analyses"] = [{**a, "revision": a["revision"] + 1} if record.id in set(a["series_ids"]) | risk_references(AnalysisDefinition.model_validate(a)) else a for a in records["analyses"]]
            records[kind] = [value if r["id"] == record.id else r for r in records[kind]] if old else [*records[kind], value]
            self._commit(records)
            return value

    def set_monitoring(self, key: str, monitored: bool) -> dict:
        with self.repository.transaction():
            records = self.records()
            analysis = next((a for a in records["analyses"] if a["id"] == key), None)
            if analysis is None:
                raise FileNotFoundError("Analysis not found")
            # Monitoring membership does not change the evaluated definition.
            analysis["monitored"] = monitored
            self.repository.write_json("catalogue", records)
            return analysis

    def delete(self, kind: str, key: str) -> None:
        with self.repository.transaction():
            records = self.records()
            if not any(r["id"] == key for r in records[kind]):
                raise FileNotFoundError("Catalogue entry not found")
            dependencies = [a["name"] for a in records["analyses"] if key in set(a["series_ids"]) | risk_references(AnalysisDefinition.model_validate(a))] if kind == "series" else []
            if dependencies:
                raise ValueError("Used by: " + ", ".join(dependencies))
            records[kind] = [r for r in records[kind] if r["id"] != key]
            self._commit(records)


def risk_references(analysis: AnalysisDefinition) -> set[str]:
    return {r.reference_id for r in analysis.settings.adjustments(len(analysis.series_ids))
            if r.method != "none" and r.reference_id is not None}


def resolve_definition(analysis: AnalysisDefinition, series: dict[str, SeriesBinding]) -> ResolvedDefinition:
    if any(i not in series for i in analysis.series_ids):
        raise ValueError("Choose existing or staged input series")
    reference_ids = risk_references(analysis)
    if any(i not in series for i in reference_ids):
        raise ValueError("Choose existing or staged risk reference series")
    units = [adjusted_unit(series[i].unit, series[r.reference_id or i].unit if r.method != "none" else series[i].unit,
        r.method, analysis.settings.measure) for i, r in zip(analysis.series_ids, analysis.settings.adjustments(len(analysis.series_ids)))]
    if analysis.calculation == "difference" and len(set(units)) != 1:
        raise ValueError("Difference requires matching units")
    return ResolvedDefinition(id=analysis.id, revision=analysis.revision, name=analysis.name,
        calculation=analysis.calculation, settings=analysis.settings, inputs=tuple(series[i] for i in analysis.series_ids),
        references=tuple(series[i] for i in sorted(reference_ids - set(analysis.series_ids))))
