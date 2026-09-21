"""CME-1 native family bindings. Legacy DTOs, mappers and engines remain unchanged."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType

from pydantic import JsonValue, TypeAdapter

from frp_master_connection.api.angle_column_moment_base import (
    AngleBaseRequestDTO,
    map_angle_base_request,
)
from frp_master_connection.api.beam_concrete_paired_angle_mapping import (
    map_beam_concrete_paired_angle_request,
)
from frp_master_connection.api.beam_concrete_paired_angle_schemas import (
    BeamConcretePairedAngleRequestDTO,
)
from frp_master_connection.api.calculation_mapping import (
    map_connection_view_extents,
    map_single_bolt_preview_request,
    map_single_bolt_request,
)
from frp_master_connection.api.channel_moment_splice_mapping import (
    map_channel_moment_splice_request,
)
from frp_master_connection.api.channel_moment_splice_schemas import ChannelMomentSpliceRequestDTO
from frp_master_connection.api.clip_angle_mapping import map_clip_angle_request
from frp_master_connection.api.clip_angle_schemas import ClipAngleConnectorRequestDTO
from frp_master_connection.api.column_base_web_angle_mapping import (
    map_column_base_web_angle_request,
)
from frp_master_connection.api.column_base_web_angle_schemas import ColumnBaseWebAngleAnyRequestDTO
from frp_master_connection.api.column_moment_base import (
    ColumnMomentBaseRequestDTO,
    map_column_moment_base_request,
)
from frp_master_connection.api.dctn3b import (
    DCTN3BRequestDTO,
    design_versioned_dctn,
    map_versioned_dctn,
    preview_versioned_dctn,
)
from frp_master_connection.api.direct_side_lap_concrete_mapping import (
    map_direct_side_lap_concrete_request,
)
from frp_master_connection.api.direct_side_lap_concrete_schemas import (
    DirectSideLapConcreteRequestDTO,
)
from frp_master_connection.api.double_channel_truss_node import DCTNRequestDTO
from frp_master_connection.api.multi_member_tee_mapping import map_multi_member_tee_request
from frp_master_connection.api.multi_member_tee_schemas import MultiMemberTeeRequestDTO
from frp_master_connection.api.multirow_mapping import map_multirow_request
from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO
from frp_master_connection.api.paired_clip_angle_mapping import map_paired_clip_angle_request
from frp_master_connection.api.paired_clip_angle_schemas import PairedClipAngleConnectorRequestDTO
from frp_master_connection.api.schemas import (
    SingleBoltEvaluationRequestDTO,
    SingleBoltPreviewRequestDTO,
)
from frp_master_connection.api.ssmc import SSMCRequestDTO, map_ssmc_request
from frp_master_connection.api.tee_mapping import map_tee_connector_request
from frp_master_connection.api.tee_schemas import TeeConnectorRequestDTO
from frp_master_connection.api.web_splice_mapping import map_web_splice_request
from frp_master_connection.api.web_splice_schemas import WebSpliceRequestDTO
from frp_master_connection.api.wi_frp_support_moment_mapping import (
    map_wi_frp_support_moment_request,
)
from frp_master_connection.api.wi_frp_support_moment_schemas import WIFrpSupportMomentRequestDTO
from frp_master_connection.api.wi_moment_splice_mapping import map_wi_moment_splice_request
from frp_master_connection.api.wi_moment_splice_schemas import WIMomentSpliceRequestDTO
from frp_master_connection.api.wi_wall_moment_mapping import map_wi_wall_moment_request
from frp_master_connection.api.wi_wall_moment_schemas import WIWallMomentRequestDTO
from frp_master_connection.application.angle_column_base_design import (
    evaluate_angle_column_moment_base,
)
from frp_master_connection.application.angle_column_base_preview import (
    preview_angle_column_moment_base,
)
from frp_master_connection.application.beam_concrete_paired_angle_orchestration import (
    design_check_beam_concrete_paired_angle,
    preview_beam_concrete_paired_angle,
)
from frp_master_connection.application.calculation_orchestration import (
    evaluate_single_bolt_connection,
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
from frp_master_connection.application.column_moment_base_design import evaluate_column_moment_base
from frp_master_connection.application.column_moment_base_preview import preview_column_moment_base
from frp_master_connection.application.connection_preview import preview_single_bolt_connection
from frp_master_connection.application.direct_side_lap_concrete_orchestration import (
    design_check_direct_side_lap_concrete,
    preview_direct_side_lap_concrete,
)
from frp_master_connection.application.multi_member_tee_orchestration import (
    design_check_multi_member_tee,
    preview_multi_member_tee,
)
from frp_master_connection.application.multirow_orchestration import (
    evaluate_multirow_connection,
    preview_multirow_connection,
)
from frp_master_connection.application.paired_clip_angle_orchestration import (
    design_check_paired_clip_angle,
    preview_paired_clip_angle,
)
from frp_master_connection.application.ssmc import design_ssmc, preview_ssmc
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
from frp_master_connection.calculation.connector_material_provider import (
    ConnectorProvider,
    NativeFRPAdapter,
    ProviderCapability,
    provider_registry,
)
from frp_master_connection.domain.connector_materials import ConnectorMaterial, Fabrication


@dataclass(frozen=True, slots=True)
class NativeFamily:
    route_id: str
    product_id: str
    category: str
    schema: dict[str, JsonValue]
    preview: Callable[[dict[str, JsonValue]], object]
    design: Callable[[dict[str, JsonValue]], object]
    native_entry_points: tuple[str, ...]


def bind[DTO, Request](
    route_id: str,
    product_id: str,
    category: str,
    adapter: TypeAdapter[DTO],
    mapper: Callable[[DTO], Request],
    preview: Callable[[Request], object],
    design: Callable[[Request], object],
) -> NativeFamily:
    def native_preview(payload: dict[str, JsonValue]) -> object:
        return preview(mapper(adapter.validate_python(payload)))

    def native_design(payload: dict[str, JsonValue]) -> object:
        return design(mapper(adapter.validate_python(payload)))

    return NativeFamily(
        route_id,
        product_id,
        category,
        adapter.json_schema(),
        native_preview,
        native_design,
        tuple(f"{f.__module__}.{f.__name__}" for f in (mapper, preview, design)),
    )


def _single_preview(payload: dict[str, JsonValue]) -> object:
    dto = SingleBoltPreviewRequestDTO.model_validate(payload)
    return preview_single_bolt_connection(
        map_single_bolt_preview_request(dto), map_connection_view_extents(dto)
    )


def _single_design(payload: dict[str, JsonValue]) -> object:
    return evaluate_single_bolt_connection(
        map_single_bolt_request(SingleBoltEvaluationRequestDTO.model_validate(payload))
    )


def _column_preview(payload: dict[str, JsonValue]) -> object:
    dto: ColumnBaseWebAngleAnyRequestDTO = TypeAdapter(
        ColumnBaseWebAngleAnyRequestDTO
    ).validate_python(payload)
    return preview_column_base_web_angles(map_column_base_web_angle_request(dto))


def _column_design(payload: dict[str, JsonValue]) -> object:
    dto: ColumnBaseWebAngleAnyRequestDTO = TypeAdapter(
        ColumnBaseWebAngleAnyRequestDTO
    ).validate_python(payload)
    return design_check_column_base_web_angles(map_column_base_web_angle_request(dto))


# No client registration, dynamic module loading, test providers or steel fallback.
FAMILIES = MappingProxyType(
    {
        item.route_id: item
        for item in (
            bind(
                "stair-stringer-miter",
                "STAIR_STRINGER_MITER_CONNECTION",
                "MOMENT",
                TypeAdapter(SSMCRequestDTO),
                map_ssmc_request,
                preview_ssmc,
                design_ssmc,
            ),
            replace(
                bind(
                    "single-bolt",
                    "DIRECT_REFERENCE",
                    "SHEAR",
                    TypeAdapter(SingleBoltPreviewRequestDTO),
                    map_single_bolt_preview_request,
                    preview_single_bolt_connection,
                    evaluate_single_bolt_connection,
                ),
                preview=_single_preview,
                design=_single_design,
            ),
            bind(
                "multi-row",
                "DIRECT_REFERENCE",
                "SHEAR",
                TypeAdapter(MultiRowConnectionRequestDTO),
                map_multirow_request,
                preview_multirow_connection,
                evaluate_multirow_connection,
            ),
            bind(
                "tee-connector",
                "FRP_TEE",
                "SHEAR",
                TypeAdapter(TeeConnectorRequestDTO),
                map_tee_connector_request,
                preview_tee_connector,
                design_check_tee_connector,
            ),
            bind(
                "clip-angle",
                "SINGLE_CLIP_ANGLE",
                "SHEAR",
                TypeAdapter(ClipAngleConnectorRequestDTO),
                map_clip_angle_request,
                preview_clip_angle,
                design_check_clip_angle,
            ),
            bind(
                "paired-clip-angle",
                "SYMMETRIC_PAIRED_CLIP_ANGLES",
                "SHEAR",
                TypeAdapter(PairedClipAngleConnectorRequestDTO),
                map_paired_clip_angle_request,
                preview_paired_clip_angle,
                design_check_paired_clip_angle,
            ),
            bind(
                "multi-member-tee",
                "MULTI_MEMBER_TEE",
                "SHEAR",
                TypeAdapter(MultiMemberTeeRequestDTO),
                map_multi_member_tee_request,
                preview_multi_member_tee,
                design_check_multi_member_tee,
            ),
            bind(
                "beam-concrete-paired-angle",
                "BEAM_CONCRETE_PAIRED_ANGLE",
                "SHEAR",
                TypeAdapter(BeamConcretePairedAngleRequestDTO),
                map_beam_concrete_paired_angle_request,
                preview_beam_concrete_paired_angle,
                design_check_beam_concrete_paired_angle,
            ),
            bind(
                "direct-side-lap-concrete",
                "DIRECT_SIDE_LAP_CONCRETE",
                "SHEAR",
                TypeAdapter(DirectSideLapConcreteRequestDTO),
                map_direct_side_lap_concrete_request,
                preview_direct_side_lap_concrete,
                design_check_direct_side_lap_concrete,
            ),
            NativeFamily(
                "column-base-web-angles",
                "COLUMN_BASE_WEB_ANGLES_CONCRETE",
                "SHEAR",
                TypeAdapter(ColumnBaseWebAngleAnyRequestDTO).json_schema(),
                _column_preview,
                _column_design,
                (
                    "map_column_base_web_angle_request",
                    "preview_column_base_web_angles",
                    "design_check_column_base_web_angles",
                ),
            ),
            bind(
                "beam-web-splice",
                "SYMMETRIC_DOUBLE_WEB_SPLICE",
                "SHEAR",
                TypeAdapter(WebSpliceRequestDTO),
                map_web_splice_request,
                preview_web_splice,
                design_check_web_splice,
            ),
            bind(
                "wi-major-axis-moment-splice",
                "WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE",
                "MOMENT",
                TypeAdapter(WIMomentSpliceRequestDTO),
                map_wi_moment_splice_request,
                preview_wi_moment_splice,
                design_check_wi_moment_splice,
            ),
            bind(
                "channel-major-axis-moment-splice",
                "CHANNEL_BEAM_MAJOR_AXIS_MOMENT_SPLICE",
                "MOMENT",
                TypeAdapter(ChannelMomentSpliceRequestDTO),
                map_channel_moment_splice_request,
                preview_channel_moment_splice,
                design_check_channel_moment_splice,
            ),
            bind(
                "wi-beam-concrete-wall-moment",
                "WI_BEAM_CONCRETE_WALL_MAJOR_AXIS_MOMENT_CONNECTION",
                "MOMENT",
                TypeAdapter(WIWallMomentRequestDTO),
                map_wi_wall_moment_request,
                preview_wi_wall_moment,
                evaluate_wi_wall_moment,
            ),
            bind(
                "wi-beam-frp-support-moment",
                "WI_BEAM_FRP_SUPPORT_MAJOR_AXIS_MOMENT_CONNECTION",
                "MOMENT",
                TypeAdapter(WIFrpSupportMomentRequestDTO),
                map_wi_frp_support_moment_request,
                preview_wi_frp_support_moment,
                evaluate_wi_frp_support_moment,
            ),
            bind(
                "angle-column-two-leg-moment-base",
                "ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_CONNECTION",
                "MOMENT",
                TypeAdapter(AngleBaseRequestDTO),
                map_angle_base_request,
                preview_angle_column_moment_base,
                evaluate_angle_column_moment_base,
            ),
            bind(
                "wi-rhs-srs-column-moment-base",
                "WI_RHS_SRS_COLUMN_MOMENT_BASE_CONNECTION",
                "MOMENT",
                TypeAdapter(ColumnMomentBaseRequestDTO),
                map_column_moment_base_request,
                preview_column_moment_base,
                evaluate_column_moment_base,
            ),
            bind(
                "double-channel-truss-node",
                "DOUBLE_CHANNEL_TRUSS_NODE_CONNECTION",
                "SHEAR",
                TypeAdapter(DCTNRequestDTO | DCTN3BRequestDTO),
                map_versioned_dctn,
                preview_versioned_dctn,
                design_versioned_dctn,
            ),
        )
    }
)


@dataclass(frozen=True, slots=True)
class NativeFamilyInput:
    """Application-only native request transport, not a synthetic resistance input."""

    route_id: str
    payload: dict[str, JsonValue]


def _family_provider(family: NativeFamily) -> ConnectorProvider:
    form = (
        "TEE"
        if family.route_id in {"tee-connector", "multi-member-tee"}
        else "PLATE"
        if family.route_id
        in {
            "beam-web-splice",
            "wi-major-axis-moment-splice",
            "channel-major-axis-moment-splice",
            "stair-stringer-miter",
        }
        else "ANGLE"
    )

    def evaluate(value: NativeFamilyInput) -> object:
        if value.route_id != family.route_id:
            raise ValueError("Native family response cannot be transferred to another family")
        return family.design(value.payload)

    return NativeFRPAdapter(
        ProviderCapability(
            "NATIVE_FRP:" + family.route_id,
            ConnectorMaterial.FRP,
            (form,),
            (Fabrication.PULTRUDED,),
            family.native_entry_points[-1],
        ),
        NativeFamilyInput,
        evaluate,
    )


def native_family_providers() -> Mapping[str, ConnectorProvider]:
    """Whole-native-result adapters; existing local/check/source scopes are untouched.

    Direct joints have no connector body/provider selection. Their FRP member and
    independent fastener checks remain available through the native family call.
    """
    return provider_registry(
        tuple(
            _family_provider(family)
            for family in FAMILIES.values()
            if family.route_id
            not in {
                "single-bolt",
                "multi-row",
                "direct-side-lap-concrete",
                "double-channel-truss-node",
            }
        )
    )
