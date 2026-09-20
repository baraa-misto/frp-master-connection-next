"""CS7-RC2 FRP-only instep resistance and qualified signed full-wrench envelope.

There is deliberately no production default qualified package, heel formula,
prying formula, support anchor distribution, or anchor/concrete resistance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, fields
from decimal import Decimal, localcontext
from enum import StrEnum
from fractions import Fraction

from frp_master_connection.calculation.angle_connector_core import (
    AngleCoreResult,
    Decimal3,
    angle_fingerprint,
    exact_decimal,
)
from frp_master_connection.calculation.angle_connector_providers import AngleProviderResult
from frp_master_connection.calculation.equations import EndUsePropertyTrace, FactorAssemblyTrace
from frp_master_connection.calculation.properties import FRPPropertyKind, MaterialPropertySnapshot
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit
from frp_master_connection.calculation.sources import (
    CalculationSourceSnapshot,
    QualificationStatus,
    SourceClassification,
    asce_74_23_chapter_8_source,
)
from frp_master_connection.domain.material_architecture import (
    ConnectorMaterialFamily,
    EngineeringPropertySource,
    PropertySourceConfirmation,
)

FRP_PROVIDER_ID = "FRP_ANGLE_CONNECTOR_RESISTANCE_PROVIDER_RC1"
INSTEP_METHOD = "ASCE_74_23_EQ_8_15_CLIP_ANGLE_INSTEP_SHEAR_RC1"
ENVELOPE_METHOD = "QUALIFIED_FRP_ANGLE_ASSEMBLY_FULL_WRENCH_ENVELOPE_RC1"
INTERACTION_METHOD = "RATIONAL_LINEAR_QUALIFIED_ANGLE_ASSEMBLY_INTERACTION_RC1"
REVIEW_PASS = "PASS_WITH_QUALIFIED_SOURCE_AND_ENGINEERING_REVIEW_REQUIRED"  # noqa: S105 - status
DISCLAIMER_ID = "QUALIFIED_FRP_ANGLE_CONNECTOR_TRANSFER_DISCLAIMER_RC1"
DISCLAIMER = (
    "Qualified FRP assembly data and source-authorized rational interaction are not a "
    "universal angle-body or prying rule. Engineering review and ASCE/SEI 74-23 Section "
    "2.3.2 qualification are required. Anchor/concrete capacity and individual flexible-"
    "fixture reactions remain external; this is not complete connection approval."
)
COMPONENT_NAMES = ("F_A", "F_B", "F_C", "M_A", "M_B", "M_C")


class QualifiedCoverage(StrEnum):
    BODY = "ANGLE_BODY"
    HEEL = "HEEL_INSTEP"
    MEMBER_LEG = "MEMBER_LEG"
    SUPPORT_LEG = "SUPPORT_LEG"
    OUT_OF_PLANE = "OUT_OF_PLANE"
    THROUGH_THICKNESS = "THROUGH_THICKNESS_DELAMINATION"
    CONTACT = "CONTACT"
    PRYING = "PRYING_EFFECT_ON_CONNECTOR"
    SECONDARY_BOLT_BENDING = "SECONDARY_BOLT_BENDING_EFFECT_ON_CONNECTOR"
    INTERACTION = "COMBINED_INTERACTION"


def _sha(value: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("Binding identities must be canonical lowercase SHA-256 digests.")


@dataclass(frozen=True, slots=True)
class FRPSourceBinding:
    geometry: str
    material: str
    member_fasteners: str
    support_fixture: str
    references: str

    def __post_init__(self) -> None:
        for field in fields(self):
            _sha(getattr(self, field.name))


@dataclass(frozen=True, slots=True)
class SignedDesignStrength:
    positive: PhysicalQuantity | None
    negative: PhysicalQuantity | None

    def __post_init__(self) -> None:
        for value in (self.positive, self.negative):
            if value is not None and (
                not isinstance(value, PhysicalQuantity) or value.magnitude <= 0
            ):
                raise ValueError("Each supplied signed DESIGN strength must be positive.")


@dataclass(frozen=True, slots=True)
class QualifiedFRPAngleSource:
    source: EngineeringPropertySource
    binding: FRPSourceBinding
    # F_A, F_B, F_C, M_A, M_B, M_C. These are already design strengths, not nominal.
    strengths: tuple[SignedDesignStrength, ...]
    coverage: tuple[QualifiedCoverage, ...]
    linear_interaction_authorized: bool

    def __post_init__(self) -> None:
        if not isinstance(self.source, EngineeringPropertySource) or not isinstance(
            self.binding, FRPSourceBinding
        ):
            raise TypeError("Qualified data require a source record and exact binding.")
        if not isinstance(self.strengths, tuple) or len(self.strengths) != 6:
            raise ValueError("Six immutable positive/negative strength records are required.")
        for index, strength in enumerate(self.strengths):
            if not isinstance(strength, SignedDesignStrength):
                raise TypeError("Strength records must be SignedDesignStrength.")
            for value in (strength.positive, strength.negative):
                if value is not None and value.dimension is not (
                    Dimension.FORCE if index < 3 else Dimension.MOMENT
                ):
                    raise ValueError("Qualified component strength has the wrong dimension.")
        if (
            not isinstance(self.coverage, tuple)
            or any(not isinstance(c, QualifiedCoverage) for c in self.coverage)
            or len(set(self.coverage)) != len(self.coverage)
        ):
            raise ValueError("Qualified coverage must be immutable, explicit, and unique.")
        if not isinstance(self.linear_interaction_authorized, bool):
            raise TypeError("Interaction authority requires an explicit boolean declaration.")


@dataclass(frozen=True, slots=True)
class FRPAngleContext:
    family: ConnectorMaterialFamily
    homogeneous_pultruded_l_angle: bool
    material: MaterialPropertySnapshot
    instep_property: EndUsePropertyTrace
    member_fasteners_fingerprint: str
    support_fixture_fingerprint: str
    qualified_source: QualifiedFRPAngleSource | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.family, ConnectorMaterialFamily) or not isinstance(
            self.homogeneous_pultruded_l_angle, bool
        ):
            raise TypeError("Material family and homogeneous pultruded applicability are explicit.")
        if not isinstance(self.material, MaterialPropertySnapshot) or not isinstance(
            self.instep_property, EndUsePropertyTrace
        ):
            raise TypeError(
                "Existing sourced material snapshot and adjusted property trace required."
            )
        _sha(self.member_fasteners_fingerprint)
        _sha(self.support_fixture_fingerprint)
        if self.qualified_source is not None and not isinstance(
            self.qualified_source, QualifiedFRPAngleSource
        ):
            raise TypeError("Qualified source must be an immutable qualified angle package.")


def frp_source_binding(core: AngleCoreResult, context: FRPAngleContext) -> FRPSourceBinding:
    return FRPSourceBinding(
        core.geometry_fingerprint,
        angle_fingerprint(
            (
                context.family,
                context.homogeneous_pultruded_l_angle,
                context.material,
                context.instep_property,
            )
        ),
        context.member_fasteners_fingerprint,
        context.support_fixture_fingerprint,
        core.reference_fingerprint,
    )


@dataclass(frozen=True, slots=True)
class FRPAngleMaterialAxes:
    lw: Decimal3
    member_cw: Decimal3
    support_cw: Decimal3
    member_tt: Decimal3
    support_tt: Decimal3


@dataclass(frozen=True, slots=True)
class InstepCheck:
    length: PhysicalQuantity
    demand: PhysicalQuantity
    factors: FactorAssemblyTrace
    utilization: Decimal
    passed: bool
    source: CalculationSourceSnapshot
    method: str = INSTEP_METHOD
    covered_component: str = "F_A"


@dataclass(frozen=True, slots=True)
class QualifiedComponentTerm:
    component: str
    signed_demand: PhysicalQuantity
    selected_design_strength: PhysicalQuantity | None
    utilization: Decimal


@dataclass(frozen=True, slots=True)
class QualifiedBodyCheck:
    status: str
    utilization: Decimal | None = None
    terms: tuple[QualifiedComponentTerm, ...] = ()
    method: str = ENVELOPE_METHOD
    interaction_method: str = INTERACTION_METHOD


@dataclass(frozen=True, slots=True)
class FRPAngleDetail:
    material_axes: FRPAngleMaterialAxes
    instep: InstepCheck | None
    body: QualifiedBodyCheck
    source_binding: FRPSourceBinding
    review_required: bool = True
    qualification: str = "REQUIRED_2_3_2"
    disclaimer_id: str = DISCLAIMER_ID
    disclaimer: str = DISCLAIMER


def _ratio(value: Fraction) -> Decimal:
    with localcontext() as context:
        context.prec = 80
        return Decimal(value.numerator) / Decimal(value.denominator)


def _valid_instep_property(context: FRPAngleContext) -> bool:
    trace = context.instep_property
    matching = tuple(p for p in context.material.properties if p.kind is FRPPropertyKind.FSH_LT)
    return (
        context.material.locked
        and len(matching) == 1
        and matching[0].value == trace.source_property
        and matching[0].use_in_chapter_8_equations
        and matching[0].source_classification
        not in {
            SourceClassification.SOURCE_PENDING,
            SourceClassification.MANUFACTURER_NOMINAL,
        }
        and trace.property_kind is FRPPropertyKind.FSH_LT
        and trace.source_property.dimension is Dimension.STRESS
        and trace.adjusted_property.dimension is Dimension.STRESS
        and trace.source_property.magnitude > 0
        and trace.adjusted_property.magnitude > 0
        and trace.qualification_status is matching[0].qualification_status
        and trace.qualification_status is not QualificationStatus.SOURCE_PENDING
        and all(
            isinstance(v, Decimal) and v.is_finite() and v > 0
            for v in (trace.cm, trace.ct, trace.cch)
        )
    )


def _instep(core: AngleCoreResult, context: FRPAngleContext) -> InstepCheck:
    geometry = core.request.geometry
    # Consume the existing adjusted property exactly once; no Section 2.4 reapplication.
    length = Fraction(geometry.length.to(Unit.IN).magnitude) - sum(
        Fraction(q.to(Unit.IN).magnitude) for q in geometry.heel_end_reliefs
    )
    thickness = Fraction(geometry.thickness.to(Unit.IN).magnitude)
    strength = Fraction(context.instep_property.adjusted_property.to(Unit.KSI).magnitude)
    nominal = length * thickness * strength
    design = Fraction(7, 10) * nominal
    demand = abs(Fraction(core.heel.force.x.to(Unit.KIP).magnitude))
    factors = FactorAssemblyTrace(
        (context.instep_property,),
        PhysicalQuantity(exact_decimal(nominal), Unit.KIP),
        Decimal(1),
        Decimal(1),
        Decimal("0.70"),
        Decimal(1),
        PhysicalQuantity(exact_decimal(design), Unit.KIP),
    )
    return InstepCheck(
        PhysicalQuantity(exact_decimal(length), Unit.IN),
        PhysicalQuantity(exact_decimal(demand), Unit.KIP),
        factors,
        _ratio(demand / design),
        demand <= design,
        asce_74_23_chapter_8_source(section="8.3.4", equation_reference="8-15"),
    )


def _body(core: AngleCoreResult, context: FRPAngleContext) -> QualifiedBodyCheck:
    h = core.heel
    demands = (h.force.x, h.force.y, h.force.z, h.moment.x, h.moment.y, h.moment.z)
    if all(q.magnitude == 0 for q in demands):
        return QualifiedBodyCheck("NOT_REQUIRED_ZERO_DEMAND")
    package = context.qualified_source
    if package is None:
        return QualifiedBodyCheck("SOURCE_REQUIRED")
    if package.binding != frp_source_binding(core, context):
        return QualifiedBodyCheck("SOURCE_NOT_APPLICABLE")
    if (
        package.source.confirmation
        not in {
            PropertySourceConfirmation.TEST_QUALIFIED,
            PropertySourceConfirmation.ENGINEER_APPROVED,
        }
        or not package.source.qualification_record_ids
    ):
        return QualifiedBodyCheck("SOURCE_REQUIRED")
    if not package.linear_interaction_authorized:
        return QualifiedBodyCheck("NOT_EVALUATED_INTERACTION_AUTHORITY_REQUIRED")
    coverage = set(package.coverage)
    if (
        not {
            QualifiedCoverage.CONTACT,
            QualifiedCoverage.PRYING,
            QualifiedCoverage.SECONDARY_BOLT_BENDING,
        }
        <= coverage
    ):
        return QualifiedBodyCheck("NOT_EVALUATED_PRYING_CONTACT_COVERAGE_REQUIRED")
    if coverage != set(QualifiedCoverage):
        return QualifiedBodyCheck("NOT_EVALUATED_QUALIFIED_COVERAGE_MISSING")
    terms: list[QualifiedComponentTerm] = []
    total = Fraction(0)
    for name, demand, strengths in zip(COMPONENT_NAMES, demands, package.strengths, strict=True):
        signed = Fraction(demand.canonical_magnitude)
        selected = strengths.positive if signed > 0 else strengths.negative
        if signed != 0 and selected is None:
            return QualifiedBodyCheck("NOT_EVALUATED_SIGNED_STRENGTH_REQUIRED")
        ratio = (
            Fraction(0)
            if signed == 0 or selected is None
            else abs(signed) / Fraction(selected.canonical_magnitude)
        )
        total += ratio
        terms.append(QualifiedComponentTerm(name, demand, selected, _ratio(ratio)))
    return QualifiedBodyCheck(REVIEW_PASS if total <= 1 else "FAIL", _ratio(total), tuple(terms))


class FRPAngleResistanceProvider:
    """Only registered provider in RC2; applicability never changes core demand."""

    def evaluate(self, core: AngleCoreResult, context: object) -> AngleProviderResult:
        if not isinstance(context, FRPAngleContext):
            return AngleProviderResult(
                core.fingerprint,
                FRP_PROVIDER_ID,
                "INVALID",
                "An explicit FRP provider context is required.",
                None,
                angle_fingerprint((FRP_PROVIDER_ID, core.fingerprint, "INVALID_CONTEXT")),
            )
        frame = core.request.frame
        axes = FRPAngleMaterialAxes(
            frame.a,
            frame.b,
            frame.c,
            frame.c,
            (frame.b[0].copy_negate(), frame.b[1].copy_negate(), frame.b[2].copy_negate()),
        )
        applicable = (
            context.family is ConnectorMaterialFamily.PULTRUDED_FRP
            and context.homogeneous_pultruded_l_angle
        )
        instep = _instep(core, context) if applicable and _valid_instep_property(context) else None
        body = _body(core, context) if instep is not None else QualifiedBodyCheck("INVALID")
        detail = FRPAngleDetail(axes, instep, body, frp_source_binding(core, context))
        status = body.status
        if instep is not None and not instep.passed:
            status = "FAIL"
        return AngleProviderResult(
            core.fingerprint,
            FRP_PROVIDER_ID,
            status,
            body.status,
            detail,
            angle_fingerprint((FRP_PROVIDER_ID, core.fingerprint, context, detail, status)),
        )
