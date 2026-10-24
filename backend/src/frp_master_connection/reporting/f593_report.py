"""Presentation of sealed F593 source and native bolt evidence; no calculation."""

from __future__ import annotations

from typing import Any

from frp_master_connection.reporting.multirow_substitutions import multirow_native_substitution
from frp_master_connection.reporting.reader_data import readable_value, short_number
from frp_master_connection.reporting.units import DisplayUnits


def f593_source_rows(source: object, system: DisplayUnits) -> list[tuple[str, str]]:
    if not isinstance(source, dict) or source.get("kind") != "CATALOG":
        return []
    rows = [
        ("F593 catalog status", str(source["fnt_state"])),
        (
            "F593 specification / alloy",
            f"{source['specification']} / Group {source['alloy_group']} / "
            f"{', '.join(source['alloys'])}",
        ),
        (
            "Resolved condition / marking",
            f"{source['condition']} / {source['marking'] or 'unresolved'}",
        ),
        ("Nominal fastener diameter", readable_value(source["nominal_diameter"], system)),
        ("Design Fnt (minimum tensile)", readable_value(source["fnt"], system)),
        (
            "F593 source / catalog revision",
            f"{source['source_classification']} / {source['catalog_record_id']} / "
            f"{source['catalog_revision']}",
        ),
        ("Source provenance", str(source["owner_approval"])),
        ("Catalog SHA-256", str(source["catalog_digest"])),
        ("Procurement information", str(source["specification_note"])),
    ]
    row = source["selected_row"]
    if row is not None:
        rows.extend(
            [
                (
                    "Applicable ASTM nominal diameter range",
                    f"{row['diameter_min']}-{row['diameter_max']} in inclusive",
                ),
                (
                    "Specified tensile range / design rule",
                    f"{row['tensile_min']}-{row['tensile_max']} ksi; "
                    f"use lower bound {row['design_fnt']} ksi",
                ),
            ]
        )
    else:
        rows.append(("Unresolved catalog row", str(source["source_requirement"])))
    for plane in source["shear_planes"]:
        rows.append(
            (
                f"Physical shear plane {plane['plane_id']}",
                f"{plane['thread_status']}; Fnv = {plane['fnv_rule']}; "
                f"consumed Fnv: {readable_value(plane['fnv'], system)}",
            )
        )
    return rows


def f593_bolt_rows(
    source: object, result: dict[str, Any], visual: dict[str, Any], system: DisplayUnits
) -> list[tuple[str, str]]:
    if not isinstance(source, dict) or source.get("kind") != "CATALOG":
        return []
    integration = result.get("automatic_group_mode_integration", {})
    candidates = [
        r for s in integration.get("scenario_results", []) for r in s.get("supported_results", [])
    ]
    single = integration.get("direct_single_row_result")
    if isinstance(single, dict):
        candidates.extend(single.get("checks", []))
    rows = []
    for check in candidates:
        if check.get("limit_state") != "BOLT_SHEAR" or check.get("availability") != "CALCULATED":
            continue
        rows.append(
            (
                str(check["result_id"]),
                multirow_native_substitution(check, visual, system)
                + f"; Demand = {readable_value(check['demand'], system)}; "
                f"UR = {short_number(check['utilization'], ratio=True)}; "
                f"{check['numerical_comparison']}",
            )
        )
    return rows
