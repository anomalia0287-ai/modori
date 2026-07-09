from __future__ import annotations

import numpy as np
import pytest

from modori.statistics_numerics import require_well_conditioned_correlation_matrix


def test_correlation_condition_error_describes_redundant_items_not_undefined_inference() -> None:
    correlation = np.array(
        [
            [1.0, 0.999999],
            [0.999999, 1.0],
        ]
    )

    with pytest.raises(ValueError) as exc_info:
        require_well_conditioned_correlation_matrix(
            correlation,
            label="McDonald's omega",
            max_condition_number=1e3,
        )

    message = str(exc_info.value)
    assert "nearly redundant" in message
    assert "factor/reliability estimates are unstable" in message
    assert "inference is undefined" not in message
