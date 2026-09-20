"""Shared exact transport fixtures for the Stage 3.3A single clip angle."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any

from frp_master_connection.api.clip_angle_mapping import map_clip_angle_request
from frp_master_connection.api.clip_angle_schemas import ClipAngleConnectorRequestDTO
from frp_master_connection.application import ClipAngleOrchestrationRequest


def build_clip_angle_payload(
    *,
    unit_system: str = "US_CUSTOMARY",
    force: tuple[str, str, str] = ("0", "0", "3"),
    moment: tuple[str, str, str] = ("0", "0", "0"),
    reference: tuple[str, str, str] = ("2.25", "2.25", "0"),
    profile_family: str = "FLAT_PLATE",
    connected_role: str = "BRACE",
    support_role: str = "W_COLUMN_FLANGE",
) -> dict[str, Any]:
    """Return the mutable controlled default in either exact transport unit system."""

    si = unit_system == "SI"
    length_unit = "mm" if si else "in"
    force_unit = "kN" if si else "kip"
    moment_unit = "kN-mm" if si else "kip-in"

    def length(value: str) -> dict[str, str]:
        converted = Decimal(value) * (Decimal("25.4") if si else Decimal(1))
        return {"value": str(converted), "unit": length_unit}

    def force_value(value: str) -> str:
        converted = Decimal(value) * (Decimal("4.4482216152605") if si else Decimal(1))
        return str(converted)

    def moment_value(value: str) -> str:
        converted = Decimal(value) * (Decimal("112.9848290276167") if si else Decimal(1))
        return str(converted)

    layout = {
        "row_count": 2,
        "bolts_per_row": 2,
        "pitch": length("2"),
        "gauge": length("2"),
        "heel_edge_distance": length("0.75"),
        "free_edge_distance": length("0.75"),
        "negative_end_distance": length("3"),
        "positive_end_distance": length("3"),
    }
    profile_dimensions: dict[str, dict[str, str]]
    selected_surface: str
    if profile_family == "FLAT_PLATE":
        profile_dimensions = {
            "member_length": length("8"),
            "width": length("6"),
            "thickness": length("0.375"),
        }
        selected_surface = "FACE_POS"
    elif profile_family == "ANGLE":
        profile_dimensions = {
            "member_length": length("8"),
            "leg_y": length("6"),
            "leg_z": length("6"),
            "thickness": length("0.375"),
        }
        selected_surface = "LEG_Y_OUTER"
    elif profile_family in {"CHANNEL", "WIDE_FLANGE_I"}:
        profile_dimensions = {
            "member_length": length("8"),
            "depth": length("6"),
            "flange_width": length("6"),
            "web_thickness": length("0.375"),
            "flange_thickness": length("0.5"),
        }
        selected_surface = "WEB_OUTER" if profile_family == "CHANNEL" else "WEB_POS_FACE"
    elif profile_family == "RECTANGULAR_HOLLOW_SECTION":
        profile_dimensions = {
            "member_length": length("8"),
            "depth": length("6"),
            "width": length("6"),
            "wall_thickness": length("0.375"),
        }
        selected_surface = "Y_POS_FACE"
    elif profile_family == "SOLID_RECTANGULAR_SECTION":
        profile_dimensions = {
            "member_length": length("8"),
            "depth": length("6"),
            "width": length("6"),
        }
        selected_surface = "Z_POS_FACE"
    else:
        raise ValueError("Unsupported clip-angle fixture profile family.")
    return {
        "orchestration_contract_version": "3.3A-RC1",
        "request_id": f"CLIP-ANGLE-{unit_system}",
        "unit_system": unit_system,
        "source_length_unit": length_unit,
        "hand": "POSITIVE_S_SIDE",
        "support_role": support_role,
        "selected_support_flange": "POSITIVE_LOCAL_Z",
        "connector_dimensions": {
            "connected_leg_width": length("4"),
            "support_leg_width": length("4"),
            "thickness": length("0.5"),
            "connector_length": length("8"),
        },
        "support_dimensions": {
            "member_length": length("16"),
            "overall_depth": length("8"),
            "flange_width": length("8"),
            "web_thickness": length("0.5"),
            "flange_thickness": length("0.75"),
        },
        "connected_member_profile": {
            "profile_id": f"clip-angle-{profile_family.lower()}-profile",
            "role": connected_role,
            "profile_family": profile_family,
            "size_basis": "CUSTOM_DIMENSIONS",
            "dimensions": profile_dimensions,
            "profile_orientation": "ROTATION_0",
            "selected_profile_surface": selected_surface,
        },
        "interface_a_layout": deepcopy(layout),
        "interface_b_layout": deepcopy(layout),
        "bolt_diameter": length("0.5"),
        "hole_diameter": length("0.563"),
        "hole_basis": "SI_PRINTED" if si else "US_CUSTOMARY_PRINTED",
        "global_force": {
            "x": force_value(force[0]),
            "y": force_value(force[1]),
            "z": force_value(force[2]),
            "unit": force_unit,
        },
        "global_moment": {
            "x": moment_value(moment[0]),
            "y": moment_value(moment[1]),
            "z": moment_value(moment[2]),
            "unit": moment_unit,
        },
        "global_reference_point": {
            "x": length(reference[0])["value"],
            "y": length(reference[1])["value"],
            "z": length(reference[2])["value"],
            "unit": length_unit,
        },
        "connector_material": "PULTRUDED_FRP",
        "fastener_material": "STAINLESS_STEEL_316",
        "fastener_snapshot_id": "ASTM_F593_17_GROUP_2_316_316L",
    }


def build_clip_angle_c2_payload(
    *,
    support_target: str = "W_COLUMN_FLANGE",
    connected_profile_family: str = "FLAT_PLATE",
    unit_system: str = "US_CUSTOMARY",
) -> dict[str, Any]:
    """Return a strict C2 payload using the one shared support DTO."""

    payload = build_clip_angle_payload(
        unit_system=unit_system,
        profile_family=connected_profile_family,
    )
    payload["orchestration_contract_version"] = "3.3C2-RC1"
    payload.pop("support_role")
    payload.pop("selected_support_flange")
    payload.pop("support_dimensions")
    si = unit_system == "SI"
    length_unit = "mm" if si else "in"

    def length(value: str) -> dict[str, str]:
        converted = Decimal(value) * (Decimal("25.4") if si else Decimal(1))
        return {"value": str(converted), "unit": length_unit}

    if connected_profile_family == "RECTANGULAR_HOLLOW_SECTION":
        payload["connected_member_profile"]["dimensions"] = {
            "member_length": length("8"),
            "depth": length("6"),
            "width": length("8"),
            "wall_thickness": length("0.5"),
        }
        payload["connected_member_profile"]["selected_profile_surface"] = "Z_POS_FACE"
    elif connected_profile_family == "SOLID_RECTANGULAR_SECTION":
        payload["connected_member_profile"]["dimensions"] = {
            "member_length": length("8"),
            "depth": length("6"),
            "width": length("8"),
        }
        payload["connected_member_profile"]["selected_profile_surface"] = "Z_POS_FACE"

    common: dict[str, Any] = {
        "profile_id": "clip-angle-support-profile",
        "role": "BEAM" if support_target == "W_BEAM_FLANGE" else "COLUMN",
        "profile_orientation": "ROTATION_0",
        "member_length": length("16"),
    }
    if support_target in {"W_COLUMN_FLANGE", "W_BEAM_FLANGE", "W_COLUMN_WEB"}:
        support_profile = {
            **common,
            "profile_family": "WIDE_FLANGE_I",
            "depth": length("8"),
            "flange_width": length("8"),
            "web_thickness": length("0.5"),
            "flange_thickness": length("0.75"),
            "selected_profile_surface": (
                "WEB_POS_FACE" if support_target == "W_COLUMN_WEB" else "FLANGE_POS_OUTER"
            ),
        }
    elif support_target == "CHANNEL_COLUMN_WEB":
        support_profile = {
            **common,
            "profile_family": "CHANNEL",
            "depth": length("8"),
            "flange_width": length("8"),
            "web_thickness": length("0.5"),
            "flange_thickness": length("0.5"),
            "selected_profile_surface": "WEB_OUTER",
        }
    elif support_target == "ANGLE_COLUMN_LEG":
        support_profile = {
            **common,
            "profile_family": "ANGLE",
            "leg_y": length("8"),
            "leg_z": length("8"),
            "thickness": length("0.5"),
            "selected_profile_surface": "LEG_Y_OUTER",
        }
    elif support_target == "RECTANGULAR_HOLLOW_COLUMN_WALL":
        support_profile = {
            **common,
            "profile_family": "RECTANGULAR_HOLLOW_SECTION",
            "width": length("8"),
            "depth": length("6"),
            "wall_thickness": length("0.5"),
            "selected_profile_surface": "Z_POS_FACE",
        }
    elif support_target == "SOLID_RECTANGULAR_COLUMN_FACE":
        support_profile = {
            **common,
            "profile_family": "SOLID_RECTANGULAR_SECTION",
            "width": length("8"),
            "depth": length("6"),
            "selected_profile_surface": "Z_POS_FACE",
        }
    else:
        raise ValueError("Unsupported C2 support fixture target.")
    payload["support_target_id"] = support_target
    payload["support_profile"] = support_profile
    return payload


def build_clip_angle_request(
    *,
    unit_system: str = "US_CUSTOMARY",
    force: tuple[str, str, str] = ("0", "0", "3"),
    moment: tuple[str, str, str] = ("0", "0", "0"),
    reference: tuple[str, str, str] = ("2.25", "2.25", "0"),
    profile_family: str = "FLAT_PLATE",
    connected_role: str = "BRACE",
    support_role: str = "W_COLUMN_FLANGE",
) -> ClipAngleOrchestrationRequest:
    return map_clip_angle_request(
        ClipAngleConnectorRequestDTO.model_validate(
            build_clip_angle_payload(
                unit_system=unit_system,
                force=force,
                moment=moment,
                reference=reference,
                profile_family=profile_family,
                connected_role=connected_role,
                support_role=support_role,
            )
        )
    )


__all__ = (
    "build_clip_angle_c2_payload",
    "build_clip_angle_payload",
    "build_clip_angle_request",
)
