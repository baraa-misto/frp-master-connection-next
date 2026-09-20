from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

import frp_master_connection.calculation.channel_moment_resultants as module
from frp_master_connection.calculation.channel_moment_resultants import (
    CHANNEL_EXPLICIT_SHEAR_CENTER_METHOD_ID,
    CHANNEL_MOMENT_ASCE_SOURCE_SHA256,
    CHANNEL_MOMENT_CALCULATION_CONTRACT_VERSION,
    CHANNEL_MOMENT_DECISION_SHA256,
    CHANNEL_MOMENT_DISCLAIMER_ID,
    CHANNEL_MOMENT_ERRATUM_SOURCE_SHA256,
    CHANNEL_MOMENT_GOLDEN_SHA256,
    CHANNEL_MOMENT_LEDGER_SHA256,
    CHANNEL_MOMENT_METHOD_ID,
    CHANNEL_MOMENT_ORDER_SHA256,
    CHANNEL_MOMENT_SOURCE_PROVENANCE,
    CHANNEL_MOMENT_SPECIFICATION_SHA256,
    CHANNEL_RATIONAL_SHEAR_CENTER_METHOD_ID,
    ChannelMomentActionInput,
    ChannelMomentCalculationInput,
    ChannelMomentFingerprintEnvelope,
    ChannelMomentInputRejected,
    ChannelMomentInputStatus,
    ChannelMomentMethod,
    ChannelMomentRegionForceState,
    ChannelMomentRegionId,
    ChannelMomentRejectionReason,
    ChannelMomentSectionInput,
    ChannelShearCenterInput,
    ChannelShearCenterMethod,
    calculate_channel_moment_component_resultants,
    canonical_channel_moment_input_json,
    channel_moment_input_fingerprint,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.sources import QualificationStatus, SourceClassification
from frp_master_connection.calculation.wi_moment_resultants import BeamQuantityVector
from frp_master_connection.domain.member_profile import (
    ChannelProfileDimensions,
    MemberProfile,
    MemberProfileFamily,
    MemberProfileOrientation,
    MemberProfileSurfaceId,
    profile_section_geometry_adapter,
)
from frp_master_connection.domain.values import ComponentMaterialKind, MemberRole

_BACKEND = Path(__file__).resolve().parents[2]
_ROOT = _BACKEND.parent
_GOLDEN_NAME = (
    "calculation_slice_6_channel_moment_reference_and_component_resultants_"
    "golden_benchmarks_rc1.json"
)
_SPECIFICATION_NAME = (
    "CALCULATION_SLICE_6_CHANNEL_MOMENT_REFERENCE_AND_COMPONENT_RESULTANTS_"
    "ENGINEERING_SPECIFICATION_RC1.md"
)
_LEDGER_NAME = (
    "CALCULATION_SLICE_6_CHANNEL_MOMENT_REFERENCE_AND_COMPONENT_RESULTANTS_AUTHORITY_LEDGER_RC1.md"
)
_GOLDEN_PATH = _BACKEND / "tests" / "golden" / _GOLDEN_NAME
_GOLDEN = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
_BENCHMARKS = {item["id"]: item for item in _GOLDEN["benchmarks"]}
_GIT = cast(str, shutil.which("git"))


def _q(value: str | int | Decimal, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def _geometry(
    d: str = "8",
    b_f: str = "4",
    t_w: str = "0.5",
    t_f: str = "0.5",
    *,
    homogeneous: bool = True,
) -> ChannelMomentSectionInput:
    return ChannelMomentSectionInput(
        _q(d, Unit.IN),
        _q(b_f, Unit.IN),
        _q(t_w, Unit.IN),
        _q(t_f, Unit.IN),
        homogeneous,
    )


def _actions(
    axial: str = "20",
    shear: str = "-10",
    moment: str = "100",
    *,
    minor_shear: str = "0",
    minor_moment: str = "0",
    torsion: str = "0",
) -> ChannelMomentActionInput:
    return ChannelMomentActionInput(
        _q(axial, Unit.KIP),
        _q(shear, Unit.KIP),
        _q(moment, Unit.KIP_IN),
        _q(minor_shear, Unit.KIP),
        _q(minor_moment, Unit.KIP_IN),
        _q(torsion, Unit.KIP_IN),
    )


def _calculate(
    axial: str = "20",
    shear: str = "-10",
    moment: str = "100",
    *,
    geometry: ChannelMomentSectionInput | None = None,
    shear_center: ChannelShearCenterInput | None = None,
) -> module.ChannelMomentComponentResultants:
    value = ChannelMomentCalculationInput(
        geometry or _geometry(),
        _actions(axial, shear, moment),
        shear_center or ChannelShearCenterInput(),
    )
    return calculate_channel_moment_component_resultants(value)


def _expected(benchmark_id: str, key: str) -> Decimal:
    return Decimal(_BENCHMARKS[benchmark_id]["expected"][key])


def _magnitude(value: PhysicalQuantity, unit: Unit) -> Decimal:
    return value.magnitude if value.unit is unit else value.to(unit).magnitude


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_controlled_artifacts_are_byte_exact_and_sentinels_are_present() -> None:
    controlled = (
        (
            _ROOT
            / "docs"
            / "governance"
            / "CALCULATION_SLICE_6_CHANNEL_MOMENT_REFERENCE_AND_COMPONENT_RESULTANTS_DECISION.md",
            CHANNEL_MOMENT_DECISION_SHA256,
            "END OF CALCULATION SLICE 6 CHANNEL MOMENT REFERENCE AND COMPONENT RESULTANTS DECISION",
        ),
        (
            _ROOT / "docs" / "engineering" / _SPECIFICATION_NAME,
            CHANNEL_MOMENT_SPECIFICATION_SHA256,
            (
                "END OF CALCULATION SLICE 6 CHANNEL MOMENT REFERENCE AND COMPONENT "
                "RESULTANTS ENGINEERING SPECIFICATION RC1"
            ),
        ),
        (
            _GOLDEN_PATH,
            CHANNEL_MOMENT_GOLDEN_SHA256,
            '"G72_STAGE_4_1B_PHYSICAL_CONNECTION_NOT_BEGUN"',
        ),
        (
            _ROOT / "docs" / "qa" / _LEDGER_NAME,
            CHANNEL_MOMENT_LEDGER_SHA256,
            (
                "END OF CALCULATION SLICE 6 CHANNEL MOMENT REFERENCE AND COMPONENT "
                "RESULTANTS AUTHORITY LEDGER RC1"
            ),
        ),
    )
    for path, expected_hash, sentinel in controlled:
        assert _sha256(path) == expected_hash
        assert sentinel in path.read_text(encoding="utf-8")


def test_g1_g2_contract_methods_and_supported_profile_are_closed() -> None:
    assert _GOLDEN["contract"] == CHANNEL_MOMENT_CALCULATION_CONTRACT_VERSION
    assert _GOLDEN["methods"] == [
        CHANNEL_MOMENT_METHOD_ID,
        CHANNEL_RATIONAL_SHEAR_CENTER_METHOD_ID,
        CHANNEL_EXPLICIT_SHEAR_CENTER_METHOD_ID,
    ]
    ids = tuple(item["id"] for item in _GOLDEN["benchmarks"])
    assert len(ids) == len(set(ids)) == 72
    assert ids[0] == "G1_CONTRACT_AND_METHODS"
    assert ids[-1] == "G72_STAGE_4_1B_PHYSICAL_CONNECTION_NOT_BEGUN"
    assert ChannelMomentMethod.RATIONAL_ELASTIC_REGION_RESULTANTS.value == CHANNEL_MOMENT_METHOD_ID
    assert _BENCHMARKS["G2_SUPPORTED_PROFILE_SCOPE"]["expected"] == {
        "supported": ["UNLIPPED_CHANNEL_EQUAL_FLANGES"],
        "WI_supported": False,
        "lipped_channel_supported": False,
        "unequal_flange_channel_supported": False,
    }


def test_source_and_erratum_provenance_is_complete_and_nonprescriptive() -> None:
    source = CHANNEL_MOMENT_SOURCE_PROVENANCE
    assert {item.section for item in source.code_sources} == {
        "2.3.2",
        "2.9",
        "5.1",
        "5.2.3.2",
        "8.1",
        "8.1.1",
        "8.1.2",
        "8.3.4.2",
        "C3.1",
        "C6.1",
        "C6.4",
        "C8.1.1",
        "C8.1.2",
        "C8.1.3",
        "C8.3.4",
    }
    assert (
        source.rational_method_classification is SourceClassification.ENGINEER_APPROVED_DEVELOPMENT
    )
    assert source.qualification_statuses == (
        QualificationStatus.ENGINEERING_REVIEW_REQUIRED,
        QualificationStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
    )
    assert source.erratum_changes_targeted_provisions is False
    assert source.direct_asce_equation_claimed is False
    assert dict(source.authoritative_source_hashes) == {
        "ASCE_SEI_74_23": CHANNEL_MOMENT_ASCE_SOURCE_SHA256,
        "ERRATUM_1_EFFECTIVE_2026_01_13": CHANNEL_MOMENT_ERRATUM_SOURCE_SHA256,
    }
    assert dict(source.controlled_artifact_hashes)["codex_order"] == CHANNEL_MOMENT_ORDER_SHA256


def test_existing_channel_dimension_geometry_surface_and_material_architecture_is_reused() -> None:
    profile = MemberProfile(
        "channel-profile",
        "channel-member",
        MemberRole.BEAM,
        MemberProfileFamily.CHANNEL,
        ChannelProfileDimensions(
            Decimal(12), Decimal(8), Decimal(4), Decimal("0.5"), Decimal("0.5")
        ),
        ComponentMaterialKind.STEEL,
        None,
        MemberProfileOrientation.ROTATION_0,
        MemberProfileSurfaceId.WEB_OUTER,
    )
    adapter = profile_section_geometry_adapter(profile)
    assert adapter.geometry_factory_name == "create_channel_geometry"
    assert adapter.section_datum_offset_y == Decimal(2)
    assert tuple(item[0] for item in adapter.dimension_values) == (
        "overall_depth",
        "flange_width",
        "web_thickness",
        "flange_thickness",
    )
    production = Path(module.__file__).read_text(encoding="utf-8")
    assert "ChannelProfileDimensions" in production
    assert "create_channel_geometry" not in production


def test_g3_through_g18_exact_geometry_properties_and_rational_shear_center() -> None:
    result = _calculate()
    properties = result.section_properties
    assert _magnitude(properties.web_height, Unit.IN) == _expected("G3_DEFAULT_GEOMETRY", "h_w_in")
    assert tuple(
        _magnitude(value, Unit.IN2)
        for value in (
            properties.flange_area,
            properties.web_area,
            properties.flange_area,
            properties.total_area,
        )
    ) == tuple(
        _expected("G4_REGION_AREAS", key)
        for key in ("A_top_in2", "A_web_in2", "A_bottom_in2", "A_total_in2")
    )
    assert tuple(
        _magnitude(value, Unit.IN)
        for value in (
            properties.top_centroid_v,
            properties.web_centroid_v,
            properties.bottom_centroid_v,
            properties.flange_centroid_t_absolute,
            properties.web_centroid_t_absolute,
        )
    ) == tuple(
        _expected("G5_ABSOLUTE_REGION_COORDINATES", key)
        for key in ("V_top_in", "V_web_in", "V_bottom_in", "T_flange_abs_in", "T_web_abs_in")
    )
    assert _magnitude(properties.channel_centroid_t_absolute, Unit.IN) == _expected(
        "G6_EXACT_CHANNEL_CENTROID", "T_c_abs_in"
    )
    assert properties.centroid_source == "EXACT_SHARP_CORNER_UNION_OF_RECTANGLES"
    assert (
        _magnitude(properties.flange_centroid_t_relative, Unit.IN),
        _magnitude(properties.web_centroid_t_relative, Unit.IN),
    ) == (
        _expected("G7_RELATIVE_REGION_COORDINATES", "T_flange_relative_in"),
        _expected("G7_RELATIVE_REGION_COORDINATES", "T_web_relative_in"),
    )
    assert (
        _magnitude(properties.flange_major_centroidal_inertia, Unit.IN4),
        _magnitude(properties.web_major_centroidal_inertia, Unit.IN4),
        _magnitude(properties.total_major_inertia, Unit.IN4),
        _magnitude(properties.total_minor_inertia, Unit.IN4),
        _magnitude(properties.product_inertia_vt, Unit.IN4),
    ) == (
        _expected("G8_REGION_CENTROIDAL_MAJOR_INERTIAS", "I_f_T_c_in4"),
        _expected("G8_REGION_CENTROIDAL_MAJOR_INERTIAS", "I_w_T_c_in4"),
        _expected("G9_TOTAL_MAJOR_AXIS_INERTIA", "I_T_in4"),
        _expected("G10_TOTAL_MINOR_AXIS_INERTIA", "I_V_in4"),
        _expected("G10_TOTAL_MINOR_AXIS_INERTIA", "I_VT_in4"),
    )
    shear_center = result.shear_center
    assert shear_center.median_web_height is not None
    assert shear_center.median_flange_width is not None
    assert shear_center.median_major_inertia is not None
    assert shear_center.rational_web_offset is not None
    assert shear_center.rational_coordinate_t is not None
    assert (
        _magnitude(shear_center.median_web_height, Unit.IN),
        _magnitude(shear_center.median_flange_width, Unit.IN),
        _magnitude(shear_center.median_major_inertia, Unit.IN4),
        _magnitude(shear_center.rational_web_offset, Unit.IN),
        _magnitude(shear_center.absolute_coordinate_t, Unit.IN),
        _magnitude(shear_center.centroid_to_shear_center, Unit.IN),
    ) == (
        _expected("G11_MEDIAN_LINE_DIMENSIONS", "h_m_in"),
        _expected("G11_MEDIAN_LINE_DIMENSIONS", "b_m_in"),
        _expected("G12_MEDIAN_LINE_MAJOR_INERTIA", "I_T_m_in4"),
        _expected("G13_RATIONAL_SHEAR_CENTER_OFFSET_FROM_WEB", "e_w_in"),
        _expected("G14_RATIONAL_SHEAR_CENTER_ABSOLUTE", "T_sc_abs_in"),
        _expected("G15_CENTROID_TO_SHEAR_CENTER_DISTANCE", "e_Csc_in"),
    )
    assert shear_center.rational_closed_form_equal is True
    assert shear_center.absolute_coordinate_t.magnitude < 0
    assert shear_center.experimentally_verified is False
    assert shear_center.rational_comparison_is_controlling is True
    ratios = _BENCHMARKS["G17_RATIONAL_SHEAR_CENTER_REVIEW"]["expected"]["thin_wall_ratios"]
    assert shear_center.web_thin_wall_ratio == Decimal(ratios["t_w_over_h_m"])
    assert shear_center.flange_thin_wall_ratio == Decimal(ratios["t_f_over_b_m"])

    unequal = _calculate(geometry=_geometry("10", "5", "0.375", "0.5"))
    assert (
        _magnitude(unequal.section_properties.channel_centroid_t_absolute, Unit.IN),
        _magnitude(cast(PhysicalQuantity, unequal.shear_center.rational_web_offset), Unit.IN),
        _magnitude(unequal.shear_center.absolute_coordinate_t, Unit.IN),
    ) == tuple(
        _expected("G18_UNEQUAL_THICKNESS_SHEAR_CENTER", key)
        for key in ("T_c_abs_in", "e_w_in", "T_sc_abs_in")
    )


def test_g19_through_g39_default_references_component_wrenches_and_equilibrium() -> None:
    result = _calculate()
    canonical = result.canonical_centroid_wrench
    assert (
        canonical.reference,
        canonical.axial_input_reference,
        canonical.major_moment_input_reference,
        canonical.major_shear_input_reference,
    ) == (
        "CHANNEL_CENTROID",
        "CHANNEL_CENTROID",
        "CHANNEL_CENTROID",
        "CHANNEL_SHEAR_CENTER",
    )
    assert tuple(_magnitude(value, Unit.KIP) for value in vars_vector(canonical.force_lvt)) == (
        Decimal(20),
        Decimal(-10),
        Decimal(0),
    )
    assert tuple(_magnitude(value, Unit.KIP_IN) for value in vars_vector(canonical.moment_lvt)) == (
        _expected("G20_DEFAULT_CANONICAL_CENTROID_WRENCH", "generated_M_L_kip_in"),
        Decimal(0),
        Decimal(100),
    )
    top, web, bottom = result.components
    assert tuple(item.region_id for item in result.components) == (
        ChannelMomentRegionId.TOP_FLANGE,
        ChannelMomentRegionId.WEB,
        ChannelMomentRegionId.BOTTOM_FLANGE,
    )
    assert tuple(_magnitude(item.wrench.force_lvt.l, Unit.KIP) for item in result.components) == (
        _expected("G21_DEFAULT_TOP_FORCE", "N_top_kip"),
        _expected("G22_DEFAULT_WEB_FORCE", "N_web_kip"),
        _expected("G23_DEFAULT_BOTTOM_FORCE", "N_bottom_kip"),
    )
    assert tuple(
        _magnitude(item.wrench.moment_lvt.t, Unit.KIP_IN) for item in result.components
    ) == (
        _expected("G24_DEFAULT_TOP_LOCAL_MAJOR_MOMENT", "m_T_top_kip_in"),
        _expected("G25_DEFAULT_WEB_LOCAL_MAJOR_MOMENT", "m_T_web_kip_in"),
        _expected("G26_DEFAULT_BOTTOM_LOCAL_MAJOR_MOMENT", "m_T_bottom_kip_in"),
    )
    assert tuple(_magnitude(item.wrench.force_lvt.v, Unit.KIP) for item in result.components) == (
        Decimal(0),
        Decimal(-10),
        Decimal(0),
    )
    assert _magnitude(result.equilibrium.summed_force_lvt.l, Unit.KIP) == _expected(
        "G28_DEFAULT_LONGITUDINAL_FORCE_EQUILIBRIUM", "sum_N_kip"
    )
    assert _magnitude(result.equilibrium.summed_moment_lvt.t, Unit.KIP_IN) == _expected(
        "G29_DEFAULT_MAJOR_MOMENT_EQUILIBRIUM", "sum_M_T_kip_in"
    )
    assert tuple(
        _magnitude(item.global_minor_moment, Unit.KIP_IN) for item in result.components
    ) == (
        _expected("G30_DEFAULT_MINOR_MOMENT_LEDGER", "top_M_V_kip_in"),
        _expected("G30_DEFAULT_MINOR_MOMENT_LEDGER", "web_M_V_kip_in"),
        _expected("G30_DEFAULT_MINOR_MOMENT_LEDGER", "bottom_M_V_kip_in"),
    )
    torsion = result.torsion_diagnostics
    assert (
        _magnitude(torsion.generated_centroidal_torsion, Unit.KIP_IN),
        _magnitude(torsion.web_shear_force_line_torsion, Unit.KIP_IN),
        _magnitude(torsion.web_free_torsion, Unit.KIP_IN),
        _magnitude(cast(PhysicalQuantity, torsion.rational_flange_shear_flow_resultant), Unit.KIP),
    ) == (
        _expected("G31_DEFAULT_CENTROIDAL_TORSION", "M_L_C_kip_in"),
        _expected("G32_WEB_SHEAR_FORCE_LINE_TORSION", "M_L_web_force_kip_in"),
        _expected("G33_WEB_FREE_TORSION", "m_L_web_kip_in"),
        _expected("G35_FLANGE_SHEAR_FLOW_RESULTANT", "H_f_each_flange_kip"),
    )
    assert torsion.rational_shear_flow_identity_exact is True
    for item, benchmark in zip(
        (top, web, bottom),
        (
            "G36_TOP_COMPONENT_REFERENCE_AND_WRENCH",
            "G37_WEB_COMPONENT_REFERENCE_AND_WRENCH",
            "G38_BOTTOM_COMPONENT_REFERENCE_AND_WRENCH",
        ),
        strict=True,
    ):
        expected = _BENCHMARKS[benchmark]["expected"]
        assert tuple(
            _magnitude(value, Unit.IN) for value in vars_vector(item.wrench.reference_lvt)
        ) == tuple(Decimal(value) for value in expected["reference_L_V_T_in"])
        assert tuple(
            _magnitude(value, Unit.KIP) for value in vars_vector(item.wrench.force_lvt)
        ) == tuple(Decimal(value) for value in expected["force_L_V_T_kip"])
        assert tuple(
            _magnitude(value, Unit.KIP_IN) for value in vars_vector(item.wrench.moment_lvt)
        ) == tuple(Decimal(value) for value in expected["moment_L_V_T_kip_in"])
    equilibrium = result.equilibrium
    assert (
        equilibrium.axial_equilibrium_exact,
        equilibrium.major_shear_equilibrium_exact,
        equilibrium.major_moment_equilibrium_exact,
        equilibrium.torsion_equilibrium_exact,
        equilibrium.zero_minor_shear_exact,
        equilibrium.zero_minor_moment_exact,
    ) == (True,) * 6
    assert result.component(ChannelMomentRegionId.WEB) is web


def vars_vector(value: BeamQuantityVector) -> tuple[PhysicalQuantity, ...]:
    return (value.l, value.v, value.t)


def test_g40_through_g47_diagnostics_stresses_and_states() -> None:
    result = _calculate()
    diagnostics = result.couple_diagnostics
    assert (
        _magnitude(diagnostics.flange_lever_arm, Unit.IN),
        _magnitude(diagnostics.exact_flange_couple_force, Unit.KIP),
        _magnitude(diagnostics.exact_flange_couple_moment, Unit.KIP_IN),
        _magnitude(diagnostics.full_moment_over_z_reference_force, Unit.KIP),
        _magnitude(diagnostics.residual_moment, Unit.KIP_IN),
        _magnitude(diagnostics.local_and_web_moment_sum, Unit.KIP_IN),
    ) == (
        _expected("G40_FLANGE_LEVER_ARM", "z_f_in"),
        _expected("G41_EXACT_FLANGE_COUPLE", "C_f_kip"),
        _expected("G41_EXACT_FLANGE_COUPLE", "M_couple_kip_in"),
        _expected("G42_FULL_MOMENT_M_OVER_Z_REFERENCE", "C_M_over_z_kip"),
        _expected("G43_RESIDUAL_MAJOR_MOMENT", "M_residual_kip_in"),
        _expected("G43_RESIDUAL_MAJOR_MOMENT", "local_and_web_identity_kip_in"),
    )
    assert diagnostics.full_moment_over_z_is_controlling is False
    assert diagnostics.residual_identity_exact is True
    expected_stress = (
        ("G44_TOP_STRESS_EXTREMA", "inner_ksi", "outer_ksi"),
        ("G45_WEB_STRESS_EXTREMA", "bottom_ksi", "top_ksi"),
        ("G46_BOTTOM_STRESS_EXTREMA", "outer_ksi", "inner_ksi"),
    )
    for component, (benchmark, first, second) in zip(
        result.components, expected_stress, strict=True
    ):
        assert _magnitude(component.stress_extrema.first_stress_l, Unit.KSI) == _expected(
            benchmark, first
        )
        assert _magnitude(component.stress_extrema.second_stress_l, Unit.KSI) == _expected(
            benchmark, second
        )
    assert tuple(item.stress_extrema.crosses_zero for item in result.components) == (
        False,
        True,
        False,
    )
    assert tuple(item.force_state for item in result.components) == (
        ChannelMomentRegionForceState.TENSION,
        ChannelMomentRegionForceState.TENSION,
        ChannelMomentRegionForceState.COMPRESSION,
    )


def test_g48_through_g54_pure_zero_and_sign_reversal_matrix() -> None:
    pure_axial = _calculate(shear="0", moment="0")
    assert tuple(
        _magnitude(item.wrench.force_lvt.l, Unit.KIP) for item in pure_axial.components
    ) == tuple(
        _expected("G48_PURE_AXIAL_COMPONENTS", key)
        for key in ("N_top_kip", "N_web_kip", "N_bottom_kip")
    )
    assert all(item.wrench.moment_lvt.t.canonical_magnitude == 0 for item in pure_axial.components)
    assert pure_axial.equilibrium.zero_minor_moment_exact

    pure_moment = _calculate(axial="0", shear="0")
    assert tuple(
        _magnitude(item.wrench.force_lvt.l, Unit.KIP) for item in pure_moment.components
    ) == tuple(
        _expected("G49_PURE_MOMENT_COMPONENTS", key)
        for key in ("N_top_kip", "N_web_kip", "N_bottom_kip")
    )
    pure_shear = _calculate(axial="0", moment="0")
    assert pure_shear.component(ChannelMomentRegionId.WEB).wrench.force_lvt.v.magnitude == -10
    assert _magnitude(
        pure_shear.torsion_diagnostics.generated_centroidal_torsion, Unit.KIP_IN
    ) == _expected("G50_PURE_MAJOR_SHEAR_COMPONENTS", "centroidal_torsion_kip_in")
    assert all(item.wrench.force_lvt.l.canonical_magnitude == 0 for item in pure_shear.components)

    zero = _calculate(axial="0", shear="0", moment="0")
    assert all(
        value.canonical_magnitude == 0
        for item in zero.components
        for value in (*vars_vector(item.wrench.force_lvt), *vars_vector(item.wrench.moment_lvt))
    )
    assert all(
        item.force_state is ChannelMomentRegionForceState.ZERO_FORCE for item in zero.components
    )

    baseline = _calculate()
    axial_reverse = _calculate(axial="-20")
    negative_uniform = _calculate(axial="-20", shear="0", moment="0")
    assert tuple(
        item.wrench.force_lvt.l.magnitude for item in negative_uniform.components
    ) == tuple(item.wrench.force_lvt.l.magnitude.copy_negate() for item in pure_axial.components)
    for original, reversed_item in zip(baseline.components, axial_reverse.components, strict=True):
        assert reversed_item.wrench.moment_lvt.t == original.wrench.moment_lvt.t
    moment_reverse = _calculate(moment="-100")
    assert tuple(item.wrench.moment_lvt.t.magnitude for item in moment_reverse.components) == tuple(
        item.wrench.moment_lvt.t.magnitude.copy_negate() for item in baseline.components
    )
    assert tuple(
        _calculate(axial="0", moment="-100").component(item.region_id).wrench.force_lvt.l.magnitude
        for item in baseline.components
    ) == tuple(
        _calculate(axial="0").component(item.region_id).wrench.force_lvt.l.magnitude.copy_negate()
        for item in baseline.components
    )
    shear_reverse = _calculate(shear="10")
    assert shear_reverse.torsion_diagnostics.generated_centroidal_torsion.magnitude == (
        baseline.torsion_diagnostics.generated_centroidal_torsion.magnitude.copy_negate()
    )
    assert shear_reverse.torsion_diagnostics.web_free_torsion.magnitude == (
        baseline.torsion_diagnostics.web_free_torsion.magnitude.copy_negate()
    )
    assert tuple(item.wrench.force_lvt.l for item in shear_reverse.components) == tuple(
        item.wrench.force_lvt.l for item in baseline.components
    )


def test_g55_through_g57_explicit_verified_shear_center_and_source_exclusivity() -> None:
    explicit = ChannelShearCenterInput(
        ChannelShearCenterMethod.EXPLICIT_VERIFIED,
        _q("-1", Unit.IN),
        "CONTROLLED_SECTION_ANALYSIS:CHANNEL-8X4-RC1",
    )
    result = _calculate(shear_center=explicit)
    assert result.shear_center.method is ChannelShearCenterMethod.EXPLICIT_VERIFIED
    assert result.shear_center.rational_coordinate_t is None
    assert result.shear_center.experimentally_verified is True
    assert result.shear_center.rational_comparison_is_controlling is False
    assert _magnitude(result.shear_center.centroid_to_shear_center, Unit.IN) == _expected(
        "G55_EXPLICIT_VERIFIED_SHEAR_CENTER", "e_Csc_in"
    )
    assert _magnitude(
        result.torsion_diagnostics.generated_centroidal_torsion, Unit.KIP_IN
    ) == _expected("G55_EXPLICIT_VERIFIED_SHEAR_CENTER", "centroidal_torsion_kip_in")
    assert _magnitude(result.torsion_diagnostics.web_free_torsion, Unit.KIP_IN) == _expected(
        "G55_EXPLICIT_VERIFIED_SHEAR_CENTER", "web_free_torsion_kip_in"
    )
    assert result.torsion_diagnostics.rational_flange_shear_flow_resultant is None
    assert result.torsion_diagnostics.rational_flange_shear_flow_moment is None
    assert result.torsion_diagnostics.rational_shear_flow_identity_exact is None
    comparison = _calculate(shear_center=replace(explicit, include_rational_comparison=True))
    assert comparison.shear_center.rational_coordinate_t is not None
    assert comparison.shear_center.rational_comparison_is_controlling is False

    with pytest.raises(ChannelMomentInputRejected) as missing_source:
        ChannelShearCenterInput(ChannelShearCenterMethod.EXPLICIT_VERIFIED)
    assert (
        missing_source.value.reason
        is ChannelMomentRejectionReason.SINGLE_SHEAR_CENTER_SOURCE_REQUIRED
    )
    with pytest.raises(ChannelMomentInputRejected) as missing_provenance:
        ChannelShearCenterInput(ChannelShearCenterMethod.EXPLICIT_VERIFIED, _q(-1, Unit.IN))
    assert missing_provenance.value.reason is (
        ChannelMomentRejectionReason.VERIFIED_SHEAR_CENTER_PROVENANCE_REQUIRED
    )
    with pytest.raises(ChannelMomentInputRejected):
        ChannelShearCenterInput(ChannelShearCenterMethod.EXPLICIT_VERIFIED, _q(-1, Unit.IN), "  ")
    with pytest.raises(ChannelMomentInputRejected) as conflict:
        ChannelShearCenterInput(
            ChannelShearCenterMethod.RATIONAL_THIN_WALL,
            _q(-1, Unit.IN),
            "MUST_NOT_OVERRIDE",
        )
    assert conflict.value.reason is ChannelMomentRejectionReason.SINGLE_SHEAR_CENTER_SOURCE_REQUIRED


@pytest.mark.parametrize(
    ("actions", "reason"),
    [
        (_actions(minor_shear="1"), ChannelMomentRejectionReason.MINOR_SHEAR_NOT_SUPPORTED),
        (
            _actions(minor_moment="1"),
            ChannelMomentRejectionReason.MINOR_AXIS_MOMENT_NOT_SUPPORTED,
        ),
        (_actions(torsion="1"), ChannelMomentRejectionReason.USER_TORSION_NOT_SUPPORTED),
    ],
)
def test_g58_through_g60_unsupported_actions_fail_closed(
    actions: ChannelMomentActionInput, reason: ChannelMomentRejectionReason
) -> None:
    with pytest.raises(ChannelMomentInputRejected) as caught:
        calculate_channel_moment_component_resultants(
            ChannelMomentCalculationInput(_geometry(), actions)
        )
    assert caught.value.status is ChannelMomentInputStatus.REJECTED
    assert caught.value.reason is reason


@pytest.mark.parametrize(
    ("geometry", "status", "reason"),
    [
        (
            _geometry("1", "4", "0.5", "0.5"),
            ChannelMomentInputStatus.REJECTED,
            ChannelMomentRejectionReason.POSITIVE_WEB_HEIGHT_REQUIRED,
        ),
        (
            _geometry("8", "0.5", "0.5", "0.25"),
            ChannelMomentInputStatus.REJECTED,
            ChannelMomentRejectionReason.FLANGE_WIDTH_MUST_EXCEED_WEB_THICKNESS,
        ),
        (
            _geometry(homogeneous=False),
            ChannelMomentInputStatus.REQUIRES_SECTION_2_3_2,
            ChannelMomentRejectionReason.HOMOGENEOUS_LONGITUDINAL_SECTION_REQUIRED,
        ),
    ],
)
def test_g61_through_g63_invalid_or_inhomogeneous_sections_fail_closed(
    geometry: ChannelMomentSectionInput,
    status: ChannelMomentInputStatus,
    reason: ChannelMomentRejectionReason,
) -> None:
    with pytest.raises(ChannelMomentInputRejected) as caught:
        _calculate(geometry=geometry)
    assert caught.value.status is status
    assert caught.value.reason is reason


def test_g64_us_si_equivalence_is_exact() -> None:
    us_input = ChannelMomentCalculationInput(_geometry(), _actions())
    si_dimensions = tuple(
        _q(value, Unit.IN).to(Unit.MM) for value in (8, 4, Decimal("0.5"), Decimal("0.5"))
    )
    si_input = ChannelMomentCalculationInput(
        ChannelMomentSectionInput(
            si_dimensions[0],
            si_dimensions[1],
            si_dimensions[2],
            si_dimensions[3],
        ),
        ChannelMomentActionInput(
            _q(20, Unit.KIP).to(Unit.KN),
            _q(-10, Unit.KIP).to(Unit.KN),
            _q(100, Unit.KIP_IN).to(Unit.KN_MM),
            _q(0, Unit.KN),
            _q(0, Unit.KN_MM),
            _q(0, Unit.KN_MM),
        ),
    )
    us = calculate_channel_moment_component_resultants(us_input)
    si = calculate_channel_moment_component_resultants(si_input)
    assert us.input_fingerprint == si.input_fingerprint
    assert us.result_fingerprint == si.result_fingerprint
    assert us.section_properties == si.section_properties
    assert us.shear_center == si.shear_center
    assert us.components == si.components
    assert us.equilibrium == si.equilibrium


def test_g65_fingerprints_are_deterministic_complete_and_presentation_excluded() -> None:
    calculation_input = ChannelMomentCalculationInput(_geometry(), _actions())
    envelope = ChannelMomentFingerprintEnvelope(
        calculation_input,
        "SI",
        "3",
        {"camera": "ignored"},
        "WEB",
        "2026-09-03T00:00:00Z",
    )
    assert channel_moment_input_fingerprint(calculation_input) == channel_moment_input_fingerprint(
        envelope
    )
    assert canonical_channel_moment_input_json(
        calculation_input
    ) == canonical_channel_moment_input_json(envelope)
    assert _calculate().input_fingerprint == _calculate().input_fingerprint
    assert _calculate().result_fingerprint == _calculate().result_fingerprint
    assert _calculate(moment="101").result_fingerprint != _calculate().result_fingerprint
    explicit = ChannelShearCenterInput(
        ChannelShearCenterMethod.EXPLICIT_VERIFIED,
        _q(-1, Unit.IN),
        "CONTROLLED_EXPLICIT_PROPERTY",
    )
    assert _calculate(shear_center=explicit).input_fingerprint != _calculate().input_fingerprint


def test_g66_g67_review_disclaimer_and_no_strength_result_are_backend_owned() -> None:
    result = _calculate()
    assert result.rational_method_engineering_review_required is True
    assert result.disclaimer_id == CHANNEL_MOMENT_DISCLAIMER_ID
    assert "not direct ASCE/SEI 74-23 connection-detail equations" in result.disclaimer
    names = set(result.__dataclass_fields__)
    assert names.isdisjoint(
        {
            "status",
            "pass_fail",
            "capacity",
            "utilization",
            "torsional_resistance",
            "warping_stress",
            "connection_stiffness",
            "moment_rotation",
        }
    )
    production = Path(module.__file__).read_text(encoding="utf-8")
    assert CHANNEL_MOMENT_DISCLAIMER_ID in production
    assert "tests/golden" not in production
    assert "calculation_slice_6_channel_moment_reference" not in production


def test_g68_frontend_production_identity_is_unchanged() -> None:
    # Slice 6 was backend-only; successor frontend work is not its historical identity.
    accepted_commit = "b275a647bbbc1786d169302f060402fbfb062aab"
    handoff = json.loads((_ROOT / "HANDOFF_MANIFEST.json").read_text(encoding="utf-8"))
    assert handoff["calculation_slice_6_accepted_commit"] == accepted_commit
    assert handoff["calculation_slice_6_frontend_production_change_count"] == 0
    frozen_manifest = (
        _ROOT
        / "docs"
        / "governance"
        / "STAGE_4_1A_WI_MAJOR_AXIS_MOMENT_SPLICE_FREEZE_MANIFEST.json"
    ).read_bytes()
    assert hashlib.sha256(frozen_manifest).hexdigest().upper() == (
        "A77FACD1A05F60E947F3F394FCFB3FC5D28120922BF6EA9841E4EC9C80D4061F"
    )
    # A depth-one successor may lack all historical objects and tags. In that case,
    # verify the immutable manifest identity retained unchanged by accepted Slice 6.
    actual = json.loads(frozen_manifest)["repository_identities"]["accepted_frontend_src_tree"]
    available = subprocess.run(  # noqa: S603 - executable resolved from the test host
        [_GIT, "cat-file", "-e", f"{accepted_commit}^{{commit}}"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if available.returncode == 0:
        actual = subprocess.run(  # noqa: S603 - executable resolved from the test host
            [_GIT, "rev-parse", f"{accepted_commit}:frontend/src"],
            cwd=_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    assert actual == "7deabca069f034e7f43f426ba31d7dca0c839419"


def test_g69_through_g71_all_freeze_audits_are_successor_safe_and_tagless_portable() -> None:
    stage_3_2_path = _BACKEND / "tests" / "calculation" / "test_stage_3_2_freeze_manifest.py"
    stage_3_2 = stage_3_2_path.read_text(encoding="utf-8")
    assert "shallow_file" in stage_3_2
    assert "stage-2.3-interface-geometry-freeze" in stage_3_2
    stages = ("3_3", "3_4", "3_5", "3_6", "3_7", "4_1a")
    for stage in stages:
        path = _BACKEND / "tests" / "calculation" / f"test_stage_{stage}_freeze_manifest.py"
        source = path.read_text(encoding="utf-8")
        assert "manifest_only" in source
        assert "tag" in source
        assert "object" in source


def test_g72_physical_channel_moment_splice_is_not_started() -> None:
    result = _calculate()
    names = set(result.__dataclass_fields__)
    assert names.isdisjoint(
        {"channel_splice_geometry", "bolt_groups", "connection_resistance", "selector_workspace"}
    )
    assert not (_ROOT / "frontend" / "src" / "channelMomentSplice").exists()


def test_public_value_objects_and_calculation_boundaries_are_strict() -> None:
    with pytest.raises(TypeError, match=r"ChannelMomentSectionInput\.d"):
        ChannelMomentSectionInput("8", _q(4, Unit.IN), _q(1, Unit.IN), _q(1, Unit.IN))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must be a length"):
        replace(_geometry(), d=_q(8, Unit.KIP))
    with pytest.raises(TypeError, match="homogeneous_longitudinal_modulus"):
        replace(_geometry(), homogeneous_longitudinal_modulus=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="axial_force_l"):
        replace(_actions(), axial_force_l="20")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="axial_force_l must be a force"):
        replace(_actions(), axial_force_l=_q(20, Unit.IN))
    with pytest.raises(TypeError, match="major_moment_t"):
        replace(_actions(), major_moment_t="100")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="major_moment_t must be a moment"):
        replace(_actions(), major_moment_t=_q(100, Unit.KIP))
    with pytest.raises(TypeError, match="method"):
        ChannelShearCenterInput(CHANNEL_RATIONAL_SHEAR_CENTER_METHOD_ID)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="include_rational_comparison"):
        replace(ChannelShearCenterInput(), include_rational_comparison=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="explicit_coordinate_t"):
        ChannelShearCenterInput(
            ChannelShearCenterMethod.EXPLICIT_VERIFIED,
            "-1",  # type: ignore[arg-type]
            "SOURCE",
        )
    with pytest.raises(ValueError, match="explicit_coordinate_t must be a length"):
        ChannelShearCenterInput(
            ChannelShearCenterMethod.EXPLICIT_VERIFIED, _q(-1, Unit.KIP), "SOURCE"
        )
    with pytest.raises(TypeError, match="explicit_provenance"):
        ChannelShearCenterInput(
            ChannelShearCenterMethod.EXPLICIT_VERIFIED,
            _q(-1, Unit.IN),
            1,  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="geometry"):
        ChannelMomentCalculationInput("geometry", _actions())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="actions"):
        ChannelMomentCalculationInput(_geometry(), "actions")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="shear_center"):
        ChannelMomentCalculationInput(_geometry(), _actions(), "source")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="contract_version"):
        ChannelMomentCalculationInput(_geometry(), _actions(), contract_version=6)  # type: ignore[arg-type]
    with pytest.raises(ChannelMomentInputRejected) as contract:
        ChannelMomentCalculationInput(_geometry(), _actions(), contract_version="CS6-RC2")
    assert contract.value.reason is ChannelMomentRejectionReason.UNSUPPORTED_CONTRACT_VERSION
    with pytest.raises(TypeError, match="method"):
        ChannelMomentCalculationInput(_geometry(), _actions(), method=CHANNEL_MOMENT_METHOD_ID)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="calculation_input"):
        calculate_channel_moment_component_resultants("input")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="region_id"):
        _calculate().component("WEB")  # type: ignore[arg-type]
    with pytest.raises(ChannelMomentInputRejected) as positive:
        _calculate(geometry=_geometry("-8"))
    assert positive.value.reason is ChannelMomentRejectionReason.POSITIVE_DIMENSIONS_REQUIRED


def test_fingerprint_canonicalizer_rejects_ambiguous_values() -> None:
    assert module._canonicalize(5) == "5"
    assert module._canonicalize(ChannelMomentRegionId.WEB) == "WEB"
    assert module._canonicalize(date(2026, 9, 3)) == "2026-09-03"
    with pytest.raises(TypeError, match="calculation input or envelope"):
        canonical_channel_moment_input_json("input")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Raw floating-point"):
        module._canonicalize(1.0)
    with pytest.raises(TypeError, match="mapping keys"):
        module._canonicalize({1: "not text"})
    with pytest.raises(TypeError, match="Unsupported Slice 6"):
        module._canonicalize(object())
