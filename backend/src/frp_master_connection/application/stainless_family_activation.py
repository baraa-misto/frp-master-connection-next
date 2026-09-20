"""CME-3 server-owned public connector-body boundary, not a resistance engine.

The frozen providers remain immutable. Planning is non-calculating, and an
available adapter is not a statement that a particular connection is qualified.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from frp_master_connection.calculation.angle_connector_core import AngleWrench, angle_fingerprint
from frp_master_connection.calculation.connector_material_plan import ConnectorMaterialPlan
from frp_master_connection.calculation.stainless_angle import ShapeResult, evaluate_stainless_angle
from frp_master_connection.calculation.stainless_plate import (
    PlateContext,
    PlateRequest,
    PlateResult,
    evaluate_stainless_plate,
)
from frp_master_connection.calculation.stainless_plate_clear_body import (
    ClearContext,
    ClearRequest,
    ClearResult,
    evaluate_clear_plate,
)
from frp_master_connection.calculation.stainless_response import (
    ResponseContext,
    ResponseRequest,
    ResponseResult,
    evaluate_stainless_response,
)
from frp_master_connection.calculation.stainless_tee import evaluate_stainless_tee
from frp_master_connection.domain.connector_materials import ConnectorMaterial
from frp_master_connection.domain.stainless_material import stainless_material
from frp_master_connection.domain.stainless_shape import ShapeContext, ShapeRequest

AUTHORITY = "CME_3_316SS_PUBLIC_CONNECTOR_BODY_ACTIVATION_RC1"
AVAILABLE = "STAINLESS_CONDITIONAL_PROVIDER_AVAILABLE"
STACKS = {
    "PLATE": ("C2_M", "C2_R", "C2_P1", "C2_P2_AS_APPLICABLE"),
    "ANGLE": ("C2_R", "C2_A", "C2_P1_P2_LOCAL_AS_APPLICABLE"),
    "TEE": ("C2_R", "C2_T", "C2_P1_P2_LOCAL_AS_APPLICABLE"),
}
ROUTES = {
    "beam-web-splice": "PLATE",
    "wi-major-axis-moment-splice": "PLATE",
    "channel-major-axis-moment-splice": "PLATE",
    "clip-angle": "ANGLE",
    "paired-clip-angle": "ANGLE",
    "beam-concrete-paired-angle": "ANGLE",
    "column-base-web-angles": "ANGLE",
    "wi-beam-concrete-wall-moment": "ANGLE",
    "wi-beam-frp-support-moment": "ANGLE",
    "angle-column-two-leg-moment-base": "ANGLE",
    "wi-rhs-srs-column-moment-base": "ANGLE",
    "tee-connector": "TEE",
    "multi-member-tee": "TEE",
}


class PublicMaterialBoundaryError(ValueError):
    """Additive CME-3 status while retaining the exact native denial message."""

    def __init__(self, code: str, native_message: str) -> None:
        super().__init__(native_message)
        self.code = code


def public_role_denial(error: ValueError) -> ValueError:
    """Translate only known role denials, never alter native planner behavior."""
    codes = {
        "ROLE_SUBSTITUTION_FORBIDDEN:PRIMARY_MEMBER": "PRIMARY_MEMBER_MATERIAL_MUST_REMAIN_FRP",
        "ROLE_SUBSTITUTION_FORBIDDEN:FASTENER_OR_HARDWARE": (
            "CONNECTOR_BODY_MATERIAL_CANNOT_REPLACE_FASTENER_AUTHORITY"
        ),
        "ROLE_SUBSTITUTION_FORBIDDEN:FOUNDATION": (
            "CONNECTOR_BODY_MATERIAL_CANNOT_REPLACE_FOUNDATION_AUTHORITY"
        ),
    }
    code = codes.get(str(error))
    return error if code is None else PublicMaterialBoundaryError(code, str(error))


def canonical_material(value: str | None) -> str:
    """Selection is not a material certificate or a source/property record."""
    if value is None or value == "FRP":
        return "FRP"
    try:
        stainless_material("316SS" if value == "SS316" else value)
    except ValueError as error:
        raise ValueError("CONNECTOR_BODY_MATERIAL_NOT_SUPPORTED") from error
    return "SS316"


def activate_plan(plan: ConnectorMaterialPlan) -> ConnectorMaterialPlan:
    """Preserve the exact historical FRP/no-body plan; change only SS316 plans."""
    materials = {t.material.family for t in plan.targets}
    if ConnectorMaterial.SS316 not in materials:
        return plan
    if len(materials) != 1:
        raise ValueError("STAINLESS_MIXED_CONNECTOR_BODY_MATERIALS_NOT_SUPPORTED_IN_CME3_RC1")
    form = ROUTES.get(plan.mode)
    if form is None or any(t.body_form != form for t in plan.targets):
        raise ValueError("STAINLESS_ACTIVATION_BODY_IDENTITY_MISMATCH")
    targets = tuple(replace(t, provider_status=AVAILABLE) for t in plan.targets)
    return replace(
        plan,
        targets=targets,
        fingerprint=angle_fingerprint((AUTHORITY, plan.fingerprint, targets)),
    )


@dataclass(frozen=True, slots=True)
class RequiredCheck:
    """One already-evaluated supported check, not an invented response/capacity."""

    id: str
    domain: str
    comparison: str
    provider_fingerprint: str


def connection_summary(
    checks: tuple[RequiredCheck, ...], blockers: tuple[str, ...], *, complete: bool
) -> str:
    """Known numerical failure outranks missing qualification in every domain."""
    identities = tuple((check.domain, check.id) for check in checks)
    if len(set(identities)) != len(identities):
        raise ValueError("STAINLESS_ACTIVATION_DUPLICATE_REQUIRED_CHECK")
    if any(check.comparison not in {"PASS", "FAIL"} for check in checks):
        raise ValueError("STAINLESS_ACTIVATION_UNEVALUATED_CHECK_IS_NOT_NUMERICAL")
    if any(check.comparison == "FAIL" for check in checks):
        return "FAIL"
    if blockers or not complete or not checks:
        return "ENGINEERING_REVIEW_REQUIRED"
    return "PASS"


@dataclass(frozen=True, slots=True)
class BodyBinding:
    """Server-derived physical identity; never deserialized from a public payload.

    Native identity contains that unit path's accepted action/geometry state.
    Owner-corrected I11 preserves inherited cross-unit differences verbatim;
    presentation-only changes do not re-author or re-execute this identity.
    """

    route: str
    body: str
    form: str
    native_identity: str

    def __post_init__(self) -> None:
        if ROUTES.get(self.route) != self.form or not self.body:
            raise ValueError("STAINLESS_ACTIVATION_BODY_IDENTITY_MISMATCH")
        if len(self.native_identity) != 64 or any(
            c not in "0123456789abcdef" for c in self.native_identity
        ):
            raise ValueError("STAINLESS_ACTIVATION_SNAPSHOT_STALE")


@dataclass(frozen=True, slots=True)
class PlateInvocation:
    request: PlateRequest
    context: PlateContext


@dataclass(frozen=True, slots=True)
class ClearInvocation:
    request: ClearRequest
    context: ClearContext


@dataclass(frozen=True, slots=True)
class ShapeInvocation:
    request: ShapeRequest
    context: ShapeContext


@dataclass(frozen=True, slots=True)
class BodyAuthority:
    """Bound internal resolver output, not a public qualification interface.

    The frozen providers validate their exact request/source records again.
    The activation layer additionally enforces current canonical body identity
    and the actual C2-R fingerprint consumed by the body provider. There is no
    mutable global registry and no public registration/deserialization path.
    """

    binding: BodyBinding
    response_request: ResponseRequest
    response_context: ResponseContext
    plate: PlateInvocation | None = None
    clear: ClearInvocation | None = None
    shape: ShapeInvocation | None = None


def unresolved_native_response(
    binding: BodyBinding, input_wrench: AngleWrench, source_identity: str
) -> BodyAuthority:
    """Reach the frozen response gate without inventing a qualified distribution.

    The exact native input wrench is evidence, not a stainless body/bolt response.
    No output wrench, stiffness, contact, product certificate or source record is
    manufactured. An empty trusted context intentionally returns C2-R's native
    source-required status before numerical resistance can run.
    """
    request = ResponseRequest(
        route=binding.route,
        bodies=(binding.body,),
        material_sha256=angle_fingerprint(("SS316", "SELECTION_ONLY")),
        product_sha256=angle_fingerprint(("UNQUALIFIED_PRODUCT", binding.form)),
        geometry_sha256=binding.native_identity,
        action_id=source_identity,
        load_combination="NATIVE_ACTION_AS_SUPPLIED",
        frame="NATIVE_RIGHT_HAND",
        input_wrench=input_wrench,
        output_wrenches=(),
        mode="QUALIFIED_EXTERNAL_MATERIAL_SPECIFIC_RESPONSE",
    )
    return BodyAuthority(binding, request, ResponseContext())


@dataclass(frozen=True, slots=True)
class ActivatedBodyResult:
    binding: BodyBinding
    response: ResponseResult | None
    plate: PlateResult | None
    clear: ClearResult | None
    shape: ShapeResult | None
    checks: tuple[RequiredCheck, ...]
    blockers: tuple[str, ...]
    fingerprint: str
    material: str = "SS316"
    activation_authority: str = AUTHORITY
    activation: str = "ACTIVE_CONDITIONAL"
    frp_body_resistance_used: bool = False


def evaluate_bound_body(
    binding: BodyBinding, authority: BodyAuthority | None
) -> ActivatedBodyResult:
    """Dispatch frozen C2 providers verbatim; never solve a second numeric path.

    Missing production section/response records are a truthful result. A source
    cannot qualify a different body, geometry/action state, or provider request.
    """
    response: ResponseResult | None = None
    plate: PlateResult | None = None
    clear: ClearResult | None = None
    shape: ShapeResult | None = None
    checks: list[RequiredCheck] = []
    blockers: list[str] = []
    if authority is None:
        blockers.append("STAINLESS_RESPONSE_SOURCE_REQUIRED")
        if binding.form in {"ANGLE", "TEE"}:
            blockers.append("STAINLESS_SHAPE_SECTION_PROPERTIES_NOT_QUALIFIED")
        else:
            blockers.append("STAINLESS_PLATE_RESOLVED_PLAN_SOURCE_REQUIRED")
    else:
        if authority.binding.route != binding.route or authority.binding.body != binding.body:
            raise ValueError("STAINLESS_ACTIVATION_BODY_IDENTITY_MISMATCH")
        if authority.binding != binding:
            raise ValueError("STAINLESS_ACTIVATION_SNAPSHOT_STALE")
        r = authority.response_request
        if r.route != binding.route or binding.body not in r.bodies:
            raise ValueError("STAINLESS_ACTIVATION_BODY_IDENTITY_MISMATCH")
        if r.geometry_sha256 != binding.native_identity:
            raise ValueError("STAINLESS_ACTIVATION_SNAPSHOT_STALE")
        # Public activation belongs here, not in frozen C2 request flags.
        response = evaluate_stainless_response(r, authority.response_context)
        if response.status != "QUALIFIED_RESPONSE":
            blockers.append(response.status)
            if binding.form in {"ANGLE", "TEE"}:
                blockers.append("STAINLESS_SHAPE_SECTION_PROPERTIES_NOT_QUALIFIED")
        else:
            if binding.form == "PLATE":
                if authority.shape is not None:
                    raise ValueError("STAINLESS_ACTIVATION_BODY_IDENTITY_MISMATCH")
                if authority.plate is None:
                    blockers.append("STAINLESS_PLATE_RESOLVED_PLAN_SOURCE_REQUIRED")
                else:
                    p = authority.plate
                    if p.request.geometry.id != binding.body:
                        raise ValueError("STAINLESS_ACTIVATION_BODY_IDENTITY_MISMATCH")
                    records = tuple(x for x in p.context.records if x.request == p.request)
                    if len(records) != 1 or records[0].demand_authority != response.fingerprint:
                        blockers.append("STAINLESS_RESPONSE_MATERIAL_DEPENDENCE_UNRESOLVED")
                    else:
                        plate = evaluate_stainless_plate(p.request, p.context)
                        for check in plate.checks:
                            checks.append(
                                RequiredCheck(
                                    f"{binding.body}:C2_P1:{check.id}:{check.method}",
                                    "BODY",
                                    check.comparison,
                                    plate.fingerprint,
                                )
                            )
                        blockers.extend(
                            (*plate.method_status, *plate.demand_status, *plate.response_status)
                        )
                        if plate.geometry_status != "VALID":
                            blockers.append(plate.geometry_status)
                        if plate.material_source_status != "VERIFIED":
                            blockers.append(plate.material_source_status)
                        if not plate.checks and not blockers:
                            blockers.append("STAINLESS_CHECK_PLAN_NOT_RESOLVED")
                if authority.clear is not None:
                    c = authority.clear
                    if c.request.section.id != binding.body:
                        raise ValueError("STAINLESS_ACTIVATION_BODY_IDENTITY_MISMATCH")
                    # P2 authority is pre-resolved; it must be bound to this R
                    # result, not a same-named legacy FRP response.
                    if c.request.demand.response_method != response.fingerprint:
                        blockers.append("STAINLESS_RESPONSE_MATERIAL_DEPENDENCE_UNRESOLVED")
                    else:
                        clear = evaluate_clear_plate(c.request, c.context)
                        if clear.numerical_comparison in {"ISOLATED_COVERED_CHECKS_PASS", "FAIL"}:
                            checks.append(
                                RequiredCheck(
                                    f"{binding.body}:C2_P2",
                                    "BODY",
                                    "FAIL" if clear.numerical_comparison == "FAIL" else "PASS",
                                    clear.fingerprint,
                                )
                            )
                        blockers.extend(
                            (*clear.method_status, *clear.demand_status, *clear.response_status)
                        )
                        if clear.geometry_status != "VALID":
                            blockers.append(clear.geometry_status)
                        if clear.material_source_status != "VERIFIED":
                            blockers.append(clear.material_source_status)
                        if not clear.checks and not blockers:
                            blockers.append("STAINLESS_CHECK_PLAN_NOT_RESOLVED")
            else:
                if authority.plate is not None or authority.clear is not None:
                    raise ValueError("STAINLESS_ACTIVATION_BODY_IDENTITY_MISMATCH")
                if authority.shape is None:
                    blockers.append("STAINLESS_SHAPE_SECTION_PROPERTIES_NOT_QUALIFIED")
                else:
                    s = authority.shape
                    if (
                        s.request.section.form != binding.form
                        or s.request.demand.body != binding.body
                        or s.request.demand.route != binding.route
                    ):
                        raise ValueError("STAINLESS_ACTIVATION_BODY_IDENTITY_MISMATCH")
                    records_s = tuple(x for x in s.context.records if x.request == s.request)
                    if (
                        len(records_s) != 1
                        or records_s[0].response_fingerprint != response.fingerprint
                    ):
                        blockers.append("STAINLESS_RESPONSE_MATERIAL_DEPENDENCE_UNRESOLVED")
                    else:
                        evaluator = (
                            evaluate_stainless_angle
                            if binding.form == "ANGLE"
                            else evaluate_stainless_tee
                        )
                        shape = evaluator(s.request, s.context)
                        if shape.status in {"FAIL", "ISOLATED_COVERED_CHECKS_PASS"}:
                            checks.append(
                                RequiredCheck(
                                    f"{binding.body}:{shape.provider}",
                                    "BODY",
                                    "FAIL" if shape.status == "FAIL" else "PASS",
                                    shape.fingerprint,
                                )
                            )
                        else:
                            blockers.append(shape.status)
    return ActivatedBodyResult(
        binding,
        response,
        plate,
        clear,
        shape,
        tuple(checks),
        tuple(blockers),
        angle_fingerprint(
            (
                AUTHORITY,
                "SS316",
                binding,
                response,
                plate,
                clear,
                shape,
                tuple(checks),
                tuple(blockers),
            )
        ),
    )
