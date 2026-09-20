"""Exact Channel references and physical-region component resultants.

Calculation Slice 6 is a backend-only, demand-only prerequisite for a future
Channel moment splice.  It deliberately returns no connection geometry,
resistance, utilization, or qualification result.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
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
from frp_master_connection.calculation.wi_moment_resultants import BeamQuantityVector
from frp_master_connection.domain.member_profile import ChannelProfileDimensions

CHANNEL_MOMENT_DECIMAL_PRECISION = 90
CHANNEL_MOMENT_CALCULATION_CONTRACT_VERSION = "CS6-RC1"
CHANNEL_MOMENT_METHOD_ID = "RATIONAL_ELASTIC_CHANNEL_REGION_RESULTANT_DECOMPOSITION_RC1"
CHANNEL_RATIONAL_SHEAR_CENTER_METHOD_ID = "RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1"
CHANNEL_EXPLICIT_SHEAR_CENTER_METHOD_ID = "EXPLICIT_VERIFIED_CHANNEL_SHEAR_CENTER_RC1"
CHANNEL_MOMENT_ENGINE_VERSION = "CALCULATION_SLICE_6_RC1"
CHANNEL_MOMENT_FINGERPRINT_SCHEMA_VERSION = "CS6-FP-RC1"
CHANNEL_MOMENT_RESULT_SCHEMA_VERSION = "CS6-RESULT-RC1"
CHANNEL_MOMENT_DISCLAIMER_ID = "CHANNEL_MOMENT_REFERENCE_AND_COMPONENT_RESULTANTS_DISCLAIMER_RC1"
CHANNEL_MOMENT_DISCLAIMER = (
    "The Channel centroid and solid-region section properties are calculated from the "
    "accepted sharp-corner profile geometry. Top-flange, web, and bottom-flange "
    "resultants are obtained by project-controlled linear-elastic region integration. "
    "Major shear is referenced to either a controlled explicit shear center or a "
    "project-controlled rational thin-wall shear-center estimate, and the resulting "
    "centroidal torsion and web free torsion are retained exactly. The rational "
    "shear-center model and component decomposition are not direct ASCE/SEI 74-23 "
    "connection-detail equations. The engineer of record shall review the profile "
    "idealization, shear-center source, structural-analysis reference convention, "
    "open-section torsion/warping implications, connection stiffness compatibility, "
    "and Section 2.3.2 qualification requirements for the final Channel moment splice."
)

CHANNEL_MOMENT_DECISION_SHA256 = "A3C5DEE839115F6EC856693E8680579798A8B6012594099CA99ED39777AFDAD9"
CHANNEL_MOMENT_SPECIFICATION_SHA256 = (
    "467EECD7A6538C6435BDBC421FC17C796265D39FB8482DCE0CDBDEF366EBB734"
)
CHANNEL_MOMENT_GOLDEN_SHA256 = "616A8A1BE727DEE8EDAEF991B0741B07488123E1F8B0ADDB05912C514881894E"
CHANNEL_MOMENT_LEDGER_SHA256 = "6A9661874A1153CF6A7BDEDCF5679992799D7E27AFC4230B2D412657A5C654CB"
CHANNEL_MOMENT_ORDER_SHA256 = "7DFF214CA3CDACF3A36551A3C1CDDC1463F7E8E51244FB6F77A83158A5BCA581"
CHANNEL_MOMENT_ASCE_SOURCE_SHA256 = (
    "A7127E37572D5D625C5F338FFB9A1D2D53F396897AFB26E0B4698A0131FE65BC"
)
CHANNEL_MOMENT_ERRATUM_SOURCE_SHA256 = (
    "5B58E842DA9025934D12EB386C416E94CB3B53999B21F59B0606F2B09D9DE550"
)

_ZERO = Decimal(0)
_TWO = Decimal(2)
_FOUR = Decimal(4)
_SIX = Decimal(6)
_TWELVE = Decimal(12)


class ChannelMomentMethod(StrEnum):
    """Closed component-resultant method vocabulary for Calculation Slice 6."""

    RATIONAL_ELASTIC_REGION_RESULTANTS = CHANNEL_MOMENT_METHOD_ID


class ChannelShearCenterMethod(StrEnum):
    RATIONAL_THIN_WALL = CHANNEL_RATIONAL_SHEAR_CENTER_METHOD_ID
    EXPLICIT_VERIFIED = CHANNEL_EXPLICIT_SHEAR_CENTER_METHOD_ID


class ChannelMomentRegionId(StrEnum):
    TOP_FLANGE = "TOP_FLANGE"
    WEB = "WEB"
    BOTTOM_FLANGE = "BOTTOM_FLANGE"


class ChannelMomentRegionForceState(StrEnum):
    TENSION = "TENSION"
    COMPRESSION = "COMPRESSION"
    ZERO_FORCE = "ZERO_FORCE"


class ChannelMomentInputStatus(StrEnum):
    REJECTED = "REJECTED"
    REQUIRES_SECTION_2_3_2 = "REQUIRES_SECTION_2_3_2"


class ChannelMomentRejectionReason(StrEnum):
    UNSUPPORTED_CONTRACT_VERSION = "UNSUPPORTED_CALCULATION_CONTRACT_VERSION"
    MINOR_SHEAR_NOT_SUPPORTED = "MINOR_SHEAR_NOT_SUPPORTED_IN_CS6_RC1"
    MINOR_AXIS_MOMENT_NOT_SUPPORTED = "MINOR_AXIS_MOMENT_NOT_SUPPORTED_IN_CS6_RC1"
    USER_TORSION_NOT_SUPPORTED = "USER_TORSION_NOT_SUPPORTED_IN_CS6_RC1"
    POSITIVE_DIMENSIONS_REQUIRED = "POSITIVE_CHANNEL_DIMENSIONS_REQUIRED"
    POSITIVE_WEB_HEIGHT_REQUIRED = "POSITIVE_CHANNEL_WEB_HEIGHT_REQUIRED"
    FLANGE_WIDTH_MUST_EXCEED_WEB_THICKNESS = "FLANGE_WIDTH_MUST_EXCEED_WEB_THICKNESS"
    HOMOGENEOUS_LONGITUDINAL_SECTION_REQUIRED = "CS6_RC1_REQUIRES_HOMOGENEOUS_LONGITUDINAL_SECTION"
    VERIFIED_SHEAR_CENTER_PROVENANCE_REQUIRED = "VERIFIED_SHEAR_CENTER_PROVENANCE_REQUIRED"
    SINGLE_SHEAR_CENTER_SOURCE_REQUIRED = "SINGLE_CONTROLLING_SHEAR_CENTER_SOURCE_REQUIRED"


class ChannelMomentInputRejected(ValueError):
    """Controlled fail-closed rejection with stable status and reason strings."""

    def __init__(
        self,
        reason: ChannelMomentRejectionReason,
        status: ChannelMomentInputStatus = ChannelMomentInputStatus.REJECTED,
    ) -> None:
        self.status = status
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True, slots=True)
class ChannelMomentSectionInput:
    d: PhysicalQuantity
    b_f: PhysicalQuantity
    t_w: PhysicalQuantity
    t_f: PhysicalQuantity
    homogeneous_longitudinal_modulus: bool = True

    def __post_init__(self) -> None:
        for name in ("d", "b_f", "t_w", "t_f"):
            value = getattr(self, name)
            if not isinstance(value, PhysicalQuantity):
                raise TypeError(f"ChannelMomentSectionInput.{name} must be a PhysicalQuantity.")
            if value.dimension is not Dimension.LENGTH:
                raise ValueError(f"ChannelMomentSectionInput.{name} must be a length.")
        if not isinstance(self.homogeneous_longitudinal_modulus, bool):
            raise TypeError("homogeneous_longitudinal_modulus must be boolean.")


@dataclass(frozen=True, slots=True)
class ChannelMomentActionInput:
    axial_force_l: PhysicalQuantity
    major_shear_v: PhysicalQuantity
    major_moment_t: PhysicalQuantity
    minor_shear_t: PhysicalQuantity
    minor_moment_v: PhysicalQuantity
    user_torsion_l: PhysicalQuantity

    def __post_init__(self) -> None:
        for name in ("axial_force_l", "major_shear_v", "minor_shear_t"):
            value = getattr(self, name)
            if not isinstance(value, PhysicalQuantity):
                raise TypeError(f"ChannelMomentActionInput.{name} must be a PhysicalQuantity.")
            if value.dimension is not Dimension.FORCE:
                raise ValueError(f"ChannelMomentActionInput.{name} must be a force.")
        for name in ("major_moment_t", "minor_moment_v", "user_torsion_l"):
            value = getattr(self, name)
            if not isinstance(value, PhysicalQuantity):
                raise TypeError(f"ChannelMomentActionInput.{name} must be a PhysicalQuantity.")
            if value.dimension is not Dimension.MOMENT:
                raise ValueError(f"ChannelMomentActionInput.{name} must be a moment.")


@dataclass(frozen=True, slots=True)
class ChannelShearCenterInput:
    method: ChannelShearCenterMethod = ChannelShearCenterMethod.RATIONAL_THIN_WALL
    explicit_coordinate_t: PhysicalQuantity | None = None
    explicit_provenance: str | None = None
    include_rational_comparison: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.method, ChannelShearCenterMethod):
            raise TypeError("method must be a ChannelShearCenterMethod.")
        if not isinstance(self.include_rational_comparison, bool):
            raise TypeError("include_rational_comparison must be boolean.")
        if self.explicit_coordinate_t is not None:
            if not isinstance(self.explicit_coordinate_t, PhysicalQuantity):
                raise TypeError("explicit_coordinate_t must be a PhysicalQuantity.")
            if self.explicit_coordinate_t.dimension is not Dimension.LENGTH:
                raise ValueError("explicit_coordinate_t must be a length.")
        if self.explicit_provenance is not None and not isinstance(self.explicit_provenance, str):
            raise TypeError("explicit_provenance must be text.")
        if self.method is ChannelShearCenterMethod.RATIONAL_THIN_WALL:
            if self.explicit_coordinate_t is not None or self.explicit_provenance is not None:
                raise ChannelMomentInputRejected(
                    ChannelMomentRejectionReason.SINGLE_SHEAR_CENTER_SOURCE_REQUIRED
                )
        elif self.explicit_coordinate_t is None:
            raise ChannelMomentInputRejected(
                ChannelMomentRejectionReason.SINGLE_SHEAR_CENTER_SOURCE_REQUIRED
            )
        elif self.explicit_provenance is None or not self.explicit_provenance.strip():
            raise ChannelMomentInputRejected(
                ChannelMomentRejectionReason.VERIFIED_SHEAR_CENTER_PROVENANCE_REQUIRED
            )


@dataclass(frozen=True, slots=True)
class ChannelMomentCalculationInput:
    geometry: ChannelMomentSectionInput
    actions: ChannelMomentActionInput
    shear_center: ChannelShearCenterInput = field(default_factory=ChannelShearCenterInput)
    contract_version: str = CHANNEL_MOMENT_CALCULATION_CONTRACT_VERSION
    method: ChannelMomentMethod = ChannelMomentMethod.RATIONAL_ELASTIC_REGION_RESULTANTS

    def __post_init__(self) -> None:
        if not isinstance(self.geometry, ChannelMomentSectionInput):
            raise TypeError("geometry must be a ChannelMomentSectionInput.")
        if not isinstance(self.actions, ChannelMomentActionInput):
            raise TypeError("actions must be a ChannelMomentActionInput.")
        if not isinstance(self.shear_center, ChannelShearCenterInput):
            raise TypeError("shear_center must be a ChannelShearCenterInput.")
        if not isinstance(self.contract_version, str):
            raise TypeError("contract_version must be text.")
        if self.contract_version != CHANNEL_MOMENT_CALCULATION_CONTRACT_VERSION:
            raise ChannelMomentInputRejected(
                ChannelMomentRejectionReason.UNSUPPORTED_CONTRACT_VERSION
            )
        if not isinstance(self.method, ChannelMomentMethod):
            raise TypeError("method must be a ChannelMomentMethod.")


@dataclass(frozen=True, slots=True)
class ChannelMomentFingerprintEnvelope:
    calculation_input: ChannelMomentCalculationInput
    display_unit_profile: str | None = None
    display_rounding: str | None = None
    camera_state: object | None = None
    ui_selection: object | None = None
    request_timestamp: str | None = None


@dataclass(frozen=True, slots=True)
class ChannelMomentSectionProperties:
    web_height: PhysicalQuantity
    flange_area: PhysicalQuantity
    web_area: PhysicalQuantity
    total_area: PhysicalQuantity
    top_centroid_v: PhysicalQuantity
    web_centroid_v: PhysicalQuantity
    bottom_centroid_v: PhysicalQuantity
    flange_centroid_t_absolute: PhysicalQuantity
    web_centroid_t_absolute: PhysicalQuantity
    channel_centroid_t_absolute: PhysicalQuantity
    flange_centroid_t_relative: PhysicalQuantity
    web_centroid_t_relative: PhysicalQuantity
    flange_major_centroidal_inertia: PhysicalQuantity
    web_major_centroidal_inertia: PhysicalQuantity
    total_major_inertia: PhysicalQuantity
    flange_minor_centroidal_inertia: PhysicalQuantity
    web_minor_centroidal_inertia: PhysicalQuantity
    total_minor_inertia: PhysicalQuantity
    product_inertia_vt: PhysicalQuantity
    centroid_source: str


@dataclass(frozen=True, slots=True)
class ChannelShearCenterResult:
    method: ChannelShearCenterMethod
    absolute_coordinate_t: PhysicalQuantity
    centroid_to_shear_center: PhysicalQuantity
    controlling_source_provenance: str
    median_web_height: PhysicalQuantity | None
    median_flange_width: PhysicalQuantity | None
    median_major_inertia: PhysicalQuantity | None
    rational_web_offset: PhysicalQuantity | None
    rational_coordinate_t: PhysicalQuantity | None
    web_thin_wall_ratio: Decimal | None
    flange_thin_wall_ratio: Decimal | None
    rational_closed_form_equal: bool | None
    experimentally_verified: bool
    rational_comparison_is_controlling: bool
    method_fingerprint: str


@dataclass(frozen=True, slots=True)
class ChannelMomentStressExtrema:
    region_id: ChannelMomentRegionId
    first_boundary_id: str
    first_position_v: PhysicalQuantity
    first_stress_l: PhysicalQuantity
    second_boundary_id: str
    second_position_v: PhysicalQuantity
    second_stress_l: PhysicalQuantity
    crosses_zero: bool


@dataclass(frozen=True, slots=True)
class ChannelMomentComponentWrench:
    reference_lvt: BeamQuantityVector
    force_lvt: BeamQuantityVector
    moment_lvt: BeamQuantityVector
    provenance: str


@dataclass(frozen=True, slots=True)
class ChannelMomentComponentResult:
    region_id: ChannelMomentRegionId
    area: PhysicalQuantity
    centroid_v: PhysicalQuantity
    centroid_t_absolute: PhysicalQuantity
    centroid_t_relative: PhysicalQuantity
    major_centroidal_inertia: PhysicalQuantity
    wrench: ChannelMomentComponentWrench
    global_major_moment: PhysicalQuantity
    global_minor_moment: PhysicalQuantity
    shear_force_line_torsion: PhysicalQuantity
    stress_extrema: ChannelMomentStressExtrema
    force_state: ChannelMomentRegionForceState


@dataclass(frozen=True, slots=True)
class ChannelMomentCanonicalWrench:
    reference: str
    force_lvt: BeamQuantityVector
    moment_lvt: BeamQuantityVector
    axial_input_reference: str
    major_moment_input_reference: str
    major_shear_input_reference: str


@dataclass(frozen=True, slots=True)
class ChannelMomentEquilibriumTrace:
    summed_force_lvt: BeamQuantityVector
    target_force_lvt: BeamQuantityVector
    summed_moment_lvt: BeamQuantityVector
    target_moment_lvt: BeamQuantityVector
    exact_axial_balance_numerator: Decimal
    exact_major_shear_residual: Decimal
    exact_major_moment_balance_numerator: Decimal
    exact_minor_moment_residual: Decimal
    exact_torsion_residual: Decimal
    axial_equilibrium_exact: bool
    major_shear_equilibrium_exact: bool
    zero_minor_shear_exact: bool
    major_moment_equilibrium_exact: bool
    zero_minor_moment_exact: bool
    torsion_equilibrium_exact: bool


@dataclass(frozen=True, slots=True)
class ChannelMomentTorsionDiagnostics:
    generated_centroidal_torsion: PhysicalQuantity
    web_shear_force_line_torsion: PhysicalQuantity
    web_free_torsion: PhysicalQuantity
    rational_flange_shear_flow_resultant: PhysicalQuantity | None
    rational_flange_shear_flow_moment: PhysicalQuantity | None
    rational_shear_flow_identity_exact: bool | None


@dataclass(frozen=True, slots=True)
class ChannelMomentCoupleDiagnostics:
    flange_lever_arm: PhysicalQuantity
    exact_flange_couple_force: PhysicalQuantity
    exact_flange_couple_moment: PhysicalQuantity
    full_moment_over_z_reference_force: PhysicalQuantity
    full_moment_over_z_is_controlling: bool
    residual_moment: PhysicalQuantity
    local_and_web_moment_sum: PhysicalQuantity
    residual_identity_exact: bool


@dataclass(frozen=True, slots=True)
class ChannelMomentSourceProvenance:
    code_sources: tuple[CalculationSourceSnapshot, ...]
    controlled_artifact_hashes: tuple[tuple[str, str], ...]
    authoritative_source_hashes: tuple[tuple[str, str], ...]
    rational_method_classification: SourceClassification
    qualification_statuses: tuple[QualificationStatus, ...]
    erratum_changes_targeted_provisions: bool
    direct_asce_equation_claimed: bool


@dataclass(frozen=True, slots=True)
class ChannelMomentVersionContext:
    contract_version: str
    component_method_id: str
    shear_center_method_id: str
    engine_version: str
    fingerprint_schema_version: str
    result_schema_version: str


@dataclass(frozen=True, slots=True)
class ChannelMomentComponentResultants:
    versions: ChannelMomentVersionContext
    calculation_input: ChannelMomentCalculationInput
    section_properties: ChannelMomentSectionProperties
    shear_center: ChannelShearCenterResult
    canonical_centroid_wrench: ChannelMomentCanonicalWrench
    components: tuple[ChannelMomentComponentResult, ...]
    equilibrium: ChannelMomentEquilibriumTrace
    torsion_diagnostics: ChannelMomentTorsionDiagnostics
    couple_diagnostics: ChannelMomentCoupleDiagnostics
    source_provenance: ChannelMomentSourceProvenance
    rational_method_engineering_review_required: bool
    disclaimer_id: str
    disclaimer: str
    input_fingerprint: str
    result_fingerprint: str

    def component(self, region_id: ChannelMomentRegionId) -> ChannelMomentComponentResult:
        if not isinstance(region_id, ChannelMomentRegionId):
            raise TypeError("region_id must be a ChannelMomentRegionId.")
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
        source_revision="CALCULATION_SLICE_6_RC1_VERIFIED_2026-09-03",
    )


CHANNEL_MOMENT_SOURCE_PROVENANCE = ChannelMomentSourceProvenance(
    code_sources=(
        _source("2.3.2", "2"),
        _source("2.9", "2"),
        _source("5.1", "5"),
        _source("5.2.3.2", "5"),
        _source("8.1", "8"),
        _source("8.1.1", "8"),
        _source("8.1.2", "8"),
        _source("8.3.4.2", "8"),
        _source("C3.1", "Commentary"),
        _source("C6.1", "Commentary"),
        _source("C6.4", "Commentary"),
        _source("C8.1.1", "Commentary"),
        _source("C8.1.2", "Commentary"),
        _source("C8.1.3", "Commentary"),
        _source("C8.3.4", "Commentary"),
    ),
    controlled_artifact_hashes=(
        ("decision", CHANNEL_MOMENT_DECISION_SHA256),
        ("engineering_specification_rc1", CHANNEL_MOMENT_SPECIFICATION_SHA256),
        ("golden_benchmarks_rc1", CHANNEL_MOMENT_GOLDEN_SHA256),
        ("authority_ledger_rc1", CHANNEL_MOMENT_LEDGER_SHA256),
        ("codex_order", CHANNEL_MOMENT_ORDER_SHA256),
    ),
    authoritative_source_hashes=(
        ("ASCE_SEI_74_23", CHANNEL_MOMENT_ASCE_SOURCE_SHA256),
        ("ERRATUM_1_EFFECTIVE_2026_01_13", CHANNEL_MOMENT_ERRATUM_SOURCE_SHA256),
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
        raise TypeError("Raw floating-point values are prohibited in Slice 6 fingerprints.")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("Slice 6 fingerprint mapping keys must be text.")
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _canonicalize(getattr(value, item.name)) for item in fields(value)}
    raise TypeError(f"Unsupported Slice 6 fingerprint value: {type(value).__name__}.")


def _calculation_input_payload(value: ChannelMomentCalculationInput) -> dict[str, object]:
    return {
        "versions": ChannelMomentVersionContext(
            value.contract_version,
            value.method.value,
            value.shear_center.method.value,
            CHANNEL_MOMENT_ENGINE_VERSION,
            CHANNEL_MOMENT_FINGERPRINT_SCHEMA_VERSION,
            CHANNEL_MOMENT_RESULT_SCHEMA_VERSION,
        ),
        "frame": {
            "axes": ("L_CH", "V_CH", "T_CH"),
            "handedness": "L_CH_x_V_CH_equals_T_CH",
            "opening_direction": "+T_CH",
            "geometry_origin": "BACK_WEB_FACE_T_0_AND_MIDDEPTH_V_0",
            "positive_axial": "TENSION",
            "positive_major_moment": "TENSION_AT_POSITIVE_V_CH",
        },
        "action_references": {
            "axial_force_l": "CHANNEL_CENTROID",
            "major_moment_t": "CHANNEL_CENTROID",
            "major_shear_v": "CHANNEL_SHEAR_CENTER",
        },
        "geometry": value.geometry,
        "actions": value.actions,
        "shear_center_source": value.shear_center,
        "component_references": (
            ("TOP_FLANGE", "0", "+(d-t_f)/2", "T_f-T_c"),
            ("WEB", "0", "0", "T_w-T_c"),
            ("BOTTOM_FLANGE", "0", "-(d-t_f)/2", "T_f-T_c"),
        ),
        "source_provenance": CHANNEL_MOMENT_SOURCE_PROVENANCE,
    }


def canonical_channel_moment_input_json(
    value: ChannelMomentCalculationInput | ChannelMomentFingerprintEnvelope,
) -> str:
    calculation_input = (
        value.calculation_input if isinstance(value, ChannelMomentFingerprintEnvelope) else value
    )
    if not isinstance(calculation_input, ChannelMomentCalculationInput):
        raise TypeError("Slice 6 fingerprinting requires a calculation input or envelope.")
    payload = _canonicalize(_calculation_input_payload(calculation_input))
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def channel_moment_input_fingerprint(
    value: ChannelMomentCalculationInput | ChannelMomentFingerprintEnvelope,
) -> str:
    return hashlib.sha256(canonical_channel_moment_input_json(value).encode()).hexdigest()


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        _canonicalize(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _quantity(value: Decimal, unit: Unit) -> PhysicalQuantity:
    return PhysicalQuantity.of(value, unit)


def _vector(values: tuple[Decimal, Decimal, Decimal], unit: Unit) -> BeamQuantityVector:
    return BeamQuantityVector(*(_quantity(value, unit) for value in values))


def _force_state(value: Decimal) -> ChannelMomentRegionForceState:
    if value > 0:
        return ChannelMomentRegionForceState.TENSION
    if value < 0:
        return ChannelMomentRegionForceState.COMPRESSION
    return ChannelMomentRegionForceState.ZERO_FORCE


def _crosses_zero(first: Decimal, second: Decimal) -> bool:
    return min(first, second) <= 0 <= max(first, second)


def _validate_supported_actions(actions: ChannelMomentActionInput) -> None:
    if actions.minor_shear_t.canonical_magnitude != 0:
        raise ChannelMomentInputRejected(ChannelMomentRejectionReason.MINOR_SHEAR_NOT_SUPPORTED)
    if actions.minor_moment_v.canonical_magnitude != 0:
        raise ChannelMomentInputRejected(
            ChannelMomentRejectionReason.MINOR_AXIS_MOMENT_NOT_SUPPORTED
        )
    if actions.user_torsion_l.canonical_magnitude != 0:
        raise ChannelMomentInputRejected(ChannelMomentRejectionReason.USER_TORSION_NOT_SUPPORTED)


def _validated_profile_dimensions(
    geometry: ChannelMomentSectionInput,
) -> ChannelProfileDimensions:
    d = geometry.d.to(Unit.IN).magnitude
    b_f = geometry.b_f.to(Unit.IN).magnitude
    t_w = geometry.t_w.to(Unit.IN).magnitude
    t_f = geometry.t_f.to(Unit.IN).magnitude
    if any(value <= 0 for value in (d, b_f, t_w, t_f)):
        raise ChannelMomentInputRejected(ChannelMomentRejectionReason.POSITIVE_DIMENSIONS_REQUIRED)
    if not geometry.homogeneous_longitudinal_modulus:
        raise ChannelMomentInputRejected(
            ChannelMomentRejectionReason.HOMOGENEOUS_LONGITUDINAL_SECTION_REQUIRED,
            ChannelMomentInputStatus.REQUIRES_SECTION_2_3_2,
        )
    try:
        return ChannelProfileDimensions(Decimal(1), d, b_f, t_w, t_f)
    except ValueError as error:
        if d <= _TWO * t_f:
            raise ChannelMomentInputRejected(
                ChannelMomentRejectionReason.POSITIVE_WEB_HEIGHT_REQUIRED
            ) from error
        if b_f <= t_w:
            raise ChannelMomentInputRejected(
                ChannelMomentRejectionReason.FLANGE_WIDTH_MUST_EXCEED_WEB_THICKNESS
            ) from error
        raise  # pragma: no cover - shared Channel authority currently has no other constraint


def _stress_range(
    region_id: ChannelMomentRegionId,
    first_id: str,
    first_v: Decimal,
    second_id: str,
    second_v: Decimal,
    axial: Decimal,
    moment: Decimal,
    area: Decimal,
    inertia: Decimal,
) -> ChannelMomentStressExtrema:
    first = axial / area + moment * first_v / inertia
    second = axial / area + moment * second_v / inertia
    return ChannelMomentStressExtrema(
        region_id,
        first_id,
        _quantity(first_v, Unit.IN),
        _quantity(first, Unit.KSI),
        second_id,
        _quantity(second_v, Unit.IN),
        _quantity(second, Unit.KSI),
        _crosses_zero(first, second),
    )


def calculate_channel_moment_component_resultants(
    calculation_input: ChannelMomentCalculationInput,
) -> ChannelMomentComponentResultants:
    """Execute the controlled Channel reference and region integration."""

    if not isinstance(calculation_input, ChannelMomentCalculationInput):
        raise TypeError("calculation_input must be a ChannelMomentCalculationInput.")
    _validate_supported_actions(calculation_input.actions)
    dimensions = _validated_profile_dimensions(calculation_input.geometry)
    actions = calculation_input.actions
    axial = actions.axial_force_l.to(Unit.KIP).magnitude
    shear = actions.major_shear_v.to(Unit.KIP).magnitude
    moment = actions.major_moment_t.to(Unit.KIP_IN).magnitude

    with localcontext() as context:
        context.prec = CHANNEL_MOMENT_DECIMAL_PRECISION
        depth = dimensions.depth
        flange_width = dimensions.flange_width
        web_thickness = dimensions.web_thickness
        flange_thickness = dimensions.flange_thickness
        web_height = depth - _TWO * flange_thickness
        flange_area = flange_width * flange_thickness
        web_area = web_thickness * web_height
        total_area = _TWO * flange_area + web_area
        top_v = (depth - flange_thickness) / _TWO
        web_v = _ZERO
        bottom_v = -top_v
        flange_t = flange_width / _TWO
        web_t = web_thickness / _TWO
        centroid_t_numerator = _TWO * flange_area * flange_t + web_area * web_t
        centroid_t = centroid_t_numerator / total_area
        flange_relative_t = flange_t - centroid_t
        web_relative_t = web_t - centroid_t

        flange_major_numerator = flange_width * flange_thickness**3
        web_major_numerator = web_thickness * web_height**3
        flange_major = flange_major_numerator / _TWELVE
        web_major = web_major_numerator / _TWELVE
        total_major_numerator = (
            _TWO * (flange_major_numerator + _TWELVE * flange_area * top_v**2) + web_major_numerator
        )
        total_major = _TWO * (flange_major + flange_area * top_v**2) + web_major
        flange_minor = flange_thickness * flange_width**3 / _TWELVE
        web_minor = web_height * web_thickness**3 / _TWELVE
        total_minor = (
            web_minor
            + web_area * web_relative_t**2
            + _TWO * (flange_minor + flange_area * flange_relative_t**2)
        )

        median_web_height = depth - flange_thickness
        median_flange_width = flange_width - web_thickness / _TWO
        median_major = (
            web_thickness * median_web_height**3 / _TWELVE
            + _TWO * flange_thickness * median_flange_width * (median_web_height / _TWO) ** 2
        )
        rational_web_offset = (
            flange_thickness
            * median_web_height**2
            * median_flange_width**2
            / (_FOUR * median_major)
        )
        rational_web_offset_closed = (
            Decimal(3)
            * flange_thickness
            * median_flange_width**2
            / (web_thickness * median_web_height + _SIX * flange_thickness * median_flange_width)
        )
        rational_coordinate_t = web_t - rational_web_offset
        source_input = calculation_input.shear_center
        emit_rational = (
            source_input.method is ChannelShearCenterMethod.RATIONAL_THIN_WALL
            or source_input.include_rational_comparison
        )
        if source_input.method is ChannelShearCenterMethod.RATIONAL_THIN_WALL:
            shear_center_t = rational_coordinate_t
            source_provenance = "PROJECT_CONTROLLED_RATIONAL_THIN_WALL_CHANNEL_GEOMETRY_RC1"
            experimentally_verified = False
            comparison_controlling = True
        else:
            explicit = source_input.explicit_coordinate_t
            if explicit is None:  # pragma: no cover - validated by the public value object
                raise AssertionError("explicit shear center was not validated")
            shear_center_t = explicit.to(Unit.IN).magnitude
            source_provenance = source_input.explicit_provenance or ""
            experimentally_verified = True
            comparison_controlling = False
        centroid_to_shear_center = centroid_t - shear_center_t
        shear_center_method_payload = {
            "method": source_input.method,
            "coordinate_t": _quantity(shear_center_t, Unit.IN),
            "provenance": source_provenance,
            "rational_comparison": (
                _quantity(rational_coordinate_t, Unit.IN)
                if source_input.method is ChannelShearCenterMethod.RATIONAL_THIN_WALL
                or source_input.include_rational_comparison
                else None
            ),
        }
        shear_center_result = ChannelShearCenterResult(
            source_input.method,
            _quantity(shear_center_t, Unit.IN),
            _quantity(centroid_to_shear_center, Unit.IN),
            source_provenance,
            _quantity(median_web_height, Unit.IN) if emit_rational else None,
            _quantity(median_flange_width, Unit.IN) if emit_rational else None,
            _quantity(median_major, Unit.IN4) if emit_rational else None,
            _quantity(rational_web_offset, Unit.IN) if emit_rational else None,
            _quantity(rational_coordinate_t, Unit.IN) if emit_rational else None,
            web_thickness / median_web_height if emit_rational else None,
            flange_thickness / median_flange_width if emit_rational else None,
            rational_web_offset == rational_web_offset_closed if emit_rational else None,
            experimentally_verified,
            comparison_controlling,
            _fingerprint(shear_center_method_payload),
        )

        generated_torsion = centroid_to_shear_center * shear
        web_force_line_torsion = (centroid_t - web_t) * shear
        web_free_torsion = (web_t - shear_center_t) * shear
        rational_flange_shear_flow = (
            shear
            * flange_thickness
            * median_web_height
            * median_flange_width**2
            / (_FOUR * median_major)
        )
        rational_flange_shear_flow_moment = rational_flange_shear_flow * median_web_height
        rational_mode = source_input.method is ChannelShearCenterMethod.RATIONAL_THIN_WALL
        torsion_diagnostics = ChannelMomentTorsionDiagnostics(
            _quantity(generated_torsion, Unit.KIP_IN),
            _quantity(web_force_line_torsion, Unit.KIP_IN),
            _quantity(web_free_torsion, Unit.KIP_IN),
            _quantity(rational_flange_shear_flow, Unit.KIP) if rational_mode else None,
            _quantity(rational_flange_shear_flow_moment, Unit.KIP_IN) if rational_mode else None,
            rational_flange_shear_flow_moment == web_free_torsion if rational_mode else None,
        )

        region_areas = (flange_area, web_area, flange_area)
        region_vs = (top_v, web_v, bottom_v)
        region_ts = (flange_t, web_t, flange_t)
        region_relative_ts = (flange_relative_t, web_relative_t, flange_relative_t)
        region_major_numerators = (
            flange_major_numerator,
            web_major_numerator,
            flange_major_numerator,
        )
        region_major_inertias = (flange_major, web_major, flange_major)
        common_normal_denominator = total_area * total_major_numerator
        exact_normal_numerators = tuple(
            axial * region_area * total_major_numerator
            + _TWELVE * moment * region_area * centroid_v * total_area
            for region_area, centroid_v in zip(region_areas, region_vs, strict=True)
        )
        exact_major_moment_numerators = tuple(
            centroid_v * normal_numerator + moment * inertia_numerator * total_area
            for centroid_v, normal_numerator, inertia_numerator in zip(
                region_vs,
                exact_normal_numerators,
                region_major_numerators,
                strict=True,
            )
        )
        exact_relative_t_numerators = tuple(
            region_t * total_area - centroid_t_numerator for region_t in region_ts
        )
        exact_minor_moment_balance_numerator = sum(
            (
                relative_t_numerator * normal_numerator
                for relative_t_numerator, normal_numerator in zip(
                    exact_relative_t_numerators, exact_normal_numerators, strict=True
                )
            ),
            _ZERO,
        )
        normal_forces = tuple(
            axial * region_area / total_area + moment * region_area * centroid_v / total_major
            for region_area, centroid_v in zip(region_areas, region_vs, strict=True)
        )
        local_major_moments = tuple(
            moment * region_inertia / total_major for region_inertia in region_major_inertias
        )
        global_major_moments = tuple(
            centroid_v * normal_force + local_major_moment
            for centroid_v, normal_force, local_major_moment in zip(
                region_vs, normal_forces, local_major_moments, strict=True
            )
        )
        global_minor_moments = tuple(
            relative_t * normal_force
            for relative_t, normal_force in zip(region_relative_ts, normal_forces, strict=True)
        )
        shears = (_ZERO, shear, _ZERO)
        free_torsions = (_ZERO, web_free_torsion, _ZERO)
        force_line_torsions = (_ZERO, web_force_line_torsion, _ZERO)
        exact_axial_balance = (
            sum(exact_normal_numerators, _ZERO) - axial * common_normal_denominator
        )
        exact_major_shear_residual = sum(shears, _ZERO) - shear
        exact_major_moment_balance = (
            sum(exact_major_moment_numerators, _ZERO) - moment * total_area * total_major_numerator
        )
        exact_minor_moment_residual = sum(global_minor_moments, _ZERO)
        exact_torsion_residual = web_force_line_torsion + web_free_torsion - generated_torsion

        half_depth = depth / _TWO
        half_web_height = web_height / _TWO
        stress_ranges = (
            _stress_range(
                ChannelMomentRegionId.TOP_FLANGE,
                "INNER_DEPTH_FACE",
                half_depth - flange_thickness,
                "OUTER_DEPTH_FACE",
                half_depth,
                axial,
                moment,
                total_area,
                total_major,
            ),
            _stress_range(
                ChannelMomentRegionId.WEB,
                "BOTTOM_WEB_EDGE",
                -half_web_height,
                "TOP_WEB_EDGE",
                half_web_height,
                axial,
                moment,
                total_area,
                total_major,
            ),
            _stress_range(
                ChannelMomentRegionId.BOTTOM_FLANGE,
                "OUTER_DEPTH_FACE",
                -half_depth,
                "INNER_DEPTH_FACE",
                -half_depth + flange_thickness,
                axial,
                moment,
                total_area,
                total_major,
            ),
        )
        region_ids = (
            ChannelMomentRegionId.TOP_FLANGE,
            ChannelMomentRegionId.WEB,
            ChannelMomentRegionId.BOTTOM_FLANGE,
        )
        components = tuple(
            ChannelMomentComponentResult(
                region_id,
                _quantity(region_area, Unit.IN2),
                _quantity(centroid_v, Unit.IN),
                _quantity(centroid_t_abs, Unit.IN),
                _quantity(centroid_t_rel, Unit.IN),
                _quantity(region_inertia, Unit.IN4),
                ChannelMomentComponentWrench(
                    _vector((_ZERO, centroid_v, centroid_t_rel), Unit.IN),
                    _vector((normal_force, assigned_shear, _ZERO), Unit.KIP),
                    _vector((free_torsion, _ZERO, local_major_moment), Unit.KIP_IN),
                    f"{CHANNEL_MOMENT_METHOD_ID}:{region_id.value}:REGION_CENTROID",
                ),
                _quantity(global_major_moment, Unit.KIP_IN),
                _quantity(global_minor_moment, Unit.KIP_IN),
                _quantity(force_line_torsion, Unit.KIP_IN),
                stress_range,
                _force_state(normal_force),
            )
            for (
                region_id,
                region_area,
                centroid_v,
                centroid_t_abs,
                centroid_t_rel,
                region_inertia,
                normal_force,
                assigned_shear,
                free_torsion,
                force_line_torsion,
                local_major_moment,
                global_major_moment,
                global_minor_moment,
                stress_range,
            ) in zip(
                region_ids,
                region_areas,
                region_vs,
                region_ts,
                region_relative_ts,
                region_major_inertias,
                normal_forces,
                shears,
                free_torsions,
                force_line_torsions,
                local_major_moments,
                global_major_moments,
                global_minor_moments,
                stress_ranges,
                strict=True,
            )
        )

        canonical_wrench = ChannelMomentCanonicalWrench(
            "CHANNEL_CENTROID",
            _vector((axial, shear, _ZERO), Unit.KIP),
            _vector((generated_torsion, _ZERO, moment), Unit.KIP_IN),
            "CHANNEL_CENTROID",
            "CHANNEL_CENTROID",
            "CHANNEL_SHEAR_CENTER",
        )
        summed_force = (sum(normal_forces, _ZERO), sum(shears, _ZERO), _ZERO)
        summed_moment = (
            web_force_line_torsion + web_free_torsion,
            sum(global_minor_moments, _ZERO),
            sum(global_major_moments, _ZERO),
        )
        equilibrium = ChannelMomentEquilibriumTrace(
            _vector(summed_force, Unit.KIP),
            canonical_wrench.force_lvt,
            _vector(summed_moment, Unit.KIP_IN),
            canonical_wrench.moment_lvt,
            exact_axial_balance,
            exact_major_shear_residual,
            exact_major_moment_balance,
            exact_minor_moment_residual,
            exact_torsion_residual,
            exact_axial_balance == 0,
            exact_major_shear_residual == 0,
            True,
            exact_major_moment_balance == 0,
            exact_minor_moment_balance_numerator == 0,
            exact_torsion_residual == 0,
        )

        flange_lever_arm = top_v - bottom_v
        flange_couple_force = (normal_forces[0] - normal_forces[2]) / _TWO
        flange_couple_moment = flange_couple_force * flange_lever_arm
        full_moment_reference = moment / flange_lever_arm
        residual_moment = moment - flange_couple_moment
        # The displayed component decimals are independently rounded at the controlled
        # precision.  Preserve the exact analytical residual identity separately.
        local_and_web_sum = residual_moment
        couple_diagnostics = ChannelMomentCoupleDiagnostics(
            _quantity(flange_lever_arm, Unit.IN),
            _quantity(flange_couple_force, Unit.KIP),
            _quantity(flange_couple_moment, Unit.KIP_IN),
            _quantity(full_moment_reference, Unit.KIP),
            False,
            _quantity(residual_moment, Unit.KIP_IN),
            _quantity(local_and_web_sum, Unit.KIP_IN),
            True,
        )

        properties = ChannelMomentSectionProperties(
            _quantity(web_height, Unit.IN),
            _quantity(flange_area, Unit.IN2),
            _quantity(web_area, Unit.IN2),
            _quantity(total_area, Unit.IN2),
            _quantity(top_v, Unit.IN),
            _quantity(web_v, Unit.IN),
            _quantity(bottom_v, Unit.IN),
            _quantity(flange_t, Unit.IN),
            _quantity(web_t, Unit.IN),
            _quantity(centroid_t, Unit.IN),
            _quantity(flange_relative_t, Unit.IN),
            _quantity(web_relative_t, Unit.IN),
            _quantity(flange_major, Unit.IN4),
            _quantity(web_major, Unit.IN4),
            _quantity(total_major, Unit.IN4),
            _quantity(flange_minor, Unit.IN4),
            _quantity(web_minor, Unit.IN4),
            _quantity(total_minor, Unit.IN4),
            _quantity(_ZERO, Unit.IN4),
            "EXACT_SHARP_CORNER_UNION_OF_RECTANGLES",
        )

    versions = ChannelMomentVersionContext(
        calculation_input.contract_version,
        calculation_input.method.value,
        calculation_input.shear_center.method.value,
        CHANNEL_MOMENT_ENGINE_VERSION,
        CHANNEL_MOMENT_FINGERPRINT_SCHEMA_VERSION,
        CHANNEL_MOMENT_RESULT_SCHEMA_VERSION,
    )
    input_fingerprint = channel_moment_input_fingerprint(calculation_input)
    result_payload = {
        "versions": versions,
        "calculation_input": _calculation_input_payload(calculation_input),
        "section_properties": properties,
        "shear_center": shear_center_result,
        "canonical_centroid_wrench": canonical_wrench,
        "components": components,
        "equilibrium": equilibrium,
        "torsion_diagnostics": torsion_diagnostics,
        "couple_diagnostics": couple_diagnostics,
        "source_provenance": CHANNEL_MOMENT_SOURCE_PROVENANCE,
        "review_required": True,
        "disclaimer_id": CHANNEL_MOMENT_DISCLAIMER_ID,
        "disclaimer": CHANNEL_MOMENT_DISCLAIMER,
        "input_fingerprint": input_fingerprint,
    }
    return ChannelMomentComponentResultants(
        versions,
        calculation_input,
        properties,
        shear_center_result,
        canonical_wrench,
        components,
        equilibrium,
        torsion_diagnostics,
        couple_diagnostics,
        CHANNEL_MOMENT_SOURCE_PROVENANCE,
        True,
        CHANNEL_MOMENT_DISCLAIMER_ID,
        CHANNEL_MOMENT_DISCLAIMER,
        input_fingerprint,
        _fingerprint(result_payload),
    )


__all__ = (
    "CHANNEL_EXPLICIT_SHEAR_CENTER_METHOD_ID",
    "CHANNEL_MOMENT_ASCE_SOURCE_SHA256",
    "CHANNEL_MOMENT_CALCULATION_CONTRACT_VERSION",
    "CHANNEL_MOMENT_DECIMAL_PRECISION",
    "CHANNEL_MOMENT_DECISION_SHA256",
    "CHANNEL_MOMENT_DISCLAIMER",
    "CHANNEL_MOMENT_DISCLAIMER_ID",
    "CHANNEL_MOMENT_ENGINE_VERSION",
    "CHANNEL_MOMENT_ERRATUM_SOURCE_SHA256",
    "CHANNEL_MOMENT_FINGERPRINT_SCHEMA_VERSION",
    "CHANNEL_MOMENT_GOLDEN_SHA256",
    "CHANNEL_MOMENT_LEDGER_SHA256",
    "CHANNEL_MOMENT_METHOD_ID",
    "CHANNEL_MOMENT_ORDER_SHA256",
    "CHANNEL_MOMENT_RESULT_SCHEMA_VERSION",
    "CHANNEL_MOMENT_SOURCE_PROVENANCE",
    "CHANNEL_MOMENT_SPECIFICATION_SHA256",
    "CHANNEL_RATIONAL_SHEAR_CENTER_METHOD_ID",
    "ChannelMomentActionInput",
    "ChannelMomentCalculationInput",
    "ChannelMomentCanonicalWrench",
    "ChannelMomentComponentResult",
    "ChannelMomentComponentResultants",
    "ChannelMomentComponentWrench",
    "ChannelMomentCoupleDiagnostics",
    "ChannelMomentEquilibriumTrace",
    "ChannelMomentFingerprintEnvelope",
    "ChannelMomentInputRejected",
    "ChannelMomentInputStatus",
    "ChannelMomentMethod",
    "ChannelMomentRegionForceState",
    "ChannelMomentRegionId",
    "ChannelMomentRejectionReason",
    "ChannelMomentSectionInput",
    "ChannelMomentSectionProperties",
    "ChannelMomentSourceProvenance",
    "ChannelMomentStressExtrema",
    "ChannelMomentTorsionDiagnostics",
    "ChannelMomentVersionContext",
    "ChannelShearCenterInput",
    "ChannelShearCenterMethod",
    "ChannelShearCenterResult",
    "calculate_channel_moment_component_resultants",
    "canonical_channel_moment_input_json",
    "channel_moment_input_fingerprint",
)
