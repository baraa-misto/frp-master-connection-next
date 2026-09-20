"""Controlled exact transport fixtures for Stage 3.3B."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from frp_master_connection.api.paired_clip_angle_mapping import map_paired_clip_angle_request
from frp_master_connection.api.paired_clip_angle_schemas import (
    PairedClipAngleConnectorRequestDTO,
)
from frp_master_connection.application import PairedClipAngleOrchestrationRequest
from tests.clip_angle_fixtures import build_clip_angle_c2_payload, build_clip_angle_payload


def build_paired_clip_angle_payload(
    *,
    unit_system: str = "US_CUSTOMARY",
    force: tuple[str, str, str] = ("0", "0", "4"),
    moment: tuple[str, str, str] = ("0", "0", "0"),
    reference: tuple[str, str, str] = ("0", "2.25", "0"),
    profile_family: str = "FLAT_PLATE",
    connected_role: str = "BRACE",
    support_role: str = "W_COLUMN_FLANGE",
) -> dict[str, Any]:
    value = build_clip_angle_payload(
        unit_system=unit_system,
        force=force,
        moment=moment,
        reference=reference,
        profile_family=profile_family,
        connected_role=connected_role,
        support_role=support_role,
    )
    value["orchestration_contract_version"] = "3.3B-RC1"
    value.pop("hand")
    value["common_member_layout"] = value.pop("interface_a_layout")
    value["mirrored_support_layout"] = value.pop("interface_b_layout")
    value["pair_symmetry"] = "LOCKED_IDENTICAL_MIRROR"
    value["connected_member_inclination_degrees"] = "0"
    value["support_dimensions"]["flange_width"] = _length("10", unit_system)
    profile = value["connected_member_profile"]
    if profile_family == "FLAT_PLATE":
        profile["dimensions"]["thickness"] = _length("0.5", unit_system)
    elif profile_family == "WIDE_FLANGE_I":
        profile["dimensions"] = {
            "member_length": _length("8", unit_system),
            "depth": _length("10", unit_system),
            "flange_width": _length("8", unit_system),
            "web_thickness": _length("0.5", unit_system),
            "flange_thickness": _length("0.5", unit_system),
        }
        profile["selected_profile_surface"] = "WEB_POS_FACE"
    elif profile_family == "CHANNEL":
        profile["dimensions"] = {
            "member_length": _length("8", unit_system),
            "depth": _length("10", unit_system),
            "flange_width": _length("4", unit_system),
            "web_thickness": _length("0.5", unit_system),
            "flange_thickness": _length("0.5", unit_system),
        }
        profile["selected_profile_surface"] = "WEB_OUTER"
    return cast_payload(value)


def _length(value: str, unit_system: str) -> dict[str, str]:
    if unit_system == "SI":
        from decimal import Decimal

        return {"value": str(Decimal(value) * Decimal("25.4")), "unit": "mm"}
    return {"value": value, "unit": "in"}


def cast_payload(value: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(value)


def build_paired_clip_angle_request(**kwargs: object) -> PairedClipAngleOrchestrationRequest:
    return map_paired_clip_angle_request(
        PairedClipAngleConnectorRequestDTO.model_validate(
            build_paired_clip_angle_payload(**kwargs)  # type: ignore[arg-type]
        )
    )


def build_paired_clip_angle_c3_payload(
    *,
    support_target: str = "W_COLUMN_FLANGE",
    connected_profile_family: str = "ANGLE",
    unit_system: str = "US_CUSTOMARY",
) -> dict[str, Any]:
    payload = build_clip_angle_c2_payload(
        support_target=support_target,
        connected_profile_family=connected_profile_family,
        unit_system=unit_system,
    )
    payload["orchestration_contract_version"] = "3.3C3-RC1"
    payload["request_id"] = f"PAIRED-C3-{connected_profile_family}-{support_target}"
    payload.pop("hand")
    payload["common_member_layout"] = payload.pop("interface_a_layout")
    payload["mirrored_support_layout"] = payload.pop("interface_b_layout")
    payload["pair_symmetry"] = "LOCKED_IDENTICAL_MIRROR"
    payload["global_force"]["z"] = "4" if unit_system == "US_CUSTOMARY" else "17.792886461042"
    payload["global_reference_point"]["x"] = "0"
    return cast_payload(payload)


def build_paired_clip_angle_c3_request(**kwargs: object) -> PairedClipAngleOrchestrationRequest:
    return map_paired_clip_angle_request(
        PairedClipAngleConnectorRequestDTO.model_validate(
            build_paired_clip_angle_c3_payload(**kwargs)  # type: ignore[arg-type]
        )
    )


__all__ = (
    "build_paired_clip_angle_c3_payload",
    "build_paired_clip_angle_c3_request",
    "build_paired_clip_angle_payload",
    "build_paired_clip_angle_request",
)
