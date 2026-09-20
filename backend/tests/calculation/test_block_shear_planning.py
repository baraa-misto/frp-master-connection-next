"""Stage 2.4A L/U block-path raw-area and Section 2.10 tests."""

from dataclasses import fields
from decimal import Decimal

import pytest

from frp_master_connection.calculation import (
    BlockPathPlanStatus,
    BoltHoleSource,
    DeferredExecutionStatus,
    HoleDeductionPlane,
    MultiRowWarningCode,
    NetAreaStatus,
    PhysicalQuantity,
    PlanAvailability,
    PublishedCodeUnitBasis,
    Unit,
    build_block_shear_area_plans,
    create_standard_hole,
)
from frp_master_connection.geometry import (
    BlockPathFamily,
    BlockPathRejectionReason,
    BlockPathSegment,
    BlockPathSegmentKind,
    BlockShearCandidatePath,
    BlockShearPathResolution,
    GeneralBolt,
    GeneralBoltGroup,
    MultiRowGeometry,
    MultiRowGeometryTolerance,
    PlanarLayerBoundary,
    PlanarPoint2D,
    ProjectedPoint2D,
    resolve_block_shear_paths,
    resolve_multirow_geometry,
)


def _geometry(
    *,
    unit_scale: float = 1.0,
    bolt_diameter: float = 0.5,
    hole_diameter: float = 0.563,
) -> MultiRowGeometry:
    rows = (4.0, 2.0, 0.0)
    lines = (-1.375, 1.375)
    bolts = tuple(
        GeneralBolt(
            f"B_R{row_index}_L{line_index}",
            PlanarPoint2D(x * unit_scale, y * unit_scale),
            bolt_diameter,
            hole_diameter,
            "BOLT-A",
            "CONNECTION-1",
        )
        for row_index, x in enumerate(rows, start=1)
        for line_index, y in enumerate(lines, start=1)
    )
    group = GeneralBoltGroup("BG", "I", 3, 6, bolts)
    boundary = PlanarLayerBoundary(
        "LAYER",
        -4 * unit_scale,
        6 * unit_scale,
        -3.375 * unit_scale,
        3.375 * unit_scale,
    )
    return resolve_multirow_geometry(
        group,
        boundary,
        (1, 0),
        MultiRowGeometryTolerance(1e-6 * unit_scale),
    )


def _us_sources(geometry: MultiRowGeometry) -> tuple[BoltHoleSource, ...]:
    definition = create_standard_hole(
        PhysicalQuantity.of("0.5", Unit.IN),
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
    )
    return tuple(BoltHoleSource(bolt.id, definition) for bolt in geometry.group.bolts)


def _candidate(
    *,
    identifier: str = "MANUAL",
    shear_length: float = 4.0,
    tension_length: float = 2.0,
    shear_full: tuple[str, ...] = (),
    tension_full: tuple[str, ...] = (),
    shared: tuple[str, ...] = (),
    rejected: bool = False,
) -> BlockShearCandidatePath:
    return BlockShearCandidatePath(
        identifier,
        BlockPathFamily.L_LEFT,
        "ROW_1",
        (
            BlockPathSegment(
                BlockPathSegmentKind.SHEAR,
                ProjectedPoint2D(0, 0),
                ProjectedPoint2D(shear_length, 0),
            ),
            BlockPathSegment(
                BlockPathSegmentKind.TENSION,
                ProjectedPoint2D(shear_length, 0),
                ProjectedPoint2D(shear_length, tension_length),
            ),
        ),
        shear_full,
        tension_full,
        shared,
        (BlockPathRejectionReason.NO_FREE_BOUNDARY_CLOSURE,) if rejected else (),
    )


def test_u_and_l_raw_areas_use_full_and_half_hole_accounting() -> None:
    geometry = _geometry()
    resolution = resolve_block_shear_paths(geometry)
    plans = build_block_shear_area_plans(
        resolution,
        geometry,
        Unit.IN,
        PhysicalQuantity.of(".375", Unit.IN),
        _us_sources(geometry),
    )
    accepted = tuple(
        item for item in plans.candidates if item.path_status is BlockPathPlanStatus.ACCEPTED
    )
    u_plan = next(item for item in accepted if "BLOCK_U_" in item.path_id)
    left = next(item for item in accepted if "BLOCK_L_LEFT" in item.path_id)
    right = next(item for item in accepted if "BLOCK_L_RIGHT" in item.path_id)

    assert len(accepted) == 3
    assert u_plan.gross_shear_length == PhysicalQuantity.of("16", Unit.IN)
    assert u_plan.net_shear_length == PhysicalQuantity.of("12.87", Unit.IN)
    assert u_plan.gross_tension_length == PhysicalQuantity.of("2.75", Unit.IN)
    assert u_plan.net_tension_length == PhysicalQuantity.of("2.124", Unit.IN)
    assert u_plan.shear_net_to_gross == Decimal("0.804375")
    assert u_plan.tension_net_to_gross is not None
    assert u_plan.tension_net_to_gross.quantize(Decimal(".000000000001")) == Decimal(
        ".772363636364"
    )
    assert (
        left.gross_tension_length == right.gross_tension_length == PhysicalQuantity.of("2", Unit.IN)
    )
    assert left.net_tension_length == PhysicalQuantity.of("1.687", Unit.IN)
    assert u_plan.shear_net_area_status is NetAreaStatus.SATISFIES_MINIMUM_NET_AREA
    assert u_plan.tension_net_area_status is NetAreaStatus.SATISFIES_MINIMUM_NET_AREA
    assert u_plan.availability is PlanAvailability.READY
    assert u_plan.minimum_selection_status is DeferredExecutionStatus.DEFERRED_STAGE_2_4B
    assert plans.minimum_selection_status is DeferredExecutionStatus.DEFERRED_STAGE_2_4B
    assert "resistance" not in {field.name for field in fields(type(u_plan))}


def test_shared_corner_is_half_each_plane_and_never_changes_physical_hole() -> None:
    geometry = _geometry()
    plan = build_block_shear_area_plans(
        BlockShearPathResolution((_candidate(shared=("B_R1_L1",)),)),
        geometry,
        Unit.IN,
        PhysicalQuantity.of(".375", Unit.IN),
        _us_sources(geometry),
    ).candidates[0]
    shared = tuple(item for item in plan.deductions if item.bolt_id == "B_R1_L1")

    assert {item.plane for item in shared} == {
        HoleDeductionPlane.SHEAR,
        HoleDeductionPlane.TENSION,
    }
    assert all(item.fraction == Decimal(".5") for item in shared)
    assert all(
        item.physical_hole_diameter == PhysicalQuantity.of(".563", Unit.IN) for item in shared
    )
    assert all(
        item.net_area_hole_diameter == PhysicalQuantity.of(".626", Unit.IN) for item in shared
    )
    assert all(item.deduction == PhysicalQuantity.of(".313", Unit.IN) for item in shared)
    assert geometry.group.bolts[0].hole_diameter == 0.563
    assert plan.warnings[0].code is MultiRowWarningCode.RATIONAL_HALF_HOLE_CORNER_ACCOUNTING


def test_us_and_si_source_hole_additions_are_converted_not_regenerated() -> None:
    us_geometry = _geometry(
        unit_scale=25.4,
        bolt_diameter=12.7,
        hole_diameter=14.3002,
    )
    us_plan = build_block_shear_area_plans(
        BlockShearPathResolution(
            (
                _candidate(
                    shear_length=101.6,
                    tension_length=50.8,
                    shear_full=("B_R1_L1",),
                ),
            )
        ),
        us_geometry,
        Unit.MM,
        PhysicalQuantity.of("9.525", Unit.MM),
        _us_sources(us_geometry),
    ).candidates[0]
    us_deduction = us_plan.deductions[0]
    assert us_deduction.physical_hole_diameter == PhysicalQuantity.of("14.3002", Unit.MM)
    assert us_deduction.net_area_hole_diameter == PhysicalQuantity.of("15.9004", Unit.MM)
    assert us_deduction.source_basis == PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED.value

    si_geometry = _geometry(
        unit_scale=25.4,
        bolt_diameter=12.7,
        hole_diameter=14.3,
    )
    si_definition = create_standard_hole(
        PhysicalQuantity.of("12.7", Unit.MM),
        PublishedCodeUnitBasis.SI_PRINTED,
    )
    si_sources = tuple(BoltHoleSource(bolt.id, si_definition) for bolt in si_geometry.group.bolts)
    si_plan = build_block_shear_area_plans(
        BlockShearPathResolution(
            (_candidate(shear_length=101.6, tension_length=50.8, shear_full=("B_R1_L1",)),)
        ),
        si_geometry,
        Unit.MM,
        PhysicalQuantity.of("9.525", Unit.MM),
        si_sources,
    ).candidates[0]
    si_deduction = si_plan.deductions[0]
    assert si_deduction.physical_hole_diameter == PhysicalQuantity.of("14.3", Unit.MM)
    assert si_deduction.net_area_hole_diameter == PhysicalQuantity.of("15.9", Unit.MM)
    assert si_deduction.source_basis == PublishedCodeUnitBasis.SI_PRINTED.value


def test_section_2_10_warning_retains_raw_area_without_floor() -> None:
    geometry = _geometry()
    candidate = _candidate(
        shear_length=2,
        tension_length=2,
        shear_full=("B_R1_L1",),
        tension_full=("B_R1_L2",),
    )
    plan = build_block_shear_area_plans(
        BlockShearPathResolution((candidate,)),
        geometry,
        Unit.IN,
        PhysicalQuantity.of(".375", Unit.IN),
        _us_sources(geometry),
    ).candidates[0]

    assert plan.shear_net_to_gross == plan.tension_net_to_gross == Decimal(".687")
    assert plan.net_shear_area == PhysicalQuantity.of(".51525", Unit.IN2)
    assert plan.net_tension_area == PhysicalQuantity.of(".51525", Unit.IN2)
    assert plan.availability is PlanAvailability.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED
    assert plan.warnings[-1].code is MultiRowWarningCode.CODE_GEOMETRY_REQUIREMENT_NOT_SATISFIED
    assert plan.net_shear_area != plan.gross_shear_area * Decimal(".75")


@pytest.mark.parametrize("length", [Decimal(".626"), Decimal(".5")])
def test_zero_or_negative_raw_net_area_is_invalid_and_retained(length: Decimal) -> None:
    geometry = _geometry()
    candidate = _candidate(
        shear_length=float(length),
        tension_length=2,
        shear_full=("B_R1_L1",),
    )
    plan = build_block_shear_area_plans(
        BlockShearPathResolution((candidate,)),
        geometry,
        Unit.IN,
        PhysicalQuantity.of(".375", Unit.IN),
        _us_sources(geometry),
    ).candidates[0]

    assert plan.shear_net_area_status is NetAreaStatus.INVALID_GEOMETRY
    assert plan.tension_net_area_status is NetAreaStatus.SATISFIES_MINIMUM_NET_AREA
    assert plan.net_shear_area.magnitude <= 0
    assert plan.availability is PlanAvailability.CALCULATION_NOT_SUPPORTED


def test_zero_gross_component_has_no_ratio_and_is_invalid() -> None:
    geometry = _geometry()
    plan = build_block_shear_area_plans(
        BlockShearPathResolution((_candidate(tension_length=0),)),
        geometry,
        Unit.IN,
        PhysicalQuantity.of(".375", Unit.IN),
        _us_sources(geometry),
    ).candidates[0]
    assert plan.tension_net_to_gross is None
    assert plan.tension_net_area_status is NetAreaStatus.INVALID_GEOMETRY


def test_rejected_candidate_is_retained_but_not_ready() -> None:
    geometry = _geometry()
    plan = build_block_shear_area_plans(
        BlockShearPathResolution((_candidate(rejected=True),)),
        geometry,
        Unit.IN,
        PhysicalQuantity.of(".375", Unit.IN),
        _us_sources(geometry),
    ).candidates[0]
    assert plan.path_status is BlockPathPlanStatus.REJECTED
    assert plan.rejection_reasons == (BlockPathRejectionReason.NO_FREE_BOUNDARY_CLOSURE.value,)
    assert plan.availability is PlanAvailability.NOT_APPLICABLE


def test_block_area_prevents_more_than_one_combined_hole_deduction() -> None:
    geometry = _geometry()
    candidate = _candidate(
        shear_full=("B_R1_L1",),
        tension_full=("B_R1_L1",),
    )
    with pytest.raises(ValueError, match="cannot exceed"):
        build_block_shear_area_plans(
            BlockShearPathResolution((candidate,)),
            geometry,
            Unit.IN,
            PhysicalQuantity.of(".375", Unit.IN),
            _us_sources(geometry),
        )


def test_hole_source_assignments_must_be_unique_complete_and_physical() -> None:
    geometry = _geometry()
    sources = _us_sources(geometry)
    resolution = BlockShearPathResolution((_candidate(),))
    with pytest.raises(ValueError, match="unique"):
        build_block_shear_area_plans(
            resolution,
            geometry,
            Unit.IN,
            PhysicalQuantity.of(".375", Unit.IN),
            (*sources, sources[0]),
        )
    with pytest.raises(ValueError, match="Every physical"):
        build_block_shear_area_plans(
            resolution,
            geometry,
            Unit.IN,
            PhysicalQuantity.of(".375", Unit.IN),
            sources[:-1],
        )
    wrong = create_standard_hole(
        PhysicalQuantity.of(".625", Unit.IN),
        PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED,
    )
    with pytest.raises(ValueError, match="unchanged physical"):
        build_block_shear_area_plans(
            resolution,
            geometry,
            Unit.IN,
            PhysicalQuantity.of(".375", Unit.IN),
            (BoltHoleSource(sources[0].bolt_id, wrong), *sources[1:]),
        )


def test_block_area_contract_validation() -> None:
    geometry = _geometry()
    resolution = BlockShearPathResolution((_candidate(),))
    sources = _us_sources(geometry)
    with pytest.raises(ValueError, match="nonempty"):
        BoltHoleSource("", sources[0].definition)
    with pytest.raises(TypeError, match="StandardHoleDefinition"):
        BoltHoleSource("B", object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="resolution"):
        build_block_shear_area_plans(
            object(),  # type: ignore[arg-type]
            geometry,
            Unit.IN,
            PhysicalQuantity.of(".375", Unit.IN),
            sources,
        )
    with pytest.raises(ValueError, match="IN or MM"):
        build_block_shear_area_plans(
            resolution, geometry, Unit.KIP, PhysicalQuantity.of(".375", Unit.IN), sources
        )
    with pytest.raises(ValueError, match="positive length"):
        build_block_shear_area_plans(
            resolution, geometry, Unit.IN, PhysicalQuantity.of("0", Unit.IN), sources
        )


def test_empty_resolution_is_a_valid_deferred_plan_set() -> None:
    geometry = _geometry()
    plans = build_block_shear_area_plans(
        BlockShearPathResolution(()),
        geometry,
        Unit.IN,
        PhysicalQuantity.of(".375", Unit.IN),
        _us_sources(geometry),
    )
    assert plans.candidates == ()
    assert plans.minimum_selection_status is DeferredExecutionStatus.DEFERRED_STAGE_2_4B
