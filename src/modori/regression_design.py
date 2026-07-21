from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CategoricalEncoding:
    variable: str
    reference: str
    levels: tuple[str, ...]


@dataclass(frozen=True)
class InteractionSpec:
    first: str
    second: str

    @property
    def terms(self) -> tuple[str, str]:
        return (self.first, self.second)


@dataclass(frozen=True)
class TermMetadata:
    name: str
    term_type: str
    source_variable: str | None = None
    level: str | None = None
    reference_level: str | None = None
    components: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScaleTerm:
    variable: str
    name: str
    center: float | None


@dataclass(frozen=True)
class RegressionDesignMatrix:
    x_pred: pd.DataFrame
    term_metadata: dict[str, TermMetadata]
    scale_terms: dict[str, ScaleTerm]
    categorical_terms: dict[str, dict[str, str]]
    transformed_terms: dict[str, str]
    centers: dict[str, float]


def categorical_level_label(value: object) -> str:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not np.isfinite(value):
            raise ValueError("Categorical levels must be finite")
        if value.is_integer():
            return str(int(value))
        return str(value)
    return str(value)


def _level_label(value: object) -> str:
    return str(value)


def _finite_float(value: object, label: str, *, error_prefix: str) -> float:
    scalar = float(np.asarray(value).squeeze())
    if not np.isfinite(scalar):
        raise ValueError(f"{error_prefix} produced non-finite {label}.")
    return scalar


def build_regression_design_matrix(
    *,
    frame: pd.DataFrame,
    predictors: Sequence[str],
    categorical_encodings: Mapping[str, CategoricalEncoding],
    interactions: Sequence[InteractionSpec],
    center_scale_interactions: bool,
    error_prefix: str,
) -> RegressionDesignMatrix:
    centered_scale_variables = {
        term
        for interaction in interactions
        for term in interaction.terms
        if term not in categorical_encodings
    }
    if not center_scale_interactions:
        centered_scale_variables = set()

    columns: dict[str, pd.Series] = {}
    term_metadata: dict[str, TermMetadata] = {}
    scale_terms: dict[str, ScaleTerm] = {}
    categorical_terms: dict[str, dict[str, str]] = {}
    transformed_terms: dict[str, str] = {}
    centers: dict[str, float] = {}

    def add_column(name: str, values: pd.Series, metadata: TermMetadata) -> None:
        if name in columns:
            raise ValueError(f"{error_prefix} design term name collision: {name}")
        columns[name] = values.astype(float)
        term_metadata[name] = metadata

    for predictor in predictors:
        if predictor in categorical_encodings:
            encoding = categorical_encodings[predictor]
            observed = frame[predictor].map(_level_label)
            undeclared = sorted(set(observed.dropna()) - set(encoding.levels))
            if undeclared:
                levels = ", ".join(undeclared)
                raise ValueError(
                    f"{error_prefix} categorical predictor {predictor} observed levels "
                    f"not declared in encoding policy: {levels}"
                )
            categorical_terms[predictor] = {}
            for level in encoding.levels:
                if level == encoding.reference:
                    continue
                term_name = f"{predictor}[T.{level}]"
                categorical_terms[predictor][level] = term_name
                add_column(
                    term_name,
                    observed == level,
                    TermMetadata(
                        name=term_name,
                        term_type="categorical_level",
                        source_variable=predictor,
                        level=level,
                        reference_level=encoding.reference,
                        components=(predictor,),
                    ),
                )
            continue

        raw = pd.to_numeric(frame[predictor], errors="raise").astype(float)
        if predictor in centered_scale_variables:
            center = _finite_float(
                raw.mean(),
                f"mean for {predictor}",
                error_prefix=error_prefix,
            )
            term_name = f"{predictor}_centered"
            values = raw - center
            term_type = "scale_centered"
            centers[predictor] = center
        else:
            center = None
            term_name = predictor
            values = raw
            term_type = "scale"
        transformed_terms[predictor] = term_name
        scale_terms[predictor] = ScaleTerm(
            variable=predictor,
            name=term_name,
            center=center,
        )
        add_column(
            term_name,
            values,
            TermMetadata(
                name=term_name,
                term_type=term_type,
                source_variable=predictor,
                components=(predictor,),
            ),
        )

    for interaction in interactions:
        first, second = interaction.terms
        first_is_categorical = first in categorical_encodings
        second_is_categorical = second in categorical_encodings
        if not first_is_categorical and not second_is_categorical:
            first_term = scale_terms[first].name
            second_term = scale_terms[second].name
            term_name = f"{first_term}:{second_term}"
            add_column(
                term_name,
                columns[first_term] * columns[second_term],
                TermMetadata(
                    name=term_name,
                    term_type="interaction",
                    components=(first, second),
                ),
            )
            continue

        scale_var = second if first_is_categorical else first
        categorical_var = first if first_is_categorical else second
        scale_term = scale_terms[scale_var].name
        encoding = categorical_encodings[categorical_var]
        for level in encoding.levels:
            if level == encoding.reference:
                continue
            categorical_term = categorical_terms[categorical_var][level]
            term_name = f"{scale_term}:{categorical_term}"
            add_column(
                term_name,
                columns[scale_term] * columns[categorical_term],
                TermMetadata(
                    name=term_name,
                    term_type="interaction",
                    level=level,
                    reference_level=encoding.reference,
                    components=(scale_var, categorical_var),
                ),
            )

    return RegressionDesignMatrix(
        x_pred=pd.DataFrame(columns, index=frame.index),
        term_metadata=term_metadata,
        scale_terms=scale_terms,
        categorical_terms=categorical_terms,
        transformed_terms=transformed_terms,
        centers=centers,
    )
