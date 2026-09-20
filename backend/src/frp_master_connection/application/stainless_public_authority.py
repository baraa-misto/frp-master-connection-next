"""Server-only native evidence resolver; there is no public certificate registry.

Exact native evidence is sent to the frozen C2-R source gate where available.
Unqualified branch/bolt distributions are not supplied as resolved outputs.
The production catalogue currently has no qualified stainless response/product
records. Tests may supply controlled internal records without registering them.
"""

from frp_master_connection.application.clip_angle_orchestration import ClipAnglePreviewResult
from frp_master_connection.application.connector_material_assembly import MaterialAssembly
from frp_master_connection.application.stainless_connection_design import ConnectionAuthority
from frp_master_connection.application.stainless_family_activation import (
    BodyBinding,
    unresolved_native_response,
)
from frp_master_connection.application.tee_orchestration import TeeConnectorPreviewResult
from frp_master_connection.application.web_splice_orchestration import WebSplicePreviewResult
from frp_master_connection.calculation.angle_connector_core import AngleWrench, components
from frp_master_connection.calculation.eccentric_demand import (
    EccentricDemandResult,
    ExactQuantityVector3D,
)
from frp_master_connection.domain.connector_materials import ComponentRole


def _native_input(demand: EccentricDemandResult | None) -> AngleWrench | None:
    if demand is None:
        return None
    # These historical shear families reject user moments. Do not add two
    # moment vectors through a new numeric path if a future contract changes.
    if any(components(demand.original_independent_connection_moments)):
        return None
    return AngleWrench(
        demand.force_reference_point,
        demand.original_global_force,
        demand.original_member_end_moments,
    )


def resolve_public_authority(
    route: str, assembly: MaterialAssembly, preview: object, native_design: object
) -> ConnectionAuthority:
    """Closed production resolver, never populated from client flags or records."""
    wrench: AngleWrench | None = None
    if isinstance(preview, ClipAnglePreviewResult):
        wrench = _native_input(preview.interface_a.demand)
    elif isinstance(preview, TeeConnectorPreviewResult):
        wrench = _native_input(preview.interface_a.preview.automatic_demand_result)
    elif isinstance(preview, WebSplicePreviewResult):
        native = preview.beam_a_group.wrench
        wrench = AngleWrench(
            ExactQuantityVector3D(
                native.reference_l_v_t.l, native.reference_l_v_t.v, native.reference_l_v_t.t
            ),
            ExactQuantityVector3D(native.force_l_v_t.l, native.force_l_v_t.v, native.force_l_v_t.t),
            ExactQuantityVector3D(
                native.moment_l_v_t.l, native.moment_l_v_t.v, native.moment_l_v_t.t
            ),
        )
    if wrench is None:
        return ConnectionAuthority()
    return ConnectionAuthority(
        tuple(
            unresolved_native_response(
                BodyBinding(route, body.physical_id, body.body_form, assembly.native_identity),
                wrench,
                assembly.native_identity,
            )
            for body in assembly.components
            if body.role is ComponentRole.CONNECTOR_BODY
        )
    )
