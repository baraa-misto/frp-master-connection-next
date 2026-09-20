"""Controlled Stage 3.5A exact transport fixtures."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any

from frp_master_connection.api.beam_concrete_paired_angle_mapping import (
    map_beam_concrete_paired_angle_request,
)
from frp_master_connection.api.beam_concrete_paired_angle_schemas import (
    BeamConcretePairedAngleRequestDTO,
)
from frp_master_connection.application import BeamConcretePairedAngleRequest
from tests.paired_clip_angle_fixtures import build_paired_clip_angle_payload


def _length(value: str, unit_system: str) -> dict[str, str]:
    if unit_system == "SI":
        return {"value": str(Decimal(value) * Decimal("25.4")), "unit": "mm"}
    return {"value": value, "unit": "in"}


def build_beam_concrete_paired_angle_payload(
    *,
    unit_system: str = "US_CUSTOMARY",
    contract_version: str = "3.5A-RC1",
    profile_family: str = "WIDE_FLANGE_I",
    major_shear: str = "-4",
    minor_shear: str = "0",
    axial_force: str = "0",
) -> dict[str, Any]:
    force_factor = Decimal("4.4482216152605")

    def force(value: str) -> str:
        return str(Decimal(value) * force_factor) if unit_system == "SI" else value

    paired = build_paired_clip_angle_payload(
        unit_system=unit_system,
        force=("0", force(axial_force), force(major_shear)),
        reference=("0", "2", "0"),
        profile_family="WIDE_FLANGE_I",
        connected_role="BEAM",
    )

    def length(value: str) -> dict[str, str]:
        return _length(value, unit_system)

    force_unit = "kip" if unit_system == "US_CUSTOMARY" else "kN"
    moment_unit = "kip-in" if unit_system == "US_CUSTOMARY" else "kN-mm"
    reaction = force(major_shear)
    beam = deepcopy(paired["connected_member_profile"])
    beam.update(
        {
            "profile_id": "beam-concrete-connected-beam-profile",
            "role": "BEAM",
            "profile_family": profile_family,
            "size_basis": "CUSTOM_DIMENSIONS",
            "profile_orientation": "ROTATION_0",
        }
    )
    if profile_family == "FLAT_PLATE":
        beam["dimensions"] = {
            "member_length": length("16"),
            "width": length("6"),
            "thickness": length("0.5"),
        }
        beam["selected_profile_surface"] = "FACE_POS"
    elif profile_family == "ANGLE":
        beam["dimensions"] = {
            "member_length": length("16"),
            "leg_y": length("6"),
            "leg_z": length("6"),
            "thickness": length("0.5"),
        }
        beam["selected_profile_surface"] = "LEG_Y_OUTER"
    elif profile_family == "CHANNEL":
        beam["dimensions"] = {
            "member_length": length("16"),
            "depth": length("8"),
            "flange_width": length("4"),
            "web_thickness": length("0.5"),
            "flange_thickness": length("0.5"),
        }
        beam["selected_profile_surface"] = "WEB_OUTER"
    elif profile_family == "WIDE_FLANGE_I":
        beam["dimensions"] = {
            "member_length": length("16"),
            "depth": length("10"),
            "flange_width": length("8"),
            "web_thickness": length("0.5"),
            "flange_thickness": length("0.5"),
        }
        beam["selected_profile_surface"] = "WEB_POS_FACE"
    elif profile_family == "RECTANGULAR_HOLLOW_SECTION":
        beam["dimensions"] = {
            "member_length": length("16"),
            "depth": length("6"),
            "width": length("4"),
            "wall_thickness": length("0.5"),
        }
        beam["selected_profile_surface"] = "Y_POS_FACE"
    elif profile_family == "SOLID_RECTANGULAR_SECTION":
        beam["dimensions"] = {
            "member_length": length("16"),
            "depth": length("6"),
            "width": length("4"),
        }
        beam["selected_profile_surface"] = "Y_POS_FACE"
    else:
        raise ValueError("Unsupported Stage 3.5A-R1 connected profile fixture.")
    common = deepcopy(paired["common_member_layout"])
    common.update(
        {
            "pitch": length("2"),
            "gauge": length("2"),
            "heel_edge_distance": length("1"),
            "free_edge_distance": length("1"),
            "negative_end_distance": length("3"),
            "positive_end_distance": length("3"),
        }
    )
    payload: dict[str, Any] = {
        "orchestration_contract_version": contract_version,
        "request_id": (f"STAGE-{contract_version.removesuffix('-RC1')}-G1-{unit_system}"),
        "unit_system": unit_system,
        "source_length_unit": "in" if unit_system == "US_CUSTOMARY" else "mm",
        "wall": {
            "width": length("48"),
            "height": length("48"),
            "thickness": length("8"),
            "connection_origin_h": length("0"),
            "connection_origin_v": length("0"),
        },
        "beam_profile": beam,
        "beam_end_gap": length("0.5"),
        "connector_dimensions": {
            "connected_leg_width": length("4"),
            "support_leg_width": length("4"),
            "thickness": length("0.5"),
            "connector_length": length("8"),
        },
        "connector_length_anchor_position": length("0"),
        "common_beam_layout": common,
        "wall_anchor_pattern": {
            "row_count": 1 if contract_version in {"3.5A-R1-RC1", "3.5A-R2-RC1"} else 2,
            "anchors_per_row": 1 if contract_version in {"3.5A-R1-RC1", "3.5A-R2-RC1"} else 2,
            "pitch": length("2"),
            "gauge": length("2"),
            "centroid_offset_h": length("3"),
            "centroid_v": length("0"),
        },
        "common_bolt_diameter": length("0.5"),
        "common_hole_diameter": length("0.563"),
        "external_anchor": {
            "nominal_diameter": length("0.5"),
            "hole_diameter": length("0.563"),
            "specified_embedment": length("4"),
            "washer_outside_diameter": length("1.0625"),
            "washer_thickness": length("0.109"),
            "system_classification": "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR",
        },
        "user_moment_hvn": {"x": "0", "y": "0", "z": "0", "unit": moment_unit},
    }
    if contract_version == "3.5A-R2-RC1":
        payload.update(
            {
                "major_shear": {"value": reaction, "unit": force_unit},
                "minor_shear": {"value": force(minor_shear), "unit": force_unit},
                "axial_force": {"value": force(axial_force), "unit": force_unit},
            }
        )
    else:
        payload.update(
            {
                "reaction_shear": {"value": reaction, "unit": force_unit},
                "user_force_hvn": {
                    "x": "0",
                    "y": reaction,
                    "z": "0",
                    "unit": force_unit,
                },
            }
        )
    return payload


def build_beam_concrete_paired_angle_request(
    *,
    unit_system: str = "US_CUSTOMARY",
    contract_version: str = "3.5A-RC1",
    profile_family: str = "WIDE_FLANGE_I",
    major_shear: str = "-4",
    minor_shear: str = "0",
    axial_force: str = "0",
) -> BeamConcretePairedAngleRequest:
    return map_beam_concrete_paired_angle_request(
        BeamConcretePairedAngleRequestDTO.model_validate(
            build_beam_concrete_paired_angle_payload(
                unit_system=unit_system,
                contract_version=contract_version,
                profile_family=profile_family,
                major_shear=major_shear,
                minor_shear=minor_shear,
                axial_force=axial_force,
            )
        )
    )


__all__ = (
    "build_beam_concrete_paired_angle_payload",
    "build_beam_concrete_paired_angle_request",
)
