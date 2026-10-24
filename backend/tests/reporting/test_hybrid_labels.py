"""Display rounding never replaces exact calculation/audit data."""

import pytest

from frp_master_connection.reporting.hybrid_labels import label, utilization


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("DIRECT_BRACE_LOCAL", "Angle connected leg - local shear paths"),
        ("PIN_BEARING:layer-A:B_R2_L1", "Pin bearing - Angle connected leg - Bolt row 2, line 1"),
        ("UNAVAILABLE_SOURCE", "Unavailable source"),
    ],
)
def test_engineer_readable_check_and_station_names(code: str, expected: str) -> None:
    assert label(code) == expected


@pytest.mark.parametrize(
    ("raw", "technical", "expected"),
    [
        (None, False, "Not evaluated"),
        ("1.000000000000000000000001", True, "1.000000000000000000000001"),
        ("1.000000000000000000000001", False, "1.000"),
    ],
)
def test_ratio_display_retains_exact_technical_values(
    raw: str | None, technical: bool, expected: str
) -> None:
    assert utilization(raw, technical=technical) == expected
