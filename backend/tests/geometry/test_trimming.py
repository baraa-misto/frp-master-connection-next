"""Tests for backend-authoritative fabrication-plane solid trimming."""

from __future__ import annotations

from typing import Any, cast

import pytest

from frp_master_connection.domain import (
    AssemblyMember,
    ComponentMaterialKind,
    MemberEnd,
    MemberRole,
    PositionVector3D,
    SectionFamily,
    create_standard_section_topology,
)
from frp_master_connection.geometry import (
    AuthoritativeCutPlane3D,
    PlacedComponentGeometry3D,
    PlateDimensions,
    RoundTubeDimensions,
    TrimmedPlanarFace3D,
    UnitVector3D,
    Vector3D,
    create_plate_geometry,
    create_round_tube_geometry,
    place_member,
    placed_rectangular_elements_overlap,
    signed_distance_to_plane,
    trim_placed_rectangular_component,
)


def _member(family: SectionFamily) -> AssemblyMember:
    return AssemblyMember(
        id=f"trim-{family.value.lower()}",
        label="Trim test member",
        role=MemberRole.BRACE,
        connected_end=MemberEnd.START,
        section_family=family,
        material_kind=ComponentMaterialKind.STEEL,
        section_topology=create_standard_section_topology(family),
    )


def _placed_plate(
    start_x: float = 0.0,
    end_x: float = 4.0,
) -> PlacedComponentGeometry3D:
    member = _member(SectionFamily.PLATE)
    geometry = create_plate_geometry(
        cast(Any, member.section_topology),
        PlateDimensions(2.0, 0.5),
    )
    return place_member(
        member,
        geometry,
        PositionVector3D(start_x, 0.0, 0.0),
        PositionVector3D(end_x, 0.0, 0.0),
        Vector3D(0.0, 0.0, 1.0),
    )


def test_trim_value_contracts_reject_invalid_identity_and_shape() -> None:
    origin = PositionVector3D(0.0, 0.0, 0.0)
    normal = UnitVector3D(1.0, 0.0, 0.0)
    with pytest.raises(ValueError, match="id must be nonempty"):
        AuthoritativeCutPlane3D(" ", origin, normal)
    with pytest.raises(TypeError, match="origin"):
        AuthoritativeCutPlane3D("CUT", cast(Any, Vector3D(0.0, 0.0, 0.0)), normal)
    with pytest.raises(TypeError, match="normal"):
        AuthoritativeCutPlane3D("CUT", origin, cast(Any, Vector3D(1.0, 0.0, 0.0)))
    with pytest.raises(ValueError, match="id must be nonempty"):
        TrimmedPlanarFace3D(" ", (origin, origin, origin))
    with pytest.raises(ValueError, match="at least three"):
        TrimmedPlanarFace3D("FACE", (origin, origin))


def test_half_space_trim_retains_exact_faces_and_deterministic_identity() -> None:
    placed = _placed_plate()
    cut = AuthoritativeCutPlane3D(
        "CUT",
        PositionVector3D(1.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )

    first = trim_placed_rectangular_component(placed, cut)
    second = trim_placed_rectangular_component(placed, cut)

    assert first == second
    assert first.geometry_fingerprint == second.geometry_fingerprint
    assert first.fabricated_face_ids == ("PLATE:0:CUT:CUT",)
    assert all(signed_distance_to_plane(point, cut) >= -1e-9 for point in first.solids[0].vertices)
    assert len(first.solids[0].triangulated_points) % 3 == 0


def test_trim_supports_uncut_and_transverse_cut_branches_but_rejects_total_removal() -> None:
    placed = _placed_plate()
    fully_retained = trim_placed_rectangular_component(
        placed,
        AuthoritativeCutPlane3D(
            "BEFORE",
            PositionVector3D(-1.0, 0.0, 0.0),
            UnitVector3D(1.0, 0.0, 0.0),
        ),
    )
    transverse = trim_placed_rectangular_component(
        placed,
        AuthoritativeCutPlane3D(
            "TRANSVERSE",
            PositionVector3D(0.0, 0.0, 0.0),
            UnitVector3D(0.0, 0.0, 1.0),
        ),
    )

    assert fully_retained.fabricated_face_ids == ()
    assert transverse.fabricated_face_ids == ("PLATE:0:CUT:TRANSVERSE",)
    with pytest.raises(ValueError, match="removed every"):
        trim_placed_rectangular_component(
            placed,
            AuthoritativeCutPlane3D(
                "AFTER",
                PositionVector3D(5.0, 0.0, 0.0),
                UnitVector3D(1.0, 0.0, 0.0),
            ),
        )


def test_trim_and_overlap_reject_nonrectangular_physical_elements() -> None:
    member = _member(SectionFamily.ROUND_TUBE)
    geometry = create_round_tube_geometry(
        cast(Any, member.section_topology),
        RoundTubeDimensions(2.0, 0.25),
    )
    tube = place_member(
        member,
        geometry,
        PositionVector3D(0.0, 0.0, 0.0),
        PositionVector3D(4.0, 0.0, 0.0),
        Vector3D(0.0, 0.0, 1.0),
    )
    plane = AuthoritativeCutPlane3D(
        "CUT",
        PositionVector3D(1.0, 0.0, 0.0),
        UnitVector3D(1.0, 0.0, 0.0),
    )

    with pytest.raises(ValueError, match="round-tube"):
        trim_placed_rectangular_component(tube, plane)
    with pytest.raises(ValueError, match="one rectangular prism"):
        placed_rectangular_elements_overlap(
            tube.physical_elements[0],
            _placed_plate().physical_elements[0],
        )


def test_rectangular_overlap_distinguishes_volume_contact_and_separation() -> None:
    first = _placed_plate(0.0, 4.0).physical_elements[0]
    overlap = _placed_plate(3.0, 7.0).physical_elements[0]
    contact = _placed_plate(4.0, 8.0).physical_elements[0]
    separated = _placed_plate(5.0, 9.0).physical_elements[0]

    assert placed_rectangular_elements_overlap(first, overlap)
    assert not placed_rectangular_elements_overlap(first, contact)
    assert not placed_rectangular_elements_overlap(first, separated)
