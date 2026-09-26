"""An executed check with missing operands must fail the report adapter."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any

import httpx
import pytest

from frp_master_connection.api.app import create_app
from frp_master_connection.reporting.multirow_substitutions import multirow_native_substitution
from tests.api.test_connector_materials import native_payload


@pytest.fixture(scope="module")
def native_multirow() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    # The fixture factory calls its own defaults route, so prepare outside the event loop.
    payload = native_payload("multi-row")

    async def prepared_run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app()), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/calculations/multi-row/design-check", json=payload
            )
            assert response.status_code == 200
            body: dict[str, Any] = response.json()
            return body

    native = asyncio.run(prepared_run())
    return native["calculation_result"]["results"], native["preview"]["visualization"]


@pytest.mark.parametrize(
    ("method", "fault", "expected"),
    [
        ("PIN_BEARING", "missing trace", "lacks equation_trace"),
        ("PIN_BEARING", "missing nominal value", "lacks quantity"),
        ("PIN_BEARING", "missing factor", "lacks scalar thread_factor"),
        ("PIN_BEARING", "missing layers", "lacks canonical layers"),
        ("PIN_BEARING", "ambiguous layer", "no unique canonical layer"),
        ("PIN_BEARING", "missing bolts", "lacks canonical bolts"),
        ("PIN_BEARING", "wrong bolt", "no unique canonical bolt"),
        ("INTERROW_ASCE_EQ_8_12", "missing pitches", "lacks physical pitches"),
        ("INTERROW_ASCE_EQ_8_12", "malformed pitch", "malformed pitch"),
        ("PIN_BEARING", "unknown method", "lacks a REPORT1 substitution"),
    ],
)
def test_executed_multirow_adapter_fails_on_missing_native_evidence(
    native_multirow: tuple[list[dict[str, Any]], dict[str, Any]],
    method: str,
    fault: str,
    expected: str,
) -> None:
    results, visual = native_multirow
    check = deepcopy(next(row for row in results if row["equation_method"] == method))
    visual = deepcopy(visual)
    if fault == "missing trace":
        del check["equation_trace"]
    elif fault == "missing nominal value":
        del check["equation_nominal_resistance"]["value"]
    elif fault == "missing factor":
        del check["equation_trace"]["thread_factor"]
    elif fault == "missing layers":
        del visual["layers"]
    elif fault == "ambiguous layer":
        visual["layers"].append(deepcopy(visual["layers"][0]))
    elif fault == "missing bolts":
        del visual["bolts"]
    elif fault == "wrong bolt":
        check["bolt_id"] = "NONEXISTENT"
    elif fault == "missing pitches":
        del check["equation_trace"]["pitches"]
    elif fault == "malformed pitch":
        check["equation_trace"]["pitches"] = [{}]
    else:
        check["equation_method"] = "FUTURE_EXECUTED_METHOD"
    with pytest.raises(ValueError, match=expected):
        multirow_native_substitution(check, visual, "US_CUSTOMARY")


def test_block_shear_b_uses_its_distinct_native_tension_factor(
    native_multirow: tuple[list[dict[str, Any]], dict[str, Any]],
) -> None:
    results, visual = native_multirow
    check = deepcopy(
        next(
            row
            for row in results
            if row["equation_method"] == "BLOCK_SHEAR_ASCE_EQ_8_14A"
            and row["availability"] == "CALCULATED"
        )
    )
    check["equation_method"] = "BLOCK_SHEAR_ASCE_EQ_8_14B"
    rendered = multirow_native_substitution(check, visual, "SI")
    assert "0.5 x A_nt(" in rendered
    assert check["equation_nominal_resistance"]["value"] not in rendered
