"""Exact W/I member-end action decomposition into physical region resultants.

Calculation Slice 5 is an internal demand-only prerequisite.  It deliberately has
no API or product-workspace binding and returns no connection resistance result.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from datetime import date
from decimal import Decimal, localcontext
from enum import Enum, StrEnum

from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    Unit,
    canonical_decimal_string,
)
from frp_master_connection.calculation.sources import (
    ASCE_74_23_EDITION,
    ASCE_74_23_ERRATUM,
    ASCE_74_23_ERRATUM_EFFECTIVE_DATE,
    ASCE_74_23_STANDARD_NAME,
    CalculationSourceSnapshot,
    QualificationStatus,
    SourceClassification,
)
from frp_master_connection.domain.member_profile import WideFlangeIProfileDimensions

WI_MOMENT_DECIMAL_PRECISION = 80
WI_MOMENT_CALCULATION_CONTRACT_VERSION = "CS5-RC1"
WI_MOMENT_METHOD_ID = "RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1"
WI_MOMENT_ENGINE_VERSION = "CALCULATION_SLICE_5_RC1"
WI_MOMENT_FINGERPRINT_SCHEMA_VERSION = "CS5-FP-RC1"
WI_MOMENT_RESULT_SCHEMA_VERSION = "CS5-RESULT-RC1"
WI_MOMENT_DISCLAIMER_ID = "WI_MOMENT_COMPONENT_RESULTANT_DECOMPOSITION_DISCLAIMER_RC1"
WI_MOMENT_DISCLAIMER = (
    "The top-flange, web, and bottom-flange forces and local moments are derived from "
    "a project-controlled linear-elastic integration of the accepted idealized W/I "
    "section. The decomposition preserves exact member-end axial-force, shear, and "
    "major-moment equilibrium, including web moment participation, but is not a direct "
    "ASCE/SEI 74-23 connection-detail equation. The engineer of record shall review the "
    "section idealization, structural-analysis assumptions, component stiffness "
    "compatibility, and Section 2.3.2 qualification requirements for the final moment "
    "connection."
)

WI_MOMENT_DECISION_SHA256 = "1E3DFA8727953087C883F5E8627778960CBD6AFECCDC357A35C89D99A6139DC9"
WI_MOMENT_SPECIFICATION_SHA256 = "33C88001777BD11CAF1EE724B5F2EFFCB84D9C0232578091755FA9751BEB49B1"
WI_MOMENT_GOLDEN_SHA256 = "8854FE7CB56B7D7CEE1FF30A5EA554B83D400386FAE4B1AFDCABC8DF7A1E3D82"
WI_MOMENT_LEDGER_SHA256 = "246EC10341A1E4011069231C296B6CCA1346DACC74455F42EFAD3C0C98937DA9"
WI_MOMENT_ORDER_SHA256 = "27E3B713F358CFBB1B27A15F3745A7FF6D263FEF0F87AC4534062723F9B60755"
WI_MOMENT_ASCE_SOURCE_SHA256 = "A7127E37572D5D625C5F338FFB9A1D2D53F396897AFB26E0B4698A0131FE65BC"
WI_MOMENT_ERRATUM_SOURCE_SHA256 = "5B58E842DA9025934D12EB386C416E94CB3B53999B21F59B0606F2B09D9DE550"

_ZERO = Decimal(0)
_TWO = Decimal(2)
_TWELVE = Decimal(12)


class WIMomentMethod(StrEnum):
    """Closed method vocabulary for Calculation Slice 5 RC1."""

    RATIONAL_ELASTIC_REGION_RESULTANTS = WI_MOMENT_METHOD_ID


class WIMomentRegionId(StrEnum):
    TOP_FLANGE = "TOP_FLANGE"
    WEB = "WEB"
    BOTTOM_FLANGE = "BOTTOM_FLANGE"


class WIMomentRegionForceState(StrEnum):
    TENSION = "TENSION"
    COMPRESSION = "COMPRESSION"
    ZERO_FORCE = "ZERO_FORCE"


class WIMomentInputStatus(StrEnum):
    REJECTED = "REJECTED"


class WIMomentRejectionReason(StrEnum):
    UNSUPPORTED_CONTRACT_VERSION = "UNSUPPORTED_CALCULATION_CONTRACT_VERSION"
    MINOR_SHEAR_NOT_SUPPORTED = "MINOR_SHEAR_NOT_SUPPORTED_IN_CS5_RC1"
    MINOR_AXIS_MOMENT_NOT_SUPPORTED = "MINOR_AXIS_MOMENT_NOT_SUPPORTED_IN_CS5_RC1"
    TORSION_NOT_SUPPORTED = "TORSION_NOT_SUPPORTED_IN_CS5_RC1"
    POSITIVE_DIMENSIONS_REQUIRED = "POSITIVE_WI_DIMENSIONS_REQUIRED"
    POSITIVE_WEB_HEIGHT_REQUIRED = "POSITIVE_WEB_HEIGHT_REQUIRED"
    FLANGE_WIDTH_MUST_EXCEED_WEB_THICKNESS = "FLANGE_WIDTH_MUST_EXCEED_WEB_THICKNESS"


class WIMomentInputRejected(ValueError):
    """Controlled fail-closed rejection with stable status and reason strings."""

    status = WIMomentInputStatus.REJECTED

    def __init__(self, reason: WIMomentRejectionReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True, slots=True)
class WIMomentSectionInput:
    d: PhysicalQuantity
    b_f: PhysicalQuantity
    t_w: PhysicalQuantity
    t_f: PhysicalQuantity

    def __post_init__(self) -> None:
        for name in ("d", "b_f", "t_w", "t_f"):
            value = getattr(self, name)
            if not isinstance(value, PhysicalQuantity):
                raise TypeError(f"WIMomentSectionInput.{name} must be a PhysicalQuantity.")
            if value.dimension is not Dimension.LENGTH:
                raise ValueError(f"WIMomentSectionInput.{name} must be a length.")


@dataclass(frozen=True, slots=True)
class WIMomentActionInput:
    axial_force_l: PhysicalQuantity
    major_shear_v: PhysicalQuantity
    major_moment_t: PhysicalQuantity
    minor_shear_t: PhysicalQuantity
    minor_moment_v: PhysicalQuantity
    torsion_l: PhysicalQuantity

    def __post_init__(self) -> None:
        for name in ("axial_force_l", "major_shear_v", "minor_shear_t"):
            value = getattr(self, name)
            if not isinstance(value, PhysicalQuantity):
                raise TypeError(f"WIMomentActionInput.{name} must be a PhysicalQuantity.")
            if value.dimension is not Dimension.FORCE:
                raise ValueError(f"WIMomentActionInput.{name} must be a force.")
        for name in ("major_moment_t", "minor_moment_v", "torsion_l"):
            value = getattr(self, name)
            if not isinstance(value, PhysicalQuantity):
                raise TypeError(f"WIMomentActionInput.{name} must be a PhysicalQuantity.")
            if value.dimension is not Dimension.MOMENT:
                raise ValueError(f"WIMomentActionInput.{name} must be a moment.")


@dataclass(frozen=True, slots=True)
class WIMomentCalculationInput:
    geometry: WIMomentSectionInput
    actions: WIMomentActionInput
    contract_version: str = WI_MOMENT_CALCULATION_CONTRACT_VERSION
    method: WIMomentMethod = WIMomentMethod.RATIONAL_ELASTIC_REGION_RESULTANTS

    def __post_init__(self) -> None:
        if not isinstance(self.geometry, WIMomentSectionInput):
            raise TypeError("geometry must be a WIMomentSectionInput.")
        if not isinstance(self.actions, WIMomentActionInput):
            raise TypeError("actions must be a WIMomentActionInput.")
        if not isinstance(self.contract_version, str):
            raise TypeError("contract_version must be text.")
        if self.contract_version != WI_MOMENT_CALCULATION_CONTRACT_VERSION:
            raise WIMomentInputRejected(WIMomentRejectionReason.UNSUPPORTED_CONTRACT_VERSION)
        if not isinstance(self.method, WIMomentMethod):
            raise TypeError("method must be a WIMomentMethod.")


@dataclass(frozen=True, slots=True)
class WIMomentFingerprintEnvelope:
    calculation_input: WIMomentCalculationInput
    display_unit_profile: str | None = None
    display_rounding: str | None = None
    camera_state: object | None = None
    ui_selection: object | None = None
    request_timestamp: str | None = None


@dataclass(frozen=True, slots=True)
class BeamQuantityVector:
    """Immutable quantity vector ordered on the controlled L_B/V_B/T_B basis."""

    l: PhysicalQuantity  # noqa: E741 - controlled longitudinal axis name
    v: PhysicalQuantity
    t: PhysicalQuantity

    def __post_init__(self) -> None:
        if any(not isinstance(item, PhysicalQuantity) for item in (self.l, self.v, self.t)):
            raise TypeError("BeamQuantityVector components must be PhysicalQuantity values.")
        if len({self.l.dimension, self.v.dimension, self.t.dimension}) != 1:
            raise ValueError("BeamQuantityVector components must share one dimension.")


@dataclass(frozen=True, slots=True)
class WIMomentSectionProperties:
    web_height: PhysicalQuantity
    flange_area: PhysicalQuantity
    web_area: PhysicalQuantity
    total_area: PhysicalQuantity
    top_centroid_v: PhysicalQuantity
    web_centroid_v: PhysicalQuantity
    bottom_centroid_v: PhysicalQuantity
    flange_centroidal_inertia: PhysicalQuantity
    web_centroidal_inertia: PhysicalQuantity
    total_major_inertia: PhysicalQuantity


@dataclass(frozen=True, slots=True)
class WIMomentStressExtrema:
    region_id: WIMomentRegionId
    first_boundary_id: str
    first_position_v: PhysicalQuantity
    first_stress_l: PhysicalQuantity
    second_boundary_id: str
    second_position_v: PhysicalQuantity
    second_stress_l: PhysicalQuantity
    crosses_zero: bool


@dataclass(frozen=True, slots=True)
class WIMomentComponentWrench:
    reference_lvt: BeamQuantityVector
    force_lvt: BeamQuantityVector
    moment_lvt: BeamQuantityVector
    provenance: str


@dataclass(frozen=True, slots=True)
class WIMomentComponentResult:
    region_id: WIMomentRegionId
    area: PhysicalQuantity
    centroid_v: PhysicalQuantity
    centroidal_inertia: PhysicalQuantity
    wrench: WIMomentComponentWrench
    global_major_moment: PhysicalQuantity
    stress_extrema: WIMomentStressExtrema
    force_state: WIMomentRegionForceState


@dataclass(frozen=True, slots=True)
class WIMomentEquilibriumTrace:
    summed_axial_force: PhysicalQuantity
    target_axial_force: PhysicalQuantity
    summed_major_shear: PhysicalQuantity
    target_major_shear: PhysicalQuantity
    summed_major_moment: PhysicalQuantity
    target_major_moment: PhysicalQuantity
    exact_axial_balance_numerator: Decimal
    exact_shear_residual: Decimal
    exact_moment_balance_numerator: Decimal
    axial_equilibrium_exact: bool
    shear_equilibrium_exact: bool
    moment_equilibrium_exact: bool
    unsupported_components_zero: bool


@dataclass(frozen=True, slots=True)
class WIMomentCoupleDiagnostics:
    flange_lever_arm: PhysicalQuantity
    exact_flange_couple_force: PhysicalQuantity
    exact_flange_couple_moment: PhysicalQuantity
    full_moment_over_z_reference_force: PhysicalQuantity
    full_moment_over_z_is_controlling: bool
    residual_moment: PhysicalQuantity
    local_and_web_moment_sum: PhysicalQuantity
    residual_identity_exact: bool


@dataclass(frozen=True, slots=True)
class WIMomentSourceProvenance:
    code_sources: tuple[CalculationSourceSnapshot, ...]
    controlled_artifact_hashes: tuple[tuple[str, str], ...]
    authoritative_source_hashes: tuple[tuple[str, str], ...]
    rational_method_classification: SourceClassification
    qualification_statuses: tuple[QualificationStatus, ...]
    erratum_changes_targeted_provisions: bool
    direct_asce_equation_claimed: bool


@dataclass(frozen=True, slots=True)
class WIMomentVersionContext:
    contract_version: str
    method_id: str
    engine_version: str
    fingerprint_schema_version: str
    result_schema_version: str


@dataclass(frozen=True, slots=True)
class WIMomentComponentResultants:
    versions: WIMomentVersionContext
    calculation_input: WIMomentCalculationInput
    section_properties: WIMomentSectionProperties
    components: tuple[WIMomentComponentResult, ...]
    equilibrium: WIMomentEquilibriumTrace
    couple_diagnostics: WIMomentCoupleDiagnostics
    source_provenance: WIMomentSourceProvenance
    rational_method_engineering_review_required: bool
    disclaimer_id: str
    disclaimer: str
    input_fingerprint: str
    result_fingerprint: str

    def component(self, region_id: WIMomentRegionId) -> WIMomentComponentResult:
        """Resolve one physical region by its stable identity."""

        if not isinstance(region_id, WIMomentRegionId):
            raise TypeError("region_id must be a WIMomentRegionId.")
        return next(item for item in self.components if item.region_id is region_id)


def _source(section: str, chapter: str) -> CalculationSourceSnapshot:
    return CalculationSourceSnapshot(
        standard_name=ASCE_74_23_STANDARD_NAME,
        edition=ASCE_74_23_EDITION,
        chapter=chapter,
        section=section,
        equation_reference=None,
        errata_identifier=ASCE_74_23_ERRATUM,
        errata_effective_date=ASCE_74_23_ERRATUM_EFFECTIVE_DATE,
        chapter_affected_by_errata=False,
        interpretation_id=None,
        source_classification=SourceClassification.CODE_CHARACTERISTIC,
        source_revision="CALCULATION_SLICE_5_RC1_VERIFIED_2026-08-31",
    )


WI_MOMENT_SOURCE_PROVENANCE = WIMomentSourceProvenance(
    code_sources=(
        _source("2.3.2", "2"),
        _source("2.9", "2"),
        _source("8.1.3", "8"),
        _source("8.3.4.2", "8"),
        _source("C2.9", "Commentary"),
        _source("C8.1.3", "Commentary"),
        _source("C8.3.4", "Commentary"),
    ),
    controlled_artifact_hashes=(
        ("decision", WI_MOMENT_DECISION_SHA256),
        ("engineering_specification_rc1", WI_MOMENT_SPECIFICATION_SHA256),
        ("golden_benchmarks_rc1", WI_MOMENT_GOLDEN_SHA256),
        ("authority_ledger_rc1", WI_MOMENT_LEDGER_SHA256),
        ("codex_order", WI_MOMENT_ORDER_SHA256),
    ),
    authoritative_source_hashes=(
        ("ASCE_SEI_74_23", WI_MOMENT_ASCE_SOURCE_SHA256),
        ("ERRATUM_1_EFFECTIVE_2026_01_13", WI_MOMENT_ERRATUM_SOURCE_SHA256),
    ),
    rational_method_classification=SourceClassification.ENGINEER_APPROVED_DEVELOPMENT,
    qualification_statuses=(
        QualificationStatus.ENGINEERING_REVIEW_REQUIRED,
        QualificationStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
    ),
    erratum_changes_targeted_provisions=False,
    direct_asce_equation_claimed=False,
)


def _canonicalize(value: object) -> object:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return value
    if isinstance(value, PhysicalQuantity):
        return {
            "dimension": value.dimension.value,
            "unit": value.canonical_unit.value,
            "value": value.canonical_string,
        }
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        raise TypeError("Raw floating-point values are prohibited in Slice 5 fingerprints.")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("Slice 5 fingerprint mapping keys must be text.")
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _canonicalize(getattr(value, field.name)) for field in fields(value)}
    raise TypeError(f"Unsupported Slice 5 fingerprint value: {type(value).__name__}.")


def _calculation_input_payload(value: WIMomentCalculationInput) -> dict[str, object]:
    return {
        "versions": WIMomentVersionContext(
            value.contract_version,
            value.method.value,
            WI_MOMENT_ENGINE_VERSION,
            WI_MOMENT_FINGERPRINT_SCHEMA_VERSION,
            WI_MOMENT_RESULT_SCHEMA_VERSION,
        ),
        "frame": {
            "axes": ("L_B", "V_B", "T_B"),
            "handedness": "L_B_x_V_B_equals_T_B",
            "positive_axial": "TENSION",
            "positive_major_moment": "TENSION_AT_POSITIVE_V_B",
        },
        "geometry": value.geometry,
        "actions": value.actions,
        "component_references": (
            ("TOP_FLANGE", "0", "+(d-t_f)/2", "0"),
            ("WEB", "0", "0", "0"),
            ("BOTTOM_FLANGE", "0", "-(d-t_f)/2", "0"),
        ),
        "source_provenance": WI_MOMENT_SOURCE_PROVENANCE,
    }


def canonical_wi_moment_input_json(
    value: WIMomentCalculationInput | WIMomentFingerprintEnvelope,
) -> str:
    """Return the unit-independent canonical JSON used by the Slice 5 digest."""

    calculation_input = (
        value.calculation_input if isinstance(value, WIMomentFingerprintEnvelope) else value
    )
    if not isinstance(calculation_input, WIMomentCalculationInput):
        raise TypeError("Slice 5 fingerprinting requires a calculation input or envelope.")
    payload = _canonicalize(_calculation_input_payload(calculation_input))
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def wi_moment_input_fingerprint(
    value: WIMomentCalculationInput | WIMomentFingerprintEnvelope,
) -> str:
    return hashlib.sha256(canonical_wi_moment_input_json(value).encode("utf-8")).hexdigest()


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        _canonicalize(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _quantity(value: Decimal, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def _vector(values: tuple[Decimal, Decimal, Decimal], unit: Unit) -> BeamQuantityVector:
    return BeamQuantityVector(*(_quantity(value, unit) for value in values))


def _force_state(value: Decimal) -> WIMomentRegionForceState:
    if value > 0:
        return WIMomentRegionForceState.TENSION
    if value < 0:
        return WIMomentRegionForceState.COMPRESSION
    return WIMomentRegionForceState.ZERO_FORCE


def _crosses_zero(first: Decimal, second: Decimal) -> bool:
    return min(first, second) <= 0 <= max(first, second)


def _validate_supported_actions(actions: WIMomentActionInput) -> None:
    if actions.minor_shear_t.canonical_magnitude != 0:
        raise WIMomentInputRejected(WIMomentRejectionReason.MINOR_SHEAR_NOT_SUPPORTED)
    if actions.minor_moment_v.canonical_magnitude != 0:
        raise WIMomentInputRejected(WIMomentRejectionReason.MINOR_AXIS_MOMENT_NOT_SUPPORTED)
    if actions.torsion_l.canonical_magnitude != 0:
        raise WIMomentInputRejected(WIMomentRejectionReason.TORSION_NOT_SUPPORTED)


def _validated_profile_dimensions(geometry: WIMomentSectionInput) -> WideFlangeIProfileDimensions:
    d = geometry.d.to(Unit.IN).magnitude
    b_f = geometry.b_f.to(Unit.IN).magnitude
    t_w = geometry.t_w.to(Unit.IN).magnitude
    t_f = geometry.t_f.to(Unit.IN).magnitude
    if any(value <= 0 for value in (d, b_f, t_w, t_f)):
        raise WIMomentInputRejected(WIMomentRejectionReason.POSITIVE_DIMENSIONS_REQUIRED)
    try:
        return WideFlangeIProfileDimensions(d, d, b_f, t_w, t_f)
    except ValueError as error:
        if d <= _TWO * t_f:
            raise WIMomentInputRejected(
                WIMomentRejectionReason.POSITIVE_WEB_HEIGHT_REQUIRED
            ) from error
        if b_f <= t_w:
            raise WIMomentInputRejected(
                WIMomentRejectionReason.FLANGE_WIDTH_MUST_EXCEED_WEB_THICKNESS
            ) from error
        raise  # pragma: no cover - the shared W/I authority currently has no other constraint


def _stress_range(
    region_id: WIMomentRegionId,
    first_id: str,
    first_y: Decimal,
    second_id: str,
    second_y: Decimal,
    axial: Decimal,
    moment: Decimal,
    area: Decimal,
    inertia: Decimal,
) -> WIMomentStressExtrema:
    first = axial / area + moment * first_y / inertia
    second = axial / area + moment * second_y / inertia
    return WIMomentStressExtrema(
        region_id,
        first_id,
        _quantity(first_y, Unit.IN),
        _quantity(first, Unit.KSI),
        second_id,
        _quantity(second_y, Unit.IN),
        _quantity(second, Unit.KSI),
        _crosses_zero(first, second),
    )


def calculate_wi_moment_component_resultants(
    calculation_input: WIMomentCalculationInput,
) -> WIMomentComponentResultants:
    """Execute the controlled demand-only W/I region integration."""

    if not isinstance(calculation_input, WIMomentCalculationInput):
        raise TypeError("calculation_input must be a WIMomentCalculationInput.")
    _validate_supported_actions(calculation_input.actions)
    dimensions = _validated_profile_dimensions(calculation_input.geometry)
    actions = calculation_input.actions
    axial = actions.axial_force_l.to(Unit.KIP).magnitude
    shear = actions.major_shear_v.to(Unit.KIP).magnitude
    moment = actions.major_moment_t.to(Unit.KIP_IN).magnitude

    with localcontext() as context:
        context.prec = WI_MOMENT_DECIMAL_PRECISION
        depth = dimensions.depth
        flange_width = dimensions.flange_width
        web_thickness = dimensions.web_thickness
        flange_thickness = dimensions.flange_thickness
        web_height = depth - _TWO * flange_thickness
        flange_area = flange_width * flange_thickness
        web_area = web_thickness * web_height
        total_area = _TWO * flange_area + web_area
        top_y = (depth - flange_thickness) / _TWO
        web_y = _ZERO
        bottom_y = -top_y

        flange_inertia_numerator = flange_width * flange_thickness**3
        web_inertia_numerator = web_thickness * web_height**3
        flange_inertia = flange_inertia_numerator / _TWELVE
        web_inertia = web_inertia_numerator / _TWELVE
        total_inertia_numerator = (
            _TWO * (flange_inertia_numerator + _TWELVE * flange_area * top_y**2)
            + web_inertia_numerator
        )
        total_inertia = total_inertia_numerator / _TWELVE

        region_areas = (flange_area, web_area, flange_area)
        region_centroids = (top_y, web_y, bottom_y)
        region_inertia_numerators = (
            flange_inertia_numerator,
            web_inertia_numerator,
            flange_inertia_numerator,
        )
        region_inertias = (flange_inertia, web_inertia, flange_inertia)
        normal_forces = tuple(
            axial * region_area / total_area + moment * region_area * centroid / total_inertia
            for region_area, centroid in zip(region_areas, region_centroids, strict=True)
        )
        local_moments = tuple(
            moment * region_inertia / total_inertia for region_inertia in region_inertias
        )
        global_moments = tuple(
            centroid * normal_force + local_moment
            for centroid, normal_force, local_moment in zip(
                region_centroids, normal_forces, local_moments, strict=True
            )
        )
        shears = (_ZERO, shear, _ZERO)

        common_normal_denominator = total_area * total_inertia_numerator
        exact_normal_numerators = tuple(
            axial * region_area * total_inertia_numerator
            + _TWELVE * moment * region_area * centroid * total_area
            for region_area, centroid in zip(region_areas, region_centroids, strict=True)
        )
        exact_moment_numerators = tuple(
            centroid * normal_numerator + moment * inertia_numerator * total_area
            for centroid, normal_numerator, inertia_numerator in zip(
                region_centroids,
                exact_normal_numerators,
                region_inertia_numerators,
                strict=True,
            )
        )
        exact_axial_balance = (
            sum(exact_normal_numerators, _ZERO) - axial * common_normal_denominator
        )
        exact_shear_residual = sum(shears, _ZERO) - shear
        exact_moment_balance = (
            sum(exact_moment_numerators, _ZERO) - moment * total_area * total_inertia_numerator
        )

        half_depth = depth / _TWO
        half_web_height = web_height / _TWO
        stress_ranges = (
            _stress_range(
                WIMomentRegionId.TOP_FLANGE,
                "INNER_FACE",
                half_depth - flange_thickness,
                "OUTER_FACE",
                half_depth,
                axial,
                moment,
                total_area,
                total_inertia,
            ),
            _stress_range(
                WIMomentRegionId.WEB,
                "BOTTOM_WEB_EDGE",
                -half_web_height,
                "TOP_WEB_EDGE",
                half_web_height,
                axial,
                moment,
                total_area,
                total_inertia,
            ),
            _stress_range(
                WIMomentRegionId.BOTTOM_FLANGE,
                "OUTER_FACE",
                -half_depth,
                "INNER_FACE",
                -half_depth + flange_thickness,
                axial,
                moment,
                total_area,
                total_inertia,
            ),
        )

        region_ids = (
            WIMomentRegionId.TOP_FLANGE,
            WIMomentRegionId.WEB,
            WIMomentRegionId.BOTTOM_FLANGE,
        )
        components = tuple(
            WIMomentComponentResult(
                region_id,
                _quantity(region_area, Unit.IN2),
                _quantity(centroid, Unit.IN),
                _quantity(region_inertia, Unit.IN4),
                WIMomentComponentWrench(
                    _vector((_ZERO, centroid, _ZERO), Unit.IN),
                    _vector((normal_force, assigned_shear, _ZERO), Unit.KIP),
                    _vector((_ZERO, _ZERO, local_moment), Unit.KIP_IN),
                    f"{WI_MOMENT_METHOD_ID}:{region_id.value}:REGION_CENTROID",
                ),
                _quantity(global_moment, Unit.KIP_IN),
                stress_range,
                _force_state(normal_force),
            )
            for (
                region_id,
                region_area,
                centroid,
                region_inertia,
                normal_force,
                assigned_shear,
                local_moment,
                global_moment,
                stress_range,
            ) in zip(
                region_ids,
                region_areas,
                region_centroids,
                region_inertias,
                normal_forces,
                shears,
                local_moments,
                global_moments,
                stress_ranges,
                strict=True,
            )
        )

        summed_axial = sum(normal_forces, _ZERO)
        summed_shear = sum(shears, _ZERO)
        summed_moment = sum(global_moments, _ZERO)
        equilibrium = WIMomentEquilibriumTrace(
            _quantity(summed_axial, Unit.KIP),
            _quantity(axial, Unit.KIP),
            _quantity(summed_shear, Unit.KIP),
            _quantity(shear, Unit.KIP),
            _quantity(summed_moment, Unit.KIP_IN),
            _quantity(moment, Unit.KIP_IN),
            exact_axial_balance,
            exact_shear_residual,
            exact_moment_balance,
            exact_axial_balance == 0,
            exact_shear_residual == 0,
            exact_moment_balance == 0,
            True,
        )

        flange_lever_arm = top_y - bottom_y
        flange_couple_force = (normal_forces[0] - normal_forces[2]) / _TWO
        flange_couple_moment = flange_couple_force * flange_lever_arm
        full_moment_reference = moment / flange_lever_arm
        residual_moment = moment - flange_couple_moment
        local_and_web_sum = local_moments[0] + global_moments[1] + local_moments[2]
        diagnostics = WIMomentCoupleDiagnostics(
            _quantity(flange_lever_arm, Unit.IN),
            _quantity(flange_couple_force, Unit.KIP),
            _quantity(flange_couple_moment, Unit.KIP_IN),
            _quantity(full_moment_reference, Unit.KIP),
            False,
            _quantity(residual_moment, Unit.KIP_IN),
            _quantity(local_and_web_sum, Unit.KIP_IN),
            residual_moment == local_and_web_sum,
        )

        properties = WIMomentSectionProperties(
            _quantity(web_height, Unit.IN),
            _quantity(flange_area, Unit.IN2),
            _quantity(web_area, Unit.IN2),
            _quantity(total_area, Unit.IN2),
            _quantity(top_y, Unit.IN),
            _quantity(web_y, Unit.IN),
            _quantity(bottom_y, Unit.IN),
            _quantity(flange_inertia, Unit.IN4),
            _quantity(web_inertia, Unit.IN4),
            _quantity(total_inertia, Unit.IN4),
        )

    versions = WIMomentVersionContext(
        calculation_input.contract_version,
        calculation_input.method.value,
        WI_MOMENT_ENGINE_VERSION,
        WI_MOMENT_FINGERPRINT_SCHEMA_VERSION,
        WI_MOMENT_RESULT_SCHEMA_VERSION,
    )
    input_fingerprint = wi_moment_input_fingerprint(calculation_input)
    result_payload = {
        "versions": versions,
        "calculation_input": _calculation_input_payload(calculation_input),
        "section_properties": properties,
        "components": components,
        "equilibrium": equilibrium,
        "couple_diagnostics": diagnostics,
        "source_provenance": WI_MOMENT_SOURCE_PROVENANCE,
        "review_required": True,
        "disclaimer_id": WI_MOMENT_DISCLAIMER_ID,
        "disclaimer": WI_MOMENT_DISCLAIMER,
        "input_fingerprint": input_fingerprint,
    }
    result_fingerprint = _fingerprint(result_payload)
    return WIMomentComponentResultants(
        versions,
        calculation_input,
        properties,
        components,
        equilibrium,
        diagnostics,
        WI_MOMENT_SOURCE_PROVENANCE,
        True,
        WI_MOMENT_DISCLAIMER_ID,
        WI_MOMENT_DISCLAIMER,
        input_fingerprint,
        result_fingerprint,
    )


__all__ = (
    "WI_MOMENT_ASCE_SOURCE_SHA256",
    "WI_MOMENT_CALCULATION_CONTRACT_VERSION",
    "WI_MOMENT_DECIMAL_PRECISION",
    "WI_MOMENT_DECISION_SHA256",
    "WI_MOMENT_DISCLAIMER",
    "WI_MOMENT_DISCLAIMER_ID",
    "WI_MOMENT_ENGINE_VERSION",
    "WI_MOMENT_ERRATUM_SOURCE_SHA256",
    "WI_MOMENT_FINGERPRINT_SCHEMA_VERSION",
    "WI_MOMENT_GOLDEN_SHA256",
    "WI_MOMENT_LEDGER_SHA256",
    "WI_MOMENT_METHOD_ID",
    "WI_MOMENT_ORDER_SHA256",
    "WI_MOMENT_RESULT_SCHEMA_VERSION",
    "WI_MOMENT_SOURCE_PROVENANCE",
    "WI_MOMENT_SPECIFICATION_SHA256",
    "BeamQuantityVector",
    "WIMomentActionInput",
    "WIMomentCalculationInput",
    "WIMomentComponentResult",
    "WIMomentComponentResultants",
    "WIMomentComponentWrench",
    "WIMomentCoupleDiagnostics",
    "WIMomentEquilibriumTrace",
    "WIMomentFingerprintEnvelope",
    "WIMomentInputRejected",
    "WIMomentInputStatus",
    "WIMomentMethod",
    "WIMomentRegionForceState",
    "WIMomentRegionId",
    "WIMomentRejectionReason",
    "WIMomentSectionInput",
    "WIMomentSectionProperties",
    "WIMomentSourceProvenance",
    "WIMomentStressExtrema",
    "WIMomentVersionContext",
    "calculate_wi_moment_component_resultants",
    "canonical_wi_moment_input_json",
    "wi_moment_input_fingerprint",
)
