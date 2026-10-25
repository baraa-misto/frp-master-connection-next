"""Physical path, layout identity and raw receiving-load proofs independent of UI."""

from dataclasses import replace
from decimal import Decimal

import pytest

from frp_master_connection.api.hybrid_workflow import HybridInputs
from frp_master_connection.application.hyb1_contract import (
    ActionBasis,
    Alignment,
    CaseManifest,
    PairedActions,
    PhysicalIdentity,
)
from frp_master_connection.application.hybrid_physical import PhysicalInputs, evaluate_physical
from frp_master_connection.application.hybrid_physical_geometry import r3_scene_geometry
from frp_master_connection.application.hybrid_same_connection import (
    SameConnectionMaterials,
    calculate_same_connection,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.rhm_direct_r3 import R3Geometry, geometry_digest
from tests.hybrid_physical_fixtures import physical_case


def inputs() -> tuple[PairedActions, R3Geometry, SameConnectionMaterials, PhysicalInputs]:
    dto = HybridInputs.model_validate(physical_case())
    assert dto.geometry is not None
    assert dto.same_connection_lrfd is not None
    assert dto.physical_context is not None
    g = dto.geometry.geometry()
    actions = PairedActions(
        PhysicalIdentity(
            "controlled-account", "DIRECT", geometry_digest(g), "MAT1", "current", Alignment.SUPPORT
        ),
        tuple(case.case(ActionBasis.LRFD) for case in dto.lrfd_cases),
        (),
        CaseManifest((), (), False, False, "Entered independent cases, completeness not assumed"),
    )
    return actions, g, dto.same_connection_lrfd.resolve(g), dto.physical_context.resolved()


def test_different_geometry_cannot_supply_the_current_demand() -> None:
    actions, g, materials, data = inputs()
    other = replace(g, xb=PhysicalQuantity.of("1.1", Unit.IN))
    with pytest.raises(ValueError, match="different physical geometry"):
        calculate_same_connection(
            actions,
            g,
            materials,
            geometry_model=r3_scene_geometry(other),
            allow_receiving_frame=True,
        )
    current = calculate_same_connection(actions, g, materials, allow_receiving_frame=True)
    result = evaluate_physical(actions, other, materials, current.demands, data, requested=True)
    assert not result.rows
    assert any("different layout or action" in reason for reason in result.cases[0]["reasons"])


def test_reversing_row_enumeration_preserves_capacity_without_reusing_an_old_layout() -> None:
    actions, g, materials, data = inputs()
    first = calculate_same_connection(actions, g, materials, allow_receiving_frame=True)
    original = evaluate_physical(actions, g, materials, first.demands, data, requested=True)
    reversed_g = replace(g, reverse_bolt_order=True)
    reversed_actions = replace(
        actions, identity=replace(actions.identity, geometry=geometry_digest(reversed_g))
    )
    fresh = calculate_same_connection(
        reversed_actions, reversed_g, materials, allow_receiving_frame=True
    )
    result = evaluate_physical(
        reversed_actions, reversed_g, materials, fresh.demands, data, requested=True
    )
    assert result.rows[0].ratio == original.rows[0].ratio
    assert result.cases[0]["nearest_unloaded_row"] == "B1"
    assert result.cases[0]["physical_bolt_centers_in"][0][0] == "B2"
    stale = evaluate_physical(
        reversed_actions, reversed_g, materials, first.demands, data, requested=True
    )
    assert not stale.rows


@pytest.mark.parametrize("rotation", [Decimal("45"), Decimal("1")])
def test_ungoverned_datum_rotation_does_not_expand_the_physical_method(rotation: Decimal) -> None:
    actions, g, materials, data = inputs()
    g = replace(g, frame_rotation_degrees=rotation)
    actions = replace(actions, identity=replace(actions.identity, geometry=geometry_digest(g)))
    current = calculate_same_connection(actions, g, materials, allow_receiving_frame=True)
    result = evaluate_physical(actions, g, materials, current.demands, data, requested=True)
    assert not result.rows
    assert any("drawing datum" in reason for reason in result.cases[0]["reasons"])
