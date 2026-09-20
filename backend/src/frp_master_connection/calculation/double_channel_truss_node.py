"""DCTN local-check adapters. Frozen equation functions remain the numerical authority."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from frp_master_connection.calculation.equations import (
    BearingTrace,
    EndUsePropertyTrace,
    adjust_frp_property,
    pin_bearing_resistance,
)
from frp_master_connection.calculation.inputs import (
    EndUseFactors,
    LapConfiguration,
    create_lap_factor_plan,
)
from frp_master_connection.calculation.multirow_equations import (
    ResistanceComparison,
    compare_resistance,
)
from frp_master_connection.calculation.properties import FRPPropertyKind, ThreadStatus
from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity
from frp_master_connection.calculation.sources import QualificationStatus
from frp_master_connection.domain.double_channel_truss_node import DCTNForm, require_quantity

METHOD = "DCTN_ASCE74_23_LOCAL_CONNECTION_RC1"
RHS_CHARACTERISTIC_FACTOR = Decimal("0.50")


def characteristic_bearing(
    value: PhysicalQuantity,
    form: DCTNForm,
    *,
    rhs_factor: Decimal = RHS_CHARACTERISTIC_FACTOR,
) -> PhysicalQuantity:
    """Owner-approved RHS characteristic-only adapter, never a demand/hardware factor."""
    require_quantity(value, Dimension.STRESS)
    if rhs_factor != RHS_CHARACTERISTIC_FACTOR:
        raise ValueError("DCTN_RHS_CLOSED_SECTION_BEARING_FACTOR_REQUIRED")
    return value * rhs_factor if form is DCTNForm.RHS else value


def local_lap_factor(form: DCTNForm, requested: Decimal | None = None) -> Decimal:
    plan = create_lap_factor_plan(
        LapConfiguration.SINGLE_LAP if form is DCTNForm.W_I else LapConfiguration.DOUBLE_LAP
    )
    if requested is not None and requested != plan.applicable_in_plane_frp_factor:
        raise ValueError("DCTN_WI_SINGLE_LAP_FACTOR_REQUIRED")
    return plan.applicable_in_plane_frp_factor


@dataclass(frozen=True, slots=True)
class DCTNBearingResult:
    owner_id: str
    bolt_id: str
    demand: PhysicalQuantity
    characteristic_property_original: PhysicalQuantity
    characteristic_property_effective: PhysicalQuantity
    closed_section_factor_applied: bool
    native_trace: BearingTrace
    comparison: ResistanceComparison


def evaluate_dctn_bearing(
    *,
    owner_id: str,
    bolt_id: str,
    incoming_form: DCTNForm,
    designated_rhs_wall: bool,
    thickness: PhysicalQuantity,
    diameter: PhysicalQuantity,
    demand: PhysicalQuantity,
    characteristic: PhysicalQuantity,
    property_kind: FRPPropertyKind,
    qualification: QualificationStatus,
    factors: EndUseFactors,
    thread: ThreadStatus,
    c_delta: Decimal,
    lambda_factor: Decimal,
) -> DCTNBearingResult:
    """Only the actual RHS-wall path gets 0.50; Channel properties are not RHS properties."""
    if designated_rhs_wall and incoming_form is not DCTNForm.RHS:
        raise ValueError("DCTN_RHS_FACTOR_OWNER_MISMATCH")
    effective = (
        characteristic_bearing(characteristic, incoming_form)
        if designated_rhs_wall
        else characteristic
    )
    adjusted: EndUsePropertyTrace = adjust_frp_property(
        property_kind, effective, qualification, factors
    )
    trace = pin_bearing_resistance(
        thickness,
        diameter,
        adjusted,
        thread,
        c_delta=c_delta,
        c_lap=local_lap_factor(incoming_form),
        lambda_factor=lambda_factor,
    )
    return DCTNBearingResult(
        owner_id,
        bolt_id,
        demand,
        characteristic,
        effective,
        designated_rhs_wall,
        trace,
        compare_resistance(demand, trace.factor_trace.design_resistance),
    )


@dataclass(frozen=True, slots=True)
class DCTNRequiredCheck:
    check_id: str
    owner_id: str
    status: str
    demand: PhysicalQuantity | None
    resistance: PhysicalQuantity | None
    native_trace: object
    source_reference: str
    reason: str | None = None

    def __post_init__(self) -> None:
        if (
            not self.check_id
            or not self.owner_id
            or self.status
            not in {
                "PASS",
                "FAIL",
                "SOURCE_REQUIRED",
                "NOT_APPLICABLE",
            }
        ):
            raise ValueError("DCTN requires identified local checks with a closed status")
        if self.status in {"PASS", "FAIL"}:
            if self.demand is None or self.resistance is None:
                raise ValueError("Evaluated DCTN checks require numerical demand and resistance")
            comparison = compare_resistance(self.demand, self.resistance)
            if comparison.numerical_comparison.value != self.status:
                raise ValueError("DCTN check status must reproduce the native comparison")


def aggregate_dctn_checks(checks: tuple[DCTNRequiredCheck, ...], blockers: tuple[str, ...]) -> str:
    if any(check.status == "FAIL" for check in checks):
        return "FAIL"
    if blockers or not checks or any(check.status == "SOURCE_REQUIRED" for check in checks):
        return "ENGINEERING_REVIEW_REQUIRED"
    return "PASS"
