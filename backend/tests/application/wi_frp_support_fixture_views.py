"""Reproducible native wire projections; not independent engineering authority."""

from typing import Any

from frp_master_connection.api.wi_frp_support_moment_mapping import serialize_wi_frp_support_moment
from frp_master_connection.application.wi_frp_support_moment_design import (
    FRPSupportMomentDesign,
    evaluate_wi_frp_support_moment,
)
from frp_master_connection.domain.wi_frp_support_moment import (
    SupportMode,
    default_frp_support_moment_request,
)


def frontend_fixture(mode: SupportMode) -> dict[str, Any]:
    """Omit heavy native subtraces only; retain every exposed number verbatim."""
    wire = serialize_wi_frp_support_moment(
        evaluate_wi_frp_support_moment(default_frp_support_moment_request(mode))
    ).model_dump(mode="json")
    r = wire["result"]
    r["beam_local_checks"] = [
        {k: c[k] for k in ("connector_id", "layer_id", "scope_status")}
        for c in r["beam_local_checks"]
    ]
    for c in r["preview"]["connectors"]:
        for key in ("flange_demand", "web_demand", "support_in_plane_demand"):
            if c[key] is not None:
                c[key] = {
                    k: v for k, v in c[key].items() if k in ("fingerprint", "result_fingerprint")
                }
    for c in r["support_local_checks"]:
        c["native_trace"] = None
    for c in r["beam_bearings"]:
        c["trace"] = {
            "factor_trace": {"design_resistance": c["trace"]["factor_trace"]["design_resistance"]}
        }
    r["native_failed_checks"] = [
        {
            k: c[k]
            for k in (
                "result_id",
                "limit_state",
                "numerical_comparison",
                "utilization",
                "demand",
                "design_resistance",
            )
        }
        for c in r["native_failed_checks"]
    ]
    g = r["preview"]["geometry"]
    g["support"] = {k: g["support"][k] for k in ("centroid", "centroid_authority")}
    g["angles"] = [
        {
            k: a[k]
            for k in ("connector_id", "heel", "member_reference_global", "support_reference_global")
        }
        for a in g["angles"]
    ]
    for b in g["support_bolts"]:
        b["crossing"].pop("core_path")
    return wire


def native_catalogue_entry(result: FRPSupportMomentDesign) -> dict[str, Any]:
    wire = serialize_wi_frp_support_moment(result).model_dump(mode="json")
    p = wire["result"]["preview"]
    return {
        "geometry_status": wire["geometry_status"],
        "engineering_fingerprint": wire["engineering_fingerprint"],
        "result_fingerprint": wire["result_fingerprint"],
        "status": result.status,
        "native_governing": list(result.native_governing_check_ids),
        "scope_statuses": [list(s) for s in result.scope_statuses],
        "support_centroid": p["geometry"]["support"]["centroid"],
        "support_contribution": p["support_contribution"],
        "equilibrium": p["equilibrium"],
        "connector_core_fingerprints": [c["core"]["fingerprint"] for c in p["connectors"]],
    }
