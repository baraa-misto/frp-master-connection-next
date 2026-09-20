"""Controlled Stage 3.5C-R2 signed compression/uplift verification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

import frp_master_connection.application.column_base_web_angle_orchestration as orchestration
from frp_master_connection.api.column_base_web_angle_mapping import (
    map_column_base_web_angle_request,
    serialize_column_base_web_angle_design,
    serialize_column_base_web_angle_preview,
)
from frp_master_connection.api.column_base_web_angle_schemas import (
    ColumnBaseWebAngleRequestDTO,
    ColumnBaseWebAngleSignedRequestDTO,
)
from frp_master_connection.application.column_base_web_angle_orchestration import (
    ColumnBaseSignedComponentTransferTrace,
    design_check_column_base_web_angles,
    preview_column_base_web_angles,
)
from frp_master_connection.application.multirow_orchestration import (
    evaluate_multirow_connection_with_resolved_demand,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.domain import (
    ColumnBaseSignedRequest,
    ColumnBaseStatus,
    ColumnBaseVector,
)
from tests.column_base_web_angle_fixtures import (
    build_column_base_signed_payload,
    build_column_base_signed_request,
    build_column_base_web_angle_request,
)

_ROOT = Path(__file__).resolve().parents[3]
_CONTROLLED_HASHES = {
    _ROOT / "docs/governance/STAGE_3_5C_R2_SIGNED_AXIAL_UPLIFT_EXPANSION_DECISION.md": (
        "8143bbc59a5ee9d38918b0280ca4d09a762b9f2dc92b5660f10951107fd24689"
    ),
    _ROOT / "docs/engineering/STAGE_3_5C_R2_SIGNED_AXIAL_UPLIFT_EXPANSION_ENGINEERING_"
    "SPECIFICATION_RC1.md": "2a60047012f52ff5aa2c09b28bd56816cda4588f2ffa6107b29fbe6b36e3f23f",
    _ROOT / "backend/tests/golden/stage_3_5c_r2_signed_axial_uplift_expansion_golden_"
    "benchmarks_rc1.json": "91f88c06554f5006e69c2aa56fe396818583b2de6af227f83e7cd80db382cd29",
    _ROOT / "docs/qa/STAGE_3_5C_R2_SIGNED_AXIAL_UPLIFT_EXPANSION_AUTHORITY_LEDGER_RC1.md": (
        "ed155c1c0082a300f44ec190e6b8eb38511a1e3b66bc29bd10dfdb396b5fb5eb"
    ),
}
_GOLDEN = next(path for path in _CONTROLLED_HASHES if path.suffix == ".json")


def _request(**kwargs: str) -> ColumnBaseSignedRequest:
    return map_column_base_web_angle_request(
        ColumnBaseWebAngleSignedRequestDTO.model_validate(
            build_column_base_signed_payload(**kwargs)
        )
    )


def _magnitudes(vector: ColumnBaseVector, unit: Unit) -> tuple[Decimal, Decimal, Decimal]:
    return (
        vector.s.to(unit).magnitude,
        vector.t.to(unit).magnitude,
        vector.longitudinal.to(unit).magnitude,
    )


def _transfer(request: ColumnBaseSignedRequest) -> ColumnBaseSignedComponentTransferTrace:
    return cast(
        ColumnBaseSignedComponentTransferTrace,
        preview_column_base_web_angles(request).component_transfer,
    )


def test_r2_artifacts_are_exact_and_g1_through_g48_are_ordered() -> None:
    for path, expected in _CONTROLLED_HASHES.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    golden = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    assert len(golden["benchmarks"]) == 48
    assert [item["id"].split("_", 1)[0] for item in golden["benchmarks"]] == [
        f"G{index}" for index in range(1, 49)
    ]
    assert golden["contracts"] == {
        "historical": "3.5C-RC1",
        "successor": "3.5C-R2-RC1",
    }


def test_historical_contract_and_fingerprints_remain_exact() -> None:
    historical = build_column_base_web_angle_request()
    before = preview_column_base_web_angles(historical)
    # The signed-only field is rejected rather than being reinterpreted historically.
    with pytest.raises(ValidationError):
        ColumnBaseWebAngleRequestDTO.model_validate(
            build_column_base_signed_payload()
            | {"axial_compression": {"value": "20", "unit": "kip"}}
        )
    after = preview_column_base_web_angles(historical)
    assert before.engineering_fingerprint == after.engineering_fingerprint
    assert before.application_fingerprint == after.application_fingerprint
    assert before.external_handoff_json == after.external_handoff_json


@pytest.mark.parametrize("signed", ["-20", "0", "20"])
def test_r2_schema_accepts_finite_signed_axial_values_and_rejects_wrong_fields(
    signed: str,
) -> None:
    dto = ColumnBaseWebAngleSignedRequestDTO.model_validate(
        build_column_base_signed_payload(signed_axial_force=signed)
    )
    assert dto.signed_axial_force.value == signed
    both = build_column_base_signed_payload(signed_axial_force=signed)
    both["axial_compression"] = {"value": "20", "unit": "kip"}
    with pytest.raises(ValidationError, match="Extra inputs"):
        ColumnBaseWebAngleSignedRequestDTO.model_validate(both)
    wrong = build_column_base_signed_payload(signed_axial_force=signed)
    wrong["orchestration_contract_version"] = "3.5C-R3-DRAFT"
    with pytest.raises(ValidationError):
        ColumnBaseWebAngleSignedRequestDTO.model_validate(wrong)


@pytest.mark.parametrize(
    ("signed", "mode", "force", "moment"),
    [
        ("-20", "COMPRESSION", ("4", "0", "-20"), ("0", "16", "0")),
        ("20", "UPLIFT", ("4", "0", "20"), ("0", "16", "0")),
        ("0", "ZERO", ("4", "0", "0"), ("0", "16", "0")),
    ],
)
def test_signed_default_uplift_and_zero_base_wrenches(
    signed: str,
    mode: str,
    force: tuple[str, str, str],
    moment: tuple[str, str, str],
) -> None:
    result = preview_column_base_web_angles(_request(signed_axial_force=signed))
    transfer = cast(ColumnBaseSignedComponentTransferTrace, result.component_transfer)
    assert transfer.axial_mode == mode
    assert _magnitudes(result.combined_foundation_wrench.force_s_t_l, Unit.KIP) == tuple(
        Decimal(value) for value in force
    )
    assert _magnitudes(result.combined_foundation_wrench.moment_s_t_l, Unit.KIP_IN) == tuple(
        Decimal(value) for value in moment
    )
    assert transfer.foundation_signed_axial_action.magnitude == Decimal(signed)
    assert transfer.component_design_demands_summed_for_equilibrium is False


@pytest.mark.parametrize(
    ("signed", "direction", "branch"),
    [("-20", "-", Decimal("-10")), ("20", "+", Decimal("10")), ("0", "", Decimal("0"))],
)
def test_web_angle_system_and_symmetric_branches_retain_signed_actions(
    signed: str, direction: str, branch: Decimal
) -> None:
    transfer = _transfer(_request(signed_axial_force=signed))
    assert transfer.column_web_signed_axial_action.magnitude == Decimal(signed)
    assert transfer.angle_system_signed_axial_action.magnitude == Decimal(signed)
    assert transfer.column_web_design_magnitude.magnitude == abs(Decimal(signed))
    assert transfer.angle_system_design_magnitude.magnitude == abs(Decimal(signed))
    assert transfer.column_web_fraction == transfer.angle_system_fraction == Decimal(1)
    assert transfer.column_web_material_direction == "LW"
    assert transfer.angle_vertical_leg_material_direction == "CW"
    assert transfer.column_web_signed_material_direction == f"{direction}LW"
    assert transfer.angle_vertical_leg_signed_material_direction == f"{direction}CW"
    assert transfer.positive_angle_signed_axial_action is not None
    assert transfer.negative_angle_signed_axial_action is not None
    assert transfer.positive_angle_signed_axial_action.magnitude == branch
    assert transfer.negative_angle_signed_axial_action.magnitude == branch
    assert transfer.branch_fraction == Decimal("0.5")


@pytest.mark.parametrize(
    ("side", "signed", "moment_s", "moment_l"),
    [
        ("+T_C", "-20", "65", "13"),
        ("+T_C", "20", "-65", "13"),
        ("-T_C", "20", "65", "-13"),
    ],
)
def test_single_signed_branch_and_exact_eccentric_wrench(
    side: str, signed: str, moment_s: str, moment_l: str
) -> None:
    result = preview_column_base_web_angles(
        _request(
            assembly="SINGLE_BASE_ANGLE",
            single_side=side,
            signed_axial_force=signed,
        )
    )
    transfer = cast(ColumnBaseSignedComponentTransferTrace, result.component_transfer)
    assert transfer.single_angle_signed_axial_action is not None
    assert transfer.single_angle_signed_axial_action.magnitude == Decimal(signed)
    assert transfer.branch_fraction == Decimal(1)
    wrench = result.anchor_groups[0].branch_wrench
    assert wrench is not None
    assert _magnitudes(wrench.force_s_t_l, Unit.KIP) == (Decimal(4), Decimal(0), Decimal(signed))
    assert _magnitudes(wrench.moment_s_t_l, Unit.KIP_IN) == (
        Decimal(moment_s),
        Decimal(16),
        Decimal(moment_l),
    )


def test_uplift_double_branch_wrenches_and_pure_uplift_moments_cancel() -> None:
    combined = preview_column_base_web_angles(_request(signed_axial_force="20"))
    positive, negative = combined.anchor_groups
    assert positive.branch_wrench is not None
    assert negative.branch_wrench is not None
    assert _magnitudes(positive.branch_wrench.moment_s_t_l, Unit.KIP_IN) == (
        Decimal("-32.5"),
        Decimal(8),
        Decimal("6.5"),
    )
    assert _magnitudes(negative.branch_wrench.moment_s_t_l, Unit.KIP_IN) == (
        Decimal("32.5"),
        Decimal(8),
        Decimal("-6.5"),
    )
    pure = preview_column_base_web_angles(_request(signed_axial_force="20", web_plane_shear="0"))
    assert _magnitudes(pure.anchor_groups[0].branch_wrench.moment_s_t_l, Unit.KIP_IN) == (  # type: ignore[union-attr]
        Decimal("-32.5"),
        Decimal(0),
        Decimal(0),
    )
    assert _magnitudes(pure.anchor_groups[1].branch_wrench.moment_s_t_l, Unit.KIP_IN) == (  # type: ignore[union-attr]
        Decimal("32.5"),
        Decimal(0),
        Decimal(0),
    )
    assert _magnitudes(pure.combined_foundation_wrench.moment_s_t_l, Unit.KIP_IN) == (
        Decimal(0),
        Decimal(0),
        Decimal(0),
    )


def test_signed_layer_vectors_reverse_without_changing_material_axis_classification() -> None:
    compression = preview_column_base_web_angles(
        _request(signed_axial_force="-20", web_plane_shear="0")
    )
    uplift = preview_column_base_web_angles(_request(signed_axial_force="20", web_plane_shear="0"))
    by_compression = {item.layer_id: item for item in compression.layer_directions}
    by_uplift = {item.layer_id: item for item in uplift.layer_directions}
    for layer_id, compressed in by_compression.items():
        lifted = by_uplift[layer_id]
        assert compressed.material_axis == lifted.material_axis
        assert (
            compressed.bearing_direction_classification == lifted.bearing_direction_classification
        )
        assert (
            compressed.force_direction_s_l[1].magnitude == -lifted.force_direction_s_l[1].magnitude
        )
    compression_demands = {
        (item.bolt_id, item.layer_id): item.force_l.magnitude for item in compression.layer_demands
    }
    uplift_demands = {
        (item.bolt_id, item.layer_id): item.force_l.magnitude for item in uplift.layer_demands
    }
    assert compression_demands == {key: -value for key, value in uplift_demands.items()}


def test_uplift_contact_reverse_path_and_external_limitations_are_fail_closed() -> None:
    result = preview_column_base_web_angles(_request(signed_axial_force="20"))
    limitations = dict(result.limitations)
    assert limitations["COLUMN_END_BEARING_FOR_UPLIFT"] == "NOT_REQUIRED"
    assert limitations["BASE_ANGLE_CW_BODY_AND_HEEL_UPLIFT_TRANSFER"] == "NOT_EVALUATED"
    assert limitations["BASE_ANGLE_HORIZONTAL_LEG_UPLIFT_PRYING"] == "NOT_EVALUATED"
    assert limitations["REVERSE_LOAD_LOCAL_FAILURE_PATH_APPLICABILITY"] == "NOT_EVALUATED"
    assert limitations["ANCHOR_TENSION_RESISTANCE"] == "EXTERNAL_DESIGN_REQUIRED"
    assert limitations["CONCRETE_UPLIFT_ANCHORAGE_LIMIT_STATES"] == "EXTERNAL_DESIGN_REQUIRED"
    assert result.assembly_status is ColumnBaseStatus.NOT_EVALUATED
    assert result.ordinary_pass_allowed is False
    assert result.external_handoff.column_end_contact_applicability == "NOT_REQUIRED"  # type: ignore[union-attr]
    handoff = json.loads(result.external_handoff_json)
    assert "anchor_tension_capacity" not in handoff
    assert "concrete_uplift_capacity" not in handoff


def test_compression_contact_and_always_external_limits_are_retained() -> None:
    result = preview_column_base_web_angles(_request(signed_axial_force="-20"))
    limitations = dict(result.limitations)
    assert limitations["COLUMN_END_VS_BASE_ANGLE_BEARING_PARTITION"] == ("EXTERNAL_DESIGN_REQUIRED")
    assert limitations["BASE_ANGLE_TO_CONCRETE_BEARING_RESISTANCE"] == ("EXTERNAL_DESIGN_REQUIRED")
    for name in (
        "CONCRETE_SUBSTRATE_RESISTANCE",
        "ANCHOR_SYSTEM_RESISTANCE",
        "ANCHOR_STEEL_RESISTANCE",
        "ANCHOR_CONCRETE_LIMIT_STATES",
    ):
        assert limitations[name] == "EXTERNAL_DESIGN_REQUIRED"
    assert limitations["EXTERNAL_ANCHOR_DEMAND_VERIFICATION"] == "REQUIRED"


def test_web_normal_uplift_retains_combined_handoff_without_fabricated_branches() -> None:
    result = preview_column_base_web_angles(
        _request(signed_axial_force="20", web_plane_shear="0", web_normal_shear="3")
    )
    assert _magnitudes(result.combined_foundation_wrench.force_s_t_l, Unit.KIP) == (
        Decimal(0),
        Decimal(3),
        Decimal(20),
    )
    assert _magnitudes(result.combined_foundation_wrench.moment_s_t_l, Unit.KIP_IN) == (
        Decimal(-12),
        Decimal(0),
        Decimal(0),
    )
    assert all(group.branch_wrench is None for group in result.anchor_groups)
    assert dict(result.limitations)["WEB_NORMAL_SHEAR_DOUBLE_ANGLE_BRANCH_ALLOCATION"] == (
        "NOT_EVALUATED"
    )


def test_preview_calls_zero_resistance_and_design_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    original = evaluate_multirow_connection_with_resolved_demand

    def counted(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(orchestration, "evaluate_multirow_connection_with_resolved_demand", counted)
    request = _request(signed_axial_force="20", web_plane_shear="0")
    preview = preview_column_base_web_angles(request)
    assert calls == 0
    assert preview.resistance_evaluated is False
    design = design_check_column_base_web_angles(request)
    assert calls == 1
    assert design.ordinary_pass_allowed is False
    assert dict(design.preview.limitations)["ANCHOR_TENSION_RESISTANCE"] == (
        "EXTERNAL_DESIGN_REQUIRED"
    )


def test_r2_handoff_and_serializers_are_deterministic_and_signed() -> None:
    request = _request(signed_axial_force="20")
    first = preview_column_base_web_angles(request)
    second = preview_column_base_web_angles(request)
    assert first.external_handoff_json == second.external_handoff_json
    payload = json.loads(first.external_handoff_json)
    assert payload["signed_axial_force"] == {"unit": "kip", "value": "20"}
    assert payload["axial_mode"] == "UPLIFT"
    assert payload["component_transfer"]["column_web_signed_axial_action"]["value"] == "20"
    assert serialize_column_base_web_angle_preview(first).orchestration_contract_version == (
        "3.5C-R2-RC1"
    )
    design = design_check_column_base_web_angles(request)
    assert serialize_column_base_web_angle_design(design).orchestration_contract_version == (
        "3.5C-R2-RC1"
    )


@pytest.mark.parametrize("signed", ["-20", "20"])
def test_us_si_signed_geometry_wrenches_handoff_and_fingerprints_are_equal(signed: str) -> None:
    us = preview_column_base_web_angles(
        _request(unit_system="US_CUSTOMARY", signed_axial_force=signed)
    )
    si = preview_column_base_web_angles(_request(unit_system="SI", signed_axial_force=signed))
    assert us.engineering_fingerprint == si.engineering_fingerprint
    assert us.application_fingerprint == si.application_fingerprint
    assert us.external_handoff.handoff_fingerprint == si.external_handoff.handoff_fingerprint
    assert us.combined_foundation_wrench.force_s_t_l.longitudinal.canonical_magnitude == (
        si.combined_foundation_wrench.force_s_t_l.longitudinal.canonical_magnitude
    )


def test_signed_domain_rejects_wrong_contract_dimensions_and_user_moments() -> None:
    request = build_column_base_signed_request()
    with pytest.raises(ValueError, match="request_id"):
        replace(request, request_id=" ")
    with pytest.raises(ValueError, match="Unsupported"):
        replace(request, contract_version="3.5C-R3-DRAFT")
    with pytest.raises(ValueError, match="Source length"):
        replace(request, source_length_unit=Unit.MM)
    with pytest.raises(ValueError, match="positive lengths"):
        replace(request, web_bolt_diameter=PhysicalQuantity.of(0, Unit.IN))
    with pytest.raises(ValueError, match="smaller"):
        replace(request, web_hole_diameter=PhysicalQuantity.of("0.4", Unit.IN))
    with pytest.raises(ValueError, match="force quantities"):
        replace(request, signed_axial_force=PhysicalQuantity.of(1, Unit.IN))
    with pytest.raises(ValueError, match="moment quantities"):
        replace(
            request,
            user_moment=ColumnBaseVector(
                *tuple(PhysicalQuantity.of(0, Unit.KIP) for _ in range(3))
            ),
        )
    with pytest.raises(ValueError, match="MOMENT_NOT_ALLOWED"):
        replace(
            request,
            user_moment=ColumnBaseVector(
                PhysicalQuantity.of(1, Unit.KIP_IN),
                PhysicalQuantity.of(0, Unit.KIP_IN),
                PhysicalQuantity.of(0, Unit.KIP_IN),
            ),
        )
    with pytest.raises(ValueError, match="action_reference"):
        replace(
            request,
            action_reference=ColumnBaseVector(
                PhysicalQuantity.of(0, Unit.KIP),
                PhysicalQuantity.of(0, Unit.KIP),
                PhysicalQuantity.of(0, Unit.KIP),
            ),
        )


def test_production_source_does_not_access_controlled_golden() -> None:
    production = (_ROOT / "backend/src/frp_master_connection").rglob("*.py")
    assert all(
        "stage_3_5c_r2_signed_axial_uplift" not in path.read_text(encoding="utf-8")
        for path in production
    )
