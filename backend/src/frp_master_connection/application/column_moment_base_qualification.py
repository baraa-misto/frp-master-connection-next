"""Stage 4.5 source/fixture identities over unchanged material and connector providers."""

from frp_master_connection.application.column_moment_base_preview import (
    ColumnMomentPreview,
    ColumnMomentTransfer,
)
from frp_master_connection.application.wi_wall_moment_demand import END_USE
from frp_master_connection.calculation.angle_column_base_response import base_fingerprint
from frp_master_connection.calculation.equations import adjust_frp_property
from frp_master_connection.calculation.frp_angle_connector_provider import FRPAngleContext
from frp_master_connection.calculation.properties import (
    FRPPropertyKind,
    create_locked_ice_material_snapshot,
)
from frp_master_connection.domain.column_moment_base import Face
from frp_master_connection.domain.material_architecture import ConnectorMaterialFamily


def connector_context(
    preview: ColumnMomentPreview, transfer: ColumnMomentTransfer, *, attachment: bool = False
) -> FRPAngleContext:
    from frp_master_connection.application.mat1_scope import material_for_owner

    material = material_for_owner(transfer.connector_id, create_locked_ice_material_snapshot())
    shear = next(p for p in material.properties if p.kind is FRPPropertyKind.FSH_LT)
    adjusted = adjust_frp_property(shear.kind, shear.value, shear.qualification_status, END_USE)
    return FRPAngleContext(
        ConnectorMaterialFamily.PULTRUDED_FRP,
        True,
        material,
        adjusted,
        base_fingerprint(
            (
                "STAGE_4_5_MEMBER_ATTACHMENT" if attachment else "STAGE_4_5_ANGLE_BODY",
                preview.response_binding,
                transfer.connector_id,
                transfer.core.request.member_action,
            )
        ),
        base_fingerprint((preview.response_binding, transfer.connector_id)),
    )


def fastener_binding(preview: ColumnMomentPreview, owner: Face) -> str:
    return base_fingerprint(
        (
            "STAGE_4_5_EXACT_PHYSICAL_BOLT_GRADE_THREAD_GRIP",
            preview.input.physical_connector(owner),
            tuple(b for b in preview.response_binding.physical_bolts if b.owner_connector == owner),
            preview.response_binding,
            preview.response.fingerprint,
        )
    )


def column_zone_binding(preview: ColumnMomentPreview) -> str:
    return base_fingerprint(
        (
            "STAGE_4_5_EXACT_COMBINED_COLUMN_END_ZONE",
            preview.response_binding,
            preview.response,
            tuple(t.core.fingerprint for t in preview.transfers),
        )
    )
