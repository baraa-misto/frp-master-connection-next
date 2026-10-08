"""Section 2.3.2 connection statistics; no component or aggregate activation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Any

from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    Unit,
    decimal_from_finite_real,
    decimal_value,
)

CONVENTION = "SAMPLE_SD_N_MINUS_1"
QUANTILE_AUTHORITY = "scipy==1.18.1; scipy.stats.t.ppf; IEEE754 binary64 round-trip decimal"


@dataclass(frozen=True, slots=True)
class QualificationStatistics:
    accepted_n: int
    ro_n: Decimal | None
    sd_n: Decimal | None
    vr: Decimal | None
    t: Decimal | None
    phi_p: Decimal | None
    blockers: tuple[str, ...]

    def trace(self) -> dict[str, Any]:
        return {
            "accepted_n": self.accepted_n,
            "Ro": None if self.ro_n is None else str(self.ro_n),
            "sample_sd": None if self.sd_n is None else str(self.sd_n),
            "VR": None if self.vr is None else str(self.vr),
            "t": None if self.t is None else str(self.t),
            "phi_p": None if self.phi_p is None else str(self.phi_p),
            "force_unit": "N",
            "probability": "0.999",
            "degrees_of_freedom": self.accepted_n - 1,
            "estimator": CONVENTION,
            "quantile_authority": QUANTILE_AUTHORITY,
            "decimal_precision": 80,
            "equation": "exp(-t_(N-1,.999) * VR * sqrt(1 + 1/N))",
            "blockers": list(self.blockers),
        }


def connection_t(accepted_n: int) -> Decimal:
    """Pinned mature inverse CDF; only used for connection qualification."""
    from scipy.stats import t  # type: ignore[import-untyped]

    if isinstance(accepted_n, bool) or accepted_n < 10:
        raise ValueError("QUALIFICATION_AT_LEAST_TEN_ACCEPTED_SPECIMENS_REQUIRED")
    result = decimal_from_finite_real(float(t.ppf(0.999, accepted_n - 1)))
    if result <= 0:
        raise ValueError("STATISTICAL_QUANTILE_AUTHORITY_INVALID")
    return result


def _reported_equal(value: Decimal, reported: dict[str, Any]) -> bool:
    """Decimal lab-report precision, never a physical engineering tolerance."""
    lab = decimal_value(reported["value"])
    quantum = reported.get("decimal_quantum")
    if quantum is None:
        return value == lab
    step = decimal_value(quantum)
    if step <= 0 or step != Decimal(1).scaleb(step.adjusted()):
        raise ValueError("LAB_REPORTED_PRECISION_INVALID")
    return value.quantize(step) == lab.quantize(step)


def recompute_statistics(
    specimens: list[dict[str, Any]], protocol: dict[str, Any]
) -> QualificationStatistics:
    """Derive N/Ro/SD/VR from raw records; aggregate assertions are never inputs."""
    blockers: list[str] = []
    strengths: list[Decimal] = []
    populations: set[tuple[str, str, str]] = set()
    identifiers: set[str] = set()
    for specimen in specimens:
        identifier = specimen["specimen_id"]
        if identifier in identifiers:
            blockers.append("DUPLICATE_SPECIMEN_ID")
        identifiers.add(identifier)
        try:
            strength = PhysicalQuantity.of(specimen["test_strength"], Unit(specimen["unit"]))
            if strength.dimension is not Dimension.FORCE or strength.magnitude <= 0:
                raise ValueError("INVALID_TEST_STRENGTH")
        except ArithmeticError, ValueError:
            blockers.append("NONFINITE_NONPOSITIVE_OR_NONFORCE_SPECIMEN_STRENGTH")
            continue
        if specimen["accepted_or_excluded"] == "EXCLUDED":
            if (
                not specimen["exclusion_rationale"]
                or not specimen["exclusion_approval_document_id"]
            ):
                blockers.append("RDP_APPROVED_EXCLUSION_EVIDENCE_REQUIRED")
            continue
        strengths.append(strength.canonical_magnitude)
        populations.add(
            (specimen["test_condition"], specimen["fixture_id"], specimen["protocol_id"])
        )
    n = len(strengths)
    if n < 10:
        blockers.append("QUALIFICATION_AT_LEAST_TEN_ACCEPTED_SPECIMENS_REQUIRED")
    if len(populations) > 1:
        blockers.append("IDENTICAL_SPECIMEN_POPULATION_REQUIRED")
    if protocol["estimator_convention"] != CONVENTION:
        blockers.append("STATISTICAL_CONVENTION_NOT_SUPPORTED")
    if protocol["connection_probability"] != "0.999":
        blockers.append("CONNECTION_STUDENT_T_PROBABILITY_MUST_BE_0_999")
    if n < 10:
        return QualificationStatistics(
            n, None, None, None, None, None, tuple(dict.fromkeys(blockers))
        )
    with localcontext() as ctx:
        ctx.prec = 80
        ctx.rounding = ROUND_HALF_EVEN
        ro = sum(strengths, Decimal(0)) / Decimal(n)
        sd = (sum(((r - ro) ** 2 for r in strengths), Decimal(0)) / Decimal(n - 1)).sqrt()
        vr = sd / ro
        quantile = connection_t(n)
        phi = (-quantile * vr * (Decimal(1) + Decimal(1) / Decimal(n)).sqrt()).exp()
        if not 0 < phi <= 1:
            blockers.append("QUALIFICATION_PHI_OUTSIDE_VALID_DOMAIN")
        for name, calculated in (("mean", ro), ("sd", sd), ("cov", vr)):
            reported = protocol.get("lab_reported_" + name)
            if reported is None:
                blockers.append("LAB_REPORTED_STATISTICS_REQUIRED")
                continue
            try:
                if name in {"mean", "sd"}:
                    unit = Unit(reported["unit"])
                    factor = PhysicalQuantity.of("1", unit)
                    if factor.dimension is not Dimension.FORCE:
                        raise ValueError("LAB_REPORTED_FORCE_UNIT_INVALID")
                    calculated /= factor.canonical_magnitude
                if not _reported_equal(calculated, reported):
                    blockers.append("LAB_STATISTICS_RECONCILIATION_FAILED:" + name)
            except ArithmeticError, ValueError:
                blockers.append("LAB_REPORTED_STATISTICS_OR_PRECISION_INVALID:" + name)
    return QualificationStatistics(n, ro, sd, vr, quantile, phi, tuple(dict.fromkeys(blockers)))


__all__ = ("CONVENTION", "QualificationStatistics", "connection_t", "recompute_statistics")
