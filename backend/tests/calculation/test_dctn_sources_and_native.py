"""Synthetic qualification fixtures exercise bindings, never production registration."""

from dataclasses import replace
from decimal import Decimal

import pytest

from frp_master_connection.application.double_channel_truss_node import (
    DCTNPreview,
    dctn_hardware_binding,
    dctn_material_binding,
    design_check_dctn,
    preview_dctn,
)
from frp_master_connection.calculation.dctn_local_resistance import evaluate_native_dctn_plane
from frp_master_connection.calculation.dctn_sources import (
    EMPTY_SOURCES,
    HARDWARE_COVERAGE,
    DCTNHardwareSource,
    DCTNMaterialSource,
    DCTNQualifiedMechanism,
    DCTNSources,
    hardware_source,
    material_source,
    mechanism_checks,
)
from frp_master_connection.calculation.double_channel_truss_node import (
    DCTNBearingResult,
    DCTNRequiredCheck,
    aggregate_dctn_checks,
    characteristic_bearing,
    local_lap_factor,
)
from frp_master_connection.calculation.equations import (
    CleavageTrace,
    adjust_frp_property,
    bolt_shear_resistance_from_nominal_stress,
    pin_bearing_resistance,
)
from frp_master_connection.calculation.inputs import EndUseFactors
from frp_master_connection.calculation.multirow_engine import resolve_multirow_end_distances
from frp_master_connection.calculation.multirow_equations import InterrowShearOutTrace
from frp_master_connection.calculation.properties import (
    FRPPropertyKind,
    ThreadStatus,
    create_locked_ice_material_snapshot,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.sources import QualificationStatus
from frp_master_connection.domain.double_channel_truss_node import (
    DCTNArrangement,
    DCTNForm,
    DCTNRequest,
    default_dctn_request,
)
from frp_master_connection.domain.material_architecture import (
    EngineeringPropertySource,
    EngineeringPropertySourceKind,
    PropertySourceConfirmation,
)

D = Decimal


def q(value: str, unit: Unit = Unit.KIP) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def synthetic_source() -> EngineeringPropertySource:
    return EngineeringPropertySource(
        EngineeringPropertySourceKind.TEST_QUALIFIED_DATA,
        "DCTN_SYNTHETIC_TEST_ONLY",
        "RC1",
        PropertySourceConfirmation.TEST_QUALIFIED,
        ("NOT_PRODUCTION_AUTHORITY",),
        True,
        "A" * 64,
        "TEST_ONLY_EOR",
        ("TEST_ONLY_QUALIFICATION",),
    )


def sourced_request(form: DCTNForm = DCTNForm.RHS, force: str = "10") -> DCTNRequest:
    value = default_dctn_request()
    return replace(
        value,
        channel=replace(value.channel, material_source_reference="MATERIAL_FIXTURE"),
        fastener=replace(value.fastener, source_reference="HARDWARE_FIXTURE"),
        members=tuple(
            replace(
                m,
                section=replace(m.section, form=form),
                axial_force=q(force),
                material_source_reference="MATERIAL_FIXTURE",
            )
            for m in value.members
        ),
    )


def registry(preview: DCTNPreview) -> DCTNSources:
    source = synthetic_source()
    original = create_locked_ice_material_snapshot()
    material = replace(
        original,
        properties=tuple(
            replace(p, qualification_status=QualificationStatus.QUALIFIED)
            for p in original.properties
        ),
    )
    return DCTNSources(
        tuple(
            DCTNMaterialSource(
                "MATERIAL_FIXTURE",
                owner,
                source,
                dctn_material_binding(preview, owner),
                material,
                EndUseFactors(D(1), D(1), D(1), "TEST_ONLY", ("TEST_ONLY",)),
                D(1),
                True,
            )
            for owner in ("CHORD_NEG", "CHORD_POS", *(m.slot for m in preview.input.members))
        ),
        (
            DCTNHardwareSource(
                "HARDWARE_FIXTURE",
                source,
                dctn_hardware_binding(preview),
                q("20", Unit.KSI),
                tuple(sorted(HARDWARE_COVERAGE)),
            ),
        ),
    )


@pytest.mark.parametrize("arrangement", tuple(DCTNArrangement))
@pytest.mark.parametrize("form", tuple(DCTNForm))
def test_no_production_qualification_is_invented(
    arrangement: DCTNArrangement, form: DCTNForm
) -> None:
    value = default_dctn_request(arrangement)
    value = replace(
        value,
        members=tuple(replace(m, section=replace(m.section, form=form)) for m in value.members),
    )
    result = design_check_dctn(value)
    assert result.preview.geometry.status == "VALID"
    assert result.preview.response.status == "QUALIFIED"
    assert result.whole_connection_status == "ENGINEERING_REVIEW_REQUIRED"
    assert result.checks == ()
    assert "DCTN_HARDWARE_SOURCE_OR_INSTALLATION_NOT_QUALIFIED" in result.blockers
    assert result.global_chord_design_evaluated is False
    assert result.preview.connector_body_count == 0
    assert DCTNSources() == EMPTY_SOURCES


@pytest.mark.parametrize("form", tuple(DCTNForm))
def test_native_numerical_failures_outrank_independent_qualification(form: DCTNForm) -> None:
    value = sourced_request(form, "100")
    preview = preview_dctn(value)
    result = design_check_dctn(value, registry(preview))
    assert result.whole_connection_status == "FAIL"
    assert result.governing_checks
    assert result.blockers
    assert len({c.check_id for c in result.checks}) == len(result.checks)
    hardware = [c for c in result.checks if c.check_id.startswith("HARDWARE_SHEAR:")]
    assert len(hardware) == len(preview.geometry.shafts)
    expected = bolt_shear_resistance_from_nominal_stress(value.fastener.diameter, q("20", Unit.KSI))
    assert all(c.resistance == expected.design_resistance for c in hardware)
    assert all(c.demand == q("25") for c in hardware)
    if form is DCTNForm.SOLID_RECTANGLE:
        full = [c for c in result.checks if c.check_id.startswith("FULL_DEPTH_PIN_BEARING:")]
        assert len(full) == 2
        assert all(c.demand == q("50") for c in full)
    if form is DCTNForm.W_I:
        assert any("DCTN_WI_FLANGE_PATH_NOT_QUALIFIED" in b for b in result.blockers)


def test_rhs_characteristic_factor_does_not_leak_to_channel_or_other_modes() -> None:
    value = sourced_request()
    preview = preview_dctn(value)
    result = design_check_dctn(value, registry(preview))
    bearings = [c for c in result.checks if c.check_id.startswith("PIN_BEARING:")]
    assert len(bearings) == 8
    for check in bearings:
        trace = check.native_trace
        assert isinstance(trace, DCTNBearingResult)
        assert trace.closed_section_factor_applied is (check.owner_id == "V")
        assert trace.characteristic_property_effective == trace.characteristic_property_original * (
            D(".5") if check.owner_id == "V" else D(1)
        )
    cleavage = [c for c in result.checks if c.check_id.startswith("CLEAVAGE:V:")]
    assert cleavage
    for c in cleavage:
        assert isinstance(c.native_trace, CleavageTrace)
        assert c.native_trace.bearing_trace.bearing_property.source_property == q("30", Unit.KSI)


def test_native_first_and_unloaded_end_authority_are_not_confused() -> None:
    value = sourced_request()
    preview = preview_dctn(value)
    plan = next(p for p in preview.local_plans if p.owner_id == "V")
    ends = resolve_multirow_end_distances(plan.geometry, Unit.IN)
    assert ends.unloaded_end_e1 == q("2", Unit.IN)
    assert ends.row_1_to_unloaded_end_distance == q("4", Unit.IN)
    assert plan.first_row.e1 == q("20", Unit.IN)
    assert plan.geometry.boundary.min_y == -1.625
    assert plan.geometry.boundary.max_y == 1.625
    assert plan.first_row.effective_width == q("3.25", Unit.IN)
    source = registry(preview).materials[-1]
    demands = tuple((b.id, q("2.5")) for b in plan.geometry.group.bolts)
    native = evaluate_native_dctn_plane(value, plan, source, demands)
    inter = next(c for c in native.checks if c.check_id.startswith("INTERROW:"))
    assert isinstance(inter.native_trace, InterrowShearOutTrace)
    assert inter.native_trace.unloaded_end_e1 == ends.unloaded_end_e1
    assert inter.native_trace.pitches == ends.physical_pitches


def test_resistance_factor_adapter_uses_native_equation_verbatim() -> None:
    value = sourced_request(DCTNForm.W_I)
    preview = preview_dctn(value)
    source = registry(preview).materials[-1]
    plan = next(p for p in preview.local_plans if p.owner_id == "V")
    demands = tuple((b.id, q("2.5")) for b in plan.geometry.group.bolts)
    actual = evaluate_native_dctn_plane(value, plan, source, demands).checks[0]
    prop = source.material.lookup(FRPPropertyKind.FBR_L)
    assert prop is not None
    adjusted = adjust_frp_property(prop.kind, prop.value, prop.qualification_status, source.factors)
    expected = pin_bearing_resistance(
        plan.thickness,
        value.fastener.diameter,
        adjusted,
        ThreadStatus.EXCLUDED,
        c_delta=D(1),
        c_lap=D(".60"),
        lambda_factor=D(1),
    )
    assert isinstance(actual.native_trace, DCTNBearingResult)
    assert actual.native_trace.native_trace == expected
    assert actual.resistance == expected.factor_trace.design_resistance
    assert characteristic_bearing(q("24", Unit.KSI), DCTNForm.RHS) == q("12", Unit.KSI)
    assert characteristic_bearing(q("24", Unit.KSI), DCTNForm.SOLID_RECTANGLE) == q("24", Unit.KSI)
    assert q("15") * local_lap_factor(DCTNForm.W_I) == q("9")


def test_qualified_records_fail_closed_on_changed_physical_binding_and_coverage() -> None:
    value = sourced_request()
    preview = preview_dctn(value)
    records = registry(preview)
    assert (
        material_source(records, "MATERIAL_FIXTURE", "V", dctn_material_binding(preview, "V"))
        is not None
    )
    assert material_source(records, "MATERIAL_FIXTURE", "V", "tampered") is None
    assert hardware_source(records, "HARDWARE_FIXTURE", dctn_hardware_binding(preview)) is not None
    reduced = replace(records, hardware=(replace(records.hardware[0], installation_coverage=()),))
    assert hardware_source(reduced, "HARDWARE_FIXTURE", dctn_hardware_binding(preview)) is None
    moved = replace(value, members=(replace(value.members[0], axial_force=q("11")),))
    result = design_check_dctn(moved, records)
    assert result.checks == ()
    assert result.whole_connection_status == "ENGINEERING_REVIEW_REQUIRED"
    with pytest.raises(ValueError, match="unique"):
        replace(records, hardware=records.hardware * 2)


def test_qualified_mechanisms_cannot_hide_failed_check_or_omit_required_coverage() -> None:
    check = DCTNRequiredCheck("PATH", "V", "FAIL", q("2"), q("1"), (), "FIXTURE")
    source = DCTNQualifiedMechanism(
        "FIXTURE", "V", synthetic_source(), "binding", ("REQUIRED",), (check,), "TEST_ONLY_METHOD"
    )
    records = DCTNSources(mechanisms=(source,))
    assert mechanism_checks(records, "FIXTURE", "V", "binding", frozenset({"REQUIRED"})) == (check,)
    assert aggregate_dctn_checks((check,), ("UNRESOLVED_OTHER",)) == "FAIL"
    assert mechanism_checks(records, "FIXTURE", "V", "binding", frozenset({"MISSING"})) is None
    assert mechanism_checks(records, "FIXTURE", "V", "different", frozenset({"REQUIRED"})) is None
    assert (
        mechanism_checks(
            replace(records, mechanisms=(replace(source, checks=()),)),
            "FIXTURE",
            "V",
            "binding",
            frozenset({"REQUIRED"}),
        )
        is None
    )


@pytest.mark.parametrize("status", ["PASS", "FAIL"])
def test_fabricated_check_status_is_rejected(status: str) -> None:
    with pytest.raises(ValueError, match="native comparison"):
        DCTNRequiredCheck(
            "X",
            "V",
            status,
            q("2") if status == "PASS" else q("1"),
            q("1") if status == "PASS" else q("2"),
            (),
            "FIXTURE",
        )
