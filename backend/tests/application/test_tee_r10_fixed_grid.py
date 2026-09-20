"""Controlled Stage 3.2-R10 fixed-grid and group-positioning regressions."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from frp_master_connection.api.tee_mapping import map_tee_connector_request
from frp_master_connection.api.tee_schemas import TeeConnectorRequestDTO
from frp_master_connection.application import (
    TeeAssemblyStatus,
    TeeConnectorOrchestrationRequest,
    TeeFixedGridCompatibilityStatus,
    design_check_tee_connector,
    preview_multirow_connection,
    preview_tee_connector,
    resolve_tee_connector_request,
)
from frp_master_connection.application import tee_orchestration as tee_module
from frp_master_connection.calculation import (
    GeometryStatus,
    PhysicalQuantity,
    PlanAvailability,
    Unit,
)
from frp_master_connection.domain import TeeBoltPlacementMode
from frp_master_connection.geometry import PlanarRectangularSurface3D
from tests.tee_fixtures import build_tee_r7_angle_payload

_GOLDEN_PATH = (
    Path(__file__).parents[1]
    / "golden"
    / "stage_3_2_r10_fixed_bolt_frame_positioning_golden_benchmarks_rc1.json"
)
_GOLDEN_SHA256 = "9F9F628082EF39F5851146973D1695F99E6F1C2AA627CD54693FDCC4FC8653DF"
_HISTORICAL_BEFORE_COMMIT = "cc336f6a7161200656f1f4689c8b72585e6627d1"
_CONTROLLED_AFTER_COMMIT = "a447ff8f384914b9c466ebd4241f3b195188926a"
_NONZERO_FINGERPRINT_TRANSITIONS = (
    (
        "30",
        (
            "27e7e4e56568920dfd439ea0445ba30ca2feb282cee26f2d81a00308e5cff63f",
            "c72b1443f4f435a33f3d74bb61587bba02b4ece57bab5ff9056e64d7be58ae48",
            "e4d3767be331318ffbc13b4a08326f2dc6a6d0b1be7103cb26dfa3d89aac64e3",
        ),
        (
            "b37cc2f170eaaa8ae1902e71c0bfdd4665a3d549924d8dac31b24a56a5e8f983",
            "51dc8986c6d4a0e8e4eb8efa19bb45999c2e6637082c9469c9d2cca9e956a7b2",
            "e4d3767be331318ffbc13b4a08326f2dc6a6d0b1be7103cb26dfa3d89aac64e3",
        ),
    ),
    (
        "-30",
        (
            "d33228e754761382a058e585cd68db7e686f007a792fbe221b5d6cd3ee23d339",
            "b13ce5e44e6c227af0181b613fc1cbf2895d98287280706e391d7cd65ae65b88",
            "e4d3767be331318ffbc13b4a08326f2dc6a6d0b1be7103cb26dfa3d89aac64e3",
        ),
        (
            "20b2f9deb4c2107598808e01875cb8bf22bc8c4fb8984a813484bedfe9ee8662",
            "56f493c23e059a0a9c5fffe6d375b80c0087d28e66088071c54f20c8045c862a",
            "e4d3767be331318ffbc13b4a08326f2dc6a6d0b1be7103cb26dfa3d89aac64e3",
        ),
    ),
    (
        "27.5",
        (
            "bb6c2503695b1cc8060d8e166f46c353ab4895ee6a60b60e0713bfe5d9d4406e",
            "e7f44c3dd9036a91d5f30867b8346eef06add4c861538f04bb569ac9664b04a6",
            "e4d3767be331318ffbc13b4a08326f2dc6a6d0b1be7103cb26dfa3d89aac64e3",
        ),
        (
            "af6e93d98dbc82da2e55e38335d1792ba915f116592895e94fc84a1923e327af",
            "c707293db29f5f42d6bd3c00bd02464b37501a17dfd959faa44bbb947c79e618",
            "e4d3767be331318ffbc13b4a08326f2dc6a6d0b1be7103cb26dfa3d89aac64e3",
        ),
    ),
)


def _request(payload: dict[str, Any]) -> TeeConnectorOrchestrationRequest:
    return map_tee_connector_request(TeeConnectorRequestDTO.model_validate(payload))


def _fixed_grid_payload(angle: str = "0") -> dict[str, Any]:
    payload = build_tee_r7_angle_payload(unloaded_end_distance="6")
    payload["brace_inclination_degrees"] = angle
    payload["interface_a_layout"]["bolts_per_row"] = 1
    payload["connector_dimensions"]["connector_length"]["value"] = "16"
    payload["connected_member_profile"]["dimensions"].update(
        {
            "leg_y": {"value": "12", "unit": "in"},
            "leg_z": {"value": "12", "unit": "in"},
            "member_length": {"value": "20", "unit": "in"},
        }
    )
    return payload


def _offset(
    payload: dict[str, Any],
    interface: str,
    vertical: str,
    horizontal: str,
) -> dict[str, Any]:
    changed = deepcopy(payload)
    layout = changed[interface]
    layout["placement_mode"] = "GROUP_OFFSET_CONTROLLED"
    layout["vertical_offset"] = {"value": vertical, "unit": "in"}
    layout["horizontal_offset"] = {"value": horizontal, "unit": "in"}
    return changed


def test_r10_owner_golden_is_byte_exact_and_complete() -> None:
    raw = _GOLDEN_PATH.read_bytes()
    fixture = json.loads(raw)

    assert hashlib.sha256(raw).hexdigest().upper() == _GOLDEN_SHA256
    assert fixture["version"] == "RC1"
    assert [item["id"] for item in fixture["benchmarks"]] == [
        f"R10_G{index}_{suffix}"
        for index, suffix in enumerate(
            (
                "ZERO_INCLINATION_LEGACY_COMPATIBILITY",
                "POSITIVE_30_FIXED_GRID",
                "NEGATIVE_30_FIXED_GRID",
                "ARBITRARY_27_5_FIXED_GRID",
                "INTERFACE_A_GROUP_OFFSET_TRANSLATION",
                "INTERFACE_B_GROUP_OFFSET_INDEPENDENCE",
                "CONTROLLED_ANGLE_CLEARANCE_LIMIT",
                "LEGACY_OFFSET_PHYSICAL_EQUIVALENCE",
                "FIXED_GRID_METHOD_APPLICABILITY_FAIL_CLOSED",
                "INDEPENDENT_COUNTS_AND_POSITION",
                "R9_HARDWARE_PERSISTENCE",
            ),
            start=1,
        )
    ]


def test_r10_g1_zero_inclination_preserves_exact_r9_fingerprints() -> None:
    payload = build_tee_r7_angle_payload()
    payload["interface_a_layout"]["bolts_per_row"] = 1
    preview = preview_tee_connector(_request(payload))

    assert preview.engineering_fingerprint == (
        "34744f607b889e09a54f4975165d3f8b82c52be009a072f29de4d2db27a72b04"
    )
    assert preview.interface_a.interface_fingerprint == (
        "54b2f9ecfcc54106ee07f03b7e57da93e2d287a5d7f13267332e385f5fae8ef8"
    )
    assert preview.interface_b.interface_fingerprint == (
        "dc2a33aaf8459c450912610d4ae8a7c25e38046c4ca45d75952d77a3cfbfe4fd"
    )


@pytest.mark.parametrize(
    ("angle", "historical_before", "controlled_after"),
    _NONZERO_FINGERPRINT_TRANSITIONS,
)
def test_r10_nonzero_fingerprint_transitions_are_exact(
    angle: str,
    historical_before: tuple[str, str, str],
    controlled_after: tuple[str, str, str],
) -> None:
    """Lock the read-only R9 provenance and executable immutable R10 results."""

    assert _HISTORICAL_BEFORE_COMMIT == "cc336f6a7161200656f1f4689c8b72585e6627d1"
    assert _CONTROLLED_AFTER_COMMIT == "a447ff8f384914b9c466ebd4241f3b195188926a"
    for fingerprint in (*historical_before, *controlled_after):
        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64
        assert fingerprint == fingerprint.lower()
        assert set(fingerprint) <= set("0123456789abcdef")
        assert "…" not in fingerprint
        assert "..." not in fingerprint

    preview = preview_tee_connector(_request(_fixed_grid_payload(angle)))
    current = (
        preview.engineering_fingerprint,
        preview.interface_a.interface_fingerprint,
        preview.interface_b.interface_fingerprint,
    )

    assert current == controlled_after
    assert historical_before[0] != controlled_after[0]
    assert historical_before[1] != controlled_after[1]
    assert historical_before[2] == controlled_after[2]


@pytest.mark.parametrize("angle", ["30", "-30", "27.5"])
def test_r10_g2_g3_g4_brace_rotates_but_bolt_groups_stay_fixed(angle: str) -> None:
    zero = preview_tee_connector(_request(_fixed_grid_payload()))
    inclined = preview_tee_connector(_request(_fixed_grid_payload(angle)))

    assert zero.visualization is not None
    assert inclined.visualization is not None
    assert inclined.visualization.interface_a_bolts == zero.visualization.interface_a_bolts
    assert inclined.visualization.interface_b_bolts == zero.visualization.interface_b_bolts
    assert inclined.interface_a.placement.bolt_centers_hvn == (
        zero.interface_a.placement.bolt_centers_hvn
    )
    assert inclined.interface_a.placement.vertical_axis == (
        zero.interface_a.placement.vertical_axis
    )
    assert inclined.interface_a.placement.horizontal_axis == (
        zero.interface_a.placement.horizontal_axis
    )
    assert inclined.connected_member_profile.brace_placement_frame != (
        zero.connected_member_profile.brace_placement_frame
    )


def test_r10_g5_interface_a_offsets_translate_only_a_in_fixed_hvn() -> None:
    payload = _fixed_grid_payload()
    payload["interface_a_layout"]["bolts_per_row"] = 2
    baseline = preview_tee_connector(_request(_offset(payload, "interface_a_layout", "0", "0")))
    moved = preview_tee_connector(_request(_offset(payload, "interface_a_layout", "1", "-0.5")))

    assert baseline.visualization is not None
    assert moved.visualization is not None
    assert moved.visualization.interface_b_bolts == baseline.visualization.interface_b_bolts
    assert moved.interface_b.interface_fingerprint == baseline.interface_b.interface_fingerprint
    for before, after in zip(
        baseline.interface_a.placement.bolt_centers_hvn,
        moved.interface_a.placement.bolt_centers_hvn,
        strict=True,
    ):
        assert after.x - before.x == Decimal("-0.5")
        assert after.y - before.y == Decimal("1")
        assert after.z - before.z == 0


def test_r10_g6_interface_b_offset_is_independent() -> None:
    payload = _fixed_grid_payload()
    baseline = preview_tee_connector(_request(_offset(payload, "interface_b_layout", "0", "0")))
    moved = preview_tee_connector(_request(_offset(payload, "interface_b_layout", "-0.75", "0.25")))

    assert baseline.visualization is not None
    assert moved.visualization is not None
    assert moved.visualization.interface_a_bolts == baseline.visualization.interface_a_bolts
    assert moved.interface_a.interface_fingerprint == baseline.interface_a.interface_fingerprint


@pytest.mark.parametrize(
    ("distance", "valid", "clearance"),
    [
        ("1", False, "-0.2815"),
        ("1.2814", False, "-0.0001"),
        ("1.2815", True, "0"),
        ("1.3", True, "0.0185"),
    ],
)
def test_r10_g7_controlled_angle_clearance_is_exact(
    distance: str,
    valid: bool,
    clearance: str,
) -> None:
    request = _request(build_tee_r7_angle_payload(unloaded_end_distance=distance))
    if not valid:
        with pytest.raises(
            ValueError,
            match=(
                rf"Complete-hole clearance {clearance} in.*"
                r"Minimum for complete-hole containment: 1\.2815 in"
            ),
        ):
            resolve_tee_connector_request(request)
        return
    preview = preview_tee_connector(request)
    trace = preview.interface_a.placement.clearances
    assert trace.minimum.magnitude == Decimal(clearance)
    assert trace.geometry_valid is True
    assert trace.minimum_complete_hole_containment is not None
    assert trace.minimum_complete_hole_containment.magnitude == Decimal("1.2815")


def test_r10_g8_edge_and_offset_modes_preserve_exact_physical_geometry() -> None:
    edge_payload = build_tee_r7_angle_payload()
    offset_payload = _offset(edge_payload, "interface_a_layout", "-1.7185", "0")
    edge = preview_tee_connector(_request(edge_payload))
    offset = preview_tee_connector(_request(offset_payload))

    assert edge.visualization is not None
    assert offset.visualization is not None
    assert offset.visualization.interface_a_bolts == edge.visualization.interface_a_bolts
    assert offset.interface_a.placement.bolt_centers_hvn == (
        edge.interface_a.placement.bolt_centers_hvn
    )
    assert offset.interface_a.placement.physical_geometry_fingerprint == (
        edge.interface_a.placement.physical_geometry_fingerprint
    )
    assert offset.interface_a.placement.placement_mode is (
        TeeBoltPlacementMode.GROUP_OFFSET_CONTROLLED
    )


def test_r10_g9_incompatible_fixed_grid_method_fails_closed_without_losing_geometry() -> None:
    payload = _fixed_grid_payload("30")
    payload["global_force"] = {"x": "0.1", "y": "0", "z": "0.1", "unit": "kip"}
    request = _request(payload)
    preview = preview_tee_connector(request)
    design = design_check_tee_connector(request)

    assert preview.assembly_status is TeeAssemblyStatus.NOT_EVALUATED
    assert preview.visualization is not None
    assert preview.interface_a.preview.geometry_status is GeometryStatus.VALID
    assert preview.interface_a.preview.plan_availability is (
        PlanAvailability.CALCULATION_NOT_SUPPORTED
    )
    assert preview.interface_a.placement.method_compatibility is (
        TeeFixedGridCompatibilityStatus.ROW_DISTRIBUTION_FRAME_COMPATIBILITY_NOT_PROVEN
    )
    assert "ROW_DISTRIBUTION_FRAME_COMPATIBILITY_NOT_PROVEN" in preview.warnings
    assert preview.design_check_ready is False
    assert design.interface_a.design is None
    assert design.ordinary_pass_allowed is False


def test_r10_transport_is_backward_compatible_strict_and_has_no_normal_offset() -> None:
    omitted = build_tee_r7_angle_payload()
    explicit = deepcopy(omitted)
    explicit["interface_a_layout"]["placement_mode"] = "EDGE_DISTANCE_CONTROLLED"
    assert _request(omitted) == _request(explicit)

    forbidden = deepcopy(explicit)
    forbidden["interface_a_layout"]["normal_offset"] = {"value": "0", "unit": "in"}
    with pytest.raises(ValidationError, match="normal_offset"):
        TeeConnectorRequestDTO.model_validate(forbidden)

    mixed = _offset(omitted, "interface_a_layout", "0", "0")
    mixed["interface_a_layout"].pop("horizontal_offset")
    with pytest.raises(ValidationError, match="horizontal_offset"):
        TeeConnectorRequestDTO.model_validate(mixed)

    forbidden_edge_offset = deepcopy(explicit)
    forbidden_edge_offset["interface_a_layout"]["vertical_offset"] = {
        "value": "0",
        "unit": "in",
    }
    with pytest.raises(ValidationError, match="forbids group offsets"):
        TeeConnectorRequestDTO.model_validate(forbidden_edge_offset)

    wrong_dimension = _offset(omitted, "interface_a_layout", "0", "0")
    wrong_dimension["interface_a_layout"]["vertical_offset"]["unit"] = "kip"
    with pytest.raises(ValueError, match="must be length quantities"):
        _request(wrong_dimension)


def test_r10_domain_layout_rejects_every_invalid_placement_contract() -> None:
    layout = _request(build_tee_r7_angle_payload()).interface_a_layout

    with pytest.raises(TypeError, match="TeeBoltPlacementMode"):
        replace(layout, placement_mode=cast(Any, "EDGE_DISTANCE_CONTROLLED"))
    with pytest.raises(ValueError, match="forbids group offsets"):
        replace(layout, vertical_offset=Decimal(0))
    with pytest.raises(ValueError, match="requires vertical and horizontal"):
        replace(
            layout,
            placement_mode=TeeBoltPlacementMode.GROUP_OFFSET_CONTROLLED,
            vertical_offset=Decimal(0),
        )
    with pytest.raises(TypeError, match="must be a Decimal"):
        replace(
            layout,
            placement_mode=TeeBoltPlacementMode.GROUP_OFFSET_CONTROLLED,
            vertical_offset=cast(Any, 0.0),
            horizontal_offset=Decimal(0),
        )
    with pytest.raises(ValueError, match="must be finite"):
        replace(
            layout,
            placement_mode=TeeBoltPlacementMode.GROUP_OFFSET_CONTROLLED,
            vertical_offset=Decimal("NaN"),
            horizontal_offset=Decimal(0),
        )


def test_r10_internal_fail_closed_invariants_and_generic_clearance_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request(_fixed_grid_payload("30"))
    layout = replace(
        request.interface_a_layout,
        placement_mode=TeeBoltPlacementMode.GROUP_OFFSET_CONTROLLED,
        vertical_offset=Decimal(0),
        horizontal_offset=Decimal(0),
    )
    object.__setattr__(layout, "horizontal_offset", None)
    with pytest.raises(RuntimeError, match="lost its exact offsets"):
        tee_module._effective_layout(layout, Decimal(16), Decimal(6))

    quantity = PhysicalQuantity.of(Decimal("-0.1"), Unit.IN)
    trace = tee_module.TeeHoleClearanceTrace(
        vertical_positive=quantity,
        vertical_negative=quantity,
        horizontal_positive=quantity,
        horizontal_negative=quantity,
        minimum=quantity,
        governing_bolt_id="A_B_R1_L1",
        governing_boundary_id="A:VERTICAL_NEGATIVE",
        exact_deficit=PhysicalQuantity.of(Decimal("0.1"), Unit.IN),
        geometry_valid=False,
    )
    message = tee_module._invalid_clearance_message(trace)
    assert "Minimum for complete-hole containment" not in message

    resolved = resolve_tee_connector_request(request)
    invalid_preview = replace(
        preview_multirow_connection(resolved.interface_a_request),
        visualization=None,
    )
    monkeypatch.setattr(
        tee_module,
        "preview_multirow_connection",
        lambda _request: invalid_preview,
    )
    assert (
        tee_module._fixed_grid_geometry_only_preview(
            resolved.interface_a_request,
            invalid_preview,
        )
        is invalid_preview
    )


def test_r10_generic_candidate_scan_continues_after_a_noncontaining_patch() -> None:
    resolved = resolve_tee_connector_request(_request(_fixed_grid_payload()))
    group = resolved.context.resolved_bolt_groups[0]
    location = group.bolt_group.locations[0]
    layer = group.paths[0].layers[0]
    candidate = next(
        surface
        for surface in (layer.entry.surface, layer.exit.surface)
        if group.bolt_group_frame.x_axis.dot(
            cast(PlanarRectangularSurface3D, surface.geometry).normal
        )
        < 0
    )
    geometry = cast(PlanarRectangularSurface3D, candidate.geometry)
    too_small = replace(
        candidate,
        geometry=replace(geometry, extent_y=0.01, extent_z=0.01),
    )

    assert (
        tee_module._opposing_patch_for_location(
            location,
            group.bolt_group_frame,
            (too_small, candidate),
            layer.hole.radius,
            group.tolerance,
        )
        is candidate
    )


def test_r10_invalid_interface_b_clearance_reports_its_physical_boundary() -> None:
    payload = _fixed_grid_payload()
    payload["interface_b_layout"]["unloaded_end_distance"]["value"] = "0.1"
    with pytest.raises(ValueError, match="TEE_INTERFACE_B"):
        resolve_tee_connector_request(_request(payload))


def test_r10_g10_counts_and_r9_hardware_axes_remain_independent() -> None:
    zero = preview_tee_connector(_request(_fixed_grid_payload()))
    inclined = preview_tee_connector(_request(_fixed_grid_payload("30")))

    assert zero.visualization is not None
    assert inclined.visualization is not None
    assert len(inclined.visualization.interface_a_bolts) == 2
    assert len(inclined.visualization.interface_b_bolts) == 4
    assert tuple(item.axis for item in inclined.visualization.interface_a_bolts) == tuple(
        item.axis for item in zero.visualization.interface_a_bolts
    )
    assert all(item.washers == () for item in inclined.visualization.interface_a_bolts)
