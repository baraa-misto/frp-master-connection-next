"""Synthetic source-present integration records. NEVER a production solver or catalogue."""

from dataclasses import replace
from fractions import Fraction
from typing import cast

from frp_master_connection.application.column_moment_base_preview import (
    ColumnMomentPreview,
    preview_column_moment_base,
)
from frp_master_connection.application.column_moment_base_sources import ColumnMomentSourceRegistry
from frp_master_connection.calculation.angle_column_base_response import (
    ZERO,
    ColumnPressurePatch,
    QualifiedBaseBranch,
    add,
    global_to_local_wrench,
    opposite,
    sum_wrenches,
    transform_wrench,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    Rational3,
    components,
    exact_decimal,
    quantity_vector,
    shift_angle_wrench,
)
from frp_master_connection.calculation.column_moment_base_response import (
    REQUIRED_COVERAGE,
    CoupledBoltResponse,
    LayerResponse,
    QualifiedColumnBaseResponse,
    ShaftSectionResponse,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.column_moment_base import ColumnMomentBaseRequest, Face
from tests.calculation.test_support_attachment_response import source


def response_sources(
    request: ColumnMomentBaseRequest,
) -> tuple[ColumnMomentBaseRequest, ColumnMomentPreview, ColumnMomentSourceRegistry]:
    request = replace(request, response_source_reference="TEST_ONLY_BASE")
    preview = preview_column_moment_base(request)
    binding = preview.response_binding
    report = binding.required_total.reference
    contact = AngleWrench(report, quantity_vector(ZERO, Unit.N), quantity_vector(ZERO, Unit.N_MM))
    patches: tuple[ColumnPressurePatch, ...] = ()
    if request.actions.axial.canonical_magnitude < 0:
        x0, x1, y0, y1 = binding.column_contact_rectangles[0]
        xa, xb = x0 + (x1 - x0) / 4, x0 + (x1 - x0) / 2
        ya, yb = y0 + (y1 - y0) / 4, y0 + (y1 - y0) / 2
        patches = (
            ColumnPressurePatch(
                "TEST_COLUMN_PRESSURE",
                PhysicalQuantity(exact_decimal(xa), Unit.MM),
                PhysicalQuantity(exact_decimal(xb), Unit.MM),
                PhysicalQuantity(exact_decimal(ya), Unit.MM),
                PhysicalQuantity(exact_decimal(yb), Unit.MM),
                PhysicalQuantity.of(".1", Unit.MPA),
            ),
        )
        contact = shift_angle_wrench(
            AngleWrench(
                quantity_vector(((xa + xb) / 2, (ya + yb) / 2, Fraction(0)), Unit.MM),
                quantity_vector(
                    (Fraction(0), Fraction(0), -Fraction(".1") * (xb - xa) * (yb - ya)), Unit.N
                ),
                quantity_vector(ZERO, Unit.N_MM),
            ),
            report,
        )
    branches = []
    for index, branch_domain in enumerate(binding.branches[1:]):
        # Deliberately unequal, stipulated small nonzero test branch wrenches.
        branch = AngleWrench(
            branch_domain.local_member_reference,
            quantity_vector((Fraction(7 + index), Fraction(11), Fraction(-13)), Unit.N),
            quantity_vector((Fraction(2), Fraction(3 + index), Fraction(5)), Unit.N_MM),
        )
        branches.append(QualifiedBaseBranch(branch_domain, branch))
    first_global = sum_wrenches(
        (
            binding.required_total,
            opposite(contact),
            *(
                opposite(
                    transform_wrench(b.member_action, b.domain.frame, b.domain.global_heel, report)
                )
                for b in branches
            ),
        ),
        report,
    )
    first = binding.branches[0]
    branches.insert(
        0,
        QualifiedBaseBranch(
            first,
            global_to_local_wrench(
                first_global,
                first.frame,
                first.global_heel,
                first.local_member_reference,
            ),
        ),
    )
    global_branches = {
        b.domain.connector_id: transform_wrench(
            b.member_action, b.domain.frame, b.domain.global_heel, report
        )
        for b in branches
    }
    bolts = []
    for domain in binding.physical_bolts:
        layers = []
        for layer in domain.layers:
            if layer.connector_id is None:
                continue
            count = sum(
                any(layer_item.connector_id == layer.connector_id for layer_item in b.layers)
                for b in binding.physical_bolts
            )
            target = shift_angle_wrench(global_branches[layer.connector_id], layer.point)
            force = cast(Rational3, tuple(v / count for v in components(target.force)))
            moment = cast(Rational3, tuple(v / count for v in components(target.moment)))
            # Explicit source-authorized secondary-bending couples. This fixture
            # stipulates them; production does not derive them from aggregate UR.
            layers.append(
                LayerResponse(
                    layer.layer_id,
                    AngleWrench(
                        layer.point,
                        quantity_vector(force, Unit.N),
                        quantity_vector(moment, Unit.N_MM),
                    ),
                    PhysicalQuantity.of(10, Unit.N),
                )
            )
        receiving = [layer_item for layer_item in domain.layers if layer_item.connector_id is None]
        remainder = opposite(
            sum_wrenches(tuple(layer_item.action for layer_item in layers), receiving[0].point)
        )
        # RHS far wall is explicitly inactive in this synthetic state, not equal-share.
        for index, layer in enumerate(receiving):
            action = (
                remainder
                if index == 0
                else AngleWrench(
                    layer.point, quantity_vector(ZERO, Unit.N), quantity_vector(ZERO, Unit.N_MM)
                )
            )
            layers.append(LayerResponse(layer.layer_id, action))
        indexed = {layer_item.layer_id: layer_item for layer_item in layers}
        ordered = tuple(indexed[layer_item.layer_id] for layer_item in domain.layers)
        cumulative = ZERO
        sections = []
        for layer_response in ordered[:-1]:
            cumulative = add(cumulative, components(layer_response.action.force))
            sections.append(
                ShaftSectionResponse(
                    "AFTER:" + layer_response.layer_id,
                    layer_response.layer_id,
                    quantity_vector(cumulative, Unit.N),
                    PhysicalQuantity.of(10, Unit.N),
                    "TEST_NORMAL_PRYING_CONTACT_BASIS",
                    "SOURCE_BOUND_ACTUAL_SINGLE_SECTION_8_2_8_3",
                    True,
                )
            )
        bolts.append(
            CoupledBoltResponse(
                domain.bolt_id,
                ordered,
                tuple(sections),
                "QUALIFIED_COUPLED_EXPLICIT_LAYER_RESPONSE",
                "TEST_ONLY_STIPULATED_COMPATIBILITY_BENDING_NOT_A_PRODUCTION_SOLVER",
                tuple(layer_item.layer_id for layer_item in domain.layers),
            )
        )
    record = QualifiedColumnBaseResponse(
        request.response_source_reference,
        source(),
        "TEST_ONLY",
        binding,
        tuple(branches),
        contact,
        patches,
        None if patches else "TEST_EXPLICIT_INACTIVE_CONTACT",
        "TEST_ONLY_EXACT_CASE_COMPATIBILITY_AND_PRESSURE_STATE",
        REQUIRED_COVERAGE,
        "EXACT_TEST_CASE_ONLY",
        tuple(bolts),
    )
    registry = ColumnMomentSourceRegistry(responses=(record,))
    preview = preview_column_moment_base(request, registry)
    assert preview.response.qualified, preview.response.reasons
    return request, preview, registry


def complete_sources(
    request: ColumnMomentBaseRequest,
) -> tuple[ColumnMomentBaseRequest, ColumnMomentPreview, ColumnMomentSourceRegistry]:
    from frp_master_connection.application.column_moment_base_design import (
        evaluate_column_moment_base,
    )
    from frp_master_connection.application.column_moment_base_qualification import (
        column_zone_binding,
        connector_context,
        fastener_binding,
    )
    from frp_master_connection.application.column_moment_base_sources import (
        QualifiedColumnMomentZone,
    )
    from frp_master_connection.application.wi_frp_support_moment_sources import (
        QualifiedZoneCheck,
        SupportFastenerSource,
    )
    from frp_master_connection.application.wi_wall_moment_sources import (
        ATTACHMENT_COVERAGE,
        WallMomentQualifiedSource,
        WallMomentSourceRegistry,
    )
    from frp_master_connection.calculation.frp_angle_connector_provider import (
        QualifiedCoverage,
        QualifiedFRPAngleSource,
        SignedDesignStrength,
        frp_source_binding,
    )

    changes = {}
    for key in ("x_positive", "x_negative", "y_positive", "y_negative"):
        connector = getattr(request, key)
        changes[key] = replace(
            connector,
            angle=replace(
                connector.angle,
                connector_source_reference="TEST_BODY_" + key,
                attachment_source_reference="TEST_ATTACHMENT_" + key,
            ),
            fastener_source_reference="TEST_FASTENER_" + key,
        )
    request = replace(request, **changes, column_zone_source_reference="TEST_ZONE")
    request, preview, registry = response_sources(request)
    strengths = tuple(
        SignedDesignStrength(
            PhysicalQuantity.of("1E20", Unit.N if i < 3 else Unit.N_MM),
            PhysicalQuantity.of("2E20", Unit.N if i < 3 else Unit.N_MM),
        )
        for i in range(6)
    )
    bodies = []
    fasteners = []
    for transfer in preview.transfers:
        face = cast(Face, transfer.connector_id)
        connector = request.physical_connector(face)
        for attachment in (False, True):
            context = connector_context(preview, transfer, attachment=attachment)
            bodies.append(
                WallMomentQualifiedSource(
                    connector.angle.attachment_source_reference
                    if attachment
                    else connector.angle.connector_source_reference,
                    transfer.connector_id,
                    QualifiedFRPAngleSource(
                        source(),
                        frp_source_binding(transfer.core, context),
                        strengths,
                        tuple(QualifiedCoverage),
                        True,
                    ),
                    attachment,
                    ATTACHMENT_COVERAGE if attachment else (),
                )
            )
        if any(b.owner_connector == face for b in preview.response_binding.physical_bolts):
            fasteners.append(
                SupportFastenerSource(
                    connector.fastener_source_reference,
                    source(),
                    fastener_binding(preview, face),
                    PhysicalQuantity.of("400", Unit.MPA),
                    PhysicalQuantity.of("250", Unit.MPA),
                    connector.angle.fastener.thread_condition,
                    ("SOURCE_BOUND_ACTUAL_SINGLE_SECTION_8_2_8_3",),
                )
            )
    registry = replace(
        registry,
        connector_sources=WallMomentSourceRegistry(tuple(bodies)),
        fasteners=tuple(fasteners),
    )
    partial = evaluate_column_moment_base(request, registry)
    assert partial.local_zone is not None
    coverage = partial.local_zone.required_coverage
    zone = QualifiedColumnMomentZone(
        request.column_zone_source_reference,
        source(),
        column_zone_binding(preview),
        (
            QualifiedZoneCheck(
                "TEST_COMMON_END_ZONE",
                coverage,
                PhysicalQuantity.of(1, Unit.N),
                PhysicalQuantity.of(2, Unit.N),
                "TEST_QUALIFIED_RESULT_NOT_FORMULA",
                "TEST_ONLY",
            ),
        ),
        coverage,
        "TEST_ONLY_EXACT_CASE",
    )
    return request, preview, replace(registry, zones=(zone,))
