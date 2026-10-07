"""Frozen C3 Direct numerical baseline; no successor activation allowed."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from tests.api.test_f593_f4 import design, supported

BASELINE = cast(
    dict[str, Any],
    json.loads(
        (Path(__file__).parents[1] / "golden/direct_a3_r1_c3_numerical_parity.json").read_text(
            encoding="utf-8"
        )
    ),
)


def direct_projection() -> dict[str, Any]:
    result = design(BASELINE["request"])
    integration = result["native_design"]["automatic_group_mode_integration"]
    return {
        "checks": supported(result),
        "integration": {k: integration[k] for k in BASELINE["expected"]["integration"]},
        "overall_status": result["overall_status"],
    }


def test_direct_c3_exact_numerical_schedule_parity() -> None:
    actual = direct_projection()
    assert actual == BASELINE["expected"]
    assert len(actual["checks"]) == 7
    assert len(actual["integration"]["unsupported_required_check_ids"]) == 7
    assert len(actual["integration"]["incomplete_required_check_ids"]) == 1
    assert len(actual["integration"]["required_check_ids"]) == 17
    assert len(actual["integration"]["not_required_check_ids"]) == 2
    assert not any("RC3" in str(c) for c in actual["checks"])
