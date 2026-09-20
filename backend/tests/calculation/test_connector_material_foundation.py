"""CME-1 F01-F24 and adversarial role/source/provider contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

import pytest

from frp_master_connection.calculation.angle_column_base_response import opposite, transform_wrench
from frp_master_connection.calculation.angle_connector_core import (
    AngleConnectorFrame,
    AngleWrench,
    resolve_angle_connector,
)
from frp_master_connection.calculation.angle_connector_providers import evaluate_angle_provider
from frp_master_connection.calculation.connector_material_plan import (
    ConnectorMaterialPlan,
    MaterialAssignment,
    plan_connector_materials,
)
from frp_master_connection.calculation.connector_material_provider import (
    NativeFRPAdapter,
    ProviderCapability,
    dispatch_connector_provider,
    provider_registry,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.multirow import (
    ConnectedMaterialPair,
    prescribed_row_fractions,
)
from frp_master_connection.calculation.native_connector_providers import (
    NativeAngleInput,
    native_connector_providers,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.connector_materials import (
    CanonicalComponent,
    ComponentRole,
    ConnectorMaterial,
    Fabrication,
    MaterialDescriptor,
    PropertyDomain,
    Readiness,
    ResponseSignature,
    SourceDescriptor,
    exact_ratio,
    revalidate_response,
)
from tests.calculation.test_angle_connector_core_and_frp_provider import context, request

ROOT = Path(__file__).resolve().parents[3]
GOLDEN = (
    ROOT
    / "backend/tests/golden/FRP_MASTER_CONNECTION_CME_1_ACCEPTANCE_AND_REFERENCE_FIXTURES_RC1.json"
)
DATA = json.loads(GOLDEN.read_bytes())
FIXTURES = {r["id"]: r for r in DATA["fixtures"]}
SS = MaterialDescriptor(
    ConnectorMaterial.SS316,
    "316",
    "ASTM_A240_A240M",
    "26",
    Fabrication.FORMED_BENT,
    "UNVERIFIED",
    None,
    "CME2_PENDING",
)
BODY = CanonicalComponent("ANGLE_1", ComponentRole.CONNECTOR_BODY, "ANGLE", ("LEG_A", "LEG_B"))


def plan(
    components: tuple[CanonicalComponent, ...] = (BODY,),
    assignments: tuple[MaterialAssignment, ...] = (),
    *,
    apply_all: MaterialDescriptor | None = None,
    trusted_sources: tuple[SourceDescriptor, ...] = (),
    responses: tuple[tuple[str, ResponseSignature], ...] = (),
) -> ConnectorMaterialPlan:
    return plan_connector_materials(
        "TEST_ONLY",
        "FIXTURE",
        components,
        assignments,
        geometry_identity="native-geometry",
        apply_all=apply_all,
        trusted_sources=trusted_sources,
        responses=responses,
    )


@pytest.mark.parametrize("fixture", ["F01", "F02", "F03", "F06", "F07", "F08", "F09"])
def test_role_fixtures_reject_substitution(fixture: str) -> None:
    row = FIXTURES[fixture]
    role = (
        ComponentRole.FASTENER_OR_HARDWARE
        if row["input"]["role"] == "FASTENER"
        else ComponentRole(row["input"]["role"])
    )
    body = replace(BODY, role=role)
    with pytest.raises(ValueError, match=r"FORBIDDEN|REINFORCEMENT_RESTRICTED"):
        plan((body,), (MaterialAssignment("ANGLE_1", SS),))
    assert body.material.family is ConnectorMaterial.FRP


def test_f04_stainless_target_is_not_capacity_or_whole_connection_pass() -> None:
    value = plan(assignments=(MaterialAssignment("ANGLE_1", SS),))
    target = value.targets[0]
    assert target.provider_status == FIXTURES["F04"]["expected"]["numerical_availability"]
    assert target.capacity is target.utilization is value.design_status is None
    assert target.material_axes == "GEOMETRIC_LOCAL_AXES_NOT_PULTRUSION"
    assert not value.resistance_evaluated
    assert not value.persisted
    assert value.derived_branch_forces is None
    assert value.known_external_actions_preserved


@pytest.mark.parametrize("qualified", [False, True])
def test_f05_real_frp_provider_native_result_and_fingerprint(qualified: bool) -> None:
    from tests.calculation.test_angle_connector_core_and_frp_provider import (
        qualified as qualified_context,
    )

    core = resolve_angle_connector(request())
    native_context = context()
    if qualified:
        native_context = qualified_context(core, native_context)
    expected = evaluate_angle_provider(core, "FRP", native_context)
    actual = dispatch_connector_provider(
        BODY,
        BODY.material,
        "CS7_FRP",
        "ANGLE_CONNECTOR_RESISTANCE_PROVIDER_RC1",
        NativeAngleInput(core, native_context),
        native_connector_providers(),
    )
    assert actual.native_result == expected
    assert cast(Any, actual.native_result).fingerprint == expected.fingerprint
    assert actual.status == "NATIVE_RESULT_UNMODIFIED"
    assert core == resolve_angle_connector(request())


def test_f10_shared_body_and_monolithic_legs_are_atomic() -> None:
    with pytest.raises(ValueError, match="CONFLICTING_SHARED"):
        plan(
            assignments=(
                MaterialAssignment("LEG_A", SS),
                MaterialAssignment("LEG_B", BODY.material),
            )
        )
    same = plan(assignments=(MaterialAssignment("LEG_A", SS), MaterialAssignment("LEG_B", SS)))
    assert len(same.targets) == 1
    assert same.targets[0].physical_id == "ANGLE_1"


def signature(material: MaterialDescriptor = BODY.material) -> ResponseSignature:
    return ResponseSignature(
        ((BODY.physical_id, material),),
        "geometry",
        "attachments",
        "contact",
        "+/-six-components",
        "native-method",
    )


def test_f11_revalidation_preserves_external_wrench_not_stale_branch_forces() -> None:
    value = revalidate_response(signature(), signature(SS))
    assert not value.applicable
    assert not value.derived_response_available
    assert value.branch_force is value.contact_force is value.prying_force is None
    assert value.known_external_action_preserved
    target = plan(
        assignments=(MaterialAssignment("ANGLE_1", SS),), responses=(("FRP_RESPONSE", signature()),)
    )
    assert target.invalidated_response_ids == ("FRP_RESPONSE",)
    assert target.required_future_coverage
    assert revalidate_response(signature(), signature()).applicable


def test_f12_no_source_or_provider_fallback_even_with_test_injection() -> None:
    called: list[object] = []
    provider = NativeFRPAdapter(
        ProviderCapability(
            "TEST_ONLY", ConnectorMaterial.FRP, ("ANGLE",), (Fabrication.PULTRUDED,), "TEST"
        ),
        str,
        lambda v: called.append(v),
    )
    result = dispatch_connector_provider(
        BODY, SS, "TEST_ONLY", "TEST", "input", provider_registry((provider,))
    )
    assert result.status == "PROVIDER_NOT_IMPLEMENTED"
    assert not called
    assert result.capacity is result.utilization is result.native_result is None
    target = plan(
        assignments=(MaterialAssignment("ANGLE_1", replace(SS, source_reference="user_typed_316")),)
    )
    assert target.targets[0].source_status == "SOURCE_UNVERIFIED"


def vector(values: list[Any], unit: Unit) -> ExactQuantityVector3D:
    return ExactQuantityVector3D(*(PhysicalQuantity.of(str(v), unit) for v in values))


def fractions(value: ExactQuantityVector3D, unit: Unit) -> list[Fraction]:
    scale = Fraction(PhysicalQuantity.of(1, unit).canonical_magnitude)
    return [Fraction(q.canonical_magnitude) / scale for q in (value.x, value.y, value.z)]


@pytest.mark.parametrize("fixture", [f"F{i}" for i in range(13, 19)])
def test_f13_f18_exact_native_transport_and_opposite_reaction(fixture: str) -> None:
    row = FIXTURES[fixture]
    data, expected = row["input"], row["expected"]
    matrix = data["Q_columns_are_local_basis_in_global"]
    frame = AngleConnectorFrame(
        *(
            cast(tuple[Decimal, Decimal, Decimal], tuple(Decimal(matrix[i][j]) for i in range(3)))
            for j in range(3)
        )
    )
    native = transform_wrench(
        AngleWrench(
            vector([0, 0, 0], Unit.IN),
            vector(data["force_local_kip"], Unit.KIP),
            vector(data["moment_local_kip_in"], Unit.KIP_IN),
        ),
        frame,
        vector(data["input_reference_global_in"], Unit.IN),
        vector(data["output_reference_global_in"], Unit.IN),
    )
    assert fractions(native.force, Unit.KIP) == list(map(Fraction, expected["force_global_kip"]))
    assert fractions(native.moment, Unit.KIP_IN) == list(
        map(Fraction, expected["moment_global_kip_in"])
    )
    reaction = opposite(native)
    assert reaction.reference == native.reference
    assert fractions(reaction.force, Unit.KIP) == list(
        map(Fraction, expected["opposite_reaction_force_global_kip"])
    )
    assert fractions(reaction.moment, Unit.KIP_IN) == list(
        map(Fraction, expected["opposite_reaction_moment_global_kip_in"])
    )


@pytest.mark.parametrize("fixture", ["F19", "F20"])
def test_f19_f20_test_only_compatibility_counterexample(fixture: str) -> None:
    data, expected = FIXTURES[fixture]["input"], FIXTURES[fixture]["expected"]
    force, k1, k2 = (
        Fraction(data[k]) for k in ("total_force_kip", "spring_1_kip_per_in", "spring_2_kip_per_in")
    )
    displacement = force / (k1 + k2)
    assert displacement == Fraction(expected["common_displacement_in"])
    assert k1 * displacement == Fraction(expected["reaction_1_kip"])
    assert k2 * displacement == Fraction(expected["reaction_2_kip"])
    assert not FIXTURES[fixture]["production_resistance_authority"]


@pytest.mark.parametrize("fixture", ["F21", "F22", "F23", "F24"])
def test_f21_f24_native_material_pair_distributions(fixture: str) -> None:
    data = FIXTURES[fixture]
    values = prescribed_row_fractions(
        ConnectedMaterialPair(data["input"]["pair_identity"]), data["input"]["row_count"]
    )
    assert list(map(Fraction, values)) == list(map(Fraction, data["expected"]["fractions"]))
    assert data["input"]["row_1"] == "farthest_from_unloaded_free_end"


def test_atomic_apply_all_exclusions_unknowns_order_and_fingerprints() -> None:
    member = CanonicalComponent("column", ComponentRole.PRIMARY_MEMBER, "ANGLE")
    second = replace(BODY, physical_id="ANGLE_2", aliases=())
    result = plan((member, BODY, second), apply_all=SS)
    assert len(result.targets) == 2
    assert result.excluded_physical_ids == ("column",)
    assert result.fingerprint == plan((second, BODY, member), apply_all=SS).fingerprint
    assert result.fingerprint != plan((member, BODY, second)).fingerprint
    assert plan((member,)).disposition == "NO_CONNECTOR_BODY"
    with pytest.raises(ValueError, match="Unknown"):
        plan(assignments=(MaterialAssignment("unknown", SS),))
    with pytest.raises(ValueError, match="Ambiguous canonical"):
        plan((BODY, BODY))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("geometry", "different"),
        ("attachment", "different"),
        ("boundary_conditions", "different"),
        ("load_sign_domain", "different"),
        ("method_version", "different"),
    ],
)
def test_each_response_domain_field_invalidates(field: str, value: str) -> None:
    assert not revalidate_response(
        signature(), replace(signature(), **{field: cast(Any, value)})
    ).applicable


def source_record(properties: tuple[PropertyDomain, ...] = ()) -> SourceDescriptor:
    return SourceDescriptor(
        "TEST_ONLY",
        "r1",
        "NOT_PRODUCTION",
        "fixture",
        "TEST_ONLY",
        "a" * 64,
        SS,
        (Readiness.METADATA_IDENTIFIED, Readiness.PROPERTY_RECORD_VERIFIED),
        properties,
    )


def property_record() -> PropertyDomain:
    return PropertyDomain(
        "TEST_ONLY",
        PhysicalQuantity.of(10, Unit.KSI),
        PhysicalQuantity.of(1, Unit.IN),
        PhysicalQuantity.of(2, Unit.IN),
        "ksi",
    )


def test_source_identity_not_qualification_and_native_table_unit_is_retained() -> None:
    prop = property_record()
    assert exact_ratio(prop.value) == Fraction(prop.value.canonical_magnitude)
    assert prop.value.to(Unit.MPA).to(Unit.KSI) == prop.value
    assert prop.original_table_unit == "ksi"
    source_ = source_record((prop,))
    result = plan(
        assignments=(MaterialAssignment("ANGLE_1", replace(SS, source_reference="TEST_ONLY")),),
        trusted_sources=(source_,),
    )
    assert result.targets[0].source_revision == "r1"
    assert result.targets[0].provider_status == "PROVIDER_NOT_IMPLEMENTED"
    assert result.targets[0].source_status == "SOURCE_METADATA_ONLY_NO_NUMERICAL_ACTIVATION"
    with pytest.raises(ValueError, match="Ambiguous trusted"):
        plan(trusted_sources=(source_, source_))
    with pytest.raises(ValueError, match="overlapping"):
        source_record((prop, prop))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("family", "SS316"),
        ("fabrication", "PULTRUDED"),
        ("grade", ""),
        ("edition", ""),
        ("source_reference", ""),
        ("grade", "316"),
    ],
)
def test_material_invalid_contracts(field: str, value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(BODY.material, **{field: cast(Any, value)})


@pytest.mark.parametrize("grade", ["316", "316L", "316/316L_DUAL_CERTIFIED"])
def test_stainless_grades_remain_distinct(grade: str) -> None:
    descriptor = replace(SS, grade=grade)
    assert (
        plan(assignments=(MaterialAssignment("ANGLE_1", descriptor),)).targets[0].material.grade
        == grade
    )


def test_additional_fail_closed_contracts() -> None:
    with pytest.raises(ValueError, match="distinct grade"):
        replace(SS, grade="F593")
    with pytest.raises(ValueError, match="pultrusion"):
        replace(SS, fabrication=Fabrication.PULTRUDED)
    with pytest.raises(TypeError, match="role"):
        replace(BODY, role=cast(Any, "PRIMARY_MEMBER"))
    with pytest.raises(ValueError, match="unique tuple"):
        replace(BODY, aliases=("X", "X"))
    with pytest.raises(ValueError, match="another component role"):
        replace(BODY, role=ComponentRole.PRIMARY_MEMBER, material=SS)
    with pytest.raises(TypeError, match="typed"):
        MaterialAssignment("X", cast(Any, "FRP"))
    with pytest.raises(ValueError, match="unique physical"):
        replace(signature(), materials=signature().materials * 2)
    with pytest.raises(ValueError, match="SHA-256"):
        replace(source_record(), content_sha256="url")
    with pytest.raises(TypeError, match="Readiness"):
        replace(source_record(), readiness=cast(Any, ("METADATA_IDENTIFIED",)))
    with pytest.raises(ValueError, match="metadata"):
        replace(source_record((property_record(),)), readiness=())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("value", True),
        ("original_table_unit", "MPa"),
        ("lower_size", PhysicalQuantity.of(0, Unit.IN)),
        ("upper_size", PhysicalQuantity.of(".5", Unit.IN)),
        ("upper_size", PhysicalQuantity.of(2, Unit.KIP)),
        ("value", PhysicalQuantity.of(0, Unit.KSI)),
    ],
)
def test_property_domain_rejects_invalid_values(field: str, value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(property_record(), **{field: cast(Any, value)})


def test_dispatch_unknown_scope_and_native_input_are_fail_closed() -> None:
    registry = native_connector_providers()
    provider = registry["CS7_FRP"]
    with pytest.raises(ValueError, match="Duplicate"):
        provider_registry((provider, provider))
    with pytest.raises(ValueError, match="protected"):
        dispatch_connector_provider(
            replace(BODY, role=ComponentRole.PRIMARY_MEMBER),
            BODY.material,
            "CS7_FRP",
            provider.capability.method,
            None,
            registry,
        )
    assert (
        dispatch_connector_provider(
            BODY, BODY.material, "unknown", "unknown", None, registry
        ).status
        == "PROVIDER_NOT_IMPLEMENTED"
    )
    for component, material, method in (
        (replace(BODY, body_form="TEE"), BODY.material, provider.capability.method),
        (
            BODY,
            replace(BODY.material, fabrication=Fabrication.WELDED_BUILT_UP),
            provider.capability.method,
        ),
        (BODY, BODY.material, "WRONG_METHOD"),
    ):
        assert (
            dispatch_connector_provider(
                component, material, "CS7_FRP", method, None, registry
            ).status
            == "PROVIDER_NOT_APPLICABLE"
        )
    with pytest.raises(TypeError, match="Wrong native input"):
        provider.evaluate(None)


def test_controlled_package_hashes_counts_and_sentinels() -> None:
    assert (
        hashlib.sha256(GOLDEN.read_bytes()).hexdigest().upper()
        == "247B49CA529AB9F8C509025DBF8DFA3B832F5BE102C1464ED518DC370D2FD89A"
    )
    order = (
        ROOT
        / "docs/governance"
        / "FRP_MASTER_CONNECTION_CME_1_CONNECTOR_MATERIAL_FOUNDATION_CODEX_ORDER_RC1.md"
    )
    assert (
        hashlib.sha256(order.read_bytes()).hexdigest().upper()
        == "B6AB97AE19EA7CE1EFAF733D07D6A83422B9BD1CD2F7138DC8299ADC56EC5E22"
    )
    assert len(DATA["requirements"]) == 80
    assert len(FIXTURES) == 24
    assert DATA["final_sentinel"] == "END_CME_1_ACCEPTANCE_AND_REFERENCE_FIXTURES_RC1"
    assert (
        "END OF CME-1 CONNECTOR MATERIAL FOUNDATION ORDER RC1 - "
        "DO NOT PROCEED IF THIS LINE IS MISSING" in order.read_text(encoding="utf-8")
    )
