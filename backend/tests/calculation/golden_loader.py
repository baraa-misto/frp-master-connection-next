"""Narrow immutable loaders for controlled Slice 1, Slice 2, and Slice 3 golden data."""

import json
import re
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import cast

type FrozenJson = (
    str | bool | int | tuple["FrozenJson", ...] | MappingProxyType[str, "FrozenJson"] | None
)

GOLDEN_PATH = Path(__file__).parents[1] / "golden" / "calculation_slice_1_rc2.json"
SLICE_2_GOLDEN_PATH = Path(__file__).parents[1] / "golden" / "calculation_slice_2_rc1.json"
SLICE_2_RC2_GOLDEN_PATH = Path(__file__).parents[1] / "golden" / "calculation_slice_2_rc2.json"
SLICE_3_RC1_GOLDEN_PATH = Path(__file__).parents[1] / "golden" / "calculation_slice_3_rc1.json"
SLICE_3_RESISTANCE_HANDOFF_RC1_GOLDEN_PATH = (
    Path(__file__).parents[1] / "golden" / "calculation_slice_3_resistance_handoff_rc1.json"
)
SLICE_3_ECCENTRIC_GROUP_MODES_RC1_GOLDEN_PATH = (
    Path(__file__).parents[1] / "golden" / "calculation_slice_3_eccentric_group_modes_rc1.json"
)
SLICE_4_CHAPTER_7_PLATE_STRENGTH_RC1_GOLDEN_PATH = (
    Path(__file__).parents[1]
    / "golden"
    / "calculation_slice_4_chapter_7_plate_strength_engine_golden_benchmarks_rc1.json"
)
EXPECTED_BENCHMARKS = {
    "P1",
    "PT1",
    "P2A",
    "P2B",
    "J1_T",
    "J1_C",
    "B1_SYNTHETIC",
    "DIRECTION_90",
    "HOLE_US_SOURCE",
    "HOLE_SI_SOURCE",
}
_DECIMAL_PATTERN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON object key {key!r}.")
        result[key] = value
    return result


def _freeze(value: object) -> FrozenJson:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, dict):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    raise TypeError(f"Golden JSON contains unsupported value type {type(value).__name__}.")


def _freeze_slice_2(value: object) -> FrozenJson:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, list):
        return tuple(_freeze_slice_2(item) for item in value)
    if isinstance(value, dict):
        return MappingProxyType({str(key): _freeze_slice_2(item) for key, item in value.items()})
    return _freeze(value)


def load_golden_fixture(path: Path = GOLDEN_PATH) -> MappingProxyType[str, FrozenJson]:
    """Load, validate, and recursively freeze the approved RC2 fixture."""

    parsed = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    if not isinstance(parsed, dict):
        raise ValueError("Golden fixture root must be an object.")
    frozen = _freeze(parsed)
    return cast(MappingProxyType[str, FrozenJson], frozen)


def load_slice_2_golden_fixture(
    path: Path = SLICE_2_GOLDEN_PATH,
) -> MappingProxyType[str, FrozenJson]:
    """Load and recursively freeze the approved RC1 Slice 2 benchmark authority."""

    parsed = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    if not isinstance(parsed, dict):
        raise ValueError("Slice 2 golden fixture root must be an object.")
    return cast(MappingProxyType[str, FrozenJson], _freeze_slice_2(parsed))


def load_slice_2_rc2_golden_fixture(
    path: Path = SLICE_2_RC2_GOLDEN_PATH,
) -> MappingProxyType[str, FrozenJson]:
    """Load and recursively freeze the approved RC2 Slice 2 benchmark authority."""

    return load_slice_2_golden_fixture(path)


def load_slice_3_rc1_golden_fixture(
    path: Path = SLICE_3_RC1_GOLDEN_PATH,
) -> MappingProxyType[str, FrozenJson]:
    """Load and recursively freeze the approved RC1 Slice 3 benchmark authority."""

    return load_slice_2_golden_fixture(path)


def load_slice_3_resistance_handoff_rc1_golden_fixture(
    path: Path = SLICE_3_RESISTANCE_HANDOFF_RC1_GOLDEN_PATH,
) -> MappingProxyType[str, FrozenJson]:
    """Load and recursively freeze the approved RC1 resistance-handoff authority."""

    return load_slice_2_golden_fixture(path)


def load_slice_3_eccentric_group_modes_rc1_golden_fixture(
    path: Path = SLICE_3_ECCENTRIC_GROUP_MODES_RC1_GOLDEN_PATH,
) -> MappingProxyType[str, FrozenJson]:
    """Load and recursively freeze the approved RC1 eccentric group-mode authority."""

    return load_slice_2_golden_fixture(path)


def load_slice_4_chapter_7_plate_strength_rc1_golden_fixture(
    path: Path = SLICE_4_CHAPTER_7_PLATE_STRENGTH_RC1_GOLDEN_PATH,
) -> MappingProxyType[str, FrozenJson]:
    """Load and freeze the controlled Calculation Slice 4 benchmark authority."""

    return load_slice_2_golden_fixture(path)


def decimal_strings(value: FrozenJson) -> tuple[Decimal, ...]:
    """Return every syntactically decimal string as a parsed Decimal."""

    if isinstance(value, str):
        return (Decimal(value),) if _DECIMAL_PATTERN.fullmatch(value) else ()
    if isinstance(value, tuple):
        return tuple(number for item in value for number in decimal_strings(item))
    if isinstance(value, MappingProxyType):
        return tuple(number for item in value.values() for number in decimal_strings(item))
    return ()


__all__ = (
    "EXPECTED_BENCHMARKS",
    "GOLDEN_PATH",
    "SLICE_2_GOLDEN_PATH",
    "SLICE_2_RC2_GOLDEN_PATH",
    "SLICE_3_ECCENTRIC_GROUP_MODES_RC1_GOLDEN_PATH",
    "SLICE_3_RC1_GOLDEN_PATH",
    "SLICE_3_RESISTANCE_HANDOFF_RC1_GOLDEN_PATH",
    "SLICE_4_CHAPTER_7_PLATE_STRENGTH_RC1_GOLDEN_PATH",
    "FrozenJson",
    "decimal_strings",
    "load_golden_fixture",
    "load_slice_2_golden_fixture",
    "load_slice_2_rc2_golden_fixture",
    "load_slice_3_eccentric_group_modes_rc1_golden_fixture",
    "load_slice_3_rc1_golden_fixture",
    "load_slice_3_resistance_handoff_rc1_golden_fixture",
    "load_slice_4_chapter_7_plate_strength_rc1_golden_fixture",
)
