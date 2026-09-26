"""Read-only quantity equivalents using the project's exact conversion service."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Literal

from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity, Unit

DisplayUnits = Literal["INHERIT", "US_CUSTOMARY", "SI"]

_TARGET: dict[str, dict[Dimension, Unit]] = {
    "US_CUSTOMARY": {
        Dimension.LENGTH: Unit.IN,
        Dimension.AREA: Unit.IN2,
        Dimension.SECOND_MOMENT_OF_AREA: Unit.IN4,
        Dimension.FORCE: Unit.KIP,
        Dimension.MOMENT: Unit.KIP_IN,
        Dimension.STRESS: Unit.KSI,
        Dimension.FORCE_PER_LENGTH: Unit.KIP_PER_IN,
    },
    "SI": {
        Dimension.LENGTH: Unit.MM,
        Dimension.AREA: Unit.MM2,
        Dimension.SECOND_MOMENT_OF_AREA: Unit.MM4,
        Dimension.FORCE: Unit.KN,
        Dimension.MOMENT: Unit.KN_MM,
        Dimension.STRESS: Unit.MPA,
        Dimension.FORCE_PER_LENGTH: Unit.N_PER_MM,
    },
}


def converted_quantity_rows(value: object, system: DisplayUnits) -> list[tuple[str, str]]:
    """Keep native values and add labelled equivalents; never alter calculation data."""

    if system == "INHERIT":
        return []
    result: list[tuple[str, str]] = []

    def visit(item: object, path: str) -> None:
        if isinstance(item, dict):
            unit = item.get("unit")
            magnitude = item.get("value", item.get("magnitude"))
            if isinstance(unit, str) and isinstance(magnitude, (str, int, float)):
                try:
                    if unit in {"degF", "degC"}:
                        number = Decimal(str(magnitude))
                        if system == "SI" and unit == "degF":
                            converted = (number - 32) * Decimal(5) / Decimal(9)
                            result.append((path, f"{magnitude} degF = {converted:.12g} degC"))
                        elif system == "US_CUSTOMARY" and unit == "degC":
                            converted = number * Decimal(9) / Decimal(5) + 32
                            result.append((path, f"{magnitude} degC = {converted:.12g} degF"))
                    else:
                        source = PhysicalQuantity.of(str(magnitude), Unit(unit))
                        target = _TARGET[system].get(source.dimension)
                        if target is not None and target != source.unit:
                            converted_quantity = source.to(target)
                            equivalent = f"{converted_quantity.magnitude:.12g} {target.value}"
                            result.append((path, f"{magnitude} {unit} = {equivalent}"))
                except InvalidOperation, TypeError, ValueError:
                    pass
            for key, child in item.items():
                visit(child, f"{path}.{key}" if path else str(key))
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, f"{path}[{index}]")

    visit(value, "")
    return result


__all__ = ("DisplayUnits", "converted_quantity_rows")
