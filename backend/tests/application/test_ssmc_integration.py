"""Serial demand, clarified geometry, native isolation and no invented resistance."""

from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from itertools import product

import pytest

from frp_master_connection.api.ssmc import (
    convert_ssmc_units,
    illustrative_ssmc,
    map_ssmc_request,
    ssmc_response,
)
from frp_master_connection.application.ssmc import preview_ssmc
from frp_master_connection.calculation.angle_connector_core import components, shift_angle_wrench
from frp_master_connection.calculation.in_plane_wrench_demand import (
    InPlaneWrenchRequest,
    WrenchBolt,
    calculate_in_plane_wrench_demand,
)
from frp_master_connection.calculation.quantities import PhysicalQuantity as Q
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.domain.ssmc import StringerForm


@pytest.mark.parametrize(
    ("horizontal", "inclined", "side", "angle", "rows", "si"),
    list(
        product(
            StringerForm,
            StringerForm,
            ("NEG_Y", "POS_Y"),
            (-45, -35, -30, 30, 35, 45),
            ((2, 2), (2, 3), (3, 2), (3, 3)),
            (False, True),
        )
    ),
)
def test_native_geometry_and_serial_demand_matrix(
    horizontal: StringerForm,
    inclined: StringerForm,
    side: str,
    angle: int,
    rows: tuple[int, int],
    si: bool,
) -> None:
    dto = illustrative_ssmc()
    dto = dto.model_copy(
        update={
            "horizontal": dto.horizontal.model_copy(update={"form": horizontal}),
            "inclined": dto.inclined.model_copy(update={"form": inclined}),
            "plate": dto.plate.model_copy(update={"side": side}),
            "theta_deg": str(angle),
            "horizontal_group": dto.horizontal_group.model_copy(update={"rows": rows[0]}),
            "inclined_group": dto.inclined_group.model_copy(update={"rows": rows[1]}),
        }
    )
    request = map_ssmc_request(convert_ssmc_units(dto, si))
    request = replace(
        request,
        N=Q(Decimal(8), Unit.KIP),
        V=Q(Decimal(-4), Unit.KIP),
        M=Q(Decimal(20), Unit.KIP_IN),
    )
    result = preview_ssmc(request)
    assert result.whole_connection_status == "ENGINEERING_REVIEW_REQUIRED"
    assert len(result.geometry.shafts) == sum(rows) * 2
    assert len({b.id for b in result.geometry.shafts}) == sum(rows) * 2
    assert result.geometry.polygon.gross_neck_width > 0
    assert result.geometry.polygon_paths.net_area > 0
    assert len(result.geometry.polygon_paths.holes) == sum(rows) * 2
    assert result.trusted_complete_response is None
    assert not result.complete_moment_capacity_qualified
    recovered = [
        shift_angle_wrench(g.plate_wrench, result.work_point_wrench.reference)
        for g in result.groups
    ]
    for name in ("force", "moment"):
        assert (
            tuple(
                a + b
                for a, b in zip(
                    components(getattr(recovered[0], name)),
                    components(getattr(recovered[1], name)),
                    strict=True,
                )
            )
            == (Fraction(0),) * 3
        )
    for group in result.groups:
        assert group.native_slice8 is not None
        assert group.bolt_axis_tension is None
        assert group.prying is None
    assert ssmc_response(result)["contract"] == "SSMC-2-RC1"


def test_side_reversal_preserves_polygon_reverses_secondary_moments() -> None:
    request = replace(
        map_ssmc_request(illustrative_ssmc()),
        N=Q(Decimal(8), Unit.KIP),
        V=Q(Decimal(-4), Unit.KIP),
        M=Q(Decimal(20), Unit.KIP_IN),
    )
    negative = preview_ssmc(request)
    positive = preview_ssmc(replace(request, plate=replace(request.plate, side="POS_Y")))
    assert negative.geometry.polygon == positive.geometry.polygon
    for n, p in zip(negative.groups, positive.groups, strict=True):
        assert components(n.plate_wrench.force) == components(p.plate_wrench.force)
        nm, pm = components(n.plate_wrench.moment), components(p.plate_wrench.moment)
        assert nm == (-pm[0], pm[1], -pm[2])


@pytest.mark.parametrize(
    "loads",
    [
        (8, 0, 0),
        (0, -4, 0),
        (0, 0, 20),
        (8, -4, 0),
        (8, 0, 20),
        (0, -4, 20),
        (8, -4, 20),
        (-8, 4, -20),
    ],
)
@pytest.mark.parametrize("si", [False, True])
@pytest.mark.parametrize("rows", [2, 3])
def test_each_load_path_consumes_direct_native_slice8_verbatim(
    loads: tuple[int, int, int],
    si: bool,
    rows: int,
) -> None:
    dto = illustrative_ssmc()
    dto = dto.model_copy(
        update={
            "N": dto.N.model_copy(update={"value": str(loads[0])}),
            "V": dto.V.model_copy(update={"value": str(loads[1])}),
            "M": dto.M.model_copy(update={"value": str(loads[2])}),
            "horizontal_group": dto.horizontal_group.model_copy(update={"rows": rows}),
            "inclined_group": dto.inclined_group.model_copy(update={"rows": rows}),
        }
    )
    request = map_ssmc_request(convert_ssmc_units(dto, si))
    result = preview_ssmc(request)
    for group in result.groups:
        wrench = group.plate_wrench
        shafts = tuple(b for b in result.geometry.shafts if b.group == group.group_id)
        direct = calculate_in_plane_wrench_demand(
            InPlaneWrenchRequest(
                tuple(WrenchBolt(b.id, str(b.center[0]), str(b.center[1])) for b in shafts),
                (wrench.reference.x.magnitude, wrench.reference.z.magnitude),
                wrench.force.x.to(Unit.N).magnitude,
                wrench.force.z.to(Unit.N).magnitude,
                wrench.moment.y.to(Unit.N_MM).magnitude.copy_negate(),
                request.length_unit,
                Unit.N,
                Unit.N_MM,
            )
        )
        assert group.native_slice8 == direct
        recovered = shift_angle_wrench(wrench, result.work_point_wrench.reference)
        sign = -1 if group == result.groups[0] else 1
        for component in ("force", "moment"):
            assert components(getattr(recovered, component)) == tuple(
                sign * value for value in components(getattr(result.work_point_wrench, component))
            )
        assert group.bolt_axis_tension is None
        assert group.contact_response is None
