"""CME-1 semantic ownership adapter over native, server-built physical scenes.

Only canonical builders supply this function. Body eligibility is an explicit
physical-ID policy, never a shape-name or client-role inference.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, fields, is_dataclass
from typing import cast

from frp_master_connection.application.calculation_orchestration import _fingerprint_code_mapping
from frp_master_connection.application.clip_angle_orchestration import (
    ClipAngleBoxTrace,
    ClipAngleTriangleMeshTrace,
)
from frp_master_connection.application.connection_preview import SingleBoltPreviewResult
from frp_master_connection.application.dctn3b import DCTN3BPreview
from frp_master_connection.application.double_channel_truss_node import DCTNPreview
from frp_master_connection.application.multi_member_tee_orchestration import (
    MultiMemberTeePreviewResult,
    MultiMemberTeeVisualizationSnapshot,
)
from frp_master_connection.application.multirow_orchestration import (
    MultiRowLayerVisualization,
    MultiRowPreviewResult,
    MultiRowVisualizationSnapshot,
)
from frp_master_connection.application.tee_orchestration import (
    TeeConnectorPreviewResult,
    TeeVisualizationSnapshot,
)
from frp_master_connection.application.visualization import (
    BoltDisplaySnapshot,
    VisualizationComponent,
)
from frp_master_connection.application.web_splice_orchestration import WebSpliceBox
from frp_master_connection.application.wi_wall_moment_geometry import WallMomentPart
from frp_master_connection.calculation.angle_connector_core import angle_fingerprint
from frp_master_connection.domain.connector_materials import CanonicalComponent, ComponentRole

R = ComponentRole
PLATES = (
    "POSITIVE_WEB_SPLICE_PLATE",
    "NEGATIVE_WEB_SPLICE_PLATE",
    "BACK_WEB_SPLICE_PLATE",
    "OPENING_WEB_SPLICE_PLATE",
    "TOP_OUTER_FLANGE_SPLICE_PLATE",
    "TOP_NEGATIVE_INNER_FLANGE_SPLICE_PLATE",
    "TOP_POSITIVE_INNER_FLANGE_SPLICE_PLATE",
    "BOTTOM_OUTER_FLANGE_SPLICE_PLATE",
    "BOTTOM_NEGATIVE_INNER_FLANGE_SPLICE_PLATE",
    "BOTTOM_POSITIVE_INNER_FLANGE_SPLICE_PLATE",
    "TOP_INNER_FLANGE_SPLICE_PLATE",
    "BOTTOM_INNER_FLANGE_SPLICE_PLATE",
)
ANGLES = (
    "single-clip-angle-connector",
    "POSITIVE_CLIP_ANGLE",
    "NEGATIVE_CLIP_ANGLE",
    "positive-base-angle",
    "negative-base-angle",
    "TOP_FLANGE_ANGLE",
    "BOTTOM_FLANGE_ANGLE",
    "POSITIVE_WEB_ANGLE",
    "NEGATIVE_WEB_ANGLE",
    "LEG_1_BASE_ANGLE",
    "LEG_2_BASE_ANGLE",
    "X_POS",
    "X_NEG",
    "Y_POS",
    "Y_NEG",
)
BODY_FORMS = {
    **dict.fromkeys(PLATES, "PLATE"),
    **dict.fromkeys(ANGLES, "ANGLE"),
    "tee-connector": "TEE",
}
FOUNDATIONS = frozenset(
    {
        "concrete-wall",
        "direct-side-lap-concrete-wall",
        "concrete-base",
        "CONCRETE_WALL",
        "FOUNDATION",
    }
)
MEMBERS = frozenset(
    {
        "clip-angle-support",
        "clip-angle-connected-member",
        "column",
        "WI_BEAM",
        "FRP_SUPPORT",
        "ANGLE_COLUMN",
        "COLUMN",
        "tee-support",
        "tee-brace",
    }
)
BEAM_PARTS = {
    f"{beam}_{part}": beam
    for beam in ("BEAM_A", "BEAM_B")
    for part in ("WEB", "TOP_FLANGE", "BOTTOM_FLANGE")
}
NO_BODY_ROUTES = frozenset(
    {"single-bolt", "multi-row", "direct-side-lap-concrete", "double-channel-truss-node"}
)


def walk_records(value: object) -> Iterator[object]:
    """Walk only an already selected native geometry/visualization record."""
    if is_dataclass(value) and not isinstance(value, type):
        yield value
        for field in fields(value):
            yield from walk_records(getattr(value, field.name))
    elif isinstance(value, tuple):
        for child in value:
            yield from walk_records(child)


def _text(value: object, name: str) -> str | None:
    found = getattr(value, name, None)
    return found if isinstance(found, str) else None


@dataclass(frozen=True, slots=True)
class MaterialAssembly:
    components: tuple[CanonicalComponent, ...]
    native_identity: str
    scene_identity: str


def canonical_material_assembly(route: str, preview: object) -> MaterialAssembly:
    if route == "double-channel-truss-node":
        if (
            not isinstance(preview, DCTNPreview | DCTN3BPreview)
            or preview.geometry.status != "VALID"
        ):
            raise ValueError("DCTN material roles require the valid canonical DCTN assembly")
        # Only actual native members and physical shafts are role-bearing.
        # Collision-envelope primitives are not connector bodies or FRP members.
        components = tuple(
            CanonicalComponent(
                member.physical_id, R.PRIMARY_MEMBER, member.profile.family.value, ()
            )
            for member in preview.geometry.members
        ) + tuple(
            CanonicalComponent(
                "HARDWARE:" + shaft.bolt_id, R.FASTENER_OR_HARDWARE, "NATIVE_FASTENER_HARDWARE", ()
            )
            for shaft in preview.geometry.shafts
        )
        return MaterialAssembly(components, preview.fingerprint, preview.fingerprint)
    geometry = getattr(preview, "geometry", None)
    scene = geometry if geometry is not None else getattr(preview, "visualization", None)
    status = str(getattr(geometry or preview, "geometry_status", getattr(geometry, "status", "")))
    if "INVALID" in status or scene is None:
        raise ValueError("A valid native canonical assembly is required before material planning")
    records: dict[str, tuple[ComponentRole, str, set[str]]] = {}

    def add(identity: str, role: ComponentRole, form: str, alias: str | None = None) -> None:
        current = records.get(identity)
        if current is not None and current[:2] != (role, form):
            raise ValueError("Conflicting native physical role identity")
        if current is None:
            records[identity] = (role, form, set())
        if alias is not None and alias != identity:
            records[identity][2].add(alias)

    physical_scene = (
        tuple(
            getattr(geometry, name, ())
            for name in (
                "parts",
                "member_bolts",
                "wall_anchors",
                "support_bolts",
                "foundation_attachments",
                "foundation_washers",
            )
        )
        if geometry is not None
        else scene
    )
    explicit_hardware = isinstance(
        preview, (TeeConnectorPreviewResult, MultiMemberTeePreviewResult, MultiRowPreviewResult)
    )
    for record in walk_records(physical_scene):
        if isinstance(record, BoltDisplaySnapshot):
            if explicit_hardware:
                continue  # Native interface arrays below exclude template proxy bolts.
            add(
                f"HARDWARE:{record.bolt_group_id}:{record.bolt_location_id}",
                R.FASTENER_OR_HARDWARE,
                "NATIVE_FASTENER_HARDWARE",
            )
        elif isinstance(record, VisualizationComponent):
            role = (
                R.CONNECTOR_BODY
                if route not in NO_BODY_ROUTES and record.id == "tee-connector"
                else R.PRIMARY_MEMBER
            )
            if role is R.PRIMARY_MEMBER and record.material_kind.value != "PULTRUDED_FRP":
                raise ValueError("PRIMARY_MEMBER_FRP_ONLY: native member material is not FRP")
            if isinstance(preview, MultiMemberTeePreviewResult) and record.id == "tee-brace":
                continue  # Per-slot member IDs below, not three aliases of one member.
            add(record.id, role, "TEE" if role is R.CONNECTOR_BODY else "FRP_MEMBER")
            for element in record.elements:
                add(
                    record.id,
                    role,
                    "TEE" if role is R.CONNECTOR_BODY else "FRP_MEMBER",
                    f"{record.id}:{element.id}",
                )
        elif isinstance(record, MultiRowLayerVisualization) and route == "multi-row":
            add(record.component_id, R.PRIMARY_MEMBER, "FRP_MEMBER")
        else:
            owner = _text(record, "owner_id") or _text(record, "component_id")
            if isinstance(record, WallMomentPart):
                owner = record.box.component_id
            # A physical solid has dimensions/points. Material-axis or demand
            # records with a component_id cannot create an eligible body.
            solid = isinstance(
                record,
                (ClipAngleBoxTrace, ClipAngleTriangleMeshTrace, WebSpliceBox, WallMomentPart),
            )
            if owner is not None and solid:
                if route not in NO_BODY_ROUTES and owner in BODY_FORMS:
                    role, form = R.CONNECTOR_BODY, BODY_FORMS[owner]
                elif owner in FOUNDATIONS:
                    role, form = R.FOUNDATION, "CONCRETE"
                elif owner in MEMBERS or owner in BEAM_PARTS:
                    role, form = R.PRIMARY_MEMBER, "FRP_MEMBER"
                else:
                    role, form = R.UNCLASSIFIED, "UNCLASSIFIED"
                identity = BEAM_PARTS.get(owner, owner)
                add(identity, role, form, owner)
                add(identity, role, form, _text(record, "id"))
                add(identity, role, form, _text(record, "part_id"))
                element_id = _text(record, "physical_element_id")
                if element_id:
                    add(identity, role, form, f"{identity}:{element_id}")
            hardware = (
                _text(record, "hardware_id")
                or _text(record, "bolt_id")
                or _text(record, "anchor_id")
            )
            if hardware is not None and not explicit_hardware:
                group = _text(record, "group_id") or _text(record, "bolt_group_id") or "NATIVE"
                add(
                    f"HARDWARE:{group}:{hardware}",
                    R.FASTENER_OR_HARDWARE,
                    "NATIVE_FASTENER_HARDWARE",
                )
    if isinstance(preview, MultiMemberTeePreviewResult):
        for slot in preview.slots:
            add(slot.connected_member_id, R.PRIMARY_MEMBER, "FRP_MEMBER")
            add("tee-connector", R.CONNECTOR_BODY, "TEE", f"{slot.slot_id}:tee-connector")
        multi_scene = cast(MultiMemberTeeVisualizationSnapshot, preview.visualization)
        for index, slot_scene in enumerate(multi_scene.slots):
            for bolt in slot_scene.visualization.interface_b_bolts:
                add(
                    f"HARDWARE:{slot_scene.bolt_group_id}:{bolt.bolt_location_id}",
                    R.FASTENER_OR_HARDWARE,
                    "NATIVE_FASTENER_HARDWARE",
                )
            if index == 0:
                for bolt in slot_scene.visualization.interface_a_bolts:
                    add(
                        f"HARDWARE:{preview.support.bolt_group_id}:{bolt.bolt_location_id}",
                        R.FASTENER_OR_HARDWARE,
                        "NATIVE_FASTENER_HARDWARE",
                    )
    elif isinstance(preview, TeeConnectorPreviewResult):
        tee_scene = cast(TeeVisualizationSnapshot, preview.visualization)
        for bolt in (
            *tee_scene.interface_a_bolts,
            *tee_scene.interface_b_bolts,
        ):
            add(
                f"HARDWARE:{bolt.bolt_group_id}:{bolt.bolt_location_id}",
                R.FASTENER_OR_HARDWARE,
                "NATIVE_FASTENER_HARDWARE",
            )
    elif isinstance(preview, MultiRowPreviewResult):
        row_scene = cast(MultiRowVisualizationSnapshot, preview.visualization)
        for bolt_location in row_scene.bolts:
            add(
                f"HARDWARE:NATIVE:{bolt_location.bolt_id}",
                R.FASTENER_OR_HARDWARE,
                "NATIVE_FASTENER_HARDWARE",
            )
    if not records:
        raise ValueError("Native preview supplied no classified physical components")
    components = tuple(
        CanonicalComponent(key, role, form, tuple(sorted(aliases)))
        for key, (role, form, aliases) in sorted(records.items())
    )
    native_identity: str | None
    if isinstance(preview, SingleBoltPreviewResult):
        native_identity = angle_fingerprint(
            (
                "CME-1-NATIVE-PREVIEW-MAPPING",
                components,
                _fingerprint_code_mapping(preview.material_relationships),
            )
        )
    else:
        native_identity = _text(preview, "engineering_fingerprint") or _text(
            preview, "preview_fingerprint"
        )
        if native_identity is None:
            raise ValueError("Native family identity policy has not been declared")
    return MaterialAssembly(components, native_identity, native_identity)
