"""Exact Stage 3.7A US/SI transport fixtures."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from frp_master_connection.api.column_base_web_angle_mapping import (
    map_column_base_web_angle_request,
)
from frp_master_connection.api.column_base_web_angle_schemas import ColumnBaseProfileRequestDTO
from frp_master_connection.domain import ColumnBaseProfileRequest


def build_column_base_profile_payload(
    *,
    unit_system: str = "US_CUSTOMARY",
    profile_family: str = "RECTANGULAR_HOLLOW_SECTION",
    assembly: str = "DOUBLE_BASE_ANGLES",
    selected_surface: str | None = None,
    signed_axial_force: str = "-20",
    connection_plane_shear: str = "4",
    connection_normal_shear: str = "0",
) -> dict[str, Any]:
    length_factor = Decimal("25.4")
    force_factor = Decimal("4.4482216152605")

    def length(value: str) -> dict[str, str]:
        converted = Decimal(value) * length_factor if unit_system == "SI" else Decimal(value)
        return {"value": str(converted), "unit": "mm" if unit_system == "SI" else "in"}

    def force(value: str) -> dict[str, str]:
        converted = Decimal(value) * force_factor if unit_system == "SI" else Decimal(value)
        return {"value": str(converted), "unit": "kN" if unit_system == "SI" else "kip"}

    profile_data: dict[str, tuple[dict[str, object], str, str]] = {
        "WIDE_FLANGE_I": (
            {
                "member_length": length("24"),
                "depth": length("10"),
                "flange_width": length("8"),
                "web_thickness": length("0.5"),
                "flange_thickness": length("0.5"),
            },
            "WEB_POS_FACE",
            "3.25",
        ),
        "RECTANGULAR_HOLLOW_SECTION": (
            {
                "member_length": length("24"),
                "depth": length("10"),
                "width": length("8"),
                "wall_thickness": length("0.5"),
            },
            "Y_POS_FACE",
            "7",
        ),
        "SOLID_RECTANGULAR_SECTION": (
            {
                "member_length": length("24"),
                "depth": length("10"),
                "width": length("8"),
            },
            "Y_POS_FACE",
            "7",
        ),
        "ANGLE": (
            {
                "member_length": length("24"),
                "leg_y": length("6"),
                "leg_z": length("6"),
                "thickness": length("0.5"),
            },
            "LEG_Y_OUTER",
            "3",
        ),
    }
    dimensions, default_surface, anchor_offset = profile_data[profile_family]
    return {
        "orchestration_contract_version": "3.7A-RC1",
        "request_id": f"STAGE-3.7A-{profile_family}-{assembly}-{unit_system}",
        "unit_system": unit_system,
        "source_length_unit": "mm" if unit_system == "SI" else "in",
        "concrete": {
            "s_dimension": length("36"),
            "t_dimension": length("36"),
            "depth": length("12"),
        },
        "column_profile": {
            "profile_id": "column-base-profile",
            "role": "COLUMN",
            "size_basis": "CUSTOM_DIMENSIONS",
            "profile_family": profile_family,
            "dimensions": dimensions,
            "profile_orientation": "ROTATION_0",
            "material_kind": "PULTRUDED_FRP",
            "selected_profile_surface": selected_surface or default_surface,
        },
        "assembly": assembly,
        "single_side": "+T_C",
        "angle": {
            "connected_leg_width": length("6"),
            "support_leg_width": length("6"),
            "thickness": length("0.5"),
            "connector_length": length("5" if profile_family == "ANGLE" else "6"),
        },
        "web_group": {
            "row_count": 2,
            "bolts_per_row": 2,
            "pitch": length("3"),
            "gauge": length("2"),
            "centroid_height_l": length("3"),
        },
        "anchor_pattern": {
            "row_count": 2,
            "anchors_per_row": 1,
            "pitch": length("3"),
            "gauge": length("0"),
            "centroid_offset_t": length(anchor_offset),
        },
        "web_bolt_diameter": length("0.5"),
        "web_hole_diameter": length("0.563"),
        "external_anchor": {
            "nominal_diameter": length("0.5"),
            "hole_diameter": length("0.563"),
            "specified_embedment": length("4"),
            "washer_outside_diameter": length("1.0625"),
            "washer_thickness": length("0.109"),
            "system_classification": "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR",
        },
        "signed_axial_force": force(signed_axial_force),
        "connection_plane_shear": force(connection_plane_shear),
        "connection_normal_shear": force(connection_normal_shear),
        "angle_double_topology": "SAME_SELECTED_LEG_OPPOSITE_FACES",
    }


def build_column_base_profile_request(**changes: object) -> ColumnBaseProfileRequest:
    payload = build_column_base_profile_payload(**cast(Any, changes))
    return map_column_base_web_angle_request(ColumnBaseProfileRequestDTO.model_validate(payload))


__all__ = ("build_column_base_profile_payload", "build_column_base_profile_request")
