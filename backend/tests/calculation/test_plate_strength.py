"""Golden and fail-closed verification for Calculation Slice 4."""

from __future__ import annotations

import hashlib
import inspect
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType

import pytest

import frp_master_connection.domain as _domain  # noqa: F401
from frp_master_connection.calculation.equations import EndUsePropertyTrace
from frp_master_connection.calculation.inputs import (
    TimeEffectCategory,
    TimeEffectFactor,
    select_time_effect_factor,
)
from frp_master_connection.calculation.plate_strength import (
    PLATE_COMPRESSION_PHI,
    PLATE_LONGITUDINAL_K_CR,
    PLATE_SHEAR_PHI,
    PLATE_TENSION_PHI,
    PlateCompressionStrengthResult,
    PlateGoverningMode,
    PlateShearStrengthResult,
    PlateStrengthAdvisory,
    PlateStrengthMethod,
    PlateStrengthStatus,
    ShearEtaBranch,
    plate_combined_compression_buckling_strength,
    plate_in_plane_shear_strength,
    plate_longitudinal_compression_strength,
    plate_longitudinal_tension_strength,
    plate_transverse_compression_rupture_reference,
    plate_transverse_tension_strength,
)
from frp_master_connection.calculation.properties import FRPPropertyKind
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.calculation.sources import (
    QualificationStatus,
    asce_74_23_chapter_7_source,
)
from tests.calculation.golden_loader import (
    SLICE_4_CHAPTER_7_PLATE_STRENGTH_RC1_GOLDEN_PATH,
    FrozenJson,
    load_slice_4_chapter_7_plate_strength_rc1_golden_fixture,
)

_ROOT = Path(__file__).parents[3]
_GOLDEN = load_slice_4_chapter_7_plate_strength_rc1_golden_fixture()


def _quantity(value: str, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def _trace(kind: FRPPropertyKind, value: str, unit: Unit) -> EndUsePropertyTrace:
    quantity = _quantity(value, unit)
    return EndUsePropertyTrace(
        property_kind=kind,
        source_property=quantity,
        qualification_status=QualificationStatus.DEVELOPMENT_ONLY,
        cm=Decimal(1),
        ct=Decimal(1),
        cch=Decimal(1),
        adjusted_property=quantity,
    )


def _fixture(*, shear_modulus: str = "500") -> dict[FRPPropertyKind, EndUsePropertyTrace]:
    return {
        FRPPropertyKind.FT_L: _trace(FRPPropertyKind.FT_L, "30", Unit.KSI),
        FRPPropertyKind.FT_T: _trace(FRPPropertyKind.FT_T, "10", Unit.KSI),
        FRPPropertyKind.FC_L: _trace(FRPPropertyKind.FC_L, "25", Unit.KSI),
        FRPPropertyKind.FC_T: _trace(FRPPropertyKind.FC_T, "12", Unit.KSI),
        FRPPropertyKind.FSH_LT: _trace(FRPPropertyKind.FSH_LT, "8", Unit.KSI),
        FRPPropertyKind.ET_L: _trace(FRPPropertyKind.ET_L, "2500", Unit.KSI),
        FRPPropertyKind.ET_T: _trace(FRPPropertyKind.ET_T, "1200", Unit.KSI),
        FRPPropertyKind.G_LT: _trace(FRPPropertyKind.G_LT, shear_modulus, Unit.KSI),
        FRPPropertyKind.NU_LT: _trace(FRPPropertyKind.NU_LT, "0.3", Unit.ONE),
    }


def _benchmark(benchmark_id: str) -> MappingProxyType[str, FrozenJson]:
    benchmarks = _GOLDEN["benchmarks"]
    assert isinstance(benchmarks, tuple)
    for benchmark in benchmarks:
        assert isinstance(benchmark, MappingProxyType)
        typed = benchmark
        if typed["id"] == benchmark_id:
            return typed
    raise AssertionError(f"Missing controlled benchmark {benchmark_id}.")


def _expected(benchmark_id: str, key: str) -> str:
    expected = _benchmark(benchmark_id)["expected"]
    assert isinstance(expected, MappingProxyType)
    value = expected[key]
    assert isinstance(value, str)
    return value


def _stress(result: PhysicalQuantity) -> Decimal:
    return result.magnitude if result.unit is Unit.KSI else result.to(Unit.KSI).magnitude


def _line_strength(result: PhysicalQuantity) -> Decimal:
    return (
        result.magnitude if result.unit is Unit.KIP_PER_IN else result.to(Unit.KIP_PER_IN).magnitude
    )


def _impact() -> TimeEffectFactor:
    return select_time_effect_factor(TimeEffectCategory.IMPACT)


def _compression(
    properties: dict[FRPPropertyKind, EndUsePropertyTrace],
    *,
    thickness: str = "0.5",
    transverse_span: str = "12",
    longitudinal_span: str | None = "24",
) -> PlateCompressionStrengthResult:
    return plate_longitudinal_compression_strength(
        _quantity(thickness, Unit.IN),
        _quantity(transverse_span, Unit.IN),
        properties[FRPPropertyKind.FC_L],
        properties[FRPPropertyKind.ET_L],
        properties[FRPPropertyKind.ET_T],
        properties[FRPPropertyKind.G_LT],
        properties[FRPPropertyKind.NU_LT],
        _impact(),
        longitudinal_span=(
            None if longitudinal_span is None else _quantity(longitudinal_span, Unit.IN)
        ),
    )


def _shear(
    properties: dict[FRPPropertyKind, EndUsePropertyTrace],
    *,
    longitudinal_span: str | None = "24",
) -> PlateShearStrengthResult:
    return plate_in_plane_shear_strength(
        _quantity("0.5", Unit.IN),
        _quantity("12", Unit.IN),
        properties[FRPPropertyKind.FSH_LT],
        properties[FRPPropertyKind.ET_L],
        properties[FRPPropertyKind.ET_T],
        properties[FRPPropertyKind.G_LT],
        properties[FRPPropertyKind.NU_LT],
        _impact(),
        longitudinal_span=(
            None if longitudinal_span is None else _quantity(longitudinal_span, Unit.IN)
        ),
    )


def test_controlled_golden_is_complete_immutable_and_hash_exact() -> None:
    assert _GOLDEN["version"] == "RC1"
    benchmarks = _GOLDEN["benchmarks"]
    assert isinstance(benchmarks, tuple)
    assert len(benchmarks) == 40
    for index, benchmark in enumerate(benchmarks, start=1):
        assert isinstance(benchmark, MappingProxyType)
        benchmark_id = benchmark["id"]
        assert isinstance(benchmark_id, str)
        assert benchmark_id.startswith(f"G{index}_")
    assert hashlib.sha256(
        SLICE_4_CHAPTER_7_PLATE_STRENGTH_RC1_GOLDEN_PATH.read_bytes()
    ).hexdigest().upper() == ("E6F00A1421751386980321A5AA046A13C706D9D32E42AAC6242F0D89525AC4CD")
    with pytest.raises(TypeError):
        _GOLDEN["version"] = "changed"  # type: ignore[index]


def test_controlled_artifacts_are_byte_exact_and_have_final_sentinels() -> None:
    specification_path = (
        _ROOT
        / "docs/engineering"
        / "CALCULATION_SLICE_4_CHAPTER_7_PLATE_STRENGTH_ENGINE_ENGINEERING_SPECIFICATION_RC1.md"
    )
    artifacts = {
        _ROOT / "docs/governance/CALCULATION_SLICE_4_CHAPTER_7_PLATE_STRENGTH_ENGINE_DECISION.md": (
            "C1FF10672CC98A832932DCBD010DCF280F0D866123280AC68565767F14093E28",
            "END OF CALCULATION SLICE 4 CHAPTER 7 PLATE STRENGTH ENGINE DECISION",
        ),
        specification_path: (
            "32F1A51AC6C82701C2C9E61F08AEC1E804D500D5507BC930A6677B40CD93C541",
            "END OF CALCULATION SLICE 4 CHAPTER 7 PLATE STRENGTH ENGINE SPECIFICATION RC1",
        ),
        SLICE_4_CHAPTER_7_PLATE_STRENGTH_RC1_GOLDEN_PATH: (
            "E6F00A1421751386980321A5AA046A13C706D9D32E42AAC6242F0D89525AC4CD",
            '"id": "G40_EARLIER_FREEZE_REGRESSIONS"',
        ),
        _ROOT
        / "docs/qa/CALCULATION_SLICE_4_CHAPTER_7_PLATE_STRENGTH_ENGINE_AUTHORITY_LEDGER_RC1.md": (
            "7E515FABD6AC3118528F3404CE06456748776054627499EE06C6A0907A782971",
            "END OF CALCULATION SLICE 4 CHAPTER 7 PLATE STRENGTH ENGINE AUTHORITY LEDGER RC1",
        ),
    }
    for path, (expected_hash, sentinel) in artifacts.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == expected_hash
        assert sentinel in path.read_text(encoding="utf-8")


def test_tension_g1_through_g4_are_exact() -> None:
    properties = _fixture()
    longitudinal = plate_longitudinal_tension_strength(
        _quantity("0.5", Unit.IN), properties[FRPPropertyKind.FT_L], _impact()
    )
    transverse = plate_transverse_tension_strength(
        _quantity("0.5", Unit.IN), properties[FRPPropertyKind.FT_T], _impact()
    )
    assert _line_strength(longitudinal.nominal_strength) == Decimal(
        _expected("G1_LONGITUDINAL_TENSION_NOMINAL", "kip_per_in")
    )
    assert longitudinal.method.value == _expected("G1_LONGITUDINAL_TENSION_NOMINAL", "method")
    assert _line_strength(longitudinal.design_strength) == Decimal(
        _expected("G2_LONGITUDINAL_TENSION_DESIGN", "kip_per_in")
    )
    assert _line_strength(transverse.nominal_strength) == Decimal(
        _expected("G3_TRANSVERSE_TENSION_NOMINAL", "kip_per_in")
    )
    assert transverse.method.value == _expected("G3_TRANSVERSE_TENSION_NOMINAL", "method")
    assert _line_strength(transverse.design_strength) == Decimal(
        _expected("G4_TRANSVERSE_TENSION_DESIGN", "kip_per_in")
    )
    assert longitudinal.resistance_factor == transverse.resistance_factor == PLATE_TENSION_PHI
    assert longitudinal.governing_mode is PlateGoverningMode.MATERIAL_RUPTURE
    assert not longitudinal.property_adjustment_applied_by_engine
    assert longitudinal.advisories == ()


def test_compression_g5_through_g11_and_advisories_are_exact() -> None:
    properties = _fixture()
    result = _compression(properties)
    transverse = plate_transverse_compression_rupture_reference(
        _quantity("0.5", Unit.IN), properties[FRPPropertyKind.FC_T], _impact()
    )
    assert _line_strength(result.rupture_nominal_strength) == Decimal(
        _expected("G5_LONGITUDINAL_COMPRESSION_RUPTURE", "kip_per_in")
    )
    assert _line_strength(transverse.rupture_nominal_strength) == Decimal(
        _expected("G6_TRANSVERSE_COMPRESSION_RUPTURE", "kip_per_in")
    )
    assert _stress(result.buckling_stress) == Decimal(
        _expected("G7_LONGITUDINAL_BUCKLING_STRESS", "ksi")
    )
    assert _line_strength(result.buckling_nominal_strength) == Decimal(
        _expected("G8_LONGITUDINAL_BUCKLING_NOMINAL", "kip_per_in")
    )
    assert result.governing_mode.value == _expected("G9_LONGITUDINAL_COMPRESSION_GOVERNING", "mode")
    assert _line_strength(result.design_strength) == Decimal(
        _expected("G10_LONGITUDINAL_COMPRESSION_DESIGN", "kip_per_in")
    )
    assert _line_strength(transverse.rupture_design_reference) == Decimal(
        _expected(
            "G11_TRANSVERSE_COMPRESSION_DESIGN_REFERENCE", "material_rupture_design_kip_per_in"
        )
    )
    assert transverse.complete_stability_status.value == _expected(
        "G11_TRANSVERSE_COMPRESSION_DESIGN_REFERENCE", "complete_stability"
    )
    assert result.k_cr == PLATE_LONGITUDINAL_K_CR
    assert result.resistance_factor == transverse.resistance_factor == PLATE_COMPRESSION_PHI
    assert result.advisories == (PlateStrengthAdvisory.SHORT_COMPRESSION_PLATE,)
    assert not result.property_adjustment_applied_by_engine


def test_combined_compression_g12_through_g17_is_exact_and_fail_closed() -> None:
    properties = _fixture()
    arguments = (
        _quantity("0.5", Unit.IN),
        _quantity("24", Unit.IN),
        _quantity("12", Unit.IN),
        properties[FRPPropertyKind.ET_L],
        properties[FRPPropertyKind.ET_T],
        properties[FRPPropertyKind.G_LT],
        properties[FRPPropertyKind.NU_LT],
    )
    result = plate_combined_compression_buckling_strength(*arguments, "0.5", _impact())
    assert result.status is PlateStrengthStatus.COMPLETE
    assert result.buckling_stress is not None
    assert result.buckling_nominal_strength is not None
    assert result.design_strength_reference is not None
    assert _stress(result.buckling_stress) == Decimal(
        _expected("G13_COMBINED_COMPRESSION_BUCKLING_STRESS", "ksi")
    )
    assert _line_strength(result.buckling_nominal_strength) == Decimal(
        _expected("G14_COMBINED_COMPRESSION_BUCKLING_NOMINAL", "kip_per_in")
    )
    assert _line_strength(result.design_strength_reference) == Decimal(
        _expected("G15_COMBINED_COMPRESSION_BUCKLING_DESIGN_REFERENCE", "kip_per_in")
    )
    for benchmark_id in (
        "G16_COMBINED_COMPRESSION_XI_LOW_REJECT",
        "G17_COMBINED_COMPRESSION_XI_HIGH_REJECT",
    ):
        input_data = _benchmark(benchmark_id)["input"]
        assert isinstance(input_data, MappingProxyType)
        xi = input_data["xi_LT"]
        assert isinstance(xi, str)
        rejected = plate_combined_compression_buckling_strength(*arguments, xi, _impact())
        assert rejected.status.value == _expected(benchmark_id, "status")
        assert rejected.buckling_stress is None
        assert rejected.buckling_nominal_strength is None
        assert rejected.design_strength_reference is None


def test_shear_g18_through_g25_is_exact_for_both_branches() -> None:
    result = _shear(_fixture())
    assert result.eta_lt == Decimal(_expected("G18_SHEAR_ETA_LE1", "eta_LT"))
    assert result.eta_branch.value == _expected("G18_SHEAR_ETA_LE1", "branch")
    assert _stress(result.buckling_stress) == Decimal(
        _expected("G19_SHEAR_BUCKLING_STRESS_LE1", "ksi")
    )
    assert _line_strength(result.buckling_nominal_strength) == Decimal(
        _expected("G20_SHEAR_BUCKLING_NOMINAL", "kip_per_in")
    )
    assert _line_strength(result.rupture_nominal_strength) == Decimal(
        _expected("G21_SHEAR_RUPTURE_NOMINAL", "kip_per_in")
    )
    assert result.governing_mode.value == _expected("G22_SHEAR_GOVERNING", "mode")
    assert _line_strength(result.design_strength) == Decimal(
        _expected("G23_SHEAR_DESIGN", "kip_per_in")
    )
    high_eta = _shear(_fixture(shear_modulus="1000"))
    assert high_eta.eta_lt == Decimal(_expected("G24_SHEAR_ETA_GT1", "eta_LT"))
    assert high_eta.eta_branch.value == _expected("G24_SHEAR_ETA_GT1", "branch")
    assert _stress(high_eta.buckling_stress) == Decimal(
        _expected("G25_SHEAR_BUCKLING_STRESS_GT1", "ksi")
    )
    assert result.resistance_factor == PLATE_SHEAR_PHI
    assert not result.property_adjustment_applied_by_engine


def test_locked_factors_single_adjustment_and_commentary_g26_through_g31() -> None:
    properties = _fixture()
    live = select_time_effect_factor(TimeEffectCategory.OTHER_LIVE)
    tension = plate_longitudinal_tension_strength(
        _quantity("0.5", Unit.IN), properties[FRPPropertyKind.FT_L], live
    )
    assert tension.design_strength == tension.nominal_strength * Decimal("0.52")
    assert tension.adjusted_property is properties[FRPPropertyKind.FT_L]
    narrow = _compression(properties, transverse_span="8")
    assert narrow.b_over_t == Decimal(_expected("G29_NARROW_PLATE_CAUTION", "b_over_t"))
    assert _stress(narrow.buckling_stress) == Decimal(
        _expected("G29_NARROW_PLATE_CAUTION", "FcrL_ksi")
    )
    assert PlateStrengthAdvisory.NARROW_PLATE in narrow.advisories
    assert PlateStrengthAdvisory.SHORT_COMPRESSION_PLATE in narrow.advisories
    shear = _shear(properties, longitudinal_span="6")
    assert shear.advisories == (PlateStrengthAdvisory.SHORT_SHEAR_PLATE,)
    no_advisory = _compression(properties, longitudinal_span=None)
    assert no_advisory.advisories == ()
    shear_no_span = _shear(properties, longitudinal_span=None)
    assert shear_no_span.advisories == ()


def test_governing_selection_and_eta_exactly_one_have_no_tolerance_switch() -> None:
    properties = _fixture()
    rupture_governs = _compression(properties, transverse_span="1", longitudinal_span="8")
    assert rupture_governs.governing_mode is PlateGoverningMode.MATERIAL_RUPTURE
    high_shear = dict(properties)
    high_shear[FRPPropertyKind.FSH_LT] = _trace(FRPPropertyKind.FSH_LT, "100", Unit.KSI)
    buckling_governs = _shear(high_shear)
    assert buckling_governs.governing_mode is PlateGoverningMode.ORTHOTROPIC_SHEAR_BUCKLING
    eta_one = dict(properties)
    eta_one[FRPPropertyKind.ET_L] = _trace(FRPPropertyKind.ET_L, "1", Unit.KSI)
    eta_one[FRPPropertyKind.ET_T] = _trace(FRPPropertyKind.ET_T, "1", Unit.KSI)
    eta_one[FRPPropertyKind.G_LT] = _trace(FRPPropertyKind.G_LT, "0.5", Unit.KSI)
    eta_one[FRPPropertyKind.NU_LT] = _trace(FRPPropertyKind.NU_LT, "0", Unit.ONE)
    result = _shear(eta_one)
    assert result.eta_lt == Decimal(1)
    assert result.eta_branch is ShearEtaBranch.ZERO_LT_ETA_LE_ONE


def test_transverse_compression_does_not_invent_stability() -> None:
    property_trace = _fixture()[FRPPropertyKind.FC_T]
    complete = plate_transverse_compression_rupture_reference(
        _quantity("0.5", Unit.IN), property_trace, _impact()
    )
    rupture_only = plate_transverse_compression_rupture_reference(
        _quantity("0.5", Unit.IN),
        property_trace,
        _impact(),
        complete_stability_requested=False,
    )
    assert complete.complete_stability_status is PlateStrengthStatus.REQUIRES_SECTION_2_3_2
    assert rupture_only.complete_stability_status is PlateStrengthStatus.COMPLETE
    assert rupture_only.method is PlateStrengthMethod.TRANSVERSE_COMPRESSION_RUPTURE
    with pytest.raises(TypeError, match="must be Boolean"):
        plate_transverse_compression_rupture_reference(
            _quantity("0.5", Unit.IN),
            property_trace,
            _impact(),
            complete_stability_requested=1,  # type: ignore[arg-type]
        )


def test_g32_through_g35_and_input_contract_fail_closed() -> None:
    properties = _fixture()
    with pytest.raises(ValueError, match="thickness must be positive"):
        _compression(properties, thickness="0")
    with pytest.raises(ValueError, match="transverse_span must be positive"):
        _compression(properties, transverse_span="0")
    with pytest.raises(ValueError, match="longitudinal_span must be positive"):
        _compression(properties, longitudinal_span="0")
    with pytest.raises(ValueError, match="effective_net_area_per_unit_width must be nonnegative"):
        plate_longitudinal_tension_strength(
            _quantity("-0.1", Unit.IN), properties[FRPPropertyKind.FT_L], _impact()
        )
    zero_area = plate_longitudinal_tension_strength(
        _quantity("0", Unit.IN), properties[FRPPropertyKind.FT_L], _impact()
    )
    assert zero_area.nominal_strength.magnitude == 0
    invalid_modulus = dict(properties)
    invalid_modulus[FRPPropertyKind.ET_L] = _trace(FRPPropertyKind.ET_L, "0", Unit.KSI)
    with pytest.raises(ValueError, match="ET_L must be positive"):
        _compression(invalid_modulus)
    with pytest.raises(ValueError, match="strictly positive"):
        TimeEffectFactor(TimeEffectCategory.IMPACT, Decimal(0), "test")
    with pytest.raises(TypeError, match="must be a length quantity"):
        plate_longitudinal_tension_strength(
            _quantity("1", Unit.KSI),
            properties[FRPPropertyKind.FT_L],
            _impact(),
        )
    with pytest.raises(TypeError, match="adjusted EndUsePropertyTrace"):
        plate_longitudinal_tension_strength(
            _quantity("0.5", Unit.IN),
            object(),  # type: ignore[arg-type]
            _impact(),
        )
    with pytest.raises(ValueError, match="Expected adjusted property FT_L"):
        plate_longitudinal_tension_strength(
            _quantity("0.5", Unit.IN), properties[FRPPropertyKind.FC_L], _impact()
        )
    wrong_dimension = replace(
        properties[FRPPropertyKind.FT_L], adjusted_property=_quantity("1", Unit.IN)
    )
    with pytest.raises(ValueError, match="must have dimension STRESS"):
        plate_longitudinal_tension_strength(_quantity("0.5", Unit.IN), wrong_dimension, _impact())
    for nu_value in ("-0.1", "1"):
        invalid_nu = dict(properties)
        invalid_nu[FRPPropertyKind.NU_LT] = _trace(FRPPropertyKind.NU_LT, nu_value, Unit.ONE)
        with pytest.raises(ValueError, match="nonnegative and less than one"):
            _compression(invalid_nu)
    with pytest.raises(TypeError, match="must be a TimeEffectFactor"):
        plate_longitudinal_tension_strength(
            _quantity("0.5", Unit.IN),
            properties[FRPPropertyKind.FT_L],
            object(),  # type: ignore[arg-type]
        )
    invalid_time = object.__new__(TimeEffectFactor)
    object.__setattr__(invalid_time, "category", TimeEffectCategory.IMPACT)
    object.__setattr__(invalid_time, "value", Decimal(0))
    object.__setattr__(invalid_time, "source_reference", "coverage")
    object.__setattr__(invalid_time, "notes", ())
    object.__setattr__(invalid_time, "approved_override_id", None)
    with pytest.raises(ValueError, match="lambda_time must be positive"):
        plate_longitudinal_tension_strength(
            _quantity("0.5", Unit.IN), properties[FRPPropertyKind.FT_L], invalid_time
        )
    with pytest.raises(TypeError, match="Decimal, int, or a decimal string"):
        plate_combined_compression_buckling_strength(
            _quantity("0.5", Unit.IN),
            _quantity("24", Unit.IN),
            _quantity("12", Unit.IN),
            properties[FRPPropertyKind.ET_L],
            properties[FRPPropertyKind.ET_T],
            properties[FRPPropertyKind.G_LT],
            properties[FRPPropertyKind.NU_LT],
            True,
            _impact(),
        )


def test_g36_us_si_equivalence_and_force_per_length_units_are_exact() -> None:
    us = _fixture()
    si = {
        kind: replace(
            trace,
            source_property=trace.source_property.to(
                Unit.ONE if trace.source_property.dimension is Dimension.DIMENSIONLESS else Unit.MPA
            ),
            adjusted_property=trace.adjusted_property.to(
                Unit.ONE
                if trace.adjusted_property.dimension is Dimension.DIMENSIONLESS
                else Unit.MPA
            ),
        )
        for kind, trace in us.items()
    }
    us_result = _compression(us)
    si_result = plate_longitudinal_compression_strength(
        _quantity("12.7", Unit.MM),
        _quantity("304.8", Unit.MM),
        si[FRPPropertyKind.FC_L],
        si[FRPPropertyKind.ET_L],
        si[FRPPropertyKind.ET_T],
        si[FRPPropertyKind.G_LT],
        si[FRPPropertyKind.NU_LT],
        _impact(),
        longitudinal_span=_quantity("609.6", Unit.MM),
    )
    assert us_result.nominal_strength == si_result.nominal_strength
    assert us_result.design_strength == si_result.design_strength
    assert us_result.buckling_stress == si_result.buckling_stress
    assert us_result.governing_mode is si_result.governing_mode
    assert us_result.advisories == si_result.advisories
    assert us_result.result_fingerprint == si_result.result_fingerprint
    line_load = _quantity("1", Unit.KIP_PER_IN)
    assert line_load.dimension is Dimension.FORCE_PER_LENGTH
    assert line_load.to(Unit.N_PER_MM).to(Unit.KIP_PER_IN) == line_load


def test_g37_fingerprints_include_method_and_provenance_but_not_presentation() -> None:
    properties = _fixture()
    baseline = plate_longitudinal_tension_strength(
        _quantity("0.5", Unit.IN), properties[FRPPropertyKind.FT_L], _impact()
    )
    si = plate_longitudinal_tension_strength(
        _quantity("12.7", Unit.MM),
        replace(
            properties[FRPPropertyKind.FT_L],
            source_property=properties[FRPPropertyKind.FT_L].source_property.to(Unit.MPA),
            adjusted_property=properties[FRPPropertyKind.FT_L].adjusted_property.to(Unit.MPA),
        ),
        _impact(),
    )
    changed_provenance = plate_longitudinal_tension_strength(
        _quantity("0.5", Unit.IN),
        replace(properties[FRPPropertyKind.FT_L], cm=Decimal("0.99")),
        _impact(),
    )
    transverse = plate_transverse_tension_strength(
        _quantity("0.5", Unit.IN), properties[FRPPropertyKind.FT_T], _impact()
    )
    assert baseline.result_fingerprint == si.result_fingerprint
    assert baseline.result_fingerprint != changed_provenance.result_fingerprint
    assert baseline.result_fingerprint != transverse.result_fingerprint
    assert len(baseline.result_fingerprint) == 64


def test_source_provenance_and_production_golden_access_boundary() -> None:
    source = asce_74_23_chapter_7_source(section="7.5.2")
    assert source.chapter == "7"
    assert source.section == "7.5.2"
    assert source.equation_reference is None
    assert not source.chapter_affected_by_errata
    assert source.errata_effective_date == date(2026, 1, 13)
    production_source = inspect.getsource(
        __import__("frp_master_connection.calculation.plate_strength", fromlist=["plate_strength"])
    )
    assert "golden" not in production_source.casefold()
    assert "adjust_frp_property" not in production_source


def test_g38_through_g40_lock_historical_regression_expectations() -> None:
    for benchmark_id in (
        "G38_STAGE_3_6A_REGRESSION",
        "G39_STAGE_3_5_FREEZE_REGRESSION",
        "G40_EARLIER_FREEZE_REGRESSIONS",
    ):
        expected = _benchmark(benchmark_id)["expected"]
        assert isinstance(expected, MappingProxyType)
        assert set(expected.values()) <= {
            "NONE",
        }
