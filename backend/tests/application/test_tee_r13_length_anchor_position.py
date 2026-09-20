"""Controlled Stage 3.2-R13 Tee length-anchor and body-position regressions."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from frp_master_connection.api.tee_mapping import (
    map_tee_connector_request,
    serialize_tee_connector_preview,
)
from frp_master_connection.api.tee_schemas import TeeConnectorRequestDTO
from frp_master_connection.application import (
    TeeConnectorOrchestrationRequest,
    TeeMemberEndInterferenceStatus,
    preview_tee_connector,
    resolve_tee_connector_request,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from tests.tee_fixtures import (
    build_tee_r2_payload,
    build_tee_r7_angle_payload,
    build_tee_r8_profile_wall_payload,
)

_GOLDEN_PATH = (
    Path(__file__).parents[1]
    / "golden"
    / "stage_3_2_r13_tee_length_anchor_position_golden_benchmarks_rc1.json"
)
_GOLDEN_SHA256 = "2859272F0C405D77DDBA4DB2C807A73033A8ED21B6C728D7123B376F63A2D1AC"


def _group_offsets(payload: dict[str, Any]) -> None:
    unit = payload["source_length_unit"]
    for key in ("interface_a_layout", "interface_b_layout"):
        layout = payload[key]
        layout["placement_mode"] = "GROUP_OFFSET_CONTROLLED"
        layout["vertical_offset"] = {"value": "0", "unit": unit}
        layout["horizontal_offset"] = {"value": "0", "unit": unit}


def _payload(
    length: str,
    anchor: str | None = None,
    anchor_position: str | None = None,
) -> dict[str, Any]:
    payload = build_tee_r2_payload()
    _group_offsets(payload)
    payload["connector_dimensions"]["connector_length"]["value"] = length
    if anchor is not None:
        payload["connector_length_anchor"] = anchor
    if anchor_position is not None:
        payload["connector_length_anchor_position"] = {
            "value": anchor_position,
            "unit": payload["source_length_unit"],
        }
    return payload


def _request(payload: dict[str, Any]) -> TeeConnectorOrchestrationRequest:
    return map_tee_connector_request(TeeConnectorRequestDTO.model_validate(payload))


def _exact_extents(payload: dict[str, Any]) -> tuple[Decimal, Decimal, Decimal]:
    trace = preview_tee_connector(_request(payload)).tee_longitudinal_placement
    return (
        trace.body_center_coordinate.magnitude,
        trace.positive_end_coordinate.magnitude,
        trace.negative_end_coordinate.magnitude,
    )


def _bolt_geometry(payload: dict[str, Any]) -> tuple[object, ...]:
    resolved = resolve_tee_connector_request(_request(payload))
    return tuple(
        (
            group.bolt_group.id,
            tuple(center.global_position for center in group.master_centers),
            tuple(axis.direction for axis in group.bolt_axes),
        )
        for group in resolved.context.resolved_bolt_groups
    )


def test_r13_owner_golden_is_byte_exact_and_complete() -> None:
    raw = _GOLDEN_PATH.read_bytes()
    fixture = json.loads(raw)

    assert hashlib.sha256(raw).hexdigest().upper() == _GOLDEN_SHA256
    assert fixture["version"] == "RC1"
    assert fixture["semantic_longitudinal_frame"] == {
        "datum_coordinate": "0",
        "positive_axis": "+L_T",
    }
    assert [item["id"] for item in fixture["benchmarks"]] == [
        "R13_A1_LEGACY_CENTERED_6",
        "R13_A2_CENTERED_8",
        "R13_A3_KEEP_POSITIVE_END_FIXED",
        "R13_A4_KEEP_NEGATIVE_END_FIXED",
        "R13_A5_ANCHOR_SWITCH_EQUIVALENCE",
        "R13_A6_BODY_POSITION_PLUS_1",
        "R13_A7_BOLT_INVARIANCE_UNDER_LENGTH_ANCHOR",
        "R13_A8_BODY_POSITION_BOLT_INDEPENDENCE",
    ]


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (_payload("6"), (Decimal(0), Decimal(3), Decimal(-3))),
        (_payload("8", "CENTER", "0"), (Decimal(0), Decimal(4), Decimal(-4))),
        (
            _payload("8", "POSITIVE_L_END", "3"),
            (Decimal(-1), Decimal(3), Decimal(-5)),
        ),
        (
            _payload("8", "NEGATIVE_L_END", "-3"),
            (Decimal(1), Decimal(5), Decimal(-3)),
        ),
        (_payload("6", "CENTER", "1"), (Decimal(1), Decimal(4), Decimal(-2))),
    ],
)
def test_r13_a1_a2_a3_a4_a6_exact_decimal_extents(
    payload: dict[str, Any],
    expected: tuple[Decimal, Decimal, Decimal],
) -> None:
    assert _exact_extents(payload) == expected
    tee = resolve_tee_connector_request(_request(payload)).context.basis.placed_connectors[0]
    assert Decimal(str(tee.extent.x_start)) == expected[2]
    assert Decimal(str(tee.extent.x_end)) == expected[1]


def test_r13_centered_six_to_eight_grows_both_ends_and_keeps_bolts_fixed() -> None:
    six = _payload("6", "CENTER", "0")
    eight = _payload("8", "CENTER", "0")

    assert _exact_extents(six) == (Decimal(0), Decimal(3), Decimal(-3))
    assert _exact_extents(eight) == (Decimal(0), Decimal(4), Decimal(-4))
    assert _bolt_geometry(six) == _bolt_geometry(eight)


def test_r13_positive_and_negative_end_anchors_grow_only_the_opposite_end() -> None:
    upper_six = _payload("6", "POSITIVE_L_END", "3")
    upper_eight = _payload("8", "POSITIVE_L_END", "3")
    lower_six = _payload("6", "NEGATIVE_L_END", "-3")
    lower_eight = _payload("8", "NEGATIVE_L_END", "-3")

    assert _exact_extents(upper_six) == (Decimal(0), Decimal(3), Decimal(-3))
    assert _exact_extents(upper_eight) == (Decimal(-1), Decimal(3), Decimal(-5))
    assert _exact_extents(lower_six) == (Decimal(0), Decimal(3), Decimal(-3))
    assert _exact_extents(lower_eight) == (Decimal(1), Decimal(5), Decimal(-3))
    assert _bolt_geometry(upper_six) == _bolt_geometry(upper_eight)
    assert _bolt_geometry(lower_six) == _bolt_geometry(lower_eight)


def test_r13_a5_anchor_switch_is_exact_body_and_fingerprint_equivalence() -> None:
    payloads = (
        _payload("6", "CENTER", "0"),
        _payload("6", "POSITIVE_L_END", "3"),
        _payload("6", "NEGATIVE_L_END", "-3"),
    )
    previews = tuple(preview_tee_connector(_request(payload)) for payload in payloads)
    resolved = tuple(resolve_tee_connector_request(_request(payload)) for payload in payloads)

    body_fingerprints = {
        item.tee_longitudinal_placement.body_geometry_fingerprint for item in previews
    }
    assert len(body_fingerprints) == 1
    assert len({item.engineering_fingerprint for item in previews}) == 1
    assert all(
        item.context.basis.placed_connectors[0] == resolved[0].context.basis.placed_connectors[0]
        for item in resolved[1:]
    )


def test_r13_a7_a8_keep_both_bolt_groups_independent_of_body_geometry() -> None:
    a1 = _payload("6", "CENTER", "0")
    a3 = _payload("8", "POSITIVE_L_END", "3")
    a6 = _payload("6", "CENTER", "1")

    assert _bolt_geometry(a1) == _bolt_geometry(a3) == _bolt_geometry(a6)
    assert _exact_extents(a1) != _exact_extents(a3)
    assert _exact_extents(a1) != _exact_extents(a6)


def test_r13_body_changes_do_not_translate_connected_member_or_support() -> None:
    baseline = resolve_tee_connector_request(_request(_payload("6", "CENTER", "0")))
    moved = resolve_tee_connector_request(_request(_payload("6", "CENTER", "1")))

    assert moved.context.basis.placed_members == baseline.context.basis.placed_members
    assert moved.context.basis.joint_frame == baseline.context.basis.joint_frame


def test_r13_body_position_recomputes_complete_hole_clearances_and_fails_closed() -> None:
    baseline = preview_tee_connector(_request(_payload("6", "CENTER", "0")))
    moved = preview_tee_connector(_request(_payload("6", "CENTER", "1")))

    for interface_before, interface_after in (
        (baseline.interface_a, moved.interface_a),
        (baseline.interface_b, moved.interface_b),
    ):
        assert interface_after.placement.clearances.vertical_negative.magnitude == (
            interface_before.placement.clearances.vertical_negative.magnitude - Decimal(1)
        )
        assert interface_after.placement.clearances.vertical_positive.magnitude == (
            interface_before.placement.clearances.vertical_positive.magnitude + Decimal(1)
        )
        assert interface_after.placement.clearances.governing_tee_end_id == ("TEE_NEGATIVE_L_END")
        assert interface_after.placement.clearances.governing_tee_end_bolt_id is not None
        assert (
            interface_after.placement.clearances.minimum_tee_end_complete_hole_clearance
            == interface_after.placement.clearances.tee_negative_end_complete_hole_clearance
        )

    with pytest.raises(ValueError, match="Complete-hole clearance"):
        preview_tee_connector(_request(_payload("6", "CENTER", "3")))


def test_r13_r12_inclined_trim_clearance_remains_exact_after_body_translation() -> None:
    payload = build_tee_r7_angle_payload()
    _group_offsets(payload)
    payload["brace_inclination_degrees"] = "25"
    payload["connected_member_end_trim_enabled"] = True
    payload["connected_member_end_clearance"] = {"value": "0.25", "unit": "in"}
    payload["connector_length_anchor"] = "CENTER"
    payload["connector_length_anchor_position"] = {"value": "0.5", "unit": "in"}

    preview = preview_tee_connector(_request(payload))
    trim = preview.connected_member_end_trim

    assert trim.normalized_clearance == PhysicalQuantity.of("0.25", Unit.IN)
    assert trim.measured_plane_clearance == PhysicalQuantity.of("0.25", Unit.IN)
    assert trim.interference_status is TeeMemberEndInterferenceStatus.TRIMMED_CLEAR
    assert preview.tee_longitudinal_placement.body_center_coordinate.magnitude == Decimal("0.5")


def test_r13_api_legacy_omission_normalizes_to_center_without_fingerprint_change() -> None:
    omitted_payload = _payload("8")
    explicit_payload = deepcopy(omitted_payload)
    explicit_payload["connector_length_anchor"] = "CENTER"
    explicit_payload["connector_length_anchor_position"] = {"value": "0", "unit": "in"}

    omitted = preview_tee_connector(_request(omitted_payload))
    explicit = preview_tee_connector(_request(explicit_payload))
    response = serialize_tee_connector_preview(omitted)

    assert omitted.engineering_fingerprint == explicit.engineering_fingerprint
    assert omitted.interface_a.interface_fingerprint == explicit.interface_a.interface_fingerprint
    assert omitted.interface_b.interface_fingerprint == explicit.interface_b.interface_fingerprint
    assert isinstance(response.result, dict)
    placement = response.result["tee_longitudinal_placement"]
    assert isinstance(placement, dict)
    assert placement["connector_length_anchor"] == "CENTER"
    assert placement["connector_length_anchor_position"] == {
        "value": "0",
        "unit": "in",
        "canonical_value": "0",
        "canonical_unit": "mm",
    }


def test_r13_exact_decimal_halves_and_invalid_contract_values_fail_closed() -> None:
    assert _exact_extents(_payload("7", "CENTER", "0")) == (
        Decimal(0),
        Decimal("3.5"),
        Decimal("-3.5"),
    )
    invalid_enum = _payload("6")
    invalid_enum["connector_length_anchor"] = "UPPER_SCREEN_END"
    with pytest.raises(ValidationError):
        TeeConnectorRequestDTO.model_validate(invalid_enum)
    wrong_unit = _payload("6", "CENTER")
    wrong_unit["connector_length_anchor_position"] = {"value": "0", "unit": "mm"}
    with pytest.raises(ValidationError, match="source_length_unit"):
        TeeConnectorRequestDTO.model_validate(wrong_unit)
    nonfinite = _payload("6", "CENTER")
    nonfinite["connector_length_anchor_position"] = {"value": "NaN", "unit": "in"}
    with pytest.raises(ValidationError):
        TeeConnectorRequestDTO.model_validate(nonfinite)

    request = _request(_payload("6"))
    with pytest.raises(TypeError, match="TeeConnectorLengthAnchor"):
        replace(request, connector_length_anchor=cast(Any, "CENTER"))
    with pytest.raises(TypeError, match="must be a PhysicalQuantity"):
        replace(request, connector_length_anchor_position=cast(Any, Decimal(0)))
    with pytest.raises(ValueError, match="must be a length"):
        replace(
            request,
            connector_length_anchor_position=PhysicalQuantity.of("1", Unit.KIP),
        )
    with pytest.raises(ValueError, match="source_length_unit"):
        replace(
            request,
            connector_length_anchor_position=PhysicalQuantity.of("0", Unit.MM),
        )


@pytest.mark.parametrize("family", ["ANGLE", "CHANNEL", "RECTANGULAR_HOLLOW_SECTION"])
def test_r13_r7_r8_profile_paths_remain_resolved(family: str) -> None:
    payload = (
        build_tee_r7_angle_payload()
        if family == "ANGLE"
        else build_tee_r8_profile_wall_payload(profile_family=family)
    )
    _group_offsets(payload)
    payload["connector_length_anchor"] = "CENTER"
    payload["connector_length_anchor_position"] = {"value": "0", "unit": "in"}

    resolved = resolve_tee_connector_request(_request(payload))

    assert len(resolved.context.resolved_bolt_groups[0].paths) == 4
    assert all(path.layers for path in resolved.context.resolved_bolt_groups[0].paths)
