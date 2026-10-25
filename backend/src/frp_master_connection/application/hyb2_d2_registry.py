"""D2 physical adoption packet. No production approvals are installed."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from hashlib import sha256

from .hyb1_contract import Alignment, PairedActions
from .hyb1_mapping import ADDITIONAL_3D, HEEL, MISSING_IDS, REQUIRED_IDS

REVISION = "HYB2-D2-A/1"
TEST_DOMAIN = "HYB2_D2_SYNTHETIC_TEST_DOMAIN"
FIELD_EXPERIENCE = (
    "Field experience as reported by the owner; no independent laboratory records or "
    "qualified testing envelope supplied."
)


class Disposition(StrEnum):
    PENDING = "RHM_PENDING_REVIEW"
    NATIVE = "ASCE_CURRENT_EVALUATED"
    APPROVED = "RHM_APPROVED_FOR_NAMED_SCOPE"
    NA = "N_A_PHYSICAL_APPROVED"
    UNAVAILABLE = "UNAVAILABLE_OR_INAPPLICABLE"


class ReviewState(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONDITIONAL = "CONDITIONAL"
    REVOKED = "REVOKED"


@dataclass(frozen=True, slots=True)
class MechanismProposal:
    native_id: str
    alignment: Alignment
    method_revision: str
    candidate: str
    cells: str
    physical_fragment: str
    transfer_and_holes: str
    exact_required_artifact: str
    responsible_role: str = "Qualified structural method reviewer / engineer of record"
    disposition: Disposition = Disposition.PENDING


def proposals(alignment: Alignment) -> tuple[MechanismProposal, ...]:
    """Keep real native IDs, all five missing checks and independent 3D mechanisms."""
    if not isinstance(alignment, Alignment):
        raise TypeError("Governed alignment required.")
    details = {
        MISSING_IDS[0]: (
            "Calcs!D93:D121",
            "Angle first-row bearing/bypass cut, integral heel and true member end",
            "Signed combined-mode proof bounding first-row net failure, or validated "
            "companion law; "
            "include actual e1 rather than importing the older 3-in W8 control.",
        ),
        MISSING_IDS[1]: (
            "Calcs!D211:D239",
            "Receiving I first-row flange stress field with continuous web",
            "Signed first-row stress-transfer derivation with actual remote N/V/M and net cut.",
        ),
        MISSING_IDS[2]: (
            "Calcs!D183:D205",
            "Receiving I inter-hole surfaces, distinct from local end tear-out",
            "Validated inter-row surface and demand correspondence for this continuous I member.",
        ),
        MISSING_IDS[3]: (
            "Calcs!D211:D239; R3 column P/V cuts",
            "Occupied-outstand independent 3D released fragment; P/V are not LEFT/RIGHT",
            "Dimensioned detachable 3D control volume with member ends, holes and remote actions.",
        ),
        MISSING_IDS[4]: (
            "R3 column V rays to x=-3 in; no companion web release law",
            "Web-attached/opposite I side; 5.841789706-in flange ray crosses integral web",
            "Validated junction fracture/control volume, or signed physical "
            "non-applicability proof.",
        ),
        HEEL: (
            "No independent heel-side free-edge law",
            "Integral Angle heel; not a second free toe",
            "Signed physical N/A or heel release analysis for the actual solid, not display crop.",
        ),
        ADDITIONAL_3D[0]: (
            "No source 3D heel companion law",
            "Angle root through-thickness stress / delamination",
            "Actual root/fillet product geometry and validated orthotropic heel/contact analysis.",
        ),
        ADDITIONAL_3D[1]: (
            "No source flange/web junction companion law",
            "I flange force transfer into web and remote member",
            "Validated 3D flange/web transfer model with root details and remote N/V/M.",
        ),
        ADDITIONAL_3D[2]: (
            "Input!R49 corrected equilibrium only; not a contact law",
            "Single-lap separation, bolt-axis force, prying and installation standoff",
            "Admissible six-action contact/bolt-stiffness model and validation for "
            "actual hardware.",
        ),
    }
    output = []
    for key in REQUIRED_IDS:
        cells, fragment, artifact = details.get(
            key,
            (
                "Calcs!D34/D46/D75/D121/D146/D159; native signed ASCE trace separately",
                "Actual named native bolt/member surface; one physical bolt group",
                "Source-matched material, demand and physical-path review; no "
                "cross-alignment reuse.",
            ),
        )
        output.append(
            MechanismProposal(
                key,
                alignment,
                REVISION,
                "NO_ADOPTION_EVIDENCE_YET"
                if key == MISSING_IDS[4]
                else "REVIEWABLE_MAPPING_CANDIDATE",
                cells,
                fragment,
                "ASD source positive P/sketch V at midpoint only; local edge-to-centerline; "
                "global actual same-surface hole unions, oblique Fs*Av+Ft*At arithmetic only. "
                "Polyester 100F Ts=.85 / listed strengths SF4; D31/D221 repeated Ts retained. "
                "316SS 12.75ksi is reference, not MAT1/F593 authority.",
                artifact
                if alignment is Alignment.SUPPORT
                else "Separately fitted BRACE geometry and signed applicability proof. " + artifact,
            )
        )
    return tuple(output)


@dataclass(frozen=True, slots=True)
class ReviewedEvidence:
    """Offline decision record. Its digest must also be pinned by trusted authority.

    A signature digest records provenance; it is not a cryptographic verification of
    an engineer's signature. D2 deliberately installs no production pin or uploader.
    """

    method_id: str
    revision: str
    mechanisms: tuple[str, ...]
    comparison_ids: tuple[str, ...]
    geometry: str
    material: str
    actions_digest: str
    context_sha256: str
    alignment: Alignment
    physical_path: str
    scope_and_exclusions: str
    engineer: str
    reviewed: date
    expires: date
    evidence_sha256: str
    signature_document_sha256: str
    state: ReviewState
    physical_na: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.state, ReviewState):
            raise TypeError("Typed engineering review disposition required.")

    @property
    def digest(self) -> str:
        return sha256(repr(self).encode()).hexdigest()

    def matches(self, actions: PairedActions, today: date, context_sha256: str) -> bool:
        return (
            self.state == "APPROVED"
            and self.reviewed <= today <= self.expires
            and bool(self.method_id and self.revision and self.physical_path)
            and bool(self.scope_and_exclusions and self.engineer)
            and all(
                len(x) == 64 and set(x) <= set("0123456789abcdef")
                for x in (self.evidence_sha256, self.signature_document_sha256)
            )
            and bool(self.mechanisms)
            and len(set(self.mechanisms)) == len(self.mechanisms)
            and set(self.mechanisms) <= set(REQUIRED_IDS)
            and (self.physical_na or bool(self.comparison_ids))
            and self.geometry == actions.identity.geometry
            and self.material == actions.identity.material
            and self.actions_digest == actions.digest
            and self.context_sha256 == context_sha256
            and self.alignment is actions.identity.alignment
        )


@dataclass(frozen=True, slots=True)
class EvidenceAuthority:
    """No production adoption pins. Synthetic evidence is restricted to TEST ONLY."""

    test_records: tuple[ReviewedEvidence, ...] = ()
    test_pins: tuple[str, ...] = ()

    def accepted(
        self, actions: PairedActions, today: date, context_sha256: str
    ) -> tuple[ReviewedEvidence, ...]:
        if actions.identity.connection != TEST_DOMAIN:
            return ()
        return tuple(
            record
            for record in self.test_records
            if record.digest in self.test_pins and record.matches(actions, today, context_sha256)
        )
