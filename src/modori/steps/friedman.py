from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from modori.core import Dataset, Measure, PipelineContext, Step, StepResult
from modori.friedman_results import FriedmanLevelSummary, FriedmanResult


_SUPPORTED_MEASURES = {Measure.SCALE, Measure.ORDINAL}


@dataclass
class FriedmanStep(Step):
    step_type = "stats.friedman"
    produces_analysis = True
    CURRENT_SCHEMA_VERSION = 1
    CONTRACT_PARAM_EXAMPLES = {
        "current": {
            "schema_version": 1,
            "measures": ["pre", "mid", "post"],
            "within_factor": "time",
            "level_labels": ["pre", "mid", "post"],
            "posthoc_method": "none",
            "p_adjust": "none",
            "language": "ko",
        },
        "newer": {"schema_version": 999, "measures": ["pre", "mid", "post"]},
        "unknown_current": {
            "schema_version": 1,
            "measures": ["pre", "mid", "post"],
            "extra": "bad",
        },
    }

    @classmethod
    def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
        version = params.get("schema_version")
        if version is None:
            raise ValueError("friedman params require schema_version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError("schema_version must be an integer")
        if version > cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("friedman params use a newer schema_version")
        if version == cls.CURRENT_SCHEMA_VERSION:
            return params
        raise ValueError(f"unsupported friedman schema_version: {version}")

    @classmethod
    def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
        allowed = {
            "schema_version",
            "measures",
            "within_factor",
            "level_labels",
            "posthoc_method",
            "p_adjust",
            "language",
        }
        unknown = set(params) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unknown friedman params: {names}")
        if params.get("schema_version") != cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("friedman params were not migrated to the current schema")

        measures = params.get("measures")
        if (
            not isinstance(measures, list)
            or not all(isinstance(item, str) and item for item in measures)
        ):
            raise ValueError("friedman measures must be a list of strings")
        if len(measures) < 3:
            raise ValueError("friedman requires three or more measures")
        if len(set(measures)) != len(measures):
            raise ValueError("friedman measures contain duplicate variables")
        within_factor = params.get("within_factor", "condition")
        if not isinstance(within_factor, str) or not within_factor.strip():
            raise ValueError("within_factor must be a non-empty string")

        raw_level_labels = params.get("level_labels")
        if raw_level_labels is None:
            level_labels = list(measures)
        else:
            if (
                not isinstance(raw_level_labels, list)
                or len(raw_level_labels) != len(measures)
                or not all(isinstance(item, str) and item for item in raw_level_labels)
            ):
                raise ValueError("level_labels must match measures length")
            level_labels = list(raw_level_labels)

        posthoc_method = str(params.get("posthoc_method", "none"))
        if posthoc_method != "none":
            raise ValueError("friedman posthoc_method currently supports none only")
        p_adjust = str(params.get("p_adjust", "none"))
        if p_adjust != "none":
            raise ValueError("friedman p_adjust currently supports none only")
        language = str(params.get("language", "ko"))
        if language not in {"ko", "en"}:
            raise ValueError("language must be ko or en")
        return {
            "schema_version": cls.CURRENT_SCHEMA_VERSION,
            "measures": list(measures),
            "within_factor": within_factor.strip(),
            "level_labels": level_labels,
            "posthoc_method": posthoc_method,
            "p_adjust": p_adjust,
            "language": language,
        }

    def compute(self, ctx: PipelineContext) -> StepResult:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        result = self._compute_result(ctx.dataset, params)
        return StepResult(analysis=result)

    def reads(self) -> set[str]:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return {str(measure) for measure in params["measures"]}

    def writes(self) -> set[str]:
        return {self.id}

    def provenance(self) -> str:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return f"Friedman test for {', '.join(params['measures'])}"

    def _compute_result(
        self,
        dataset: Dataset,
        params: dict[str, object],
    ) -> FriedmanResult:
        measures = [str(item) for item in params["measures"]]
        level_labels = [str(item) for item in params["level_labels"]]
        self._validate_dataset(dataset, measures)
        source = dataset.frame_for_compute(measures)
        n_total = int(len(source))
        complete = source.dropna(axis=0, how="any").copy()
        n_used = int(len(complete))
        if n_used < 3:
            raise ValueError("friedman requires at least three complete subjects")
        n_excluded = n_total - n_used
        for measure in measures:
            complete[measure] = self._numeric_series(complete[measure], measure)

        arrays = [complete[measure].to_numpy(dtype=float) for measure in measures]
        test = stats.friedmanchisquare(*arrays)
        statistic = _as_finite_float(test.statistic, "Friedman Q")
        p_value = _as_finite_float(test.pvalue, "Friedman p-value")
        degrees_of_freedom = len(measures) - 1
        method_details = {
            "method": "chi_square_approximation",
            "ties_present": _has_row_ties(complete[measures].to_numpy(dtype=float)),
            "tie_correction": "scipy_friedmanchisquare",
            "subjects": n_used,
            "conditions": len(measures),
        }
        kendalls_w = _as_finite_float(
            statistic / (n_used * degrees_of_freedom),
            "Kendall's W",
        )
        warnings = ["검증된 Friedman 사후검정은 아직 제공하지 않는다."]
        if n_used <= 13 and len(measures) <= 4:
            warnings.append(
                "Friedman p-value는 카이제곱 근사에 기반하므로 작은 표본 또는 "
                "조건 수가 적은 설계에서는 해석을 보수적으로 해야 한다."
            )
        return FriedmanResult(
            analysis_key="friedman",
            title_ko="Friedman 검정",
            measures=tuple(measures),
            within_factor=str(params["within_factor"]),
            n_total=n_total,
            n_used=n_used,
            n_excluded=n_excluded,
            levels=tuple(
                self._level_summary(
                    complete,
                    variable=measure,
                    level_index=index + 1,
                    level_label=level_labels[index],
                    mean_rank=self._mean_rank(complete, column_index=index),
                )
                for index, measure in enumerate(measures)
            ),
            statistic_label="Q",
            statistic=statistic,
            degrees_of_freedom=degrees_of_freedom,
            p_value=p_value,
            kendalls_w=kendalls_w,
            posthoc=None,
            warnings_ko=tuple(warnings),
            notes_ko=(
                "Kendall's W는 Q / (N * (k - 1)) 공식을 사용했다.",
                "중앙 차트 렌더링 훅이 없어 Friedman 차트는 아직 생성하지 않는다.",
            ),
            apa_template_id=None,
            chart_spec=None,
            no_canonical_chart_reason_ko=(
                "Friedman ChartSpec의 중앙 렌더링 훅이 아직 연결되지 않아 차트를 생성하지 않는다."
            ),
            method_details=method_details,
        )

    @staticmethod
    def _validate_dataset(dataset: Dataset, measures: list[str]) -> None:
        if dataset.df.empty:
            raise ValueError("데이터셋이 비어 있어 Friedman 검정을 실행할 수 없습니다.")
        missing = [measure for measure in measures if measure not in dataset.variables]
        if missing:
            raise ValueError(f"데이터셋에 없는 변수: {', '.join(missing)}")
        for measure in measures:
            if dataset.variables[measure].measure not in _SUPPORTED_MEASURES:
                raise ValueError("friedman measures must be scale or ordinal variables")

    @staticmethod
    def _numeric_series(series: pd.Series, key: str) -> pd.Series:
        try:
            values = pd.to_numeric(series, errors="raise").astype(float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"friedman measure must be numeric: {key}") from exc
        if len(values) and not np.all(np.isfinite(values.to_numpy(dtype=float))):
            raise ValueError(f"friedman measure must be finite: {key}")
        return values

    @staticmethod
    def _mean_rank(frame: pd.DataFrame, *, column_index: int) -> float:
        ranks = np.apply_along_axis(stats.rankdata, 1, frame.to_numpy(dtype=float))
        return float(ranks[:, column_index].mean())

    @staticmethod
    def _level_summary(
        frame: pd.DataFrame,
        *,
        variable: str,
        level_index: int,
        level_label: str,
        mean_rank: float,
    ) -> FriedmanLevelSummary:
        values = frame[variable]
        return FriedmanLevelSummary(
            variable=variable,
            level_index=level_index,
            level_label=level_label,
            n=int(len(values)),
            median=float(values.median()),
            mean_rank=mean_rank,
            mean=float(values.mean()),
            sd=float(values.std(ddof=1)),
        )


def _as_finite_float(value: Any, label: str) -> float:
    scalar = float(np.asarray(value).squeeze())
    if not np.isfinite(scalar):
        raise ValueError(f"Friedman test produced non-finite {label}.")
    return scalar


def _has_row_ties(matrix: np.ndarray) -> bool:
    return any(len(np.unique(row)) < len(row) for row in matrix)


Step.register_type(FriedmanStep.step_type, FriedmanStep)
