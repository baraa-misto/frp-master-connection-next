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


def resolved_display_units(
    request: dict[str, object], result: dict[str, object], selected: DisplayUnits
) -> DisplayUnits:
    """Use the calculation's submitted display system when no override was chosen."""

    if selected != "INHERIT":
        return selected
    for source in (request, result):
        for key in ("display_unit_system", "unit_system"):
            value = source.get(key)
            if isinstance(value, str) and value in {"US_CUSTOMARY", "SI"}:
                return value  # type: ignore[return-value]
    length = request.get("source_length_unit") or request.get("length_unit")
    if length == "in":
        return "US_CUSTOMARY"
    if length == "mm":
        return "SI"
    return "INHERIT"


def display_quantity(value: object, system: DisplayUnits) -> str:
    """Format a native quantity in one engineer-facing report system.

    This changes display bytes only. The signed native quantity remains in the
    full technical appendix, including its exact value and canonical fields.
    """

    if not isinstance(value, dict) or "value" not in value:
        return "Not supplied"
    magnitude = value["value"]
    unit = value.get("unit", "")
    native = f"{magnitude} {unit}".strip()
    if system == "INHERIT" or not isinstance(unit, str):
        return native
    try:
        source = PhysicalQuantity.of(str(magnitude), Unit(unit))
        target = _TARGET[system].get(source.dimension)
        if target is None:
            return native
        if target == source.unit:
            return f"{source.magnitude:.12g} {source.unit.value}"
        converted = source.to(target)
        return f"{converted.magnitude:.12g} {target.value}"
    except InvalidOperation, TypeError, ValueError:
        return native


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


__all__ = (
    "DisplayUnits",
    "converted_quantity_rows",
    "display_quantity",
    "resolved_display_units",
)
