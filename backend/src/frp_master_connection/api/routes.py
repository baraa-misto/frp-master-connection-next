"""Thin routes for health, metadata, and stateless calculation transport."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from frp_master_connection.api.angle_column_moment_base import build_angle_base_router
from frp_master_connection.api.beam_concrete_paired_angle_mapping import (
    map_beam_concrete_paired_angle_request,
    serialize_beam_concrete_paired_angle_design,
    serialize_beam_concrete_paired_angle_preview,
)
from frp_master_connection.api.beam_concrete_paired_angle_schemas import (
    BeamConcretePairedAngleDesignResponseDTO,
    BeamConcretePairedAnglePreviewResponseDTO,
    BeamConcretePairedAngleRequestDTO,
)
from frp_master_connection.api.calculation_mapping import (
    map_connection_view_extents,
    map_single_bolt_preview_request,
    map_single_bolt_request,
    serialize_single_bolt_preview_response,
    serialize_single_bolt_response,
)
from frp_master_connection.api.channel_moment_splice_mapping import (
    map_channel_moment_splice_request,
    serialize_channel_moment_splice_design,
    serialize_channel_moment_splice_preview,
)
from frp_master_connection.api.channel_moment_splice_schemas import (
    ChannelMomentSpliceDesignResponseDTO,
    ChannelMomentSplicePreviewResponseDTO,
    ChannelMomentSpliceRequestDTO,
)
from frp_master_connection.api.clip_angle_mapping import (
    map_clip_angle_request,
    serialize_clip_angle_design,
    serialize_clip_angle_preview,
)
from frp_master_connection.api.clip_angle_schemas import (
    ClipAngleConnectorRequestDTO,
    ClipAngleDesignResponseDTO,
    ClipAnglePreviewResponseDTO,
)
from frp_master_connection.api.column_base_web_angle_mapping import (
    map_column_base_web_angle_request,
    serialize_column_base_web_angle_design,
    serialize_column_base_web_angle_preview,
)
from frp_master_connection.api.column_base_web_angle_schemas import (
    ColumnBaseWebAngleAnyRequestDTO,
    ColumnBaseWebAngleDesignResponseDTO,
    ColumnBaseWebAnglePreviewResponseDTO,
)
from frp_master_connection.api.column_moment_base import build_column_moment_base_router
from frp_master_connection.api.connector_materials import build_connector_material_router
from frp_master_connection.api.dependencies import build_trusted_identity_dependency
from frp_master_connection.api.direct_side_lap_concrete_mapping import (
    map_direct_side_lap_concrete_request,
    serialize_direct_side_lap_concrete_design,
    serialize_direct_side_lap_concrete_preview,
)
from frp_master_connection.api.direct_side_lap_concrete_schemas import (
    DirectSideLapConcreteDesignResponseDTO,
    DirectSideLapConcretePreviewResponseDTO,
    DirectSideLapConcreteRequestDTO,
)
from frp_master_connection.api.double_channel_truss_node import build_dctn_router
from frp_master_connection.api.multi_member_tee_mapping import (
    map_multi_member_tee_request,
    serialize_multi_member_tee_design,
    serialize_multi_member_tee_preview,
)
from frp_master_connection.api.multi_member_tee_schemas import (
    MultiMemberTeeDesignResponseDTO,
    MultiMemberTeePreviewResponseDTO,
    MultiMemberTeeRequestDTO,
)
from frp_master_connection.api.multirow_mapping import (
    map_multirow_request,
    serialize_multirow_design,
    serialize_multirow_preview,
)
from frp_master_connection.api.multirow_schemas import (
    MultiRowConnectionRequestDTO,
    MultiRowDesignResponseDTO,
    MultiRowPreviewResponseDTO,
)
from frp_master_connection.api.paired_clip_angle_mapping import (
    map_paired_clip_angle_request,
    serialize_paired_clip_angle_design,
    serialize_paired_clip_angle_preview,
)
from frp_master_connection.api.paired_clip_angle_schemas import (
    PairedClipAngleConnectorRequestDTO,
    PairedClipAngleDesignResponseDTO,
    PairedClipAnglePreviewResponseDTO,
)
from frp_master_connection.api.schemas import (
    HealthResponse,
    MetadataResponse,
    SingleBoltEvaluationRequestDTO,
    SingleBoltEvaluationResponseDTO,
    SingleBoltPreviewRequestDTO,
    SingleBoltPreviewResponseDTO,
)
from frp_master_connection.api.stainless_activation import (
    material_selection,
    stainless_design_response,
)
from frp_master_connection.api.tee_mapping import (
    map_tee_connector_request,
    serialize_tee_connector_design,
    serialize_tee_connector_preview,
)
from frp_master_connection.api.tee_schemas import (
    TeeConnectorDesignResponseDTO,
    TeeConnectorPreviewResponseDTO,
    TeeConnectorRequestDTO,
)
from frp_master_connection.api.web_splice_mapping import (
    map_web_splice_request,
    serialize_web_splice_design,
    serialize_web_splice_preview,
)
from frp_master_connection.api.web_splice_schemas import (
    WebSpliceDesignResponseDTO,
    WebSplicePreviewResponseDTO,
    WebSpliceRequestDTO,
)
from frp_master_connection.api.wi_frp_support_moment_mapping import (
    map_wi_frp_support_moment_request,
    serialize_wi_frp_support_moment,
)
from frp_master_connection.api.wi_frp_support_moment_schemas import (
    WIFrpSupportMomentRequestDTO,
    WIFrpSupportMomentResponseDTO,
)
from frp_master_connection.api.wi_moment_splice_mapping import (
    map_wi_moment_splice_request,
    serialize_wi_moment_splice_design,
    serialize_wi_moment_splice_preview,
)
from frp_master_connection.api.wi_moment_splice_schemas import (
    WIMomentSpliceDesignResponseDTO,
    WIMomentSplicePreviewResponseDTO,
    WIMomentSpliceRequestDTO,
)
from frp_master_connection.api.wi_wall_moment_mapping import (
    map_wi_wall_moment_request,
    serialize_wi_wall_moment,
)
from frp_master_connection.api.wi_wall_moment_schemas import (
    WIWallMomentRequestDTO,
    WIWallMomentResponseDTO,
)
from frp_master_connection.application import (
    build_single_bolt_visualization_snapshot,
    evaluate_multirow_connection,
    evaluate_single_bolt_connection,
    preview_multirow_connection,
    preview_single_bolt_connection,
)
from frp_master_connection.application.beam_concrete_paired_angle_orchestration import (
    design_check_beam_concrete_paired_angle,
    preview_beam_concrete_paired_angle,
)
from frp_master_connection.application.channel_moment_splice_orchestration import (
    design_check_channel_moment_splice,
    preview_channel_moment_splice,
)
from frp_master_connection.application.clip_angle_orchestration import (
    design_check_clip_angle,
    preview_clip_angle,
)
from frp_master_connection.application.column_base_web_angle_orchestration import (
    design_check_column_base_web_angles,
    preview_column_base_web_angles,
)
from frp_master_connection.application.direct_side_lap_concrete_orchestration import (
    design_check_direct_side_lap_concrete,
    preview_direct_side_lap_concrete,
)
from frp_master_connection.application.multi_member_tee_orchestration import (
    design_check_multi_member_tee,
    preview_multi_member_tee,
)
from frp_master_connection.application.paired_clip_angle_orchestration import (
    design_check_paired_clip_angle,
    preview_paired_clip_angle,
)
from frp_master_connection.application.tee_orchestration import (
    design_check_tee_connector,
    preview_tee_connector,
)
from frp_master_connection.application.web_splice_orchestration import (
    design_check_web_splice,
    preview_web_splice,
)
from frp_master_connection.application.wi_frp_support_moment_design import (
    evaluate_wi_frp_support_moment,
)
from frp_master_connection.application.wi_frp_support_moment_orchestration import (
    preview_wi_frp_support_moment,
)
from frp_master_connection.application.wi_moment_splice_orchestration import (
    design_check_wi_moment_splice,
    preview_wi_moment_splice,
)
from frp_master_connection.application.wi_wall_moment_design import evaluate_wi_wall_moment
from frp_master_connection.application.wi_wall_moment_orchestration import preview_wi_wall_moment
from frp_master_connection.security import TrustedIdentity, TrustedIdentityResolver
from frp_master_connection.version import (
    APPLICATION_VERSION,
    CALCULATION_ENGINE_VERSION,
    CODE_BASIS,
    ENGINEERING_CALCULATIONS_AVAILABLE,
    ENGINEERING_RULE_SET_VERSION,
    ERRATA_STATUS,
    PRODUCT_ID,
    PROJECT_SCHEMA_VERSION,
    REPORT_GENERATION_AVAILABLE,
)


def build_router(identity_resolver: TrustedIdentityResolver) -> APIRouter:
    """Build the Stage 2.2B route set around one trusted resolver."""
    router = APIRouter()
    router.include_router(build_angle_base_router(identity_resolver))
    router.include_router(build_column_moment_base_router(identity_resolver))
    router.include_router(build_dctn_router(identity_resolver))
    router.include_router(build_connector_material_router(identity_resolver))
    identity_dependency = build_trusted_identity_dependency(identity_resolver)

    @router.post(
        "/api/v1/calculations/wi-beam-frp-support-moment/preview",
        response_model=WIFrpSupportMomentResponseDTO,
        summary="Preview the W/I beam-to-FRP-support moment connection; no resistance",
    )
    async def preview_wi_frp_support_connection(
        request: WIFrpSupportMomentRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> WIFrpSupportMomentResponseDTO:
        try:
            return serialize_wi_frp_support_moment(
                preview_wi_frp_support_moment(map_wi_frp_support_moment_request(request))
            )
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_WI_FRP_SUPPORT_MOMENT_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error

    @router.post(
        "/api/v1/calculations/wi-beam-frp-support-moment/design-check",
        response_model=WIFrpSupportMomentResponseDTO,
        summary="Explicit Stage 4.3 design check with qualified FRP support-response boundary",
    )
    async def design_wi_frp_support_connection(
        request: WIFrpSupportMomentRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        material: Annotated[str, Depends(material_selection)],
    ) -> WIFrpSupportMomentResponseDTO | JSONResponse:
        try:
            response = evaluate_wi_frp_support_moment(map_wi_frp_support_moment_request(request))
            if material == "SS316":
                return stainless_design_response("wi-beam-frp-support-moment", response)
            return serialize_wi_frp_support_moment(response)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_WI_FRP_SUPPORT_MOMENT_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error

    @router.post(
        "/api/v1/calculations/wi-beam-concrete-wall-moment/preview",
        response_model=WIWallMomentResponseDTO,
        summary="Preview the W/I beam-to-concrete-wall moment connection; no resistance",
    )
    async def preview_wi_wall_connection(
        request: WIWallMomentRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> WIWallMomentResponseDTO:
        try:
            return serialize_wi_wall_moment(
                preview_wi_wall_moment(map_wi_wall_moment_request(request))
            )
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "CANONICAL_WI_WALL_MOMENT_MAPPING_INVALID", "message": str(error)},
            ) from error

    @router.post(
        "/api/v1/calculations/wi-beam-concrete-wall-moment/design-check",
        response_model=WIWallMomentResponseDTO,
        summary="Explicit Stage 4.2 internal design check; anchor/concrete design remains external",
    )
    async def design_wi_wall_connection(
        request: WIWallMomentRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        material: Annotated[str, Depends(material_selection)],
    ) -> WIWallMomentResponseDTO | JSONResponse:
        try:
            response = evaluate_wi_wall_moment(map_wi_wall_moment_request(request))
            if material == "SS316":
                return stainless_design_response("wi-beam-concrete-wall-moment", response)
            return serialize_wi_wall_moment(response)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "CANONICAL_WI_WALL_MOMENT_MAPPING_INVALID", "message": str(error)},
            ) from error

    @router.post(
        "/api/v1/calculations/channel-major-axis-moment-splice/preview",
        response_model=ChannelMomentSplicePreviewResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Preview one Channel major-axis moment splice",
        description=(
            "Builds the backend-authoritative Channel beams, six physical splice plates, "
            "exact Slice 6 component and shear-center handoff, physical bolt paths, actual "
            "group demands, six-component equilibrium, and review plan with zero resistance."
        ),
    )
    async def preview_channel_major_axis_moment_splice(
        request: ChannelMomentSpliceRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> ChannelMomentSplicePreviewResponseDTO:
        try:
            response = preview_channel_moment_splice(map_channel_moment_splice_request(request))
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_CHANNEL_MOMENT_SPLICE_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        return serialize_channel_moment_splice_preview(response)

    @router.post(
        "/api/v1/calculations/channel-major-axis-moment-splice/design-check",
        response_model=ChannelMomentSpliceDesignResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Run the Stage 4.1B Channel moment-splice design check",
        description=(
            "Explicitly executes Channel web/flange local and plate-body checks and actual "
            "unequal two-plane common-bolt shear checks. Ordinary PASS is prohibited and "
            "rational-method engineering review remains mandatory."
        ),
    )
    async def design_check_channel_major_axis_moment_splice(
        request: ChannelMomentSpliceRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        material: Annotated[str, Depends(material_selection)],
    ) -> ChannelMomentSpliceDesignResponseDTO | JSONResponse:
        try:
            response = design_check_channel_moment_splice(
                map_channel_moment_splice_request(request)
            )
            if material == "SS316":
                return stainless_design_response("channel-major-axis-moment-splice", response)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_CHANNEL_MOMENT_SPLICE_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        return serialize_channel_moment_splice_design(response)

    @router.post(
        "/api/v1/calculations/wi-major-axis-moment-splice/preview",
        response_model=WIMomentSplicePreviewResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Preview one W/I major-axis moment splice",
        description=(
            "Builds the backend-authoritative W/I beams, web and balanced flange-splice "
            "systems, exact Slice 5 component handoff, physical bolt paths, group demands, "
            "equilibrium, and review plan with zero resistance execution."
        ),
    )
    async def preview_wi_major_axis_moment_splice(
        request: WIMomentSpliceRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> WIMomentSplicePreviewResponseDTO:
        try:
            response = preview_wi_moment_splice(map_wi_moment_splice_request(request))
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_WI_MOMENT_SPLICE_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        return serialize_wi_moment_splice_preview(response)

    @router.post(
        "/api/v1/calculations/wi-major-axis-moment-splice/design-check",
        response_model=WIMomentSpliceDesignResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Run the Stage 4.1A W/I moment-splice design check",
        description=(
            "Explicitly executes the inherited web subsystem, flange local/body checks, "
            "and actual unequal two-plane common-bolt shear checks. Ordinary PASS is "
            "prohibited and rational-method review remains mandatory."
        ),
    )
    async def design_check_wi_major_axis_moment_splice(
        request: WIMomentSpliceRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        material: Annotated[str, Depends(material_selection)],
    ) -> WIMomentSpliceDesignResponseDTO | JSONResponse:
        try:
            response = design_check_wi_moment_splice(map_wi_moment_splice_request(request))
            if material == "SS316":
                return stainless_design_response("wi-major-axis-moment-splice", response)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_WI_MOMENT_SPLICE_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        return serialize_wi_moment_splice_design(response)

    @router.post(
        "/api/v1/calculations/beam-web-splice/preview",
        response_model=WebSplicePreviewResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Preview one symmetric double web-splice connection",
        description=(
            "Backend-authoritative collinear W/I beams, gap, mirrored FRP plates, two "
            "distinct Plate/Web/Plate bolt groups, signed wrenches, material axes, and "
            "zero resistance execution."
        ),
    )
    async def preview_beam_web_splice(
        request: WebSpliceRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> WebSplicePreviewResponseDTO:
        try:
            response = preview_web_splice(map_web_splice_request(request))
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "CANONICAL_WEB_SPLICE_MAPPING_INVALID", "message": str(error)},
            ) from error
        return serialize_web_splice_preview(response)

    @router.post(
        "/api/v1/calculations/beam-web-splice/design-check",
        response_model=WebSpliceDesignResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Run the authorized local web-splice design checks",
        description=(
            "Runs only accepted local FRP/fastener checks. Plate inter-group body transfer, "
            "common-bolt double shear, minor-shear bolt-axis response, and member moment "
            "transfer remain explicit limitations; ordinary whole-splice PASS is prohibited."
        ),
    )
    async def design_check_beam_web_splice(
        request: WebSpliceRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        material: Annotated[str, Depends(material_selection)],
    ) -> WebSpliceDesignResponseDTO | JSONResponse:
        try:
            response = design_check_web_splice(map_web_splice_request(request))
            if material == "SS316":
                return stainless_design_response("beam-web-splice", response)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "CANONICAL_WEB_SPLICE_MAPPING_INVALID", "message": str(error)},
            ) from error
        return serialize_web_splice_design(response)

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Report service/process health without claiming engineering readiness."""
        return HealthResponse(
            status="healthy",
            product_id=PRODUCT_ID,
            application_version=APPLICATION_VERSION,
        )

    @router.get("/api/v1/meta", response_model=MetadataResponse)
    async def metadata(
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> MetadataResponse:
        """Return controlled product metadata after trusted identity resolution."""
        return MetadataResponse(
            product_id=PRODUCT_ID,
            application_version=APPLICATION_VERSION,
            project_schema_version=PROJECT_SCHEMA_VERSION,
            calculation_engine_version=CALCULATION_ENGINE_VERSION,
            engineering_rule_set_version=ENGINEERING_RULE_SET_VERSION,
            code_basis=CODE_BASIS,
            errata_status=ERRATA_STATUS,
            engineering_calculations_available=ENGINEERING_CALCULATIONS_AVAILABLE,
            report_generation_available=REPORT_GENERATION_AVAILABLE,
        )

    @router.post(
        "/api/v1/calculations/single-bolt/evaluate",
        response_model=SingleBoltEvaluationResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Evaluate one selected single bolt",
        description=(
            "Stateless single-bolt/single-row evaluation. A valid transport request returns "
            "HTTP 200 even when the engineering outcome is FAIL, unsupported, source-pending, "
            "or review-required. Resistance requires an explicit resolved one-bolt demand; "
            "automatic demand distribution and persistence are not provided. Current ICE, "
            "F593, and whole-connection qualification limits remain explicit."
        ),
    )
    async def evaluate_single_bolt(
        request: SingleBoltEvaluationRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> SingleBoltEvaluationResponseDTO:
        """Map one untrusted snapshot, invoke orchestration once, and serialize it."""
        try:
            canonical_request = map_single_bolt_request(request)
        except (KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        response = evaluate_single_bolt_connection(canonical_request)
        visualization = build_single_bolt_visualization_snapshot(canonical_request, response)
        return serialize_single_bolt_response(response, visualization)

    @router.post(
        "/api/v1/calculations/single-bolt/preview",
        response_model=SingleBoltPreviewResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Preview one canonical single-bolt model",
        description=(
            "Stateless interactive canonical geometry/action validation using the same trusted "
            "identity and server-authoritative geometry mapping as design evaluation. Valid, "
            "invalid, incomplete, and unsupported model outcomes return HTTP 200. This operation "
            "executes zero resistance equations and returns no design result or utilization."
        ),
    )
    async def preview_single_bolt(
        request: SingleBoltPreviewRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> SingleBoltPreviewResponseDTO:
        """Map an untrusted preview snapshot and return current canonical model status."""
        try:
            canonical_request = map_single_bolt_preview_request(request)
            view_extents = map_connection_view_extents(request)
        except (KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        response = preview_single_bolt_connection(canonical_request, view_extents)
        return serialize_single_bolt_preview_response(response)

    @router.post(
        "/api/v1/calculations/multi-row/preview",
        response_model=MultiRowPreviewResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Preview one rectangular multi-row bolt group",
        description=(
            "Stateless backend-authoritative geometry, planning, applicability, and "
            "visualization preview for the controlled rectangular multi-row workflow. "
            "This operation executes zero resistance equations."
        ),
    )
    async def preview_multi_row(
        request: MultiRowConnectionRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> MultiRowPreviewResponseDTO:
        try:
            canonical_request = map_multirow_request(request)
        except (KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "CANONICAL_MAPPING_INVALID", "message": str(error)},
            ) from error
        return serialize_multirow_preview(preview_multirow_connection(canonical_request))

    @router.post(
        "/api/v1/calculations/multi-row/design-check",
        response_model=MultiRowDesignResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Run one rectangular multi-row design check",
        description=(
            "Stateless explicit or automatic member-end-force design evaluation through the "
            "verified Stage 2.5A demand, Stage 2.5B handoff, Stage 2.6A eccentric group-mode "
            "compatibility, and authorized Stage 2.4B resistance chain. Member-end moments "
            "are retained but not transferred; no friction credit, automatic axis-tension "
            "distribution, generated prying, or eccentric first-row method is provided."
        ),
    )
    async def design_check_multi_row(
        request: MultiRowConnectionRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> MultiRowDesignResponseDTO:
        try:
            canonical_request = map_multirow_request(request)
        except (KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "CANONICAL_MAPPING_INVALID", "message": str(error)},
            ) from error
        return serialize_multirow_design(evaluate_multirow_connection(canonical_request))

    @router.post(
        "/api/v1/calculations/multi-member-tee/preview",
        response_model=MultiMemberTeePreviewResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Preview one Multi-Member Tee node",
        description=(
            "Stateless backend-authoritative Tee-node geometry, independent active-member "
            "groups, complete member actions, exact assembled support wrench, and "
            "visualization. This operation executes zero resistance equations."
        ),
    )
    async def preview_multi_member_tee_node(
        request: MultiMemberTeeRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> MultiMemberTeePreviewResponseDTO:
        try:
            response = preview_multi_member_tee(map_multi_member_tee_request(request))
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_MULTI_MEMBER_TEE_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        return serialize_multi_member_tee_preview(response)

    @router.post(
        "/api/v1/calculations/multi-member-tee/design-check",
        response_model=MultiMemberTeeDesignResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Run the Multi-Member Tee node design orchestration",
        description=(
            "Runs the existing verified demand and eligible resistance handoff independently "
            "for each active member group and once for the assembled support transfer. Tee-body "
            "and intergroup load-path/stability limitations prohibit ordinary PASS."
        ),
    )
    async def design_check_multi_member_tee_node(
        request: MultiMemberTeeRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        material: Annotated[str, Depends(material_selection)],
    ) -> MultiMemberTeeDesignResponseDTO | JSONResponse:
        try:
            response = design_check_multi_member_tee(map_multi_member_tee_request(request))
            if material == "SS316":
                return stainless_design_response("multi-member-tee", response)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_MULTI_MEMBER_TEE_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        return serialize_multi_member_tee_design(response)

    @router.post(
        "/api/v1/calculations/tee-connector/preview",
        response_model=TeeConnectorPreviewResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Preview one reusable two-interface FRP Tee connection",
        description=(
            "Stateless backend-authoritative column- or beam-flange Tee geometry, "
            "two physical bolt groups, action decomposition, material authority, and "
            "visualization. This operation executes zero resistance equations."
        ),
    )
    async def preview_tee(
        request: TeeConnectorRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> TeeConnectorPreviewResponseDTO:
        try:
            canonical_request = map_tee_connector_request(request)
            response = preview_tee_connector(canonical_request)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "CANONICAL_TEE_MAPPING_INVALID", "message": str(error)},
            ) from error
        return serialize_tee_connector_preview(response)

    @router.post(
        "/api/v1/calculations/tee-connector/design-check",
        response_model=TeeConnectorDesignResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Run the two-interface FRP Tee design orchestration",
        description=(
            "Runs the accepted Stage 2 demand and eligible resistance handoff separately "
            "for both Tee interfaces. General Tee-body resistance and automatic "
            "interface-normal bolt tension remain explicitly not evaluated, so Stage 3.2 "
            "cannot return an ordinary whole-connection PASS."
        ),
    )
    async def design_check_tee(
        request: TeeConnectorRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        material: Annotated[str, Depends(material_selection)],
    ) -> TeeConnectorDesignResponseDTO | JSONResponse:
        try:
            canonical_request = map_tee_connector_request(request)
            response = design_check_tee_connector(canonical_request)
            if material == "SS316":
                return stainless_design_response("tee-connector", response)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "CANONICAL_TEE_MAPPING_INVALID", "message": str(error)},
            ) from error
        return serialize_tee_connector_design(response)

    @router.post(
        "/api/v1/calculations/clip-angle/preview",
        response_model=ClipAnglePreviewResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Preview one single FRP clip-angle connection",
        description=(
            "Stateless backend-authoritative single-angle geometry, two independent physical "
            "bolt groups, action transformation, Stage 2.5A demand, material regions, trim, "
            "and visualization. This operation executes zero resistance equations."
        ),
    )
    async def preview_single_clip_angle(
        request: ClipAngleConnectorRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> ClipAnglePreviewResponseDTO:
        try:
            response = preview_clip_angle(map_clip_angle_request(request))
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "CANONICAL_CLIP_ANGLE_MAPPING_INVALID", "message": str(error)},
            ) from error
        return serialize_clip_angle_preview(response)

    @router.post(
        "/api/v1/calculations/clip-angle/design-check",
        response_model=ClipAngleDesignResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Run the single FRP clip-angle design orchestration",
        description=(
            "Explicitly evaluates both eligible interface paths using the existing verified "
            "demand and resistance foundations. Connector-body and interface-normal transfer "
            "remain not evaluated, so an ordinary whole-connection PASS is prohibited."
        ),
    )
    async def design_check_single_clip_angle(
        request: ClipAngleConnectorRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        material: Annotated[str, Depends(material_selection)],
    ) -> ClipAngleDesignResponseDTO | JSONResponse:
        try:
            response = design_check_clip_angle(map_clip_angle_request(request))
            if material == "SS316":
                return stainless_design_response("clip-angle", response)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "CANONICAL_CLIP_ANGLE_MAPPING_INVALID", "message": str(error)},
            ) from error
        return serialize_clip_angle_design(response)

    @router.post(
        "/api/v1/calculations/paired-clip-angle/preview",
        response_model=PairedClipAnglePreviewResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Preview one symmetric paired FRP clip-angle connection",
        description=(
            "Stateless backend-authoritative paired geometry across six connected profiles "
            "and the seven shared support targets, one common through-bolt group, two "
            "support groups, exact symmetry proof, Stage 2.5A demands, trim, material "
            "regions, and visualization. This operation executes zero resistance equations."
        ),
    )
    async def preview_paired_clip_angles(
        request: PairedClipAngleConnectorRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> PairedClipAnglePreviewResponseDTO:
        try:
            response = preview_paired_clip_angle(map_paired_clip_angle_request(request))
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_PAIRED_CLIP_ANGLE_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        return serialize_paired_clip_angle_preview(response)

    @router.post(
        "/api/v1/calculations/paired-clip-angle/design-check",
        response_model=PairedClipAngleDesignResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Run the symmetric paired FRP clip-angle design orchestration",
        description=(
            "Runs only the accepted pure-reaction-shear path after the complete pair symmetry "
            "proof. Paired connector body, common-bolt double-shear, branch compatibility, "
            "rectangular local mechanics where present, and whole-connection qualification "
            "remain explicitly not evaluated, so ordinary PASS is prohibited."
        ),
    )
    async def design_check_paired_clip_angles(
        request: PairedClipAngleConnectorRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        material: Annotated[str, Depends(material_selection)],
    ) -> PairedClipAngleDesignResponseDTO | JSONResponse:
        try:
            response = design_check_paired_clip_angle(map_paired_clip_angle_request(request))
            if material == "SS316":
                return stainless_design_response("paired-clip-angle", response)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_PAIRED_CLIP_ANGLE_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        return serialize_paired_clip_angle_design(response)

    @router.post(
        "/api/v1/calculations/beam-concrete-paired-angle/preview",
        response_model=BeamConcretePairedAnglePreviewResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Preview paired FRP clip angles connecting a beam to a concrete wall",
        description=(
            "Resolves backend-authoritative wall, beam, paired-angle, common-bolt, external-"
            "anchor coordination geometry, exact transferred wrenches, and a deterministic "
            "external anchor-design handoff. This operation executes zero resistance equations."
        ),
    )
    async def preview_beam_concrete_paired_angles(
        request: BeamConcretePairedAngleRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> BeamConcretePairedAnglePreviewResponseDTO:
        try:
            response = preview_beam_concrete_paired_angle(
                map_beam_concrete_paired_angle_request(request)
            )
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_BEAM_CONCRETE_PAIRED_ANGLE_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        return serialize_beam_concrete_paired_angle_preview(response)

    @router.post(
        "/api/v1/calculations/beam-concrete-paired-angle/design-check",
        response_model=BeamConcretePairedAngleDesignResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Run the supported beam/FRP-side design handoff",
        description=(
            "Runs only the accepted beam/FRP-side resistance seam. Concrete and external-"
            "anchor resistance remain outside this application and ordinary PASS is prohibited."
        ),
    )
    async def design_check_beam_concrete_paired_angles(
        request: BeamConcretePairedAngleRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        material: Annotated[str, Depends(material_selection)],
    ) -> BeamConcretePairedAngleDesignResponseDTO | JSONResponse:
        try:
            response = design_check_beam_concrete_paired_angle(
                map_beam_concrete_paired_angle_request(request)
            )
            if material == "SS316":
                return stainless_design_response("beam-concrete-paired-angle", response)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_BEAM_CONCRETE_PAIRED_ANGLE_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        return serialize_beam_concrete_paired_angle_design(response)

    @router.post(
        "/api/v1/calculations/direct-side-lap-concrete/preview",
        response_model=DirectSideLapConcretePreviewResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Preview a direct side-lap FRP Angle/Channel connection to concrete",
        description=(
            "Resolves the finite wall free end, physical overlap, direct FRP-to-concrete "
            "anchor paths, exact transferred wrench, and external anchor-design handoff. "
            "This operation executes zero resistance equations."
        ),
    )
    async def preview_direct_side_lap_concrete_connection(
        request: DirectSideLapConcreteRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> DirectSideLapConcretePreviewResponseDTO:
        try:
            response = preview_direct_side_lap_concrete(
                map_direct_side_lap_concrete_request(request)
            )
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_DIRECT_SIDE_LAP_CONCRETE_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        return serialize_direct_side_lap_concrete_preview(response)

    @router.post(
        "/api/v1/calculations/direct-side-lap-concrete/design-check",
        response_model=DirectSideLapConcreteDesignResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Run the supported direct side-lap FRP design handoff",
        description=(
            "Runs only existing supported FRP-side seams. Concrete, anchor, pull-through, "
            "prying, and unsupported out-of-plane response remain explicitly external or "
            "not evaluated, so ordinary PASS is prohibited."
        ),
    )
    async def design_check_direct_side_lap_concrete_connection(
        request: DirectSideLapConcreteRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> DirectSideLapConcreteDesignResponseDTO:
        try:
            response = design_check_direct_side_lap_concrete(
                map_direct_side_lap_concrete_request(request)
            )
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_DIRECT_SIDE_LAP_CONCRETE_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        return serialize_direct_side_lap_concrete_design(response)

    @router.post(
        "/api/v1/calculations/column-base-web-angles/preview",
        response_model=ColumnBaseWebAnglePreviewResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Preview single/double FRP web base angles at a concrete-supported column base",
        description=(
            "Resolves backend-authoritative column, base-angle, web-bolt, anchor coordination, "
            "component demands, exact foundation wrench, and external-design handoff. Preview "
            "executes zero resistance equations."
        ),
    )
    async def preview_column_base_web_angle_connection(
        request: ColumnBaseWebAngleAnyRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> ColumnBaseWebAnglePreviewResponseDTO:
        try:
            response = preview_column_base_web_angles(map_column_base_web_angle_request(request))
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_COLUMN_BASE_WEB_ANGLE_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        return serialize_column_base_web_angle_preview(response)

    @router.post(
        "/api/v1/calculations/column-base-web-angles/design-check",
        response_model=ColumnBaseWebAngleDesignResponseDTO,
        status_code=status.HTTP_200_OK,
        summary="Run supported local FRP/web-bolt checks for the column-base assembly",
        description=(
            "Runs only existing supported local FRP/web-bolt resistance seams. Base-angle "
            "body/heel, prying, concrete bearing, anchor resistance, and bearing partition "
            "remain not evaluated or external, so ordinary PASS is prohibited."
        ),
    )
    async def design_check_column_base_web_angle_connection(
        request: ColumnBaseWebAngleAnyRequestDTO,
        _identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
        material: Annotated[str, Depends(material_selection)],
    ) -> ColumnBaseWebAngleDesignResponseDTO | JSONResponse:
        try:
            response = design_check_column_base_web_angles(
                map_column_base_web_angle_request(request)
            )
            if material == "SS316":
                return stainless_design_response("column-base-web-angles", response)
        except (ArithmeticError, KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "CANONICAL_COLUMN_BASE_WEB_ANGLE_MAPPING_INVALID",
                    "message": str(error),
                },
            ) from error
        return serialize_column_base_web_angle_design(response)

    return router


__all__ = ("build_router",)
