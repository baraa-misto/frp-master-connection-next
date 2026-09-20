"""Synthetic Stage 4.4 sources: test infrastructure, NEVER production qualification."""

from dataclasses import replace
from fractions import Fraction

from frp_master_connection.application.angle_column_base_design import (
    evaluate_angle_column_moment_base,
)
from frp_master_connection.application.angle_column_base_preview import (
    AngleBasePreview,
    AngleBaseTransfer,
    preview_angle_column_moment_base,
)
from frp_master_connection.application.angle_column_base_qualification import (
    MEMBER_RESPONSE_COVERAGE,
    column_zone_binding,
    connector_context,
    fastener_binding,
    member_response_binding,
)
from frp_master_connection.application.angle_column_base_sources import (
    AngleBaseSourceRegistry,
    QualifiedColumnBaseZone,
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
from frp_master_connection.calculation.angle_column_base_response import (
    REQUIRED_COVERAGE,
    ZERO,
    ColumnPressurePatch,
    QualifiedBaseBranch,
    QualifiedBaseResponse,
    global_to_local_wrench,
    opposite,
    sum_wrenches,
    transform_wrench,
)
from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    components,
    quantity_vector,
)
from frp_master_connection.calculation.frp_angle_connector_provider import (
    QualifiedCoverage,
    QualifiedFRPAngleSource,
    SignedDesignStrength,
    frp_source_binding,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.support_attachment_response import (
    QualifiedSupportResponse,
    ShaftDemand,
    SupportResponseAction,
)
from frp_master_connection.domain.angle_column_moment_base import (
    AngleBaseConnector,
    AngleColumnMomentBaseRequest,
)
from tests.calculation.test_support_attachment_response import source


def references(r: AngleColumnMomentBaseRequest) -> AngleColumnMomentBaseRequest:
    def connector(c: AngleBaseConnector, n: int) -> AngleBaseConnector:
        return replace(
            c,
            angle=replace(
                c.angle,
                connector_source_reference=f"TEST_BODY_{n}",
                attachment_source_reference=f"TEST_ATTACHMENT_{n}",
            ),
            normal_response_source_reference=f"TEST_NORMAL_{n}",
            fastener_source_reference=f"TEST_BOLT_{n}",
        )

    return replace(
        r,
        leg_1=connector(r.leg_1, 1),
        leg_2=connector(r.leg_2, 2),
        response_source_reference="TEST_BASE",
        column_zone_source_reference="TEST_ZONE",
    )


def _normal(
    preview: AngleBasePreview, transfer: AngleBaseTransfer, reference: str
) -> QualifiedSupportResponse:
    """Explicit exact normal-only fixture; Slice 8 independently supplies all shear.

    Positive bolt tension plus a compressive contact point can recover the
    complementary three-component target. Its TEST qualification is stipulated,
    not inferred from balance. No source couple or solver tolerance is inserted.
    """
    binding = member_response_binding(preview, transfer)
    group, target = binding.group_targets[0]
    domain = binding.contact_domains[0]
    cx, cy, cz = components(target.reference)
    fz = components(target.force)[2]
    ma, mb, _ = components(target.moment)
    k = Fraction(1)
    while True:
        tension = k + fz / 4
        contact = (cx + mb / (4 * k), cy - ma / (4 * k), cz)
        if (
            tension >= 0
            and Fraction(domain.u_min.canonical_magnitude)
            <= contact[0]
            <= Fraction(domain.u_max.canonical_magnitude)
            and Fraction(domain.v_min.canonical_magnitude)
            <= contact[1]
            <= Fraction(domain.v_max.canonical_magnitude)
        ):
            break
        k *= 10
    zero = quantity_vector(ZERO, Unit.N_MM)
    actions = []
    shafts = []
    projected = {
        f"{transfer.connector_id}:{b.bolt_id}": b
        for b in transfer.in_plane_demand.solution.projected_bolts()
    }
    for bolt in binding.physical_bolts:
        point = quantity_vector((components(bolt.near)[0], components(bolt.near)[1], cz), Unit.MM)
        action = SupportResponseAction(
            bolt.bolt_id,
            group,
            "BOLT",
            point,
            quantity_vector((Fraction(0), Fraction(0), tension), Unit.N),
            zero,
            bolt.bolt_id,
            domain.layer_id,
        )
        actions.append(action)
        native = projected[bolt.bolt_id]
        shafts.append(
            ShaftDemand(
                bolt.bolt_id,
                "ACTUAL_SINGLE_INTERFACE",
                bolt.layer_ids,
                replace(
                    native.total_force.u, magnitude=native.total_force.u.magnitude.copy_negate()
                ),
                replace(
                    native.total_force.v, magnitude=native.total_force.v.magnitude.copy_negate()
                ),
                action.force.z,
                "SINGLE_PLANE_8_2_8_3",
                True,
            )
        )
    actions.append(
        SupportResponseAction(
            "TEST_CONTACT",
            group,
            "CONTACT",
            quantity_vector(contact, Unit.MM),
            quantity_vector((Fraction(0), Fraction(0), -4 * k), Unit.N),
            zero,
            None,
            domain.layer_id,
        )
    )
    return QualifiedSupportResponse(
        reference,
        source(),
        "TEST_ONLY",
        binding,
        tuple(actions),
        tuple(shafts),
        ("TEST_EXACT_SINGLE_ACTION_NORMAL_CONTACT_STATE",),
        MEMBER_RESPONSE_COVERAGE,
        "TEST_ONLY_NORMAL_STATE_NOT_A_PRODUCTION_SOLVER",
        True,
    )


def complete_sources(
    r: AngleColumnMomentBaseRequest,
) -> tuple[AngleColumnMomentBaseRequest, AngleBasePreview, AngleBaseSourceRegistry]:
    r = references(r)
    p = preview_angle_column_moment_base(r)
    one, two = p.response_binding.branches
    # Nonzero on BOTH perpendicular connectors; deliberately not an equal split.
    second = AngleWrench(
        two.local_member_reference,
        quantity_vector((Fraction(7), Fraction(11), Fraction(-13)), Unit.N),
        quantity_vector((Fraction(2), Fraction(3), Fraction(5)), Unit.N_MM),
    )
    patches: tuple[ColumnPressurePatch, ...] = ()
    contact = AngleWrench(
        p.required_total_foundation_action.reference,
        quantity_vector(ZERO, Unit.N),
        quantity_vector(ZERO, Unit.N_MM),
    )
    if r.actions.axial.canonical_magnitude < 0:
        patches = (
            ColumnPressurePatch(
                "TEST_COLUMN_PATCH",
                PhysicalQuantity.of("25.4", Unit.MM),
                PhysicalQuantity.of("50.8", Unit.MM),
                PhysicalQuantity.of("0", Unit.MM),
                PhysicalQuantity.of("6.35", Unit.MM),
                PhysicalQuantity.of(".1", Unit.MPA),
            ),
        )
        patch_action = AngleWrench(
            quantity_vector((Fraction("38.1"), Fraction("3.175"), Fraction(0)), Unit.MM),
            quantity_vector(
                (Fraction(0), Fraction(0), -Fraction(".1") * Fraction("25.4") * Fraction("6.35")),
                Unit.N,
            ),
            quantity_vector(ZERO, Unit.N_MM),
        )
        contact = sum_wrenches((patch_action,), contact.reference)
    first_global = sum_wrenches(
        (
            p.required_total_foundation_action,
            opposite(
                transform_wrench(
                    second, two.frame, two.global_heel, p.required_total_foundation_action.reference
                )
            ),
            opposite(contact),
        ),
        p.required_total_foundation_action.reference,
    )
    first = global_to_local_wrench(
        first_global, one.frame, one.global_heel, one.local_member_reference
    )
    record = QualifiedBaseResponse(
        r.response_source_reference,
        source(),
        "TEST_ONLY",
        p.response_binding,
        (QualifiedBaseBranch(one, first, None), QualifiedBaseBranch(two, second, None)),
        contact,
        patches,
        None if patches else "TEST_EXPLICIT_INACTIVE_COLUMN_CONTACT",
        "TEST_ONLY_STIPULATED_COMPATIBILITY_NOT_A_RESPONSE_SOLVER",
        REQUIRED_COVERAGE,
        "EXACT_CASE_ONLY",
    )
    sources = AngleBaseSourceRegistry(responses=(record,))
    p = preview_angle_column_moment_base(r, sources)
    assert p.response.qualified, p.response.reasons
    bodies = []
    normals = []
    fasteners = []
    strengths = tuple(
        SignedDesignStrength(
            PhysicalQuantity.of("1E20", Unit.N if i < 3 else Unit.N_MM),
            PhysicalQuantity.of("2E20", Unit.N if i < 3 else Unit.N_MM),
        )
        for i in range(6)
    )
    for index, t in enumerate(p.transfers):
        c = r.connectors[index]
        for attachment in (False, True):
            ctx = connector_context(p, t, attachment=attachment)
            package = QualifiedFRPAngleSource(
                source(), frp_source_binding(t.core, ctx), strengths, tuple(QualifiedCoverage), True
            )
            bodies.append(
                WallMomentQualifiedSource(
                    c.angle.attachment_source_reference
                    if attachment
                    else c.angle.connector_source_reference,
                    t.connector_id,
                    package,
                    attachment,
                    ATTACHMENT_COVERAGE if attachment else (),
                )
            )
        normals.append(_normal(p, t, c.normal_response_source_reference))
        fasteners.append(
            SupportFastenerSource(
                c.fastener_source_reference,
                source(),
                fastener_binding(p, t),
                PhysicalQuantity.of("400", Unit.MPA),
                PhysicalQuantity.of("250", Unit.MPA),
                c.angle.fastener.thread_condition,
                ("SINGLE_PLANE_8_2_8_3",),
            )
        )
    sources = replace(
        sources,
        connector_sources=WallMomentSourceRegistry(tuple(bodies)),
        member_responses=tuple(normals),
        fasteners=tuple(fasteners),
    )
    partial = evaluate_angle_column_moment_base(r, sources)
    assert partial.local_zone is not None
    coverage = partial.local_zone.required_coverage
    zone = QualifiedColumnBaseZone(
        r.column_zone_source_reference,
        source(),
        column_zone_binding(p),
        (
            QualifiedZoneCheck(
                "TEST_COUPLED_END_ZONE",
                coverage,
                PhysicalQuantity.of(1, Unit.N),
                PhysicalQuantity.of(2, Unit.N),
                "TEST_QUALIFIED_RESULT_NOT_NEW_FORMULA",
                "TEST_ONLY",
            ),
        ),
        coverage,
        "TEST_EXACT_CASE_ONLY",
    )
    return r, p, replace(sources, zones=(zone,))
