import pandas as pd

from modori.core import Dataset, Measure, Variable


def _variable(
    name: str,
    *,
    measure: Measure,
    dtype: str,
    value_labels: dict[float, str] | None = None,
    missing_values: list[float] | None = None,
) -> Variable:
    return Variable(
        name=name,
        label=name,
        measure=measure,
        value_labels=value_labels or {},
        missing_values=missing_values or [],
        dtype=dtype,
        origin_step_id="import",
    )


def test_value_recode_inventory_lists_eligible_string_categories_by_count() -> None:
    from modori.value_inventory import value_recode_inventory

    dataset = Dataset(
        df=pd.DataFrame(
            {
                "지역": ["서울", "부산", "서울", "", None],
                "점수": [1, 2, 3, 4, 5],
            }
        ),
        variables={
            "지역": _variable("지역", measure=Measure.NOMINAL, dtype="string"),
            "점수": _variable("점수", measure=Measure.SCALE, dtype="int"),
        },
    )

    inventory = {entry["column"]: entry for entry in value_recode_inventory(dataset)}

    assert inventory["지역"]["eligible"] is True
    assert inventory["지역"]["output"] == "지역_수정"
    assert inventory["지역"]["values"] == [
        {"value": "서울", "count": 2},
        {"value": "부산", "count": 1},
    ]
    assert inventory["점수"]["eligible"] is False
    assert inventory["점수"]["reason"] == "숫자 변수는 아직 값 수정을 지원하지 않습니다."


def test_value_recode_inventory_rejects_labelled_columns_visibly() -> None:
    from modori.value_inventory import value_recode_inventory

    dataset = Dataset(
        df=pd.DataFrame({"group": [1, 2, 1]}),
        variables={
            "group": _variable(
                "group",
                measure=Measure.NOMINAL,
                dtype="int",
                value_labels={1.0: "A", 2.0: "B"},
            )
        },
    )

    [entry] = value_recode_inventory(dataset)

    assert entry["eligible"] is False
    assert entry["reason"] == "값 라벨이 있는 변수는 아직 값 수정을 지원하지 않습니다."
