"""Hand-defined paired test actions; no adopted combinations or qualifications."""

from decimal import Decimal
from hashlib import sha256

from frp_master_connection.application.hyb1_contract import (
    ActionBasis,
    ActionCase,
    Alignment,
    CaseManifest,
    PairedActions,
    PhysicalIdentity,
)
from frp_master_connection.application.hyb1_mapping import EXISTING_IDS, HEEL, REQUIRED_IDS
from frp_master_connection.application.hyb1_review import (
    ComparisonRow,
    NativeCapture,
    SupplementalSet,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit


def q(value: str = "0", unit: Unit = Unit.KIP) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def case(
    basis: ActionBasis = ActionBasis.LRFD, key: str = "L1", v: str = ".4", p: str = "0"
) -> ActionCase:
    return ActionCase(
        basis,
        key,
        "TEST_HAND_DEFINED:" + key,
        "TEST_SAME_SCENARIO",
        "WORKBOOK_VP",
        (q(unit=Unit.IN), q(unit=Unit.IN), q(unit=Unit.IN)),
        (q(v), q(p), q(), q(unit=Unit.KIP_IN), q(unit=Unit.KIP_IN), q(unit=Unit.KIP_IN)),
    )


def paired(connection: str = "HYB1_SYNTHETIC_TEST_DOMAIN") -> PairedActions:
    identity = PhysicalIdentity(
        "TEST_ACCOUNT", connection, "GEOM1", "MAT1", "ACTION1", Alignment.BRACE
    )
    return PairedActions(
        identity,
        (case(), case(key="L2", v=".8")),
        (case(ActionBasis.ASD, "A1", ".6"), case(ActionBasis.ASD, "A2", ".2")),
        CaseManifest(("L1", "L2"), ("A1", "A2"), True, True, "TEST_HAND_DEFINED_ONLY"),
    )


def complete_fixture(actions: PairedActions) -> tuple[NativeCapture, SupplementalSet]:
    native: list[ComparisonRow] = []
    extra: list[ComparisonRow] = []
    for mechanism in REQUIRED_IDS:
        lrfd = mechanism in (*EXISTING_IDS, HEEL)
        for action in actions.lrfd if lrfd else actions.asd:
            ratio = action.components[0]
            assert ratio is not None
            row = ComparisonRow(
                mechanism,
                action.case_id,
                action.digest,
                action.basis,
                ratio.to(Unit.KIP).magnitude,
                "PASS",
                "TEST D/(1 kip)",
                "TEST ONLY: constant 1 kip, not a real mechanism resistance",
                "TEST_DOMAIN_ONLY",
                "SYNTHETIC_TEST_ONLY",
            )
            (native if lrfd else extra).append(row)
    payload = b'{"synthetic":true,"authority_installed":false}'
    return (
        NativeCapture(
            actions.identity,
            actions.digest,
            payload,
            sha256(payload).hexdigest(),
            tuple(native),
            "TEST_ONLY",
            "TEST_ONLY_NOT_QUALIFICATION",
        ),
        SupplementalSet(actions.identity, actions.digest, tuple(extra)),
    )


def row(ratio: str = ".5", basis: ActionBasis = ActionBasis.ASD) -> ComparisonRow:
    action = case(basis, "A1" if basis is ActionBasis.ASD else "L1")
    return ComparisonRow(
        "REFERENCE",
        action.case_id,
        action.digest,
        basis,
        Decimal(ratio),
        "PASS" if Decimal(ratio) <= 1 else "FAIL",
        "D/R",
        "1 kip",
        "REFERENCE_ONLY",
        "WORKBOOK_REFERENCE",
    )
