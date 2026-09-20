"""Deterministic binary64 trigonometry for controlled geometry angles."""

from __future__ import annotations

from decimal import Decimal, localcontext

_BINARY_RADIANS_PER_DEGREE = float.fromhex("0x1.1df46a2529d39p-6")


def deterministic_sine_cosine_degrees(angle_degrees: Decimal) -> tuple[float, float]:
    """Evaluate a semantic angle without platform libm trigonometry.

    This is the Stage 3.2-R5 authority, shared by every backend-owned geometry
    placement that needs the same deterministic binary64 direction values.
    """

    normalized = angle_degrees % Decimal(360)
    if normalized == Decimal(45):
        with localcontext() as context:
            context.prec = 100
            diagonal = float((Decimal(1) / Decimal(2)).sqrt())
        return diagonal, diagonal

    # Preserve the accepted IEEE-754 degree-to-radian input exactly, then
    # evaluate both series in Decimal space. Converting the final values once
    # gives one deterministic binary64 result on every supported platform.
    radians = Decimal.from_float(float(normalized) * _BINARY_RADIANS_PER_DEGREE)
    with localcontext() as context:
        context.prec = 100
        squared = radians * radians

        sine_term = radians
        sine_decimal = radians
        index = 1
        while True:
            sine_term *= -squared / (Decimal(2 * index) * Decimal(2 * index + 1))
            updated_sine = sine_decimal + sine_term
            if updated_sine == sine_decimal:
                break
            sine_decimal = updated_sine
            index += 1

        cosine_term = Decimal(1)
        cosine_decimal = Decimal(1)
        index = 1
        while True:
            cosine_term *= -squared / (Decimal(2 * index - 1) * Decimal(2 * index))
            updated_cosine = cosine_decimal + cosine_term
            if updated_cosine == cosine_decimal:
                break
            cosine_decimal = updated_cosine
            index += 1
    return float(sine_decimal), float(cosine_decimal)


__all__ = ("deterministic_sine_cosine_degrees",)
