"""Controlled exact Stage 3.5B transport fixtures."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from frp_master_connection.api.direct_side_lap_concrete_mapping import (
    map_direct_side_lap_concrete_request,
)
from frp_master_connection.api.direct_side_lap_concrete_schemas import (
    DirectSideLapConcreteRequestDTO,
)
from frp_master_connection.application import DirectSideLapRequest


def build_direct_side_lap_concrete_payload(
    *,
    unit_system: str = "US_CUSTOMARY",
    profile_family: str = "CHANNEL",
    side_lap_length: str = "12",
    anchor_distance: str = "6",
    axial_force: str = "0",
    major_shear: str = "-4",
    minor_shear: str = "0",
) -> dict[str, Any]:
    length_factor = Decimal("25.4")
    force_factor = Decimal("4.4482216152605")

    def length(value: str) -> dict[str, str]:
        magnitude = Decimal(value) * length_factor if unit_system == "SI" else Decimal(value)
        return {"value": str(magnitude), "unit": "mm" if unit_system == "SI" else "in"}

    def force(value: str) -> dict[str, str]:
        magnitude = Decimal(value) * force_factor if unit_system == "SI" else Decimal(value)
        return {"value": str(magnitude), "unit": "kN" if unit_system == "SI" else "kip"}

    dimensions = (
        {
            "member_length": length("28"),
            "depth": length("8"),
            "flange_width": length("4"),
            "web_thickness": length("0.5"),
            "flange_thickness": length("0.5"),
        }
        if profile_family == "CHANNEL"
        else {
            "member_length": length("28"),
            "leg_y": length("6"),
            "leg_z": length("6"),
            "thickness": length("0.5"),
        }
    )
    return {
        "orchestration_contract_version": "3.5B-RC1",
        "request_id": f"STAGE-3.5B-G1-{unit_system}-{profile_family}",
        "unit_system": unit_system,
        "source_length_unit": "mm" if unit_system == "SI" else "in",
        "wall": {
            "run_length": length("48"),
            "transverse_width": length("48"),
            "thickness": length("8"),
        },
        "side_lap_length": length(side_lap_length),
        "member_projection_beyond_wall": length("16"),
        "connected_profile": {
            "profile_id": "direct-side-lap-connected-member-profile",
            "role": "BRACE",
            "profile_family": profile_family,
            "size_basis": "CUSTOM_DIMENSIONS",
            "dimensions": dimensions,
            "profile_orientation": "ROTATION_0",
            "selected_profile_surface": (
                "WEB_OUTER" if profile_family == "CHANNEL" else "LEG_Y_OUTER"
            ),
        },
        "anchor_pattern": {
            "row_count": 2,
            "anchors_per_row": 1,
            "pitch": length("4"),
            "gauge": length("4"),
            "centroid_distance_behind_free_end": length(anchor_distance),
            "transverse_offset": length("0"),
        },
        "external_anchor": {
            "nominal_diameter": length("0.5"),
            "hole_diameter": length("0.563"),
            "specified_embedment": length("4"),
            "washer_outside_diameter": length("1.0625"),
            "washer_thickness": length("0.109"),
            "system_classification": "EXTERNALLY_DESIGNED_BLIND_EMBEDDED_ANCHOR",
        },
        "axial_force": force(axial_force),
        "major_shear": force(major_shear),
        "minor_shear": force(minor_shear),
    }


def build_direct_side_lap_concrete_request(**kwargs: str) -> DirectSideLapRequest:
    dto = DirectSideLapConcreteRequestDTO.model_validate(
        build_direct_side_lap_concrete_payload(**kwargs)
    )
    return map_direct_side_lap_concrete_request(dto)


__all__ = (
    "build_direct_side_lap_concrete_payload",
    "build_direct_side_lap_concrete_request",
)
