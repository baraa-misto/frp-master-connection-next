"""Explicit native-real boundary for new DCTN fingerprints only."""

from dataclasses import fields, is_dataclass

from frp_master_connection.calculation.angle_column_base_response import base_fingerprint
from frp_master_connection.calculation.quantities import PhysicalQuantity, decimal_from_finite_real


def _native(value: object) -> object:
    if isinstance(value, float):
        return decimal_from_finite_real(value)
    if isinstance(value, PhysicalQuantity):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _native(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, (tuple, list)):
        return tuple(_native(item) for item in value)
    if isinstance(value, dict):
        return {str(key): _native(item) for key, item in value.items()}
    return value


def dctn_fingerprint(value: object) -> str:
    """No rounding/tolerance: retain each native float's exact accepted str adapter."""
    return base_fingerprint(_native(value))
