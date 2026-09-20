"""Stage 3.3C3-R1 material-axis payload coverage and invariance regressions."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

import pytest

from frp_master_connection.api.clip_angle_mapping import (
    map_clip_angle_request,
    serialize_clip_angle_preview,
)
from frp_master_connection.api.clip_angle_schemas import ClipAngleConnectorRequestDTO
from frp_master_connection.api.paired_clip_angle_mapping import (
    map_paired_clip_angle_request,
    serialize_paired_clip_angle_preview,
)
from frp_master_connection.api.paired_clip_angle_schemas import (
    PairedClipAngleConnectorRequestDTO,
)
from frp_master_connection.application import (
    ClipAnglePreviewResult,
    PairedClipAnglePreviewResult,
    preview_clip_angle,
    preview_paired_clip_angle,
)
from tests.clip_angle_fixtures import build_clip_angle_c2_payload
from tests.paired_clip_angle_fixtures import build_paired_clip_angle_c3_payload

PROFILE_ELEMENTS = {
    "FLAT_PLATE": ("PLATE",),
    "WIDE_FLANGE_I": ("WEB", "TOP_FLANGE", "BOTTOM_FLANGE"),
    "CHANNEL": ("WEB", "TOP_FLANGE", "BOTTOM_FLANGE"),
    "ANGLE": ("LEG_1", "LEG_2"),
    "RECTANGULAR_HOLLOW_SECTION": (
        "TOP_WALL",
        "BOTTOM_WALL",
        "SIDE_WALL_1",
        "SIDE_WALL_2",
    ),
    "SOLID_RECTANGULAR_SECTION": ("PLATE",),
}

SUPPORT_ELEMENTS = {
    "W_COLUMN_FLANGE": ("WEB", "TOP_FLANGE", "BOTTOM_FLANGE"),
    "W_BEAM_FLANGE": ("WEB", "TOP_FLANGE", "BOTTOM_FLANGE"),
    "W_COLUMN_WEB": ("WEB", "TOP_FLANGE", "BOTTOM_FLANGE"),
    "CHANNEL_COLUMN_WEB": ("WEB", "TOP_FLANGE", "BOTTOM_FLANGE"),
    "ANGLE_COLUMN_LEG": ("LEG_1", "LEG_2"),
    "RECTANGULAR_HOLLOW_COLUMN_WALL": (
        "TOP_WALL",
        "BOTTOM_WALL",
        "SIDE_WALL_1",
        "SIDE_WALL_2",
    ),
    "SOLID_RECTANGULAR_COLUMN_FACE": ("PLATE",),
}

SINGLE_PROFILE_FINGERPRINTS = {
    "FLAT_PLATE": "a7cb1ae63b16a316ba13b8480270a36b6df537b15f9b01ee752d87216cd3e556",
    "WIDE_FLANGE_I": "b87c80c632c9591757223e5a7e01d88c2301ac2db5a5cdf1d9f0cce2f37e9310",
    "CHANNEL": "8fcff6fe14b96a03c4162afe0b5a2f21a9a0a5e074b45af35b8a4b1c6032fccd",
    "ANGLE": "523928b8f9ecf676050c96d628346211722d294a7b3cf07489815ca25400b8c2",
    "RECTANGULAR_HOLLOW_SECTION": (
        "30e855c9cb8b7ffa80c67f95cef3900df78408f306b809a1f3790037fc46316d"
    ),
    "SOLID_RECTANGULAR_SECTION": "7dec6a5cd7ba8884aaa4d2d50fc475e35257602e6b840d09a026c1058fc754fc",
}

PAIRED_PROFILE_FINGERPRINTS = {
    "FLAT_PLATE": "25081c5b3ee3fbcc6f19d283406fb0f6b33ae800f893a11fdb5128f8ba0d18d6",
    "WIDE_FLANGE_I": "49415e2d24496e7a8f4a550a93f8124053f0295c1754012ac7eb237573c42600",
    "CHANNEL": "d40c2a9b4110846f25ce52ada607cc62d11b58cad17ad5ac06a34c033a16d00a",
    "ANGLE": "db52bf2334265f15ef9a24b415a6e48801966773d2e524d6c4a204e9d63bb0c7",
    "RECTANGULAR_HOLLOW_SECTION": (
        "ac3b1a52b1677214030a334fdbabf13a841e1a758e5a0b70b3c2cef231ef17b0"
    ),
    "SOLID_RECTANGULAR_SECTION": "1f5e555d2c7007b9dcb7dc3db9fe52b2c5a6102ae6ab9867573922efdabaf9ff",
}

SINGLE_SUPPORT_FINGERPRINTS = {
    "W_COLUMN_FLANGE": "a7cb1ae63b16a316ba13b8480270a36b6df537b15f9b01ee752d87216cd3e556",
    "W_BEAM_FLANGE": "8dd74b97fbd770658b21b204957994b7ad24326c643b2afaedcb582da41c3c62",
    "W_COLUMN_WEB": "bfca041b7922a5a197ea3daa282f30c218ee5f7afb23db813fe32c7fbec713a6",
    "CHANNEL_COLUMN_WEB": "c760357852794ebbc986059477224852f67a4238320b54aba950ce76a0e780ab",
    "ANGLE_COLUMN_LEG": "f38ec10901b76faf58fac4be46b21705f0e56beb02fd7108b3f4e1ef984b6349",
    "RECTANGULAR_HOLLOW_COLUMN_WALL": (
        "7cb5f7a92e3c22ad012bd729e48a8c515b3ae3cac68ac7c1cf2d96fa0b911928"
    ),
    "SOLID_RECTANGULAR_COLUMN_FACE": (
        "eac55e85afacfd2db27c2590482935d4138a28326cb4095c2e53d71455c20caa"
    ),
}

PAIRED_SUPPORT_FINGERPRINTS = {
    "W_COLUMN_FLANGE": "db52bf2334265f15ef9a24b415a6e48801966773d2e524d6c4a204e9d63bb0c7",
    "W_BEAM_FLANGE": "c62fc003b952eef73c1b1674023af9c604a35508a4ee6723573b189dec3c303a",
    "W_COLUMN_WEB": "ec6125fa424b8e29ed97bb6a47c03f263c0ea4eaa9acaff27e53fc723902b2ee",
    "CHANNEL_COLUMN_WEB": "6d6f21dea0d2142b8b1c5de830d29ea2dcfd6bae0e8b7ab9d4e4b5134367fe08",
    "ANGLE_COLUMN_LEG": "799d766c176779e3e696b3237a52e7446771235916c2d7fe3011e8b75d66ce4e",
    "RECTANGULAR_HOLLOW_COLUMN_WALL": (
        "ead500c156f6b9cb1dc5827ccf6d754997059aa1592d5c40bf17f6de07405b10"
    ),
    "SOLID_RECTANGULAR_COLUMN_FACE": (
        "cf9d1521897b94065504d5741ce357b02a19c972801406ef5933483416946070"
    ),
}


def _length(value: str) -> dict[str, str]:
    return {"value": value, "unit": "in"}


def _widen_support(payload: dict[str, Any], target: str) -> None:
    profile = payload["support_profile"]
    if target in {"W_COLUMN_FLANGE", "W_BEAM_FLANGE"}:
        profile["flange_width"] = _length("20")
    elif target in {"W_COLUMN_WEB", "CHANNEL_COLUMN_WEB"}:
        profile["depth"] = _length("20")
    elif target == "ANGLE_COLUMN_LEG":
        profile["leg_y"] = _length("20")
        profile["leg_z"] = _length("20")
    else:
        profile["width"] = _length("20")


def _single_payload(
    profile: str = "FLAT_PLATE", support: str = "W_COLUMN_FLANGE"
) -> dict[str, Any]:
    payload = build_clip_angle_c2_payload(
        connected_profile_family=profile,
        support_target=support,
    )
    _widen_support(payload, support)
    if profile in {"WIDE_FLANGE_I", "CHANNEL"}:
        payload["connected_member_profile"]["dimensions"]["depth"] = _length("10")
    return payload


def _paired_payload(profile: str = "ANGLE", support: str = "W_COLUMN_FLANGE") -> dict[str, Any]:
    payload = build_paired_clip_angle_c3_payload(
        connected_profile_family=profile,
        support_target=support,
    )
    _widen_support(payload, support)
    if profile in {"WIDE_FLANGE_I", "CHANNEL"}:
        payload["connected_member_profile"]["dimensions"]["depth"] = _length("10")
    return payload


def _single(
    profile: str = "FLAT_PLATE", support: str = "W_COLUMN_FLANGE"
) -> ClipAnglePreviewResult:
    dto = ClipAngleConnectorRequestDTO.model_validate(_single_payload(profile, support))
    return preview_clip_angle(map_clip_angle_request(dto))


def _paired(
    profile: str = "ANGLE", support: str = "W_COLUMN_FLANGE"
) -> PairedClipAnglePreviewResult:
    dto = PairedClipAngleConnectorRequestDTO.model_validate(_paired_payload(profile, support))
    return preview_paired_clip_angle(map_paired_clip_angle_request(dto))


def _assert_orthonormal(regions: tuple[Any, ...]) -> None:
    for region in regions:
        vectors = (region.lw, region.cw, region.tt)
        assert all(
            sum(component * component for component in vector) == Decimal(1) for vector in vectors
        )
        assert all(
            sum(left[index] * right[index] for index in range(3)) == Decimal(0)
            for left, right in (
                (vectors[0], vectors[1]),
                (vectors[0], vectors[2]),
                (vectors[1], vectors[2]),
            )
        )


def test_single_and_paired_payloads_serialize_complete_exact_r14b_regions() -> None:
    single = _single()
    paired = _paired("WIDE_FLANGE_I")
    single_visualization = single.visualization
    paired_visualization = paired.visualization
    assert single_visualization is not None
    assert paired_visualization is not None

    assert tuple(
        (item.physical_element_id, item.lw, item.cw, item.tt)
        for item in single_visualization.material_regions
    ) == (
        (
            "CONNECTED_MEMBER_LEG",
            (Decimal(0), Decimal(0), Decimal(1)),
            (Decimal(0), Decimal(-1), Decimal(0)),
            (Decimal(1), Decimal(0), Decimal(0)),
        ),
        (
            "SUPPORT_LEG",
            (Decimal(0), Decimal(0), Decimal(1)),
            (Decimal(-1), Decimal(0), Decimal(0)),
            (Decimal(0), Decimal(-1), Decimal(0)),
        ),
    )
    assert tuple(
        (item.physical_element_id, item.lw, item.cw, item.tt)
        for item in paired_visualization.material_regions
    ) == (
        (
            "POSITIVE_CLIP_ANGLE:CONNECTED_MEMBER_LEG",
            (Decimal(0), Decimal(0), Decimal(1)),
            (Decimal(0), Decimal(-1), Decimal(0)),
            (Decimal(1), Decimal(0), Decimal(0)),
        ),
        (
            "POSITIVE_CLIP_ANGLE:SUPPORT_LEG",
            (Decimal(0), Decimal(0), Decimal(1)),
            (Decimal(-1), Decimal(0), Decimal(0)),
            (Decimal(0), Decimal(-1), Decimal(0)),
        ),
        (
            "NEGATIVE_CLIP_ANGLE:CONNECTED_MEMBER_LEG",
            (Decimal(0), Decimal(0), Decimal(-1)),
            (Decimal(0), Decimal(-1), Decimal(0)),
            (Decimal(-1), Decimal(0), Decimal(0)),
        ),
        (
            "NEGATIVE_CLIP_ANGLE:SUPPORT_LEG",
            (Decimal(0), Decimal(0), Decimal(-1)),
            (Decimal(1), Decimal(0), Decimal(0)),
            (Decimal(0), Decimal(-1), Decimal(0)),
        ),
    )
    assert (
        tuple(item.physical_element_id for item in single_visualization.support_material_regions)
        == SUPPORT_ELEMENTS["W_COLUMN_FLANGE"]
    )
    assert (
        tuple(
            item.physical_element_id
            for item in paired_visualization.connected_member_material_regions
        )
        == PROFILE_ELEMENTS["WIDE_FLANGE_I"]
    )
    assert (
        tuple(item.physical_element_id for item in paired_visualization.support_material_regions)
        == SUPPORT_ELEMENTS["W_COLUMN_FLANGE"]
    )

    _assert_orthonormal(
        (
            *single_visualization.material_regions,
            *single_visualization.connected_member_material_regions,
            *single_visualization.support_material_regions,
            *paired_visualization.material_regions,
            *paired_visualization.connected_member_material_regions,
            *paired_visualization.support_material_regions,
        )
    )
    serialized_single = cast(
        dict[str, Any], serialize_clip_angle_preview(single).result["visualization"]
    )
    serialized_paired = cast(
        dict[str, Any], serialize_paired_clip_angle_preview(paired).result["visualization"]
    )
    assert len(serialized_single["support_material_regions"]) == 3
    assert len(serialized_paired["material_regions"]) == 4
    assert len(serialized_paired["connected_member_material_regions"]) == 3
    assert len(serialized_paired["support_material_regions"]) == 3


@pytest.mark.parametrize(("profile", "elements"), PROFILE_ELEMENTS.items())
def test_six_connected_profiles_keep_complete_regions_and_exact_fingerprints(
    profile: str, elements: tuple[str, ...]
) -> None:
    single = _single(profile)
    paired = _paired(profile)
    assert single.geometry_status.value == paired.geometry_status.value == "VALID"
    assert single.engineering_fingerprint == SINGLE_PROFILE_FINGERPRINTS[profile]
    assert paired.engineering_fingerprint == PAIRED_PROFILE_FINGERPRINTS[profile]
    assert single.visualization is not None
    assert paired.visualization is not None
    assert (
        tuple(
            item.physical_element_id
            for item in single.visualization.connected_member_material_regions
        )
        == elements
    )
    assert (
        tuple(
            item.physical_element_id
            for item in paired.visualization.connected_member_material_regions
        )
        == elements
    )
    assert "CAVITY" not in elements


@pytest.mark.parametrize(("support", "elements"), SUPPORT_ELEMENTS.items())
def test_seven_support_targets_keep_complete_regions_and_exact_fingerprints(
    support: str, elements: tuple[str, ...]
) -> None:
    single = _single(support=support)
    paired = _paired(support=support)
    assert single.geometry_status.value == paired.geometry_status.value == "VALID"
    assert single.engineering_fingerprint == SINGLE_SUPPORT_FINGERPRINTS[support]
    assert paired.engineering_fingerprint == PAIRED_SUPPORT_FINGERPRINTS[support]
    assert single.visualization is not None
    assert paired.visualization is not None
    assert (
        tuple(item.physical_element_id for item in single.visualization.support_material_regions)
        == elements
    )
    assert (
        tuple(item.physical_element_id for item in paired.visualization.support_material_regions)
        == elements
    )
    assert "CAVITY" not in elements
