"""Additive CME-1 capability and stateless planning transport; no design endpoint."""

import json
from dataclasses import asdict
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import JsonValue, StrictStr

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.dependencies import build_trusted_identity_dependency
from frp_master_connection.api.schemas import _StrictModel
from frp_master_connection.application.connector_material_assembly import (
    NO_BODY_ROUTES,
    canonical_material_assembly,
)
from frp_master_connection.application.stainless_family_activation import (
    AUTHORITY,
    AVAILABLE,
    STACKS,
    PublicMaterialBoundaryError,
    activate_plan,
    public_role_denial,
)
from frp_master_connection.calculation.connector_material_plan import (
    MaterialAssignment,
    plan_connector_materials,
)
from frp_master_connection.domain.connector_materials import (
    ComponentRole,
    ConnectorMaterial,
    Fabrication,
    MaterialDescriptor,
    ResponseSignature,
)
from frp_master_connection.security import TrustedIdentity, TrustedIdentityResolver


class MaterialDescriptorDTO(_StrictModel):
    family: ConnectorMaterial = ConnectorMaterial.FRP
    grade: StrictStr = "PULTRUDED_FRP"
    stock_specification: StrictStr = "EXISTING_NATIVE_FRP_AUTHORITY"
    edition: StrictStr = "NATIVE"
    fabrication: Fabrication = Fabrication.PULTRUDED
    condition: StrictStr = "NATIVE_LOCKED_RECORD"
    source_reference: StrictStr | None = None
    method_version: StrictStr = "NATIVE_FRP"

    def domain(self) -> MaterialDescriptor:
        return MaterialDescriptor(
            self.family,
            self.grade,
            self.stock_specification,
            self.edition,
            self.fabrication,
            self.condition,
            self.source_reference,
            self.method_version,
        )


class MaterialAssignmentDTO(_StrictModel):
    component_id: StrictStr
    material: MaterialDescriptorDTO


class MaterialPlanRequestDTO(_StrictModel):
    contract: Literal["CME-1-RC1"] = "CME-1-RC1"
    route_id: StrictStr
    product_id: StrictStr
    native_input: dict[str, JsonValue]
    assignments: tuple[MaterialAssignmentDTO, ...] = ()
    apply_all: MaterialDescriptorDTO | None = None


class MaterialResponseDTO(_StrictModel):
    contract: Literal["CME-1-RC1"] = "CME-1-RC1"
    result: dict[str, JsonValue]
    resistance_evaluated: Literal[False] = False
    persisted: Literal[False] = False


def mode_contract(schema: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """All finite native schema choices, including modes hidden by legacy editors.

    The independently archived inventory declares these choices. Coverage tests
    compare it to the runtime schema and fail on undeclared new modes/products.
    Geometry validity/applicability remains the native mapper's responsibility.
    """
    choices: dict[str, JsonValue] = {}

    def visit(value: JsonValue, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"enum", "const"}:
                    choices[path + "/" + key] = child
                elif key not in {"description", "title", "default", "examples"}:
                    visit(child, path + "/" + key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, path + f"/{index}")

    visit(schema, "")
    return choices


def capabilities() -> dict[str, JsonValue]:
    return {
        "phase": "CME-3_CONDITIONAL_PUBLIC_ACTIVATION",
        "primary_members": "FRP_ONLY",
        "roles": [role.value for role in ComponentRole],
        "frp": "NATIVE_EXISTING_SCOPE_UNCHANGED",
        "SS316": AVAILABLE,
        "stainless_editor_enabled": False,
        "connector_body_material_selector_enabled": True,
        "connector_body_materials": ["FRP", "316 Stainless Steel"],
        "stainless_activation": "CONDITIONAL",
        "activation_authority": AUTHORITY,
        "hardware_authority": "INDEPENDENT",
        "foundation_authority": "INDEPENDENT",
        "custom_stainless_properties_editable": False,
        "reinforcement": "FRP_REINFORCEMENT_RESTRICTED_QUALIFIED_ALTERNATIVE_REQUIRED",
        "families": [
            {
                "route_id": family.route_id,
                "product_id": family.product_id,
                "category": family.category,
                "disposition": "NO_CONNECTOR_BODY"
                if family.route_id in NO_BODY_ROUTES
                else "CONNECTOR_BODY_CONDITIONAL_ACTIVATION",
                "native_entry_points": list(family.native_entry_points),
                "declared_native_modes": mode_contract(family.schema),
                "stainless": "CONNECTOR_BODY_MATERIAL_NOT_APPLICABLE_TO_ROUTE"
                if family.route_id in NO_BODY_ROUTES
                else AVAILABLE,
            }
            for family in FAMILIES.values()
        ],
    }


def material_plan(request: MaterialPlanRequestDTO) -> dict[str, JsonValue]:
    family = FAMILIES.get(request.route_id)
    if family is None or family.product_id != request.product_id:
        raise ValueError("Undeclared or inconsistent product/native route identity")
    preview = family.preview(request.native_input)
    assembly = canonical_material_assembly(request.route_id, preview)
    # Mode and geometry identity are derived by the native builder, not a
    # client-provided semantic role or asserted geometry fingerprint.
    plan = plan_connector_materials(
        family.product_id,
        family.route_id,
        assembly.components,
        tuple(MaterialAssignment(a.component_id, a.material.domain()) for a in request.assignments),
        geometry_identity=assembly.scene_identity,
        apply_all=None if request.apply_all is None else request.apply_all.domain(),
        responses=(
            (
                "NATIVE_ASSEMBLY_RESPONSE_QUALIFICATION",
                ResponseSignature(
                    tuple(
                        (c.physical_id, c.material)
                        for c in assembly.components
                        if c.role is ComponentRole.CONNECTOR_BODY
                    ),
                    assembly.scene_identity,
                    assembly.native_identity,
                    "NATIVE_BOUNDARY_CONDITIONS_UNCHANGED",
                    "NATIVE_SIGNED_ACTION_DOMAIN",
                    "NATIVE_FAMILY_RESPONSE",
                ),
            ),
        ),
    )
    plan = activate_plan(plan)
    result = cast(dict[str, JsonValue], json.loads(json.dumps(asdict(plan))))
    if any(t.material.family is ConnectorMaterial.SS316 for t in plan.targets):
        result["activation_authority"] = AUTHORITY
        targets = cast(list[dict[str, JsonValue]], result["targets"])
        for target, native_target in zip(targets, plan.targets, strict=True):
            target["required_provider_stack"] = list(STACKS[native_target.body_form])
            target["activation_authority"] = AUTHORITY
    result["canonical_components"] = cast(
        JsonValue, json.loads(json.dumps(asdict(assembly)["components"]))
    )
    result["native_identity_unchanged"] = assembly.native_identity
    # Connector descriptors are not fastener, foundation or member property records.
    # Expose the native role's independent policy rather than a fictitious FRP bolt.
    records = cast(list[dict[str, JsonValue]], result["canonical_components"])
    for component in records:
        if component["role"] != ComponentRole.CONNECTOR_BODY:
            component["material"] = None
            component["native_material_policy"] = (
                "FRP_ONLY"
                if component["role"] == ComponentRole.PRIMARY_MEMBER
                else "NATIVE_RESTRICTED_REINFORCEMENT"
                if component["role"] == ComponentRole.MEMBER_REINFORCEMENT
                else "INDEPENDENT_NATIVE_AUTHORITY_NOT_CONNECTOR_MATERIAL"
            )
    result["native_response_reuse"] = (
        "REVALIDATION_REQUIRED" if plan.required_future_coverage else "NATIVE_FRP_SCOPE_ONLY"
    )
    return result


def build_connector_material_router(identity_resolver: TrustedIdentityResolver) -> APIRouter:
    router = APIRouter(prefix="/api/v1/connector-materials")
    identity_dependency = build_trusted_identity_dependency(identity_resolver)

    @router.get("/capabilities", response_model=MaterialResponseDTO)
    async def read_capabilities(
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> MaterialResponseDTO:
        return MaterialResponseDTO(result=capabilities())

    @router.post("/plan", response_model=MaterialResponseDTO)
    async def plan(
        request: MaterialPlanRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> MaterialResponseDTO:
        try:
            return MaterialResponseDTO(result=material_plan(request))
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            # Keep native planning and FRP responses unchanged. Only the
            # successor HTTP status channel names the approved role boundary.
            mapped = (
                public_role_denial(error)
                if isinstance(error, ValueError)
                and any(a.material.family is ConnectorMaterial.SS316 for a in request.assignments)
                else error
            )
            raise HTTPException(
                status_code=422,
                detail={
                    "code": mapped.code
                    if isinstance(mapped, PublicMaterialBoundaryError)
                    else "CONNECTOR_MATERIAL_PLAN_INVALID",
                    "message": str(error),
                },
            ) from error

    return router
