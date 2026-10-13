"""Inactive HYB1 adapter; never modifies native F8/F9 or installs design authority."""

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import cast

from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit, decimal_value
from frp_master_connection.calculation.rhm_workbook_case import WorkbookCase, execute_workbook_case

from .hyb1_contract import ActionBasis, PairedActions, PhysicalIdentity
from .hyb1_mapping import ADDITIONAL_3D, EXISTING_IDS, HEEL, MISSING_IDS, REQUIRED_IDS


@dataclass(frozen=True, slots=True)
class ComparisonRow:
    mechanism: str
    case_id: str
    case_digest: str
    basis: ActionBasis
    ratio: Decimal | None
    outcome: str
    equation: str
    resistance_trace: str
    mapping: str
    evidence_scope: str
    na_reason: str = ""
    native_outcome: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.basis, ActionBasis):
            raise TypeError("A check comparison must retain its action basis.")
        if self.ratio is not None:
            ratio = decimal_value(self.ratio)
            if ratio < 0 or self.outcome != ("PASS" if ratio <= 1 else "FAIL"):
                raise ValueError(
                    "Outcome must agree with finite nonnegative method-specific ratio."
                )
            object.__setattr__(self, "ratio", ratio)
        elif self.outcome not in ("NOT_EVALUATED", "NOT_APPLICABLE"):
            raise ValueError("A numerical outcome needs its evaluated ratio.")


@dataclass(frozen=True, slots=True)
class NativeCapture:
    identity: PhysicalIdentity
    paired_digest: str
    immutable_payload: bytes
    payload_sha256: str
    rows: tuple[ComparisonRow, ...]
    status: str
    provenance: str
    qualification_state: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if sha256(self.immutable_payload).hexdigest() != self.payload_sha256:
            raise ValueError("Immutable native payload digest mismatch.")
        if not self.provenance:
            raise ValueError("Native capture needs unchanged source/snapshot provenance.")


@dataclass(frozen=True, slots=True)
class SupplementalSet:
    identity: PhysicalIdentity
    paired_digest: str
    rows: tuple[ComparisonRow, ...]
    workbooks: tuple[WorkbookCase, ...] = ()


def calculate_reference_cases(actions: PairedActions) -> SupplementalSet:
    """Only declared workbook-domain ASD cases; actual Direct has no adopted mapping."""
    if actions.identity.connection != "HYB1_WORKBOOK_REFERENCE":
        raise ValueError("Reference arithmetic cannot discharge actual Direct coverage.")
    rows: list[ComparisonRow] = []
    workbooks: list[WorkbookCase] = []
    for case in actions.asd:
        if case.frame != "WORKBOOK_VP" or not case.complete:
            raise ValueError(
                "Reference mapping needs a complete explicitly oriented workbook case."
            )
        values = case.components
        if any(q is not None and q.magnitude != 0 for q in values[2:]):
            raise ValueError(
                "Workbook direct/uniform mapping excludes transverse third force and moments."
            )
        v, p = values[0], values[1]
        # Complete tuple was validated above; no absent action is substituted by zero.
        workbook = execute_workbook_case(
            shear=cast(PhysicalQuantity, v), axial=cast(PhysicalQuantity, p)
        )
        workbooks.append(workbook)
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
                "WORKBOOK_REFERENCE",
            )
            for comparison in workbook.comparisons
        )
    return SupplementalSet(actions.identity, actions.digest, tuple(rows), tuple(workbooks))


@dataclass(frozen=True, slots=True)
class HybridReview:
    identity: PhysicalIdentity
    paired_digest: str
    native_payload_sha256: str
    native_status: str
    native_provenance: str
    current: bool
    numerical_outcome: str
    case_sets_complete: bool
    analytical_candidate_complete: bool
    uncovered: tuple[str, ...]
    rows: tuple[ComparisonRow, ...]
    governing_lrfd: ComparisonRow | None
    governing_asd: ComparisonRow | None
    comparison_index: Decimal | None
    evidence_scope: str
    basis_adoption: str = "PENDING_OWNER_ENGINEERING_REVIEW"
    qualification: str = "UNCHANGED_SECTION_2_3_2_UNRESOLVED"
    owner_acceptance: str = "PENDING"
    public_activation: bool = False


def assess_hybrid(
    actions: PairedActions,
    native: NativeCapture,
    supplemental: SupplementalSet,
) -> HybridReview:
    """Fixed mandatory inventory; no caller-approved state or selectable requirement set."""
    current = (
        native.identity == actions.identity == supplemental.identity
        and native.paired_digest == actions.digest == supplemental.paired_digest
    )
    rows = native.rows + supplemental.rows
    cases = {
        basis: {c.case_id: c for c in group}
        for basis, group in ((ActionBasis.LRFD, actions.lrfd), (ActionBasis.ASD, actions.asd))
    }
    if any(
        row.case_id not in cases[row.basis]
        or row.case_digest != cases[row.basis][row.case_id].digest
        for row in rows
    ):
        current = False
    if any(row.basis is not ActionBasis.LRFD for row in native.rows) or any(
        row.basis is not ActionBasis.ASD for row in supplemental.rows
    ):
        current = False
    if len({(r.basis, r.case_id, r.mechanism) for r in rows}) != len(rows):
        current = False
    synthetic = actions.identity.connection == "HYB1_SYNTHETIC_TEST_DOMAIN"
    coverage: set[str] = set()
    for mechanism in REQUIRED_IDS:
        required_basis = ActionBasis.LRFD if mechanism in (*EXISTING_IDS, HEEL) else ActionBasis.ASD
        required_cases = (
            actions.manifest.required_lrfd
            if required_basis is ActionBasis.LRFD
            else actions.manifest.required_asd
        )
        matches = [r for r in rows if r.mechanism == mechanism and r.basis is required_basis]
        valid_scope = "SYNTHETIC_TEST_ONLY" if synthetic else "UNCHANGED_NATIVE_ASCE"
        applicable = [
            r
            for r in matches
            if r.evidence_scope == valid_scope
            and (r.ratio is not None or (r.outcome == "NOT_APPLICABLE" and bool(r.na_reason)))
        ]
        # New RHM/3D mappings remain unadopted; native coverage retains its own domain.
        if not synthetic and mechanism in (*MISSING_IDS, *ADDITIONAL_3D):
            applicable = []
        if required_cases and {r.case_id for r in applicable} == set(required_cases):
            coverage.add(mechanism)
    uncovered = tuple(key for key in REQUIRED_IDS if key not in coverage)
    evaluated = [r for r in rows if r.ratio is not None]
    fail = native.status == "RED" or any(r.outcome == "FAIL" for r in evaluated)
    outcome = "FAIL" if fail else "PASS" if evaluated else "NOT_EVALUATED"
    lrfd = max(
        (r for r in evaluated if r.basis is ActionBasis.LRFD),
        key=lambda r: cast(Decimal, r.ratio),
        default=None,
    )
    asd = max(
        (r for r in evaluated if r.basis is ActionBasis.ASD),
        key=lambda r: cast(Decimal, r.ratio),
        default=None,
    )
    return HybridReview(
        actions.identity,
        actions.digest,
        native.payload_sha256,
        native.status,
        native.provenance,
        current,
        outcome,
        actions.complete,
        current and actions.complete and not uncovered,
        uncovered,
        rows,
        lrfd,
        asd,
        max((r.ratio for r in evaluated if r.ratio is not None), default=None),
        "SYNTHETIC_TEST_ONLY" if synthetic else "INACTIVE_CANDIDATE_ONLY",
        qualification="UNCHANGED_NATIVE: " + "; ".join(native.qualification_state)
        if native.qualification_state
        else "UNCHANGED_NATIVE_NOT_REPORTED",
    )
