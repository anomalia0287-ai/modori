from __future__ import annotations

import pandas as pd

from modori.value_clustering import fingerprint, value_clusters


def test_fingerprint_normalizes_whitespace_width_and_case() -> None:
    assert fingerprint(" 서울 특별시 ") == fingerprint("서울특별시")
    assert fingerprint("ＡＢＣ") == fingerprint("abc")
    assert fingerprint("Seoul") == fingerprint("SEOUL")


def test_value_clusters_group_formatting_variants_only() -> None:
    series = pd.Series(
        ["서울특별시", "서울 특별시", "서울특별시 ", "부산광역시", "서울"]
    )

    clusters = value_clusters(series)

    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.canonical == "서울특별시"
    assert {variant.value for variant in cluster.variants} == {
        "서울특별시",
        "서울 특별시",
        "서울특별시 ",
    }
    assert cluster.mapping == {
        "서울 특별시": "서울특별시",
        "서울특별시 ": "서울특별시",
    }


def test_value_clusters_canonical_is_cleaned_most_frequent_variant() -> None:
    series = pd.Series(["중구 ", "중구 ", "중구", "중구 "])

    clusters = value_clusters(series)

    assert clusters[0].canonical == "중구"
    assert clusters[0].mapping == {"중구 ": "중구"}


def test_value_clusters_exclude_missing_and_blank_values() -> None:
    series = pd.Series(["서울", "서울 ", None, "", "   "])

    clusters = value_clusters(series)

    assert len(clusters) == 1
    assert {variant.value for variant in clusters[0].variants} == {"서울", "서울 "}


def test_value_clusters_respect_unique_value_cap() -> None:
    values = [f"값{index}" for index in range(201)] + ["값0 "]
    series = pd.Series(values)

    assert value_clusters(series) == []


def test_value_clusters_are_deterministically_ordered() -> None:
    series = pd.Series(
        ["a", "a ", "a", "b", "b ", "b", "b"]
    )

    clusters = value_clusters(series)

    assert [cluster.canonical for cluster in clusters] == ["b", "a"]


def test_unification_suggestions_cover_string_categorical_columns(tmp_path) -> None:
    from pathlib import Path

    from modori.core import Dataset, Pipeline
    from modori.steps import ImportStep
    from modori.value_clustering import unification_suggestions

    path = Path(tmp_path) / "regions.csv"
    path.write_text(
        "지역,인구\n서울특별시,100\n서울 특별시,200\n부산광역시,300\n",
        encoding="utf-8",
    )
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(id="import", title="Import", params={"path": str(path), "file_type": "csv"})
    )
    pipeline.recompute(dirty_from=None)

    suggestions = unification_suggestions(pipeline.current_dataset)

    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion["column"] == "지역"
    assert suggestion["cluster_count"] == 1
    assert suggestion["mapping"] == {"서울 특별시": "서울특별시"}
    assert "지역" in suggestion["summary"]
    assert suggestion["output"] == "지역_정리"


def test_unification_suggestions_skip_numeric_and_already_unified_columns(tmp_path) -> None:
    from pathlib import Path

    from modori.core import Dataset, Pipeline
    from modori.steps import ImportStep, UnifyValuesStep
    from modori.value_clustering import unification_suggestions

    path = Path(tmp_path) / "regions.csv"
    path.write_text(
        "지역,인구\n서울특별시,100\n서울 특별시,100\n",
        encoding="utf-8",
    )
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(id="import", title="Import", params={"path": str(path), "file_type": "csv"})
    )
    pipeline.add(
        UnifyValuesStep(
            id="transform:unify:지역",
            title="Unify",
            params={"column": "지역", "mapping": {"서울 특별시": "서울특별시"}},
        )
    )
    pipeline.recompute(dirty_from=None)

    assert unification_suggestions(pipeline.current_dataset) == []
