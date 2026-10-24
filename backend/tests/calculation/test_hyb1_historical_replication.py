"""Known historical defects retained; these tests do not approve them."""

from decimal import Decimal, localcontext

from frp_master_connection.calculation.rhm_reference import ReferenceStream, StormSetting
from frp_master_connection.calculation.rhm_workbook_case import execute_workbook_case


def test_historical_column_summary_retains_omitted_axial_component() -> None:
    result = execute_workbook_case(stream=ReferenceStream.HISTORICAL_REPLICATION)
    assert result.column_summary == result.comparisons[4].components[0]
    assert result.column_summary < result.comparisons[4].utilization
    assert result.summary_cell == "Summary!C11 -> Calcs!D149"
    assert len(result.discrepancies) == 5


def test_historical_two_thirds_demand_only() -> None:
    result = execute_workbook_case(
        stream=ReferenceStream.HISTORICAL_REPLICATION, storm=StormSetting.HISTORICAL_TWO_THIRDS
    )
    ordinary = execute_workbook_case()
    with localcontext() as context:
        context.prec = 60
        assert result.storm_multiplier == Decimal(2) / 3
        assert abs(
            result.comparisons[0].utilization - ordinary.comparisons[0].utilization * Decimal(2) / 3
        ) < Decimal("1e-58")
    assert result.storm_multiplier != Decimal(".75")
