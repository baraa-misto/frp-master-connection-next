"""Strict transport fixtures for the controlled Stage 3.4A node."""

from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Any, cast

_IN_TO_MM = Decimal("25.4")
_KIP_TO_KN = Decimal("4.4482216152605")


def _text(value: Decimal) -> str:
    return format(value, "f").rstrip("0").rstrip(".") or "0"


def build_multi_member_tee_payload(
    *,
    unit_system: str = "US_CUSTOMARY",
    active_slots: tuple[str, ...] = ("UPPER_BRACE", "MIDDLE_BEAM", "LOWER_BRACE"),
) -> dict[str, Any]:
    si = unit_system == "SI"
    length_unit = "mm" if si else "in"
    force_unit = "kN" if si else "kip"
    moment_unit = "kN-mm" if si else "kip-in"

    def length(value: str) -> dict[str, str]:
        source = Decimal(value)
        return {"value": _text(source * _IN_TO_MM) if si else value, "unit": length_unit}

    def force(value: str) -> str:
        source = Decimal(value)
        with localcontext() as context:
            context.prec = 50
            return _text(source * _KIP_TO_KN) if si else value

    def moment(value: str) -> str:
        source = Decimal(value)
        with localcontext() as context:
            context.prec = 50
            return _text(source * _KIP_TO_KN * _IN_TO_MM) if si else value

    def vector(values: tuple[str, str, str], unit: str) -> dict[str, str]:
        convert = length if unit == length_unit else None
        if convert is not None:
            converted = tuple(convert(item)["value"] for item in values)
        elif unit == force_unit:
            converted = tuple(force(item) for item in values)
        else:
            converted = tuple(moment(item) for item in values)
        return {"x": converted[0], "y": converted[1], "z": converted[2], "unit": unit}

    def action(
        force_values: tuple[str, str, str],
        reference: tuple[str, str, str],
        moment_values: tuple[str, str, str] = ("0", "0", "0"),
    ) -> dict[str, object]:
        return {
            "force_hvn": vector(force_values, force_unit),
            "moment_hvn": vector(moment_values, moment_unit),
            "reference_hvn": vector(reference, length_unit),
        }

    group = {
        "row_count": 2,
        "bolts_per_row": 2,
        "pitch": length("2"),
        "gauge": length("2"),
    }
    payload: dict[str, Any] = {
        "orchestration_contract_version": "3.4A-RC1",
        "request_id": "MULTI-MEMBER-TEE-DEFAULT",
        "unit_system": unit_system,
        "source_length_unit": length_unit,
        "connector_dimensions": {
            "connector_length": length("30"),
            "flange_width": length("8"),
            "flange_thickness": length("0.5"),
            "stem_depth": length("6"),
            "stem_thickness": length("0.5"),
        },
        "connector_length_anchor": "CENTER",
        "connector_length_anchor_position": length("0"),
        "support_dimensions": {
            "member_length": length("40"),
            "depth": length("8"),
            "flange_width": length("8"),
            "web_thickness": length("0.5"),
            "flange_thickness": length("0.5"),
        },
        "support_group": group,
        "support_reference_hvn": vector(("0", "0", "0"), length_unit),
        "bolt_diameter": length("0.5"),
        "hole_basis": "US_CUSTOMARY_PRINTED",
    }
    if "UPPER_BRACE" in active_slots:
        payload["upper_brace"] = {
            "leg_y": length("6"),
            "leg_z": length("6"),
            "thickness": length("0.5"),
            "member_length": length("12"),
            "selected_profile_surface": "LEG_Y_OUTER",
            "inclination_degrees": "30",
            "profile_roll_degrees": "0",
            "anchor_h": length("3"),
            "anchor_v": length("10"),
            "bolt_group": group,
            "action": action(("3.4641016151377544", "2", "0"), ("3", "10", "0")),
        }
    if "MIDDLE_BEAM" in active_slots:
        payload["middle_beam"] = {
            "depth": length("10"),
            "flange_width": length("8"),
            "web_thickness": length("0.5"),
            "flange_thickness": length("0.75"),
            "member_length": length("12"),
            "selected_profile_surface": "WEB_POS_FACE",
            "inclination_degrees": "0",
            "profile_roll_degrees": "0",
            "anchor_h": length("3"),
            "anchor_v": length("0"),
            "bolt_group": group,
            "action": action(("6", "0", "0"), ("3", "0", "0")),
        }
    if "LOWER_BRACE" in active_slots:
        payload["lower_brace"] = {
            "leg_y": length("6"),
            "leg_z": length("6"),
            "thickness": length("0.5"),
            "member_length": length("12"),
            "selected_profile_surface": "LEG_Y_OUTER",
            "inclination_degrees": "-30",
            "profile_roll_degrees": "0",
            "anchor_h": length("3"),
            "anchor_v": length("-10"),
            "bolt_group": group,
            "action": action(("3.4641016151377544", "-2", "0"), ("3", "-10", "0")),
        }
    return payload


def build_expanded_multi_member_tee_payload(
    *,
    unit_system: str = "US_CUSTOMARY",
    active_slots: tuple[str, ...] = ("UPPER_BRACE", "MIDDLE_BEAM", "LOWER_BRACE"),
    profile_families: tuple[str, str, str] = ("ANGLE", "WIDE_FLANGE_I", "ANGLE"),
    support_target: str = "W_COLUMN_FLANGE",
) -> dict[str, Any]:
    """Build one strict 3.4B payload while omitting every inactive/stale family field."""

    payload = build_multi_member_tee_payload(
        unit_system=unit_system,
        active_slots=active_slots,
    )
    si = unit_system == "SI"
    unit = "mm" if si else "in"

    def length(value: str) -> dict[str, str]:
        source = Decimal(value)
        return {"value": _text(source * _IN_TO_MM) if si else value, "unit": unit}

    dimensions: dict[str, dict[str, object]] = {
        "FLAT_PLATE": {
            "dimensions": {
                "width": length("6"),
                "thickness": length("0.5"),
                "member_length": length("12"),
            },
            "surface": "FACE_POS",
        },
        "ANGLE": {
            "dimensions": {
                "leg_y": length("6"),
                "leg_z": length("6"),
                "thickness": length("0.5"),
                "member_length": length("12"),
            },
            "surface": "LEG_Y_OUTER",
        },
        "CHANNEL": {
            "dimensions": {
                "depth": length("8"),
                "flange_width": length("4"),
                "web_thickness": length("0.5"),
                "flange_thickness": length("0.5"),
                "member_length": length("12"),
            },
            "surface": "WEB_OUTER",
        },
        "WIDE_FLANGE_I": {
            "dimensions": {
                "depth": length("10"),
                "flange_width": length("8"),
                "web_thickness": length("0.5"),
                "flange_thickness": length("0.75"),
                "member_length": length("12"),
            },
            "surface": "WEB_POS_FACE",
        },
        "RECTANGULAR_HOLLOW_SECTION": {
            "dimensions": {
                "depth": length("6"),
                "width": length("4"),
                "wall_thickness": length("0.5"),
                "member_length": length("12"),
            },
            "surface": "Y_POS_FACE",
        },
        "SOLID_RECTANGULAR_SECTION": {
            "dimensions": {
                "depth": length("6"),
                "width": length("4"),
                "member_length": length("12"),
            },
            "surface": "Y_POS_FACE",
        },
    }
    slot_fields = (
        ("upper_brace", "UPPER_BRACE"),
        ("middle_beam", "MIDDLE_BEAM"),
        ("lower_brace", "LOWER_BRACE"),
    )
    for (key, slot_id), family in zip(slot_fields, profile_families, strict=True):
        slot = payload.get(key)
        if not isinstance(slot, dict):
            continue
        semantic = {
            name: slot[name]
            for name in (
                "inclination_degrees",
                "profile_roll_degrees",
                "anchor_h",
                "anchor_v",
                "bolt_group",
                "action",
            )
        }
        source = dimensions[family]
        semantic.update(
            {
                "slot_id": slot_id,
                "trim_enabled": False,
                "trim_clearance": None,
                "profile": {
                    "profile_id": f"multi-member-tee-{slot_id.lower()}-profile",
                    "role": "BRACE",
                    "profile_family": family,
                    "size_basis": "CUSTOM_DIMENSIONS",
                    "dimensions": source["dimensions"],
                    "profile_orientation": "ROTATION_0",
                    "selected_profile_surface": source["surface"],
                    "material_kind": "PULTRUDED_FRP",
                },
            }
        )
        payload[key] = semantic
    support_sources: dict[str, dict[str, object]] = {
        "W_COLUMN_FLANGE": {
            "family": "WIDE_FLANGE_I",
            "role": "COLUMN",
            "surface": "FLANGE_POS_OUTER",
            "values": {
                "member_length": length("16"),
                "depth": length("8"),
                "flange_width": length("8"),
                "web_thickness": length("0.5"),
                "flange_thickness": length("0.75"),
            },
        },
        "W_BEAM_FLANGE": {
            "family": "WIDE_FLANGE_I",
            "role": "BEAM",
            "surface": "FLANGE_POS_OUTER",
            "values": {
                "member_length": length("16"),
                "depth": length("8"),
                "flange_width": length("8"),
                "web_thickness": length("0.5"),
                "flange_thickness": length("0.75"),
            },
        },
        "W_COLUMN_WEB": {
            "family": "WIDE_FLANGE_I",
            "role": "COLUMN",
            "surface": "WEB_POS_FACE",
            "values": {
                "member_length": length("16"),
                "depth": length("8"),
                "flange_width": length("8"),
                "web_thickness": length("0.5"),
                "flange_thickness": length("0.75"),
            },
        },
        "CHANNEL_COLUMN_WEB": {
            "family": "CHANNEL",
            "role": "COLUMN",
            "surface": "WEB_OUTER",
            "values": {
                "member_length": length("16"),
                "depth": length("8"),
                "flange_width": length("4"),
                "web_thickness": length("0.5"),
                "flange_thickness": length("0.5"),
            },
        },
        "ANGLE_COLUMN_LEG": {
            "family": "ANGLE",
            "role": "COLUMN",
            "surface": "LEG_Y_OUTER",
            "values": {
                "member_length": length("16"),
                "leg_y": length("8"),
                "leg_z": length("8"),
                "thickness": length("0.5"),
            },
        },
        "RECTANGULAR_HOLLOW_COLUMN_WALL": {
            "family": "RECTANGULAR_HOLLOW_SECTION",
            "role": "COLUMN",
            "surface": "Z_POS_FACE",
            "values": {
                "member_length": length("16"),
                "width": length("10"),
                "depth": length("6"),
                "wall_thickness": length("0.5"),
            },
        },
        "SOLID_RECTANGULAR_COLUMN_FACE": {
            "family": "SOLID_RECTANGULAR_SECTION",
            "role": "COLUMN",
            "surface": "Z_POS_FACE",
            "values": {"member_length": length("16"), "width": length("10"), "depth": length("6")},
        },
    }
    support = support_sources[support_target]
    support_values = cast(dict[str, object], support["values"])
    payload["orchestration_contract_version"] = "3.4B-RC1"
    payload["request_id"] = "MULTI-MEMBER-TEE-EXPANDED"
    payload.pop("support_dimensions")
    payload["support_target_id"] = support_target
    payload["support_profile"] = {
        "profile_id": "multi-member-tee-support-profile",
        "role": support["role"],
        "profile_family": support["family"],
        "profile_orientation": "ROTATION_0",
        "selected_profile_surface": support["surface"],
        **support_values,
    }
    return payload


__all__ = ("build_expanded_multi_member_tee_payload", "build_multi_member_tee_payload")
