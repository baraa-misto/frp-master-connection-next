"""Bounded DCTN-3B integration: exact demand is distinct from qualified response."""

from dataclasses import dataclass
from fractions import Fraction

from frp_master_connection.application.double_channel_truss_node import (
    DCTNDesign,
    DCTNPreview,
    design_check_dctn,
    preview_dctn,
)
from frp_master_connection.application.double_channel_truss_node_geometry import build_dctn_geometry
from frp_master_connection.calculation.angle_connector_core import quantity_vector
from frp_master_connection.calculation.dctn3b_demand import DCTN3BDemand, calculate_dctn3b_demand
from frp_master_connection.calculation.dctn3b_trusted_response import (
    EMPTY_TRUSTED_RESPONSES,
    CompleteResponseValidation,
    TrustedCompleteResponse,
    resolve_complete_response,
)
from frp_master_connection.calculation.dctn_fingerprint import dctn_fingerprint
from frp_master_connection.calculation.dctn_sources import EMPTY_SOURCES, DCTNSources
from frp_master_connection.calculation.double_channel_truss_node import (
    DCTNRequiredCheck,
    aggregate_dctn_checks,
)
from frp_master_connection.calculation.double_channel_truss_node_response import channel_section
from frp_master_connection.domain.dctn3b import DCTN3BRequest
from frp_master_connection.domain.dctn_geometry import DCTNGeometry

TRANSVERSE = "DCTN_TRANSVERSE_RESPONSE_NOT_QUALIFIED"


@dataclass(frozen=True, slots=True)
class DCTN3BPreview:
    input: DCTN3BRequest
    geometry: DCTNGeometry
    demand: DCTN3BDemand
    historical_preview: DCTNPreview | None
    trusted_response: CompleteResponseValidation | None
    geometry_status: str
    demand_status: str
    response_status: str
    qualification_status: str
    design_status: str
    blockers: tuple[str, ...]
    fingerprint: str
    connector_body_count: int = 0
    global_chord_design_evaluated: bool = False
    global_boundary: str = "DCTN_GLOBAL_CHORD_DESIGN_OUTSIDE_LOCAL_CONNECTION_SCOPE"


def preview_dctn3b(
    value: DCTN3BRequest,
    trusted: tuple[TrustedCompleteResponse, ...] = EMPTY_TRUSTED_RESPONSES,
) -> DCTN3BPreview:
    legacy = value.legacy_geometry_request()
    historical = None if value.has_transverse else preview_dctn(legacy)
    geometry = build_dctn_geometry(legacy) if historical is None else historical.geometry
    section = channel_section(legacy)
    offset = Fraction(section.channel_centroid_t_absolute.to(value.length_unit).magnitude)
    references = tuple(
        (
            name,
            quantity_vector(
                (Fraction(0), sign * (Fraction(geometry.gap) / 2 + offset), Fraction(0)),
                value.length_unit,
            ),
        )
        for name, sign in (("CHORD_NEG", -1), ("CHORD_POS", 1))
    )
    demand = calculate_dctn3b_demand(value, geometry, references)
    validated = None
    blockers = list(geometry.reasons)
    if historical is not None:
        response_status = historical.response.status
        blockers.extend(historical.response.reasons)
        qualification = "NATIVE_QUALIFICATION_NOT_EVALUATED"
        design_status = "NOT_CHECKED"
    else:
        if geometry.status == "VALID":
            validated = resolve_complete_response(value, geometry, demand, trusted)
        response_status = (
            "QUALIFIED" if validated is not None and validated.status == "QUALIFIED" else TRANSVERSE
        )
        if response_status != "QUALIFIED":
            blockers.append(TRANSVERSE)
        if validated is not None:
            blockers.extend(validated.reasons)
        # Qualified response does not confer local material/resistance qualification.
        blockers.append("DCTN_TRANSVERSE_LOCAL_RESISTANCE_NOT_QUALIFIED")
        qualification = "REQUIRED_RESPONSE_OR_LOCAL_QUALIFICATION_MISSING"
        design_status = "ENGINEERING_REVIEW_REQUIRED"
    unique = tuple(dict.fromkeys(blockers))
    return DCTN3BPreview(
        value,
        geometry,
        demand,
        historical,
        validated,
        geometry.status,
        demand.status,
        response_status,
        qualification,
        design_status,
        unique,
        dctn_fingerprint((value, geometry, demand, historical, validated, unique)),
    )


@dataclass(frozen=True, slots=True)
class DCTN3BDesign:
    preview: DCTN3BPreview
    historical_design: DCTNDesign | None
    checks: tuple[DCTNRequiredCheck, ...]
    blockers: tuple[str, ...]
    governing_checks: tuple[str, ...]
    whole_connection_status: str
    fingerprint: str


def design_check_dctn3b(
    value: DCTN3BRequest,
    sources: DCTNSources = EMPTY_SOURCES,
    trusted: tuple[TrustedCompleteResponse, ...] = EMPTY_TRUSTED_RESPONSES,
) -> DCTN3BDesign:
    preview = preview_dctn3b(value, trusted)
    historical = (
        None
        if value.has_transverse
        else design_check_dctn(value.legacy_geometry_request(), sources)
    )
    checks = () if historical is None else historical.checks
    blockers = preview.blockers if historical is None else historical.blockers
    status = (
        aggregate_dctn_checks(checks, blockers)
        if historical is None
        else historical.whole_connection_status
    )
    governing = tuple(c.check_id for c in checks if c.status == "FAIL")
    return DCTN3BDesign(
        preview,
        historical,
        checks,
        blockers,
        governing,
        status,
        dctn_fingerprint((preview.fingerprint, historical, checks, blockers, status)),
    )
