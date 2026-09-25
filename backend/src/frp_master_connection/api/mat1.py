"""MAT1 catalog and diagnostic adjustment transport.

The factor endpoint makes numerical candidates visible; it never certifies a
source or substitutes for a connection design check.
"""

from collections.abc import Callable
from dataclasses import asdict, replace
from decimal import Decimal
from typing import Annotated, Any, Literal, Self, cast

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import Field, JsonValue, StrictStr, model_validator

from frp_master_connection.api.angle_column_moment_base import serialize_angle_base
from frp_master_connection.api.beam_concrete_paired_angle_mapping import (
    serialize_beam_concrete_paired_angle_design,
)
from frp_master_connection.api.calculation_mapping import (
    map_single_bolt_request,
    serialize_single_bolt_response,
)
from frp_master_connection.api.channel_moment_splice_mapping import (
    serialize_channel_moment_splice_design,
)
from frp_master_connection.api.clip_angle_mapping import serialize_clip_angle_design
from frp_master_connection.api.column_base_web_angle_mapping import (
    serialize_column_base_web_angle_design,
)
from frp_master_connection.api.column_moment_base import serialize_column_moment_base
from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.dctn3b import dctn3b_response
from frp_master_connection.api.dependencies import build_trusted_identity_dependency
from frp_master_connection.api.direct_side_lap_concrete_mapping import (
    serialize_direct_side_lap_concrete_design,
)
from frp_master_connection.api.double_channel_truss_node import dctn_response
from frp_master_connection.api.multi_member_tee_mapping import (
    serialize_multi_member_tee_design,
)
from frp_master_connection.api.multirow_mapping import (
    map_multirow_request,
    serialize_multirow_design,
)
from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO
from frp_master_connection.api.paired_clip_angle_mapping import (
    serialize_paired_clip_angle_design,
)
from frp_master_connection.api.schemas import (
    QuantityDTO,
    SingleBoltEvaluationRequestDTO,
    _StrictModel,
)
from frp_master_connection.api.ssmc import (
    SSMCAnalyticalRequestDTO,
    map_ssmc_request,
    serialize_ssmc_value,
)
from frp_master_connection.api.tee_mapping import (
    map_tee_connector_request,
    serialize_tee_connector_design,
)
from frp_master_connection.api.tee_schemas import TeeConnectorRequestDTO
from frp_master_connection.api.web_splice_mapping import serialize_web_splice_design
from frp_master_connection.api.wi_frp_support_moment_mapping import (
    serialize_wi_frp_support_moment,
)
from frp_master_connection.api.wi_moment_splice_mapping import (
    serialize_wi_moment_splice_design,
)
from frp_master_connection.api.wi_wall_moment_mapping import serialize_wi_wall_moment
from frp_master_connection.application import (
    build_single_bolt_visualization_snapshot,
    evaluate_multirow_connection,
    evaluate_single_bolt_connection,
)
from frp_master_connection.application.connector_material_assembly import (
    canonical_material_assembly,
)
from frp_master_connection.application.dctn3b import DCTN3BDesign
from frp_master_connection.application.mat1_materials import (
    DesignConditions,
    MaterialRecord,
    PropertyLedger,
    Resin,
    catalog_record,
    decimal_input,
    predefined_catalog,
    property_ledger,
    session_record,
    temperature_fahrenheit,
)
from frp_master_connection.application.mat1_multirow import bind_multirow_material
from frp_master_connection.application.mat1_native import adapt_native_material
from frp_master_connection.application.mat1_scope import MAT1Scope, bind_mat1_scope
from frp_master_connection.application.ssmc_analytical import (
    SSMCAnalyticalRequest,
    SSMCDesignAction,
    SSMCSingleLapDeclaration,
    evaluate_ssmc_analytical,
)
from frp_master_connection.application.tee_orchestration import design_check_tee_connector
from frp_master_connection.calculation.inputs import TimeEffectCategory
from frp_master_connection.calculation.quantities import PhysicalQuantity
from frp_master_connection.domain.connector_materials import ComponentRole
from frp_master_connection.security import TrustedIdentity, TrustedIdentityResolver


class CatalogSelectionDTO(_StrictModel):
    kind: Literal["CATALOG"]
    id: StrictStr
    revision: StrictStr
    content_digest: StrictStr


class SessionSelectionDTO(_StrictModel):
    kind: Literal["SESSION"]
    id: StrictStr
    revision: StrictStr
    display_name: StrictStr
    company: StrictStr
    resin: Resin
    properties: dict[str, dict[str, StrictStr]]
    copied_from: StrictStr | None = None


MaterialSelectionDTO = Annotated[
    CatalogSelectionDTO | SessionSelectionDTO, Field(discriminator="kind")
]


_FAMILY_SERIALIZERS: dict[str, Callable[[Any], Any]] = {
    "clip-angle": serialize_clip_angle_design,
    "paired-clip-angle": serialize_paired_clip_angle_design,
    "multi-member-tee": serialize_multi_member_tee_design,
    "beam-concrete-paired-angle": serialize_beam_concrete_paired_angle_design,
    "direct-side-lap-concrete": serialize_direct_side_lap_concrete_design,
    "column-base-web-angles": serialize_column_base_web_angle_design,
    "beam-web-splice": serialize_web_splice_design,
    "wi-major-axis-moment-splice": serialize_wi_moment_splice_design,
    "channel-major-axis-moment-splice": serialize_channel_moment_splice_design,
    "wi-beam-concrete-wall-moment": serialize_wi_wall_moment,
    "wi-beam-frp-support-moment": serialize_wi_frp_support_moment,
    "angle-column-two-leg-moment-base": serialize_angle_base,
    "wi-rhs-srs-column-moment-base": serialize_column_moment_base,
    "double-channel-truss-node": lambda native: (
        dctn3b_response(native) if isinstance(native, DCTN3BDesign) else dctn_response(native)
    ),
}


class MaterialTemperatureDTO(_StrictModel):
    value: StrictStr
    unit: Literal["degF", "degC"]


class MaterialConditionsDTO(_StrictModel):
    sustained_temperature: MaterialTemperatureDTO
    maximum_temperature: MaterialTemperatureDTO
    glass_transition_temperature: MaterialTemperatureDTO | None
    moisture: Literal["REFERENCE", "SUSTAINED_MOISTURE", "OTHER", "UNKNOWN"]
    chemical: Literal["NONE_DECLARED", "SPECIFIED", "UNKNOWN"]
    load_case_name: StrictStr
    time_effect_category: TimeEffectCategory
    source_reference_condition: Literal["REFERENCE", "ALREADY_ADJUSTED", "UNKNOWN"]
    chemical_substance: StrictStr = ""
    chemical_concentration: StrictStr = ""
    chemical_contact_form: StrictStr = ""
    chemical_duration: StrictStr = ""
    uv_weathering: Literal["NONE_DECLARED", "SPECIFIED", "UNKNOWN"] = "UNKNOWN"
    freeze_thaw: Literal["NONE_DECLARED", "SPECIFIED", "UNKNOWN"] = "UNKNOWN"
    protective_measures: StrictStr = ""
    exposure_notes: StrictStr = ""
    action_provenance: StrictStr = ""
    live_load_subtype: StrictStr = ""
    full_amplitude_duration: StrictStr = ""
    design_period: StrictStr = ""
    service_period: StrictStr = ""
    fatigue_cycles: StrictStr = ""

    @model_validator(mode="after")
    def validate_temperatures(self) -> Self:
        if temperature_fahrenheit(
            self.maximum_temperature.value, self.maximum_temperature.unit
        ) < temperature_fahrenheit(
            self.sustained_temperature.value, self.sustained_temperature.unit
        ):
            raise ValueError("MAT1 maximum material temperature is below sustained temperature.")
        if not self.load_case_name.strip():
            raise ValueError("MAT1 load case name must be nonempty.")
        return self


class FactorRequestDTO(_StrictModel):
    contract: Literal["MAT1-FACTOR-RC0"]
    material: MaterialSelectionDTO
    conditions: MaterialConditionsDTO
    component_id: StrictStr
    property_ids: tuple[StrictStr, ...]

    @model_validator(mode="after")
    def validate_ids(self) -> Self:
        if not self.component_id.strip() or not self.property_ids:
            raise ValueError("MAT1 factor inspection needs a component and properties.")
        if len(set(self.property_ids)) != len(self.property_ids):
            raise ValueError("MAT1 property IDs must be unique.")
        return self


class MaterialAssignmentsDTO(_StrictModel):
    default_material: MaterialSelectionDTO
    material_overrides: dict[StrictStr, MaterialSelectionDTO] = Field(default_factory=dict)
    default_conditions: MaterialConditionsDTO
    condition_overrides: dict[StrictStr, MaterialConditionsDTO] = Field(default_factory=dict)


class SingleBoltMAT1RequestDTO(_StrictModel):
    contract: Literal["MAT1-SINGLE-BOLT-RC0"]
    legacy_request: SingleBoltEvaluationRequestDTO
    assignments: MaterialAssignmentsDTO


class MultiRowMAT1RequestDTO(_StrictModel):
    contract: Literal["MAT1-MULTI-ROW-RC0"]
    legacy_request: MultiRowConnectionRequestDTO
    assignments: MaterialAssignmentsDTO


class TeeMAT1RequestDTO(_StrictModel):
    contract: Literal["MAT1-TEE-RC0"]
    legacy_request: TeeConnectorRequestDTO
    assignments: MaterialAssignmentsDTO


class FamilyMAT1RequestDTO(_StrictModel):
    contract: Literal["MAT1-FAMILY-RC0"]
    family_id: StrictStr
    legacy_request: dict[str, JsonValue]
    assignments: MaterialAssignmentsDTO


class OwnerPreviewDTO(_StrictModel):
    contract: Literal["MAT1-OWNER-PREVIEW-RC0"]
    family_id: StrictStr
    legacy_request: dict[str, JsonValue]


class SSMCMAT1RequestDTO(_StrictModel):
    contract: Literal["MAT1-SSMC-ANALYTICAL-RC0"]
    legacy_request: SSMCAnalyticalRequestDTO
    assignments: MaterialAssignmentsDTO


def resolve_material(selection: CatalogSelectionDTO | SessionSelectionDTO) -> MaterialRecord:
    if isinstance(selection, CatalogSelectionDTO):
        return catalog_record(selection.id, selection.revision, selection.content_digest)
    return session_record(
        selection.id,
        selection.revision,
        selection.display_name,
        selection.company,
        selection.resin,
        {key: dict(value) for key, value in selection.properties.items()},
        selection.copied_from,
    )


def resolve_conditions(dto: MaterialConditionsDTO) -> DesignConditions:
    return DesignConditions(
        sustained_f=temperature_fahrenheit(
            dto.sustained_temperature.value, dto.sustained_temperature.unit
        ),
        maximum_f=temperature_fahrenheit(
            dto.maximum_temperature.value, dto.maximum_temperature.unit
        ),
        tg_f=(
            temperature_fahrenheit(
                dto.glass_transition_temperature.value,
                dto.glass_transition_temperature.unit,
            )
            if dto.glass_transition_temperature is not None
            else None
        ),
        moisture=dto.moisture,
        chemical=dto.chemical,
        load_case_name=dto.load_case_name,
        time_category=dto.time_effect_category,
        source_reference_condition=dto.source_reference_condition,
        chemical_substance=dto.chemical_substance,
        chemical_concentration=dto.chemical_concentration,
        chemical_contact_form=dto.chemical_contact_form,
        chemical_duration=dto.chemical_duration,
        uv_weathering=dto.uv_weathering,
        freeze_thaw=dto.freeze_thaw,
        protective_measures=dto.protective_measures,
        exposure_notes=dto.exposure_notes,
        action_provenance=dto.action_provenance,
        live_load_subtype=dto.live_load_subtype,
        full_amplitude_duration=dto.full_amplitude_duration,
        design_period=dto.design_period,
        service_period=dto.service_period,
        fatigue_cycles=dto.fatigue_cycles,
    )


def resolve_scope(dto: MaterialAssignmentsDTO, family_id: str = "") -> MAT1Scope:
    default = (resolve_material(dto.default_material), resolve_conditions(dto.default_conditions))
    overrides = {
        owner_id: (
            resolve_material(dto.material_overrides.get(owner_id, dto.default_material)),
            resolve_conditions(dto.condition_overrides.get(owner_id, dto.default_conditions)),
        )
        for owner_id in set(dto.material_overrides) | set(dto.condition_overrides)
    }
    if any(
        condition.time_category != default[1].time_category for _, condition in overrides.values()
    ):
        raise ValueError("MAT1_ONE_LOAD_CASE_CANNOT_HAVE_CONFLICTING_TIME_CATEGORIES")
    return MAT1Scope(default, overrides, family_id)


def bind_physical_owners(scope: MAT1Scope, family_id: str, preview: object) -> None:
    assembly = canonical_material_assembly(family_id, preview)
    scope.canonical_owners = frozenset(
        component.physical_id
        for component in assembly.components
        if component.role in {ComponentRole.PRIMARY_MEMBER, ComponentRole.CONNECTOR_BODY}
    )


def complete_owner_ledger(scope: MAT1Scope) -> None:
    """Report all physical owners while preserving evidence of actual consumers."""

    if scope.canonical_owners is None:
        raise ValueError("MAT1_PHYSICAL_OWNERS_NOT_BOUND")
    consumed = frozenset(scope.adapters)
    for owner_id in sorted(scope.canonical_owners):
        if owner_id not in consumed:
            scope.issues.append(f"MAT1_OWNER_NOT_NUMERICALLY_CONSUMED:{owner_id}")
        scope.material(owner_id)


def _json_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def _quantity(value: QuantityDTO) -> PhysicalQuantity:
    return PhysicalQuantity.of(value.value, value.unit)


def build_mat1_router(identity_resolver: TrustedIdentityResolver) -> APIRouter:
    """Expose server-owned records and diagnostic factors to the shared UI."""

    router = APIRouter(prefix="/api/v1/frp-materials")
    identity = build_trusted_identity_dependency(identity_resolver)

    @router.get("/catalog")
    async def catalog(
        _identity: Annotated[TrustedIdentity, Depends(identity)],
    ) -> dict[str, object]:
        return {
            "contract": "MAT1-CATALOG-RC0",
            "records": [
                _json_value(
                    {
                        **asdict(record),
                        "qualification": "OWNER_OR_CATALOG_DATA_NOT_SERVER_QUALIFIED",
                    }
                )
                for record in predefined_catalog()
            ],
        }

    @router.post("/factor-candidates")
    async def factors(
        request: FactorRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity)],
    ) -> dict[str, object]:
        try:
            record = resolve_material(request.material)
            conditions = resolve_conditions(request.conditions)
            ledgers = [
                property_ledger(request.component_id, record, prop_id, conditions)
                for prop_id in request.property_ids
            ]
        except (KeyError, TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail={"code": str(error)}) from error
        return {
            "contract": "MAT1-FACTOR-RC0",
            "result_status": "SOURCE_REQUIRED",
            "record_id": record.id,
            "record_revision": record.revision,
            "content_digest": record.content_digest,
            "load_case_name": conditions.load_case_name,
            "ledgers": [_json_value(asdict(item)) for item in ledgers],
            "design_check_performed": False,
        }

    @router.post("/family/owners")
    async def family_owners(
        request: OwnerPreviewDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity)],
    ) -> dict[str, object]:
        """Discover assignable FRP owners from native preview without resistance."""

        family = FAMILIES.get(request.family_id)
        if family is None:
            raise HTTPException(status_code=422, detail={"code": "MAT1_UNKNOWN_FAMILY"})
        try:
            if request.family_id == "single-bolt":
                family.preview(request.legacy_request)
                assignments = cast(list[JsonValue], request.legacy_request["material_assignments"])
                # The successful native preview has already validated this required list.
                owners = tuple(
                    ":".join(
                        (
                            str(item["participant_id"]),
                            str(item["physical_element_id"]),
                            str(item["material_region_id"]),
                        )
                    )
                    for item in assignments
                    if isinstance(item, dict)
                )
            else:
                assembly = canonical_material_assembly(
                    request.family_id, family.preview(request.legacy_request)
                )
                owners = tuple(
                    item.physical_id
                    for item in assembly.components
                    if item.role in {ComponentRole.PRIMARY_MEMBER, ComponentRole.CONNECTOR_BODY}
                )
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail={"code": str(error)}) from error
        return {
            "contract": "MAT1-OWNER-PREVIEW-RC0",
            "family_id": request.family_id,
            "owners": sorted(set(owners)),
            "design_check_performed": False,
        }

    @router.post("/single-bolt/design-check")
    async def single_bolt_design(
        request: SingleBoltMAT1RequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity)],
    ) -> dict[str, object]:
        """Use actual assigned property values in the existing native bolt checks."""

        legacy = request.legacy_request
        if (
            len(legacy.material_snapshots) != 1
            or legacy.material_snapshots[0].id != "ICE_LOCKED_PULTRUDED_FRP"
            or not legacy.material_snapshots[0].locked
        ):
            raise HTTPException(
                status_code=422, detail={"code": "MAT1_LEGACY_MATERIAL_DATA_MUST_BE_REFERENCE_ONLY"}
            )
        if any(
            decimal_input(value) != 1
            for value in (
                legacy.end_use_factors.cm,
                legacy.end_use_factors.ct,
                legacy.end_use_factors.cch,
            )
        ):
            raise HTTPException(status_code=422, detail={"code": "MAT1_DUAL_END_USE_FACTORS"})
        if (
            legacy.time_effect_category
            != request.assignments.default_conditions.time_effect_category
        ):
            raise HTTPException(status_code=422, detail={"code": "MAT1_DUAL_TIME_CATEGORY"})
        try:
            canonical = map_single_bolt_request(legacy)
            keys = {
                ":".join((item.participant_id, item.physical_element_id, item.material_region_id))
                for item in canonical.material_assignments
            }
            if (
                set(request.assignments.material_overrides) - keys
                or set(request.assignments.condition_overrides) - keys
            ):
                raise ValueError("MAT1_UNKNOWN_PHYSICAL_COMPONENT_OVERRIDE")
            adapted = []
            ledgers: list[PropertyLedger] = []
            issues: list[str] = []
            for item in canonical.material_assignments:
                key = ":".join(
                    (item.participant_id, item.physical_element_id, item.material_region_id)
                )
                selection = request.assignments.material_overrides.get(
                    key, request.assignments.default_material
                )
                condition = request.assignments.condition_overrides.get(
                    key, request.assignments.default_conditions
                )
                if (
                    condition.time_effect_category
                    != request.assignments.default_conditions.time_effect_category
                ):
                    raise ValueError("MAT1_ONE_LOAD_CASE_CANNOT_HAVE_CONFLICTING_TIME_CATEGORIES")
                adapter = adapt_native_material(
                    key, resolve_material(selection), resolve_conditions(condition)
                )
                adapted.append(replace(item, material_snapshot=adapter.adjusted_snapshot))
                ledgers.extend(adapter.ledgers)
                issues.extend(adapter.unresolved_issues)
            canonical = replace(canonical, material_assignments=tuple(adapted))
            native = evaluate_single_bolt_connection(canonical)
            visualization = build_single_bolt_visualization_snapshot(canonical, native)
            serialized = serialize_single_bolt_response(native, visualization)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail={"code": str(error)}) from error
        return {
            "contract": "MAT1-SINGLE-BOLT-RC0",
            "overall_status": "SOURCE_REQUIRED",
            "native_design": serialized.model_dump(mode="json"),
            "material_ledgers": [_json_value(asdict(item)) for item in ledgers],
            "material_issues": sorted(set(issues)),
            "design_check_performed": True,
        }

    @router.post("/multi-row/design-check")
    async def multirow_design(
        request: MultiRowMAT1RequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity)],
    ) -> dict[str, object]:
        """Bind a common source where this native method assumes identical layers."""

        legacy = request.legacy_request
        assigned = request.assignments
        layer_keys = {item.component_id for item in legacy.layers}
        if (
            set(assigned.material_overrides) - layer_keys
            or set(assigned.condition_overrides) - layer_keys
        ):
            raise HTTPException(status_code=422, detail={"code": "MAT1_UNKNOWN_PHYSICAL_LAYER"})
        if legacy.time_effect_category != assigned.default_conditions.time_effect_category:
            raise HTTPException(status_code=422, detail={"code": "MAT1_DUAL_TIME_CATEGORY"})
        if any(
            any(
                decimal_input(value) != 1
                for value in (
                    item.end_use_factors.cm,
                    item.end_use_factors.ct,
                    item.end_use_factors.cch,
                )
            )
            for item in legacy.layers
        ):
            raise HTTPException(status_code=422, detail={"code": "MAT1_DUAL_END_USE_FACTORS"})
        try:
            per_layer = [
                (
                    item.component_id,
                    resolve_material(
                        assigned.material_overrides.get(
                            item.component_id, assigned.default_material
                        )
                    ),
                    resolve_conditions(
                        assigned.condition_overrides.get(
                            item.component_id, assigned.default_conditions
                        )
                    ),
                )
                for item in legacy.layers
            ]
            identities = {
                (
                    record.id,
                    record.revision,
                    record.content_digest,
                    condition,
                )
                for _, record, condition in per_layer
            }
            if len(identities) != 1:
                raise ValueError("MAT1_MULTIROW_LINKED_LAYER_MATERIAL_OR_CONDITIONS_REQUIRED")
            adapters = [
                adapt_native_material(layer_id, record, condition)
                for layer_id, record, condition in per_layer
            ]
            canonical = bind_multirow_material(
                map_multirow_request(legacy), adapters[0].adjusted_snapshot
            )
            native = serialize_multirow_design(evaluate_multirow_connection(canonical))
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail={"code": str(error)}) from error
        return {
            "contract": "MAT1-MULTI-ROW-RC0",
            "overall_status": "SOURCE_REQUIRED",
            "native_design": native.model_dump(mode="json"),
            "material_ledgers": [
                _json_value(asdict(ledger)) for adapter in adapters for ledger in adapter.ledgers
            ],
            "material_issues": sorted(
                {issue for adapter in adapters for issue in adapter.unresolved_issues}
            ),
            "design_check_performed": True,
        }

    @router.post("/tee-connector/design-check")
    async def tee_design(
        request: TeeMAT1RequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity)],
    ) -> dict[str, object]:
        """Retain the native two-interface Tee mechanics with explicit MAT1 sources."""

        try:
            scope = resolve_scope(request.assignments, "tee-connector")
            with bind_mat1_scope(scope):
                bind_physical_owners(
                    scope,
                    "tee-connector",
                    FAMILIES["tee-connector"].preview(
                        request.legacy_request.model_dump(mode="json")
                    ),
                )
                native = design_check_tee_connector(
                    map_tee_connector_request(request.legacy_request)
                )
                complete_owner_ledger(scope)
            if scope.unconsumed_overrides():
                raise ValueError("MAT1_UNKNOWN_TEE_PHYSICAL_COMPONENT_OVERRIDE")
            serialized = serialize_tee_connector_design(native)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail={"code": str(error)}) from error
        return {
            "contract": "MAT1-TEE-RC0",
            "overall_status": "SOURCE_REQUIRED",
            "native_design": serialized.model_dump(mode="json"),
            "material_ledgers": [_json_value(asdict(item)) for item in scope.ledgers],
            "material_issues": sorted(set(scope.issues)),
            "design_check_performed": True,
        }

    @router.post("/family/design-check")
    async def family_design(
        request: FamilyMAT1RequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity)],
    ) -> dict[str, object]:
        """Route a named native family through request-local material bindings."""

        family = FAMILIES.get(request.family_id)
        if family is None or request.family_id in {"single-bolt", "multi-row", "tee-connector"}:
            raise HTTPException(status_code=422, detail={"code": "MAT1_UNKNOWN_FAMILY"})
        try:
            scope = resolve_scope(request.assignments, request.family_id)
            with bind_mat1_scope(scope):
                bind_physical_owners(
                    scope, request.family_id, family.preview(request.legacy_request)
                )
                native = family.design(request.legacy_request)
                if not scope.adapters:
                    if (
                        getattr(native, "assembly_status", None) == "NOT_EVALUATED"
                        or getattr(native, "resistance_evaluated", None) is False
                    ):
                        scope.issues.append("MAT1_NATIVE_RESISTANCE_NOT_EVALUATED_FOR_THIS_REQUEST")
                    else:
                        raise ValueError("MAT1_FAMILY_MATERIAL_CONSUMER_UNIMPLEMENTED")
                complete_owner_ledger(scope)
            if scope.unconsumed_overrides():
                raise ValueError("MAT1_UNKNOWN_FAMILY_PHYSICAL_COMPONENT_OVERRIDE")
            client_design = jsonable_encoder(_FAMILY_SERIALIZERS[request.family_id](native))
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail={"code": str(error)}) from error
        return {
            "contract": "MAT1-FAMILY-RC0",
            "family_id": request.family_id,
            "overall_status": "SOURCE_REQUIRED",
            "client_design": client_design,
            "material_ledgers": [_json_value(asdict(item)) for item in scope.ledgers],
            "material_issues": sorted(set(scope.issues)),
            "design_check_performed": True,
        }

    @router.post("/stair-stringer-miter/analytical-design-check")
    async def ssmc_design(
        request: SSMCMAT1RequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity)],
    ) -> dict[str, object]:
        """Bind owner data while preserving SSMC's exact source-gated analytical method."""

        dto = request.legacy_request
        if (
            dto.action.time_effect_category
            != request.assignments.default_conditions.time_effect_category
        ):
            raise HTTPException(status_code=422, detail={"code": "MAT1_DUAL_TIME_CATEGORY"})
        try:
            scope = resolve_scope(request.assignments, "stair-stringer-miter")
            with bind_mat1_scope(scope):
                physical = map_ssmc_request(dto.physical)
                bind_physical_owners(
                    scope,
                    "stair-stringer-miter",
                    FAMILIES["stair-stringer-miter"].preview(dto.physical.model_dump(mode="json")),
                )
                action = SSMCDesignAction(
                    dto.action.basis,
                    dto.action.combination_id,
                    dto.action.combination_source,
                    dto.action.already_factored,
                    dto.action.time_effect_category,
                    dto.action.time_effect_reference,
                )
                lap = SSMCSingleLapDeclaration(
                    dto.single_lap.external_actions_at_faying_interface,
                    _quantity(dto.single_lap.independent_normal_force),
                    _quantity(dto.single_lap.independent_out_of_plane_moment),
                    dto.single_lap.imposed_separation,
                    dto.single_lap.non_contact_gap,
                    dto.single_lap.friction_or_preload_credit,
                    dto.single_lap.miter_bearing_credit,
                )
                native = evaluate_ssmc_analytical(SSMCAnalyticalRequest(physical, action, lap))
                complete_owner_ledger(scope)
            if scope.unconsumed_overrides():
                raise ValueError("MAT1_UNKNOWN_SSMC_PHYSICAL_COMPONENT_OVERRIDE")
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail={"code": str(error)}) from error
        return {
            "contract": "MAT1-SSMC-ANALYTICAL-RC0",
            "overall_status": "SOURCE_REQUIRED",
            "client_design": {
                "contract": native.contract,
                "method": native.method,
                "whole_connection_status": native.whole_connection_status,
                "result": serialize_ssmc_value(native),
            },
            "material_ledgers": [_json_value(asdict(item)) for item in scope.ledgers],
            "material_issues": sorted(
                {*scope.issues, "SSMC_EXACT_PLATE_AND_MEMBER_PATH_SOURCE_BINDINGS_REQUIRED"}
            ),
            "design_check_performed": True,
        }

    return router
