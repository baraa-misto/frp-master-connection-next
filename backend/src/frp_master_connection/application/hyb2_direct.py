"""Inactive source-matched Direct integration, paired actions and physical mapping leads."""

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import cast

from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.rhm_direct_corrections import (
    ENDPOINT_QUESTION,
    DirectCorrections,
    execute_direct_corrections,
)
from frp_master_connection.calculation.rhm_direct_reference import (
    SOURCE_SHA256,
    DirectCandidateStream,
    DirectGeometry,
    DirectSourceCase,
    execute_direct_source,
)
from frp_master_connection.calculation.rhm_reference import ReferenceStream

from .hyb1_contract import ActionBasis, Alignment, PairedActions
from .hyb1_mapping import (
    ADDITIONAL_3D,
    EXISTING_IDS,
    HEEL,
    MISSING_IDS,
    REQUIRED_IDS,
    MethodMapping,
)
from .hyb1_review import ComparisonRow, SupplementalSet


def direct_geometry_digest(geometry: DirectGeometry) -> str:
    return sha256(json.dumps(asdict(geometry), sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class DirectIntegration:
    supplemental: SupplementalSet
    records: tuple[tuple[str, DirectSourceCase], ...]
    withheld: tuple[tuple[str, str], ...]
    corrections: tuple[tuple[str, DirectCorrections], ...] = ()


def calculate_direct_references(
    actions: PairedActions,
    geometry: DirectGeometry,
    *,
    stream: ReferenceStream | DirectCandidateStream = ReferenceStream.CORRECTED_REFERENCE,
) -> DirectIntegration:
    """Available LRFD checks remain independent when an ASD case cannot be mapped.

    No caller adoption flag exists. The signed Cartesian u/v action ledger is retained
    intact. Only complete, positive source directions at the group centroid map here.
    """
    if (
        actions.identity.geometry != direct_geometry_digest(geometry)
        or actions.identity.material != SOURCE_SHA256
    ):
        raise ValueError(
            "Direct source reference needs its exact geometry and source property identity."
        )
    rows: list[ComparisonRow] = []
    records: list[tuple[str, DirectSourceCase]] = []
    withheld: list[tuple[str, str]] = []
    corrections: list[tuple[str, DirectCorrections]] = []
    if not actions.asd:
        withheld.append(
            ("ASD", "Missing independently supplied ASD action set; no LRFD conversion.")
        )
    for case in actions.asd:
        reason = ""
        if actions.identity.alignment is not Alignment.SUPPORT:
            reason = (
                "Rotated brace pair requires fresh paths and applicability; no "
                "inherited source result."
            )
        elif not case.complete or case.frame != "DIRECT_UV_CENTROID":
            reason = "Complete source u/v axes and all six actions at the group centroid required."
        elif any(v.magnitude != 0 for v in case.reference):
            reason = (
                "Reference is not the source group centroid; retain eccentric "
                "transport before applicability."
            )
        elif any(v is not None and v.magnitude != 0 for v in case.components[2:]):
            reason = (
                "Unsupported moment/out-of-plane demand retained; source scalar "
                "envelope is not adopted."
            )
        elif any(v is not None and v.magnitude < 0 for v in case.components[:2]):
            reason = (
                "Signed reversal needs its own opposite-edge/contact path; negative "
                "utilization is not PASS."
            )
        if reason:
            withheld.append((case.case_id, reason))
            continue
        axial, shear = case.components[:2]
        # Completeness checked above; no missing component becomes zero.
        if isinstance(stream, DirectCandidateStream):
            correction = execute_direct_corrections(
                geometry=geometry,
                axial=cast(PhysicalQuantity, axial),
                shear=cast(PhysicalQuantity, shear),
            )
            corrections.append((case.case_id, correction))
            book = correction.corrected
        else:
            book = execute_direct_source(
                geometry=geometry,
                axial=cast(PhysicalQuantity, axial),
                shear=cast(PhysicalQuantity, shear),
                stream=stream,
            )
        records.append((case.case_id, book))
        rows.extend(
            ComparisonRow(
                comparison.method_id,
                case.case_id,
                case.digest,
                ActionBasis.ASD,
                comparison.utilization,
                comparison.numerical_outcome,
                comparison.equation,
                "; ".join(str(r.to(Unit.KIP).magnitude) + " kip" for r in comparison.capacities),
                "REFERENCE_ONLY",
                "HYB2_DIRECT_REFERENCE",
                "; ".join(comparison.assumptions),
                reference_stream=book.stream.value,
                reference_source_sha256=SOURCE_SHA256,
            )
            for comparison in book.comparisons
        )
    return DirectIntegration(
        SupplementalSet(
            actions.identity,
            actions.digest,
            tuple(rows),
            limitations=tuple(
                case_id + ": Direct supplemental checks NOT EVALUATED. " + reason
                for case_id, reason in withheld
            )
            + tuple(
                case_id
                + ": R2 COS and net-hole sensitivities remain reference-only. "
                + ENDPOINT_QUESTION
                for case_id, _ in corrections
            ),
        ),
        tuple(records),
        tuple(withheld),
        tuple(corrections),
    )


def direct_source_mappings(alignment: Alignment) -> tuple[MethodMapping, ...]:
    """Every actual mechanism, both alignments. Direct column equations supersede old leads.

    Seven arithmetic comparisons are not eight independent mechanisms. Joint coverage
    awaits physical substantiation; no manufactured one-to-one ASCE row equivalence.
    """
    if not isinstance(alignment, Alignment):
        raise TypeError("Actual governed alignment required.")
    output: list[MethodMapping] = []
    for key in REQUIRED_IDS:
        if key in MISSING_IDS[:2]:
            cells, path, question = (
                "Calcs!D93:D121;D211:D239",
                (
                    "Global tension contribution exists; standalone first-row or "
                    "substantiated combined coverage unestablished"
                ),
                "Q1",
            )
        elif key in (*ADDITIONAL_3D, HEEL):
            cells, path, question = (
                "No explicit 3D/contact/junction or heel companion law",
                "Integral heel/web continuity and out-of-plane release remain independent",
                "Q4",
            )
        elif key.startswith("BOLT_SHEAR"):
            cells, path, question = (
                "Calcs!D46;D159",
                "One physical two-bolt group; duplicate source summary is not extra resistance",
                "Q4",
            )
        elif key.startswith("PIN_BEARING"):
            cells, path, question = (
                "Calcs!D34;D146",
                "Brace directional and column CW bearing; source positive/uniform group reference",
                "Q5",
            )
        elif key == EXISTING_IDS[6]:
            cells, path, question = (
                "Calcs!D53:D75",
                (
                    "Brace local end tear-out is now direct; inter-hole release still "
                    "needs geometric correspondence"
                ),
                "Q3",
            )
        elif key == MISSING_IDS[2]:
            cells, path, question = (
                "Calcs!D183:D205",
                (
                    "Direct receiving-column local P/V release exists; not yet proof of "
                    "inter-row or web-junction failure"
                ),
                "Q2",
            )
        else:
            cells, path, question = (
                "Calcs!D93:D121;D211:D239",
                (
                    "Direct brace/column global P/V fragments exist; P and V are not "
                    "LEFT and RIGHT geometric releases"
                ),
                "Q2",
            )
        output.append(
            MethodMapping(
                alignment,
                key,
                key,
                "REFERENCE_ONLY",
                cells,
                path,
                (
                    "Two actual holes/member; thickness .5/.375; center-derived "
                    "gross/effective convention and Xb datum pending Q3; no reinforcement"
                ),
                "Explicit ASD positive directions at centroid, no moments. "
                + (
                    "Source vertical pair; 2/cos(phi)"
                    if alignment is Alignment.SUPPORT
                    else (
                        "Separately rotated pair, freshly calculated paths; source "
                        "boundaries do not fit saved rotation"
                    )
                ),
                (
                    "Source polyester listed/SF4, source Ts retained including D31/D221 "
                    "extra reduction; no ASCE factor substitution"
                ),
                (
                    "Simultaneous P/V additive source interactions, same physical bolts "
                    "counted once; no standalone net check inferred"
                ),
                (
                    "Physical adoption pending; original native ASCE authority and "
                    "qualification remain unchanged"
                ),
                question,
            )
        )
    return tuple(output)
