"""Small resolved data/evidence contracts; provider records independently reusable."""
from datetime import date as Date
from math import isfinite
from typing import Annotated, Literal
from uuid import uuid4
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue, StringConstraints, model_validator

from .periods import Period


EconomicRationale = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, max_length=10000)]


def identity() -> str:
    return uuid4().hex


class Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    schema_version: Literal[1] = 1


class ComparisonBasis(Record):
    label: str = Field(min_length=1)
    currency: str = Field(min_length=1)
    reference_curve: str = Field(min_length=1)
    adjustment: str = Field(min_length=1)


class SeriesBinding(Record):
    id: str = Field(default_factory=identity, pattern=r"^[A-Za-z0-9_-]{1,128}$")
    revision: int = Field(default=1, ge=1)
    name: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1)
    instrument: str = Field(min_length=1)
    field: str | None = None
    unit: str = Field(min_length=1)
    currency: str = Field(min_length=1)
    basis: ComparisonBasis | None = None
    catalog_name: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,128}$")
    path: str | None = None
    params: dict[str, JsonValue] = Field(default_factory=dict)
    description: str | None = None

    @model_validator(mode="after")
    def query_fields(self):
        if self.catalog_name is not None and self.field is not None and not self.field.strip():
            raise ValueError("Provider field must be nonempty or omitted")
        if not self.instrument.strip() or not self.source.strip():
            raise ValueError("Provider source and symbol must be nonempty")
        return self


class Observation(Record):
    date: Date
    value: float | None
    observed_on: Date | None
    value_issue: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_nonfinite(cls, values):
        if isinstance(values, dict) and isinstance(values.get("value"), (int, float, str)):
            try:
                finite = isfinite(float(values["value"]))
            except (ValueError, OverflowError):
                return values
            if not finite:
                return {**values, "value": None, "value_issue": "Non-finite supplied value"}
        return values


class DataRequest(Record):
    bindings: tuple[SeriesBinding, ...]
    start: Date
    end: Date
    freshness: Literal["prefer_cache", "require_fresh"] = "require_fresh"


class SeriesResult(Record):
    binding: SeriesBinding
    observations: tuple[Observation, ...]
    provenance: str


class DataFailure(Record):
    binding_id: str
    code: str
    message: str


class DataResponse(Record):
    mode: Literal["mock", "live"]
    requested: tuple[str, ...]
    series: tuple[SeriesResult, ...]
    attempted_at: AwareDatetime
    completed_at: AwareDatetime
    outcome: Literal["synthetic", "fresh", "cache", "partial", "failed", "unverified"]
    failures: tuple[DataFailure, ...] = ()


class RiskAdjustment(Record):
    method: Literal["none", "volatility", "beta", "var", "es"] = "none"
    estimation_measure: Literal["change", "return"] | None = None
    reference_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,128}$")
    lookback_years: Period = 3
    weighting: Literal["equal", "exponential"] = "equal"
    half_life: float = Field(default=63, gt=0, le=2520)
    confidence: float = Field(default=95, gt=50, lt=100)
    downside: Literal["increase", "decrease"] = "increase"
    minimum_samples: int = Field(default=60, ge=3, le=10000)
    estimator: Literal["historical-risk-v1"] = "historical-risk-v1"


class AnalysisSettings(Record):
    calculation_contract: Literal["input-pipeline-v1", "input-pipeline-v2"] = "input-pipeline-v1"
    history_years: Period = 3
    fit_years: Period = 3
    horizon: Literal["day", "week", "month"] = "day"
    measure: Literal["level", "change", "return"] = "level"
    standardization: Literal["none", "zscore"] = "none"
    zscore_threshold: float = Field(default=2, gt=0)
    risk_adjustment: RiskAdjustment = Field(default_factory=RiskAdjustment)
    risk_overrides: tuple[RiskAdjustment, ...] = Field(default=(), max_length=2)
    minimum_history: int = Field(default=60, ge=3)
    minimum_fit: int = Field(default=20, ge=3)
    upper_percentile: float = Field(default=95, gt=50, le=100)
    move_threshold: float | None = Field(default=None, gt=0)
    material_change: float | None = Field(default=None, gt=0)
    calibration: Literal["demo-native-v1", "configured-native-v1"] = "demo-native-v1"

    @model_validator(mode="after")
    def risk_measure(self):
        if self.calculation_contract == "input-pipeline-v1":
            if self.measure == "level" and any(r.method != "none" for r in self.adjustments(2)):
                raise ValueError("Risk adjustment requires changes or percentage returns")
            if any(r.method != "none" and r.estimation_measure is not None for r in self.adjustments(2)):
                raise ValueError("Explicit risk estimation measure requires input-pipeline-v2")
        return self

    def check_standardization(self, calculation: str) -> None:
        if self.calculation_contract == "input-pipeline-v1" and self.standardization == "zscore" and not (calculation in ("difference", "regression") or
                calculation == "level" and self.measure in ("change", "return")):
            raise ValueError("Z-scores require standalone changes, pair differences or regression residuals")

    def adjustments(self, count: int) -> tuple[RiskAdjustment, ...]:
        return self.risk_overrides or (self.risk_adjustment,) * count

    def estimation_basis(self, options: RiskAdjustment) -> Literal["change", "return"]:
        if self.calculation_contract == "input-pipeline-v2" and options.estimation_measure:
            return options.estimation_measure
        return "return" if self.measure == "return" else "change"

    def needs_moves(self, count: int) -> bool:
        return self.measure != "level" or any(r.method != "none" for r in self.adjustments(count))


class AnalysisDefinition(Record):
    id: str = Field(default_factory=identity, pattern=r"^[A-Za-z0-9_-]{1,128}$")
    revision: int = Field(default=1, ge=1)
    name: str = Field(min_length=1, max_length=200)
    economic_rationale: EconomicRationale = ""
    calculation: Literal["level", "difference", "ratio", "regression"] = "level"
    series_ids: tuple[str, ...]
    monitored: bool = False
    settings: AnalysisSettings = Field(default_factory=AnalysisSettings)

    @model_validator(mode="after")
    def input_count(self):
        self.settings.check_standardization(self.calculation)
        if len(self.series_ids) != (1 if self.calculation == "level" else 2):
            raise ValueError("Standalone needs one input; Pair needs two ordered inputs")
        if len(set(self.series_ids)) != len(self.series_ids):
            raise ValueError("Pair inputs must differ")
        if self.settings.risk_overrides and len(self.settings.risk_overrides) != len(self.series_ids):
            raise ValueError("Risk overrides must match the input series count")
        return self


class ResolvedDefinition(Record):
    id: str
    revision: int
    name: str
    economic_rationale: EconomicRationale = ""
    calculation: Literal["level", "difference", "ratio", "regression"]
    inputs: tuple[SeriesBinding, ...]
    settings: AnalysisSettings
    references: tuple[SeriesBinding, ...] = ()

    @model_validator(mode="after")
    def override_count(self):
        self.settings.check_standardization(self.calculation)
        if self.settings.risk_overrides and len(self.settings.risk_overrides) != len(self.inputs):
            raise ValueError("Risk overrides must match the input series count")
        return self


class MetricPoint(Record):
    date: Date
    value: float | None
    inputs: tuple[float | None, ...]
    observed_on: tuple[Date | None, ...]
    eligible: bool
    unstandardized_value: float | None = None
    transformed_inputs: tuple[float | None, ...] = ()
    risk_scales: tuple[float | None, ...] = ()
    period_start: tuple[Date | None, ...] = ()


class AdjustmentEstimate(Record):
    reference_id: str
    scale: float | None
    sample_count: int = 0
    start: Date | None = None
    end: Date | None = None
    limitation: str | None = None
    estimation_measure: Literal["change", "return"] | None = None
    cutoff: Date | None = None
    sample_dates: tuple[Date, ...] = ()


class Fit(Record):
    slope: float
    intercept: float
    r_squared: float | None
    sample_count: int
    start: Date
    end: Date
    x_min: float
    x_max: float


class StandardizationEstimate(Record):
    mean: float | None = None
    standard_deviation: float | None = None
    sample_count: int = 0
    start: Date | None = None
    end: Date | None = None
    unit: str
    limitation: str | None = None


class Evaluation(Record):
    id: str = Field(default_factory=identity)
    definition: ResolvedDefinition
    request: DataRequest
    data: DataResponse
    evaluated_at: AwareDatetime
    points: tuple[MetricPoint, ...]
    unit: str
    input_units: tuple[str, ...] = ()
    adjustment_estimates: tuple[AdjustmentEstimate, ...] = ()
    standardization_estimate: StandardizationEstimate | None = None
    current: float | None
    observation_date: Date | None
    input_dates: tuple[Date | None, ...]
    percentile: float | None
    change: float | None
    change_start: Date | None
    eligible: bool
    limitations: tuple[str, ...]
    fit: Fit | None = None
    sensitivity: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    condition_keys: tuple[str, ...] = ()
    finding: Literal["quiet", "condition", "new", "changed", "unchanged", "correction", "incompatible", "unavailable"] = "quiet"
    baseline_id: str | None = None
    method: Literal["midrank-exact-ols-v1"] = "midrank-exact-ols-v1"


class DisplaySettings(Record):
    years: Period = 3
    view: Literal["analysis", "underlying", "scatter", "changes"] = "analysis"
    hidden_traces: tuple[Annotated[int, Field(ge=0, le=1)], ...] = Field(default=(), max_length=2)
    axis_ranges: dict[Literal["xaxis", "yaxis", "yaxis2"],
                      tuple[float | Annotated[str, Field(max_length=64)],
                            float | Annotated[str, Field(max_length=64)]]] = Field(default_factory=dict)


class Snapshot(Record):
    id: str = Field(default_factory=identity)
    evaluation: Evaluation
    display: DisplaySettings
    captured_at: AwareDatetime
    mode: Literal["saved", "latest", "investigation"]
    image_sha256: str


class ChartEntry(Record):
    id: str = Field(default_factory=identity)
    snapshot_id: str
    note: str = ""
    modified_at: AwareDatetime | None = None


class IdeaNote(Record):
    id: str = Field(default_factory=identity)
    text: str = Field(min_length=1, max_length=50000)
    created_at: AwareDatetime
    modified_at: AwareDatetime | None = None


class Idea(Record):
    id: str = Field(default_factory=identity)
    title: str = Field(min_length=1, max_length=200)
    thought: str = Field(default="", max_length=50000)
    shortlisted: bool = False
    archived: bool = False
    charts: tuple[ChartEntry, ...] = ()
    notes: tuple[IdeaNote, ...] = ()
    created_at: AwareDatetime
    modified_at: AwareDatetime
    version: str = Field(default_factory=identity)

    def add_note(self, text: str, now: AwareDatetime) -> "Idea":
        note = IdeaNote(text=text.strip(), created_at=now)
        return self.model_copy(update={"notes": (*self.notes, note)})

    def change_note(self, key: str, text: str | None, now: AwareDatetime) -> "Idea":
        if not any(note.id == key for note in self.notes):
            raise FileNotFoundError("Idea note not found")
        notes = tuple(IdeaNote.model_validate({**note.model_dump(), "text": text.strip(), "modified_at": now})
            if note.id == key else note for note in self.notes) if text is not None else tuple(note for note in self.notes if note.id != key)
        return self.model_copy(update={"notes": notes})

    def annotate_chart(self, key: str, text: str, now: AwareDatetime) -> "Idea":
        if not any(chart.id == key for chart in self.charts):
            raise FileNotFoundError("Chart not found")
        return self.model_copy(update={"charts": tuple(chart.model_copy(update={"note": text, "modified_at": now})
            if chart.id == key else chart for chart in self.charts)})

    def remove_chart(self, key: str) -> "Idea":
        if not any(chart.id == key for chart in self.charts):
            raise FileNotFoundError("Chart not found")
        return self.model_copy(update={"charts": tuple(chart for chart in self.charts if chart.id != key)})
