"""Versioned Explore definitions, authoritative samples and frozen evidence.

Collection IDs identify associations, never provider queries. Full retained
bindings/definitions pin revisions even after Library entries change or disappear.
"""
from datetime import date as Date, datetime
from math import isfinite
from typing import Any, Literal

from pydantic import Field, model_validator

from .models import AnalysisDefinition, Record, ResolvedDefinition, SeriesBinding, identity


class CollectionItem(Record):
    id: str = Field(default_factory=identity, pattern=r"^[A-Za-z0-9_-]{1,128}$")
    symbol: str = Field(min_length=1, max_length=200)
    field: str = Field(min_length=1, max_length=200)
    kind: Literal["series", "analysis"] = "series"
    origin: Literal["library", "local"] = "library"
    binding: SeriesBinding | None = None
    analysis: ResolvedDefinition | None = None
    semantics: str = Field(default="unknown", max_length=10000)

    @model_validator(mode="after")
    def reference(self):
        if (self.kind == "series") != (self.binding is not None) or (self.kind == "analysis") != (self.analysis is not None):
            raise ValueError("Choose exactly one retained series binding or resolved Analysis")
        if not self.symbol.strip() or not self.field.strip():
            raise ValueError("Explicit symbol and field associations are required")
        if self.analysis:
            from .catalogue import resolve_definition
            definition = self.analysis
            records = (*definition.inputs, *definition.references)
            if len({binding.id for binding in records}) != len(records):
                raise ValueError("Resolved Analysis input/reference identities must be unique")
            draft = AnalysisDefinition(id=definition.id, revision=definition.revision, name=definition.name,
                economic_rationale=definition.economic_rationale, calculation=definition.calculation,
                series_ids=tuple(binding.id for binding in definition.inputs), settings=definition.settings)
            resolved = resolve_definition(draft, {binding.id: binding for binding in records})
            if {binding.id for binding in definition.references} != {binding.id for binding in resolved.references}:
                raise ValueError("Resolved Analysis references must match its active calculation dependencies")
        return self


class SuppliedAttribute(Record):
    symbol: str
    name: str
    value: str
    source: str = Field(min_length=1)
    effective_start: Date | None = None
    effective_end: Date | None = None

    @model_validator(mode="after")
    def interval(self):
        if self.effective_start and self.effective_end and self.effective_end < self.effective_start:
            raise ValueError("Attribute end precedes start")
        return self


class NumericFilter(Record):
    field: str
    minimum: float | None = None
    maximum: float | None = None


class ViewSample(Record):
    start: Date | None = None
    end: Date | None = None
    members: tuple[str, ...] | None = None
    excluded_row_ids: tuple[str, ...] = ()
    row_ids: tuple[str, ...] = ()
    date_policy: Literal["exact", "backward"] = "exact"
    maximum_age_days: int = Field(default=0, ge=0, le=3660)
    interval_start: Date | None = None
    interval_measure: Literal["level", "change", "return"] = "level"
    filters: tuple[NumericFilter, ...] = ()

    @model_validator(mode="after")
    def dates(self):
        if self.start and self.end and self.end < self.start:
            raise ValueError("Sample end precedes start")
        if self.interval_measure != "level" and self.interval_start is None:
            raise ValueError("Interval changes require an explicit start date")
        return self


class ViewDefinition(Record):
    id: str = Field(default_factory=identity, pattern=r"^[A-Za-z0-9_-]{1,128}$")
    name: str = Field(default="View", min_length=1, max_length=200)
    family: Literal["history", "scatter", "ranking", "distribution", "heatmap", "correlation"] = "history"
    measures: tuple[str, ...] = ()
    shape: Literal["history", "cross_section", "paired_date", "panel"] = "history"
    sample: ViewSample = Field(default_factory=ViewSample)
    as_of: Date | None = None
    display_start: Date | None = None
    display_end: Date | None = None
    pinned: bool = False
    width: Literal[1, 2] = 1
    highlight: tuple[str, ...] = ()
    size_by: str | None = None
    color_by: str | None = None
    facet_by: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def operation_options(self):
        # Separate descriptive-fit samples need a retained typed sample contract.
        # Unprovenanced caller rows must never enter calculation or capture.
        allowed = {"axes", "x", "y", "value", "history_layout", "descriptive_fit", "fit", "allow_pooled_fit",
            "distribution", "form", "bandwidth", "bandwidth_multiplier", "shared_bandwidth", "bins", "bin_edges",
            "group_by", "weight_policy", "selected_value", "selected_row_id", "heatmap_layout", "orientation", "aggregation",
            "correlation_orientation", "correlation_method", "correlation_sample", "method", "sample_policy"}
        if set(self.options) - allowed:
            raise ValueError("Unsupported view options; external fit_rows are unavailable until retained fit samples are implemented")
        if "axes" in self.options and (not isinstance(self.options["axes"], (list, tuple)) or any(not isinstance(axis, str) for axis in self.options["axes"])):
            raise ValueError("View axes must be a list of retained measure fields")
        for key in ("x", "y", "value", "history_layout", "distribution", "form", "group_by", "weight_policy", "heatmap_layout", "orientation", "aggregation", "correlation_orientation", "correlation_method", "correlation_sample", "method", "sample_policy", "selected_row_id"):
            if key in self.options and self.options[key] is not None and not isinstance(self.options[key], str):
                raise ValueError(f"{key}: expected a named option")
        for key in ("descriptive_fit", "fit", "allow_pooled_fit", "shared_bandwidth"):
            if key in self.options and not isinstance(self.options[key], bool):
                raise ValueError(f"{key}: expected a boolean")
        for key in ("bandwidth", "bandwidth_multiplier"):
            if key in self.options and (isinstance(self.options[key], bool) or not isinstance(self.options[key], (int, float)) or not isfinite(self.options[key]) or self.options[key] <= 0):
                raise ValueError(f"{key}: expected a positive number")
        if "bins" in self.options and (isinstance(self.options["bins"], bool) or not isinstance(self.options["bins"], int) or not 1 <= self.options["bins"] <= 1000):
            raise ValueError("Histogram bins must be an integer from 1 to 1000")
        if "bin_edges" in self.options:
            edges = self.options["bin_edges"]
            if not isinstance(edges, (list, tuple)) or not 2 <= len(edges) <= 1001 or any(isinstance(v, bool) or not isinstance(v, (float, int)) or not isfinite(v) for v in edges) or any(a >= b for a, b in zip(edges, edges[1:])):
                raise ValueError("Histogram edges must be finite strictly increasing numbers")
        if "selected_value" in self.options and (isinstance(self.options["selected_value"], bool) or not isinstance(self.options["selected_value"], (int, float)) or not isfinite(self.options["selected_value"])):
            raise ValueError("Selected value must be a finite number")
        non_time = (self.family == "heatmap" and self.options.get("heatmap_layout", self.options.get("orientation")) in ("fields", "symbols_fields")) or (self.family == "correlation" and self.options.get("correlation_orientation", self.options.get("orientation")) in ("fields", "fields_across_symbols"))
        if non_time and self.shape not in ("cross_section", "panel"):
            raise ValueError("Field comparisons require a cross-section or explicitly selected panel sample")
        return self


class WorkspaceDefinition(Record):
    id: str = Field(default_factory=identity, pattern=r"^[A-Za-z0-9_-]{1,128}$")
    name: str = Field(default="Untitled exploration", min_length=1, max_length=200)
    version: str | None = None
    collection: tuple[CollectionItem, ...] = Field(default=(), max_length=400)
    views: tuple[ViewDefinition, ...] = Field(default=(), max_length=32)
    as_of: Date | None = None
    question: str = Field(default="", max_length=10000)
    notes: str = Field(default="", max_length=50000)
    attributes: tuple[SuppliedAttribute, ...] = ()
    layout: Literal["workbench", "focus"] = "workbench"

    @model_validator(mode="after")
    def dependencies(self):
        ids = [c.id for c in self.collection]
        if len(ids) != len(set(ids)):
            raise ValueError("Collection identities must be unique")
        associations = [(c.symbol, c.field) for c in self.collection]
        if len(associations) != len(set(associations)):
            raise ValueError("Duplicate symbol/field assignment; give revised outputs distinct explicit fields")
        if len({v.id for v in self.views}) != len(self.views):
            raise ValueError("View identities must be unique")
        for view in self.views:
            if not view.measures or any(i not in ids for i in view.measures):
                raise ValueError(f"{view.name}: choose existing collection measures")
            if view.size_by and view.size_by not in ids:
                raise ValueError(f"{view.name}: Size by must reference a collection measure")
            available = set(view.measures) if view.shape == "paired_date" else {c.field for c in self.collection if c.id in view.measures}
            selected_axes = view.options.get("axes") or list(available)
            if any(axis not in available for axis in selected_axes):
                raise ValueError(f"{view.name}: axes must reference selected retained measures")
            if view.family == "scatter" and any(view.options.get(axis) and view.options[axis] not in selected_axes for axis in ("x", "y")):
                raise ValueError(f"{view.name}: scatter axes must reference the selected sample fields")
            attribute_names = {a.name for a in self.attributes}
            if view.color_by and view.color_by != "symbol":
                valid_colour = view.color_by in attribute_names or view.color_by in ids or view.shape != "paired_date" and any(c.field == view.color_by for c in self.collection)
                if not valid_colour:
                    raise ValueError(f"{view.name}: choose a retained numeric measure or supplied colour attribute")
            if view.sample.interval_start and (view.as_of or self.as_of) and view.sample.interval_start > (view.as_of or self.as_of):
                raise ValueError(f"{view.name}: interval start follows as-of date")
        for i, attribute in enumerate(self.attributes):
            for other in self.attributes[:i]:
                if (other.symbol, other.name) == (attribute.symbol, attribute.name):
                    if max(other.effective_start or Date.min, attribute.effective_start or Date.min) <= min(other.effective_end or Date.max, attribute.effective_end or Date.max):
                        raise ValueError("Overlapping supplied attribute assignments")
        return self


class SampleRow(Record):
    id: str
    symbol: str
    date: Date
    values: dict[str, float | None]
    dates: dict[str, Date | None] = Field(default_factory=dict)
    observed_on: dict[str, Date | None] = Field(default_factory=dict)
    bindings: dict[str, str] = Field(default_factory=dict)
    endpoints: dict[str, dict[str, Any]] = Field(default_factory=dict)
    attributes: dict[str, str] = Field(default_factory=dict)
    reasons: tuple[str, ...] = ()
    source_row_ids: tuple[str, ...] = ()


class ViewResult(Record):
    id: str = Field(default_factory=identity)
    view_id: str
    workspace_id: str
    definition_fingerprint: str
    workspace_fingerprint: str
    data_fingerprint: str
    created_at: datetime
    expires_at: datetime
    as_of: Date
    view: ViewDefinition
    rows: tuple[SampleRow, ...]
    excluded: tuple[SampleRow, ...]
    measures: dict[str, dict[str, Any]]
    axes: tuple[str, ...]
    axis_units: dict[str, str] = Field(default_factory=dict)
    statistics: dict[str, Any]
    input_evidence: dict[str, Any]
    limitations: tuple[str, ...] = ()
    display_row_ids: tuple[str, ...] = ()


class ExplorationSnapshot(Record):
    id: str = Field(default_factory=identity)
    captured_at: datetime
    workspace: WorkspaceDefinition
    results: tuple[ViewResult, ...]
    role: Literal["supporting", "challenging", "contextual"] = "contextual"
    images: dict[str, str]
