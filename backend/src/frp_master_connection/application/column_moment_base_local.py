"""Actual signed per-region demand and native local FRP applicability."""

from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
from typing import cast

from frp_master_connection.application.column_moment_base_paths import connector_paths
from frp_master_connection.application.column_moment_base_preview import ColumnMomentPreview
from frp_master_connection.application.wi_frp_support_local_checks import SupportLocalCheck
from frp_master_connection.application.wi_wall_moment_demand import END_USE
from frp_master_connection.calculation import MaterialDirection, ThreadStatus
from frp_master_connection.calculation.angle_connector_core import components, exact_decimal
from frp_master_connection.calculation.equations import (
    pin_bearing_resistance,
    pull_through_resistance,
)
from frp_master_connection.calculation.in_plane_wrench_demand import project_rational
from frp_master_connection.calculation.multirow_equations import (
    adjusted_property_trace,
    compare_resistance,
)
from frp_master_connection.calculation.properties import (
    FRPPropertyKind,
    create_locked_ice_material_snapshot,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.resistance_handoff import _material_direction
from frp_master_connection.domain.column_moment_base import Face


def member_local_checks(preview: ColumnMomentPreview) -> tuple[SupportLocalCheck, ...]:
    record = preview.response.response
    if record is None:
        return ()
    from frp_master_connection.application.mat1_scope import material_for_owner

    properties = {
        p.kind: p
        for p in material_for_owner("COLUMN", create_locked_ice_material_snapshot()).properties
    }
    checks = []
    domains = {b.bolt_id: b for b in preview.response_binding.physical_bolts}
    for response in record.bolts:
        domain = domains[response.bolt_id]
        owner = cast(Face, domain.owner_connector)
        item = preview.input.physical_connector(owner)
        forces = {layer_item.layer_id: layer_item.action for layer_item in response.layers}
        for layer in domain.layers:
            action = forces[layer.layer_id]
            f = components(action.force)
            lw, cw, _tt = tuple(
                sum((x * y for x, y in zip(f, axis, strict=True)), Fraction(0))
                for axis in layer.material_basis_global
            )
            with localcontext() as context:
                context.prec = 80
                direction = _material_direction(
                    (exact_decimal(lw), exact_decimal(cw)), (Decimal(1), Decimal(0))
                )
            magnitude = PhysicalQuantity(
                project_rational(lw * lw + cw * cw, square_root=True), Unit.N
            )
            # A native single-lap constant-row bearing subcase only. A qualified
            # coupled record is not itself authority to assume long-grip C_delta/C_lap.
            group_actions = tuple(
                forces_for_bolt.action
                for bolt in record.bolts
                for forces_for_bolt in bolt.layers
                if forces_for_bolt.layer_id == layer.layer_id
            )
            cardinal = (lw == 0) != (cw == 0)
            same = all(
                components(a.force) == f
                and components(a.moment) == (Fraction(0), Fraction(0), Fraction(0))
                for a in group_actions
            )
            short_single = preview.input.column.family == "WI" and owner.startswith("Y")
            native_bearing = short_single and cardinal and same
            kind = (
                FRPPropertyKind.FBR_L
                if direction is MaterialDirection.LONGITUDINAL
                else FRPPropertyKind.FBR_T
            )
            trace = None
            comparison = None
            if native_bearing:
                # Prescriptive pitch correction still needs the physical row axis.
                from frp_master_connection.application.wi_wall_moment_geometry import q
                from frp_master_connection.calculation.multirow_equations import (
                    constant_pitch_factor,
                )

                spec = item.angle
                across = bool(lw) if layer.connector_id else bool(cw)
                pitch = spec.member_pattern.gauge if across else spec.member_pattern.pitch
                count = spec.member_pattern.across if across else spec.member_pattern.along
                delta = (
                    constant_pitch_factor(
                        tuple(q(pitch.to(Unit.IN).magnitude) for _ in range(count - 1)),
                        spec.fastener.bolt_diameter,
                    ).pitch_factor_c_delta
                    if count > 1
                    else Decimal(1)
                )
                trace = pin_bearing_resistance(
                    layer.material_thickness,
                    spec.fastener.bolt_diameter,
                    adjusted_property_trace(properties[kind], END_USE),
                    ThreadStatus(spec.fastener.thread_condition),
                    c_delta=delta,
                    c_lap=Decimal(".6"),
                    lambda_factor=Decimal(1),
                )
                comparison = compare_resistance(magnitude, trace.factor_trace.design_resistance)
            checks.append(
                SupportLocalCheck(
                    "PIN_BEARING:" + domain.bolt_id + ":" + layer.layer_id,
                    domain.owner_connector,
                    layer.layer_id,
                    domain.bolt_id,
                    "NATIVE_ASCE_8_5",
                    "SOURCE_REQUIRED"
                    if comparison is None
                    else comparison.numerical_comparison.value,
                    magnitude,
                    None if trace is None else trace.factor_trace.design_resistance,
                    trace,
                    comparison,
                    "ACTUAL_SINGLE_LAP_CONSTANT_DIRECTION_NATIVE_BEARING"
                    if native_bearing
                    else "COUPLED_LONG_GRIP_SOLID_OR_OBLIQUE_REGION_APPLICABILITY_REQUIRED",
                    preview.response.fingerprint,
                    direction.value,
                    (
                        PhysicalQuantity(exact_decimal(lw), Unit.N),
                        PhysicalQuantity(exact_decimal(cw), Unit.N),
                    ),
                )
            )
            # Only a real terminal exterior washer uses the native thin-leaf check.
            # No washer exists at an RHS cavity wall or in a solid middle section.
            terminal = layer.connector_id is not None
            tensile = next(
                r.attachment_tensile_demand for r in response.layers if r.layer_id == layer.layer_id
            )
            pull = None
            pc = None
            if terminal and tensile is not None:
                pull = pull_through_resistance(
                    item.member_hardware.washer_diameter,
                    layer.material_thickness,
                    adjusted_property_trace(properties[FRPPropertyKind.FSH_LT], END_USE),
                    adjusted_property_trace(properties[FRPPropertyKind.FSH_INT], END_USE),
                    c_delta=Decimal(1),
                    lambda_factor=Decimal(1),
                )
                pc = compare_resistance(tensile, pull.factor_trace.design_resistance)
            checks.append(
                SupportLocalCheck(
                    "PULL_THROUGH:" + domain.bolt_id + ":" + layer.layer_id,
                    domain.owner_connector,
                    layer.layer_id,
                    domain.bolt_id,
                    "NATIVE_ASCE_8_4_LESSER_BRANCHES",
                    "SOURCE_REQUIRED" if pc is None else pc.numerical_comparison.value,
                    tensile,
                    None if pull is None else pull.factor_trace.design_resistance,
                    pull,
                    pc,
                    "ACTUAL_TERMINAL_WASHER"
                    if terminal
                    else "NO_INTERNAL_WASHER_OR_AUTOMATIC_SOLID_THIN_PLATE",
                    preview.response.fingerprint,
                    "TT",
                )
            )
    for angle in preview.geometry.angles:
        transfer = next(t for t in preview.transfers if t.connector_id == angle.connector_id)
        checks.extend(connector_paths(preview, transfer))
        checks.append(
            SupportLocalCheck(
                "LOCAL_PATHS:" + angle.connector_id,
                angle.connector_id,
                angle.connector_id,
                None,
                "EXACT_NET_SHEAROUT_CLEAVAGE_BLOCK_AND_JUNCTION_APPLICABILITY",
                "SOURCE_REQUIRED",
                None,
                None,
                None,
                None,
                "QUALIFIED_COMMON_PHYSICAL_FAILURE_PATHS_REQUIRED_NO_VIEW_END_OR_THIN_SOLID_ASSUMPTION",
                preview.response.fingerprint,
                "ACTUAL_R14B_REGION_BASES",
            )
        )
    return tuple(checks)
