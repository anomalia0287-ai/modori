from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from modori.core import Dataset, Measure, PipelineContext, Step, StepResult
from modori.correlation_results import CorrelationPairResult, CorrelationResult


_SUPPORTED_MEASURES = {Measure.SCALE, Measure.ORDINAL}
_SUPPORTED_METHODS = {"auto", "pearson", "spearman"}
_SUPPORTED_MISSING_POLICIES = {"pairwise", "listwise"}
_SUPPORTED_P_ADJUST = {"none"}


@dataclass
class CorrelationStep(Step):
    step_type = "stats.correlation"
    produces_analysis = True
    CURRENT_SCHEMA_VERSION = 1
    CONTRACT_PARAM_EXAMPLES = {
        "current": {
            "schema_version": 1,
            "variables": ["x", "y"],
            "method": "auto",
            "missing_policy": "pairwise",
            "p_adjust": "none",
        },
        "newer": {"schema_version": 999, "variables": ["x", "y"]},
        "unknown_current": {
            "schema_version": 1,
            "variables": ["x", "y"],
            "extra": "bad",
        },
    }

    @classmethod
    def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
        version = params.get("schema_version")
        if version is None:
            raise ValueError("correlation params require schema_version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError("schema_version must be an integer")
        if version > cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("correlation params use a newer schema_version")
        if version == 1:
            return params
        raise ValueError(f"unsupported correlation schema_version: {version}")

    @classmethod
    def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
        allowed = {
            "schema_version",
            "variables",
            "pairs",
            "method",
            "missing_policy",
            "p_adjust",
        }
        unknown = set(params) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unknown correlation params: {names}")
        if params.get("schema_version") != cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("correlation params were not migrated to the current schema")

        has_variables = "variables" in params
        has_pairs = "pairs" in params
        if has_variables == has_pairs:
            raise ValueError("correlation params require exactly one of variables or pairs")

        method = str(params.get("method", "auto"))
        if method not in _SUPPORTED_METHODS:
            raise ValueError("correlation method must be auto, pearson, or spearman")
        missing_policy = str(params.get("missing_policy", "pairwise"))
        if missing_policy not in _SUPPORTED_MISSING_POLICIES:
            raise ValueError("correlation missing_policy must be pairwise or listwise")
        p_adjust = str(params.get("p_adjust", "none"))
        if p_adjust not in _SUPPORTED_P_ADJUST:
            raise ValueError("correlation p_adjust currently supports none only")

        if has_variables:
            variables = params.get("variables")
            if (
                not isinstance(variables, list)
                or len(variables) < 2
                or not all(isinstance(variable, str) for variable in variables)
            ):
                raise ValueError("variables must contain at least two variable keys")
            if len(set(variables)) != len(variables):
                raise ValueError("correlation variables must be unique")
            pairs = [list(pair) for pair in combinations(variables, 2)]
        else:
            raw_pairs = params.get("pairs")
            if not isinstance(raw_pairs, list) or not raw_pairs:
                raise ValueError("pairs must be a non-empty list of variable key pairs")
            pairs = []
            for raw_pair in raw_pairs:
                if (
                    not isinstance(raw_pair, list | tuple)
                    or len(raw_pair) != 2
                    or not all(isinstance(variable, str) for variable in raw_pair)
                ):
                    raise ValueError("pairs must be variable key pairs")
                x, y = raw_pair
                if x == y:
                    raise ValueError("correlation pair variables must differ")
                pairs.append([x, y])
            if len({tuple(pair) for pair in pairs}) != len(pairs):
                raise ValueError("correlation pairs must be unique")
            variables = list(dict.fromkeys(variable for pair in pairs for variable in pair))

        return {
            "schema_version": cls.CURRENT_SCHEMA_VERSION,
            "variables": list(variables),
            "pairs": pairs,
            "method": method,
            "missing_policy": missing_policy,
            "p_adjust": p_adjust,
        }

    def compute(self, ctx: PipelineContext) -> StepResult:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        result = self._compute_result(ctx, params)
        return StepResult(analysis=result)

    def reads(self) -> set[str]:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return set(params["variables"])

    def writes(self) -> set[str]:
        return {self.id}

    def provenance(self) -> str:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        variables = ", ".join(str(variable) for variable in params["variables"])
        return f"correlation analysis for {variables}"

    def _compute_result(
        self,
        ctx: PipelineContext,
        params: dict[str, object],
    ) -> CorrelationResult:
        dataset = ctx.dataset
        variables = [str(variable) for variable in params["variables"]]
        pairs = [tuple(str(variable) for variable in pair) for pair in params["pairs"]]
        self._validate_dataset(dataset, variables)

        frame = dataset.frame_for_compute(variables)
        pair_results = tuple(
            self._compute_pair(
                dataset=dataset,
                frame=frame,
                pair=pair,
                method_policy=str(params["method"]),
                missing_policy=str(params["missing_policy"]),
            )
            for pair in pairs
        )
        warnings_ko = self._warnings(pair_results)
        notes_ko = (
            "p_adjust가 none이므로 p-value는 조정하지 않은 원값이다.",
            "중앙 차트 렌더링 훅이 없어 표준 상관행렬 차트는 아직 생성하지 않는다.",
        )
        return CorrelationResult(
            analysis_key="correlation",
            title_ko="상관분석",
            variables=tuple(variables),
            method_policy=str(params["method"]),
            missing_policy=str(params["missing_policy"]),
            n_total=int(len(frame)),
            pairs=pair_results,
            warnings_ko=warnings_ko,
            notes_ko=notes_ko,
            apa_template_id=None,
            chart_spec=None,
            no_canonical_chart_reason_ko=(
                "상관행렬 ChartSpec의 중앙 렌더링 훅이 아직 연결되지 않아 차트를 생성하지 않는다."
            ),
        )

    @staticmethod
    def _validate_dataset(dataset: Dataset, variables: list[str]) -> None:
        if dataset.df.empty:
            raise ValueError("데이터셋이 비어 있어 상관분석을 실행할 수 없습니다.")

        missing = [key for key in variables if key not in dataset.variables]
        if missing:
            names = ", ".join(missing)
            raise ValueError(f"데이터셋에 없는 변수: {names}")

        unsupported = [
            key
            for key in variables
            if dataset.variables[key].measure not in _SUPPORTED_MEASURES
        ]
        if unsupported:
            names = ", ".join(unsupported)
            raise ValueError(f"상관분석 변수는 척도 또는 서열이어야 합니다: {names}")

    def _compute_pair(
        self,
        *,
        dataset: Dataset,
        frame: pd.DataFrame,
        pair: tuple[str, str],
        method_policy: str,
        missing_policy: str,
    ) -> CorrelationPairResult:
        x, y = pair
        pair_frame = self._pair_frame(frame, [x, y], missing_policy)
        n = int(len(pair_frame))
        excluded_n = int(len(frame) - n)
        if n < 3:
            raise ValueError("상관분석은 변수쌍마다 최소 3개의 완전한 관측치가 필요합니다.")

        x_values = self._numeric_series(pair_frame[x], x)
        y_values = self._numeric_series(pair_frame[y], y)
        self._validate_nonzero_variance(x_values, x)
        self._validate_nonzero_variance(y_values, y)

        method = self._method_for_pair(dataset, x, y, method_policy)
        if method == "pearson":
            statistic = stats.pearsonr(x_values, y_values)
            statistic_label = "r"
            method_details = {"method": "scipy_pearsonr"}
            warnings_ko: tuple[str, ...] = ()
        else:
            statistic = stats.spearmanr(x_values, y_values)
            statistic_label = "rho"
            x_ties = _has_ties(x_values.to_numpy(dtype=float))
            y_ties = _has_ties(y_values.to_numpy(dtype=float))
            method_details = {
                "method": "scipy_spearmanr",
                "ties_present": bool(x_ties or y_ties),
                "x_ties_present": x_ties,
                "y_ties_present": y_ties,
                "p_value_method": "scipy_asymptotic",
            }
            warnings_ko = (
                "Spearman 상관은 동점 rank를 SciPy spearmanr 정책으로 처리했다. "
                "동점이 많은 자료의 p-value는 소프트웨어별로 달라질 수 있다.",
            ) if x_ties or y_ties else ()

        coefficient = _as_finite_float(statistic.statistic, f"{method} coefficient")
        p_value = _as_finite_float(statistic.pvalue, f"{method} p-value")
        return CorrelationPairResult(
            x=x,
            y=y,
            x_label=dataset.variables[x].label or x,
            y_label=dataset.variables[y].label or y,
            method=method,
            statistic_label=statistic_label,
            coefficient=coefficient,
            p_value=p_value,
            n=n,
            excluded_n=excluded_n,
            warnings_ko=warnings_ko,
            method_details=method_details,
        )

    @staticmethod
    def _pair_frame(
        frame: pd.DataFrame,
        variables: list[str],
        missing_policy: str,
    ) -> pd.DataFrame:
        if missing_policy == "pairwise":
            return frame.loc[:, variables].dropna(axis=0, how="any")
        if missing_policy == "listwise":
            return frame.dropna(axis=0, how="any").loc[:, variables]
        raise ValueError("correlation missing_policy must be pairwise or listwise")

    @staticmethod
    def _numeric_series(series: pd.Series, key: str) -> pd.Series:
        try:
            values = pd.to_numeric(series, errors="raise").astype(float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"상관분석 변수는 숫자여야 합니다: {key}") from exc
        if len(values) and not np.all(np.isfinite(values.to_numpy(dtype=float))):
            raise ValueError(f"상관분석 변수는 유한한 숫자여야 합니다: {key}")
        return values

    @staticmethod
    def _validate_nonzero_variance(values: pd.Series, key: str) -> None:
        if values.nunique(dropna=True) < 2:
            raise ValueError(f"상관분석 변수는 0이 아닌 분산이 필요합니다: {key}")

    @staticmethod
    def _method_for_pair(
        dataset: Dataset,
        x: str,
        y: str,
        method_policy: str,
    ) -> str:
        if method_policy == "pearson":
            if (
                dataset.variables[x].measure is not Measure.SCALE
                or dataset.variables[y].measure is not Measure.SCALE
            ):
                raise ValueError("Pearson correlation requires two scale variables.")
            return "pearson"
        if method_policy == "spearman":
            return method_policy
        if (
            dataset.variables[x].measure is Measure.ORDINAL
            or dataset.variables[y].measure is Measure.ORDINAL
        ):
            return "spearman"
        return "pearson"

    @staticmethod
    def _warnings(pairs: tuple[CorrelationPairResult, ...]) -> tuple[str, ...]:
        if len(pairs) <= 1:
            return ()
        return (
            "상관행렬은 여러 쌍을 동시에 검토하므로 다중비교 가능성을 함께 해석해야 한다.",
        )


def _as_finite_float(value: Any, label: str) -> float:
    scalar = float(np.asarray(value).squeeze())
    if not np.isfinite(scalar):
        raise ValueError(f"Correlation produced non-finite {label}; inference is undefined.")
    return scalar


def _has_ties(values: np.ndarray) -> bool:
    return bool(len(np.unique(values)) < len(values))


Step.register_type(CorrelationStep.step_type, CorrelationStep)
