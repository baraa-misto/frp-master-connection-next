"""Stage 3.1 strict adapters into unchanged Stage 2 material contracts."""

import ast
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

import frp_master_connection.calculation.material_compatibility as compatibility_module
from frp_master_connection.calculation.material_compatibility import (
    ExistingMetallicBoltEligibilityStatus,
    LegacyMaterialPairResolution,
    resolve_existing_metallic_bolt_eligibility,
    resolve_legacy_material_pair,
)
from frp_master_connection.calculation.multirow import ConnectedMaterialPair
from frp_master_connection.calculation.properties import (
    FastenerSnapshot,
    create_locked_f593_fastener_snapshot,
    create_synthetic_fastener_snapshot,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.material_architecture import (
    EngineeringCoverageClass,
    EngineeringGeometryReference,
    EngineeringPropertySource,
    EngineeringPropertySourceKind,
    FastenerMaterialAssignment,
    FastenerMaterialFamily,
    FastenerSystem,
    MaterialBehaviorFamily,
    PropertySourceConfirmation,
    ResistanceAuthority,
    ResistanceAuthorityKind,
)


def _source(source_id: str = "controlled-source") -> EngineeringPropertySource:
    return EngineeringPropertySource(
        EngineeringPropertySourceKind.CONTROLLED_PROJECT_DATA,
        source_id,
        "revision-1",
        PropertySourceConfirmation.CONFIRMED,
        (),
        False,
    )


def _authority(
    *,
    kind: ResistanceAuthorityKind = (ResistanceAuthorityKind.EXISTING_METALLIC_BOLT_AUTHORITY),
    approved: bool = True,
) -> ResistanceAuthority:
    if kind is ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY:
        return ResistanceAuthority("authority-none", kind, False)
    source = replace(
        _source("authority-source"),
        confirmation=PropertySourceConfirmation.ENGINEER_APPROVED,
        approval_authority_id="engineer-1",
    )
    return ResistanceAuthority("authority-1", kind, approved, source)


def _system(
    family: FastenerMaterialFamily = FastenerMaterialFamily.STAINLESS_STEEL_316,
    *,
    snapshot_id: str | None = "metallic-properties",
    authoritative_geometry: bool = True,
    authority: ResistanceAuthority | None = None,
) -> FastenerSystem:
    behavior = (
        MaterialBehaviorFamily.CUSTOM_FASTENER_MATERIAL
        if family is FastenerMaterialFamily.CUSTOM_FRP
        else MaterialBehaviorFamily.ISOTROPIC_METAL
    )
    source = _source()
    return FastenerSystem(
        "fastener-system-1",
        FastenerMaterialAssignment(
            "fastener-material-1",
            family,
            behavior,
            source,
            EngineeringCoverageClass.PRESCRIPTIVE,
        ),
        EngineeringGeometryReference(
            "fastener-geometry-1",
            source,
            authoritative_geometry,
        ),
        (
            authority
            if authority is not None
            else _authority(kind=ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY)
            if family is FastenerMaterialFamily.CUSTOM_FRP
            else _authority()
        ),
        snapshot_id,
        source,
    )


def _snapshot(
    snapshot_id: str = "metallic-properties",
    *,
    fnt: str = "100",
) -> FastenerSnapshot:
    return create_synthetic_fastener_snapshot(
        id=snapshot_id,
        fnt=PhysicalQuantity.of(fnt, Unit.KSI),
    )


@pytest.mark.parametrize(
    ("participant_a", "participant_b", "expected_pair", "expected_metal"),
    [
        (
            "PULTRUDED_FRP",
            "PULTRUDED_FRP",
            ConnectedMaterialPair.FRP_FRP,
            None,
        ),
        (
            "PULTRUDED_FRP",
            "STAINLESS_STEEL_316",
            ConnectedMaterialPair.FRP_STEEL,
            "STAINLESS_STEEL_316",
        ),
        (
            "STAINLESS_STEEL_316",
            "PULTRUDED_FRP",
            ConnectedMaterialPair.FRP_STEEL,
            "STAINLESS_STEEL_316",
        ),
        (
            "PULTRUDED_FRP",
            "CARBON_STEEL",
            ConnectedMaterialPair.FRP_STEEL,
            "CARBON_STEEL",
        ),
        (
            "CARBON_STEEL",
            "PULTRUDED_FRP",
            ConnectedMaterialPair.FRP_STEEL,
            "CARBON_STEEL",
        ),
    ],
)
def test_legacy_pair_resolver_preserves_order_exact_subtype_and_legacy_identity(
    participant_a: str,
    participant_b: str,
    expected_pair: ConnectedMaterialPair,
    expected_metal: str | None,
) -> None:
    from frp_master_connection.domain.material_architecture import ConnectorMaterialFamily

    first = ConnectorMaterialFamily(participant_a)
    second = ConnectorMaterialFamily(participant_b)
    result = resolve_legacy_material_pair(first, second)

    assert result.participant_a is first
    assert result.participant_b is second
    assert result.legacy_pair is expected_pair
    assert result.metal_subtype is (
        None if expected_metal is None else ConnectorMaterialFamily(expected_metal)
    )
    with pytest.raises(FrozenInstanceError):
        result.legacy_pair = ConnectedMaterialPair.FRP_FRP  # type: ignore[misc]


def test_legacy_pair_resolver_rejects_every_metal_metal_pair_and_arbitrary_strings() -> None:
    from frp_master_connection.domain.material_architecture import ConnectorMaterialFamily

    metals = (
        ConnectorMaterialFamily.STAINLESS_STEEL_316,
        ConnectorMaterialFamily.CARBON_STEEL,
    )
    for first in metals:
        for second in metals:
            with pytest.raises(ValueError, match="No legacy material-pair mapping"):
                resolve_legacy_material_pair(first, second)

    with pytest.raises(TypeError, match="exact ConnectorMaterialFamily"):
        resolve_legacy_material_pair("PULTRUDED_FRP", metals[0])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="exact ConnectorMaterialFamily"):
        resolve_legacy_material_pair(metals[0], "PULTRUDED_FRP")  # type: ignore[arg-type]


def test_legacy_pair_resolution_contract_rejects_inconsistent_or_malformed_state() -> None:
    from frp_master_connection.domain.material_architecture import ConnectorMaterialFamily

    frp = ConnectorMaterialFamily.PULTRUDED_FRP
    stainless = ConnectorMaterialFamily.STAINLESS_STEEL_316
    with pytest.raises(TypeError, match="participants"):
        LegacyMaterialPairResolution("FRP", frp, ConnectedMaterialPair.FRP_FRP, None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="ConnectedMaterialPair"):
        LegacyMaterialPairResolution(frp, frp, "FRP_FRP", None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="exact supported connector metal"):
        LegacyMaterialPairResolution(frp, frp, ConnectedMaterialPair.FRP_FRP, frp)
    with pytest.raises(ValueError, match="inconsistent"):
        LegacyMaterialPairResolution(
            frp,
            stainless,
            ConnectedMaterialPair.FRP_FRP,
            stainless,
        )
    with pytest.raises(ValueError, match="No legacy material-pair mapping"):
        LegacyMaterialPairResolution(
            stainless,
            ConnectorMaterialFamily.CARBON_STEEL,
            ConnectedMaterialPair.FRP_STEEL,
            stainless,
        )


@pytest.mark.parametrize(
    "family",
    [
        FastenerMaterialFamily.STAINLESS_STEEL_316,
        FastenerMaterialFamily.CARBON_STEEL,
    ],
)
def test_supported_metal_requires_every_gate_and_exposes_exact_snapshot_only_when_eligible(
    family: FastenerMaterialFamily,
) -> None:
    system = _system(family)
    snapshot = _snapshot()

    result = resolve_existing_metallic_bolt_eligibility(system, snapshot)

    assert result.status is ExistingMetallicBoltEligibilityStatus.ELIGIBLE
    assert result.is_eligible
    assert result.material_family is family
    assert result.expected_snapshot_id == snapshot.id
    assert result.provided_snapshot_id == snapshot.id
    assert result.eligible_snapshot is snapshot
    with pytest.raises(FrozenInstanceError):
        result.status = ExistingMetallicBoltEligibilityStatus.BLOCKED_EXPLICIT_FNT_REQUIRED  # type: ignore[misc]


def test_custom_frp_is_blocked_even_when_supplied_an_explicit_synthetic_fnt() -> None:
    snapshot = _snapshot()
    result = resolve_existing_metallic_bolt_eligibility(
        _system(FastenerMaterialFamily.CUSTOM_FRP),
        snapshot,
    )

    assert result.status is ExistingMetallicBoltEligibilityStatus.BLOCKED_CUSTOM_FRP_MATERIAL
    assert not result.is_eligible
    assert result.provided_snapshot_id == snapshot.id
    assert result.eligible_snapshot is None


@pytest.mark.parametrize(
    ("system", "snapshot", "expected"),
    [
        (
            _system(authoritative_geometry=False),
            _snapshot(),
            ExistingMetallicBoltEligibilityStatus.BLOCKED_AUTHORITATIVE_GEOMETRY_REQUIRED,
        ),
        (
            _system(
                authority=_authority(kind=ResistanceAuthorityKind.NO_AUTOMATIC_RESISTANCE_AUTHORITY)
            ),
            _snapshot(),
            ExistingMetallicBoltEligibilityStatus.BLOCKED_EXISTING_METALLIC_AUTHORITY_REQUIRED,
        ),
        (
            _system(authority=_authority(approved=False)),
            _snapshot(),
            ExistingMetallicBoltEligibilityStatus.BLOCKED_EXISTING_METALLIC_AUTHORITY_REQUIRED,
        ),
        (
            _system(snapshot_id=None),
            _snapshot(),
            ExistingMetallicBoltEligibilityStatus.BLOCKED_PROPERTY_SNAPSHOT_ID_REQUIRED,
        ),
        (
            _system(),
            None,
            ExistingMetallicBoltEligibilityStatus.BLOCKED_PROPERTY_SNAPSHOT_REQUIRED,
        ),
        (
            _system(),
            _snapshot("other-properties"),
            ExistingMetallicBoltEligibilityStatus.BLOCKED_PROPERTY_SNAPSHOT_ID_MISMATCH,
        ),
        (
            _system(snapshot_id="ASTM_F593_17_GROUP_2_316_316L"),
            create_locked_f593_fastener_snapshot(),
            ExistingMetallicBoltEligibilityStatus.BLOCKED_EXPLICIT_FNT_REQUIRED,
        ),
        (
            _system(),
            _snapshot(fnt="0"),
            ExistingMetallicBoltEligibilityStatus.BLOCKED_POSITIVE_FNT_REQUIRED,
        ),
    ],
)
def test_metallic_eligibility_is_fail_closed_with_deterministic_reason(
    system: FastenerSystem,
    snapshot: FastenerSnapshot | None,
    expected: ExistingMetallicBoltEligibilityStatus,
) -> None:
    result = resolve_existing_metallic_bolt_eligibility(system, snapshot)

    assert result.status is expected
    assert not result.is_eligible
    assert result.eligible_snapshot is None


def test_metallic_eligibility_rejects_wrong_root_types_and_unknown_family_state() -> None:
    with pytest.raises(TypeError, match="FastenerSystem"):
        resolve_existing_metallic_bolt_eligibility(object(), None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="FastenerSnapshot or None"):
        resolve_existing_metallic_bolt_eligibility(_system(), object())  # type: ignore[arg-type]

    system = _system()
    object.__setattr__(system.material, "family", "UNKNOWN")
    with pytest.raises(ValueError, match="Unsupported fastener material family"):
        resolve_existing_metallic_bolt_eligibility(system, _snapshot())


def test_eligibility_result_contract_rejects_inconsistent_state() -> None:
    snapshot = _snapshot()
    eligible = resolve_existing_metallic_bolt_eligibility(_system(), snapshot)

    with pytest.raises(ValueError, match="fastener_system_id"):
        replace(eligible, fastener_system_id=" ")
    with pytest.raises(TypeError, match="FastenerMaterialFamily"):
        replace(eligible, material_family="METAL")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="EligibilityStatus"):
        replace(eligible, status="ELIGIBLE")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="expected_snapshot_id"):
        replace(eligible, expected_snapshot_id="")
    with pytest.raises(ValueError, match="provided_snapshot_id"):
        replace(eligible, provided_snapshot_id="")
    with pytest.raises(ValueError, match="supported metallic family"):
        replace(eligible, material_family=FastenerMaterialFamily.CUSTOM_FRP)
    with pytest.raises(TypeError, match="requires a FastenerSnapshot"):
        replace(eligible, eligible_snapshot=None)
    with pytest.raises(ValueError, match="identities must match"):
        replace(eligible, provided_snapshot_id="other")
    with pytest.raises(ValueError, match="positive explicit Fnt"):
        replace(eligible, eligible_snapshot=_snapshot(fnt="0"))

    blocked = resolve_existing_metallic_bolt_eligibility(_system(), None)
    with pytest.raises(ValueError, match="must not expose"):
        replace(blocked, eligible_snapshot=snapshot)


def test_compatibility_module_has_no_equation_or_numerical_executor_dependency() -> None:
    assert compatibility_module.__file__ is not None
    source_path = Path(compatibility_module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert imported_modules.isdisjoint(
        {
            "frp_master_connection.calculation.equations",
            "frp_master_connection.calculation.evaluation",
            "frp_master_connection.calculation.multirow_engine",
            "frp_master_connection.application",
            "frp_master_connection.api",
        }
    )
    assert set(compatibility_module.__all__) == {
        "ExistingMetallicBoltEligibilityResult",
        "ExistingMetallicBoltEligibilityStatus",
        "LegacyMaterialPairResolution",
        "resolve_existing_metallic_bolt_eligibility",
        "resolve_legacy_material_pair",
    }
