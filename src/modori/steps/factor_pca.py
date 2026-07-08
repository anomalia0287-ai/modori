from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
import warnings

import numpy as np
import pandas as pd
from factor_analyzer import FactorAnalyzer
from factor_analyzer.factor_analyzer import (
    calculate_bartlett_sphericity,
    calculate_kmo,
)

from modori.core import Dataset, Measure, PipelineContext, Step, StepResult
from modori.factor_pca_results import (
    BartlettSphericityResult,
    FactorPcaComponent,
    FactorPcaLoading,
    FactorPcaResult,
    KmoResult,
    ParallelAnalysisResult,
)


_SUPPORTED_MEASURES = {Measure.SCALE, Measure.ORDINAL}
_SUPPORTED_METHODS = {"pca", "efa"}
_SUPPORTED_MISSING_POLICIES = {"listwise"}
_SUPPORTED_EFA_ROTATIONS = {"none", "varimax"}
_SUPPORTED_EFA_EXTRACTION_METHODS = {"minres"}
_PARALLEL_DEFAULTS = {"seed": 20260707, "iterations": 100, "percentile": 95.0}


@dataclass
class FactorPcaStep(Step):
    step_type = "stats.factor_pca"
    produces_analysis = True
    CURRENT_SCHEMA_VERSION = 1
    CONTRACT_PARAM_EXAMPLES = {
        "current": {
            "schema_version": 1,
            "variables": ["q1", "q2", "q3"],
            "method": "pca",
            "missing_policy": "listwise",
            "rotation": "none",
        },
        "newer": {"schema_version": 999, "variables": ["q1", "q2", "q3"]},
        "unknown_current": {
            "schema_version": 1,
            "variables": ["q1", "q2", "q3"],
            "method": "pca",
            "missing_policy": "listwise",
            "rotation": "none",
            "extra": "bad",
        },
    }

    @classmethod
    def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
        version = params.get("schema_version")
        if version is None:
            raise ValueError("factor_pca params require schema_version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError("schema_version must be an integer")
        if version > cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("factor_pca params use a newer schema_version")
        if version == cls.CURRENT_SCHEMA_VERSION:
            return params
        raise ValueError(f"unsupported factor_pca schema_version: {version}")

    @classmethod
    def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
        allowed = {
            "schema_version",
            "variables",
            "method",
            "missing_policy",
            "rotation",
            "factor_count",
            "extraction_method",
            "parallel_analysis",
        }
        unknown = set(params) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unknown factor_pca params: {names}")
        if params.get("schema_version") != cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("factor_pca params were not migrated to the current schema")

        variables = cls._validate_variables(params.get("variables"))
        method = params.get("method")
        if method not in _SUPPORTED_METHODS:
            raise ValueError("factor_pca method must be pca or efa")
        method = str(method)

        missing_policy = str(params.get("missing_policy", "listwise"))
        if missing_policy not in _SUPPORTED_MISSING_POLICIES:
            raise ValueError("factor_pca missing_policy currently supports listwise only")

        rotation = str(params.get("rotation", "none"))
        if method == "pca" and rotation != "none":
            raise ValueError("PCA rotation currently supports none only")
        if method == "efa" and rotation not in _SUPPORTED_EFA_ROTATIONS:
            raise ValueError("factor_pca rotation must be none or varimax")

        extraction_method = cls._validate_extraction_method(params, method)
        factor_count = cls._validate_factor_count(params, method, len(variables))
        parallel = cls._validate_parallel_analysis(params.get("parallel_analysis", {}))
        return {
            "schema_version": cls.CURRENT_SCHEMA_VERSION,
            "variables": variables,
            "method": method,
            "missing_policy": missing_policy,
            "rotation": rotation,
            "factor_count": factor_count,
            "extraction_method": extraction_method,
            "parallel_analysis": parallel,
        }

    @staticmethod
    def _validate_variables(value: object) -> list[str]:
        if (
            not isinstance(value, list)
            or len(value) < 3
            or not all(isinstance(variable, str) and variable for variable in value)
        ):
            raise ValueError("factor_pca variables must contain at least three keys")
        if len(set(value)) != len(value):
            raise ValueError("factor_pca variables must not contain duplicate values (중복).")
        return list(value)

    @staticmethod
    def _validate_extraction_method(
        params: Mapping[str, object],
        method: str,
    ) -> str | None:
        raw = params.get("extraction_method")
        if method == "pca":
            if raw is not None:
                raise ValueError("PCA does not support extraction_method")
            return None
        extraction_method = "minres" if raw is None else str(raw)
        if extraction_method not in _SUPPORTED_EFA_EXTRACTION_METHODS:
            raise ValueError("factor_pca extraction_method currently supports minres only")
        return extraction_method

    @staticmethod
    def _validate_factor_count(
        params: Mapping[str, object],
        method: str,
        variable_count: int,
    ) -> int | None:
        raw = params.get("factor_count")
        if method == "pca":
            if raw is not None:
                raise ValueError("PCA does not support factor_count")
            return None
        if not isinstance(raw, int) or isinstance(raw, bool):
            raise ValueError("EFA factor_count must be an integer")
        if raw < 1 or raw >= variable_count:
            raise ValueError("EFA factor_count must be between 1 and variables - 1")
        return raw

    @staticmethod
    def _validate_parallel_analysis(value: object) -> dict[str, object]:
        if value is None:
            value = {}
        if not isinstance(value, Mapping):
            raise ValueError("parallel_analysis must be an object")
        unknown = set(value) - set(_PARALLEL_DEFAULTS)
        if unknown:
            names = ", ".join(sorted(str(key) for key in unknown))
            raise ValueError(f"unknown parallel_analysis params: {names}")
        merged = dict(_PARALLEL_DEFAULTS)
        merged.update(value)
        seed = merged["seed"]
        iterations = merged["iterations"]
        percentile = merged["percentile"]
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("parallel_analysis seed must be an integer")
        if not isinstance(iterations, int) or isinstance(iterations, bool):
            raise ValueError("parallel_analysis iterations must be an integer")
        if iterations < 1:
            raise ValueError("parallel_analysis iterations must be positive")
        if not isinstance(percentile, int | float) or isinstance(percentile, bool):
            raise ValueError("parallel_analysis percentile must be numeric")
        percentile = float(percentile)
        if not 0.0 < percentile <= 100.0:
            raise ValueError("parallel_analysis percentile must be in (0, 100]")
        return {"seed": seed, "iterations": iterations, "percentile": percentile}

    def compute(self, ctx: PipelineContext) -> StepResult:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return StepResult(analysis=self._compute_result(ctx, params))

    def reads(self) -> set[str]:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return set(str(variable) for variable in params["variables"])

    def writes(self) -> set[str]:
        return {self.id}

    def provenance(self) -> str:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        variables = ", ".join(str(variable) for variable in params["variables"])
        return f"factor/PCA analysis for {variables}"

    def _compute_result(
        self,
        ctx: PipelineContext,
        params: dict[str, object],
    ) -> FactorPcaResult:
        dataset = ctx.dataset
        variables = [str(variable) for variable in params["variables"]]
        self._validate_dataset(dataset, variables)

        source_frame = dataset.frame_for_compute(variables)
        n_total = int(len(source_frame))
        frame = source_frame.dropna(axis=0, how="any").copy()
        n_used = int(len(frame))
        n_excluded = n_total - n_used
        frame = self._numeric_frame(frame, variables)
        self._validate_nonzero_variance(frame, variables)
        self._validate_complete_case_count(frame, len(variables))

        corr = self._correlation_matrix(frame)
        eigenvalues, eigenvectors = self._pca_eigendecomposition(corr)
        kmo = self._kmo(frame, variables)
        bartlett = self._bartlett(frame)
        parallel = self._parallel_analysis(frame, eigenvalues, params)

        method = str(params["method"])
        if method == "pca":
            components, loadings, communalities, uniquenesses = self._pca_payload(
                dataset,
                variables,
                eigenvalues,
                eigenvectors,
            )
            title_ko = "주성분분석"
        else:
            components, loadings, communalities, uniquenesses = self._efa_payload(
                dataset,
                variables,
                frame,
                factor_count=int(params["factor_count"]),
                rotation=str(params["rotation"]),
                extraction_method=str(params["extraction_method"]),
            )
            title_ko = "탐색적 요인분석"

        warnings_ko = self._warnings(n_excluded)
        notes_ko = (
            "KMO와 Bartlett 검정은 요인분석 적합성 진단이며 구성개념을 자동으로 입증하지 않는다.",
            "평행분석 제안 수는 보조 기준이며 연구자가 이론과 문항 내용을 함께 판단해야 한다.",
            "중앙 차트 렌더링 훅이 없어 요인/PCA 차트는 아직 생성하지 않는다.",
        )
        return FactorPcaResult(
            analysis_key="factor_pca",
            title_ko=title_ko,
            method=method,
            variables=tuple(variables),
            variable_labels={
                variable: dataset.variables[variable].label or variable
                for variable in variables
            },
            n_total=n_total,
            n_used=n_used,
            n_excluded=n_excluded,
            missing_policy=str(params["missing_policy"]),
            rotation=str(params["rotation"]),
            factor_count=params["factor_count"],
            extraction_method=params["extraction_method"],
            components=components,
            loadings=loadings,
            communalities=communalities,
            uniquenesses=uniquenesses,
            kmo=kmo,
            bartlett=bartlett,
            parallel_analysis=parallel,
            warnings_ko=warnings_ko,
            notes_ko=notes_ko,
            apa_template_id=None,
            chart_spec=None,
            no_canonical_chart_reason_ko=(
                "요인/PCA ChartSpec의 중앙 렌더링 훅이 아직 연결되지 않아 "
                "차트를 생성하지 않는다."
            ),
        )

    @staticmethod
    def _validate_dataset(dataset: Dataset, variables: list[str]) -> None:
        if dataset.df.empty:
            raise ValueError("데이터셋이 비어 있어 요인/PCA 분석을 실행할 수 없습니다.")
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
            raise ValueError(f"요인/PCA 변수는 척도 또는 서열이어야 합니다: {names}")

    @staticmethod
    def _numeric_frame(frame: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
        numeric = frame.copy()
        for variable in variables:
            try:
                numeric[variable] = pd.to_numeric(
                    numeric[variable],
                    errors="raise",
                ).astype(float)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"요인/PCA 변수는 숫자여야 합니다: {variable}") from exc
            if len(numeric[variable]) and not np.all(
                np.isfinite(numeric[variable].to_numpy(dtype=float))
            ):
                raise ValueError(f"요인/PCA 변수는 유한한 숫자여야 합니다: {variable}")
        return numeric

    @staticmethod
    def _validate_nonzero_variance(frame: pd.DataFrame, variables: list[str]) -> None:
        zero_variance = [
            variable for variable in variables if frame[variable].nunique(dropna=True) < 2
        ]
        if zero_variance:
            names = ", ".join(zero_variance)
            raise ValueError(f"요인/PCA 변수는 0이 아닌 분산이 필요합니다: {names}")

    @staticmethod
    def _validate_complete_case_count(frame: pd.DataFrame, variable_count: int) -> None:
        minimum = max(5, variable_count + 1)
        if len(frame) < minimum:
            raise ValueError(
                "요인/PCA 분석은 최소 "
                f"{minimum}개의 완전한 관측치가 필요합니다."
            )

    @staticmethod
    def _correlation_matrix(frame: pd.DataFrame) -> np.ndarray:
        corr = frame.corr().to_numpy(dtype=float)
        if corr.shape[0] != corr.shape[1] or not np.all(np.isfinite(corr)):
            raise ValueError("요인/PCA 상관행렬을 유한한 정방행렬로 만들 수 없습니다.")
        if np.linalg.matrix_rank(corr) < corr.shape[0]:
            raise ValueError("요인/PCA 상관행렬이 특이행렬이라 분석을 중단합니다.")
        return corr

    @staticmethod
    def _pca_eigendecomposition(corr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        eigenvalues, eigenvectors = np.linalg.eigh(corr)
        order = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[order]
        eigenvectors = eigenvectors[:, order]
        for index in range(eigenvectors.shape[1]):
            column = eigenvectors[:, index]
            anchor = int(np.argmax(np.abs(column)))
            if column[anchor] < 0:
                eigenvectors[:, index] = -column
        return eigenvalues, eigenvectors

    @staticmethod
    def _kmo(frame: pd.DataFrame, variables: list[str]) -> KmoResult:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", RuntimeWarning)
                warnings.simplefilter("error", UserWarning)
                per_variable, overall = calculate_kmo(frame)
        except Exception as exc:
            raise ValueError(f"KMO 진단을 안전하게 산출할 수 없습니다: {exc}") from exc
        per_variable = np.asarray(per_variable, dtype=float)
        overall_value = _as_finite_float(overall, "KMO overall")
        if not np.all(np.isfinite(per_variable)):
            raise ValueError("KMO 변수별 값이 유한하지 않아 분석을 중단합니다.")
        return KmoResult(
            overall=overall_value,
            per_variable={
                variable: float(value)
                for variable, value in zip(variables, per_variable, strict=True)
            },
        )

    @staticmethod
    def _bartlett(frame: pd.DataFrame) -> BartlettSphericityResult:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", RuntimeWarning)
                warnings.simplefilter("error", UserWarning)
                chi_square, p_value = calculate_bartlett_sphericity(frame)
        except Exception as exc:
            raise ValueError(
                f"Bartlett 구형성 검정을 안전하게 산출할 수 없습니다: {exc}"
            ) from exc
        return BartlettSphericityResult(
            chi_square=_as_finite_float(chi_square, "Bartlett chi-square"),
            p_value=_as_finite_float(p_value, "Bartlett p-value"),
        )

    @staticmethod
    def _parallel_analysis(
        frame: pd.DataFrame,
        eigenvalues: np.ndarray,
        params: Mapping[str, object],
    ) -> ParallelAnalysisResult:
        settings = params["parallel_analysis"]
        if not isinstance(settings, Mapping):
            raise ValueError("parallel_analysis settings were not validated")
        seed = int(settings["seed"])
        iterations = int(settings["iterations"])
        percentile = float(settings["percentile"])
        rng = np.random.default_rng(seed)
        random_eigenvalues = np.empty((iterations, len(frame.columns)), dtype=float)
        for index in range(iterations):
            random_frame = pd.DataFrame(
                rng.normal(size=frame.shape),
                columns=frame.columns,
            )
            corr = random_frame.corr().to_numpy(dtype=float)
            random_eigenvalues[index], _ = FactorPcaStep._pca_eigendecomposition(corr)

        random_mean = random_eigenvalues.mean(axis=0)
        random_percentile = np.percentile(random_eigenvalues, percentile, axis=0)
        suggested = int(np.sum(eigenvalues > random_percentile))
        return ParallelAnalysisResult(
            seed=seed,
            iterations=iterations,
            percentile=percentile,
            suggested_factor_count=suggested,
            observed_eigenvalues=_float_tuple(eigenvalues),
            random_mean_eigenvalues=_float_tuple(random_mean),
            random_percentile_eigenvalues=_float_tuple(random_percentile),
        )

    @staticmethod
    def _pca_payload(
        dataset: Dataset,
        variables: list[str],
        eigenvalues: np.ndarray,
        eigenvectors: np.ndarray,
    ) -> tuple[
        tuple[FactorPcaComponent, ...],
        tuple[FactorPcaLoading, ...],
        dict[str, float],
        dict[str, float],
    ]:
        explained = eigenvalues / len(variables)
        cumulative = np.cumsum(explained)
        components = tuple(
            FactorPcaComponent(
                name=f"PC{index + 1}",
                eigenvalue=float(eigenvalue),
                explained_variance_ratio=float(explained[index]),
                cumulative_variance_ratio=float(cumulative[index]),
            )
            for index, eigenvalue in enumerate(eigenvalues)
        )
        loadings_matrix = eigenvectors * np.sqrt(np.maximum(eigenvalues, 0.0))
        loadings = _loading_rows(
            dataset,
            variables,
            [component.name for component in components],
            loadings_matrix,
        )
        return components, loadings, {}, {}

    @staticmethod
    def _efa_payload(
        dataset: Dataset,
        variables: list[str],
        frame: pd.DataFrame,
        *,
        factor_count: int,
        rotation: str,
        extraction_method: str,
    ) -> tuple[
        tuple[FactorPcaComponent, ...],
        tuple[FactorPcaLoading, ...],
        dict[str, float],
        dict[str, float],
    ]:
        dependency_rotation = None if rotation == "none" else rotation
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                analyzer = FactorAnalyzer(
                    n_factors=factor_count,
                    rotation=dependency_rotation,
                    method=extraction_method,
                )
                analyzer.fit(frame)
        except Exception as exc:
            raise ValueError(f"EFA 산출에 실패했습니다: {exc}") from exc

        factor_names = [f"F{index + 1}" for index in range(factor_count)]
        components = tuple(FactorPcaComponent(name=name) for name in factor_names)
        loadings = _loading_rows(dataset, variables, factor_names, analyzer.loadings_)
        communalities = {
            variable: float(value)
            for variable, value in zip(
                variables,
                analyzer.get_communalities(),
                strict=True,
            )
        }
        uniquenesses = {
            variable: float(value)
            for variable, value in zip(
                variables,
                analyzer.get_uniquenesses(),
                strict=True,
            )
        }
        if not np.all(np.isfinite(analyzer.loadings_)):
            raise ValueError("EFA 적재량이 유한하지 않아 분석을 중단합니다.")
        return components, loadings, communalities, uniquenesses

    @staticmethod
    def _warnings(n_excluded: int) -> tuple[str, ...]:
        warnings_ko = [
            "요인/PCA 결과는 탐색적 근거이며 구성개념을 자동으로 단정하지 않는다.",
        ]
        if n_excluded:
            warnings_ko.append(f"listwise 결측 처리로 {n_excluded}건을 제외했다.")
        return tuple(warnings_ko)


def _loading_rows(
    dataset: Dataset,
    variables: list[str],
    dimensions: list[str],
    matrix: np.ndarray,
) -> tuple[FactorPcaLoading, ...]:
    if not np.all(np.isfinite(matrix)):
        raise ValueError("요인/PCA 적재량이 유한하지 않아 분석을 중단합니다.")
    rows = []
    for variable_index, variable in enumerate(variables):
        for dimension_index, dimension in enumerate(dimensions):
            rows.append(
                FactorPcaLoading(
                    variable=variable,
                    variable_label=dataset.variables[variable].label or variable,
                    dimension=dimension,
                    loading=float(matrix[variable_index, dimension_index]),
                )
            )
    return tuple(rows)


def _float_tuple(values: np.ndarray) -> tuple[float, ...]:
    return tuple(float(value) for value in values)


def _as_finite_float(value: Any, label: str) -> float:
    scalar = float(np.asarray(value).squeeze())
    if not np.isfinite(scalar):
        raise ValueError(f"Factor/PCA produced non-finite {label}; inference is undefined.")
    return scalar


Step.register_type(FactorPcaStep.step_type, FactorPcaStep)
