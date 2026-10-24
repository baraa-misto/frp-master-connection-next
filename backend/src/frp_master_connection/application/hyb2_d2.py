"""Inactive D2 integrated assessment. Native F8/F9 and all R3 arithmetic are unchanged."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from hashlib import sha256

from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.rhm_direct_r3 import R3Geometry, R3Record, execute_r3

from .hyb1_contract import ActionBasis, Alignment, PairedActions
from .hyb1_mapping import EXISTING_IDS, HEEL
from .hyb1_review import ComparisonRow, NativeCapture
from .hyb2_d2_registry import (
    FIELD_EXPERIENCE,
    REVISION,
    TEST_DOMAIN,
    Disposition,
    EvidenceAuthority,
    MechanismProposal,
    proposals,
)
from .hyb2_direct_r3 import calculate_r3_references


@dataclass(frozen=True, slots=True)
class SourceConditions:
    resin: str = "SOURCE_POLYESTER"
    temperature_f: Decimal = Decimal(100)
    strength_basis: str = "RHM_LISTED_SF4_TS085_REPEATED_D31_D221"
    service_domain: str = "SAVED_REFERENCE_ONLY_NO_DURATION_MOISTURE_CHEMICAL_APPROVAL"
    hardware: str = "SOURCE_316SS_INCLUDED_THREADS_12_75_KSI_REFERENCE_ONLY"

    @property
    def matched(self) -> bool:
        return self == SourceConditions()


@dataclass(frozen=True, slots=True)
class HardwareEvidence:
    bearing_face: str = "UNVERIFIED"
    washer_od: PhysicalQuantity | None = None
    face_evidence_sha256: str = ""

    def __post_init__(self) -> None:
        if self.bearing_face not in ("UNVERIFIED", "R3_BRACE_END_FREE_EDGE", "DIFFERENT_FACE"):
            raise ValueError("Explicit physical bearing-face disposition required.")
        if self.washer_od is not None and self.washer_od.to(Unit.IN).magnitude <= 0:
            raise ValueError("Positive actual washer diameter required.")
        if self.bearing_face != "UNVERIFIED" and (
            len(self.face_evidence_sha256) != 64
            or not set(self.face_evidence_sha256) <= set("0123456789abcdef")
        ):
            raise ValueError("Confirmed face identity needs its physical evidence digest.")


DEFAULT_CONDITIONS = SourceConditions()
DEFAULT_HARDWARE = HardwareEvidence()
DEFAULT_AUTHORITY = EvidenceAuthority()


@dataclass(frozen=True, slots=True)
class FitReview:
    state: str
    hole_state: str
    washer_state: str
    screening_od_in: Decimal | None
    conditional_overhang_in: Decimal | None
    actual_overhang_in: Decimal | None
    action: str
    unknowns: tuple[str, ...]


def physical_fit(
    geometry: R3Geometry | None,
    alignment: Alignment,
    hardware: HardwareEvidence,
    record: R3Record | None,
) -> FitReview:
    """Hardware screening is separate from hole containment and structural strength."""
    unknowns = (
        "Actual washer/head/nut thickness and envelopes, tool access and standoff",
        "Root/fillet and adjacent solids; true member-end/crop dimensions",
        "Fabricated near-B1 edge vs inherited nominal source anchor",
        "ASCE Table 8-1 physical edge/end designation and 8.2.4 hardware applicability",
    )
    if geometry is None or record is None:
        return FitReview(
            "PHYSICAL_FIT_UNVERIFIED",
            "SEE_NATIVE_SIGNED_MODEL",
            "FACE_UNKNOWN",
            None,
            None,
            None,
            "Retain native geometry authority; installation evidence not supplied.",
            unknowns,
        )
    nominal = record.hole_fit if alignment is Alignment.SUPPORT else record.rotation_fit
    with localcontext() as ctx:
        ctx.prec = 60
        screening = (
            Decimal(1)
            if alignment is Alignment.SUPPORT
            and geometry.diameter.to(Unit.IN).magnitude == Decimal(".5")
            else None
        )
        conditional = (
            None
            if screening is None
            else max(Decimal(0), screening / 2 - geometry.xb.to(Unit.IN).magnitude)
        )
        actual = (
            max(
                Decimal(0),
                hardware.washer_od.to(Unit.IN).magnitude / 2 - geometry.xb.to(Unit.IN).magnitude,
            )
            if hardware.washer_od is not None
            and hardware.bearing_face == "R3_BRACE_END_FREE_EDGE"
            and alignment is Alignment.SUPPORT
            else None
        )
    washer = (
        "CONFIRMED_OVERHANG"
        if actual is not None and actual > 0
        else "NOMINAL_WASHER_EDGE_CLEARANCE_ONLY"
        if actual is not None
        else "FACE_UNKNOWN_CONDITIONAL_SCREEN"
    )
    nofit = not nominal or (actual is not None and actual > 0)
    return FitReview(
        "NOT_FIT" if nofit else "PHYSICAL_FIT_UNVERIFIED",
        "NOMINAL_FIT" if nominal else "NOT_FIT",
        washer,
        screening,
        conditional,
        actual,
        "Correct actual physical interference before installation; no hole relocation assumed."
        if nofit
        else "Confirm bearing face and actual hardware; conditional screen is not measured fit.",
        unknowns,
    )


@dataclass(frozen=True, slots=True)
class CoverageRow:
    native_id: str
    disposition: Disposition
    evidence_id: str
    comparison_ids: tuple[str, ...]
    missing_artifact: str


@dataclass(frozen=True, slots=True)
class D2Assessment:
    revision: str
    identity_digest: str
    paired_digest: str
    native_payload_sha256: str
    native_status: str
    evaluated_outcome: str
    tone: str
    coverage_state: str
    case_sets_complete: bool
    analytical_complete: bool
    fit: FitReview
    coverage: tuple[CoverageRow, ...]
    comparisons: tuple[ComparisonRow, ...]
    governing_lrfd: ComparisonRow | None
    governing_asd: ComparisonRow | None
    r3_records: tuple[tuple[str, R3Record], ...]
    method_packet: tuple[MechanismProposal, ...]
    withheld: tuple[tuple[str, str], ...]
    notes: tuple[str, ...]
    scope: str
    source_domain: str
    qualification: str = "NOT_ESTABLISHED_SECTION_2_3_2"
    public_activation: bool = False
    complete_connection_verification: bool = False


def source_domain(
    geometry: R3Geometry | None, conditions: SourceConditions, alignment: Alignment
) -> str:
    if geometry is None:
        return "NATIVE_GEOMETRY_ONLY_NO_SOURCE_MAPPING"
    if alignment is not Alignment.SUPPORT:
        return "BRACE_GEOMETRY_ONLY_NO_SUPPORT_SOURCE_MAPPING"
    nominal = R3Geometry()
    dimensions = (
        "vertical_bolt_pitch",
        "xb",
        "xc",
        "brace_near_v_edge_distance",
        "brace_leg",
        "column_flange",
        "brace_thickness",
        "column_thickness",
        "diameter",
        "hole",
    )
    matched = (
        conditions.matched
        and geometry.phi == nominal.phi
        and all(
            getattr(geometry, key).to(Unit.IN) == getattr(nominal, key).to(Unit.IN)
            for key in dimensions
        )
    )
    return (
        "SOURCE_MATCHED_NOMINAL_ARITHMETIC_ONLY"
        if matched
        else "PARAMETRIC_ARITHMETIC_OUTSIDE_SOURCE_DOMAIN"
    )


def assess_d2(
    actions: PairedActions,
    native: NativeCapture,
    *,
    geometry: R3Geometry | None = None,
    conditions: SourceConditions = DEFAULT_CONDITIONS,
    hardware: HardwareEvidence = DEFAULT_HARDWARE,
    authority: EvidenceAuthority = DEFAULT_AUTHORITY,
    today: date,
) -> D2Assessment:
    """Trusted orchestration only; HTTP clients cannot supply native rows or approvals."""
    if native.identity != actions.identity or native.paired_digest != actions.digest:
        raise ValueError("Stale or mismatched native/action source.")
    cases = {(c.basis, c.case_id): c for c in (*actions.lrfd, *actions.asd)}
    if any(
        r.basis is not ActionBasis.LRFD
        or (r.basis, r.case_id) not in cases
        or r.case_digest != cases[(r.basis, r.case_id)].digest
        for r in native.rows
    ):
        raise ValueError("Native comparisons do not bind original LRFD cases.")
    rows = native.rows
    records: tuple[tuple[str, R3Record], ...] = ()
    withheld: tuple[tuple[str, str], ...] = ()
    if geometry is not None:
        if not conditions.matched:
            withheld = (
                ("SOURCE_PROPERTIES", "Source product/environment/hardware identity unmatched."),
            )
        else:
            integration = calculate_r3_references(actions, geometry)
            rows += integration.supplemental.rows
            records, withheld = integration.records, integration.withheld
    if len({(r.basis, r.case_id, r.mechanism) for r in rows}) != len(rows):
        raise ValueError("Duplicate physical comparison in the same basis/case.")
    native_evaluated = tuple(
        r
        for r in native.rows
        if r.evidence_scope == "UNCHANGED_NATIVE_ASCE" and r.ratio is not None
    )
    numerical = tuple(r for r in rows if r.ratio is not None)
    fail = native.status == "RED" or any(r.outcome == "FAIL" for r in numerical)
    outcome = "FAIL" if fail else "PASS" if numerical else "NOT_EVALUATED"
    context_digest = sha256(repr((geometry, conditions, hardware)).encode()).hexdigest()
    accepted = authority.accepted(actions, today, context_digest)
    coverage = []
    for proposal in proposals(actions.identity.alignment):
        key = proposal.native_id
        matches = tuple(r for r in native_evaluated if r.mechanism == key)
        native_ok = (
            actions.identity.alignment is Alignment.BRACE
            and key in EXISTING_IDS
            and bool(actions.manifest.required_lrfd)
            and {r.case_id for r in matches} == set(actions.manifest.required_lrfd)
        )
        native_na_rows = tuple(
            r
            for r in native.rows
            if r.mechanism == key
            and r.evidence_scope == "UNCHANGED_NATIVE_ASCE"
            and r.outcome == "NOT_APPLICABLE"
            and bool(r.na_reason)
        )
        native_na = (
            actions.identity.alignment is Alignment.BRACE
            and key == HEEL
            and bool(actions.manifest.required_lrfd)
            and {r.case_id for r in native_na_rows} == set(actions.manifest.required_lrfd)
        )
        disposition = (
            Disposition.NATIVE
            if native_ok
            else Disposition.NA
            if native_na
            else Disposition.PENDING
        )
        evidence = native.provenance if native_ok or native_na else "NONE"
        comparisons: tuple[str, ...] = (key,) if native_ok else ()
        for review in accepted:
            required = set(actions.manifest.required_asd)
            complete_comparisons = all(
                {
                    r.case_id
                    for r in rows
                    if r.basis is ActionBasis.ASD
                    and r.mechanism == comparison
                    and r.ratio is not None
                }
                == required
                for comparison in review.comparison_ids
            )
            if key in review.mechanisms and (
                review.physical_na or (required and complete_comparisons)
            ):
                disposition = Disposition.NA if review.physical_na else Disposition.APPROVED
                evidence, comparisons = review.digest, review.comparison_ids
        covered = disposition in (Disposition.NATIVE, Disposition.APPROVED, Disposition.NA)
        coverage.append(
            CoverageRow(
                key,
                disposition,
                evidence,
                comparisons,
                "" if covered else proposal.exact_required_artifact,
            )
        )
    complete = actions.complete and all(not r.missing_artifact for r in coverage)
    coverage_state = (
        "COMPLETE"
        if complete
        else ("PARTIAL" if any(not r.missing_artifact for r in coverage) else "NOT_ESTABLISHED")
    )
    fit_record = records[0][1] if records else execute_r3(geometry=geometry) if geometry else None
    fit = physical_fit(geometry, actions.identity.alignment, hardware, fit_record)
    return D2Assessment(
        REVISION,
        sha256(repr(actions.identity).encode()).hexdigest(),
        actions.digest,
        native.payload_sha256,
        native.status,
        outcome,
        "red" if fail else "green" if numerical else "neutral",
        coverage_state,
        actions.complete,
        complete,
        fit,
        tuple(coverage),
        rows,
        max(
            (r for r in numerical if r.basis is ActionBasis.LRFD),
            key=lambda r: r.ratio or Decimal(0),
            default=None,
        ),
        max(
            (r for r in numerical if r.basis is ActionBasis.ASD),
            key=lambda r: r.ratio or Decimal(0),
            default=None,
        ),
        records,
        proposals(actions.identity.alignment),
        withheld,
        (
            FIELD_EXPERIENCE,
            "No production engineering adoption pins installed; blank approval slots "
            "grant nothing.",
            "R3 source listed/SF4, Ts=.85 with D31/D221 repeated factors; no MAT1 or "
            "F593 substitution.",
            "Oblique Fs*Av+Ft*At remains arithmetic; global tensile term is not "
            "standalone first-row.",
            "Source entered M=0 does not establish zero transported contact/prying moments.",
            "Storm relief excluded. Complete independent ASD and LRFD combinations required.",
            "C13-05/06/07/08 and Section 2.3.2 remain unresolved; native F8/F9 unchanged.",
        ),
        "SYNTHETIC_TEST_ONLY_NOT_ENGINEERING_EVIDENCE"
        if actions.identity.connection == TEST_DOMAIN
        else "HYPOTHETICAL_FIT_TEST_ONLY_NOT_AS_BUILT_EVIDENCE"
        if actions.identity.connection == "HYB2_D2_HYPOTHETICAL_HARDWARE_TEST_ONLY"
        else "INACTIVE_ENGINEERING_REVIEW_ONLY",
        source_domain(geometry, conditions, actions.identity.alignment),
    )
