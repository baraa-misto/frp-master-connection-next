"""Stage 3.2 Tee engineering-input contract tests."""

from dataclasses import replace
from decimal import Decimal

import pytest

from frp_master_connection.domain import (
    SelectedSupportFlange,
    TeeBoltLayout,
    TeeBraceDimensions,
    TeeConnectorDimensions,
    TeeInterfaceIdentity,
    TeeSupportDimensions,
    TeeSupportRole,
)


def _connector() -> TeeConnectorDimensions:
    return TeeConnectorDimensions(
        Decimal("8"), Decimal("6"), Decimal(".5"), Decimal("4"), Decimal(".375")
    )


def _layout() -> TeeBoltLayout:
    return TeeBoltLayout(
        2,
        2,
        Decimal("2"),
        Decimal("2"),
        Decimal("1"),
        Decimal("1"),
        Decimal("1"),
        Decimal("1"),
    )


def test_exact_tee_identities_and_derived_dimensions() -> None:
    connector = _connector()
    layout = _layout()

    assert TeeSupportRole.COLUMN.value == "COLUMN"
    assert TeeSupportRole.BEAM.value == "BEAM"
    assert SelectedSupportFlange.POSITIVE_LOCAL_Z.value == "POSITIVE_LOCAL_Z"
    assert SelectedSupportFlange.NEGATIVE_LOCAL_Z.value == "NEGATIVE_LOCAL_Z"
    assert TeeInterfaceIdentity.BRACE_TO_STEM.value == "TEE_INTERFACE_A_BRACE_TO_STEM"
    assert TeeInterfaceIdentity.FLANGE_TO_SUPPORT.value == "TEE_INTERFACE_B_FLANGE_TO_SUPPORT"
    assert connector.overall_depth == Decimal("4.5")
    assert layout.row_span == Decimal("2")
    assert layout.line_span == Decimal("2")
    assert layout.required_row_extent == Decimal("4")
    assert layout.required_line_extent == Decimal("4")


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("connector_length", Decimal("0"), "greater than zero"),
        ("flange_width", Decimal("NaN"), "finite"),
        ("flange_thickness", 1.0, "Decimal"),
        ("stem_depth", Decimal("-1"), "greater than zero"),
        ("stem_thickness", Decimal("Infinity"), "finite"),
    ],
)
def test_connector_dimensions_reject_invalid_values(field: str, value: object, error: str) -> None:
    with pytest.raises((TypeError, ValueError), match=error):
        replace(_connector(), **{field: value})  # type: ignore[arg-type]


def test_connector_rejects_invalid_stem_flange_relationship() -> None:
    with pytest.raises(ValueError, match="less than flange_width"):
        replace(_connector(), stem_thickness=Decimal("6"))


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"overall_depth": Decimal("1.5")}, "clear web depth"),
        ({"flange_width": Decimal(".5")}, "wider than its web"),
        ({"member_length": Decimal("0")}, "greater than zero"),
    ],
)
def test_support_dimensions_are_physical(change: dict[str, Decimal], error: str) -> None:
    support = TeeSupportDimensions(
        Decimal("16"), Decimal("8"), Decimal("8"), Decimal(".5"), Decimal(".75")
    )
    with pytest.raises(ValueError, match=error):
        replace(support, **change)


@pytest.mark.parametrize("value", [Decimal("0"), Decimal("NaN")])
def test_brace_dimensions_reject_nonphysical_values(value: Decimal) -> None:
    with pytest.raises(ValueError, match=r"finite|greater than zero"):
        TeeBraceDimensions(Decimal("8"), Decimal(".375"), value)


@pytest.mark.parametrize("count", [True, 0, 2.5])
def test_layout_rejects_invalid_counts(count: object) -> None:
    values = list(_layout().__dict__.values()) if hasattr(_layout(), "__dict__") else None
    assert values is None  # slotted/frozen is intentional
    with pytest.raises(ValueError, match="non-Boolean integer"):
        replace(_layout(), row_count=count)  # type: ignore[arg-type]


def test_layout_accepts_one_row_and_one_bolt_per_row_independently() -> None:
    layout = replace(_layout(), row_count=1, bolts_per_row=1)

    assert layout.row_count == 1
    assert layout.bolts_per_row == 1
    assert layout.row_span == 0
    assert layout.line_span == 0


@pytest.mark.parametrize(
    "field",
    [
        "pitch",
        "gauge",
        "unloaded_end_distance",
        "loaded_end_distance",
        "negative_side_distance",
        "positive_side_distance",
    ],
)
def test_layout_rejects_nonpositive_distances(field: str) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        replace(_layout(), **{field: Decimal("0")})  # type: ignore[arg-type]
