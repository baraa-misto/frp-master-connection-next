"""Controlled Stage 3.5A domain, orchestration, golden, and boundary tests."""

from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest

import frp_master_connection.application.beam_concrete_paired_angle_orchestration as module
from frp_master_connection.application import (
    design_check_beam_concrete_paired_angle,
    preview_beam_concrete_paired_angle,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.domain import (
    ConcreteWallFrame,
    ConcreteWallGeometry,
    ExternalAnchorTrace,
    MemberRole,
    WallAnchorGroupIdentity,
    WallAnchorPattern,
    WallEdgeDistances,
    WallQuantityVector,
    WallWrench,
)
from tests.beam_concrete_paired_angle_fixtures import (
    build_beam_concrete_paired_angle_request,
)

_ROOT = Path(__file__).parents[3]
_ARTIFACTS = (
    (
        _ROOT
        / "docs/governance/STAGE_3_5A_BEAM_TO_CONCRETE_PAIRED_CLIP_ANGLE_SELECTION_DECISION.md",
        "2288823909D7C5057C3627232665DAE8E41AB906AE03E38BD55055EEA8B87614",
        b"**END OF STAGE 3.5A BEAM-TO-CONCRETE PAIRED CLIP-ANGLE SELECTION DECISION**",
    ),
    (
        _ROOT
        / "docs/engineering"
        / "STAGE_3_5A_BEAM_TO_CONCRETE_PAIRED_CLIP_ANGLE_ENGINEERING_SPECIFICATION_RC1.md",
        "E3D5F1F80149A5D9EA610FBE9DEC6B261B34A0C943D3F9EA134764C4F8BAEA9B",
        b"**END OF CONTROLLED ENGINEERING SPECIFICATION \xe2\x80\x94 RC1**",
    ),
    (
        _ROOT
        / "backend/tests/golden"
        / "stage_3_5a_beam_to_concrete_paired_clip_angle_golden_benchmarks_rc1.json",
        "B68F6323453497B90469D437BF1A8707EAB2808B4561B30256A1EE67FF6389BD",
        None,
    ),
    (
        _ROOT / "docs/qa/STAGE_3_5A_BEAM_TO_CONCRETE_PAIRED_CLIP_ANGLE_AUTHORITY_LEDGER_RC1.md",
        "ED5735BA0A17221C5B7A1650B653A38E8AD8A1AFEC8797C4EF05CBD8F16C9534",
        b"**END OF AUTHORITY LEDGER RC1**",
    ),
)


def _values(vector: WallQuantityVector, unit: Unit) -> tuple[Decimal, Decimal, Decimal]:
    return tuple(item.to(unit).magnitude for item in (vector.h, vector.v, vector.n))  # type: ignore[return-value]


def _per_bolt_kip(group: object) -> tuple[Decimal, ...]:
    demand = group.demand  # type: ignore[attr-defined]
    return tuple(
        item.total_force_magnitude.to(Unit.KIP).magnitude for item in demand.scenarios[0].per_bolt
    )


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_all_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_all_keys(item) for item in value), set())
    return set()


def test_controlled_artifacts_and_g1_through_g24_are_exact() -> None:
    for path, expected, sentinel in _ARTIFACTS:
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest().upper() == expected
        if sentinel is not None:
            assert raw.rstrip().endswith(sentinel)
    golden = json.loads(_ARTIFACTS[2][0].read_text(encoding="utf-8"))
    assert [item["id"].split("_", 1)[0] for item in golden["benchmarks"]] == [
        f"G{i}" for i in range(1, 25)
    ]


def test_wall_domain_is_immutable_and_frame_is_exact_right_handed() -> None:
    frame = ConcreteWallFrame()
    assert frame.h_axis == (Decimal(1), Decimal(0), Decimal(0))
    assert frame.v_axis == (Decimal(0), Decimal(1), Decimal(0))
    assert frame.n_axis == (Decimal(0), Decimal(0), Decimal(1))
    with pytest.raises(FrozenInstanceError):
        frame.handedness = "invalid"  # type: ignore[misc]
    with pytest.raises(ValueError, match="right-handed"):
        ConcreteWallFrame(n_axis=(Decimal(0), Decimal(0), Decimal(-1)))
    with pytest.raises(ValueError, match="greater than zero"):
        ConcreteWallGeometry(Decimal(0), Decimal(48), Decimal(8), Decimal(0), Decimal(0))


def test_wall_domain_rejects_every_invalid_contract_branch() -> None:
    with pytest.raises(TypeError, match="Decimal"):
        ConcreteWallGeometry(1, Decimal(48), Decimal(8), Decimal(0), Decimal(0))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite"):
        ConcreteWallGeometry(Decimal("NaN"), Decimal(48), Decimal(8), Decimal(0), Decimal(0))
    with pytest.raises(ValueError, match="positive non-Boolean"):
        WallAnchorPattern(True, 2, Decimal(2), Decimal(2), Decimal(3))

    request = build_beam_concrete_paired_angle_request()
    anchor = request.external_anchor
    with pytest.raises(ValueError, match="positive lengths"):
        replace(anchor, nominal_diameter=PhysicalQuantity.of(Decimal(1), Unit.KIP))
    with pytest.raises(ValueError, match="smaller"):
        replace(anchor, hole_diameter=PhysicalQuantity.of(Decimal("0.25"), Unit.IN))
    with pytest.raises(ValueError, match="wider"):
        replace(anchor, washer_outside_diameter=PhysicalQuantity.of(Decimal("0.5"), Unit.IN))
    with pytest.raises(ValueError, match="classification"):
        replace(anchor, system_classification="UNCONTROLLED")

    length = PhysicalQuantity.of(Decimal(0), Unit.IN)
    force = PhysicalQuantity.of(Decimal(0), Unit.KIP)
    moment = PhysicalQuantity.of(Decimal(0), Unit.KIP_IN)
    length_vector = WallQuantityVector(length, length, length)
    force_vector = WallQuantityVector(force, force, force)
    moment_vector = WallQuantityVector(moment, moment, moment)
    with pytest.raises(ValueError, match="share one"):
        WallQuantityVector(length, force, length)
    with pytest.raises(ValueError, match="reference"):
        WallWrench(force_vector, force_vector, moment_vector, "source")
    with pytest.raises(ValueError, match="force"):
        WallWrench(length_vector, length_vector, moment_vector, "source")
    with pytest.raises(ValueError, match="moment"):
        WallWrench(length_vector, force_vector, force_vector, "source")
    with pytest.raises(ValueError, match="provenance"):
        WallWrench(length_vector, force_vector, moment_vector, " ")

    preview = preview_beam_concrete_paired_angle(request)
    trace = preview.positive_wall_group.anchors[0]
    with pytest.raises(ValueError, match="ID"):
        replace(trace, anchor_id=" ")
    with pytest.raises(ValueError, match="coordinates"):
        replace(trace, coordinate_hvn=force_vector)
    with pytest.raises(ValueError, match="far-side"):
        replace(trace, hardware_configuration="FAR_SIDE_NUT")
    assert isinstance(trace, ExternalAnchorTrace)
    assert isinstance(trace.wall_edge_distances, WallEdgeDistances)
    assert trace.group_id is WallAnchorGroupIdentity.POSITIVE_WALL_ANCHOR_GROUP


def test_request_contract_rejects_every_unauthorized_input_branch() -> None:
    request = build_beam_concrete_paired_angle_request()
    length = PhysicalQuantity.of(Decimal(1), Unit.IN)
    force = PhysicalQuantity.of(Decimal(1), Unit.KIP)
    length_vector = WallQuantityVector(length, length, length)
    cases: tuple[tuple[Callable[[], object], str], ...] = (
        (lambda: replace(request, request_id=" "), "request_id"),
        (lambda: replace(request, contract_version="other"), "contract version"),
        (lambda: replace(request, source_length_unit=Unit.MM), "Source length unit"),
        (
            lambda: replace(
                request, beam_profile=replace(request.beam_profile, role=MemberRole.BRACE)
            ),
            "W/I",
        ),
        (lambda: replace(request, connector_length_anchor_position=force), "Connector position"),
        (lambda: replace(request, reaction_shear=length), "Reaction shear"),
        (lambda: replace(request, user_force_hvn=length_vector), "User force"),
        (lambda: replace(request, user_moment_hvn=length_vector), "User moment"),
        (lambda: replace(request, common_bolt_diameter=force), "bolt diameter"),
        (
            lambda: replace(
                request,
                common_hole_diameter=PhysicalQuantity.of(Decimal("0.25"), Unit.IN),
            ),
            "smaller",
        ),
        (lambda: replace(request, connector_material_source="other"), "FRP material"),
        (lambda: replace(request, common_fastener_source="other"), "F593"),
        (lambda: replace(request, anchor_design_authority="other"), "external"),
    )
    for factory, message in cases:
        with pytest.raises(ValueError, match=message):
            factory()


def test_g1_through_g6_exact_default_demands_and_wall_wrenches() -> None:
    preview = preview_beam_concrete_paired_angle(build_beam_concrete_paired_angle_request())
    assert preview.positive_wall_group.wrench is not None
    assert preview.negative_wall_group.wrench is not None
    assert preview.geometry_status.value == "VALID"
    assert preview.symmetry_proof.equal_sharing_eligible is True
    assert len(preview.common_beam_group.placement.bolts) == 4
    assert _per_bolt_kip(preview.common_beam_group) == (Decimal(1),) * 4
    assert _values(preview.positive_wall_group.wrench.reference_hvn, Unit.IN) == (
        Decimal(3),
        Decimal(0),
        Decimal(0),
    )
    assert _values(preview.positive_wall_group.wrench.force_hvn, Unit.KIP) == (
        Decimal(0),
        Decimal(-2),
        Decimal(0),
    )
    assert _values(preview.positive_wall_group.wrench.moment_hvn, Unit.KIP_IN) == (
        Decimal(8),
        Decimal(0),
        Decimal(6),
    )
    assert _values(preview.negative_wall_group.wrench.reference_hvn, Unit.IN) == (
        Decimal(-3),
        Decimal(0),
        Decimal(0),
    )
    assert _values(preview.negative_wall_group.wrench.moment_hvn, Unit.KIP_IN) == (
        Decimal(8),
        Decimal(0),
        Decimal(-6),
    )
    assert _values(preview.combined_wall_wrench.force_hvn, Unit.KIP) == (
        Decimal(0),
        Decimal(-4),
        Decimal(0),
    )
    assert _values(preview.combined_wall_wrench.moment_hvn, Unit.KIP_IN) == (
        Decimal(16),
        Decimal(0),
        Decimal(0),
    )
    assert preview.positive_wall_group.force_equilibrium
    assert preview.negative_wall_group.moment_equilibrium


def test_g9_g12_g18_g23_geometry_handoff_and_material_coverage() -> None:
    preview = preview_beam_concrete_paired_angle(build_beam_concrete_paired_angle_request())
    positive = tuple(
        (_values(item.coordinate_hvn, Unit.IN)[0], _values(item.coordinate_hvn, Unit.IN)[1])
        for item in preview.positive_wall_group.anchors
    )
    negative = tuple(
        (_values(item.coordinate_hvn, Unit.IN)[0], _values(item.coordinate_hvn, Unit.IN)[1])
        for item in preview.negative_wall_group.anchors
    )
    assert positive == (
        (Decimal(2), Decimal(-1)),
        (Decimal(4), Decimal(-1)),
        (Decimal(2), Decimal(1)),
        (Decimal(4), Decimal(1)),
    )
    assert negative == (
        (Decimal(-4), Decimal(-1)),
        (Decimal(-2), Decimal(-1)),
        (Decimal(-4), Decimal(1)),
        (Decimal(-2), Decimal(1)),
    )
    assert (
        preview.positive_wall_group.demand_label
        == "COORDINATION / FRP-SIDE DEMAND — EXTERNAL ANCHOR SOFTWARE GOVERNS"
    )
    assert preview.external_anchor_handoff.schema_version == "3.5A-RC1"
    assert preview.external_anchor_handoff.demand_method_versions == (
        "2.5A-RC1",
        "2.5B-RC1",
        "2.6A-RC1",
        "3.3B-RC1",
        "3.5A-RC1",
    )
    assert (
        json.dumps(
            json.loads(preview.external_anchor_handoff_json),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        == preview.external_anchor_handoff_json
    )
    assert preview.visualization is not None
    assert len(preview.visualization.material_regions) == 4
    assert len(preview.visualization.beam_material_regions) == 3
    assert all(item.owner_id != "concrete-wall" for item in preview.visualization.meshes)


def test_g11_common_two_by_one_retains_wall_handoff() -> None:
    request = build_beam_concrete_paired_angle_request()
    layout = replace(
        request.common_beam_layout,
        bolts_per_row=1,
        gauge=Decimal(1),
        heel_edge_distance=Decimal(2),
        free_edge_distance=Decimal(2),
    )
    preview = preview_beam_concrete_paired_angle(replace(request, common_beam_layout=layout))
    assert len(preview.common_beam_group.placement.bolts) == 2
    assert _per_bolt_kip(preview.common_beam_group) == (Decimal(2), Decimal(2))
    assert _values(preview.combined_wall_wrench.moment_hvn, Unit.KIP_IN) == (
        Decimal(16),
        Decimal(0),
        Decimal(0),
    )


def test_g13_g14_g16_wall_and_hole_geometry_fail_closed() -> None:
    request = build_beam_concrete_paired_angle_request()
    outside = preview_beam_concrete_paired_angle(
        replace(request, wall=replace(request.wall, width=Decimal(6)))
    )
    assert outside.geometry_status.value == "INVALID_GEOMETRY"
    assert any(
        reason.startswith("ANCHOR_CENTER_OUTSIDE_FINITE_WALL")
        for reason in outside.geometry_invalid_reasons
    )
    embedment = preview_beam_concrete_paired_angle(
        replace(
            request,
            external_anchor=replace(
                request.external_anchor,
                specified_embedment=PhysicalQuantity.of(Decimal(9), Unit.IN),
            ),
        )
    )
    assert "ANCHOR_EMBEDMENT_EXCEEDS_WALL_THICKNESS" in embedment.geometry_invalid_reasons
    pattern = replace(request.wall_anchor_pattern, gauge=Decimal("3.75"))
    holes = preview_beam_concrete_paired_angle(replace(request, wall_anchor_pattern=pattern))
    assert holes.geometry_status.value == "INVALID_GEOMETRY"
    assert any("COMPLETE_HOLE_CONTAINMENT" in reason for reason in holes.geometry_invalid_reasons)
    common_hole = preview_beam_concrete_paired_angle(
        replace(request, common_hole_diameter=PhysicalQuantity.of(Decimal(8), Unit.IN))
    )
    assert "PAIRED_BEAM_CONNECTOR_GEOMETRY_INVALID" in common_hole.geometry_invalid_reasons
    overlap = preview_beam_concrete_paired_angle(
        replace(
            request,
            wall_anchor_pattern=replace(request.wall_anchor_pattern, centroid_offset_h=Decimal(1)),
        )
    )
    assert "DUPLICATE_OR_OVERLAPPING_WALL_ANCHOR_AXES" in overlap.geometry_invalid_reasons
    assert module._export_value({"b": Decimal(2), "a": Decimal(1)}) == {
        "a": "1",
        "b": "2",
    }


def test_g17_no_anchor_or_concrete_capacity_and_no_ordinary_pass() -> None:
    preview = preview_beam_concrete_paired_angle(build_beam_concrete_paired_angle_request())
    keys = {item.lower() for item in _all_keys(json.loads(preview.external_anchor_handoff_json))}
    assert not (
        {
            "anchor_steel_capacity",
            "concrete_breakout_capacity",
            "pullout_capacity",
            "pryout_capacity",
            "concrete_member_capacity",
            "utilization",
        }
        & keys
    )
    assert preview.ordinary_pass_allowed is False
    assert preview.external_design_required is True
    assert dict(preview.limitations)["CONCRETE_SUBSTRATE_RESISTANCE"] == "EXTERNAL_DESIGN_REQUIRED"


def test_g19_g20_failure_precedence_and_external_limitations() -> None:
    default = design_check_beam_concrete_paired_angle(build_beam_concrete_paired_angle_request())
    assert default.assembly_status.value == "FAIL"
    assert default.supported_beam_side_failure_present is True
    low = build_beam_concrete_paired_angle_request()
    low_force = PhysicalQuantity.of(Decimal("-0.1"), Unit.KIP)
    low = replace(
        low, reaction_shear=low_force, user_force_hvn=replace(low.user_force_hvn, v=low_force)
    )
    result = design_check_beam_concrete_paired_angle(low)
    assert result.assembly_status.value == "NOT_EVALUATED"
    assert result.ordinary_pass_allowed is False
    assert result.preview.external_design_required is True


def test_g21_preview_never_calls_resistance_and_design_calls_supported_seam_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wrapped = Mock(wraps=module._with_common_resistance)  # type: ignore[attr-defined]
    monkeypatch.setattr(module, "_with_common_resistance", wrapped)
    request = build_beam_concrete_paired_angle_request()
    preview = preview_beam_concrete_paired_angle(request)
    assert wrapped.call_count == 0
    assert preview.resistance_evaluated is False
    design_check_beam_concrete_paired_angle(request)
    assert wrapped.call_count == 1


def test_g22_us_si_equivalence_and_deterministic_fingerprints() -> None:
    us = preview_beam_concrete_paired_angle(build_beam_concrete_paired_angle_request())
    si = preview_beam_concrete_paired_angle(
        build_beam_concrete_paired_angle_request(unit_system="SI")
    )
    assert us.canonical_input_fingerprint == si.canonical_input_fingerprint
    assert us.wall_geometry_fingerprint == si.wall_geometry_fingerprint
    assert us.beam_geometry_fingerprint == si.beam_geometry_fingerprint
    assert us.paired_connector_geometry_fingerprint == si.paired_connector_geometry_fingerprint
    assert us.combined_wall_handoff_fingerprint == si.combined_wall_handoff_fingerprint
    assert (
        us.external_anchor_handoff.handoff_fingerprint
        == si.external_anchor_handoff.handoff_fingerprint
    )
    assert us.application_fingerprint == si.application_fingerprint
    assert us.engineering_fingerprint == si.engineering_fingerprint


def test_production_never_reads_golden_fixture() -> None:
    source = inspect.getsource(module).lower()
    assert "tests/golden" not in source
    assert "stage_3_5a_beam_to_concrete_paired_clip_angle_golden" not in source
