"""Shared exact fixtures for the Stage 3.2 Tee vertical slice."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from frp_master_connection.api.tee_mapping import map_tee_connector_request
from frp_master_connection.api.tee_schemas import TeeConnectorRequestDTO
from frp_master_connection.application import TeeConnectorOrchestrationRequest


def _q(value: str, unit: str = "in") -> dict[str, str]:
    return {"value": value, "unit": unit}


def build_tee_payload(
    *,
    role: str = "COLUMN",
    selected_flange: str = "POSITIVE_LOCAL_Z",
    force: tuple[str, str, str] | None = None,
    moment: tuple[str, str, str] = ("0", "0", "0"),
    reference: tuple[str, str, str] = ("0", "0", "0"),
    unit_system: str = "US_CUSTOMARY",
) -> dict[str, Any]:
    """Return a mutable transport payload with independent A/B layout objects."""

    si = unit_system == "SI"
    resolved_force = force or (("0.1", "0", "0") if role == "BEAM" else ("0", "0", "0.1"))
    length_unit = "mm" if si else "in"
    force_unit = "kN" if si else "kip"
    moment_unit = "kN-mm" if si else "kip-in"
    factor = "25.4" if si else "1"

    def length(us_value: str) -> dict[str, str]:
        if not si:
            return _q(us_value)
        from decimal import Decimal

        return _q(str(Decimal(us_value) * Decimal(factor)), length_unit)

    layout = {
        "row_count": 2,
        "bolts_per_row": 2,
        "pitch": length("2"),
        "gauge": length("2"),
        "unloaded_end_distance": length("1"),
        "loaded_end_distance": length("1"),
        "negative_side_distance": length("1"),
        "positive_side_distance": length("1"),
    }
    return {
        "orchestration_contract_version": "3.2-RC1",
        "request_id": f"TEE-{role}-{unit_system}",
        "unit_system": unit_system,
        "source_length_unit": length_unit,
        "support_role": role,
        "selected_support_flange": selected_flange,
        "connector_dimensions": {
            "connector_length": length("8"),
            "flange_width": length("6"),
            "flange_thickness": length("0.5"),
            "stem_depth": length("4"),
            "stem_thickness": length("0.375"),
        },
        "support_dimensions": {
            "member_length": length("16"),
            "overall_depth": length("8"),
            "flange_width": length("8"),
            "web_thickness": length("0.5"),
            "flange_thickness": length("0.75"),
        },
        "brace_dimensions": {
            "width": length("8"),
            "thickness": length("0.375"),
            "view_length": length("6"),
        },
        "interface_a_layout": deepcopy(layout),
        "interface_b_layout": deepcopy(layout),
        "bolt_diameter": length("0.5"),
        "hole_basis": "SI_PRINTED" if si else "US_CUSTOMARY_PRINTED",
        "global_force": {
            "x": resolved_force[0],
            "y": resolved_force[1],
            "z": resolved_force[2],
            "unit": force_unit,
        },
        "global_moment": {
            "x": moment[0],
            "y": moment[1],
            "z": moment[2],
            "unit": moment_unit,
        },
        "global_reference_point": {
            "x": reference[0],
            "y": reference[1],
            "z": reference[2],
            "unit": length_unit,
        },
        "connector_material": "PULTRUDED_FRP",
        "fastener_material": "STAINLESS_STEEL_316",
        "fastener_snapshot_id": "ASTM_F593_17_GROUP_2_316_316L",
    }


def build_tee_request(
    *,
    role: str = "COLUMN",
    selected_flange: str = "POSITIVE_LOCAL_Z",
    force: tuple[str, str, str] | None = None,
    moment: tuple[str, str, str] = ("0", "0", "0"),
    reference: tuple[str, str, str] = ("0", "0", "0"),
    unit_system: str = "US_CUSTOMARY",
) -> TeeConnectorOrchestrationRequest:
    """Map a standard fixture through the same strict DTO boundary as HTTP."""

    return map_tee_connector_request(
        TeeConnectorRequestDTO.model_validate(
            build_tee_payload(
                role=role,
                selected_flange=selected_flange,
                force=force,
                moment=moment,
                reference=reference,
                unit_system=unit_system,
            )
        )
    )


def build_tee_r2_payload(
    *,
    profile_family: str = "ANGLE",
    selected_surface: str | None = None,
    profile_orientation: str = "ROTATION_0",
    role: str = "COLUMN",
    selected_flange: str = "POSITIVE_LOCAL_Z",
    force: tuple[str, str, str] | None = None,
    moment: tuple[str, str, str] = ("0", "0", "0"),
    reference: tuple[str, str, str] = ("0", "0", "0"),
    unit_system: str = "US_CUSTOMARY",
) -> dict[str, Any]:
    """Return one strict R2 payload with real family-specific profile dimensions."""

    payload = build_tee_payload(
        role=role,
        selected_flange=selected_flange,
        force=force,
        moment=moment,
        reference=reference,
        unit_system=unit_system,
    )
    payload["orchestration_contract_version"] = "3.2-R2"
    payload.pop("brace_dimensions")
    length_unit = "mm" if unit_system == "SI" else "in"

    def length(us_value: str) -> dict[str, str]:
        if unit_system != "SI":
            return _q(us_value, length_unit)
        from decimal import Decimal

        return _q(str(Decimal(us_value) * Decimal("25.4")), length_unit)

    defaults = {
        "ANGLE": "LEG_Y_OUTER",
        "CHANNEL": "WEB_OUTER",
        "WIDE_FLANGE_I": "WEB_POS_FACE",
        "RECTANGULAR_HOLLOW_SECTION": "Y_POS_FACE",
        "FLAT_PLATE": "FACE_NEG",
        "ROUND_HOLLOW_SECTION": None,
    }
    dimensions: dict[str, dict[str, str]]
    if profile_family == "ANGLE":
        dimensions = {
            "leg_y": length("8"),
            "leg_z": length("8"),
            "thickness": length("0.375"),
            "member_length": length("6"),
        }
    elif profile_family in {"CHANNEL", "WIDE_FLANGE_I"}:
        dimensions = {
            "depth": length("8"),
            "flange_width": length("8"),
            "web_thickness": length("0.375"),
            "flange_thickness": length("0.5"),
            "member_length": length("6"),
        }
    elif profile_family == "RECTANGULAR_HOLLOW_SECTION":
        dimensions = {
            "depth": length("8"),
            "width": length("8"),
            "wall_thickness": length("0.375"),
            "member_length": length("6"),
        }
    elif profile_family == "SOLID_RECTANGULAR_SECTION":
        dimensions = {
            "depth": length("6"),
            "width": length("8"),
            "member_length": length("6"),
        }
    elif profile_family == "FLAT_PLATE":
        dimensions = {
            "width": length("8"),
            "thickness": length("0.375"),
            "member_length": length("6"),
        }
    elif profile_family == "ROUND_HOLLOW_SECTION":
        dimensions = {
            "outer_diameter": length("8"),
            "wall_thickness": length("0.375"),
            "member_length": length("6"),
        }
    else:
        raise ValueError("Unsupported fixture profile family.")
    payload["connected_member_profile"] = {
        "profile_id": f"tee-r2-{profile_family.lower()}-profile",
        "role": "BRACE",
        "profile_family": profile_family,
        "size_basis": "CUSTOM_DIMENSIONS",
        "dimensions": dimensions,
        "profile_orientation": profile_orientation,
        "selected_profile_surface": (
            defaults[profile_family] if selected_surface is None else selected_surface
        ),
        "material_kind": "PULTRUDED_FRP",
    }
    return payload


def build_tee_c2_payload(
    *,
    support_target: str = "W_COLUMN_FLANGE",
    connected_profile_family: str = "FLAT_PLATE",
    unit_system: str = "US_CUSTOMARY",
) -> dict[str, Any]:
    """Return a strict C2 payload using the one shared supporting-member contract."""

    payload = build_tee_r2_payload(
        profile_family=connected_profile_family,
        selected_surface=(
            "Z_POS_FACE"
            if connected_profile_family
            in {"RECTANGULAR_HOLLOW_SECTION", "SOLID_RECTANGULAR_SECTION"}
            else None
        ),
        unit_system=unit_system,
    )
    payload["orchestration_contract_version"] = "3.3C2-RC1"
    payload["hole_basis"] = "US_CUSTOMARY_PRINTED"
    payload.pop("support_role")
    payload.pop("selected_support_flange")
    payload.pop("support_dimensions")
    length_unit = "mm" if unit_system == "SI" else "in"

    def length(us_value: str) -> dict[str, str]:
        if unit_system != "SI":
            return _q(us_value, length_unit)
        from decimal import Decimal

        return _q(str(Decimal(us_value) * Decimal("25.4")), length_unit)

    if connected_profile_family == "RECTANGULAR_HOLLOW_SECTION":
        payload["connected_member_profile"]["dimensions"] = {
            "depth": length("6"),
            "width": length("8"),
            "wall_thickness": length("0.5"),
            "member_length": length("8"),
        }
        payload["connected_member_profile"]["selected_profile_surface"] = "Z_POS_FACE"
        payload["connector_dimensions"]["stem_thickness"] = length("0.5")
    elif connected_profile_family == "SOLID_RECTANGULAR_SECTION":
        payload["connected_member_profile"]["dimensions"] = {
            "depth": length("6"),
            "width": length("8"),
            "member_length": length("8"),
        }
        payload["connected_member_profile"]["selected_profile_surface"] = "Z_POS_FACE"
        payload["connector_dimensions"]["stem_thickness"] = length("0.5")

    common: dict[str, Any] = {
        "profile_id": "tee-support-profile",
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
    if support_target == "W_BEAM_FLANGE":
        payload["request_id"] = f"TEE-BEAM-{unit_system}"
        payload["global_force"] = {
            "x": "0.1" if unit_system == "US_CUSTOMARY" else "0.44482216152605",
            "y": "0",
            "z": "0",
            "unit": "kip" if unit_system == "US_CUSTOMARY" else "kN",
        }
    elif unit_system == "SI":
        payload["global_force"] = {
            "x": "0",
            "y": "0",
            "z": "0.44482216152605",
            "unit": "kN",
        }
    return payload


def build_tee_c2_workspace_rhs_payload() -> dict[str, Any]:
    """Return the exact C2 workspace request that exposed the RHS routing defect."""

    payload = build_tee_c2_payload(connected_profile_family="RECTANGULAR_HOLLOW_SECTION")
    payload["request_id"] = "TEE-WORKSPACE-US_CUSTOMARY"
    profile = payload["connected_member_profile"]
    assert isinstance(profile, dict)
    profile.update(
        {
            "profile_id": "tee-connected-brace-profile",
            "selected_profile_surface": "Y_POS_FACE",
            "dimensions": {
                "member_length": _q("8"),
                "depth": _q("6"),
                "width": _q("4"),
                "wall_thickness": _q("0.5"),
            },
        }
    )
    connector = payload["connector_dimensions"]
    assert isinstance(connector, dict)
    connector["stem_thickness"] = _q("0.375")
    for key, horizontal in (("interface_a_layout", "0"), ("interface_b_layout", "-1")):
        layout = payload[key]
        assert isinstance(layout, dict)
        layout.update(
            {
                "placement_mode": "GROUP_OFFSET_CONTROLLED",
                "vertical_offset": _q("-2"),
                "horizontal_offset": _q(horizontal),
            }
        )
    return payload


def build_tee_r2_request(
    *,
    profile_family: str = "ANGLE",
    selected_surface: str | None = None,
    profile_orientation: str = "ROTATION_0",
    role: str = "COLUMN",
    selected_flange: str = "POSITIVE_LOCAL_Z",
    force: tuple[str, str, str] | None = None,
    moment: tuple[str, str, str] = ("0", "0", "0"),
    reference: tuple[str, str, str] = ("0", "0", "0"),
    unit_system: str = "US_CUSTOMARY",
) -> TeeConnectorOrchestrationRequest:
    return map_tee_connector_request(
        TeeConnectorRequestDTO.model_validate(
            build_tee_r2_payload(
                profile_family=profile_family,
                selected_surface=selected_surface,
                profile_orientation=profile_orientation,
                role=role,
                selected_flange=selected_flange,
                force=force,
                moment=moment,
                reference=reference,
                unit_system=unit_system,
            )
        )
    )


def build_tee_r4_benchmark_payload(*, unit_system: str = "US_CUSTOMARY") -> dict[str, Any]:
    """Return the controlled physically equivalent R4 flat-plate benchmark."""

    force = ("0", "0", "0.1") if unit_system == "US_CUSTOMARY" else ("0", "0", "0.44482216152605")
    payload = build_tee_r2_payload(
        profile_family="FLAT_PLATE",
        selected_surface="FACE_POS",
        force=force,
        unit_system=unit_system,
    )
    payload["hole_basis"] = "US_CUSTOMARY_PRINTED"
    return payload


def build_tee_r4_benchmark_request(
    *, unit_system: str = "US_CUSTOMARY"
) -> TeeConnectorOrchestrationRequest:
    return map_tee_connector_request(
        TeeConnectorRequestDTO.model_validate(
            build_tee_r4_benchmark_payload(unit_system=unit_system)
        )
    )


def build_tee_r7_angle_payload(
    *,
    unloaded_end_distance: str = "1.2815",
    profile_orientation: str = "ROTATION_0",
) -> dict[str, Any]:
    """Return the controlled R7 Angle fixture with finite hole-edge clearance."""

    payload = build_tee_r2_payload(
        profile_family="ANGLE",
        selected_surface="LEG_Y_OUTER",
        profile_orientation=profile_orientation,
    )
    payload["connected_member_profile"]["dimensions"] = {
        "leg_y": _q("6"),
        "leg_z": _q("6"),
        "thickness": _q("0.5"),
        "member_length": _q("8"),
    }
    payload["interface_a_layout"]["unloaded_end_distance"] = _q(unloaded_end_distance)
    return payload


def build_tee_r7_angle_request(
    *,
    unloaded_end_distance: str = "1.2815",
    profile_orientation: str = "ROTATION_0",
) -> TeeConnectorOrchestrationRequest:
    """Map the controlled R7 Angle fixture through the strict HTTP DTO boundary."""

    return map_tee_connector_request(
        TeeConnectorRequestDTO.model_validate(
            build_tee_r7_angle_payload(
                unloaded_end_distance=unloaded_end_distance,
                profile_orientation=profile_orientation,
            )
        )
    )


def build_tee_r8_profile_wall_payload(
    *,
    profile_family: str,
    unloaded_end_distance: str = "1.7815",
    selected_surface: str | None = None,
) -> dict[str, Any]:
    """Return one controlled R8 Channel or RHS full-Tee fixture."""

    dimensions_by_family = {
        "CHANNEL": {
            "depth": _q("6"),
            "flange_width": _q("3"),
            "web_thickness": _q("0.5"),
            "flange_thickness": _q("0.5"),
            "member_length": _q("8"),
        },
        "RECTANGULAR_HOLLOW_SECTION": {
            "depth": _q("6"),
            "width": _q("4"),
            "wall_thickness": _q("0.5"),
            "member_length": _q("8"),
        },
    }
    selected_by_family = {
        "CHANNEL": "WEB_OUTER",
        "RECTANGULAR_HOLLOW_SECTION": "Y_POS_FACE",
    }
    if profile_family not in dimensions_by_family:
        raise ValueError("R8 full-Tee fixtures support only Channel and RHS profiles.")
    payload = build_tee_r2_payload(
        profile_family=profile_family,
        selected_surface=selected_surface or selected_by_family[profile_family],
    )
    payload["connected_member_profile"]["dimensions"] = dimensions_by_family[profile_family]
    payload["interface_a_layout"]["unloaded_end_distance"] = _q(unloaded_end_distance)
    return payload


def build_tee_r8_profile_wall_request(
    *,
    profile_family: str,
    unloaded_end_distance: str = "1.7815",
    selected_surface: str | None = None,
) -> TeeConnectorOrchestrationRequest:
    """Map one controlled R8 profile-wall fixture through the strict DTO boundary."""

    return map_tee_connector_request(
        TeeConnectorRequestDTO.model_validate(
            build_tee_r8_profile_wall_payload(
                profile_family=profile_family,
                unloaded_end_distance=unloaded_end_distance,
                selected_surface=selected_surface,
            )
        )
    )


__all__ = (
    "build_tee_c2_payload",
    "build_tee_payload",
    "build_tee_r2_payload",
    "build_tee_r2_request",
    "build_tee_r4_benchmark_payload",
    "build_tee_r4_benchmark_request",
    "build_tee_r7_angle_payload",
    "build_tee_r7_angle_request",
    "build_tee_r8_profile_wall_payload",
    "build_tee_r8_profile_wall_request",
    "build_tee_request",
)
