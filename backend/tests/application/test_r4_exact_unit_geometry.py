"""Controlled Stage 3.2-R4 exact-unit and Tee benchmark regressions."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import fields
from decimal import Decimal
from pathlib import Path
from typing import cast

import frp_master_connection.application.multirow_orchestration as multirow_service
from frp_master_connection.application import (
    MultiRowOrchestrationRequest,
    TeeAssemblyStatus,
    preview_tee_connector,
    resolve_tee_connector_request,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.domain import FlatPlateProfileDimensions, MemberProfileFamily
from tests.tee_fixtures import build_tee_r4_benchmark_request

_GOLDEN_PATH = (
    Path(__file__).parents[1] / "golden" / "stage_3_2_r4_exact_unit_and_tee_benchmark_rc1.json"
)
_GOLDEN_SHA256 = "86600A897FF557CF176027E34449000C8B43AE227318B854D0C0AD4904BFC381"


def _golden() -> dict[str, object]:
    return cast(dict[str, object], json.loads(_GOLDEN_PATH.read_text(encoding="utf-8")))


def _assert_decimal_dimensions_equivalent(
    customary: object, metric: object, names: tuple[str, ...]
) -> None:
    for name in names:
        customary_value = cast(Decimal, getattr(customary, name))
        metric_value = cast(Decimal, getattr(metric, name))
        assert PhysicalQuantity(customary_value, Unit.IN).to(Unit.MM).magnitude == metric_value


def _normalized_geometry(request: MultiRowOrchestrationRequest) -> tuple[object, ...]:
    resolved = multirow_service._resolve(request)
    rows = tuple(
        PhysicalQuantity.from_finite_real(item.projected_coordinate, request.source_length_unit)
        .to(Unit.IN)
        .magnitude
        for item in resolved.geometry.rows
    )
    bolts = tuple(
        (
            PhysicalQuantity.from_finite_real(item.center.x, request.source_length_unit)
            .to(Unit.IN)
            .magnitude,
            PhysicalQuantity.from_finite_real(item.center.y, request.source_length_unit)
            .to(Unit.IN)
            .magnitude,
        )
        for item in sorted(resolved.geometry.group.bolts, key=lambda value: value.id)
    )
    end_distances = (
        resolved.end_distances.unloaded_end_e1.to(Unit.IN).magnitude,
        tuple(item.to(Unit.IN).magnitude for item in resolved.end_distances.physical_pitches),
        resolved.end_distances.row_1_to_unloaded_end_distance.to(Unit.IN).magnitude,
        resolved.end_distances.loaded_boundary_to_row_1_distance.to(Unit.IN).magnitude,
    )
    return rows, bolts, end_distances


def test_r4_owner_golden_is_byte_exact_and_declares_the_controlled_transition() -> None:
    assert hashlib.sha256(_GOLDEN_PATH.read_bytes()).hexdigest().upper() == _GOLDEN_SHA256
    golden = _golden()
    transition = cast(dict[str, str], golden["known_fingerprint_transition"])
    assert transition == {
        "case": "affected generic SI exact-coordinate execution",
        "deprecated_before": "7c6d7bb9b3d04246c789ad9ed9b291d5b7349a46435594d9bebb181c8488bf57",
        "required_after": "40ba8cb419f56f5b5c59e2b102c9842850bc925a600088b62185d96cc0314a69",
    }


def test_r4_us_and_si_benchmarks_are_exactly_equivalent_and_preview_valid() -> None:
    customary = build_tee_r4_benchmark_request()
    metric = build_tee_r4_benchmark_request(unit_system="SI")
    customary_preview = preview_tee_connector(customary)
    metric_preview = preview_tee_connector(metric)

    assert customary_preview.assembly_status is TeeAssemblyStatus.NOT_EVALUATED
    assert metric_preview.assembly_status is TeeAssemblyStatus.NOT_EVALUATED
    assert customary_preview.design_check_ready is metric_preview.design_check_ready is True
    assert (
        customary_preview.connected_member_profile.profile_family is MemberProfileFamily.FLAT_PLATE
    )
    assert metric_preview.connected_member_profile.profile_family is MemberProfileFamily.FLAT_PLATE
    assert customary_preview.connected_member_profile.selected_profile_surface.value == "FACE_POS"
    assert metric_preview.connected_member_profile.selected_profile_surface.value == "FACE_POS"
    assert customary.hole_basis is metric.hole_basis

    _assert_decimal_dimensions_equivalent(
        customary.connector_dimensions,
        metric.connector_dimensions,
        tuple(field.name for field in fields(customary.connector_dimensions)),
    )
    _assert_decimal_dimensions_equivalent(
        customary.support_dimensions,
        metric.support_dimensions,
        tuple(field.name for field in fields(customary.support_dimensions)),
    )
    customary_profile = cast(
        FlatPlateProfileDimensions, customary.connected_member_profile.dimensions
    )
    metric_profile = cast(FlatPlateProfileDimensions, metric.connected_member_profile.dimensions)
    _assert_decimal_dimensions_equivalent(
        customary_profile, metric_profile, ("width", "thickness", "member_length")
    )
    for customary_layout, metric_layout in (
        (customary.interface_a_layout, metric.interface_a_layout),
        (customary.interface_b_layout, metric.interface_b_layout),
    ):
        assert customary_layout.row_count == metric_layout.row_count == 2
        assert customary_layout.bolts_per_row == metric_layout.bolts_per_row == 2
        _assert_decimal_dimensions_equivalent(
            customary_layout,
            metric_layout,
            (
                "pitch",
                "gauge",
                "unloaded_end_distance",
                "loaded_end_distance",
                "negative_side_distance",
                "positive_side_distance",
            ),
        )
    assert customary.bolt_diameter.to(Unit.MM) == metric.bolt_diameter
    assert customary.global_force.z.to(Unit.KN) == metric.global_force.z
    assert customary.global_reference_point.x.to(Unit.MM) == metric.global_reference_point.x

    customary_resolved = resolve_tee_connector_request(customary)
    metric_resolved = resolve_tee_connector_request(metric)
    assert customary_resolved.context.basis.joint_frame.origin == (
        metric_resolved.context.basis.joint_frame.origin
    )
    assert _normalized_geometry(customary_resolved.interface_a_request) == _normalized_geometry(
        metric_resolved.interface_a_request
    )
    assert _normalized_geometry(customary_resolved.interface_b_request) == _normalized_geometry(
        metric_resolved.interface_b_request
    )


def test_r4_benchmark_bolt_paths_remain_finite_without_a_validation_bypass() -> None:
    for unit_system in ("US_CUSTOMARY", "SI"):
        resolved = resolve_tee_connector_request(
            build_tee_r4_benchmark_request(unit_system=unit_system)
        )
        groups = {item.bolt_group.id: item for item in resolved.context.resolved_bolt_groups}
        assert len(groups["tee-bolt-group-a"].paths) == 4
        assert len(groups["tee-bolt-group-b"].paths) == 1
        for group in groups.values():
            for path in group.paths:
                assert len(path.layers) == 2
                assert all(
                    math.isfinite(layer.raw_minimum_patch_clearance)
                    and layer.raw_minimum_patch_clearance > 0
                    and math.isfinite(layer.raw_thickness)
                    and layer.raw_thickness > 0
                    for layer in path.layers
                )
