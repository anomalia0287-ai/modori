from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any

import pandas as pd

from modori.core import Measure

_MAX_UNIQUE_VALUES = 200
_UNIFY_SUFFIX = "_정리"
_SUGGESTION_SUMMARY = "'{column}' 열에서 표기만 다른 값 {count}묶음을 감지했습니다."
_PREVIEW_CLUSTER_LIMIT = 3


@dataclass(frozen=True)
class ValueVariant:
    value: str
    count: int


@dataclass(frozen=True)
class ValueCluster:
    canonical: str
    variants: tuple[ValueVariant, ...]

    @property
    def total_count(self) -> int:
        return sum(variant.count for variant in self.variants)

    @property
    def mapping(self) -> dict[str, str]:
        return {
            variant.value: self.canonical
            for variant in self.variants
            if variant.value != self.canonical
        }


def fingerprint(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value)).strip()
    text = "".join(text.split())
    return text.casefold()


def _cleaned(value: str) -> str:
    return unicodedata.normalize("NFKC", str(value)).strip()


def value_clusters(series: pd.Series) -> list[ValueCluster]:
    non_missing = series.dropna()
    counts: dict[str, int] = {}
    first_seen: dict[str, int] = {}
    for position, raw in enumerate(non_missing):
        value = str(raw)
        if not value.strip():
            continue
        counts[value] = counts.get(value, 0) + 1
        first_seen.setdefault(value, position)
    if len(counts) > _MAX_UNIQUE_VALUES:
        return []

    grouped: dict[str, list[str]] = {}
    for value in counts:
        key = fingerprint(value)
        if not key:
            continue
        grouped.setdefault(key, []).append(value)

    clusters: list[ValueCluster] = []
    for values in grouped.values():
        if len(values) < 2:
            continue
        ordered = sorted(values, key=lambda value: (-counts[value], first_seen[value]))
        variants = tuple(ValueVariant(value=value, count=counts[value]) for value in ordered)
        clusters.append(
            ValueCluster(
                canonical=_cleaned(ordered[0]),
                variants=variants,
            )
        )
    clusters.sort(key=lambda cluster: (-cluster.total_count, cluster.canonical))
    return clusters


def unification_suggestions(dataset: Any, *, suffix: str = _UNIFY_SUFFIX) -> list[dict[str, Any]]:
    if dataset is None:
        return []
    suggestions: list[dict[str, Any]] = []
    for name, variable in dataset.variables.items():
        if variable.measure not in (Measure.NOMINAL, Measure.ORDINAL):
            continue
        output = f"{name}{suffix}"
        if output in dataset.variables:
            continue
        series = dataset.df[name]
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
            continue
        clusters = value_clusters(series)
        if not clusters:
            continue
        mapping: dict[str, str] = {}
        for cluster in clusters:
            mapping.update(cluster.mapping)
        preview = " / ".join(
            f"{cluster.canonical} ← "
            + ", ".join(
                variant.value
                for variant in cluster.variants
                if variant.value != cluster.canonical
            )
            for cluster in clusters[:_PREVIEW_CLUSTER_LIMIT]
        )
        suggestions.append(
            {
                "column": str(name),
                "cluster_count": len(clusters),
                "summary": _SUGGESTION_SUMMARY.format(column=name, count=len(clusters)),
                "preview": preview,
                "mapping": mapping,
                "output": output,
            }
        )
    return suggestions
