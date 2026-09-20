"""Stage 3.4B profile/support expansion and historical-boundary regressions."""

from __future__ import annotations

import asyncio
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

import frp_master_connection.api.multi_member_tee_mapping as mapping_module
from frp_master_connection.api.app import create_app
from frp_master_connection.api.multi_member_tee_mapping import map_multi_member_tee_request
from frp_master_connection.api.multi_member_tee_schemas import MultiMemberTeeRequestDTO
from frp_master_connection.application.multi_member_tee_orchestration import (
    MULTI_MEMBER_TEE_EXPANDED_ORCHESTRATION_CONTRACT_VERSION,
    MultiMemberTeeAssemblyStatus,
    MultiMemberTeePreviewResult,
    preview_multi_member_tee,
)
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.domain import MemberProfileFamily, SharedSupportTargetId
from tests.multi_member_tee_fixtures import (
    build_expanded_multi_member_tee_payload,
    build_multi_member_tee_payload,
)

_FAMILIES = tuple(
    item.value
    for item in (
        MemberProfileFamily.FLAT_PLATE,
        MemberProfileFamily.ANGLE,
        MemberProfileFamily.CHANNEL,
        MemberProfileFamily.WIDE_FLANGE_I,
        MemberProfileFamily.RECTANGULAR_HOLLOW_SECTION,
        MemberProfileFamily.SOLID_RECTANGULAR_SECTION,
    )
)
_TARGETS = tuple(item.value for item in SharedSupportTargetId)
_REPOSITORY_ROOT = Path(__file__).parents[3]
_CONTROLLED_ARTIFACTS = (
    (
        _REPOSITORY_ROOT
        / "docs/governance/STAGE_3_4B_MULTI_MEMBER_TEE_PROFILE_SUPPORT_EXPANSION_DECISION.md",
        "2300908F7CC45E6385A7C55C180A5946A96278D82067AA60C2ED1C44DB2C564A",
        b"**END OF STAGE 3.4B MULTI-MEMBER TEE PROFILE AND SUPPORT EXPANSION DECISION**",
    ),
    (
        _REPOSITORY_ROOT
        / "docs/engineering"
        / "STAGE_3_4B_MULTI_MEMBER_TEE_PROFILE_SUPPORT_EXPANSION_ENGINEERING_SPECIFICATION_RC1.md",
        "A35DEDF8280B6C4E91D486D9777E95750423D055C45AC26FB64AFA8531B59BDD",
        b"**END OF CONTROLLED ENGINEERING SPECIFICATION \xe2\x80\x94 RC1**",
    ),
    (
        _REPOSITORY_ROOT
        / "backend/tests/golden"
        / "stage_3_4b_multi_member_tee_profile_support_expansion_golden_benchmarks_rc1.json",
        "ED98DD604A126B9A4B122A5569AC7CEAE3C3D0B4608422E2955246583B97FC36",
        None,
    ),
    (
        _REPOSITORY_ROOT
        / "docs/qa/STAGE_3_4B_MULTI_MEMBER_TEE_PROFILE_SUPPORT_EXPANSION_AUTHORITY_LEDGER_RC1.md",
        "3A43B82BACA61DB79CCB1EAD49E71F2E746DED318638C2CF685AB835124F0F6F",
        b"**END OF AUTHORITY LEDGER RC1**",
    ),
)


def _preview(payload: dict[str, object]) -> MultiMemberTeePreviewResult:
    dto = MultiMemberTeeRequestDTO.model_validate(payload)
    return preview_multi_member_tee(map_multi_member_tee_request(dto))


def _post(path: str, payload: dict[str, object]) -> httpx.Response:
    async def send() -> httpx.Response:
        application = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://testserver"
        ) as client:
            return await client.post(path, json=payload)

    return asyncio.run(send())


def test_g1_through_g28_fixture_is_complete_and_never_a_production_input() -> None:
    path = (
        Path(__file__).parents[1]
        / "golden"
        / ("stage_3_4b_multi_member_tee_profile_support_expansion_golden_benchmarks_rc1.json")
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    assert [item["id"].split("_", maxsplit=1)[0] for item in value["benchmarks"]] == [
        f"G{index}" for index in range(1, 29)
    ]
    production = Path(__file__).parents[2] / "src" / "frp_master_connection"
    assert all(
        "stage_3_4b_multi_member_tee_profile_support_expansion_golden"
        not in item.read_text(encoding="utf-8")
        for item in production.rglob("*.py")
    )


def test_controlled_artifact_hashes_and_final_sentinels_are_exact() -> None:
    for path, expected_hash, sentinel in _CONTROLLED_ARTIFACTS:
        content = path.read_bytes()
        assert hashlib.sha256(content).hexdigest().upper() == expected_hash
        if sentinel is not None:
            assert content.rstrip().endswith(sentinel)


@pytest.mark.parametrize("slot", ["UPPER_BRACE", "MIDDLE_BEAM", "LOWER_BRACE"])
@pytest.mark.parametrize("family", _FAMILIES)
def test_all_six_profiles_are_accepted_in_every_semantic_slot(slot: str, family: str) -> None:
    defaults = ["ANGLE", "WIDE_FLANGE_I", "ANGLE"]
    index = ("UPPER_BRACE", "MIDDLE_BEAM", "LOWER_BRACE").index(slot)
    defaults[index] = family
    result = _preview(
        build_expanded_multi_member_tee_payload(
            active_slots=(slot,),
            profile_families=tuple(defaults),  # type: ignore[arg-type]
        )
    )
    assert (
        result.orchestration_contract_version
        == MULTI_MEMBER_TEE_EXPANDED_ORCHESTRATION_CONTRACT_VERSION
    )
    assert result.assembly_status is MultiMemberTeeAssemblyStatus.NOT_EVALUATED
    assert result.slots[0].profile is not None
    assert result.slots[0].profile.profile_family.value == family
    assert result.visualization is not None
    snapshot = result.visualization.slots[0].visualization
    material_axes = (
        *snapshot.base_connection.material_directions,
        *snapshot.interface_b_connection.material_directions,
    )
    assert {item.component_id for item in material_axes} >= {
        "tee-brace",
        "tee-connector",
        "tee-support",
    }
    assert all(item.physical_element_id != "RHS_CAVITY" for item in material_axes)
    if family == "RECTANGULAR_HOLLOW_SECTION":
        connected_paths = tuple(
            item
            for item in snapshot.rectangular_full_through_paths
            if item.path.segments[0].identity == "TEE_STEM"
        )
        assert len(connected_paths) == 4
        assert {
            tuple(segment.identity for segment in item.path.segments) for item in connected_paths
        } == {("TEE_STEM", "RHS_NEAR_WALL", "RHS_CAVITY", "RHS_FAR_WALL")}
        assert all(item.hardware.internal_hardware_count == 0 for item in connected_paths)
    elif family == "SOLID_RECTANGULAR_SECTION":
        connected_paths = tuple(
            item
            for item in snapshot.rectangular_full_through_paths
            if item.path.segments[0].identity == "TEE_STEM"
        )
        assert len(connected_paths) == 4
        assert {
            tuple(segment.identity for segment in item.path.segments) for item in connected_paths
        } == {("TEE_STEM", "SOLID_RECTANGULAR_SECTION")}


@pytest.mark.parametrize("target", _TARGETS)
def test_all_seven_shared_support_targets_are_accepted(target: str) -> None:
    result = _preview(
        build_expanded_multi_member_tee_payload(
            active_slots=("UPPER_BRACE",),
            support_target=target,
        )
    )
    assert result.assembly_status is MultiMemberTeeAssemblyStatus.NOT_EVALUATED
    assert result.support.profile is not None
    assert result.visualization is not None
    snapshot = result.visualization.slots[0].visualization
    assert snapshot.support_target_id.value == target
    material_axes = (
        *snapshot.base_connection.material_directions,
        *snapshot.interface_b_connection.material_directions,
    )
    assert {item.component_id for item in material_axes} >= {
        "tee-brace",
        "tee-connector",
        "tee-support",
    }
    if target == "RECTANGULAR_HOLLOW_COLUMN_WALL":
        support_paths = tuple(
            item
            for item in snapshot.rectangular_full_through_paths
            if item.path.segments[0].identity == "TEE_FLANGE"
        )
        assert len(support_paths) == 4
        assert {
            tuple(segment.identity for segment in item.path.segments) for item in support_paths
        } == {("TEE_FLANGE", "RHS_NEAR_WALL", "RHS_CAVITY", "RHS_FAR_WALL")}
        assert all(item.hardware.internal_hardware_count == 0 for item in support_paths)
    elif target == "SOLID_RECTANGULAR_COLUMN_FACE":
        support_paths = tuple(
            item
            for item in snapshot.rectangular_full_through_paths
            if item.path.segments[0].identity == "TEE_FLANGE"
        )
        assert len(support_paths) == 4
        assert {
            tuple(segment.identity for segment in item.path.segments) for item in support_paths
        } == {("TEE_FLANGE", "SOLID_RECTANGULAR_SECTION")}


@pytest.mark.parametrize("family", _FAMILIES)
def test_all_six_profiles_use_actual_trimmed_solids_without_moving_the_group(
    family: str,
) -> None:
    payload = build_expanded_multi_member_tee_payload(
        active_slots=("UPPER_BRACE",),
        profile_families=(family, "WIDE_FLANGE_I", "ANGLE"),
    )
    upper = payload["upper_brace"]
    assert isinstance(upper, dict)
    upper["trim_enabled"] = True
    upper["trim_clearance"] = {"value": "0", "unit": "in"}
    trimmed = _preview(payload)
    untrimmed = _preview(
        build_expanded_multi_member_tee_payload(
            active_slots=("UPPER_BRACE",),
            profile_families=(family, "WIDE_FLANGE_I", "ANGLE"),
        )
    )
    trace = trimmed.slots[0].trim
    assert trace is not None
    assert trace.geometry_valid
    assert trace.trimmed_member_geometry_identity is not None
    assert trace.fabricated_trim_edge_ids
    assert trace.minimum_hole_edge_clearance is not None
    assert trimmed.slots[0].placement == untrimmed.slots[0].placement
    assert trimmed.visualization is not None
    assert untrimmed.visualization is not None
    trimmed_geometry = trimmed.visualization.slots[0].visualization.base_connection.primitives
    untrimmed_geometry = untrimmed.visualization.slots[0].visualization.base_connection.primitives
    assert trimmed_geometry != untrimmed_geometry


@pytest.mark.parametrize(
    "active_slots",
    [
        ("UPPER_BRACE",),
        ("MIDDLE_BEAM",),
        ("LOWER_BRACE",),
        ("UPPER_BRACE", "MIDDLE_BEAM"),
        ("UPPER_BRACE", "LOWER_BRACE"),
        ("MIDDLE_BEAM", "LOWER_BRACE"),
        ("UPPER_BRACE", "MIDDLE_BEAM", "LOWER_BRACE"),
    ],
)
def test_all_expanded_slot_combinations_are_valid_and_omit_inactive_slots(
    active_slots: tuple[str, ...],
) -> None:
    result = _preview(build_expanded_multi_member_tee_payload(active_slots=active_slots))
    assert result.assembly_status is MultiMemberTeeAssemblyStatus.NOT_EVALUATED
    assert tuple(item.value for item in result.active_slot_ids) == active_slots
    assert tuple(item.slot_id.value for item in result.slots) == active_slots
    assert len(result.support_wrench.contributions) == len(active_slots)


def test_profile_and_support_changes_leave_unaffected_slots_actions_and_wrench_exact() -> None:
    baseline = _preview(build_expanded_multi_member_tee_payload())
    profile_changed = _preview(
        build_expanded_multi_member_tee_payload(
            profile_families=("CHANNEL", "WIDE_FLANGE_I", "ANGLE")
        )
    )
    support_changed = _preview(
        build_expanded_multi_member_tee_payload(support_target="CHANNEL_COLUMN_WEB")
    )
    assert profile_changed.support_wrench == baseline.support_wrench
    assert support_changed.support_wrench == baseline.support_wrench
    assert profile_changed.slots[1:] == baseline.slots[1:]
    assert [item.action for item in support_changed.slots] == [
        item.action for item in baseline.slots
    ]
    assert [item.geometry_fingerprint for item in support_changed.slots] == [
        item.geometry_fingerprint for item in baseline.slots
    ]


def test_rectangular_physical_hardware_is_unique_per_axis_and_uses_external_endpoints() -> None:
    result = _preview(
        build_expanded_multi_member_tee_payload(
            active_slots=("UPPER_BRACE",),
            profile_families=("RECTANGULAR_HOLLOW_SECTION", "WIDE_FLANGE_I", "ANGLE"),
            support_target="RECTANGULAR_HOLLOW_COLUMN_WALL",
        )
    )
    assert result.visualization is not None
    paths = result.visualization.slots[0].visualization.rectangular_full_through_paths
    assert len(paths) == 8
    identities = tuple((item.path.segments[0].identity, item.path.bolt_id) for item in paths)
    assert len(identities) == len(set(identities))
    assert all(item.geometry_valid for item in paths)
    assert all(item.hardware.internal_hardware_count == 0 for item in paths)
    assert all(item.hardware.shank_length > Decimal(0) for item in paths)


def test_rectangular_limitations_do_not_promote_valid_geometry_to_invalid() -> None:
    result = _preview(
        build_expanded_multi_member_tee_payload(
            active_slots=("MIDDLE_BEAM",),
            profile_families=("ANGLE", "RECTANGULAR_HOLLOW_SECTION", "ANGLE"),
            support_target="SOLID_RECTANGULAR_COLUMN_FACE",
        )
    )
    assert result.assembly_status is MultiMemberTeeAssemblyStatus.NOT_EVALUATED
    assert result.design_check_ready
    assert set(result.required_limitations) == {
        "TEE_CONNECTOR_BODY_RESISTANCE",
        "MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY",
        "RHS_LOCAL_WALL_RESPONSE",
        "RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT",
        "SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY",
    }


def test_strict_contracts_reject_stale_unknown_and_semantically_invalid_fields() -> None:
    cases: list[dict[str, object]] = []
    flat = build_expanded_multi_member_tee_payload(active_slots=("MIDDLE_BEAM",))
    middle = flat["middle_beam"]
    assert isinstance(middle, dict)
    profile = middle["profile"]
    assert isinstance(profile, dict)
    profile["profile_family"] = "FLAT_PLATE"
    profile["dimensions"] = {
        "width": {"value": "6", "unit": "in"},
        "thickness": {"value": "0.5", "unit": "in"},
        "member_length": {"value": "12", "unit": "in"},
        "web_thickness": {"value": "0.5", "unit": "in"},
    }
    profile["selected_profile_surface"] = "FACE_POS"
    cases.append(flat)
    nonzero = build_expanded_multi_member_tee_payload(active_slots=("MIDDLE_BEAM",))
    assert isinstance(nonzero["middle_beam"], dict)
    nonzero["middle_beam"]["inclination_degrees"] = "1"
    cases.append(nonzero)
    future = build_expanded_multi_member_tee_payload(active_slots=("UPPER_BRACE",))
    future["orchestration_contract_version"] = "3.4C-RC1"
    cases.append(future)
    for payload in cases:
        with pytest.raises(ValidationError):
            MultiMemberTeeRequestDTO.model_validate(payload)


def test_expanded_slot_domains_roll_and_contract_shapes_fail_closed() -> None:
    cases: list[dict[str, object]] = []
    upper = build_expanded_multi_member_tee_payload(active_slots=("UPPER_BRACE",))
    assert isinstance(upper["upper_brace"], dict)
    upper["upper_brace"]["inclination_degrees"] = "-1"
    cases.append(upper)
    lower = build_expanded_multi_member_tee_payload(active_slots=("LOWER_BRACE",))
    assert isinstance(lower["lower_brace"], dict)
    lower["lower_brace"]["inclination_degrees"] = "1"
    cases.append(lower)
    roll = build_expanded_multi_member_tee_payload(active_slots=("UPPER_BRACE",))
    assert isinstance(roll["upper_brace"], dict)
    roll["upper_brace"]["profile_roll_degrees"] = "90"
    cases.append(roll)
    expanded_with_legacy = build_expanded_multi_member_tee_payload(active_slots=("UPPER_BRACE",))
    expanded_with_legacy["support_dimensions"] = build_multi_member_tee_payload()[
        "support_dimensions"
    ]
    cases.append(expanded_with_legacy)
    expanded_missing_support = build_expanded_multi_member_tee_payload(
        active_slots=("UPPER_BRACE",)
    )
    expanded_missing_support.pop("support_target_id")
    cases.append(expanded_missing_support)
    mismatched_slot = build_expanded_multi_member_tee_payload(active_slots=("UPPER_BRACE",))
    mismatched_slot["middle_beam"] = mismatched_slot.pop("upper_brace")
    cases.append(mismatched_slot)
    legacy_missing_support = build_multi_member_tee_payload(active_slots=("UPPER_BRACE",))
    legacy_missing_support.pop("support_dimensions")
    cases.append(legacy_missing_support)
    legacy_with_expanded = build_multi_member_tee_payload(active_slots=("UPPER_BRACE",))
    source = build_expanded_multi_member_tee_payload(active_slots=("UPPER_BRACE",))
    legacy_with_expanded["support_target_id"] = source["support_target_id"]
    legacy_with_expanded["support_profile"] = source["support_profile"]
    cases.append(legacy_with_expanded)
    legacy_expanded_slot = build_expanded_multi_member_tee_payload(active_slots=("UPPER_BRACE",))
    legacy_expanded_slot["orchestration_contract_version"] = "3.4A-RC1"
    legacy_expanded_slot["support_dimensions"] = build_multi_member_tee_payload()[
        "support_dimensions"
    ]
    legacy_expanded_slot.pop("support_target_id")
    legacy_expanded_slot.pop("support_profile")
    cases.append(legacy_expanded_slot)
    for payload in cases:
        with pytest.raises(ValidationError):
            MultiMemberTeeRequestDTO.model_validate(payload)


def test_mapping_defensive_guards_reject_bypassed_transport_invariants() -> None:
    legacy = MultiMemberTeeRequestDTO.model_validate(build_multi_member_tee_payload())
    expanded = MultiMemberTeeRequestDTO.model_validate(build_expanded_multi_member_tee_payload())
    missing_legacy = legacy.model_copy(update={"support_dimensions": None})
    with pytest.raises(ValueError, match="support_dimensions"):
        mapping_module._support_profile(missing_legacy, missing_legacy.source_length_unit)
    with pytest.raises(ValueError, match="support_dimensions"):
        map_multi_member_tee_request(missing_legacy)
    with pytest.raises(ValueError, match="support_profile"):
        map_multi_member_tee_request(expanded.model_copy(update={"support_profile": None}))


def test_historical_3_4a_default_contract_and_fingerprints_remain_exact() -> None:
    result = _preview(build_multi_member_tee_payload())
    assert result.orchestration_contract_version == "3.4A-RC1"
    assert result.engineering_fingerprint == (
        "2594c3e28cd47fac2b5235710733ab0bd94d0c61bb82bb174e21b9979c252717"
    )
    assert result.support_wrench.wrench_fingerprint == (
        "1a045a3fdd132d18249c2cc27a9208ffad18a7dd6e857cf85215aaf5090a2e34"
    )


def test_expanded_preview_and_design_routes_keep_preview_resistance_free() -> None:
    payload = build_expanded_multi_member_tee_payload(active_slots=("MIDDLE_BEAM",))
    preview = _post("/api/v1/calculations/multi-member-tee/preview", payload)
    design = _post("/api/v1/calculations/multi-member-tee/design-check", payload)
    assert preview.status_code == 200
    assert preview.json()["orchestration_contract_version"] == "3.4B-RC1"
    assert preview.json()["resistance_evaluated"] is False
    assert design.status_code == 200
    assert design.json()["orchestration_contract_version"] == "3.4B-RC1"


def test_representative_mixed_profile_rhs_support_is_us_si_equivalent() -> None:
    values = []
    for system in ("US_CUSTOMARY", "SI"):
        result = _preview(
            build_expanded_multi_member_tee_payload(
                unit_system=system,
                profile_families=(
                    "RECTANGULAR_HOLLOW_SECTION",
                    "FLAT_PLATE",
                    "SOLID_RECTANGULAR_SECTION",
                ),
                support_target="RECTANGULAR_HOLLOW_COLUMN_WALL",
            )
        )
        values.append(
            (
                result.assembly_status,
                result.engineering_fingerprint,
                result.support_wrench.wrench_fingerprint,
            )
        )
    assert values[0] == values[1]
