"""Stage 3.3C2-R2 physical endpoint and hardware-side regression tests."""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any, cast

import pytest

from frp_master_connection.api.clip_angle_mapping import (
    map_clip_angle_request,
    serialize_clip_angle_preview,
)
from frp_master_connection.api.clip_angle_schemas import ClipAngleConnectorRequestDTO
from frp_master_connection.api.tee_mapping import (
    map_tee_connector_request,
    serialize_tee_connector_preview,
)
from frp_master_connection.api.tee_schemas import TeeConnectorRequestDTO
from frp_master_connection.application import (
    ClipAnglePreviewResult,
    TeeConnectorPreviewResult,
    preview_clip_angle,
    preview_tee_connector,
)
from frp_master_connection.application.shared_support_integration import (
    IntegratedFullThroughBoltTrace,
    build_integrated_full_through_bolt,
)
from frp_master_connection.calculation import Unit
from frp_master_connection.domain import (
    FullThroughHardwareLocation,
    MemberProfileSurfaceId,
    PositionVector3D,
)
from tests.clip_angle_fixtures import build_clip_angle_c2_payload
from tests.tee_fixtures import build_tee_c2_payload


def _tee(payload: dict[str, Any]) -> TeeConnectorPreviewResult:
    return preview_tee_connector(
        map_tee_connector_request(TeeConnectorRequestDTO.model_validate(payload))
    )


def _clip(payload: dict[str, Any]) -> ClipAnglePreviewResult:
    return preview_clip_angle(
        map_clip_angle_request(ClipAngleConnectorRequestDTO.model_validate(payload))
    )


def _point(value: PositionVector3D) -> tuple[float, float, float]:
    return (value.x, value.y, value.z)


def _length(trace: IntegratedFullThroughBoltTrace) -> float:
    return math.dist(_point(trace.physical_start_point), _point(trace.physical_end_point))


def _axis(
    result: TeeConnectorPreviewResult | ClipAnglePreviewResult,
    *,
    support: bool = False,
) -> tuple[float, float, float]:
    if isinstance(result, ClipAnglePreviewResult):
        assert result.visualization is not None
        clip_bolt = (
            result.visualization.interface_b_bolts[0]
            if support
            else result.visualization.interface_a_bolts[0]
        )
        return (
            float(clip_bolt.axis[0]),
            float(clip_bolt.axis[1]),
            float(clip_bolt.axis[2]),
        )
    assert result.visualization is not None
    tee_bolt = (
        result.visualization.interface_b_bolts[0]
        if support
        else result.visualization.interface_a_bolts[0]
    )
    return (tee_bolt.axis.x, tee_bolt.axis.y, tee_bolt.axis.z)


@pytest.mark.parametrize(
    ("family", "role", "expected_start", "expected_end", "engineering_axis", "fingerprint"),
    [
        (
            "TEE",
            "BRACE",
            (3.5, -0.25, -3.0),
            (3.5, 6.25, -3.0),
            (0.0, -1.0, 0.0),
            "a089c44a4652b207ff1145d8a5790154855c1078cf006a6022c8d649f947a6f9",
        ),
        (
            "SINGLE_CLIP_ANGLE",
            "BRACE",
            (0.5, 1.25, -1.0),
            (-6.0, 1.25, -1.0),
            (1.0, 0.0, 0.0),
            "16ae7ce854c5b5b4d34da713373bcf5924f5fc411687e5dc0a765928e5db3288",
        ),
        (
            "SINGLE_CLIP_ANGLE",
            "BEAM",
            (0.5, 1.25, -1.0),
            (-6.0, 1.25, -1.0),
            (1.0, 0.0, 0.0),
            "1c995ab0e90b76cd405bff1c5f4990bef2fdbba83e12daac47dffd9fbace7c51",
        ),
    ],
)
def test_connected_rhs_uses_physical_head_to_nut_endpoints_without_changing_engineering_axis(
    family: str,
    role: str,
    expected_start: tuple[float, float, float],
    expected_end: tuple[float, float, float],
    engineering_axis: tuple[float, float, float],
    fingerprint: str,
) -> None:
    if family == "TEE":
        result: TeeConnectorPreviewResult | ClipAnglePreviewResult = _tee(
            build_tee_c2_payload(connected_profile_family="RECTANGULAR_HOLLOW_SECTION")
        )
    else:
        payload = build_clip_angle_c2_payload(connected_profile_family="RECTANGULAR_HOLLOW_SECTION")
        payload["connected_member_profile"]["role"] = role
        result = _clip(payload)

    trace = result.rectangular_full_through_paths[0]
    assert _point(trace.physical_start_point) == expected_start
    assert _point(trace.physical_end_point) == expected_end
    assert _length(trace) == pytest.approx(float(trace.hardware.shank_length), abs=1.0e-12)
    assert tuple(item.identity for item in trace.path.segments) == (
        "TEE_STEM" if family == "TEE" else "CLIP_ANGLE_CONNECTED_LEG",
        "RHS_NEAR_WALL",
        "RHS_CAVITY",
        "RHS_FAR_WALL",
    )
    assert tuple(item.length for item in trace.path.segments) == (
        Decimal("0.5"),
        Decimal("0.5"),
        Decimal("5.0"),
        Decimal("0.5"),
    )
    assert _axis(result) == engineering_axis
    physical_vector = tuple(
        end - start for start, end in zip(expected_start, expected_end, strict=True)
    )
    assert sum(a * b for a, b in zip(physical_vector, engineering_axis, strict=True)) < 0
    assert trace.hardware.head_location is FullThroughHardwareLocation.EXTERIOR_NEAR_SIDE
    assert trace.hardware.nut_location is FullThroughHardwareLocation.EXTERIOR_FAR_SIDE
    assert trace.hardware.washer_locations == (
        FullThroughHardwareLocation.EXTERIOR_NEAR_SIDE,
        FullThroughHardwareLocation.EXTERIOR_FAR_SIDE,
    )
    assert trace.hardware.physical_bolt_count == 1
    assert trace.hardware.continuous_shank_count == 1
    assert trace.hardware.internal_hardware_count == 0
    assert len(trace.containment.face_results) == 2
    assert all(item.valid for item in trace.containment.face_results)
    assert result.engineering_fingerprint == fingerprint


@pytest.mark.parametrize(
    ("family", "expected_start", "expected_end", "engineering_axis", "fingerprint"),
    [
        (
            "TEE",
            (0.5, -1.0, -3.0),
            (-6.0, -1.0, -3.0),
            (-1.0, 0.0, 0.0),
            "5eb5ce6e2a9bffe2a94dedd5ac2b18af82197f4b4fbeace35e85519c2275a239",
        ),
        (
            "SINGLE_CLIP_ANGLE",
            (1.25, 0.5, -1.0),
            (1.25, -6.0, -1.0),
            (0.0, -1.0, 0.0),
            "20d54cebf9ea15decc83cc2d2c91b558eb3bbcd317f2cd26f2f4930a9f3e6586",
        ),
    ],
)
def test_known_good_rhs_support_endpoints_and_axes_remain_unchanged(
    family: str,
    expected_start: tuple[float, float, float],
    expected_end: tuple[float, float, float],
    engineering_axis: tuple[float, float, float],
    fingerprint: str,
) -> None:
    payload = (
        build_tee_c2_payload(support_target="RECTANGULAR_HOLLOW_COLUMN_WALL")
        if family == "TEE"
        else build_clip_angle_c2_payload(support_target="RECTANGULAR_HOLLOW_COLUMN_WALL")
    )
    payload["support_profile"]["width"] = {"value": "10", "unit": "in"}
    result = _tee(payload) if family == "TEE" else _clip(payload)
    trace = result.rectangular_full_through_paths[0]

    assert _point(trace.physical_start_point) == expected_start
    assert _point(trace.physical_end_point) == expected_end
    assert _length(trace) == pytest.approx(float(trace.hardware.shank_length), abs=1.0e-12)
    assert _axis(result, support=True) == engineering_axis
    physical_vector = tuple(
        end - start for start, end in zip(expected_start, expected_end, strict=True)
    )
    assert sum(a * b for a, b in zip(physical_vector, engineering_axis, strict=True)) > 0
    assert result.engineering_fingerprint == fingerprint


@pytest.mark.parametrize("family", ["TEE", "SINGLE_CLIP_ANGLE"])
def test_connected_srs_uses_the_same_exact_external_endpoint_contract(family: str) -> None:
    result = (
        _tee(build_tee_c2_payload(connected_profile_family="SOLID_RECTANGULAR_SECTION"))
        if family == "TEE"
        else _clip(
            build_clip_angle_c2_payload(connected_profile_family="SOLID_RECTANGULAR_SECTION")
        )
    )
    trace = result.rectangular_full_through_paths[0]
    expected = (
        ((3.5, -0.25, -3.0), (3.5, 6.25, -3.0))
        if family == "TEE"
        else ((0.5, 1.25, -1.0), (-6.0, 1.25, -1.0))
    )
    assert (_point(trace.physical_start_point), _point(trace.physical_end_point)) == expected
    assert tuple(item.identity for item in trace.path.segments) == (
        "TEE_STEM" if family == "TEE" else "CLIP_ANGLE_CONNECTED_LEG",
        "SOLID_RECTANGULAR_SECTION",
    )
    assert trace.hardware.internal_hardware_count == 0


@pytest.mark.parametrize("family", ["TEE", "SINGLE_CLIP_ANGLE"])
def test_rhs_trim_retains_current_physical_cross_section_endpoints(family: str) -> None:
    builder = build_tee_c2_payload if family == "TEE" else build_clip_angle_c2_payload
    payload = builder(connected_profile_family="RECTANGULAR_HOLLOW_SECTION")
    untrimmed = _tee(payload) if family == "TEE" else _clip(payload)
    payload["connected_member_end_trim_enabled"] = True
    payload["connected_member_end_clearance"] = {"value": "0.25", "unit": "in"}
    trimmed = _tee(payload) if family == "TEE" else _clip(payload)

    before = untrimmed.rectangular_full_through_paths[0]
    after = trimmed.rectangular_full_through_paths[0]
    assert after.physical_start_point == before.physical_start_point
    assert after.physical_end_point == before.physical_end_point
    assert after.path == before.path
    assert after.path_fingerprint == before.path_fingerprint
    if isinstance(trimmed, TeeConnectorPreviewResult):
        assert trimmed.connected_member_end_trim.geometry_valid is True
        assert trimmed.connected_member_end_trim.fabricated_trim_edge_ids
    else:
        assert trimmed.trim.geometry_valid is True
        assert trimmed.trim.fabricated_trim_edge_ids


@pytest.mark.parametrize("family", ["TEE", "SINGLE_CLIP_ANGLE"])
def test_current_transport_carries_decimal_string_physical_endpoints_and_external_hardware(
    family: str,
) -> None:
    if family == "TEE":
        tee_result = _tee(
            build_tee_c2_payload(connected_profile_family="RECTANGULAR_HOLLOW_SECTION")
        )
        body = serialize_tee_connector_preview(tee_result).model_dump(mode="json")
        fingerprint = tee_result.engineering_fingerprint
    else:
        clip_result = _clip(
            build_clip_angle_c2_payload(connected_profile_family="RECTANGULAR_HOLLOW_SECTION")
        )
        body = serialize_clip_angle_preview(clip_result).model_dump(mode="json")
        fingerprint = clip_result.engineering_fingerprint
    trace = body["result"]["rectangular_full_through_paths"][0]
    assert all(isinstance(trace["physical_start_point"][axis], str) for axis in "xyz")
    assert all(isinstance(trace["physical_end_point"][axis], str) for axis in "xyz")
    assert trace["hardware"]["head_location"] == "EXTERIOR_NEAR_SIDE"
    assert trace["hardware"]["nut_location"] == "EXTERIOR_FAR_SIDE"
    assert trace["hardware"]["washer_locations"] == [
        "EXTERIOR_NEAR_SIDE",
        "EXTERIOR_FAR_SIDE",
    ]
    assert body["engineering_fingerprint"] == fingerprint


def test_integrated_endpoint_construction_requires_the_authoritative_placed_profile() -> None:
    request = map_clip_angle_request(
        ClipAngleConnectorRequestDTO.model_validate(
            build_clip_angle_c2_payload(connected_profile_family="RECTANGULAR_HOLLOW_SECTION")
        )
    )
    profile = request.connected_member_profile
    with pytest.raises(TypeError, match="requires placed_profile"):
        build_integrated_full_through_bolt(
            profile,
            selected_surface=cast(MemberProfileSurfaceId, profile.selected_surface),
            bolt_id="MISSING-PLACED-PROFILE",
            local_uv=(Decimal(0), Decimal(0)),
            hole_radius=Decimal("0.2815"),
            connector_identity="CLIP_ANGLE_CONNECTED_LEG",
            connector_thickness=request.connector_dimensions.thickness,
            connector_material_region_id="CLIP_ANGLE_CONNECTED_LEG_REGION",
            rectangular_material_region_id="CONNECTED_RECTANGULAR_PROFILE_REGION",
            source_length_unit=Unit.IN,
        )
