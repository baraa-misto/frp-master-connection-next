"""Inactive R3 paired-action integration. No public route or native status changes."""

from dataclasses import dataclass
from typing import cast

from frp_master_connection.calculation.quantities import PhysicalQuantity
from frp_master_connection.calculation.rhm_direct_r3 import (
    METHOD_LIMIT,
    STREAM,
    R3Geometry,
    R3Record,
    execute_r3,
    geometry_digest,
)
from frp_master_connection.calculation.rhm_direct_reference import SOURCE_SHA256

from .hyb1_contract import ActionBasis, Alignment, PairedActions
from .hyb1_review import ComparisonRow, SupplementalSet


@dataclass(frozen=True, slots=True)
class R3Integration:
    supplemental: SupplementalSet
    records: tuple[tuple[str, R3Record], ...]
    withheld: tuple[tuple[str, str], ...]


def calculate_r3_references(actions: PairedActions, geometry: R3Geometry) -> R3Integration:
    """Complete independently entered ASD actions only; never infer ASD from LRFD.

    The action frame explicitly uses P and sketch V=-n at the physical midpoint.
    Unsupported/reversed/transported actions retain their records and limitations.
    """
    if (
        actions.identity.geometry != geometry_digest(geometry)
        or actions.identity.material != SOURCE_SHA256
    ):
        raise ValueError(
            "R3 requires the exact corrected geometry and original source property identity."
        )
    records = []
    rows: list[ComparisonRow] = []
    withheld = []
    if not actions.asd:
        withheld.append(("ASD", "Independently supplied ASD action set missing; no conversion."))
    for case in actions.asd:
        reason = ""
        if actions.identity.alignment is not Alignment.SUPPORT:
            reason = "Brace rotation is freshly derived geometry only; no inherited resistance."
        elif not case.complete or case.frame != "DIRECT_P_SKETCH_V_CENTROID":
            reason = "Complete six actions in P/sketch V=-n centroid frame required."
        elif any(x.magnitude != 0 for x in case.reference):
            reason = "Transport all moments to the declared midpoint; nonzero reference withheld."
        elif any(x is not None and x.magnitude != 0 for x in case.components[2:]):
            reason = (
                "Finite moment/out-of-plane action unsupported; isolated "
                "equilibrium is not adoption."
            )
        elif any(x is not None and x.magnitude < 0 for x in case.components[:2]):
            reason = (
                "Load reversal needs explicit opposite paths; negative demand is not zero or PASS."
            )
        if reason:
            withheld.append((case.case_id, reason))
            continue
        p, v = case.components[:2]
        record = execute_r3(
            geometry=geometry, axial=cast(PhysicalQuantity, p), shear=cast(PhysicalQuantity, v)
        )
        records.append((case.case_id, record))
        rows.extend(
            ComparisonRow(
                row.method_id,
                case.case_id,
                case.digest,
                ActionBasis.ASD,
                row.utilization,
                row.numerical_outcome,
                row.equation,
                str(row.capacities_kip) + " kip",
                "REFERENCE_ONLY",
                "HYB2_DIRECT_REFERENCE",
                row.applicability,
                reference_stream=STREAM,
                reference_source_sha256=SOURCE_SHA256,
            )
            for row in record.checks
            if row.variant == "R3_SAME_SURFACE_NET_ARITHMETIC"
            and row.method_id.startswith("DIRECT_")
        )
    return R3Integration(
        SupplementalSet(
            actions.identity,
            actions.digest,
            tuple(rows),
            limitations=(
                *(key + ": NOT EVALUATED. " + reason for key, reason in withheld),
                METHOD_LIMIT,
            ),
        ),
        tuple(records),
        tuple(withheld),
    )
