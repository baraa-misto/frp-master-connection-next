"""Stage 3.7A controlled profile-matrix and golden verification."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from pydantic import ValidationError

import frp_master_connection.application.column_base_profile_orchestration as profile_module
from frp_master_connection.api.app import create_app
from frp_master_connection.api.column_base_web_angle_mapping import (
    map_column_base_web_angle_request,
    serialize_column_base_web_angle_preview,
)
from frp_master_connection.api.column_base_web_angle_schemas import (
    ColumnBaseProfileRequestDTO,
    ColumnBaseWideFlangeProfileDTO,
)
from frp_master_connection.application.column_base_web_angle_orchestration import (
    preview_column_base_web_angles,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.domain import (
    ChannelProfileDimensions,
    ColumnBaseAssembly,
    ColumnBaseSide,
    ComponentMaterialKind,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
    MemberRole,
    profile_member_axis_reference,
)
from tests.column_base_profile_fixtures import (
    build_column_base_profile_payload,
    build_column_base_profile_request,
)
from tests.column_base_web_angle_fixtures import build_column_base_signed_request

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = (
    ROOT
    / "backend/tests/golden"
    / "stage_3_7a_column_base_profile_matrix_expansion_golden_benchmarks_rc1.json"
)


def _post(path: str, payload: dict[str, object]) -> httpx.Response:
    async def send() -> httpx.Response:
        app = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)

    return asyncio.run(send())


def _exact_angle_orientation_result(
    *,
    selected_surface: str,
    single_side: str,
    assembly: str,
    signed_axial_force: str = "-20",
) -> profile_module.ColumnBaseProfilePreviewResult:
    payload = build_column_base_profile_payload(
        profile_family="ANGLE",
        assembly=assembly,
        selected_surface=selected_surface,
    )
    payload["single_side"] = single_side
    payload["signed_axial_force"] = {"value": signed_axial_force, "unit": "kip"}
    cast(dict[str, Any], payload["web_group"]).update(
        {
            "row_count": 2,
            "bolts_per_row": 1,
            "pitch": {"value": "1.5", "unit": "in"},
            "gauge": {"value": "2", "unit": "in"},
            "centroid_height_l": {"value": "2", "unit": "in"},
        }
    )
    return preview_column_base_web_angles(
        map_column_base_web_angle_request(ColumnBaseProfileRequestDTO.model_validate(payload))
    )


@pytest.mark.parametrize(
    ("relative", "digest", "sentinel"),
    [
        (
            "docs/governance/STAGE_3_7A_COLUMN_BASE_PROFILE_MATRIX_EXPANSION_DECISION.md",
            "D2B435F19D2F3F89035EB98B92A8F0D984C16595D1AA413D88CA5BA03F7854B1",
            "END OF STAGE 3.7A COLUMN-BASE PROFILE MATRIX EXPANSION DECISION",
        ),
        (
            "docs/engineering/STAGE_3_7A_COLUMN_BASE_PROFILE_MATRIX_EXPANSION_ENGINEERING_SPECIFICATION_RC1.md",
            "AEABF6E5146670E3D3598E6D538598A01D0AE00BEEA37F049B2E67A8D9DFEB5C",
            "END OF STAGE 3.7A COLUMN-BASE PROFILE MATRIX EXPANSION ENGINEERING SPECIFICATION RC1",
        ),
        (
            "backend/tests/golden/stage_3_7a_column_base_profile_matrix_expansion_golden_benchmarks_rc1.json",
            "D07174B4C347C3CDF391DA1DBDAE11E5D8D996506651BFC2848548874F2E6DBF",
            None,
        ),
        (
            "docs/qa/STAGE_3_7A_COLUMN_BASE_PROFILE_MATRIX_EXPANSION_AUTHORITY_LEDGER_RC1.md",
            "EA01458DBE3BE4E95F2946601017744E76B0347F221B5E1AD8762FEA189110B2",
            "END OF STAGE 3.7A COLUMN-BASE PROFILE MATRIX EXPANSION AUTHORITY LEDGER RC1",
        ),
    ],
)
def test_controlled_artifacts_are_byte_exact(
    relative: str, digest: str, sentinel: str | None
) -> None:
    data = (ROOT / relative).read_bytes()
    assert hashlib.sha256(data).hexdigest().upper() == digest
    if sentinel is not None:
        assert sentinel in (ROOT / relative).read_text(encoding="utf-8").rstrip().splitlines()[-1]


def test_golden_register_is_complete_g1_through_g60() -> None:
    payload = json.loads(GOLDEN.read_text(encoding="utf-8"))
    identifiers = [item["id"] for item in payload["benchmarks"]]
    assert len(identifiers) == 60
    assert len(set(identifiers)) == 60
    assert identifiers[0].startswith("G1_")
    assert identifiers[-1].startswith("G60_")
    assert payload["successor_contract"] == "3.7A-RC1"


def test_successor_transport_rejects_blank_profile_and_request_ids() -> None:
    payload = build_column_base_profile_payload(profile_family="WIDE_FLANGE_I")
    profile_payload = cast(dict[str, Any], payload["column_profile"])
    profile_payload["profile_id"] = " "
    with pytest.raises(ValidationError, match="profile_id must be nonempty"):
        ColumnBaseWideFlangeProfileDTO.model_validate(profile_payload)
    payload = build_column_base_profile_payload()
    payload["request_id"] = " "
    with pytest.raises(ValidationError, match="request_id must be nonempty"):
        ColumnBaseProfileRequestDTO.model_validate(payload)


def test_member_axis_reference_rejects_non_profile() -> None:
    with pytest.raises(TypeError, match="profile must be a MemberProfile"):
        profile_member_axis_reference(cast(Any, object()))


def test_successor_domain_contract_rejects_every_closed_boundary() -> None:
    request = build_column_base_profile_request(profile_family="WIDE_FLANGE_I")
    angle_request = build_column_base_profile_request(profile_family="ANGLE")
    profile = request.column_profile
    cases: tuple[tuple[Callable[[], object], type[Exception], str], ...] = (
        (lambda: replace(request, request_id=" "), ValueError, "request_id"),
        (lambda: replace(request, contract_version="wrong"), ValueError, "contract version"),
        (lambda: replace(request, source_length_unit=Unit.MM), ValueError, "Source length unit"),
        (
            lambda: replace(request, column_profile=cast(Any, object())),
            TypeError,
            "column_profile",
        ),
        (
            lambda: replace(request, column_profile=replace(profile, role=MemberRole.BRACE)),
            ValueError,
            "pultruded FRP column",
        ),
        (
            lambda: replace(
                request,
                column_profile=replace(
                    profile,
                    material_kind=ComponentMaterialKind.STEEL,
                    material_orientation=None,
                ),
            ),
            ValueError,
            "pultruded FRP column",
        ),
        (
            lambda: replace(
                request,
                column_profile=replace(
                    profile,
                    family=MemberProfileFamily.CHANNEL,
                    dimensions=ChannelProfileDimensions(
                        Decimal("24"),
                        Decimal("10"),
                        Decimal("8"),
                        Decimal("0.5"),
                        Decimal("0.5"),
                    ),
                    selected_surface=MemberProfileSurfaceId.WEB_OUTER,
                ),
            ),
            ValueError,
            "Unsupported Stage 3.7A column profile",
        ),
        (
            lambda: replace(request, assembly=ColumnBaseAssembly.SYMMETRIC_DOUBLE_BASE_ANGLES),
            ValueError,
            "only Single or Double",
        ),
        (
            lambda: replace(angle_request, angle_double_topology="DIFFERENT_LEGS"),
            ValueError,
            "TWO_DIFFERENT_LEGS",
        ),
        (
            lambda: replace(request, web_bolt_diameter=request.signed_axial_force),
            ValueError,
            "diameters",
        ),
        (
            lambda: replace(request, web_bolt_diameter=PhysicalQuantity.of("0", Unit.IN)),
            ValueError,
            "diameters",
        ),
        (
            lambda: replace(request, web_hole_diameter=PhysicalQuantity.of("0.25", Unit.IN)),
            ValueError,
            "smaller",
        ),
        (
            lambda: replace(request, signed_axial_force=request.web_bolt_diameter),
            ValueError,
            "force quantities",
        ),
        (
            lambda: replace(
                request,
                user_moment=cast(
                    Any,
                    SimpleNamespace(
                        s=PhysicalQuantity.of("1", Unit.IN),
                        t=PhysicalQuantity.of("0", Unit.IN),
                        longitudinal=PhysicalQuantity.of("0", Unit.IN),
                    ),
                ),
            ),
            ValueError,
            "USER_APPLIED_MOMENT",
        ),
        (
            lambda: replace(
                request,
                user_moment=replace(
                    request.user_moment,
                    s=PhysicalQuantity.of("1", Unit.KIP_IN),
                ),
            ),
            ValueError,
            "USER_APPLIED_MOMENT",
        ),
    )
    for invalid, error, match in cases:
        with pytest.raises(error, match=match):
            invalid()


def test_fingerprint_normalizer_canonicalizes_dictionary_order() -> None:
    assert profile_module._fingerprint_normalize({"b": 2, "a": 1}) == (
        ("a", 1),
        ("b", 2),
    )


def test_rotated_profile_and_negative_side_single_use_backend_frame() -> None:
    request = build_column_base_profile_request(
        profile_family="ANGLE",
        assembly="SINGLE_BASE_ANGLE",
    )
    rotated = replace(
        request,
        column_profile=replace(
            request.column_profile,
            orientation=MemberProfileOrientation.ROTATION_90,
        ),
        single_side=ColumnBaseSide.NEGATIVE_T_C,
    )
    result = preview_column_base_web_angles(rotated)
    assert result.geometry_status.value == "VALID"
    assert result.visualization is not None
    owners = {item.owner_id for item in result.visualization.boxes}
    assert "negative-base-angle" in owners
    assert "positive-base-angle" not in owners


@pytest.mark.parametrize("selected_surface", ["LEG_Y_OUTER", "LEG_Z_OUTER"])
@pytest.mark.parametrize(
    (
        "assembly",
        "single_side",
        "expected_start_t",
        "expected_end_t",
        "expected_axis_t",
        "expected_layers",
    ),
    [
        (
            "SINGLE_BASE_ANGLE",
            "+T_C",
            Decimal("0.5"),
            Decimal("-0.5"),
            Decimal("-1"),
            ("POSITIVE_BASE_ANGLE_VERTICAL_LEG", "SELECTED_ANGLE_COLUMN_LEG"),
        ),
        (
            "SINGLE_BASE_ANGLE",
            "-T_C",
            Decimal("-1.0"),
            Decimal("0"),
            Decimal("1"),
            ("NEGATIVE_BASE_ANGLE_VERTICAL_LEG", "SELECTED_ANGLE_COLUMN_LEG"),
        ),
        (
            "DOUBLE_BASE_ANGLES",
            "+T_C",
            Decimal("0.5"),
            Decimal("-1.0"),
            Decimal("-1"),
            (
                "POSITIVE_BASE_ANGLE_VERTICAL_LEG",
                "SELECTED_ANGLE_COLUMN_LEG",
                "NEGATIVE_BASE_ANGLE_VERTICAL_LEG",
            ),
        ),
    ],
)
def test_angle_single_face_and_double_bolt_orientation_matrix(
    selected_surface: str,
    assembly: str,
    single_side: str,
    expected_start_t: Decimal,
    expected_end_t: Decimal,
    expected_axis_t: Decimal,
    expected_layers: tuple[str, ...],
) -> None:
    result = _exact_angle_orientation_result(
        selected_surface=selected_surface,
        single_side=single_side,
        assembly=assembly,
    )
    assert result.geometry_status.value == "VALID"
    assert result.visualization is not None
    expected_engineering_fingerprint = {
        ("LEG_Y_OUTER", "SINGLE_BASE_ANGLE", "+T_C"): (
            "1d41db61599618dfbefc495bfec8319837900a1e8bb65ed836e15e3e4a330a86"
        ),
        ("LEG_Y_OUTER", "SINGLE_BASE_ANGLE", "-T_C"): (
            "e3595b4ad56e37c57d1281b99c4154140e423cf4f6a6f8b944a600b0b2dd7999"
        ),
        ("LEG_Z_OUTER", "SINGLE_BASE_ANGLE", "+T_C"): (
            "3010e376a70b0937fb15e453287f3c147e1c2db5306952430a4a129192e03f7f"
        ),
        ("LEG_Z_OUTER", "SINGLE_BASE_ANGLE", "-T_C"): (
            "e1c9aab26cdd7108d564c99c78d64d66cd50eabdb3061dc046243b8c73b633e9"
        ),
        ("LEG_Y_OUTER", "DOUBLE_BASE_ANGLES", "+T_C"): (
            "42dc3e9e7cad40c01256a89cdf8321f7198439fcd6c5dee75b747f905f6d5e37"
        ),
        ("LEG_Z_OUTER", "DOUBLE_BASE_ANGLES", "+T_C"): (
            "646eaf0151388384042d7286b7ac1686fb663258720bb2175176176f1468c56b"
        ),
    }[(selected_surface, assembly, single_side)]
    expected_path_fingerprints = (
        (
            "a6ab52edfa37171fa59440201d8b90e18e944236c2286c3c41886291b249affc",
            "f7cade8f592a3128d5fe67b42552479df71661deb3ead7938a370606ab9458c0",
        )
        if single_side == "-T_C"
        else (
            "bf42cf34bbe76df6abe0db63b30904b140443eaa40c92865d42dd5d1f5fce521",
            "ce289ff37a8d763ac2af5f136bfdbd09019144058ba838117da931e6f3522a68",
        )
        if assembly == "DOUBLE_BASE_ANGLES"
        else (
            "56121df73a3f4f8de48fb30446b0752bd7b9df33c24bec36e25143b268bd81f8",
            "d3b9227d7586e27ad0571a0259a0e67c52729680ab47da083e8d062c619c8710",
        )
    )
    assert result.engineering_fingerprint == expected_engineering_fingerprint
    assert len(result.physical_bolt_paths) == len(result.visualization.web_bolts) == 2
    assert {
        box.physical_element_id for box in result.visualization.boxes if box.owner_id == "column"
    } == {"COLUMN_LEG_1", "COLUMN_LEG_2"}
    for path, bolt, expected_path_fingerprint in zip(
        result.physical_bolt_paths,
        result.visualization.web_bolts,
        expected_path_fingerprints,
        strict=True,
    ):
        assert tuple(item.identity for item in path.segments) == expected_layers
        assert path.path_fingerprint == expected_path_fingerprint
        assert path.stack_start_s_t_l[1].magnitude == expected_start_t
        assert path.stack_end_s_t_l[1].magnitude == expected_end_t
        assert bolt.stack_start == path.stack_start_s_t_l
        assert bolt.stack_end == path.stack_end_s_t_l
        assert bolt.axis == (Decimal(0), expected_axis_t, Decimal(0))
        assert path.physical_bolt_count == path.continuous_shank_count == 1
        assert path.internal_hardware_count == 0
        assert path.head_location == "EXTERIOR_NEAR_SIDE"
        assert path.nut_location == "EXTERIOR_FAR_SIDE"
        assert path.washer_locations == ("EXTERIOR_NEAR_SIDE", "EXTERIOR_FAR_SIDE")
        assert abs(expected_end_t - expected_start_t) == sum(
            (segment.length.magnitude for segment in path.segments), start=Decimal(0)
        )


@pytest.mark.parametrize("selected_surface", ["LEG_Y_OUTER", "LEG_Z_OUTER"])
def test_angle_face_reversal_changes_only_physical_path_geometry(
    selected_surface: str,
) -> None:
    positive = _exact_angle_orientation_result(
        selected_surface=selected_surface,
        single_side="+T_C",
        assembly="SINGLE_BASE_ANGLE",
    )
    negative = _exact_angle_orientation_result(
        selected_surface=selected_surface,
        single_side="-T_C",
        assembly="SINGLE_BASE_ANGLE",
    )
    assert positive.connection_frame == negative.connection_frame
    assert positive.member_action_reference_s_t_l == negative.member_action_reference_s_t_l
    assert positive.web_group_demand == negative.web_group_demand
    assert tuple(
        (
            item.material_axis,
            item.material_axis_angle_degrees,
            item.bearing_direction_classification,
            item.force_direction_s_l,
        )
        for item in positive.layer_directions
    ) == tuple(
        (
            item.material_axis,
            item.material_axis_angle_degrees,
            item.bearing_direction_classification,
            item.force_direction_s_l,
        )
        for item in negative.layer_directions
    )
    assert positive.combined_foundation_wrench == negative.combined_foundation_wrench
    assert positive.external_handoff.combined_foundation_wrench == (
        negative.external_handoff.combined_foundation_wrench
    )
    assert positive.application_fingerprint != negative.application_fingerprint
    assert positive.engineering_fingerprint != negative.engineering_fingerprint


@pytest.mark.parametrize("selected_surface", ["LEG_Y_OUTER", "LEG_Z_OUTER"])
def test_angle_double_uplift_retains_the_physical_path(
    selected_surface: str,
) -> None:
    compression = _exact_angle_orientation_result(
        selected_surface=selected_surface,
        single_side="+T_C",
        assembly="DOUBLE_BASE_ANGLES",
    )
    uplift = _exact_angle_orientation_result(
        selected_surface=selected_surface,
        single_side="+T_C",
        assembly="DOUBLE_BASE_ANGLES",
        signed_axial_force="20",
    )
    assert uplift.component_transfer.axial_mode == "UPLIFT"
    assert uplift.connection_frame == compression.connection_frame
    assert uplift.member_action_reference_s_t_l == compression.member_action_reference_s_t_l
    assert uplift.physical_bolt_paths == compression.physical_bolt_paths
    assert uplift.visualization is not None
    assert compression.visualization is not None
    assert uplift.visualization.web_bolts == compression.visualization.web_bolts


def test_full_through_containment_and_angle_path_fail_closed() -> None:
    rectangular_payload = build_column_base_profile_payload(
        profile_family="RECTANGULAR_HOLLOW_SECTION"
    )
    rectangular_payload["web_hole_diameter"] = {"value": "9", "unit": "in"}
    rectangular = preview_column_base_web_angles(
        map_column_base_web_angle_request(
            ColumnBaseProfileRequestDTO.model_validate(rectangular_payload)
        )
    )
    assert rectangular.geometry_status.value == "INVALID_GEOMETRY"
    assert any(
        item.startswith("FULL_THROUGH_HOLE_CONTAINMENT_INVALID")
        for item in rectangular.geometry_invalid_reasons
    )

    angle_request = build_column_base_profile_request(profile_family="ANGLE")
    angle = preview_column_base_web_angles(
        replace(
            angle_request,
            web_layout=replace(angle_request.web_layout, width_offset=Decimal("20")),
        )
    )
    assert angle.geometry_status.value == "INVALID_GEOMETRY"
    assert any(
        item.startswith("ANGLE_BOLT_PATH_INVALID") for item in angle.geometry_invalid_reasons
    )


def test_excessive_anchor_embedment_fails_closed() -> None:
    request = build_column_base_profile_request()
    result = preview_column_base_web_angles(
        replace(
            request,
            external_anchor=replace(
                request.external_anchor,
                specified_embedment=PhysicalQuantity.of("13", Unit.IN),
            ),
        )
    )
    assert result.geometry_status.value == "INVALID_GEOMETRY"
    assert "ANCHOR_EMBEDMENT_EXCEEDS_CONCRETE_DEPTH" in result.geometry_invalid_reasons


def test_wide_flange_fallback_bolts_are_retained_without_historical_scene(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = build_column_base_profile_request(profile_family="WIDE_FLANGE_I")
    profile_module_any = cast(Any, profile_module)
    original_preview = profile_module_any._preview

    def preview_without_scene(value: object, *, resistance: bool) -> tuple[object, object]:
        preview, design = original_preview(cast(Any, value), resistance=resistance)
        return replace(preview, visualization=None), design

    monkeypatch.setattr(profile_module, "_preview", preview_without_scene)
    result = preview_column_base_web_angles(request)
    assert result.geometry_status.value == "VALID"
    assert result.visualization is not None
    assert len(result.visualization.web_bolts) == 4


@pytest.mark.parametrize(
    "profile_family",
    [
        "WIDE_FLANGE_I",
        "RECTANGULAR_HOLLOW_SECTION",
        "SOLID_RECTANGULAR_SECTION",
        "ANGLE",
    ],
)
@pytest.mark.parametrize("assembly", ["SINGLE_BASE_ANGLE", "DOUBLE_BASE_ANGLES"])
def test_complete_profile_assembly_matrix_is_valid(profile_family: str, assembly: str) -> None:
    result = preview_column_base_web_angles(
        build_column_base_profile_request(
            profile_family=profile_family,
            assembly=assembly,
        )
    )
    assert result.orchestration_contract_version == "3.7A-RC1"
    assert result.profile_family == profile_family
    assert result.geometry_status.value == "VALID"
    assert result.resistance_evaluated is False
    assert result.ordinary_pass_allowed is False
    assert result.component_transfer.column_fraction == Decimal(1)
    assert result.component_transfer.base_angle_system_fraction == Decimal(1)
    assert result.component_transfer.component_design_demands_summed_for_equilibrium is False


@pytest.mark.parametrize(
    ("profile_family", "assembly", "expected"),
    [
        (
            "RECTANGULAR_HOLLOW_SECTION",
            "SINGLE_BASE_ANGLE",
            (
                "POSITIVE_BASE_ANGLE_VERTICAL_LEG",
                "RHS_NEAR_WALL",
                "FREE_SHANK_CAVITY",
                "RHS_FAR_WALL",
            ),
        ),
        (
            "RECTANGULAR_HOLLOW_SECTION",
            "DOUBLE_BASE_ANGLES",
            (
                "POSITIVE_BASE_ANGLE_VERTICAL_LEG",
                "RHS_NEAR_WALL",
                "FREE_SHANK_CAVITY",
                "RHS_FAR_WALL",
                "NEGATIVE_BASE_ANGLE_VERTICAL_LEG",
            ),
        ),
        (
            "SOLID_RECTANGULAR_SECTION",
            "SINGLE_BASE_ANGLE",
            ("POSITIVE_BASE_ANGLE_VERTICAL_LEG", "SOLID_RECTANGULAR_COLUMN"),
        ),
        (
            "SOLID_RECTANGULAR_SECTION",
            "DOUBLE_BASE_ANGLES",
            (
                "POSITIVE_BASE_ANGLE_VERTICAL_LEG",
                "SOLID_RECTANGULAR_COLUMN",
                "NEGATIVE_BASE_ANGLE_VERTICAL_LEG",
            ),
        ),
        (
            "ANGLE",
            "DOUBLE_BASE_ANGLES",
            (
                "POSITIVE_BASE_ANGLE_VERTICAL_LEG",
                "SELECTED_ANGLE_COLUMN_LEG",
                "NEGATIVE_BASE_ANGLE_VERTICAL_LEG",
            ),
        ),
    ],
)
def test_physical_path_matrix(
    profile_family: str, assembly: str, expected: tuple[str, ...]
) -> None:
    result = preview_column_base_web_angles(
        build_column_base_profile_request(
            profile_family=profile_family,
            assembly=assembly,
        )
    )
    assert {
        tuple(item.identity for item in path.segments) for path in result.physical_bolt_paths
    } == {expected}
    assert all(path.physical_bolt_count == 1 for path in result.physical_bolt_paths)
    assert all(path.continuous_shank_count == 1 for path in result.physical_bolt_paths)
    assert all(path.internal_hardware_count == 0 for path in result.physical_bolt_paths)
    for path in result.physical_bolt_paths:
        serialized_span = abs(
            path.stack_start_s_t_l[1].magnitude - path.stack_end_s_t_l[1].magnitude
        )
        assert serialized_span == sum(
            (segment.length.magnitude for segment in path.segments), start=Decimal(0)
        )
    if profile_family == "RECTANGULAR_HOLLOW_SECTION":
        cavity = next(
            item
            for item in result.physical_bolt_paths[0].segments
            if item.identity == "FREE_SHANK_CAVITY"
        )
        assert cavity.kind == "FREE_SHANK_SPAN"
        assert cavity.length.magnitude == Decimal("7")
        assert cavity.material_region_id is None
        assert cavity.has_material_axes is False
    if profile_family == "SOLID_RECTANGULAR_SECTION":
        assert all(
            item.kind != "FREE_SHANK_SPAN" for item in result.physical_bolt_paths[0].segments
        )


@pytest.mark.parametrize("selected_surface", ["LEG_Y_OUTER", "LEG_Z_OUTER"])
def test_angle_centroid_reference_and_other_leg_are_backend_authored(
    selected_surface: str,
) -> None:
    request = build_column_base_profile_request(
        profile_family="ANGLE",
        selected_surface=selected_surface,
    )
    centroid = profile_member_axis_reference(request.column_profile)
    assert centroid.y == centroid.z == Decimal("1.684782608695652173913043478")
    result = preview_column_base_web_angles(request)
    assert result.visualization is not None
    assert result.member_action_reference_s_t_l == result.visualization.action_reference_s_t_l
    assert result.combined_foundation_wrench.moment_s_t_l.s.canonical_magnitude != 0
    column_roles = {
        box.physical_element_id for box in result.visualization.boxes if box.owner_id == "column"
    }
    assert {"COLUMN_LEG_1", "COLUMN_LEG_2"} <= column_roles
    assert (
        len(
            [
                item
                for item in result.visualization.material_regions
                if "COLUMN_LEG" in item.physical_element_id
            ]
        )
        == 2
    )


def test_successor_wide_flange_physical_shape_and_material_axes_match_historical() -> None:
    historical = preview_column_base_web_angles(build_column_base_signed_request())
    successor = preview_column_base_web_angles(
        build_column_base_profile_request(profile_family="WIDE_FLANGE_I")
    )
    assert historical.visualization is not None
    assert successor.visualization is not None
    historical_boxes = tuple(
        item for item in historical.visualization.boxes if item.owner_id == "column"
    )
    successor_boxes = tuple(
        item for item in successor.visualization.boxes if item.owner_id == "column"
    )
    assert successor_boxes == historical_boxes
    historical_axes = tuple(
        item
        for item in historical.visualization.material_regions
        if item.physical_element_id.startswith("COLUMN_")
    )
    successor_axes = tuple(
        item
        for item in successor.visualization.material_regions
        if item.physical_element_id.startswith("COLUMN_")
    )
    assert successor_axes == historical_axes


def test_angle_double_retains_local_provenance_without_fabricated_branch_wrenches() -> None:
    result = preview_column_base_web_angles(
        build_column_base_profile_request(profile_family="ANGLE")
    )
    fractions = {item.layer_id: item.fraction_of_parent for item in result.layer_demands}
    assert fractions["POSITIVE_BASE_ANGLE_VERTICAL_LEG"] == Decimal("0.5")
    assert fractions["SELECTED_ANGLE_COLUMN_LEG"] == Decimal("1")
    assert fractions["NEGATIVE_BASE_ANGLE_VERTICAL_LEG"] == Decimal("0.5")
    assert result.symmetry_proof.angle_local_common_group_half_sharing_eligible is True
    assert result.symmetry_proof.complete_branch_half_sharing_eligible is False
    assert all(group.branch_wrench is None for group in result.anchor_groups)
    assert (
        "ANGLE_COLUMN_BASE_ANGLE_BRANCH_WRENCH_ALLOCATION",
        "NOT_EVALUATED",
    ) in result.limitations


@pytest.mark.parametrize(
    "profile_family", ["RECTANGULAR_HOLLOW_SECTION", "SOLID_RECTANGULAR_SECTION"]
)
def test_rectangular_double_symmetry_requires_zero_normal_action(profile_family: str) -> None:
    symmetric = preview_column_base_web_angles(
        build_column_base_profile_request(profile_family=profile_family)
    )
    assert symmetric.symmetry_proof.complete_branch_half_sharing_eligible is True
    assert all(group.branch_wrench is not None for group in symmetric.anchor_groups)
    normal = preview_column_base_web_angles(
        build_column_base_profile_request(
            profile_family=profile_family,
            connection_normal_shear="2",
        )
    )
    assert normal.symmetry_proof.complete_branch_half_sharing_eligible is False
    assert all(group.branch_wrench is None for group in normal.anchor_groups)
    assert ("CONNECTION_NORMAL_BOLT_AXIS_RESPONSE", "NOT_EVALUATED") in normal.limitations


def test_angle_interference_fails_closed_without_repositioning() -> None:
    request = build_column_base_profile_request(profile_family="ANGLE")
    invalid = replace(request, angle=replace(request.angle, connector_length=Decimal("5.75")))
    result = preview_column_base_web_angles(invalid)
    assert result.geometry_status.value == "INVALID_GEOMETRY"
    assert (
        "ANGLE_CONNECTOR_HEEL_OR_PERPENDICULAR_LEG_INTERFERENCE" in result.geometry_invalid_reasons
    )
    assert result.visualization is None


def test_future_angle_different_leg_topology_is_rejected() -> None:
    payload = build_column_base_profile_payload(profile_family="ANGLE")
    payload["angle_double_topology"] = "DIFFERENT_LEGS"
    with pytest.raises(ValidationError):
        ColumnBaseProfileRequestDTO.model_validate(payload)


@pytest.mark.parametrize(
    "profile_family",
    [
        "WIDE_FLANGE_I",
        "RECTANGULAR_HOLLOW_SECTION",
        "SOLID_RECTANGULAR_SECTION",
        "ANGLE",
    ],
)
def test_us_si_successor_fingerprints_are_equal(profile_family: str) -> None:
    us = preview_column_base_web_angles(
        build_column_base_profile_request(profile_family=profile_family)
    )
    si = preview_column_base_web_angles(
        build_column_base_profile_request(profile_family=profile_family, unit_system="SI")
    )
    assert us.external_handoff.input_fingerprint == si.external_handoff.input_fingerprint
    assert us.external_handoff.handoff_fingerprint == si.external_handoff.handoff_fingerprint
    assert us.application_fingerprint == si.application_fingerprint
    assert us.engineering_fingerprint == si.engineering_fingerprint
    assert [item.path_fingerprint for item in us.physical_bolt_paths] == [
        item.path_fingerprint for item in si.physical_bolt_paths
    ]


def test_api_serialization_accepts_successor_without_changing_historical_contract() -> None:
    successor = preview_column_base_web_angles(build_column_base_profile_request())
    serialized = serialize_column_base_web_angle_preview(successor)
    assert serialized.orchestration_contract_version == "3.7A-RC1"
    assert serialized.result["profile_family"] == "RECTANGULAR_HOLLOW_SECTION"
    historical_request = build_column_base_signed_request()
    historical = preview_column_base_web_angles(historical_request)
    assert historical.orchestration_contract_version == "3.5C-R2-RC1"
    assert (
        historical.engineering_fingerprint
        == preview_column_base_web_angles(historical_request).engineering_fingerprint
    )


@pytest.mark.parametrize(
    "profile_family",
    [
        "WIDE_FLANGE_I",
        "RECTANGULAR_HOLLOW_SECTION",
        "SOLID_RECTANGULAR_SECTION",
        "ANGLE",
    ],
)
def test_stateless_api_exposes_every_successor_profile_without_automatic_resistance(
    profile_family: str,
) -> None:
    payload = build_column_base_profile_payload(profile_family=profile_family)
    preview = _post("/api/v1/calculations/column-base-web-angles/preview", payload)
    design = _post("/api/v1/calculations/column-base-web-angles/design-check", payload)
    assert preview.status_code == design.status_code == 200
    assert preview.json()["orchestration_contract_version"] == "3.7A-RC1"
    assert preview.json()["resistance_evaluated"] is False
    assert preview.json()["result"]["profile_family"] == profile_family
    assert design.json()["ordinary_pass_allowed"] is False
    if profile_family != "WIDE_FLANGE_I":
        assert design.json()["result"]["web_group_resistance"] is None


def test_successor_api_rejects_unknown_profile_and_different_leg_topology() -> None:
    unknown = build_column_base_profile_payload()
    unknown["column_profile"]["profile_family"] = "CHANNEL"
    assert _post("/api/v1/calculations/column-base-web-angles/preview", unknown).status_code == 422
    different_leg = build_column_base_profile_payload(profile_family="ANGLE")
    different_leg["angle_double_topology"] = "DIFFERENT_LEGS"
    assert (
        _post("/api/v1/calculations/column-base-web-angles/preview", different_leg).status_code
        == 422
    )
