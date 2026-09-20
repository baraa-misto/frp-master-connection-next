"""Exact Stage 3.5C US/SI transport fixtures."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any

from frp_master_connection.api.column_base_web_angle_mapping import (
    map_column_base_web_angle_request,
)
from frp_master_connection.api.column_base_web_angle_schemas import (
    ColumnBaseWebAngleRequestDTO,
    ColumnBaseWebAngleSignedRequestDTO,
)
from frp_master_connection.domain import ColumnBaseRequest, ColumnBaseSignedRequest


def build_column_base_web_angle_payload(
    *,
    unit_system: str = "US_CUSTOMARY",
    assembly: str = "SYMMETRIC_DOUBLE_BASE_ANGLES",
    single_side: str = "+T_C",
    axial_compression: str = "20",
    web_plane_shear: str = "4",
    web_normal_shear: str = "0",
) -> dict[str, Any]:
    length_factor = Decimal("25.4")
    force_factor = Decimal("4.4482216152605")

    def length(value: str) -> dict[str, str]:
        converted = Decimal(value) * length_factor if unit_system == "SI" else Decimal(value)
        return {"value": str(converted), "unit": "mm" if unit_system == "SI" else "in"}

    def force(value: str) -> dict[str, str]:
        converted = Decimal(value) * force_factor if unit_system == "SI" else Decimal(value)
        return {"value": str(converted), "unit": "kN" if unit_system == "SI" else "kip"}

    return {
        "orchestration_contract_version": "3.5C-RC1",
        "request_id": f"STAGE-3.5C-{assembly}-{unit_system}",
        "unit_system": unit_system,
        "source_length_unit": "mm" if unit_system == "SI" else "in",
        "concrete": {
            "s_dimension": length("36"),
            "t_dimension": length("36"),
            "depth": length("12"),
        },
        "column": {
            "profile_family": "WIDE_FLANGE_I",
            "depth_s": length("10"),
            "flange_width_t": length("8"),
            "web_thickness": length("0.5"),
            "flange_thickness": length("0.5"),
            "display_height": length("24"),
        },
        "assembly": assembly,
        "single_side": single_side,
        "angle": {
            "connected_leg_width": length("6"),
            "support_leg_width": length("6"),
            "thickness": length("0.5"),
            "connector_length": length("6"),
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
            "centroid_offset_t": length("3.25"),
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
        "axial_compression": force(axial_compression),
        "web_plane_shear": force(web_plane_shear),
        "web_normal_shear": force(web_normal_shear),
        "action_reference_s_t_l": {
            "x": length("0")["value"],
            "y": length("0")["value"],
            "z": length("4")["value"],
            "unit": "mm" if unit_system == "SI" else "in",
        },
    }


def build_column_base_web_angle_request(**changes: object) -> ColumnBaseRequest:
    payload = build_column_base_web_angle_payload()
    for name, value in changes.items():
        payload[name] = deepcopy(value)
    return map_column_base_web_angle_request(ColumnBaseWebAngleRequestDTO.model_validate(payload))


def build_column_base_signed_payload(
    *,
    unit_system: str = "US_CUSTOMARY",
    assembly: str = "SYMMETRIC_DOUBLE_BASE_ANGLES",
    single_side: str = "+T_C",
    signed_axial_force: str = "-20",
    web_plane_shear: str = "4",
    web_normal_shear: str = "0",
) -> dict[str, Any]:
    payload = build_column_base_web_angle_payload(
        unit_system=unit_system,
        assembly=assembly,
        single_side=single_side,
        axial_compression=signed_axial_force,
        web_plane_shear=web_plane_shear,
        web_normal_shear=web_normal_shear,
    )
    payload["orchestration_contract_version"] = "3.5C-R2-RC1"
    payload["request_id"] = f"STAGE-3.5C-R2-{assembly}-{unit_system}"
    payload["signed_axial_force"] = payload.pop("axial_compression")
    return payload


def build_column_base_signed_request(**changes: object) -> ColumnBaseSignedRequest:
    payload = build_column_base_signed_payload()
    for name, value in changes.items():
        payload[name] = deepcopy(value)
    return map_column_base_web_angle_request(
        ColumnBaseWebAngleSignedRequestDTO.model_validate(payload)
    )


__all__ = (
    "build_column_base_signed_payload",
    "build_column_base_signed_request",
    "build_column_base_web_angle_payload",
    "build_column_base_web_angle_request",
)
