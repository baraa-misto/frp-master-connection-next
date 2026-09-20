"""Pure Stage 3.5C DTO mapping and deterministic serialization."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, cast, overload

if TYPE_CHECKING:
    from frp_master_connection.application.column_base_profile_orchestration import (
        ColumnBaseProfileDesignResult,
        ColumnBaseProfilePreviewResult,
    )

from frp_master_connection.api.clip_angle_mapping import _length, _serialize
from frp_master_connection.api.column_base_web_angle_schemas import (
    COLUMN_BASE_WEB_ANGLE_API_TRANSPORT_SCHEMA_VERSION,
    ColumnBaseAngleProfileDTO,
    ColumnBaseProfileRequestDTO,
    ColumnBaseRectangularHollowProfileDTO,
    ColumnBaseSolidRectangularProfileDTO,
    ColumnBaseWebAngleDesignResponseDTO,
    ColumnBaseWebAnglePreviewResponseDTO,
    ColumnBaseWebAngleRequestDTO,
    ColumnBaseWebAngleSignedRequestDTO,
    ColumnBaseWideFlangeProfileDTO,
)
from frp_master_connection.api.schemas import DecimalVector3DTO
from frp_master_connection.application.column_base_web_angle_orchestration import (
    ColumnBaseDesignResult,
    ColumnBasePreviewResult,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.domain import (
    AngleProfileDimensions,
    ClipAngleBoltLayout,
    ClipAngleBoltPlacementMode,
    ClipAngleDimensions,
    ColumnBaseAnchorPattern,
    ColumnBaseConcreteGeometry,
    ColumnBaseProfileRequest,
    ColumnBaseRequest,
    ColumnBaseSignedRequest,
    ColumnBaseVector,
    ColumnBaseWideFlangeGeometry,
    ComponentMaterialKind,
    CoordinateFrameKind,
    CoordinateFrameReference,
    ExternalAnchorGeometry,
    FRPComponentOrientation,
    MemberProfile,
    MemberProfileDimensions,
    PrincipalAxisFamily,
    RectangularHollowProfileDimensions,
    SolidRectangularProfileDimensions,
    WideFlangeIProfileDimensions,
)


def _vector(value: DecimalVector3DTO) -> ColumnBaseVector:
    return ColumnBaseVector(
        PhysicalQuantity.of(value.x, value.unit),
        PhysicalQuantity.of(value.y, value.unit),
        PhysicalQuantity.of(value.z, value.unit),
    )


def _column_profile(value: ColumnBaseProfileRequestDTO) -> MemberProfile:
    source = value.column_profile
    unit = value.source_length_unit
    dimensions: MemberProfileDimensions
    if isinstance(source, ColumnBaseWideFlangeProfileDTO):
        wide_flange = source.dimensions
        dimensions = WideFlangeIProfileDimensions(
            _length(wide_flange.member_length, unit),
            _length(wide_flange.depth, unit),
            _length(wide_flange.flange_width, unit),
            _length(wide_flange.web_thickness, unit),
            _length(wide_flange.flange_thickness, unit),
        )
    elif isinstance(source, ColumnBaseRectangularHollowProfileDTO):
        hollow = source.dimensions
        dimensions = RectangularHollowProfileDimensions(
            _length(hollow.member_length, unit),
            _length(hollow.depth, unit),
            _length(hollow.width, unit),
            _length(hollow.wall_thickness, unit),
        )
    elif isinstance(source, ColumnBaseSolidRectangularProfileDTO):
        solid = source.dimensions
        dimensions = SolidRectangularProfileDimensions(
            _length(solid.member_length, unit),
            _length(solid.depth, unit),
            _length(solid.width, unit),
        )
    elif isinstance(source, ColumnBaseAngleProfileDTO):
        angle = source.dimensions
        dimensions = AngleProfileDimensions(
            _length(angle.member_length, unit),
            _length(angle.leg_y, unit),
            _length(angle.leg_z, unit),
            _length(angle.thickness, unit),
        )
    else:  # pragma: no cover - discriminated transport union is closed
        raise TypeError("Unsupported Stage 3.7A column profile.")
    member_id = "column"
    return MemberProfile(
        source.profile_id,
        member_id,
        source.role,
        source.profile_family,
        dimensions,
        ComponentMaterialKind.PULTRUDED_FRP,
        FRPComponentOrientation(
            CoordinateFrameReference(CoordinateFrameKind.MEMBER_LOCAL, member_id),
            PrincipalAxisFamily.X,
        ),
        source.profile_orientation,
        source.selected_profile_surface,
        source.size_basis,
    )


@overload
def map_column_base_web_angle_request(
    value: ColumnBaseWebAngleRequestDTO,
) -> ColumnBaseRequest: ...


@overload
def map_column_base_web_angle_request(
    value: ColumnBaseWebAngleSignedRequestDTO,
) -> ColumnBaseSignedRequest: ...


@overload
def map_column_base_web_angle_request(
    value: ColumnBaseProfileRequestDTO,
) -> ColumnBaseProfileRequest: ...


def map_column_base_web_angle_request(
    value: ColumnBaseWebAngleRequestDTO
    | ColumnBaseWebAngleSignedRequestDTO
    | ColumnBaseProfileRequestDTO,
) -> ColumnBaseRequest | ColumnBaseSignedRequest | ColumnBaseProfileRequest:
    unit = value.source_length_unit
    concrete = value.concrete
    angle = value.angle
    web = value.web_group
    anchor = value.anchor_pattern
    external = value.external_anchor
    angle_dimensions = ClipAngleDimensions(
        _length(angle.connected_leg_width, unit),
        _length(angle.support_leg_width, unit),
        _length(angle.thickness, unit),
        _length(angle.connector_length, unit),
    )
    pitch = _length(web.pitch, unit)
    gauge = _length(web.gauge, unit)
    centroid = _length(web.centroid_height_l, unit)
    heel = (angle_dimensions.connector_length - Decimal(web.bolts_per_row - 1) * gauge) / 2
    end = (angle_dimensions.connected_leg_width - Decimal(web.row_count - 1) * pitch) / 2
    flat_center = (angle_dimensions.thickness + angle_dimensions.connected_leg_width) / 2
    layout = ClipAngleBoltLayout(
        web.row_count,
        web.bolts_per_row,
        pitch,
        gauge,
        heel,
        heel,
        end,
        end,
        ClipAngleBoltPlacementMode.GROUP_OFFSET_CONTROLLED,
        centroid,
        -flat_center,
    )
    moment_unit = Unit.KIP_IN if value.unit_system.value == "US_CUSTOMARY" else Unit.KN_MM
    if isinstance(value, ColumnBaseProfileRequestDTO):
        return ColumnBaseProfileRequest(
            value.request_id,
            value.unit_system,
            unit,
            ColumnBaseConcreteGeometry(
                PhysicalQuantity.of(concrete.s_dimension.value, concrete.s_dimension.unit),
                PhysicalQuantity.of(concrete.t_dimension.value, concrete.t_dimension.unit),
                PhysicalQuantity.of(concrete.depth.value, concrete.depth.unit),
            ),
            _column_profile(value),
            value.assembly,
            value.single_side,
            angle_dimensions,
            layout,
            ColumnBaseAnchorPattern(
                anchor.row_count,
                anchor.anchors_per_row,
                PhysicalQuantity.of(anchor.pitch.value, anchor.pitch.unit),
                PhysicalQuantity.of(anchor.gauge.value, anchor.gauge.unit),
                PhysicalQuantity.of(anchor.centroid_offset_t.value, anchor.centroid_offset_t.unit),
            ),
            PhysicalQuantity.of(value.web_bolt_diameter.value, value.web_bolt_diameter.unit),
            PhysicalQuantity.of(value.web_hole_diameter.value, value.web_hole_diameter.unit),
            ExternalAnchorGeometry(
                PhysicalQuantity.of(
                    external.nominal_diameter.value, external.nominal_diameter.unit
                ),
                PhysicalQuantity.of(external.hole_diameter.value, external.hole_diameter.unit),
                PhysicalQuantity.of(
                    external.specified_embedment.value, external.specified_embedment.unit
                ),
                PhysicalQuantity.of(
                    external.washer_outside_diameter.value, external.washer_outside_diameter.unit
                ),
                PhysicalQuantity.of(
                    external.washer_thickness.value, external.washer_thickness.unit
                ),
                external.system_classification,
            ),
            PhysicalQuantity.of(value.signed_axial_force.value, value.signed_axial_force.unit),
            PhysicalQuantity.of(
                value.connection_plane_shear.value, value.connection_plane_shear.unit
            ),
            PhysicalQuantity.of(
                value.connection_normal_shear.value, value.connection_normal_shear.unit
            ),
            ColumnBaseVector(*tuple(PhysicalQuantity.of(0, moment_unit) for _ in range(3))),
            value.angle_double_topology,
            value.orchestration_contract_version,
        )
    column = value.column
    axial = (
        value.axial_compression
        if isinstance(value, ColumnBaseWebAngleRequestDTO)
        else value.signed_axial_force
    )
    request_type = (
        ColumnBaseRequest
        if isinstance(value, ColumnBaseWebAngleRequestDTO)
        else ColumnBaseSignedRequest
    )
    return request_type(
        value.request_id,
        value.unit_system,
        unit,
        ColumnBaseConcreteGeometry(
            PhysicalQuantity.of(concrete.s_dimension.value, concrete.s_dimension.unit),
            PhysicalQuantity.of(concrete.t_dimension.value, concrete.t_dimension.unit),
            PhysicalQuantity.of(concrete.depth.value, concrete.depth.unit),
        ),
        ColumnBaseWideFlangeGeometry(
            PhysicalQuantity.of(column.depth_s.value, column.depth_s.unit),
            PhysicalQuantity.of(column.flange_width_t.value, column.flange_width_t.unit),
            PhysicalQuantity.of(column.web_thickness.value, column.web_thickness.unit),
            PhysicalQuantity.of(column.flange_thickness.value, column.flange_thickness.unit),
            PhysicalQuantity.of(column.display_height.value, column.display_height.unit),
            column.profile_family,
        ),
        value.assembly,
        value.single_side,
        angle_dimensions,
        layout,
        ColumnBaseAnchorPattern(
            anchor.row_count,
            anchor.anchors_per_row,
            PhysicalQuantity.of(anchor.pitch.value, anchor.pitch.unit),
            PhysicalQuantity.of(anchor.gauge.value, anchor.gauge.unit),
            PhysicalQuantity.of(anchor.centroid_offset_t.value, anchor.centroid_offset_t.unit),
        ),
        PhysicalQuantity.of(value.web_bolt_diameter.value, value.web_bolt_diameter.unit),
        PhysicalQuantity.of(value.web_hole_diameter.value, value.web_hole_diameter.unit),
        ExternalAnchorGeometry(
            PhysicalQuantity.of(external.nominal_diameter.value, external.nominal_diameter.unit),
            PhysicalQuantity.of(external.hole_diameter.value, external.hole_diameter.unit),
            PhysicalQuantity.of(
                external.specified_embedment.value, external.specified_embedment.unit
            ),
            PhysicalQuantity.of(
                external.washer_outside_diameter.value, external.washer_outside_diameter.unit
            ),
            PhysicalQuantity.of(external.washer_thickness.value, external.washer_thickness.unit),
            external.system_classification,
        ),
        PhysicalQuantity.of(axial.value, axial.unit),
        PhysicalQuantity.of(value.web_plane_shear.value, value.web_plane_shear.unit),
        PhysicalQuantity.of(value.web_normal_shear.value, value.web_normal_shear.unit),
        ColumnBaseVector(*tuple(PhysicalQuantity.of(0, moment_unit) for _ in range(3))),
        _vector(value.action_reference_s_t_l),
        value.orchestration_contract_version,
    )


def serialize_column_base_web_angle_preview(
    value: ColumnBasePreviewResult | ColumnBaseProfilePreviewResult,
) -> ColumnBaseWebAnglePreviewResponseDTO:
    return ColumnBaseWebAnglePreviewResponseDTO.model_validate(
        {
            "api_transport_schema_version": COLUMN_BASE_WEB_ANGLE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.orchestration_contract_version,
            "preview_schema_version": value.preview_schema_version,
            "request_id": value.request_id,
            "geometry_status": value.geometry_status.value,
            "geometry_invalid_reasons": value.geometry_invalid_reasons,
            "assembly_status": value.assembly_status.value,
            "ordinary_pass_allowed": False,
            "resistance_evaluated": False,
            "design_check_ready": value.design_check_ready,
            "external_design_required": True,
            "engineering_fingerprint": value.engineering_fingerprint,
            "application_fingerprint": value.application_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


def serialize_column_base_web_angle_design(
    value: ColumnBaseDesignResult | ColumnBaseProfileDesignResult,
) -> ColumnBaseWebAngleDesignResponseDTO:
    return ColumnBaseWebAngleDesignResponseDTO.model_validate(
        {
            "api_transport_schema_version": COLUMN_BASE_WEB_ANGLE_API_TRANSPORT_SCHEMA_VERSION,
            "orchestration_contract_version": value.preview.orchestration_contract_version,
            "request_id": value.preview.request_id,
            "assembly_status": value.assembly_status.value,
            "required_check_status": value.required_check_status,
            "ordinary_pass_allowed": False,
            "external_design_required": True,
            "supported_local_failure_present": value.supported_local_failure_present,
            "result_fingerprint": value.result_fingerprint,
            "result": cast(dict[str, object], _serialize(value)),
        }
    )


__all__ = (
    "map_column_base_web_angle_request",
    "serialize_column_base_web_angle_design",
    "serialize_column_base_web_angle_preview",
)
