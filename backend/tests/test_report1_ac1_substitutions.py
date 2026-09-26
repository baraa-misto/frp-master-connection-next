"""Native-value and unit regressions for worked REPORT1 multi-row checks."""

from __future__ import annotations

import asyncio
import io
import re
from typing import Any

import httpx
import pytest
from pypdf import PdfReader

from frp_master_connection.api.app import create_app
from tests.api.test_connector_materials import native_payload


def _multirow_report(
    display_units: str, changes: dict[str, object] | None = None
) -> tuple[dict[str, Any], str]:
    payload = native_payload("multi-row")
    payload.update(changes or {})

    async def run() -> tuple[dict[str, Any], bytes]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app()), base_url="http://test"
        ) as client:
            design = await client.post("/api/v1/calculations/multi-row/design-check", json=payload)
            assert design.status_code == 200, design.text
            report = await client.post(
                "/api/v1/reports/export",
                json={
                    "report_handle": design.headers["X-Report-Handle"],
                    "display_units": display_units,
                },
            )
            assert report.status_code == 200, report.text
            return design.json(), report.content

    native, data = asyncio.run(run())
    return native, "\n".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages
    )


@pytest.mark.parametrize("system", ["US_CUSTOMARY", "SI"])
def test_executed_first_row_and_block_shear_have_native_worked_substitutions(
    system: str,
) -> None:
    native, text = _multirow_report(system)
    checks = native["calculation_result"]["results"]
    expected = {
        "FIRST_ROW_SIMPLIFIED": ("w(", "t(", "F_t("),
        "BLOCK_SHEAR_ASCE_EQ_8_14A": ("A_nv(", "A_nt(", "F_s(", "F_t("),
    }
    compact = re.sub(r"\s+", " ", text)
    assert "Native factor-stage substitution unavailable" not in compact
    for method, terms in expected.items():
        matching = [
            check
            for check in checks
            if check["availability"] == "CALCULATED" and check["equation_method"] == method
        ]
        assert matching
        for check in matching:
            marker = f"{check['result_id']} - "
            position = compact.rfind(marker)
            assert position >= 0
            detail = compact[position : position + 2500]
            for term in terms:
                assert term in detail, (method, term)
            assert "R_n =" in detail
            assert "R_d =" in detail


@pytest.mark.parametrize(("system", "force_unit"), [("US_CUSTOMARY", "kip"), ("SI", "kN")])
def test_engineer_facing_multirow_comparison_uses_one_force_system(
    system: str, force_unit: str
) -> None:
    native, text = _multirow_report(system)
    first = next(
        check
        for check in native["calculation_result"]["results"]
        if check["availability"] == "CALCULATED"
        and check["equation_method"] == "FIRST_ROW_SIMPLIFIED"
    )
    compact = re.sub(r"\s+", " ", text)
    marker = f"{first['result_id']} - First-row net tension"
    position = compact.rindex(marker)
    detail = compact[position : position + 2300]
    for label in ("Demand", "Nominal resistance", "Design resistance"):
        assert re.search(rf"{label} [^|]*? {force_unit}", detail), (label, detail[:500])
    unwrapped = re.sub(r"\s+", "", text)
    assert first["utilization"] in unwrapped
    assert native["calculation_result"]["input_fingerprint"] in unwrapped
