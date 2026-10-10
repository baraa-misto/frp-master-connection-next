"""Independent physical-boundary and hardware regressions for the F3 contract."""

from __future__ import annotations

import io
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import pytest
from pypdf import PdfReader
from tests.api.test_mat1_routes import call
from tests.application.test_direct_f1_edges import _row_context
from tests.direct_or2_fixtures import historical_support_ends, owner_body, owner_request

from frp_master_connection.api.calculation_mapping import map_single_bolt_preview_request
from frp_master_connection.api.multirow_mapping import map_multirow_request
from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO
from frp_master_connection.api.schemas import SingleBoltPreviewRequestDTO
from frp_master_connection.application import multirow_orchestration, preview_multirow_connection
from frp_master_connection.application.direct_engineering_geometry import (
    _boundary,
    _check,
    direct_engineering_geometry,
)
from frp_master_connection.application.direct_physical import (
    direct_bolt_containment_issues,
    direct_face_clearance_provenance,
)
from frp_master_connection.calculation import Unit
from frp_master_connection.domain import ComponentMaterialKind, PositionVector3D
from frp_master_connection.geometry.placement import (
    PlacedComponentGeometry3D,
    place_member_with_physical_length,
)
from frp_master_connection.geometry.spatial import UnitVector3D
from frp_master_connection.geometry.surfaces import (
    PlanarAnnularSurface3D,
    PlanarRectangularSurface3D,
    SurfaceExposure,
    SurfacePatch3D,
    SurfacePatchRole,
)
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner

PREVIEW = "/api/v1/calculations/multi-row/preview"
DESIGN = "/api/v1/frp-materials/multi-row/design-check"
OUTCOME_OK = "PASS"
OUTCOME_BAD = "FAIL"


def f3_request(case: str = "owner", *, si: bool = False) -> dict[str, Any]:
    request = owner_request(si=si)
    request["supporting_w_longitudinal_ends"] = historical_support_ends(si=si)
    scale = Decimal("25.4") if si else Decimal(1)
    template = request["physical_connection"]["geometry_template"]
    if case == "45":
        template["brace_to_column_directed_angle_deg"] = "45"
    elif case in {"free-edge", "edge-only"}:
        end = Decimal("4.77" if case == "free-edge" else "4.015")
        request["unloaded_end_e1"]["value"] = str(end * scale)
        template["bolt_to_brace_end_distance"]["value"] = str(end * scale)
    elif case == "patch-only":
        template["brace_to_column_directed_angle_deg"] = "105"
        request["bolts_per_row"] = 2
        request["physical_connection"]["joint_assembly"]["members"][1]["section"]["flange_width"][
            "value"
        ] = str(Decimal(10) * scale)
    elif case == "web":
        request["loaded_boundary_to_row_1_distance"]["value"] = str(Decimal(4) * scale)
    elif case == "heel":
        request["physical_connection"]["fastener_snapshot"]["washer_geometry"]["outside_diameter"][
            "value"
        ] = str(Decimal("3.6") * scale)
    return request


def preview(case: str = "owner", *, si: bool = False) -> dict[str, Any]:
    response = call("POST", PREVIEW, f3_request(case, si=si))
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


@pytest.mark.parametrize("si", [False, True])
def test_physical_end_equals_submitted_native_and_report_e1_without_moving_bolts(si: bool) -> None:
    payload = owner_request(si=si)
    scale = Decimal("25.4") if si else Decimal(1)
    original = map_single_bolt_preview_request(
        SingleBoltPreviewRequestDTO.model_validate(payload["physical_connection"])
    )
    request = map_multirow_request(MultiRowConnectionRequestDTO.model_validate(payload))
    corrected = request.physical_connection_request
    assert corrected is not None
    assert corrected.assembly == original.assembly
    assert (
        corrected.geometry_context.basis.joint_frame == original.geometry_context.basis.joint_frame
    )
    for old, new in zip(
        original.geometry_context.basis.placed_members,
        corrected.geometry_context.basis.placed_members,
        strict=True,
    ):
        assert old.global_frame == new.global_frame
        assert old.cross_section == new.cross_section
        assert old.section_offset == new.section_offset
    old_group = original.geometry_context.resolved_bolt_groups[0]
    new_group = corrected.geometry_context.resolved_bolt_groups[0]
    assert old_group.bolt_group_frame == new_group.bolt_group_frame
    assert old_group.master_centers == new_group.master_centers
    for old_path, new_path in zip(old_group.paths, new_group.paths, strict=True):
        assert old_path.definition == new_path.definition
        assert old_path.first_entry_point == new_path.first_entry_point
        assert old_path.last_exit_point == new_path.last_exit_point
        assert old_path.geometric_stack_span == new_path.geometric_stack_span
    assert corrected.geometry_context.basis.placed_members[0].extent.x_end == float(8 * scale)
    data = preview(si=si)
    assert data["geometry_status"] == "VALID"
    assert data["design_check_ready"]
    face = next(
        f
        for f in data["direct_engineering_geometry"]
        if f["component_id"] == "member-a" and f["bolt_id"] == "B_R1_L1"
    )
    end = next(c for c in face["checks"] if c["check_kind"] == "CHAPTER_8_END_DISTANCE")
    assert Decimal(end["actual_distance"]) == 3 * scale
    assert end["engineering_boundary_role"] == "PHYSICAL_LOADED_END"
    assert not end["contact_patch_boundary_used_as_engineering_edge"]
    assert (
        face["coordinate_canonicalization"] == "DIRECT_NATIVE_ROW_X_WITHIN_TEMPLATE_FRAME_PRECISION"
    )
    assert Decimal(data["visualization"]["loaded_boundary_to_row_1_distance"]["value"]) == 3 * scale
    assert len(data["direct_engineering_geometry"]) == 4
    assert data["visualization"]["physical_bolts"] is not None
    physical = data["visualization"]["physical_connection"]
    angle_frame = next(f["frame"] for f in physical["frames"] if f["id"] == "MEMBER_LOCAL:member-a")
    origin = [Decimal(angle_frame["origin"][axis]) for axis in ("x", "y", "z")]
    delta = [Decimal(v) - origin[i] for i, v in enumerate(face["bolt_center_global"])]
    transformed = [
        sum(delta[i] * Decimal(angle_frame[name][axis]) for i, axis in enumerate(("x", "y", "z")))
        for name in ("x_axis", "y_axis", "z_axis")
    ]
    assert [float(v) for v in face["raw_bolt_center_member_local"]] == pytest.approx(
        [float(v) for v in transformed], abs=float(Decimal("1e-9") * scale)
    )
    assert face["penetration_point_member_local"][2] != face["bolt_center_member_local"][2]


@pytest.mark.parametrize("angle", ["44.9", "45", "45.1", "134.9", "135", "135.1"])
def test_orientation_is_evaluated_from_physical_ends_not_angle_or_patch_identity(
    angle: str,
) -> None:
    payload = f3_request()
    payload["physical_connection"]["geometry_template"]["brace_to_column_directed_angle_deg"] = (
        angle
    )
    data = call("POST", PREVIEW, payload).json()
    expected = "INVALID_GEOMETRY" if Decimal(angle) < 90 else "VALID"
    assert data["geometry_status"] == expected
    face = next(
        f
        for f in data["direct_engineering_geometry"]
        if f["component_id"] == "member-b" and f["bolt_id"] == "B_R1_L1"
    )
    edges = [c for c in face["checks"] if c["check_kind"] == "CHAPTER_8_EDGE_DISTANCE"]
    assert all(c["pass_fail"] == OUTCOME_OK for c in edges)
    assert min(Decimal(c["actual_distance"]) for c in edges) > Decimal("1.33")
    end = next(c for c in face["checks"] if c["check_kind"] == "CHAPTER_8_END_DISTANCE")
    assert end["pass_fail"] == ("FAIL" if Decimal(angle) < 90 else "PASS")
    if Decimal(angle) < 90:
        assert Decimal(".08") < Decimal(end["actual_distance"]) < Decimal(".09")
        assert any(
            c["check_kind"] == "HOLE_PHYSICAL_CONTAINMENT" and c["pass_fail"] == OUTCOME_BAD
            for c in face["checks"]
        )
    else:
        assert all(c["pass_fail"] == OUTCOME_OK for c in face["checks"])


@pytest.mark.parametrize("si", [False, True])
@pytest.mark.parametrize("case", ["free-edge", "patch-only", "web", "heel"])
def test_distinguishes_physical_edges_computational_subfaces_and_obstructing_solids(
    case: str,
    si: bool,
) -> None:
    data = preview(case, si=si)
    checks = [c for f in data["direct_engineering_geometry"] for c in f["checks"]]
    edges = [c for c in checks if c["check_kind"] == "CHAPTER_8_EDGE_DISTANCE"]
    if case == "free-edge":
        failed = next(c for c in edges if c["pass_fail"] == OUTCOME_BAD)
        scale = Decimal("25.4") if si else Decimal(1)
        assert float(Decimal(failed["actual_distance"]) / scale) == pytest.approx(0.086047263146894)
        assert failed["engineering_boundary_role"] == "PHYSICAL_FREE_SIDE_EDGE"
    else:
        assert all(c["pass_fail"] == OUTCOME_OK for c in edges)
        if case == "patch-only":
            assert data["geometry_status"] == "VALID"
            assert any(not f["valid"] for f in data["direct_clearance_provenance"])
            assert all(c["pass_fail"] == OUTCOME_OK for c in checks)
        else:
            obstruction = "WEB" if case == "web" else "LEG_2"
            assert any(
                c["check_kind"] == "WASHER_SEATING"
                and c["pass_fail"] == OUTCOME_BAD
                and obstruction in c["source_geometry_id"]
                for c in checks
            )
            assert data["geometry_status"] == "INVALID_GEOMETRY"


@pytest.mark.parametrize("si", [False, True])
@pytest.mark.parametrize(
    ("offset", "expected"), [("-1e-9", "FAIL"), ("0", "PASS"), ("1e-9", "PASS")]
)
def test_exact_boundary_is_strict_at_the_governed_template_distance_precision(
    si: bool,
    offset: str,
    expected: str,
) -> None:
    response = preview_multirow_connection(
        map_multirow_request(MultiRowConnectionRequestDTO.model_validate(owner_request(si=si)))
    )
    visual = response.visualization
    assert visual is not None
    assert visual.physical_connection is not None
    physical = visual.physical_connection
    primitive = next(
        p
        for p in physical.primitives
        if p.owner_id == "member-b" and p.physical_element_id == "TOP_FLANGE"
    )
    frame = next(f.frame for f in physical.frames if f.id == primitive.frame_id)
    scale = Decimal("25.4") if si else Decimal(1)
    point = (5.0, float((Decimal(".75") + Decimal(offset)) * scale), 0.0)
    boundary = _boundary(
        primitive,
        frame,
        point,
        point,
        1,
        0.0,
        True,
        "PHYSICAL_FREE_SIDE_EDGE",
        "independent physical free edge",
        2,
    )
    check = _check(
        "CHAPTER_8_EDGE_DISTANCE",
        visual.physical_bolts[0].display,
        boundary,
        Decimal(".75") * scale,
        Unit.MM if si else Unit.IN,
        "audit-test",
        "ASCE/SEI 74-23 Table 8-1",
    )
    assert check.pass_fail == expected
    assert check.actual_distance == (Decimal(".75") + Decimal(offset)) * scale


@pytest.mark.parametrize("si", [False, True])
def test_washer_can_seat_while_chapter8_free_edge_still_fails(si: bool) -> None:
    data = preview("edge-only", si=si)
    checks = [c for face in data["direct_engineering_geometry"] for c in face["checks"]]
    scale = Decimal("25.4") if si else Decimal(1)
    failure = next(
        c
        for c in checks
        if c["check_kind"] == "CHAPTER_8_EDGE_DISTANCE" and c["pass_fail"] == OUTCOME_BAD
    )
    assert Decimal(".5") < Decimal(failure["actual_distance"]) / scale < Decimal(".75")
    assert all(
        c["pass_fail"] == OUTCOME_OK
        for c in checks
        if c["check_kind"]
        in {"WASHER_SEATING", "HOLE_PHYSICAL_CONTAINMENT", "COMPONENT_INTERFERENCE"}
    )


@pytest.mark.parametrize(("rows", "lines"), [(1, 1), (1, 2), (2, 1), (3, 1)])
def test_all_supported_direct_layouts_have_two_layer_physical_provenance(
    rows: int, lines: int
) -> None:
    payload = owner_request(one_row=rows == 1)
    payload["supporting_w_longitudinal_ends"] = historical_support_ends()
    payload["row_count"], payload["bolts_per_row"] = rows, lines
    data = call("POST", PREVIEW, payload).json()
    assert len(data["direct_engineering_geometry"]) == 2 * rows * lines
    for face in data["direct_engineering_geometry"]:
        assert face["associated_contact_patch_id"]
        assert {c["check_kind"] for c in face["checks"]} >= {
            "CHAPTER_8_EDGE_DISTANCE",
            "CHAPTER_8_END_DISTANCE",
            "HOLE_PHYSICAL_CONTAINMENT",
            "WASHER_SEATING",
        }


def test_presentation_extents_do_not_enter_physical_checks_or_demand() -> None:
    payload = owner_request()
    before = call("POST", PREVIEW, payload).json()
    payload["physical_connection"]["view_extents"] = {
        name: {"value": "30", "unit": "in"}
        for name in ("brace_view_length", "column_view_extent_above", "column_view_extent_below")
    }
    after = call("POST", PREVIEW, payload).json()
    assert before["direct_engineering_geometry"] == after["direct_engineering_geometry"]
    assert before["automatic_demand_result"] == after["automatic_demand_result"]


def test_computational_subdivision_at_point_086_cannot_create_an_engineering_edge() -> None:
    response = preview_multirow_connection(
        map_multirow_request(MultiRowConnectionRequestDTO.model_validate(owner_request()))
    )
    visual = response.visualization
    assert visual is not None
    physical = visual.physical_connection
    assert physical is not None
    bolt = visual.physical_bolts[0].display
    frame = next(
        f.frame
        for f in physical.frames
        if f.owner_id == "member-a" and f.kind.value == "MEMBER_LOCAL"
    )
    contact = frame.parent_to_local_point(bolt.holes[0].end)
    corners = tuple(
        frame.local_to_parent_point(PositionVector3D(x, y, contact.z))
        for x, y in (
            (contact.x - 0.086, contact.y - 1),
            (contact.x + 2, contact.y - 1),
            (contact.x + 2, contact.y + 1),
            (contact.x - 0.086, contact.y + 1),
        )
    )
    zone = physical.interface_zones[0]
    cropped = replace(
        zone,
        corners=corners,
        center=frame.local_to_parent_point(
            PositionVector3D(contact.x + 0.957, contact.y, contact.z)
        ),
    )
    changed = replace(physical, interface_zones=(cropped, *physical.interface_zones[1:]))
    native = {b.bolt_id: b.x for b in visual.bolts}
    before = direct_engineering_geometry(
        physical, (bolt,), row_count=2, force_global=(0, -1, -1), brace_local_x=native
    )
    after = direct_engineering_geometry(
        changed, (bolt,), row_count=2, force_global=(0, -1, -1), brace_local_x=native
    )
    assert before == after
    assert all(c.pass_fail == OUTCOME_OK for f in after for c in f.checks)
    witness = direct_face_clearance_provenance(changed, (bolt,))[0]
    assert witness.center_to_boundary == pytest.approx(0.086)
    assert not witness.valid
    assert direct_bolt_containment_issues(changed, (bolt,))
    assert all(
        b.computational_only and not b.engineering_edge_authority for b in witness.boundaries
    )
    expanded = replace(
        physical,
        interface_zones=tuple(
            replace(
                z,
                corners=tuple(
                    PositionVector3D(
                        z.center.x + 10 * (p.x - z.center.x),
                        z.center.y + 10 * (p.y - z.center.y),
                        z.center.z + 10 * (p.z - z.center.z),
                    )
                    for p in z.corners
                ),
            )
            for z in physical.interface_zones
        ),
    )
    assert direct_bolt_containment_issues(expanded, (bolt,)) == ()
    assert (
        direct_engineering_geometry(
            expanded, (bolt,), row_count=2, force_global=(0, -1, -1), brace_local_x=native
        )
        == before
    )


def test_physical_end_selection_requires_an_authoritative_force_direction() -> None:
    request, resolved, _ = _row_context()
    missing = replace(
        resolved, visualization=replace(resolved.visualization, connection_demand=None)
    )
    with pytest.raises(ValueError, match="DIRECT_PHYSICAL_FORCE_DIRECTION_REQUIRED"):
        multirow_orchestration._preview_from_resolved(request, missing, None)


def test_physical_member_extent_builder_rejects_nonmember_authority() -> None:
    invalid = cast(PlacedComponentGeometry3D, SimpleNamespace(component=object()))
    with pytest.raises(ValueError, match="requires a placed member"):
        place_member_with_physical_length(invalid, 8)


def test_direct_end_reconciliation_rejects_an_unresolved_face_kind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import frp_master_connection.api.calculation_mapping as mapping

    original = mapping._surface

    def altered(
        surfaces: tuple[SurfacePatch3D, ...],
        participant_id: str,
        physical_element_id: str,
        patch_id: str,
        role: object,
    ) -> SurfacePatch3D:
        patch = original(surfaces, participant_id, physical_element_id, patch_id, role)
        if patch.participant.entity_id == "member-a":
            assert isinstance(patch.geometry, PlanarRectangularSurface3D)
            return replace(
                patch,
                exposure=SurfaceExposure.END_CUT,
                role=SurfacePatchRole.ANNULAR_END_FACE,
                geometry=PlanarAnnularSurface3D(patch.geometry.frame, 4, 1),
            )
        return patch

    monkeypatch.setattr(mapping, "_surface", altered)
    dto = SingleBoltPreviewRequestDTO.model_validate(owner_request()["physical_connection"])
    with pytest.raises(ValueError, match="requires a rectangular face"):
        map_single_bolt_preview_request(dto, direct_brace_physical_length=8)


@pytest.mark.parametrize(
    "defect", ["holes", "member", "steel", "solid", "normal", "row", "plane", "zone", "washer"]
)
def test_incomplete_or_inconsistent_physical_evidence_cannot_become_valid(defect: str) -> None:
    response = preview_multirow_connection(
        map_multirow_request(MultiRowConnectionRequestDTO.model_validate(owner_request()))
    )
    visual = response.visualization
    assert visual is not None
    physical = visual.physical_connection
    assert physical is not None
    bolt = visual.physical_bolts[0].display
    native = {b.bolt_id: b.x for b in visual.bolts}
    if defect == "holes":
        bolt = replace(bolt, holes=())
    elif defect == "member":
        physical = replace(physical, components=())
    elif defect == "steel":
        physical = replace(
            physical,
            components=tuple(
                replace(m, material_kind=ComponentMaterialKind.STEEL) for m in physical.components
            ),
        )
    elif defect == "solid":
        physical = replace(physical, primitives=())
    elif defect == "normal":
        bolt = replace(bolt, axis=UnitVector3D(0, 1, 0))
    elif defect == "row":
        native[bolt.bolt_location_id] += 1
    elif defect == "plane":

        def shifted(p: PositionVector3D) -> PositionVector3D:
            return PositionVector3D(p.x + 1, p.y, p.z)

        bolt = replace(
            bolt,
            holes=tuple(replace(h, start=shifted(h.start), end=shifted(h.end)) for h in bolt.holes),
        )
    elif defect == "zone":
        physical = replace(physical, interface_zones=())
    else:
        bolt = replace(bolt, washers=())
    with pytest.raises(ValueError, match="Direct"):
        direct_engineering_geometry(
            physical, (bolt,), row_count=2, force_global=(0, -1, -1), brace_local_x=native
        )


@pytest.mark.parametrize("case", ["owner", "45", "free-edge", "patch-only", "web", "heel"])
def test_report_reads_one_snapshot_and_preserves_exhaustive_evidence(case: str) -> None:
    body = owner_body()
    body["legacy_request"] = f3_request(case)
    result = call("POST", DESIGN, body).json()
    signer = SnapshotSigner(b"DIRECT-F3-REPORT-ONLY-SIGNER-32-BYTES")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row", kind="design", request=body, result=result, account_id="f3"
        ),
        account_id="f3",
    )
    original = deepcopy((snapshot.request, snapshot.result))
    pdf = render_report_pdf(snapshot, ReportOptions(mode="ENGINEER_REPORT"))
    reader = PdfReader(io.BytesIO(pdf))
    text = " ".join(" ".join(p.extract_text() or "" for p in reader.pages).split())
    assert "physical member ends and free side edges" in text
    assert "NOT AN ENGINEERING EDGE UNLESS MAPPED" in text
    assert len(reader.pages) <= 10
    if case in {"web", "heel"}:
        assert "Washer seating / hardware clearance" in text
    if case == "45":
        assert "Chapter 8 loaded-end distance" in text
        assert "0.085786" in text
    if case == "free-edge":
        assert "Chapter 8 physical free-edge distance" in text
    assert (snapshot.request, snapshot.result) == original


@pytest.mark.parametrize("legacy", [False, True])
def test_report_handles_historical_or_incomplete_geometry_metadata_without_inventing_checks(
    legacy: bool,
) -> None:
    body = owner_body()
    body["legacy_request"] = f3_request("free-edge")
    result = call("POST", DESIGN, body).json()
    physical_preview = result["native_design"]["preview"]
    if legacy:
        physical_preview.pop("direct_engineering_geometry")
        physical_preview["direct_clearance_provenance"].extend([None, {"valid": True}])
    else:
        physical_preview["direct_engineering_geometry"] = [None, {"checks": [None]}]
    signer = SnapshotSigner(b"DIRECT-F3-HISTORICAL-REPORT-KEY-32")
    snapshot = signer.verify(
        signer.issue(
            family="multi-row", kind="design", request=body, result=result, account_id="f3"
        ),
        account_id="f3",
    )
    original = deepcopy((snapshot.request, snapshot.result))
    reader = PdfReader(io.BytesIO(render_report_pdf(snapshot, ReportOptions())))
    text = " ".join(p.extract_text() or "" for p in reader.pages)
    if legacy:
        assert "canonical contact-patch boundary" in text
        assert "not automatically a physical free member" in text
    else:
        assert "physical member ends and free side edges" in text
        assert "Physical engineering geometry checks" not in text
    assert (snapshot.request, snapshot.result) == original

    if legacy:
        owner = owner_body()
        owner_result = call("POST", DESIGN, owner).json()
        owner_preview = owner_result["native_design"]["preview"]
        owner_preview.pop("direct_engineering_geometry")
        assert all(w["valid"] for w in owner_preview["direct_clearance_provenance"])
        historical_owner = signer.verify(
            signer.issue(
                family="multi-row",
                kind="design",
                request=owner,
                result=owner_result,
                account_id="f3",
            ),
            account_id="f3",
        )
        unchanged = deepcopy((historical_owner.request, historical_owner.result))
        owner_pdf = render_report_pdf(historical_owner, ReportOptions())
        owner_text = " ".join(
            p.extract_text() or "" for p in PdfReader(io.BytesIO(owner_pdf)).pages
        )
        assert "Geometry issue — canonical contact-patch boundary" not in owner_text
        assert (historical_owner.request, historical_owner.result) == unchanged
