"""Additive SAB2 transport: geometry authority is separate from structural authority."""

import asyncio
import hashlib
import json
from collections.abc import Awaitable, Callable
from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal, localcontext
from typing import Annotated, Any, Literal, Protocol, Self, cast

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from fastapi.routing import APIRoute
from pydantic import Field, StrictStr, model_validator

from frp_master_connection.api.dependencies import build_trusted_identity_dependency
from frp_master_connection.api.mat1 import MultiRowMAT1RequestDTO, build_mat1_router
from frp_master_connection.api.multirow_mapping import (
    _serialize,
    map_multirow_request,
    serialize_multirow_preview,
)
from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO
from frp_master_connection.api.schemas import Identifier, QuantityDTO, _StrictModel
from frp_master_connection.application.direct_support_ends import DirectSupportEndAuthority
from frp_master_connection.application.direct_two_bolt_display import display_constraints
from frp_master_connection.application.direct_two_bolt_geometry import (
    FRAME_PRECISION,
    ONE,
    P2,
    V3,
    ZERO,
    Axes,
    Boundary,
    Cylinder,
    Face,
    Obstacle,
    PairInput,
    accessible_strips,
    add,
    bounded_regions,
    dot,
    evaluate_pair,
    local_point,
    polygon_boundaries,
    scale,
    shifted_moment,
    subtract,
)
from frp_master_connection.application.direct_two_bolt_source import (
    GeometrySourceView,
    GeometrySupportEnds,
    unmapped_geometry_source,
)
from frp_master_connection.application.multirow_orchestration import (
    DirectMultiRowPreviewResult,
    MultiRowVisualizationSnapshot,
    preview_multirow_connection,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.reporting.provenance import server_defaulted_fields
from frp_master_connection.reporting.routes import (
    MAX_CONCURRENT_REPORTS,
    MAX_PDF_BYTES,
    MAX_QUEUE_SECONDS,
    MAX_RENDER_SECONDS,
)
from frp_master_connection.reporting.snapshot import SnapshotError
from frp_master_connection.security import TrustedIdentity, TrustedIdentityResolver

CONTRACT = "SHEAR01-DIRECT-SAB2-GEOMETRY-V1"


def inches(quantity: QuantityDTO) -> Decimal:
    if quantity.unit not in {Unit.IN, Unit.MM}:
        raise ValueError("Geometry dimensions require explicit in or mm units.")
    return PhysicalQuantity.of(quantity.value, quantity.unit).to(Unit.IN).magnitude


class OffsetDTO(_StrictModel):
    support_longitudinal: QuantityDTO
    support_transverse: QuantityDTO


class EnvelopeDTO(_StrictModel):
    kind: Literal["HEAD", "NUT", "TOOL"]
    radius: QuantityDTO
    axial_start: QuantityDTO
    axial_end: QuantityDTO
    source: Annotated[StrictStr, Field(min_length=1, max_length=512)]


class NeighborDTO(_StrictModel):
    id: Identifier
    support_local_lower: tuple[QuantityDTO, QuantityDTO, QuantityDTO]
    support_local_upper: tuple[QuantityDTO, QuantityDTO, QuantityDTO]
    source: Annotated[StrictStr, Field(min_length=1, max_length=512)]


class EndCutDTO(_StrictModel):
    member_id: Identifier
    polygon: Annotated[
        tuple[tuple[QuantityDTO, QuantityDTO], ...], Field(min_length=3, max_length=16)
    ]
    source: Annotated[StrictStr, Field(min_length=1, max_length=512)]


class SearchDTO(_StrictModel):
    minimum: OffsetDTO
    maximum: OffsetDTO


class TwoBoltRequestDTO(_StrictModel):
    contract: Literal["SHEAR01-DIRECT-SAB2-GEOMETRY-V1"]
    revision: Annotated[StrictStr, Field(min_length=1, max_length=128)]
    legacy: MultiRowConnectionRequestDTO
    material_request: MultiRowMAT1RequestDTO | None = None
    alignment: Literal["BRACE", "SUPPORT"] = "BRACE"
    spacing: QuantityDTO | None = None
    hole_diameter: QuantityDTO | None = None
    offset: OffsetDTO | None = None
    angle_root_encroachment: QuantityDTO | None = None
    support_root_encroachment: QuantityDTO | None = None
    manufactured_geometry_source: Annotated[StrictStr, Field(max_length=512)] = ""
    end_cuts: Annotated[tuple[EndCutDTO, ...], Field(max_length=2)] = ()
    neighbors: Annotated[tuple[NeighborDTO, ...], Field(max_length=32)] = ()
    hardware: Annotated[tuple[EnvelopeDTO, ...], Field(max_length=3)] = ()
    midpoint_search: SearchDTO | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> Self:
        legacy = self.legacy
        if self.material_request is not None and self.material_request.legacy_request != legacy:
            raise ValueError(
                "Material design inputs must match the submitted geometry inputs exactly."
            )
        if legacy.direct_finalization_contract_version != "SHEAR01-DIRECT-F1":
            raise ValueError("SAB2 requires the accepted physical Direct contract.")
        if legacy.physical_connection is None or sorted(
            m.section.kind for m in legacy.physical_connection.joint_assembly.members
        ) != ["ANGLE", "WIDE_FLANGE"]:
            raise ValueError("SAB2 production geometry requires the actual Angle and I/W members.")
        if legacy.row_count != 2 or legacy.bolts_per_row != 1:
            raise ValueError(
                "This new option requires exactly two collinear bolts. The legacy "
                "row-count workflow remains available."
            )
        sizes = [self.spacing or legacy.pitch]
        if self.hole_diameter is not None and inches(self.hole_diameter) < inches(
            legacy.bolt_diameter
        ):
            raise ValueError("A geometry-only hole cannot be smaller than the actual bolt.")
        if any(inches(q) <= ZERO for q in sizes):
            raise ValueError("Spacing must be finite and positive.")
        for root in (self.angle_root_encroachment, self.support_root_encroachment):
            if root is not None and (
                inches(root) < ZERO or not self.manufactured_geometry_source.strip()
            ):
                raise ValueError("Root geometry requires a nonnegative sourced encroachment.")
        if self.offset is not None:
            inches(self.offset.support_longitudinal)
            inches(self.offset.support_transverse)
        if len({c.member_id for c in self.end_cuts}) != len(self.end_cuts):
            raise ValueError("Duplicate physical end-cut definitions are not permitted.")
        if len({n.id for n in self.neighbors}) != len(self.neighbors) or len(
            {e.kind for e in self.hardware}
        ) != len(self.hardware):
            raise ValueError("Duplicate neighbor or hardware definitions are not permitted.")
        return self


def fingerprint(request: TwoBoltRequestDTO) -> str:
    payload = request.model_dump(mode="json")
    # View extents and display units never change the physical geometry identity.
    for legacy in (
        payload["legacy"],
        None
        if payload["material_request"] is None
        else payload["material_request"]["legacy_request"],
    ):
        if legacy is not None:
            physical = legacy["physical_connection"]
            if physical is not None:
                physical.pop("view_extents", None)
            legacy.pop("display_unit_system", None)
    payload.pop("revision")
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class Coordinates(Protocol):
    @property
    def x(self) -> float: ...
    @property
    def y(self) -> float: ...
    @property
    def z(self) -> float: ...


def _vector(value: Coordinates, factor: Decimal = ONE) -> V3:
    return (
        Decimal(str(value.x)) * factor,
        Decimal(str(value.y)) * factor,
        Decimal(str(value.z)) * factor,
    )


def resolve_geometry(request: TwoBoltRequestDTO) -> tuple[PairInput, dict[str, Any]]:
    """Reconstruct from typed members, actual selected faces and server placements."""
    legacy = request.legacy
    mapped = map_multirow_request(legacy)
    native = preview_multirow_connection(mapped)
    evidence = serialize_multirow_preview(native, include_direct_clearance=True).model_dump(
        mode="json"
    )
    visual: MultiRowVisualizationSnapshot | GeometrySourceView
    support_authority: DirectSupportEndAuthority | GeometrySupportEnds | None
    if isinstance(native, DirectMultiRowPreviewResult) and native.visualization is not None:
        visual = native.visualization
        support_authority = native.direct_support_end_authority
    else:
        visual, support_authority = unmapped_geometry_source(mapped)
        evidence["design_check_ready"] = False
        evidence["visualization"] = {
            "physical_connection": _serialize(visual.physical_connection),
            "physical_bolts": _serialize(visual.physical_bolts),
            "source_length_unit": legacy.source_length_unit.value,
            "connection_demand": None,
            "automatic_bolt_demands": [],
        }
        evidence["geometry_source_scope"] = (
            "Physical geometry only; original resistance preview and guards remain unchanged."
        )
        evidence["source_placement_trace"] = _serialize(visual.placement_trace)
    physical = visual.physical_connection
    if physical is None or len(visual.physical_bolts) != 2:
        raise ValueError("Both physical Direct bolt paths are required.")
    factor = PhysicalQuantity.of("1", legacy.source_length_unit).to(Unit.IN).magnitude
    frames = {f.id: f.frame for f in physical.frames}
    components = {c.id: c for c in physical.components}
    support = next(c for c in physical.components if c.section_family == "WIDE_FLANGE")
    declaration = legacy.supporting_w_longitudinal_ends
    evidence["geometry_support_end_authority"] = {
        "condition": str(support_authority.condition)
        if support_authority is not None
        else "UNSPECIFIED",
        "component_id": support.id,
        "length_unit": legacy.source_length_unit.value,
        "negative_end_distance": None
        if declaration is None or declaration.negative_end_distance is None
        else declaration.negative_end_distance.model_dump(mode="json"),
        "positive_end_distance": None
        if declaration is None or declaration.positive_end_distance is None
        else declaration.positive_end_distance.model_dump(mode="json"),
        "negative_end_member_local_station": None
        if support_authority is None or support_authority.actual_end(True) is None
        else str(support_authority.actual_end(True)),
        "positive_end_member_local_station": None
        if support_authority is None or support_authority.actual_end(False) is None
        else str(support_authority.actual_end(False)),
    }
    support_frame = frames[f"MEMBER_LOCAL:{support.id}"]
    support_axes: Axes = (
        _vector(support_frame.x_axis),
        _vector(support_frame.y_axis),
        _vector(support_frame.z_axis),
    )
    original = tuple(item.display for item in visual.physical_bolts)
    midpoint = scale(
        add(_vector(original[0].center, factor), _vector(original[1].center, factor)), Decimal(".5")
    )
    if request.offset is not None:
        midpoint = add(
            midpoint,
            add(
                scale(support_axes[0], inches(request.offset.support_longitudinal)),
                scale(support_axes[1], inches(request.offset.support_transverse)),
            ),
        )
    brace_id = original[0].holes[0].participant_id
    brace_frame = frames[f"MEMBER_LOCAL:{brace_id}"]
    direction = _vector(brace_frame.x_axis) if request.alignment == "BRACE" else support_axes[0]
    if identical_legacy_layout(request):
        # Retain the exact accepted physical station representation. Its direction
        # is reconstructed from those same two stations, not a new placement.
        first, second = _vector(original[0].center, factor), _vector(original[1].center, factor)
        delta = subtract(second, first)
        sign = ONE if dot(delta, direction) > ZERO else -ONE
        canonical = scale(delta, sign / inches(legacy.pitch))
        if any(abs(a - b) > FRAME_PRECISION for a, b in zip(canonical, direction, strict=True)):
            raise ValueError("Legacy physical stations do not match the governed brace frame.")
        direction = canonical
    normal = _vector(original[0].axis)
    faces: list[Face] = []
    strips: tuple[tuple[Decimal, Decimal], ...]
    for index, hole in enumerate(original[0].holes):
        primitive = next(
            p
            for p in physical.primitives
            if p.owner_id == hole.participant_id
            and p.physical_element_id == hole.physical_element_id
            and p.kind.value == "BOX"
        )
        frame = frames[primitive.frame_id]
        values = {p.name: Decimal(str(p.value)) * factor for p in primitive.parameters}
        leg_two = hole.physical_element_id == "LEG_2"
        transverse = "z" if leg_two else "y"
        axes: Axes = (
            _vector(frame.x_axis),
            _vector(frame.z_axis) if leg_two else _vector(frame.y_axis),
            scale(_vector(frame.y_axis), -ONE) if leg_two else _vector(frame.z_axis),
        )
        # Each washer seats on its actual outer member face, not the contact crop.
        washer = next(
            w
            for w in original[0].washers
            if w.location == ("UNDER_HEAD" if index == 0 else "UNDER_NUT")
        )
        seat = washer.end if index == 0 else washer.start
        member_origin = _vector(frame.origin, factor)
        seat_local = local_point(_vector(seat, factor), member_origin, axes)
        origin = add(member_origin, scale(axes[2], seat_local[2]))
        is_support = hole.participant_id == support.id
        boundaries = [
            Boundary(
                f"{primitive.id}:FREE_SIDE_MIN",
                ZERO,
                -ONE,
                -values[f"min_{transverse}"],
                "INTERNAL_JUNCTION" if not is_support else "PHYSICAL_FREE_EDGE",
                primitive.id,
            ),
            Boundary(
                f"{primitive.id}:FREE_SIDE_MAX",
                ZERO,
                ONE,
                values[f"max_{transverse}"],
                "PHYSICAL_FREE_EDGE",
                primitive.id,
            ),
        ]
        unknowns = [
            "Actual installation access and neighboring connection geometry are not established."
        ]
        if is_support:
            authority = support_authority
            if authority is None:
                raise ValueError("Supporting-member end authority is missing.")
            for minimum in (True, False):
                end = authority.actual_end(minimum)
                if end is not None:
                    boundaries.append(
                        Boundary(
                            f"{support.id}:END:{minimum}",
                            -ONE if minimum else ONE,
                            ZERO,
                            end * factor * (-ONE if minimum else ONE),
                            "REAL_SUPPORT_MEMBER_END",
                            authority.reference_source,
                        )
                    )
            if authority.condition.value == "UNSPECIFIED":
                unknowns.append(
                    "Actual supporting-member end condition is unspecified; display crops"
                    " are not ends."
                )
            web = next(
                p
                for p in physical.primitives
                if p.owner_id == support.id
                and p.physical_element_id == "WEB"
                and p.kind.value == "BOX"
            )
            web_values = {p.name: Decimal(str(p.value)) * factor for p in web.parameters}
            root = (
                ZERO
                if request.support_root_encroachment is None
                else inches(request.support_root_encroachment)
            )
            strips = accessible_strips(
                values["min_y"],
                values["max_y"],
                web_values["min_y"],
                web_values["max_y"],
                root,
                "I",
            )
            if request.support_root_encroachment is None:
                unknowns.append(
                    "Actual manufactured support root/fillet profile is unknown; nominal "
                    "sharp geometry only."
                )
        else:
            boundaries.extend(
                (
                    Boundary(
                        f"{brace_id}:PHYSICAL_END_MIN",
                        -ONE,
                        ZERO,
                        -values["x_start"],
                        "PHYSICAL_MEMBER_END",
                        primitive.id,
                    ),
                    Boundary(
                        f"{brace_id}:PHYSICAL_END_MAX",
                        ONE,
                        ZERO,
                        values["x_end"],
                        "PHYSICAL_MEMBER_END",
                        primitive.id,
                    ),
                )
            )
            root = (
                ZERO
                if request.angle_root_encroachment is None
                else inches(request.angle_root_encroachment)
            )
            boundaries[0] = Boundary(
                boundaries[0].id,
                ZERO,
                -ONE,
                -values[f"min_{transverse}"] - root,
                "INTERNAL_JUNCTION",
                request.manufactured_geometry_source or primitive.id,
            )
            strips = ()
            if request.angle_root_encroachment is None:
                unknowns.append(
                    "Actual manufactured Angle heel/root profile is unknown; nominal "
                    "sharp geometry only."
                )
        cut = next((c for c in request.end_cuts if c.member_id == hole.participant_id), None)
        if cut is not None:
            boundaries.extend(
                polygon_boundaries(
                    tuple((inches(p[0]), inches(p[1])) for p in cut.polygon), cut.source
                )
            )
        faces.append(
            Face(
                f"{hole.participant_id}:{hole.physical_element_id}:OUTER_SEAT",
                hole.participant_id,
                origin,
                axes,
                tuple(boundaries),
                strips,
                tuple(unknowns),
                primitive.id,
            )
        )
    if any(c.member_id not in components for c in request.end_cuts):
        raise ValueError("End-cut member is not part of the submitted Direct assembly.")
    # Neighbor coordinates refer to the actual support frame; no adjacent assembly
    # is borrowed from a different connection workspace.
    obstacles = tuple(
        Obstacle(
            n.id,
            _vector(support_frame.origin, factor),
            support_axes,
            cast(V3, tuple(inches(q) for q in n.support_local_lower)),
            cast(V3, tuple(inches(q) for q in n.support_local_upper)),
            n.source,
        )
        for n in request.neighbors
    )
    stack_start = _vector(original[0].stack_start, factor)
    stack_end = _vector(original[0].stack_end, factor)
    span = tuple(
        sorted(
            (
                dot(subtract(stack_start, _vector(original[0].center, factor)), normal),
                dot(subtract(stack_end, _vector(original[0].center, factor)), normal),
            )
        )
    )
    washer_spans = tuple(
        cast(
            tuple[Decimal, Decimal],
            tuple(
                sorted(
                    (
                        dot(
                            subtract(_vector(w.start, factor), _vector(original[0].center, factor)),
                            normal,
                        ),
                        dot(
                            subtract(_vector(w.end, factor), _vector(original[0].center, factor)),
                            normal,
                        ),
                    )
                )
            ),
        )
        for w in original[0].washers
    )
    pair = PairInput(
        midpoint,
        direction,
        normal,
        inches(request.spacing or legacy.pitch),
        Decimal(str(original[0].bolt_diameter)) * factor / 2,
        (
            Decimal(str(original[0].holes[0].diameter)) * factor
            if request.hole_diameter is None
            else inches(request.hole_diameter)
        )
        / 2,
        Decimal(str(original[0].washers[0].outside_diameter)) * factor / 2,
        cast(tuple[Decimal, Decimal], span),
        washer_spans,
        tuple(faces),
        obstacles,
        tuple(
            Cylinder(e.kind, inches(e.radius), inches(e.axial_start), inches(e.axial_end), e.source)
            for e in request.hardware
        ),
    )
    return pair, evidence


def identical_legacy_layout(request: TwoBoltRequestDTO) -> bool:
    legacy = request.legacy
    return (
        request.alignment == "BRACE"
        and request.hole_diameter is None
        and inches(request.spacing or legacy.pitch) == inches(legacy.pitch)
        and (
            request.offset is None
            or (
                inches(request.offset.support_longitudinal) == ZERO
                and inches(request.offset.support_transverse) == ZERO
            )
        )
        and not request.end_cuts
    )


def absolute_proposal_offset(request: TwoBoltRequestDTO, proposed_offset: P2) -> list[str]:
    """Use the shared kernel precision for exact Apply strings; no UI float sum."""
    with localcontext() as context:
        context.prec = 64
        current = (
            (ZERO, ZERO)
            if request.offset is None
            else (
                inches(request.offset.support_longitudinal),
                inches(request.offset.support_transverse),
            )
        )
        return [str(a + b) for a, b in zip(current, proposed_offset, strict=True)]


def geometry_response(request: TwoBoltRequestDTO) -> dict[str, Any]:
    pair, previous = resolve_geometry(request)
    result = evaluate_pair(pair)
    unchanged = identical_legacy_layout(request)
    # Full physical/action/material/hardware contract is preserved in the strict
    # typed legacy object. Only the identical layout may enter its existing route.
    compatible = (
        unchanged and previous["design_check_ready"] and result.aggregate_state != "DOES_NOT_FIT"
    )
    route = "B_FRESH_LEGACY_COMPATIBLE" if compatible else "C_GEOMETRY_ONLY"
    reason = (
        "Server-preserved identical typed Direct layout, physical faces, "
        "stack, actions/references, material/conditions, methods and existing"
        " applicability guards. A fresh accepted calculation is required."
        if compatible
        else "Structural design not evaluated: this layout has no complete mapping"
        " to the accepted Direct calculation contract, or current "
        "physical/input guards block it."
    )
    if request.alignment == "SUPPORT":
        reason = (
            "Support-aligned two-bolt geometry has no approved Direct "
            "bolt-demand, first-row or Supporting W method mapping. Structural "
            "design is not evaluated."
        )
    data: dict[str, Any] = {
        "contract": CONTRACT,
        "revision": request.revision,
        "geometry_fingerprint": fingerprint(request),
        "alignment": request.alignment,
        "pair_input": asdict(pair),
        "geometry": asdict(result),
        "structural_route": route,
        "structural_eligible": compatible,
        "structural_reason": reason,
        "resistance_evaluated": False,
        "qualification_activated": False,
        "direct_support_end_authority": previous["geometry_support_end_authority"],
        "legacy_mapping_proof": {
            "identical_layout": unchanged,
            "existing_guard_ready": previous["design_check_ready"],
            "preserved_typed_request": request.legacy.model_dump(mode="json"),
            "material_request": None
            if request.material_request is None
            else request.material_request.model_dump(mode="json"),
            "legacy_preview_fingerprint": previous["preview_fingerprint"],
            "mapping_scope": {
                "physical_members_faces_ends": "Preserved accepted typed physical_connection",
                "stations_holes_paths": (
                    "Reconstructed from the same two accepted physical stations; neutral "
                    "labels mapped by coordinates"
                ),
                "axes_actions_references": (
                    "Preserved accepted placements, source_action_id and joint_assembly"
                ),
                "fastener_threads_lap": (
                    "Preserved accepted native fastener snapshot and optional current "
                    "MAT1 fastener binding"
                ),
                "materials_conditions_factors": (
                    "Same typed material_request, validated to contain exactly the "
                    "current legacy_request"
                ),
                "method_applicability": (
                    "Same preview_multirow_connection guards and fresh existing MAT1 design handler"
                ),
                "new_root_hardware_context": (
                    "Independent constructability context; any known negative margin blocks Route B"
                ),
            },
            "accepted_physical_stations": previous["visualization"]["physical_bolts"],
            "neutral_to_legacy_station_mapping": [
                {
                    "neutral_station": f"B{i + 1}",
                    "legacy_bolt_id": station["bolt_id"],
                    "legacy_row_id": station["row_id"],
                    "raw_legacy_global_center": station["display"]["center"],
                    "canonical_global_center_inches": list(result.centers[i]),
                    "structural_authority": (
                        "Fresh original legacy IDs only; neutral labels establish no first-row rule"
                    ),
                }
                for i, station in enumerate(
                    sorted(
                        previous["visualization"]["physical_bolts"],
                        key=lambda bolt: dot(
                            cast(
                                V3,
                                tuple(
                                    Decimal(str(bolt["display"]["center"][a]))
                                    for a in ("x", "y", "z")
                                ),
                            ),
                            pair.direction,
                        ),
                    )
                )
            ]
            if unchanged
            else [],
            "source_placement_trace": previous.get("source_placement_trace"),
            "representation_contract": (
                "Existing dimensionless proper-frame precision; no clearance margin is clamped"
            ),
        },
        "comparison": {},
        "midpoint_regions": [],
        "visualization": display_constraints(
            geometry_visualization(
                previous["visualization"],
                result.centers,
                pair.hole_radius * 2,
                preserve_native_identity=compatible,
            ),
            pair,
            PhysicalQuantity.of("1", Unit.IN)
            .to(Unit(previous["visualization"]["source_length_unit"]))
            .magnitude,
        ),
        "moment_diagnostic": moment_diagnostic(previous["visualization"], pair.midpoint),
    }
    other = request.model_copy(
        update={
            "alignment": "SUPPORT" if request.alignment == "BRACE" else "BRACE",
            "midpoint_search": None,
        }
    )
    other_pair, _ = resolve_geometry(other)
    data["comparison"] = {
        "basis": "Fixed members, midpoint, spacing, hardware and actions; only "
        "center-line alignment changes.",
        "alignment": other.alignment,
        "geometry": asdict(evaluate_pair(other_pair)),
    }
    if request.midpoint_search is not None:
        minimum, maximum = request.midpoint_search.minimum, request.midpoint_search.maximum
        support_face = pair.faces[1]
        regions = bounded_regions(
            pair,
            (support_face.axes[0], support_face.axes[1]),
            (
                inches(minimum.support_longitudinal),
                inches(maximum.support_longitudinal),
                inches(minimum.support_transverse),
                inches(maximum.support_transverse),
            ),
        )
        from dataclasses import replace

        for region in regions:
            proposed = replace(
                pair,
                midpoint=add(
                    pair.midpoint,
                    add(
                        scale(support_face.axes[0], region.proposed_offset[0]),
                        scale(support_face.axes[1], region.proposed_offset[1]),
                    ),
                ),
            )
            data["midpoint_regions"].append(
                {
                    **asdict(region),
                    "proposed_request_offset": absolute_proposal_offset(
                        request, region.proposed_offset
                    ),
                    "scope": (
                        "Bounded seating region; known obstruction and envelope recheck at proposal"
                    ),
                    "candidate_geometry": asdict(evaluate_pair(proposed)),
                    "moment_diagnostic": moment_diagnostic(
                        previous["visualization"], proposed.midpoint
                    ),
                }
            )
    return cast(dict[str, Any], json.loads(json.dumps(data, default=str)))


def geometry_visualization(
    legacy: dict[str, Any],
    centers: tuple[V3, V3],
    hole_diameter: Decimal,
    *,
    preserve_native_identity: bool = False,
) -> dict[str, Any]:
    """Translate actual shaft, holes and washers to the common new centers.

    This is presentation reconstruction, never a demand or resistance result.
    Member solids, faces, action references and physical ends are preserved.
    """
    visual = deepcopy(legacy)
    factor = PhysicalQuantity.of("1", Unit.IN).to(Unit(visual["source_length_unit"])).magnitude
    for index, bolt in enumerate(visual["physical_bolts"]):
        if preserve_native_identity:
            # Eligible Route B retains original IDs and station coordinates so
            # fresh native row results bind to the same physical bolt. The audit
            # explicitly maps neutral geometry labels to those original IDs.
            continue
        display = bolt["display"]
        old = tuple(Decimal(str(display["center"][axis])) for axis in ("x", "y", "z"))
        delta = tuple(centers[index][i] * factor - old[i] for i in range(3))

        def translate(point: dict[str, Any], displacement: tuple[Decimal, ...] = delta) -> None:
            for i, axis in enumerate(("x", "y", "z")):
                point[axis] = str(Decimal(str(point[axis])) + displacement[i])

        for name in ("center", "stack_start", "stack_end"):
            translate(display[name])
        for part in (*display["holes"], *display["washers"]):
            translate(part["start"])
            translate(part["end"])
        for hole in display["holes"]:
            hole["diameter"] = str(hole_diameter * factor)
        bolt["bolt_id"] = display["bolt_location_id"] = f"B{index + 1}"
        bolt["row_id"] = f"GEOMETRIC_STATION_{index + 1}"
    visual["physical_connection"]["bolt"] = deepcopy(visual["physical_bolts"][0]["display"])
    # Old native row forces and engineering block paths cannot describe new stations.
    visual["automatic_bolt_demands"] = []
    visual["connection_demand"] = None
    visual["block_paths"] = []
    return visual


def moment_diagnostic(visual: dict[str, Any], midpoint: V3) -> dict[str, Any]:
    """Transport only M_G=M_P+(P-G)xF from authenticated global action arrows."""
    snapshot = visual["physical_connection"]
    arrows = snapshot["applied_action_directions"]
    references = {p["id"]: p["position"] for p in snapshot["reference_points"]}
    origins = {
        tuple(str(references[a["reference_point_id"]][axis]) for axis in ("x", "y", "z"))
        for a in arrows
    }
    if len(origins) != 1:
        return {
            "state": "NOT_EVALUATED",
            "reason": "A single resolved action reference is required.",
        }
    factor = PhysicalQuantity.of("1", Unit(snapshot["length_unit"])).to(Unit.IN).magnitude
    reference = cast(V3, tuple(Decimal(v) * factor for v in next(iter(origins))))
    force: V3 = (ZERO, ZERO, ZERO)
    moment: V3 = (ZERO, ZERO, ZERO)
    for arrow in arrows:
        if arrow["signed_value"] is None or arrow["unit"] is None:
            return {"state": "NOT_EVALUATED", "reason": "Action magnitude or units are unresolved."}
        axis = cast(V3, tuple(Decimal(str(arrow["axis"][a])) for a in ("x", "y", "z")))
        rotational = arrow["kind"] == "ROTATIONAL"
        magnitude = (
            PhysicalQuantity.of(arrow["signed_value"], Unit(arrow["unit"]))
            .to(Unit.KIP_IN if rotational else Unit.KIP)
            .magnitude
        )
        if rotational:
            moment = add(moment, scale(axis, magnitude))
        else:
            force = add(force, scale(axis, magnitude))
    return {
        "state": "REFERENCE_TRANSPORT_DIAGNOSTIC_ONLY",
        "equation": "M_G = M_P + (P-G) x F",
        "P_global_in": reference,
        "G_global_in": midpoint,
        "F_global_kip": force,
        "M_P_global_kip_in": moment,
        "M_G_global_kip_in": shifted_moment(moment, reference, midpoint, force),
        "per_bolt_demand_evaluated": False,
        "resistance_center_established": False,
    }


class GeometryExportDTO(_StrictModel):
    report_handle: Annotated[StrictStr, Field(min_length=32, max_length=80)]
    current_request: TwoBoltRequestDTO


def build_two_bolt_router(identity_resolver: TrustedIdentityResolver) -> APIRouter:
    router = APIRouter(prefix="/api/v1/direct-two-bolt")
    identity_dependency = build_trusted_identity_dependency(identity_resolver)
    render_slots = asyncio.Semaphore(MAX_CONCURRENT_REPORTS)
    accepted_router = build_mat1_router(identity_resolver)
    accepted_route = next(
        r
        for r in accepted_router.routes
        if isinstance(r, APIRoute) and r.path.endswith("/multi-row/design-check")
    )
    accepted_design = cast(Callable[..., Awaitable[dict[str, object]]], accepted_route.endpoint)

    @router.post("/preview")
    async def preview(
        dto: TwoBoltRequestDTO,
        request: Request,
        identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> dict[str, Any]:
        try:
            result = geometry_response(dto)
            token = request.app.state.report_signer.issue(
                family="direct-sab2-geometry",
                kind="input_only",
                request=dto.model_dump(mode="json"),
                result=result,
                account_id=identity.account_id,
                input_provenance={
                    "server_defaulted_fields": server_defaulted_fields(
                        request.scope.get("route"),
                        await request.json(),
                    ),
                },
            )
            result["geometry_report_handle"] = request.app.state.report_snapshot_store.put(token)
            return result
        except ValueError as error:
            raise HTTPException(
                status_code=422, detail={"code": "SAB2_GEOMETRY_INPUT", "message": str(error)}
            ) from error

    @router.post("/design-check")
    async def design_check(
        dto: TwoBoltRequestDTO,
        request: Request,
        identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> dict[str, Any]:
        try:
            geometry = geometry_response(dto)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if not geometry["structural_eligible"]:
            raise HTTPException(
                status_code=422,
                detail={"code": "SAB2_GEOMETRY_ONLY", "message": geometry["structural_reason"]},
            )
        # This invokes the same accepted handler, with newly validated server-owned
        # inputs. No previous result, utilization or conclusion enters this call.
        if dto.material_request is None:
            raise HTTPException(
                status_code=422,
                detail="Complete current Materials and Project Conditions before Run Design Check.",
            )
        fresh = await accepted_design(dto.material_request, request, identity)
        token = request.app.state.report_signer.issue(
            family="multi-row",
            kind="design",
            request=dto.material_request.model_dump(mode="json"),
            result=fresh,
            input_provenance={
                "SAB2_geometry_fingerprint": geometry["geometry_fingerprint"],
                "SAB2_structural_route": geometry["structural_route"],
                "server_defaulted_fields": server_defaulted_fields(
                    accepted_route,
                    (await request.json())["material_request"],
                ),
            },
            account_id=identity.account_id,
        )
        return {
            "geometry_fingerprint": geometry["geometry_fingerprint"],
            "structural_route": geometry["structural_route"],
            "result": fresh,
            "report_handle": request.app.state.report_snapshot_store.put(token),
        }

    @router.post("/geometry-review")
    async def geometry_review(
        dto: GeometryExportDTO,
        request: Request,
        identity: Annotated[TrustedIdentity, Depends(identity_dependency)],
    ) -> Response:
        try:
            snapshot = request.app.state.report_signer.verify(
                request.app.state.report_snapshot_store.get(dto.report_handle),
                account_id=identity.account_id,
            )
            if snapshot.family != "direct-sab2-geometry" or snapshot.result[
                "geometry_fingerprint"
            ] != fingerprint(dto.current_request):
                raise SnapshotError(
                    "Geometry review is stale or belongs to a different layout. Refresh "
                    "the current geometry preview."
                )
        except (SnapshotError, KeyError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        from frp_master_connection.reporting.direct_two_bolt import render_geometry_review

        try:
            await asyncio.wait_for(render_slots.acquire(), timeout=MAX_QUEUE_SECONDS)
        except TimeoutError as error:
            raise HTTPException(
                status_code=503, detail="Geometry renderer is busy; try again"
            ) from error
        task = asyncio.create_task(asyncio.to_thread(render_geometry_review, snapshot))

        def release_slot(completed: asyncio.Task[bytes]) -> None:
            if not completed.cancelled():
                completed.exception()
            render_slots.release()

        task.add_done_callback(release_slot)
        try:
            pdf = await asyncio.wait_for(asyncio.shield(task), timeout=MAX_RENDER_SECONDS)
        except TimeoutError as error:
            raise HTTPException(status_code=503, detail="Geometry rendering timed out") from error
        except Exception as error:
            raise HTTPException(status_code=503, detail="Geometry rendering failed") from error
        if len(pdf) > MAX_PDF_BYTES:
            raise HTTPException(
                status_code=413, detail="Geometry PDF exceeds the export size limit"
            )
        return Response(
            pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    'attachment; filename="direct-geometry-constructability-review.pdf"'
                ),
                "Cache-Control": "no-store, private",
            },
        )

    return router
