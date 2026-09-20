"""Fixed startup inputs must pass unchanged geometry and retain historical requests."""

from dataclasses import replace
from decimal import Decimal

import pytest

from frp_master_connection.application.angle_column_base_preview import (
    preview_angle_column_moment_base,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain.angle_column_moment_base import (
    default_angle_column_moment_base_request,
)
from frp_master_connection.domain.connection_workspace_defaults import (
    angle_column_workspace_default,
)


@pytest.mark.parametrize("si", [False, True])
def test_fixed_base_default_native_validity_and_protected_hardware(si: bool) -> None:
    historical = default_angle_column_moment_base_request(si=si)
    before = preview_angle_column_moment_base(historical)
    request = angle_column_workspace_default(si=si)
    native = preview_angle_column_moment_base(request)
    assert native.geometry.status == "VALID", native.geometry.reasons
    assert not native.resistance_evaluated
    assert request.actions == historical.actions
    assert request.foundation == historical.foundation
    for quantity in (request.column.leg_x, request.column.leg_y):
        assert quantity.to(Unit.IN).magnitude == Decimal("4")
    assert request.column.thickness == historical.column.thickness
    for current, old in zip(request.connectors, historical.connectors, strict=True):
        assert current.angle.geometry.length.to(Unit.IN).magnitude == Decimal("5.5")
        assert current.angle.geometry.member_leg.to(Unit.IN).magnitude == Decimal("4")
        assert current.angle.geometry.support_leg.to(Unit.IN).magnitude == Decimal("4")
        assert current.angle.geometry.thickness == old.angle.geometry.thickness
        assert current.angle.geometry.inside_radius == old.angle.geometry.inside_radius
        assert current.extrusion_center.to(Unit.IN).magnitude == Decimal("2.75")
        assert current.angle.member_pattern.across == 2
        assert current.angle.member_pattern.along == 1
        assert current.angle.member_pattern.gauge.to(Unit.IN).magnitude == Decimal("1.25")
        assert current.angle.member_pattern.pitch == old.angle.member_pattern.pitch
        assert current.angle.member_pattern.center == old.angle.member_pattern.center
        assert current.angle.support_pattern.across == current.angle.support_pattern.along == 1
        assert current.angle.fastener == old.angle.fastener
        assert current.angle.anchors == old.angle.anchors
        assert current.member_hardware == old.member_hardware
        assert current.angle.provider_id == old.angle.provider_id
    assert request.leg_1.angle.geometry == request.leg_2.angle.geometry
    assert preview_angle_column_moment_base(historical) == before
    assert default_angle_column_moment_base_request(si=si) == historical
    assert angle_column_workspace_default(si=si, unequal=True) == (
        default_angle_column_moment_base_request(si=si, unequal=True)
    )


@pytest.mark.parametrize("si", [False, True])
def test_base_length_immediately_above_fixed_maximum_fails_native_corner_rule(si: bool) -> None:
    request = angle_column_workspace_default(si=si)
    length = PhysicalQuantity.of("5.500001", Unit.IN).to(Unit.MM if si else Unit.IN)
    request = replace(
        request,
        leg_1=replace(
            request.leg_1,
            angle=replace(
                request.leg_1.angle,
                geometry=replace(
                    request.leg_1.angle.geometry,
                    length=length,
                ),
            ),
        ),
        leg_2=replace(
            request.leg_2,
            angle=replace(
                request.leg_2.angle,
                geometry=replace(
                    request.leg_2.angle.geometry,
                    length=length,
                ),
            ),
        ),
    )
    native = preview_angle_column_moment_base(request)
    assert native.geometry.status == "INVALID_GEOMETRY"
    assert "COLUMN_CONNECTOR_FOUNDATION_SOLID_INTERFERENCE" in native.geometry.reasons
