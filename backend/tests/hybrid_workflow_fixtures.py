"""Declared input specimens only; no client results, approval or source-engine copies."""

from typing import Any


def q(value: str, unit: str = "in") -> dict[str, str]:
    return {"value": value, "unit": unit}


def live_source() -> dict[str, Any]:
    return {
        "contract": "HYB2-D3-P1-LIVE",
        "workspace_id": "live-source",
        "revision": 0,
        "connection": "RHM_R3",
        "alignment": "SUPPORT",
        "native_request": None,
        "geometry": {
            "vertical_bolt_pitch": q("2"),
            "phi": "30.9",
            "xb": q(".4375"),
            "xc": q("1"),
            "brace_near_v_edge_distance": q("1"),
            "brace_leg": q("4"),
            "column_flange": q("4"),
            "brace_thickness": q(".5"),
            "column_thickness": q(".375"),
            "diameter": q(".5"),
            "hole": q(".563"),
        },
        "include_native_lrfd": False,
        "lrfd_cases": [],
        "asd_cases": [
            {
                "case_id": "source-ASD",
                "frame": "DIRECT_P_SKETCH_V_CENTROID",
                "reference": [q("0"), q("0"), q("0")],
                "components": [
                    q(".09155", "kip"),
                    q(".0134", "kip"),
                    q("0", "kip"),
                    q("0", "kip-in"),
                    q("0", "kip-in"),
                    q("0", "kip-in"),
                ],
            }
        ],
        "source_profile": "RHM_POLYESTER_100F_SF4",
        "bearing_face": "UNKNOWN",
        "washer_od": None,
        "native_edge_distance": None,
    }


def live_native() -> dict[str, Any]:
    from tests.api.test_direct_two_bolt import sab2_body

    body = live_source()
    body.update(
        connection="CURRENT_NATIVE",
        alignment="BRACE",
        geometry=None,
        native_request=sab2_body(alignment="BRACE"),
        include_native_lrfd=True,
        asd_cases=[],
        source_profile="UNMATCHED",
    )
    return body
