"""Controlled Stage 3.4A Multi-Member Tee node behavior and golden regressions."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import httpx
import pytest

import frp_master_connection.api.multi_member_tee_mapping as mapping_module
import frp_master_connection.application.multi_member_tee_orchestration as node_module
from frp_master_connection.api.app import create_app
from frp_master_connection.api.multi_member_tee_mapping import (
    map_multi_member_tee_request,
    serialize_multi_member_tee_design,
    serialize_multi_member_tee_preview,
)
from frp_master_connection.api.multi_member_tee_schemas import MultiMemberTeeRequestDTO
from frp_master_connection.api.schemas import QuantityDTO
from frp_master_connection.application.calculation_orchestration import (
    SingleBoltOrchestrationRequest,
)
from frp_master_connection.application.connection_preview import (
    preview_single_bolt_connection,
)
from frp_master_connection.application.multi_member_tee_orchestration import (
    MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY,
    TEE_CONNECTOR_BODY_RESISTANCE,
    MultiMemberTeeAssemblyStatus,
    MultiMemberTeeOrchestrationRequest,
    MultiMemberTeeSlotAction,
    MultiMemberTeeSlotRequest,
    NodeVectorInput,
    assemble_support_wrench,
    design_check_multi_member_tee,
    preview_multi_member_tee,
)
from frp_master_connection.application.tee_orchestration import (
    TeeConnectorOrchestrationRequest,
    resolve_tee_connector_request,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.domain import (
    EngineeringUnitSystem,
    MemberProfile,
    MemberProfileFamily,
    TeeBoltLayout,
    TeeConnectorDimensions,
)
from frp_master_connection.domain.multi_member_tee import (
    MultiMemberTeeConnectedRole,
    MultiMemberTeeSlot,
    MultiMemberTeeSlotId,
    MultiMemberTeeSlotSet,
)
from tests.multi_member_tee_fixtures import build_multi_member_tee_payload


def _request(
    unit_system: str = "US_CUSTOMARY",
    active_slots: tuple[str, ...] = ("UPPER_BRACE", "MIDDLE_BEAM", "LOWER_BRACE"),
) -> MultiMemberTeeOrchestrationRequest:
    dto = MultiMemberTeeRequestDTO.model_validate(
        build_multi_member_tee_payload(unit_system=unit_system, active_slots=active_slots)
    )
    return map_multi_member_tee_request(dto)


def _post(path: str, payload: dict[str, object]) -> httpx.Response:
    async def send() -> httpx.Response:
        application = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://testserver"
        ) as client:
            return await client.post(path, json=payload)

    return asyncio.run(send())


def _per_bolt_magnitude(result: node_module.MultiMemberTeeSlotResult) -> Decimal:
    assert result.preview is not None
    demand = result.preview.automatic_demand_result
    assert demand is not None
    return demand.scenarios[0].per_bolt[0].total_force_magnitude.to(Unit.KIP).magnitude


def test_controlled_golden_is_complete_and_production_does_not_read_it() -> None:
    path = (
        Path(__file__).parents[1]
        / "golden"
        / ("stage_3_4a_multi_member_tee_node_golden_benchmarks_rc1.json")
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    assert [item["id"] for item in value["benchmarks"]] == [
        f"G{index}_{suffix}"
        for index, suffix in enumerate(
            (
                "UPPER_ONLY_CONCENTRIC",
                "MIDDLE_ONLY_INDEPENDENT_COUNTS",
                "LOWER_ONLY_CONCENTRIC",
                "DEFAULT_ALL_THREE_WRENCH_ASSEMBLY",
                "ZERO_NET_FORCE_NONZERO_COUPLE",
                "DISABLED_SLOT_IS_ABSENT",
                "SLOT_ORDER_AND_DOMAIN_VALIDATION",
                "GROUP_INDEPENDENCE",
                "CROSS_GROUP_HOLE_OVERLAP",
                "CONNECTED_MEMBER_INTERFERENCE",
                "SLOT_INCLINATION_RULES",
                "SAME_SUPPORT_WRENCH_DIFFERENT_DECOMPOSITION",
                "UNSUPPORTED_NORMAL_ACTION",
                "MEMBER_END_MOMENTS_RETAINED",
                "US_SI_EQUIVALENCE",
                "MATERIAL_AXES_COVERAGE",
                "PREVIEW_ZERO_RESISTANCE",
                "REQUIRED_LIMITATIONS",
                "SUPPORTED_FAILURE_PRECEDENCE",
                "FROZEN_FAMILY_REGRESSION",
            ),
            start=1,
        )
    ]
    production = Path(__file__).parents[2] / "src" / "frp_master_connection"
    assert all(
        "stage_3_4a_multi_member_tee_node_golden" not in item.read_text(encoding="utf-8")
        for item in production.rglob("*.py")
    )


@pytest.mark.parametrize(
    ("active", "expected"),
    [
        (("UPPER_BRACE",), (MultiMemberTeeSlotId.UPPER_BRACE,)),
        (("MIDDLE_BEAM",), (MultiMemberTeeSlotId.MIDDLE_BEAM,)),
        (("LOWER_BRACE",), (MultiMemberTeeSlotId.LOWER_BRACE,)),
        (
            ("UPPER_BRACE", "LOWER_BRACE"),
            (MultiMemberTeeSlotId.UPPER_BRACE, MultiMemberTeeSlotId.LOWER_BRACE),
        ),
        (("UPPER_BRACE", "MIDDLE_BEAM", "LOWER_BRACE"), tuple(MultiMemberTeeSlotId)),
    ],
)
def test_one_two_three_slot_activation_and_absence(
    active: tuple[str, ...], expected: tuple[MultiMemberTeeSlotId, ...]
) -> None:
    result = preview_multi_member_tee(_request(active_slots=active))
    assert result.assembly_status is MultiMemberTeeAssemblyStatus.NOT_EVALUATED
    assert result.active_slot_ids == expected
    assert tuple(item.slot_id for item in result.slots) == expected
    assert result.visualization is not None
    assert tuple(item.slot_id for item in result.visualization.slots) == expected
    assert len(result.support_wrench.contributions) == len(active)


def test_default_g4_wrench_per_bolt_limitations_and_material_coverage() -> None:
    result = preview_multi_member_tee(_request())
    assert result.support_wrench.force.to(Unit.KIP) == (
        Decimal("12.9282032302755088"),
        Decimal(0),
        Decimal(0),
    )
    assert result.support_wrench.moment.to(Unit.KIP_IN) == (Decimal(0), Decimal(0), Decimal(0))
    assert [
        item.shifted_moment.n.to(Unit.KIP_IN).magnitude
        for item in result.support_wrench.contributions
    ] == [Decimal("-28.6410161513775440"), Decimal(0), Decimal("28.6410161513775440")]
    magnitudes = [_per_bolt_magnitude(item) for item in result.slots]
    assert magnitudes[0] == pytest.approx(Decimal(1), abs=Decimal("1e-15"))
    assert magnitudes[1] == Decimal("1.5")
    assert magnitudes[2] == pytest.approx(Decimal(1), abs=Decimal("1e-15"))
    assert result.required_limitations == (
        TEE_CONNECTOR_BODY_RESISTANCE,
        MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY,
    )
    assert not result.ordinary_pass_allowed
    assert not result.resistance_evaluated
    assert result.design_check_ready
    assert result.visualization is not None
    axes = tuple(
        axis
        for item in result.visualization.slots
        for axis in (
            *item.visualization.base_connection.material_directions,
            *item.visualization.interface_b_connection.material_directions,
        )
    )
    assert {axis.component_id for axis in axes} >= {"tee-brace", "tee-connector", "tee-support"}


def test_g1_g2_g3_independent_group_counts_and_demands() -> None:
    cases = (
        (("UPPER_BRACE",), "upper", 4, Decimal(1)),
        (("MIDDLE_BEAM",), "middle", 2, Decimal(3)),
        (("LOWER_BRACE",), "lower", 4, Decimal(1)),
    )
    for active, _label, count, expected in cases:
        payload = build_multi_member_tee_payload(active_slots=active)
        key = {
            "UPPER_BRACE": "upper_brace",
            "MIDDLE_BEAM": "middle_beam",
            "LOWER_BRACE": "lower_brace",
        }[active[0]]
        slot = cast(dict[str, object], payload[key])
        group = cast(dict[str, object], slot["bolt_group"])
        if active == ("MIDDLE_BEAM",):
            group = dict(group)
            slot["bolt_group"] = group
            group["bolts_per_row"] = 1
        result = preview_multi_member_tee(
            map_multi_member_tee_request(MultiMemberTeeRequestDTO.model_validate(payload))
        )
        demand = result.slots[0].preview
        assert demand is not None
        assert demand.automatic_demand_result is not None
        assert len(demand.automatic_demand_result.scenarios[0].per_bolt) == count
        assert _per_bolt_magnitude(result.slots[0]) == pytest.approx(expected, abs=Decimal("1e-15"))


def test_exact_wrench_retains_couple_free_moments_and_provenance() -> None:
    request = _request(active_slots=("UPPER_BRACE", "LOWER_BRACE"))
    force_unit = Unit.KIP
    moment_unit = Unit.KIP_IN
    length_unit = Unit.IN

    def vector(values: tuple[str, str, str], unit: Unit) -> NodeVectorInput:
        return NodeVectorInput(*(PhysicalQuantity.of(value, unit) for value in values))

    upper = replace(
        request.slots[0],
        action=replace(
            request.slots[0].action,
            force=vector(("2", "0", "0"), force_unit),
            moment=vector(("0", "0", "1"), moment_unit),
            reference_point=vector(("0", "3", "0"), length_unit),
        ),
    )
    lower = replace(
        request.slots[1],
        action=replace(
            request.slots[1].action,
            force=vector(("-2", "0", "0"), force_unit),
            moment=vector(("0", "0", "-1"), moment_unit),
            reference_point=vector(("0", "-3", "0"), length_unit),
        ),
    )
    wrench = assemble_support_wrench(
        (upper, lower), request.support_reference_point, EngineeringUnitSystem.US_CUSTOMARY
    )
    assert wrench.force.to(Unit.KIP) == (Decimal(0), Decimal(0), Decimal(0))
    assert wrench.moment.to(Unit.KIP_IN) == (Decimal(0), Decimal(0), Decimal("-12"))
    same = replace(
        middle := _request(active_slots=("MIDDLE_BEAM",)),
        slots=(
            replace(
                middle.slots[0],
                action=replace(
                    middle.slots[0].action,
                    force=vector(("4", "0", "0"), force_unit),
                    reference_point=vector(("0", "0", "0"), length_unit),
                ),
            ),
        ),
    )
    split = replace(
        request,
        slots=(
            replace(
                upper,
                action=replace(
                    upper.action,
                    moment=vector(("0", "0", "0"), moment_unit),
                    force=vector(("2", "0", "0"), force_unit),
                    reference_point=vector(("0", "2", "0"), length_unit),
                ),
            ),
            replace(
                lower,
                action=replace(
                    lower.action,
                    moment=vector(("0", "0", "0"), moment_unit),
                    force=vector(("2", "0", "0"), force_unit),
                    reference_point=vector(("0", "-2", "0"), length_unit),
                ),
            ),
        ),
    )
    first = assemble_support_wrench(same.slots, same.support_reference_point, same.unit_system)
    second = assemble_support_wrench(split.slots, split.support_reference_point, split.unit_system)
    assert first.wrench_fingerprint == second.wrench_fingerprint
    assert first.application_provenance_fingerprint != second.application_provenance_fingerprint


def test_us_si_equivalence_and_serialization() -> None:
    us = preview_multi_member_tee(_request("US_CUSTOMARY"))
    si = preview_multi_member_tee(_request("SI"))
    assert us.input_fingerprint == si.input_fingerprint
    assert us.engineering_fingerprint == si.engineering_fingerprint
    assert us.support_wrench.wrench_fingerprint == si.support_wrench.wrench_fingerprint
    dto = serialize_multi_member_tee_preview(us)
    assert dto.engineering_fingerprint == us.engineering_fingerprint
    design = design_check_multi_member_tee(_request())
    assert serialize_multi_member_tee_design(design).result_fingerprint == design.result_fingerprint


def test_preview_never_calls_resistance_and_design_preserves_fail_precedence() -> None:
    with patch.object(
        node_module, "evaluate_tee_interface", side_effect=AssertionError("resistance")
    ):
        assert preview_multi_member_tee(_request()).resistance_evaluated is False
    with patch.object(node_module, "tee_interface_failed", return_value=True):
        result = design_check_multi_member_tee(_request(active_slots=("MIDDLE_BEAM",)))
    assert result.assembly_status is MultiMemberTeeAssemblyStatus.FAIL
    assert result.supported_failure_present
    assert result.required_limitations == (
        TEE_CONNECTOR_BODY_RESISTANCE,
        MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY,
    )
    assert not result.ordinary_pass_allowed


def test_invalid_overlap_interference_and_visualization_fail_closed() -> None:
    request = _request(active_slots=("UPPER_BRACE", "LOWER_BRACE"))
    overlapping = replace(
        request,
        slots=(
            replace(request.slots[0], slot=replace(request.slots[0].slot, anchor_v=Decimal("0.1"))),
            replace(request.slots[1], slot=replace(request.slots[1].slot, anchor_v=Decimal(0))),
        ),
    )
    result = preview_multi_member_tee(overlapping)
    assert result.assembly_status is MultiMemberTeeAssemblyStatus.INVALID_GEOMETRY
    assert result.warnings == ("CROSS_GROUP_COMPLETE_HOLE_OVERLAP",)
    assert not result.design_check_ready
    assert result.visualization is None
    assert (
        design_check_multi_member_tee(overlapping).assembly_status
        is MultiMemberTeeAssemblyStatus.INVALID_GEOMETRY
    )
    separated_holes = replace(
        request,
        slots=tuple(
            replace(
                item,
                slot=replace(
                    item.slot,
                    bolt_layout=replace(item.slot.bolt_layout, row_count=1, bolts_per_row=1),
                    anchor_v=value,
                ),
            )
            for item, value in zip(request.slots, (Decimal(2), Decimal(0)), strict=True)
        ),
    )
    interference = preview_multi_member_tee(separated_holes)
    assert interference.assembly_status is MultiMemberTeeAssemblyStatus.INVALID_GEOMETRY
    assert interference.warnings == ("CONNECTED_MEMBER_POSITIVE_VOLUME_INTERFERENCE",)
    assert (
        design_check_multi_member_tee(separated_holes).assembly_status
        is MultiMemberTeeAssemblyStatus.INVALID_GEOMETRY
    )
    with patch.object(node_module, "_visualization", return_value=None):
        absent = preview_multi_member_tee(_request(active_slots=("UPPER_BRACE",)))
        blocked = design_check_multi_member_tee(_request(active_slots=("UPPER_BRACE",)))
    assert absent.warnings == ("VISUALIZATION_GEOMETRY_UNAVAILABLE",)
    assert blocked.assembly_status is MultiMemberTeeAssemblyStatus.INVALID_GEOMETRY
    with patch.object(node_module, "_invalid_trim", return_value=True):
        trimmed = preview_multi_member_tee(_request(active_slots=("UPPER_BRACE",)))
    assert trimmed.warnings == ("CONNECTED_MEMBER_TRIM_INVALID_GEOMETRY",)


def test_visualization_fails_closed_for_missing_support_or_slot_snapshot() -> None:
    request = _request(active_slots=("UPPER_BRACE",))
    resolved_slots, resolved_support, _wrench = node_module._resolve_node(request)
    with patch.object(
        node_module,
        "preview_single_bolt_connection",
        return_value=SimpleNamespace(visualization=None),
    ):
        assert node_module._visualization(resolved_slots, resolved_support) is None
    support_physical = cast(
        SingleBoltOrchestrationRequest,
        resolved_support.interface_b_request.physical_connection_request,
    )
    support = preview_single_bolt_connection(support_physical)
    with patch.object(
        node_module,
        "preview_single_bolt_connection",
        side_effect=(support, SimpleNamespace(visualization=None)),
    ):
        assert node_module._visualization(resolved_slots, resolved_support) is None


def test_normal_action_retained_without_generated_axis_tension() -> None:
    request = _request(active_slots=("UPPER_BRACE",))
    normal = NodeVectorInput(
        request.slots[0].action.force.h,
        request.slots[0].action.force.v,
        PhysicalQuantity.of(Decimal(1), Unit.KIP),
    )
    request = replace(
        request,
        slots=(replace(request.slots[0], action=replace(request.slots[0].action, force=normal)),),
    )
    result = preview_multi_member_tee(request)
    assert result.slots[0].normal_action_retained
    assert not result.slots[0].automatic_axis_tension_generated
    assert "INTERFACE_NORMAL_ACTION_RETAINED_WITHOUT_AXIS_TENSION_GENERATION" in result.warnings


def test_domain_immutability_roles_and_fail_closed_validation() -> None:
    request = _request()
    upper, middle, lower = (item.slot for item in request.slots)
    assert upper.connected_role is MultiMemberTeeConnectedRole.BRACE
    assert middle.connected_role is MultiMemberTeeConnectedRole.BEAM
    with pytest.raises(FrozenInstanceError):
        upper.anchor_v = Decimal(1)  # type: ignore[misc]
    invalids = (
        lambda: MultiMemberTeeSlotSet(()),
        lambda: MultiMemberTeeSlotSet((upper, upper)),
        lambda: MultiMemberTeeSlotSet((middle, upper)),
        lambda: MultiMemberTeeSlotSet((replace(upper, anchor_v=Decimal(0)), middle, lower)),
        lambda: MultiMemberTeeSlotSet((upper, replace(middle, anchor_v=Decimal(-20)), lower)),
        lambda: MultiMemberTeeSlotSet((replace(upper, anchor_v=Decimal(-20)), lower)),
        lambda: replace(upper, inclination_degrees=Decimal(-1)),
        lambda: replace(lower, inclination_degrees=Decimal(1)),
        lambda: replace(middle, inclination_degrees=Decimal(1)),
        lambda: replace(middle, profile=upper.profile),
        lambda: replace(upper, profile=middle.profile),
        lambda: replace(upper, profile_roll_degrees=Decimal(1)),
        lambda: replace(upper, trim_enabled=True, trim_clearance=None),
        lambda: replace(upper, trim_enabled=True, trim_clearance=Decimal(-1)),
        lambda: replace(upper, trim_clearance=Decimal(0)),
        lambda: replace(upper, slot_id=cast(MultiMemberTeeSlotId, "bad")),
        lambda: replace(upper, profile=cast(MemberProfile, "bad")),
        lambda: replace(upper, anchor_h=Decimal("NaN")),
        lambda: replace(upper, bolt_layout=cast(TeeBoltLayout, "bad")),
        lambda: replace(upper, trim_enabled=cast(bool, 1)),
        lambda: replace(upper, expanded_profile_allowed=cast(bool, 1)),
        lambda: MultiMemberTeeSlotSet(
            cast(tuple[MultiMemberTeeSlot, ...], (upper, middle, lower, lower))
        ),
    )
    for invalid in invalids:
        with pytest.raises((TypeError, ValueError)):
            invalid()
    assert replace(upper, trim_enabled=True, trim_clearance=Decimal(0)).trim_enabled is True
    assert upper.profile.family is MemberProfileFamily.ANGLE


def test_application_contract_defensive_boundaries() -> None:
    request = _request(active_slots=("UPPER_BRACE",))
    slot_request = request.slots[0]
    force = slot_request.action.force
    moment = slot_request.action.moment
    reference = slot_request.action.reference_point
    with pytest.raises(TypeError, match="PhysicalQuantity"):
        NodeVectorInput(cast(PhysicalQuantity, "bad"), force.v, force.n)
    actions: tuple[Callable[[], object], ...] = (
        lambda: MultiMemberTeeSlotAction(reference, moment, reference),
        lambda: MultiMemberTeeSlotAction(force, force, reference),
        lambda: MultiMemberTeeSlotAction(force, moment, force),
    )
    for action in actions:
        with pytest.raises(ValueError, match="must contain"):
            action()
    mismatched_profile = _request(active_slots=("MIDDLE_BEAM",)).slots[0].slot.profile
    invalid_slots: tuple[Callable[[], object], ...] = (
        lambda: MultiMemberTeeSlotRequest(
            cast(MultiMemberTeeSlot, "bad"),
            slot_request.action,
            slot_request.tee_request,
        ),
        lambda: MultiMemberTeeSlotRequest(
            slot_request.slot,
            cast(MultiMemberTeeSlotAction, "bad"),
            slot_request.tee_request,
        ),
        lambda: MultiMemberTeeSlotRequest(
            slot_request.slot,
            slot_request.action,
            cast(TeeConnectorOrchestrationRequest, "bad"),
        ),
        lambda: replace(
            slot_request,
            tee_request=replace(
                slot_request.tee_request,
                connected_member_profile=mismatched_profile,
            ),
        ),
        lambda: replace(
            slot_request,
            tee_request=replace(slot_request.tee_request, brace_inclination_degrees=Decimal(31)),
        ),
    )
    for invalid in invalid_slots:
        with pytest.raises((TypeError, ValueError)):
            invalid()
    with pytest.raises(ValueError, match="vertical_offset"):
        resolve_tee_connector_request(
            slot_request.tee_request,
            connected_member_vertical_offset=Decimal("NaN"),
        )
    with pytest.raises(ValueError, match="group_anchor_h"):
        resolve_tee_connector_request(
            slot_request.tee_request,
            connected_member_group_anchor_h=Decimal("NaN"),
        )
    with pytest.raises(TypeError, match="roundoff_tolerance"):
        resolve_tee_connector_request(
            slot_request.tee_request,
            connected_member_node_roundoff_tolerance=cast(bool, 1),
        )
    invalid_requests: tuple[Callable[[], object], ...] = (
        lambda: replace(request, request_id=" "),
        lambda: replace(request, orchestration_contract_version="bad"),
        lambda: replace(request, unit_system=cast(EngineeringUnitSystem, "bad")),
        lambda: replace(request, source_length_unit=Unit.MM),
        lambda: replace(request, connector_dimensions=cast(TeeConnectorDimensions, "bad")),
        lambda: replace(request, slots=cast(tuple[MultiMemberTeeSlotRequest, ...], ("bad",))),
        lambda: replace(request, support_reference_point=force),
        lambda: replace(
            request,
            slots=(
                replace(
                    slot_request,
                    tee_request=replace(
                        slot_request.tee_request,
                        connector_dimensions=replace(
                            slot_request.tee_request.connector_dimensions, stem_depth=Decimal(7)
                        ),
                    ),
                ),
            ),
        ),
    )
    for invalid_request in invalid_requests:
        with pytest.raises((TypeError, ValueError)):
            invalid_request()
    assert node_module._canonical(1.25) == "1.25"
    assert node_module._canonical([Decimal(1)]) == ["1"]
    assert node_module._canonical({"value": Decimal(2)}) == {"value": "2"}
    assert node_module._canonical_lengths((Decimal(1),), Unit.IN) == (
        PhysicalQuantity.of(Decimal(1), Unit.IN),
    )


def test_mapping_and_schema_defensive_boundaries() -> None:
    with pytest.raises(ValueError, match="must be lengths"):
        mapping_module._length(QuantityDTO(value="1", unit=Unit.KIP), Unit.IN)
    with pytest.raises(ValueError, match="must be positive"):
        mapping_module._length(QuantityDTO(value="0", unit=Unit.IN), Unit.IN)
    assert mapping_module._serialize([Decimal(1)]) == ["1"]
    assert mapping_module._serialize({"value": Decimal(2)}) == {"value": "2"}
    valid_trim = build_multi_member_tee_payload()
    cast(dict[str, object], valid_trim["upper_brace"]).update(
        trim_enabled=True,
        trim_clearance={"value": "0", "unit": "in"},
    )
    assert MultiMemberTeeRequestDTO.model_validate(valid_trim).upper_brace is not None
    invalids: list[dict[str, object]] = []
    mutations: tuple[Callable[[dict[str, object]], object], ...] = (
        lambda p: cast(dict[str, object], p["support_group"]).__setitem__("row_count", 0),
        lambda p: cast(dict[str, object], p["upper_brace"]).__setitem__(
            "profile_roll_degrees", "1"
        ),
        lambda p: cast(dict[str, object], p["upper_brace"]).__setitem__(
            "profile_roll_degrees", "NaN"
        ),
        lambda p: cast(dict[str, object], p["upper_brace"]).__setitem__(
            "profile_roll_degrees", "not-a-decimal"
        ),
        lambda p: cast(dict[str, object], p["upper_brace"]).__setitem__("trim_enabled", True),
        lambda p: cast(dict[str, object], p["upper_brace"]).__setitem__(
            "trim_clearance", {"value": "0", "unit": "in"}
        ),
        lambda p: cast(dict[str, object], p["upper_brace"]).update(
            trim_enabled=True,
            trim_clearance={"value": "-1", "unit": "in"},
        ),
        lambda p: cast(dict[str, object], p["lower_brace"]).__setitem__(
            "inclination_degrees", "-91"
        ),
        lambda p: p.__setitem__("request_id", " "),
        lambda p: p.__setitem__("connector_length_anchor_position", {"value": "0", "unit": "mm"}),
    )
    for mutate_payload in mutations:
        payload = build_multi_member_tee_payload()
        mutate_payload(payload)
        invalids.append(payload)
    for payload in invalids:
        with pytest.raises(ValueError, match=r".+"):
            MultiMemberTeeRequestDTO.model_validate(payload)


def test_strict_api_contract_success_and_rejections() -> None:
    payload = build_multi_member_tee_payload()
    preview = _post("/api/v1/calculations/multi-member-tee/preview", payload)
    design = _post("/api/v1/calculations/multi-member-tee/design-check", payload)
    assert preview.status_code == 200
    assert preview.json()["resistance_evaluated"] is False
    assert design.status_code == 200
    assert design.json()["ordinary_pass_allowed"] is False
    invalids: list[dict[str, object]] = []
    zero = build_multi_member_tee_payload(active_slots=())
    invalids.append(zero)
    extra = build_multi_member_tee_payload()
    extra["fingerprint"] = "client"
    invalids.append(extra)
    version = build_multi_member_tee_payload()
    version["orchestration_contract_version"] = "bad"
    invalids.append(version)
    angle = build_multi_member_tee_payload()
    cast(dict[str, object], angle["upper_brace"])["inclination_degrees"] = "91"
    invalids.append(angle)
    middle = build_multi_member_tee_payload()
    cast(dict[str, object], middle["middle_beam"])["inclination_degrees"] = "1"
    invalids.append(middle)
    unit = build_multi_member_tee_payload()
    unit["source_length_unit"] = "mm"
    invalids.append(unit)
    for invalid in invalids:
        response = _post("/api/v1/calculations/multi-member-tee/preview", invalid)
        assert response.status_code == 422
        assert "Traceback" not in response.text


def test_routes_fail_closed_when_canonical_mapping_rejects_a_valid_dto() -> None:
    payload = build_multi_member_tee_payload()
    with patch(
        "frp_master_connection.api.routes.map_multi_member_tee_request",
        side_effect=ValueError("canonical node rejected"),
    ):
        for path in (
            "/api/v1/calculations/multi-member-tee/preview",
            "/api/v1/calculations/multi-member-tee/design-check",
        ):
            response = _post(path, payload)
            assert response.status_code == 422
            assert response.json()["detail"] == {
                "code": "CANONICAL_MULTI_MEMBER_TEE_MAPPING_INVALID",
                "message": "canonical node rejected",
            }


def test_public_entry_points_reject_wrong_runtime_types() -> None:
    with pytest.raises(TypeError, match="MultiMemberTeeOrchestrationRequest"):
        preview_multi_member_tee(cast(object, "bad"))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="MultiMemberTeeOrchestrationRequest"):
        design_check_multi_member_tee(cast(object, "bad"))  # type: ignore[arg-type]
    force = PhysicalQuantity.of(Decimal(1), Unit.KIP)
    with pytest.raises(ValueError, match="share one dimension"):
        NodeVectorInput(force, PhysicalQuantity.of(Decimal(1), Unit.IN), force)
