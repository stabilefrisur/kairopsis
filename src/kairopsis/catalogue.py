"""Small active catalogue. Binding changes advance affected resolved definitions."""
from .fixtures import analysis_fixture, series_fixture
from .models import AnalysisDefinition, AnalysisSettings, ResolvedDefinition, SeriesBinding
from .repository import Repository
from .risk import adjusted_unit
from .metapyle_catalogue import publish_catalogue
from .repository import atomic_bytes


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
        reference_ids = risk_references(analysis)
        if any(i not in series for i in reference_ids):
            raise ValueError("Choose an existing risk reference series")
        return ResolvedDefinition(id=analysis.id, revision=analysis.revision, name=analysis.name,
            calculation=analysis.calculation, settings=analysis.settings, inputs=tuple(series[i] for i in analysis.series_ids),
            references=tuple(series[i] for i in sorted(reference_ids - set(analysis.series_ids))))

    def save(self, kind: str, record: SeriesBinding | AnalysisDefinition) -> dict:
        with self.repository.transaction():
            records = self.records()
            old = next((r for r in records[kind] if r["id"] == record.id), None)
            value = record.model_dump(mode="json")
            value["revision"] = old["revision"] + 1 if old else 1
            if kind == "analyses":
                definition = AnalysisDefinition.model_validate(value)
                series = {s["id"]: s for s in records["series"]}
                if any(i not in series for i in definition.series_ids):
                    raise ValueError("Choose existing input series")
                if any(i not in series for i in risk_references(definition)):
                    raise ValueError("Choose an existing risk reference series")
                units = [adjusted_unit(series[i]["unit"], series[r.reference_id or i]["unit"] if r.method != "none" else series[i]["unit"],
                    r.method, definition.settings.measure) for i, r in zip(definition.series_ids, definition.settings.adjustments(len(definition.series_ids)))]
                if definition.calculation == "difference" and len(set(units)) != 1:
                    raise ValueError("Difference requires matching units")
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
