"""Stage 2.4A general geometry, demand, applicability, and plan-contract tests."""

from dataclasses import fields, replace
from decimal import Decimal
from enum import Enum

import pytest

from frp_master_connection.calculation import (
    ConnectedMaterialPair,
    DeferredExecutionStatus,
    EffectiveWidthStatus,
    EngineerRowForce,
    EngineerRowFraction,
    FirstRowGeometryMapping,
    FirstRowPlanMethod,
    GeometryStatus,
    InterrowShearOutMethod,
    MaterialDirection,
    MethodProvenance,
    MultiRowAggregateStatus,
    MultiRowApplicability,
    MultiRowCalculationPlanSet,
    MultiRowFingerprintEnvelope,
    MultiRowFingerprintInput,
    MultiRowMethodApplicability,
    MultiRowNumericalComparison,
    MultiRowWarning,
    MultiRowWarningCode,
    PhysicalQuantity,
    PlanAvailability,
    PultrudedElementClassification,
    QualificationDisposition,
    RowDistributionBasis,
    Unit,
    aggregate_multirow_status,
    assess_multirow_applicability,
    build_first_row_net_tension_plans,
    build_interrow_shear_out_plans,
    canonical_multirow_fingerprint_json,
    multirow_plan_fingerprint,
    plan_row_demands,
    prescribed_row_fractions,
    resolve_first_row_geometry,
)
from frp_master_connection.geometry import (
    BlockPathFamily,
    BlockPathRejectionReason,
    BlockPathSegment,
    BlockPathSegmentKind,
    BlockShearCandidatePath,
    BoundaryObstacleKind,
    GeneralBolt,
    GeneralBoltGroup,
    MultiRowGeometry,
    MultiRowGeometryTolerance,
    PlanarLayerBoundary,
    PlanarPoint2D,
    ProjectedBolt,
    ProjectedPoint2D,
    RectangularObstacle2D,
    resolve_block_shear_paths,
    resolve_multirow_geometry,
    validate_block_shear_candidate,
)


def _provenance(*, reference: str | None = "CALC-1") -> MethodProvenance:
    return MethodProvenance(
        "approved-test-method",
        reference,
        "R1",
        "LC-1",
        "RP-1",
        True,
        True,
    )


def _bolt(
    identifier: str, x: float, y: float, *, identity: str = "A", hole: float = 0.563
) -> GeneralBolt:
    return GeneralBolt(
        identifier,
        PlanarPoint2D(x, y),
        0.5,
        hole,
        identity,
        "CONNECTION-1",
    )


def _geometry(
    row_coordinates: tuple[float, ...] = (4.0, 2.0, 0.0),
    row_line_coordinates: tuple[tuple[float, ...], ...] | None = None,
    *,
    boundary: PlanarLayerBoundary | None = None,
    reverse_array: bool = False,
    identities: tuple[str, ...] | None = None,
    tolerance: float = 1e-6,
    force: tuple[float, float] = (1.0, 0.0),
) -> MultiRowGeometry:
    lines = row_line_coordinates or tuple((-1.0, 1.0) for _ in row_coordinates)
    bolts = tuple(
        _bolt(
            f"B_X{x:g}_Y{y:g}",
            x,
            y,
            identity="A" if identities is None else identities[row_index],
        )
        for row_index, (x, ys) in enumerate(zip(row_coordinates, lines, strict=True))
        for y in ys
    )
    if reverse_array:
        bolts = tuple(reversed(bolts))
    group = GeneralBoltGroup(
        "BG-1",
        "INTERFACE-1",
        len(row_coordinates),
        len(bolts),
        bolts,
    )
    physical_boundary = boundary or PlanarLayerBoundary(
        "LAYER-1",
        min(row_coordinates) - 4.0,
        max(row_coordinates) + 2.0,
        -3.0,
        3.0,
    )
    return resolve_multirow_geometry(
        group,
        physical_boundary,
        force,
        MultiRowGeometryTolerance(tolerance),
    )


def _first_row(
    geometry: MultiRowGeometry,
    direction: MaterialDirection = MaterialDirection.LONGITUDINAL,
    element: PultrudedElementClassification = PultrudedElementClassification.SHAPE,
) -> FirstRowGeometryMapping:
    return resolve_first_row_geometry(
        geometry,
        Unit.IN,
        PhysicalQuantity.of("0.5", Unit.IN),
        direction,
        element,
    )


def test_general_geometry_accepts_arbitrary_counts_and_is_deterministic() -> None:
    five_rows = _geometry((8.0, 6.0, 4.0, 2.0, 0.0))
    four_across = _geometry((4.0, 2.0), ((-3.0, -1.0, 1.0, 3.0),) * 2)
    shuffled = _geometry(reverse_array=True)

    assert len(five_rows.rows) == 5
    assert len(four_across.rows[0].bolts) == 4
    assert five_rows.group.declared_row_count == 5
    assert [row.id for row in shuffled.rows] == ["ROW_1", "ROW_2", "ROW_3"]
    assert [[bolt.bolt.id for bolt in row.bolts] for row in shuffled.rows] == [
        ["B_X4_Y-1", "B_X4_Y1"],
        ["B_X2_Y-1", "B_X2_Y1"],
        ["B_X0_Y-1", "B_X0_Y1"],
    ]


@pytest.mark.parametrize("value", [0, -1, True])
def test_general_group_rejects_nonpositive_or_boolean_counts(value: int) -> None:
    bolt = _bolt("B1", 0.0, 0.0)
    expected = TypeError if isinstance(value, bool) else ValueError
    with pytest.raises(expected):
        GeneralBoltGroup("BG", "I", value, 1, (bolt,))
    with pytest.raises(expected):
        GeneralBoltGroup("BG", "I", 1, value, (bolt,))


def test_general_geometry_rejects_duplicate_id_location_count_and_nonfinite_data() -> None:
    first = _bolt("B1", 0.0, 0.0)
    with pytest.raises(ValueError, match="tuple length"):
        GeneralBoltGroup("BG", "I", 1, 2, (first,))
    with pytest.raises(ValueError, match="IDs"):
        GeneralBoltGroup("BG", "I", 1, 2, (first, replace(first, center=PlanarPoint2D(1, 0))))
    with pytest.raises(ValueError, match="locations"):
        GeneralBoltGroup("BG", "I", 1, 2, (first, replace(first, id="B2")))
    with pytest.raises(ValueError, match="finite"):
        PlanarPoint2D(float("nan"), 0)
    with pytest.raises(ValueError, match="finite"):
        PlanarPoint2D(0, float("inf"))


def test_general_geometry_contract_validation_failures() -> None:
    point = PlanarPoint2D(0, 0)
    with pytest.raises(TypeError, match="real"):
        PlanarPoint2D(True, 0)
    with pytest.raises(ValueError, match="positive"):
        GeneralBolt("B", point, 0, 0.563, "A", "C")
    with pytest.raises(ValueError, match="positive"):
        GeneralBolt("B", point, 0.5, -1, "A", "C")
    with pytest.raises(ValueError, match="smaller"):
        GeneralBolt("B", point, 0.5, 0.4, "A", "C")
    with pytest.raises(TypeError, match="PlanarPoint2D"):
        GeneralBolt("B", object(), 0.5, 0.563, "A", "C")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="tuple"):
        GeneralBoltGroup("BG", "I", 1, 1, [_bolt("B", 0, 0)])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="invalid item"):
        GeneralBoltGroup("BG", "I", 1, 1, (object(),))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="integer"):
        GeneralBoltGroup("BG", "I", 1.0, 1, ())  # type: ignore[arg-type]


def test_boundary_and_obstacle_contract_validation() -> None:
    obstacle = RectangularObstacle2D("VOID-1", BoundaryObstacleKind.VOID, -1, 1, -1, 1)
    boundary = PlanarLayerBoundary("L", -2, 2, -2, 2, obstacles=(obstacle,))
    assert boundary.obstacles == (obstacle,)
    with pytest.raises(TypeError, match="kind"):
        RectangularObstacle2D("O", "VOID", -1, 1, -1, 1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="positive"):
        RectangularObstacle2D("O", BoundaryObstacleKind.VOID, 1, 1, -1, 1)
    with pytest.raises(ValueError, match="finite"):
        RectangularObstacle2D("O", BoundaryObstacleKind.VOID, -1, float("inf"), -1, 1)
    with pytest.raises(ValueError, match="positive"):
        PlanarLayerBoundary("L", 0, 0, -1, 1)
    with pytest.raises(TypeError, match="Boolean"):
        PlanarLayerBoundary("L", -1, 1, -1, 1, unloaded_end_is_free=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="tuple"):
        PlanarLayerBoundary("L", -1, 1, -1, 1, obstacles=[obstacle])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="invalid item"):
        PlanarLayerBoundary("L", -1, 1, -1, 1, obstacles=(object(),))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="unique"):
        PlanarLayerBoundary("L", -2, 2, -2, 2, obstacles=(obstacle, obstacle))


def test_row_resolution_uses_signed_force_and_not_array_order() -> None:
    forward = _geometry()
    reverse = _geometry(force=(-1.0, 0.0))

    assert {item.bolt.center.x for item in forward.rows[0].bolts} == {4.0}
    assert {item.bolt.center.x for item in reverse.rows[0].bolts} == {0.0}
    assert forward.unloaded_free_end_u == -4.0
    assert reverse.unloaded_free_end_u == -6.0
    assert forward.sorting_tolerance == 1e-6
    assert [line.id for line in forward.bolt_lines] == ["BOLT_LINE_1", "BOLT_LINE_2"]


def test_rectangular_classification_retains_nonuniformity_and_no_normalization() -> None:
    pitch = _geometry((4.0, 2.0, -1.0))
    gauge = _geometry((4.0, 2.0), ((-2.0, -0.5, 2.0),) * 2)
    staggered = _geometry((4.0, 2.0), ((-1.0, 1.0), (-0.5, 1.5)))
    uneven = _geometry((4.0, 2.0), ((-1.0, 1.0), (0.0,)))
    mixed = _geometry(identities=("A", "B", "A"))

    assert pitch.classification.pitches == (2.0, 3.0)
    assert not pitch.classification.constant_pitch
    assert pitch.classification.pitch_deviation == pytest.approx(0.5)
    assert gauge.classification.gauges == (1.5, 2.5)
    assert not gauge.classification.constant_gauge
    assert gauge.classification.gauge_deviation == pytest.approx(0.5)
    assert not staggered.classification.nonstaggered
    assert not uneven.classification.equal_bolts_per_row
    assert not mixed.classification.same_bolt_identity
    assert not pitch.classification.supports_uniform_rectangular_method


def test_geometry_resolver_rejects_invalid_calls_and_mismatched_physical_data() -> None:
    group = GeneralBoltGroup("BG", "I", 1, 1, (_bolt("B", 0, 0),))
    boundary = PlanarLayerBoundary("L", -1, 1, -1, 1)
    tolerance = MultiRowGeometryTolerance(1e-6)
    with pytest.raises(ValueError, match="positive"):
        MultiRowGeometryTolerance(0)
    with pytest.raises(TypeError, match="group"):
        resolve_multirow_geometry(object(), boundary, (1, 0), tolerance)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="boundary"):
        resolve_multirow_geometry(group, object(), (1, 0), tolerance)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="tolerance"):
        resolve_multirow_geometry(group, boundary, (1, 0), object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="two-value"):
        resolve_multirow_geometry(group, boundary, (1,), tolerance)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="nonzero"):
        resolve_multirow_geometry(group, boundary, (0, 0), tolerance)
    with pytest.raises(ValueError, match="finite"):
        resolve_multirow_geometry(group, boundary, (float("nan"), 0), tolerance)
    outside = GeneralBoltGroup("BG", "I", 1, 1, (_bolt("B", 2, 0),))
    with pytest.raises(ValueError, match="outside"):
        resolve_multirow_geometry(outside, boundary, (1, 0), tolerance)
    wrong_rows = GeneralBoltGroup("BG", "I", 2, 1, (_bolt("B", 0, 0),))
    with pytest.raises(ValueError, match="row count"):
        resolve_multirow_geometry(wrong_rows, boundary, (1, 0), tolerance)
    projected = ProjectedBolt(_bolt("B2", 0, 0), 0, 0)
    assert projected.u == 0
    with pytest.raises(TypeError, match="GeneralBolt"):
        ProjectedBolt(object(), 0, 0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite"):
        ProjectedBolt(_bolt("B3", 0, 0), float("inf"), 0)


@pytest.mark.parametrize(
    ("pair", "row_count", "expected"),
    [
        (ConnectedMaterialPair.FRP_FRP, 2, (Decimal("0.50"), Decimal("0.50"))),
        (ConnectedMaterialPair.FRP_STEEL, 2, (Decimal("0.60"), Decimal("0.40"))),
        (
            ConnectedMaterialPair.FRP_FRP,
            3,
            (Decimal("0.40"), Decimal("0.20"), Decimal("0.40")),
        ),
        (
            ConnectedMaterialPair.FRP_STEEL,
            3,
            (Decimal("0.50"), Decimal("0.30"), Decimal("0.20")),
        ),
    ],
)
def test_prescribed_distributions_are_exact(
    pair: ConnectedMaterialPair,
    row_count: int,
    expected: tuple[Decimal, ...],
) -> None:
    assert prescribed_row_fractions(pair, row_count) == expected


def test_prescribed_distribution_row_and_per_bolt_demands() -> None:
    geometry = _geometry()
    plan = plan_row_demands(
        geometry,
        PhysicalQuantity.of("5", Unit.KIP),
        RowDistributionBasis.ASCE_PRESCRIBED,
        _provenance(),
        connected_materials=ConnectedMaterialPair.FRP_FRP,
    )
    rows = plan.scenarios[0].rows

    assert plan.availability is PlanAvailability.READY
    assert [item.row_id for item in rows] == ["ROW_1", "ROW_2", "ROW_3"]
    assert [item.row_fraction for item in rows] == [Decimal(".4"), Decimal(".2"), Decimal(".4")]
    assert [item.row_demand.magnitude for item in rows] == [
        Decimal("2"),
        Decimal("1"),
        Decimal("2"),
    ]
    assert [item.per_bolt_demands[0].demand.magnitude for item in rows] == [
        Decimal("1"),
        Decimal(".5"),
        Decimal("1"),
    ]
    assert not plan.row_sharing_credit
    assert not plan.friction_credit


def test_frp_steel_three_row_distribution_keeps_row_one_farthest_from_free_end() -> None:
    geometry = _geometry()
    plan = plan_row_demands(
        geometry,
        PhysicalQuantity.of("10", Unit.KIP),
        RowDistributionBasis.ASCE_PRESCRIBED,
        _provenance(),
        connected_materials=ConnectedMaterialPair.FRP_STEEL,
    )
    rows = plan.scenarios[0].rows

    assert geometry.rows[0].id == "ROW_1"
    assert geometry.rows[0].projected_coordinate > geometry.rows[1].projected_coordinate
    assert geometry.rows[1].projected_coordinate > geometry.rows[2].projected_coordinate
    assert geometry.rows[2].projected_coordinate > geometry.unloaded_free_end_u
    assert [item.row_id for item in rows] == ["ROW_1", "ROW_2", "ROW_3"]
    assert [item.row_fraction for item in rows] == [
        Decimal("0.50"),
        Decimal("0.30"),
        Decimal("0.20"),
    ]
    assert [item.row_demand.magnitude for item in rows] == [
        Decimal("5"),
        Decimal("3"),
        Decimal("2"),
    ]


def test_prescribed_distribution_enforces_prerequisites_and_arguments() -> None:
    nonuniform = _geometry((4.0, 2.0, -1.0))
    plan = plan_row_demands(
        nonuniform,
        PhysicalQuantity.of("5", Unit.KIP),
        RowDistributionBasis.ASCE_PRESCRIBED,
        _provenance(),
        connected_materials=ConnectedMaterialPair.FRP_FRP,
    )
    assert plan.availability is PlanAvailability.CALCULATION_NOT_SUPPORTED
    assert plan.scenarios == ()
    with pytest.raises(ValueError, match="connected_materials"):
        plan_row_demands(
            _geometry(),
            PhysicalQuantity.of("5", Unit.KIP),
            RowDistributionBasis.ASCE_PRESCRIBED,
            _provenance(),
        )
    with pytest.raises(ValueError, match="mixed"):
        plan_row_demands(
            _geometry(),
            PhysicalQuantity.of("5", Unit.KIP),
            RowDistributionBasis.ASCE_PRESCRIBED,
            _provenance(),
            connected_materials=ConnectedMaterialPair.FRP_FRP,
            engineer_fractions=(EngineerRowFraction("ROW_1", Decimal(1)),),
        )
    with pytest.raises(ValueError, match="No prescribed"):
        prescribed_row_fractions(ConnectedMaterialPair.FRP_FRP, 4)
    with pytest.raises(TypeError, match="material_pair"):
        prescribed_row_fractions("FRP_FRP", 2)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="row_count"):
        prescribed_row_fractions(ConnectedMaterialPair.FRP_FRP, True)


def test_conservative_full_row_envelope_uses_full_demand_for_each_physical_row() -> None:
    geometry = _geometry((4.0, 2.0), ((-1.0, 1.0), (0.0,)))
    plan = plan_row_demands(
        geometry,
        PhysicalQuantity.of("6", Unit.KIP),
        RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
        _provenance(),
    )

    assert [scenario.controlling_row_id for scenario in plan.scenarios] == ["ROW_1", "ROW_2"]
    assert all(scenario.rows[0].row_demand.magnitude == Decimal(6) for scenario in plan.scenarios)
    assert [len(item.rows[0].per_bolt_demands) for item in plan.scenarios] == [2, 1]
    assert [item.rows[0].per_bolt_demands[0].demand.magnitude for item in plan.scenarios] == [
        Decimal(3),
        Decimal(6),
    ]
    assert plan.warnings[0].code is MultiRowWarningCode.CONSERVATIVE_FULL_ROW_ENVELOPE_USED
    assert not plan.row_sharing_credit
    assert not plan.friction_credit


def test_engineer_defined_fraction_and_direct_force_plans_retain_provenance() -> None:
    geometry = _geometry()
    fractions = tuple(
        EngineerRowFraction(row_id, value)
        for row_id, value in zip(
            ("ROW_3", "ROW_1", "ROW_2"),
            (Decimal(".5"), Decimal(".25"), Decimal(".25")),
            strict=True,
        )
    )
    provenance = _provenance(reference=None)
    fraction_plan = plan_row_demands(
        geometry,
        PhysicalQuantity.of("8", Unit.KIP),
        RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
        provenance,
        engineer_fractions=fractions,
    )
    direct_plan = plan_row_demands(
        geometry,
        PhysicalQuantity.of("8", Unit.KIP),
        RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
        _provenance(),
        engineer_forces=(
            EngineerRowForce("ROW_2", PhysicalQuantity.of("2", Unit.KIP)),
            EngineerRowForce("ROW_3", PhysicalQuantity.of("4", Unit.KIP)),
            EngineerRowForce("ROW_1", PhysicalQuantity.of("2", Unit.KIP)),
        ),
    )

    assert [item.row_fraction for item in fraction_plan.scenarios[0].rows] == [
        Decimal(".25"),
        Decimal(".25"),
        Decimal(".5"),
    ]
    assert [item.row_demand.magnitude for item in direct_plan.scenarios[0].rows] == [
        Decimal(2),
        Decimal(2),
        Decimal(4),
    ]
    assert fraction_plan.provenance is provenance
    assert provenance.support_reference_trace == "OPTIONAL_SUPPORT_REFERENCE_NOT_SUPPLIED"
    assert direct_plan.provenance.support_reference_trace == "support_reference:CALC-1"


def test_engineer_defined_distribution_validation() -> None:
    geometry = _geometry()
    total = PhysicalQuantity.of("8", Unit.KIP)
    base = (EngineerRowFraction("ROW_1", Decimal(".4")),)
    with pytest.raises(ValueError, match="exactly one"):
        plan_row_demands(
            geometry,
            total,
            RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
            _provenance(),
        )
    with pytest.raises(ValueError, match="exactly one"):
        plan_row_demands(
            geometry,
            total,
            RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
            _provenance(),
            engineer_fractions=base,
            engineer_forces=(EngineerRowForce("ROW_1", total),),
        )
    with pytest.raises(ValueError, match="unique"):
        plan_row_demands(
            geometry,
            total,
            RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
            _provenance(),
            engineer_fractions=(
                EngineerRowFraction("ROW_1", Decimal(".5")),
                EngineerRowFraction("ROW_1", Decimal(".5")),
            ),
        )
    with pytest.raises(ValueError, match="every physical row"):
        plan_row_demands(
            geometry,
            total,
            RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
            _provenance(),
            engineer_fractions=base,
        )
    with pytest.raises(ValueError, match="balance to one"):
        plan_row_demands(
            geometry,
            total,
            RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
            _provenance(),
            engineer_fractions=tuple(
                EngineerRowFraction(row.id, Decimal(".2")) for row in geometry.rows
            ),
        )
    with pytest.raises(ValueError, match="balance the total"):
        plan_row_demands(
            geometry,
            total,
            RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
            _provenance(),
            engineer_forces=tuple(
                EngineerRowForce(row.id, PhysicalQuantity.of("1", Unit.KIP))
                for row in geometry.rows
            ),
        )
    tolerant = plan_row_demands(
        geometry,
        total,
        RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
        _provenance(),
        engineer_fractions=(
            EngineerRowFraction("ROW_1", Decimal(".333333333333")),
            EngineerRowFraction("ROW_2", Decimal(".333333333333")),
            EngineerRowFraction("ROW_3", Decimal(".333333333333")),
        ),
        fraction_tolerance=Decimal(".00000000001"),
    )
    assert tolerant.availability is PlanAvailability.READY


def test_demand_contract_validation_rejects_wrong_types_and_values() -> None:
    geometry = _geometry()
    force = PhysicalQuantity.of("1", Unit.KIP)
    with pytest.raises(TypeError, match="MultiRowWarningCode"):
        MultiRowWarning("warning", "label")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="nonempty"):
        MultiRowWarning(MultiRowWarningCode.CONSERVATIVE_FULL_ROW_ENVELOPE_USED, "")
    with pytest.raises(ValueError, match="nonempty"):
        MethodProvenance("")
    with pytest.raises(TypeError, match="Boolean"):
        MethodProvenance("x", engineer_confirmed=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Boolean or None"):
        MethodProvenance("x", clearance_or_contact_modeled=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="negative"):
        EngineerRowFraction("ROW_1", Decimal("-1"))
    with pytest.raises(ValueError, match="row_id"):
        EngineerRowFraction("", Decimal(1))
    with pytest.raises(ValueError, match="negative"):
        EngineerRowForce("ROW_1", PhysicalQuantity.of("-1", Unit.KIP))
    with pytest.raises(ValueError, match="row_id"):
        EngineerRowForce("", PhysicalQuantity.of("1", Unit.KIP))
    with pytest.raises(ValueError, match="force"):
        EngineerRowForce("ROW_1", PhysicalQuantity.of("1", Unit.IN))
    with pytest.raises(TypeError, match="geometry"):
        plan_row_demands(
            object(),  # type: ignore[arg-type]
            force,
            RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
            _provenance(),
        )
    with pytest.raises(ValueError, match="force"):
        plan_row_demands(
            geometry,
            PhysicalQuantity.of("1", Unit.IN),
            RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
            _provenance(),
        )
    with pytest.raises(ValueError, match="negative"):
        plan_row_demands(
            geometry,
            PhysicalQuantity.of("-1", Unit.KIP),
            RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
            _provenance(),
        )
    with pytest.raises(TypeError, match="basis"):
        plan_row_demands(geometry, force, "x", _provenance())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="provenance"):
        plan_row_demands(
            geometry,
            force,
            RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
            object(),  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="positive"):
        plan_row_demands(
            geometry,
            force,
            RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
            _provenance(),
            fraction_tolerance=Decimal(0),
        )
    with pytest.raises(ValueError, match="cannot be negative"):
        plan_row_demands(
            geometry,
            force,
            RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
            _provenance(),
            force_tolerance=PhysicalQuantity.of("-1", Unit.N),
        )
    with pytest.raises(ValueError, match="only used"):
        plan_row_demands(
            geometry,
            force,
            RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
            _provenance(),
            connected_materials=ConnectedMaterialPair.FRP_FRP,
        )
    with pytest.raises(ValueError, match="mixed with the row envelope"):
        plan_row_demands(
            geometry,
            force,
            RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
            _provenance(),
            engineer_fractions=(EngineerRowFraction("ROW_1", Decimal(1)),),
        )


def test_first_row_geometry_maps_e1_side_caps_gauge_width_and_identity() -> None:
    one = _geometry((4.0, 2.0), ((0.0,), (0.0,)))
    two = _geometry((4.0, 2.0))
    three = _geometry((4.0, 2.0), ((-2.0, 0.0, 2.0),) * 2)
    one_mapping = _first_row(one)
    two_mapping = _first_row(two, MaterialDirection.TRANSVERSE)
    three_mapping = _first_row(three, element=PultrudedElementClassification.PLATE)

    assert one_mapping.e1 == PhysicalQuantity.of("2", Unit.IN)
    assert one_mapping.raw_e3 == PhysicalQuantity.of("3", Unit.IN)
    assert one_mapping.raw_e4 == PhysicalQuantity.of("3", Unit.IN)
    assert one_mapping.e3_cap == PhysicalQuantity.of("1.5", Unit.IN)
    assert one_mapping.effective_width == PhysicalQuantity.of("6", Unit.IN)
    assert two_mapping.gauge == PhysicalQuantity.of("2", Unit.IN)
    assert two_mapping.effective_width == PhysicalQuantity.of("6", Unit.IN)
    assert three_mapping.effective_width == PhysicalQuantity.of("6", Unit.IN)
    assert two_mapping.material_direction is MaterialDirection.TRANSVERSE
    assert three_mapping.element_classification is PultrudedElementClassification.PLATE
    assert one_mapping.source_authority == "CANONICAL_PHYSICAL_GEOMETRY"
    assert "ROW_1" in one_mapping.source_geometry_ids


def test_first_row_side_cap_branches_and_nb4_unsupported() -> None:
    one_near = _geometry(
        (4.0, 2.0),
        ((0.0,), (0.0,)),
        boundary=PlanarLayerBoundary("L", -2, 6, -1, 4),
    )
    both_far = _geometry(
        (4.0, 2.0),
        ((0.0,), (0.0,)),
        boundary=PlanarLayerBoundary("L", -2, 6, -4, 5),
    )
    unequal_uncapped = _geometry(
        (4.0, 2.0),
        ((0.0,), (0.0,)),
        boundary=PlanarLayerBoundary("L", -2, 6, -1, 1.2),
    )
    nb4 = _geometry((4.0, 2.0), ((-3.0, -1.0, 1.0, 3.0),) * 2)

    first = _first_row(one_near)
    second = _first_row(both_far)
    third = _first_row(unequal_uncapped)
    fourth = _first_row(nb4)
    assert {first.effective_e3, first.effective_e4} == {
        PhysicalQuantity.of("1", Unit.IN),
        PhysicalQuantity.of("1.5", Unit.IN),
    }
    assert second.effective_e3 == second.e3_cap
    assert second.effective_e4 == second.e4_cap
    assert third.width_status is EffectiveWidthStatus.CALCULATION_NOT_SUPPORTED
    assert third.effective_width is None
    assert fourth.bolts_per_row == 4
    assert fourth.width_status is EffectiveWidthStatus.CALCULATION_NOT_SUPPORTED


def test_first_row_geometry_rejects_invalid_inputs() -> None:
    geometry = _geometry()
    with pytest.raises(TypeError, match="geometry"):
        resolve_first_row_geometry(
            object(),  # type: ignore[arg-type]
            Unit.IN,
            PhysicalQuantity.of(".5", Unit.IN),
            MaterialDirection.LONGITUDINAL,
            PultrudedElementClassification.SHAPE,
        )
    with pytest.raises(ValueError, match="IN or MM"):
        resolve_first_row_geometry(
            geometry,
            Unit.KIP,
            PhysicalQuantity.of(".5", Unit.IN),
            MaterialDirection.LONGITUDINAL,
            PultrudedElementClassification.SHAPE,
        )
    with pytest.raises(ValueError, match="positive length"):
        resolve_first_row_geometry(
            geometry,
            Unit.IN,
            PhysicalQuantity.of("0", Unit.IN),
            MaterialDirection.LONGITUDINAL,
            PultrudedElementClassification.SHAPE,
        )
    with pytest.raises(TypeError, match="MaterialDirection"):
        resolve_first_row_geometry(
            geometry,
            Unit.IN,
            PhysicalQuantity.of(".5", Unit.IN),
            "L",  # type: ignore[arg-type]
            PultrudedElementClassification.SHAPE,
        )
    with pytest.raises(TypeError, match="PultrudedElementClassification"):
        resolve_first_row_geometry(
            geometry,
            Unit.IN,
            PhysicalQuantity.of(".5", Unit.IN),
            MaterialDirection.LONGITUDINAL,
            "shape",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("direction", "element", "expected_c", "warning"),
    [
        (MaterialDirection.LONGITUDINAL, PultrudedElementClassification.SHAPE, Decimal(".5"), None),
        (MaterialDirection.LONGITUDINAL, PultrudedElementClassification.PLATE, Decimal(".4"), None),
        (MaterialDirection.TRANSVERSE, PultrudedElementClassification.SHAPE, Decimal(".5"), None),
        (
            MaterialDirection.TRANSVERSE,
            PultrudedElementClassification.PLATE,
            Decimal(".5"),
            MultiRowWarningCode.ASCE_SOURCE_CONFLICT_CONSERVATIVE_INTERPRETATION,
        ),
    ],
)
def test_first_row_plan_types_retain_raw_inputs_without_resistance(
    direction: MaterialDirection,
    element: PultrudedElementClassification,
    expected_c: Decimal,
    warning: MultiRowWarningCode | None,
) -> None:
    mapping = _first_row(_geometry((4.0, 2.0)), direction, element)
    plans = build_first_row_net_tension_plans(
        mapping,
        PhysicalQuantity.of(".375", Unit.IN),
        PhysicalQuantity.of("33", Unit.KSI),
        PhysicalQuantity.of(".626", Unit.IN),
        prescribed_lbr=Decimal(".5"),
    )

    assert [item.method for item in plans] == [
        FirstRowPlanMethod.ASCE_STANDARD_SIMPLIFIED,
        FirstRowPlanMethod.ASCE_COMMENTARY_FULL,
        FirstRowPlanMethod.RATIONAL_MULTIROW_LOWER_ENVELOPE,
    ]
    assert plans[0].equation_locator.endswith("8-10 or 8-11")
    assert plans[0].phi == (
        Decimal(".5") if direction is MaterialDirection.LONGITUDINAL else Decimal(".45")
    )
    assert plans[1].coefficient_inputs is not None
    assert plans[1].coefficient_inputs.coefficient_c_i == expected_c
    assert (
        plans[1].coefficient_inputs.execution_status is DeferredExecutionStatus.DEFERRED_STAGE_2_4B
    )
    assert plans[1].lbr == Decimal(".5")
    assert plans[2].availability is PlanAvailability.NOT_APPLICABLE
    assert all(
        item.execution_status is DeferredExecutionStatus.DEFERRED_STAGE_2_4B for item in plans
    )
    assert "resistance" not in {field.name for field in fields(type(plans[0]))}
    warning_codes = {item.code for item in plans[1].warnings}
    assert (warning in warning_codes) if warning is not None else not warning_codes
    if warning is not None:
        assert len(plans[1].coefficient_inputs.source_locators) == 2


def test_more_than_three_row_lower_envelope_and_nb4_partial_support() -> None:
    rows5 = _geometry((8.0, 6.0, 4.0, 2.0, 0.0))
    mapping = _first_row(rows5)
    plans = build_first_row_net_tension_plans(
        mapping,
        PhysicalQuantity.of(".375", Unit.IN),
        PhysicalQuantity.of("33", Unit.KSI),
        PhysicalQuantity.of(".626", Unit.IN),
    )
    rational = plans[2]

    assert (
        plans[0].method_applicability
        is MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE
    )
    assert rational.availability is PlanAvailability.READY
    assert rational.unknown_lbr_envelope is not None
    assert (
        rational.unknown_lbr_envelope.execution_status
        is DeferredExecutionStatus.DEFERRED_STAGE_2_4B
    )
    assert rational.qualification is QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    assert rational.warnings[0].code is MultiRowWarningCode.ASCE_PRESCRIPTIVE_ROW_LIMIT_EXCEEDED

    nb4 = _first_row(_geometry((4.0, 2.0), ((-3.0, -1.0, 1.0, 3.0),) * 2))
    nb4_plans = build_first_row_net_tension_plans(
        nb4,
        PhysicalQuantity.of(".375", Unit.IN),
        PhysicalQuantity.of("33", Unit.KSI),
        PhysicalQuantity.of(".626", Unit.IN),
    )
    assert all(item.availability is not PlanAvailability.READY for item in nb4_plans)
    assert nb4_plans[1].coefficient_inputs is None


def test_first_row_plan_input_validation() -> None:
    mapping = _first_row(_geometry())
    thickness = PhysicalQuantity.of(".375", Unit.IN)
    strength = PhysicalQuantity.of("33", Unit.KSI)
    hole = PhysicalQuantity.of(".626", Unit.IN)
    with pytest.raises(TypeError, match="FirstRowGeometryMapping"):
        build_first_row_net_tension_plans(object(), thickness, strength, hole)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="thickness"):
        build_first_row_net_tension_plans(
            mapping, PhysicalQuantity.of("0", Unit.IN), strength, hole
        )
    with pytest.raises(ValueError, match="tensile_strength"):
        build_first_row_net_tension_plans(
            mapping, thickness, PhysicalQuantity.of("1", Unit.IN), hole
        )
    with pytest.raises(ValueError, match="net_hole"):
        build_first_row_net_tension_plans(
            mapping, thickness, strength, PhysicalQuantity.of("0", Unit.IN)
        )
    with pytest.raises(ValueError, match="between"):
        build_first_row_net_tension_plans(
            mapping, thickness, strength, hole, prescribed_lbr=Decimal("1.1")
        )


@pytest.mark.parametrize(
    ("coordinates", "expected_method"),
    [
        ((4.0, 2.0), InterrowShearOutMethod.ASCE_EQ_8_12),
        ((4.0, 2.0, 0.0), InterrowShearOutMethod.ASCE_EQ_8_13),
        ((8.0, 6.0, 4.0, 2.0, 0.0), InterrowShearOutMethod.RATIONAL_EXTENSION_EQ_8_13),
    ],
)
def test_shear_out_plans_per_line_and_actual_row_span(
    coordinates: tuple[float, ...],
    expected_method: InterrowShearOutMethod,
) -> None:
    geometry = _geometry(coordinates)
    plans = build_interrow_shear_out_plans(
        geometry,
        Unit.IN,
        PhysicalQuantity.of(".375", Unit.IN),
        PhysicalQuantity.of("8", Unit.KSI),
        PhysicalQuantity.of("6", Unit.KIP),
        ("lambda:1", "phi:.45"),
    )

    assert len(plans) == 2
    assert all(item.method is expected_method for item in plans)
    assert all(item.per_line_demand == PhysicalQuantity.of("3", Unit.KIP) for item in plans)
    assert plans[0].row_span == PhysicalQuantity.of(str(2 * (len(coordinates) - 1)), Unit.IN)
    assert all(
        item.execution_status is DeferredExecutionStatus.DEFERRED_STAGE_2_4B for item in plans
    )
    assert "resistance" not in {field.name for field in fields(type(plans[0]))}
    if len(coordinates) > 3:
        assert plans[0].warnings[0].code is MultiRowWarningCode.RATIONAL_EQ_8_13_EXTENSION_USED


def test_variable_pitch_is_retained_and_direct_method_fails_closed() -> None:
    variable = _geometry((4.0, 2.0, -1.0))
    plans = build_interrow_shear_out_plans(
        variable,
        Unit.IN,
        PhysicalQuantity.of(".375", Unit.IN),
        PhysicalQuantity.of("8", Unit.KSI),
        PhysicalQuantity.of("6", Unit.KIP),
        (),
    )
    assert [item.magnitude for item in plans[0].pitches] == [Decimal(2), Decimal(3)]
    assert plans[0].availability is PlanAvailability.CALCULATION_NOT_SUPPORTED
    assert plans[0].qualification is QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED


def test_shear_out_plan_validation_and_single_row_partial_plan() -> None:
    geometry = _geometry((0.0,), ((0.0,),))
    plans = build_interrow_shear_out_plans(
        geometry,
        Unit.IN,
        PhysicalQuantity.of(".375", Unit.IN),
        PhysicalQuantity.of("8", Unit.KSI),
        PhysicalQuantity.of("0", Unit.KIP),
        (),
    )
    assert len(plans) == 1
    assert plans[0].availability is PlanAvailability.CALCULATION_NOT_SUPPORTED
    assert (
        build_interrow_shear_out_plans(
            replace(geometry, bolt_lines=()),
            Unit.IN,
            PhysicalQuantity.of(".375", Unit.IN),
            PhysicalQuantity.of("8", Unit.KSI),
            PhysicalQuantity.of("0", Unit.KIP),
            (),
        )
        == ()
    )
    with pytest.raises(ValueError, match="IN or MM"):
        build_interrow_shear_out_plans(
            geometry,
            Unit.KIP,
            PhysicalQuantity.of(".375", Unit.IN),
            PhysicalQuantity.of("8", Unit.KSI),
            PhysicalQuantity.of("1", Unit.KIP),
            (),
        )
    with pytest.raises(ValueError, match="thickness"):
        build_interrow_shear_out_plans(
            geometry,
            Unit.IN,
            PhysicalQuantity.of("0", Unit.IN),
            PhysicalQuantity.of("8", Unit.KSI),
            PhysicalQuantity.of("1", Unit.KIP),
            (),
        )
    with pytest.raises(ValueError, match="shear_strength"):
        build_interrow_shear_out_plans(
            geometry,
            Unit.IN,
            PhysicalQuantity.of(".375", Unit.IN),
            PhysicalQuantity.of("1", Unit.IN),
            PhysicalQuantity.of("1", Unit.KIP),
            (),
        )
    with pytest.raises(ValueError, match="force"):
        build_interrow_shear_out_plans(
            geometry,
            Unit.IN,
            PhysicalQuantity.of(".375", Unit.IN),
            PhysicalQuantity.of("8", Unit.KSI),
            PhysicalQuantity.of("1", Unit.IN),
            (),
        )
    with pytest.raises(ValueError, match="negative"):
        build_interrow_shear_out_plans(
            geometry,
            Unit.IN,
            PhysicalQuantity.of(".375", Unit.IN),
            PhysicalQuantity.of("8", Unit.KSI),
            PhysicalQuantity.of("-1", Unit.KIP),
            (),
        )


def test_applicability_keeps_independent_status_dimensions() -> None:
    four = _geometry((6.0, 4.0, 2.0, 0.0))
    status = assess_multirow_applicability(
        four,
        _first_row(four),
        RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
    )
    assert status.geometry_status is GeometryStatus.VALID
    assert status.availability is PlanAvailability.READY
    assert (
        status.method_applicability
        is MultiRowMethodApplicability.CALCULATED_OUTSIDE_PRESCRIPTIVE_SCOPE
    )
    assert status.qualification is QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED
    assert status.numerical_comparison is MultiRowNumericalComparison.NOT_EVALUATED
    assert (
        aggregate_multirow_status((status,))
        is MultiRowAggregateStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED
    )

    nb4 = _geometry((4.0, 2.0), ((-3.0, -1.0, 1.0, 3.0),) * 2)
    nb4_status = assess_multirow_applicability(
        nb4,
        _first_row(nb4),
        RowDistributionBasis.ENGINEER_DEFINED_ROW_DISTRIBUTION,
    )
    assert nb4_status.geometry_status is GeometryStatus.VALID
    assert nb4_status.first_row_availability is PlanAvailability.CALCULATION_NOT_SUPPORTED
    assert (
        nb4_status.method_applicability
        is MultiRowMethodApplicability.ENGINEER_DEFINED_METHOD_OUTSIDE_PRESCRIPTIVE_SCOPE
    )

    staggered = _geometry((4.0, 2.0), ((-1.0, 1.0), (-0.5, 1.5)))
    staggered_status = assess_multirow_applicability(
        staggered,
        _first_row(staggered),
        RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
    )
    assert staggered_status.availability is PlanAvailability.CALCULATION_NOT_SUPPORTED
    with pytest.raises(TypeError, match="demand_basis"):
        assess_multirow_applicability(four, _first_row(four), "x")  # type: ignore[arg-type]


def _status(
    *,
    geometry: GeometryStatus = GeometryStatus.VALID,
    availability: PlanAvailability = PlanAvailability.READY,
    qualification: QualificationDisposition = QualificationDisposition.QUALIFIED_ASCE_PRESCRIPTIVE,
    numerical: MultiRowNumericalComparison = MultiRowNumericalComparison.NOT_EVALUATED,
) -> MultiRowApplicability:
    return MultiRowApplicability(
        geometry,
        availability,
        PlanAvailability.READY,
        MultiRowMethodApplicability.ASCE_PRESCRIPTIVE,
        qualification,
        numerical,
        (),
    )


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ((), MultiRowAggregateStatus.INCOMPLETE_OR_UNSUPPORTED),
        (
            (_status(geometry=GeometryStatus.INVALID_GEOMETRY),),
            MultiRowAggregateStatus.INVALID_GEOMETRY,
        ),
        ((_status(numerical=MultiRowNumericalComparison.FAIL),), MultiRowAggregateStatus.FAIL),
        (
            (_status(availability=PlanAvailability.INCOMPLETE_INPUT),),
            MultiRowAggregateStatus.INCOMPLETE_OR_UNSUPPORTED,
        ),
        (
            (_status(availability=PlanAvailability.SOURCE_DATA_PENDING),),
            MultiRowAggregateStatus.INCOMPLETE_OR_UNSUPPORTED,
        ),
        (
            (_status(availability=PlanAvailability.CALCULATION_NOT_SUPPORTED),),
            MultiRowAggregateStatus.INCOMPLETE_OR_UNSUPPORTED,
        ),
        (
            (_status(availability=PlanAvailability.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED),),
            MultiRowAggregateStatus.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED,
        ),
        (
            (_status(qualification=QualificationDisposition.SECTION_2_3_2_QUALIFICATION_REQUIRED),),
            MultiRowAggregateStatus.SECTION_2_3_2_QUALIFICATION_REQUIRED,
        ),
        (
            (_status(qualification=QualificationDisposition.ENGINEERING_REVIEW_REQUIRED),),
            MultiRowAggregateStatus.ENGINEERING_REVIEW_REQUIRED,
        ),
        ((_status(numerical=MultiRowNumericalComparison.PASS),), MultiRowAggregateStatus.PASS),
        ((_status(),), MultiRowAggregateStatus.NOT_EVALUATED),
    ],
)
def test_aggregate_status_hierarchy_is_deterministic(
    statuses: tuple[MultiRowApplicability, ...],
    expected: MultiRowAggregateStatus,
) -> None:
    assert aggregate_multirow_status(statuses) is expected


def test_block_path_resolver_retains_u_l_rejections_and_deterministic_ids() -> None:
    geometry = _geometry()
    result = resolve_block_shear_paths(geometry)
    accepted = result.accepted
    rejected = result.rejected

    assert [item.family for item in accepted] == [
        BlockPathFamily.U,
        BlockPathFamily.L_LEFT,
        BlockPathFamily.L_RIGHT,
    ]
    assert all(item.row_id == "ROW_1" for item in accepted)
    assert {BlockPathRejectionReason.INTERMEDIATE_ROW_TENSION_PLANE} == {
        reason
        for item in rejected
        for reason in item.rejection_reasons
        if reason is BlockPathRejectionReason.INTERMEDIATE_ROW_TENSION_PLANE
    }
    assert [item.id for item in result.candidates] == [
        item.id for item in resolve_block_shear_paths(geometry).candidates
    ]


def test_block_path_requires_real_free_boundary_and_rejects_bridging_bolts() -> None:
    closed = _geometry(
        boundary=PlanarLayerBoundary(
            "L",
            -4,
            6,
            -3,
            3,
            unloaded_end_is_free=False,
            negative_side_is_free=False,
            positive_side_is_free=False,
        )
    )
    assert all(
        BlockPathRejectionReason.NO_FREE_BOUNDARY_CLOSURE in item.rejection_reasons
        for item in resolve_block_shear_paths(closed).candidates
    )
    three_lines = _geometry((4.0, 2.0), ((-2.0, 0.0, 2.0),) * 2)
    candidates = resolve_block_shear_paths(three_lines).candidates
    assert any(
        BlockPathRejectionReason.BRIDGING_BOLT in item.rejection_reasons for item in candidates
    )
    assert any(item.accepted and item.family is BlockPathFamily.U for item in candidates)


@pytest.mark.parametrize(
    ("kind", "reason"),
    [
        (BoundaryObstacleKind.VOID, BlockPathRejectionReason.VOID_CROSSING),
        (BoundaryObstacleKind.DEFERRED_HEEL, BlockPathRejectionReason.DEFERRED_HEEL_CROSSING),
        (
            BoundaryObstacleKind.DEFERRED_JUNCTION,
            BlockPathRejectionReason.DEFERRED_JUNCTION_CROSSING,
        ),
        (BoundaryObstacleKind.DEFERRED_CORNER, BlockPathRejectionReason.DEFERRED_CORNER_CROSSING),
    ],
)
def test_block_path_rejects_each_excluded_region(
    kind: BoundaryObstacleKind,
    reason: BlockPathRejectionReason,
) -> None:
    obstacle = RectangularObstacle2D("O", kind, -3.5, -2.5, -1.1, -0.9)
    geometry = _geometry(boundary=PlanarLayerBoundary("L", -4, 6, -3, 3, obstacles=(obstacle,)))
    assert any(
        reason in item.rejection_reasons for item in resolve_block_shear_paths(geometry).candidates
    )


def test_manual_block_candidate_validation_rejects_boundary_self_intersection_and_zero_length() -> (
    None
):
    geometry = _geometry()
    crossing = BlockShearCandidatePath(
        "CROSS",
        BlockPathFamily.U,
        "ROW_1",
        (
            BlockPathSegment(
                BlockPathSegmentKind.SHEAR, ProjectedPoint2D(-1, -1), ProjectedPoint2D(1, 1)
            ),
            BlockPathSegment(
                BlockPathSegmentKind.TENSION, ProjectedPoint2D(-1, 1), ProjectedPoint2D(1, -1)
            ),
            BlockPathSegment(
                BlockPathSegmentKind.SHEAR, ProjectedPoint2D(10, 0), ProjectedPoint2D(10, 0)
            ),
        ),
        (),
        (),
        (),
    )
    validated = validate_block_shear_candidate(crossing, geometry)
    assert BlockPathRejectionReason.SELF_INTERSECTION in validated.rejection_reasons
    assert BlockPathRejectionReason.PHYSICAL_BOUNDARY_CROSSING in validated.rejection_reasons
    assert BlockPathRejectionReason.NONPOSITIVE_NET_LENGTH in validated.rejection_reasons
    with pytest.raises(TypeError, match="candidate"):
        validate_block_shear_candidate(object(), geometry)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="geometry"):
        validate_block_shear_candidate(crossing, object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="geometry"):
        resolve_block_shear_paths(object())  # type: ignore[arg-type]


def test_block_candidate_prevents_double_deduction_category() -> None:
    geometry = _geometry()
    candidate = BlockShearCandidatePath(
        "DUP",
        BlockPathFamily.L_LEFT,
        "ROW_1",
        (
            BlockPathSegment(
                BlockPathSegmentKind.SHEAR, ProjectedPoint2D(-1, 0), ProjectedPoint2D(1, 0)
            ),
        ),
        ("B_X4_Y-1",),
        ("B_X4_Y-1",),
        (),
    )
    with pytest.raises(ValueError, match="more than one deduction"):
        validate_block_shear_candidate(candidate, geometry)


def _fingerprint_input(
    geometry: MultiRowGeometry,
    *,
    plan_set: MultiRowCalculationPlanSet,
) -> MultiRowFingerprintInput:
    return MultiRowFingerprintInput(
        "ASCE/SEI 74-23",
        "2023",
        "Erratum 1",
        "FRP_MASTER_CONNECTION_CALCULATION_SLICE_2_ENGINEERING_SPECIFICATION_RC1",
        "frp-master-connection-calculation-slice-2-golden-rc1",
        "project-schema.dev1",
        "multirow-plan-contract.dev1",
        "0.1.0.dev1",
        "asce74-23-ch8-single-bolt-rc2.dev1",
        geometry,
        ("MAT-1",),
        plan_set,
        {"paths": plan_set.block_shear_plan_ids},
        {"lambda": Decimal(1)},
        {"source": "controlled RC1"},
    )


def test_multirow_fingerprint_is_deterministic_unit_equivalent_and_excludes_presentation() -> None:
    geometry = _geometry(reverse_array=True)
    demand = plan_row_demands(
        geometry,
        PhysicalQuantity.of("5", Unit.KIP),
        RowDistributionBasis.ASCE_PRESCRIBED,
        _provenance(),
        connected_materials=ConnectedMaterialPair.FRP_FRP,
    )
    first = _first_row(geometry)
    plans = build_first_row_net_tension_plans(
        first,
        PhysicalQuantity.of(".375", Unit.IN),
        PhysicalQuantity.of("33", Unit.KSI),
        PhysicalQuantity.of(".626", Unit.IN),
        prescribed_lbr=Decimal(".4"),
    )
    shear = build_interrow_shear_out_plans(
        geometry,
        Unit.IN,
        PhysicalQuantity.of(".375", Unit.IN),
        PhysicalQuantity.of("8", Unit.KSI),
        PhysicalQuantity.of("5", Unit.KIP),
        (),
    )
    applicability = assess_multirow_applicability(
        geometry,
        first,
        RowDistributionBasis.ASCE_PRESCRIBED,
    )
    plan_set = MultiRowCalculationPlanSet(demand, applicability, plans, shear, ("BLOCK_U",))
    calculation_input = _fingerprint_input(geometry, plan_set=plan_set)
    envelope_us = MultiRowFingerprintEnvelope(
        calculation_input, "US", "3", {"eye": 1}, "row1", 25, "now"
    )
    envelope_si = MultiRowFingerprintEnvelope(
        calculation_input, "SI", "6", {"eye": 9}, "row2", 100, "later"
    )

    first_hash = multirow_plan_fingerprint(envelope_us)
    assert first_hash == multirow_plan_fingerprint(envelope_si)
    assert first_hash == multirow_plan_fingerprint(calculation_input)
    assert len(first_hash) == 64
    content = canonical_multirow_fingerprint_json(envelope_us)
    assert "display_unit_profile" not in content
    assert "camera_state" not in content
    assert "0.1.0.dev1" in content
    assert content == canonical_multirow_fingerprint_json(envelope_si)


def test_fingerprint_is_array_order_independent_for_physical_bolts() -> None:
    forward = _geometry()
    reversed_geometry = _geometry(reverse_array=True)
    assert [bolt.id for bolt in forward.group.bolts] != [
        bolt.id for bolt in reversed_geometry.group.bolts
    ]

    def plan_set(geometry: MultiRowGeometry) -> MultiRowCalculationPlanSet:
        demand = plan_row_demands(
            geometry,
            PhysicalQuantity.of("5", Unit.KIP),
            RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
            _provenance(),
        )
        first = _first_row(geometry)
        applicability = assess_multirow_applicability(
            geometry,
            first,
            RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
        )
        return MultiRowCalculationPlanSet(demand, applicability, (), (), ())

    assert multirow_plan_fingerprint(
        _fingerprint_input(forward, plan_set=plan_set(forward))
    ) == multirow_plan_fingerprint(
        _fingerprint_input(reversed_geometry, plan_set=plan_set(reversed_geometry))
    )


def test_fingerprint_validation_rejects_invalid_inputs_and_unsupported_payloads() -> None:
    geometry = _geometry()
    plan = plan_row_demands(
        geometry,
        PhysicalQuantity.of("1", Unit.KIP),
        RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
        _provenance(),
    )
    applicability = assess_multirow_applicability(
        geometry,
        _first_row(geometry),
        RowDistributionBasis.CONSERVATIVE_FULL_ROW_ENVELOPE,
    )
    plan_set = MultiRowCalculationPlanSet(plan, applicability, (), (), ())
    with pytest.raises(ValueError, match="nonempty"):
        replace(_fingerprint_input(geometry, plan_set=plan_set), standard="")
    with pytest.raises(TypeError, match="requires"):
        canonical_multirow_fingerprint_json(object())  # type: ignore[arg-type]
    invalid = replace(_fingerprint_input(geometry, plan_set=plan_set), source_metadata={1: "x"})
    with pytest.raises(TypeError, match="keys"):
        canonical_multirow_fingerprint_json(invalid)
    unsupported = replace(_fingerprint_input(geometry, plan_set=plan_set), source_metadata=object())
    with pytest.raises(TypeError, match="Unsupported"):
        canonical_multirow_fingerprint_json(unsupported)

    class IntegerValuedEnum(Enum):
        VALUE = 1

    class StringValuedEnum(Enum):
        VALUE = "VALUE"

    bad_enum = replace(
        _fingerprint_input(geometry, plan_set=plan_set),
        source_metadata=IntegerValuedEnum.VALUE,
    )
    with pytest.raises(TypeError, match="stable strings"):
        canonical_multirow_fingerprint_json(bad_enum)
    valid_enum = replace(
        _fingerprint_input(geometry, plan_set=plan_set),
        source_metadata=StringValuedEnum.VALUE,
    )
    assert '"source_metadata":"VALUE"' in canonical_multirow_fingerprint_json(valid_enum)
