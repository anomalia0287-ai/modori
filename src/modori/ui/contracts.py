from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


Language = Literal["ko", "en"]
ControllerModeValue = Literal["guided", "standard"]
RunStatusValue = Literal["empty", "ready", "running", "error"]
SelectionProvenance = Literal["manual", "experimental_candidate_assisted"]


class ControllerMode(str, Enum):
    GUIDED = "guided"
    STANDARD = "standard"


class RunStatus(str, Enum):
    EMPTY = "empty"
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    message_ko: str
    error_code: str | None = None
    run_id: int | None = None
    pipeline_version: int = 0
    changed_step_ids: list[str] = field(default_factory=list)
    result_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExplainResult:
    ok: bool
    slug: str | None
    title: str
    content: dict[str, object]
    error_code: str | None = None
    message_ko: str = ""


@dataclass(frozen=True)
class ImportOptions:
    preserve_sav_metadata: bool = True
    confirm_new_session: bool = False
    table_layout: dict[str, Any] | None = None
    drop_aggregate_rows: bool = False
    drop_duplicate_rows: bool = False
    import_selection: dict[str, Any] | None = None


@dataclass(frozen=True)
class ReportExportOptions:
    language: Language = "ko"
    include_descriptives: bool = True
    include_reliability: bool = True
    include_comparison: bool = True
    include_association: bool = True
    include_group_models: bool = True
    include_dimension_reduction: bool = True
    include_regression: bool = True
    include_figures: bool = True
    selection_provenance: SelectionProvenance = "manual"


@dataclass(frozen=True)
class DisplayColumn:
    label: str
    entity_key: str | None = None
    not_explainable: bool = False


@dataclass(frozen=True)
class DisplayTable:
    caption_ko: str
    caption_en: str
    columns: list[DisplayColumn]
    rows: list[list[str]]


@dataclass(frozen=True)
class DisplayNote:
    title: str
    body: str
    entity_key: str | None = None


@dataclass(frozen=True)
class DisplayResult:
    result_id: str
    kind: Literal[
        "descriptives",
        "reliability",
        "comparison",
        "regression",
        "frequency_crosstab",
        "correlation",
        "anova_oneway",
        "kruskal_wallis",
        "ancova",
        "factor_pca",
        "repeated_measures_anova",
        "friedman",
        "mediation",
        "moderated_mediation",
        "report",
    ]
    title_ko: str
    title_en: str
    prose_ko: str
    prose_en: str
    tables: list[DisplayTable] = field(default_factory=list)
    chart_paths: list[str] = field(default_factory=list)
    notes: list[DisplayNote] = field(default_factory=list)


@dataclass(frozen=True)
class ReliabilityPatch:
    item_keys: list[str]
    language: Language


@dataclass(frozen=True)
class ComparisonPatch:
    outcome_key: str
    group_key: str
    group_a: str | int | float
    group_b: str | int | float
    language: Language


@dataclass(frozen=True)
class RegressionPatch:
    outcome_key: str
    predictor_keys: list[str]
    include_intercept: bool
    language: Language


@dataclass(frozen=True)
class ReportPatch:
    language: Language
    include_descriptives: bool
    include_reliability: bool
    include_comparison: bool
    include_association: bool
    include_group_models: bool
    include_dimension_reduction: bool
    include_regression: bool
    include_figures: bool


@dataclass(frozen=True)
class VariableMetadataPatch:
    variable_key: str
    label: str | None = None
    measure: Literal["scale", "ordinal", "nominal"] | None = None
    value_labels: dict[str, Any] | None = None
    missing_codes: list[Any] | None = None
    display_type: str | None = None


@dataclass(frozen=True)
class DataCellPatch:
    row_id: str
    variable_key: str
    new_value: Any
