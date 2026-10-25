"""Strict current physical data; no uploaded result, source approval or qualification."""

from copy import deepcopy
from typing import Annotated, Any, Literal, Self, cast

from pydantic import Field, model_validator

from frp_master_connection.api.schemas import Identifier, QuantityDTO, _StrictModel
from frp_master_connection.application.hybrid_physical import (
    PhysicalInputs,
    ReceivingAdditionalActions,
    SixActions,
)
from frp_master_connection.application.hybrid_physical_geometry import (
    EndCondition,
    ReceivingEnd,
    ReceivingEnds,
)
from frp_master_connection.calculation.quantities import (
    PhysicalQuantity,
    PublishedCodeUnitBasis,
    Unit,
    canonical_decimal_string,
)


def _quantity(value: QuantityDTO) -> PhysicalQuantity:
    return PhysicalQuantity.of(value.value, value.unit)


class ReceivingEndDTO(_StrictModel):
    condition: Literal["UNKNOWN", "CONTINUOUS", "FREE"] = "UNKNOWN"
    distance: QuantityDTO | None = None

    @model_validator(mode="after")
    def actual_end(self) -> Self:
        ReceivingEnd(
            EndCondition(self.condition),
            None if self.distance is None else _quantity(self.distance),
        )
        return self

    def resolved(self) -> ReceivingEnd:
        return ReceivingEnd(
            EndCondition(self.condition),
            None if self.distance is None else _quantity(self.distance),
        )


class ReceivingActionsDTO(_StrictModel):
    case_id: Identifier
    components: tuple[
        QuantityDTO | None,
        QuantityDTO | None,
        QuantityDTO | None,
        QuantityDTO | None,
        QuantityDTO | None,
        QuantityDTO | None,
    ]

    @model_validator(mode="after")
    def known_dimensions(self) -> Self:
        for i, value in enumerate(self.components):
            if value is not None:
                _quantity(value).to(Unit.N if i < 3 else Unit.N_MM)
        return self


class PhysicalInputsDTO(_StrictModel):
    contract: Literal["HYB2-D3-P4-PHYSICAL/1"]
    positive_end: ReceivingEndDTO = Field(default_factory=ReceivingEndDTO)
    negative_end: ReceivingEndDTO = Field(default_factory=ReceivingEndDTO)
    hole_source: Literal["US_CUSTOMARY_PRINTED", "SI_PRINTED"] | None = None
    clear_flat_outstand: QuantityDTO | None = None
    interface_gap: QuantityDTO | None = None
    receiving_actions: Annotated[tuple[ReceivingActionsDTO, ...], Field(max_length=8)] = ()

    @model_validator(mode="after")
    def finite_geometry_and_cases(self) -> Self:
        for name, value in (
            ("Clear flat outstand", self.clear_flat_outstand),
            ("Interface gap", self.interface_gap),
        ):
            if value is not None:
                magnitude = _quantity(value).to(Unit.IN).magnitude
                if magnitude < 0 or (name == "Clear flat outstand" and magnitude == 0):
                    raise ValueError(name + " requires a valid measured length.")
        ids = [case.case_id for case in self.receiving_actions]
        if len(set(ids)) != len(ids):
            raise ValueError("Additional receiving-action case IDs must be unique.")
        if (
            self.positive_end.condition == "FREE"
            and self.negative_end.condition == "FREE"
            and self.positive_end.distance is not None
            and self.negative_end.distance is not None
            and _quantity(self.positive_end.distance).magnitude == 0
            and _quantity(self.negative_end.distance).magnitude == 0
        ):
            raise ValueError("The receiving member must have positive longitudinal extent.")
        return self

    def resolved(self) -> PhysicalInputs:
        return PhysicalInputs(
            ReceivingEnds(self.positive_end.resolved(), self.negative_end.resolved()),
            None if self.hole_source is None else PublishedCodeUnitBasis(self.hole_source),
            None if self.clear_flat_outstand is None else _quantity(self.clear_flat_outstand),
            None if self.interface_gap is None else _quantity(self.interface_gap),
            tuple(
                ReceivingAdditionalActions(
                    case.case_id,
                    cast(
                        SixActions,
                        tuple(None if q is None else _quantity(q) for q in case.components),
                    ),
                )
                for case in self.receiving_actions
            ),
        )


def physical_fingerprint_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """Normalize supported quantity representations; retain every other input.

    The strict DTO has already validated all quantities and fields. Source unit
    identity, unknowns, provenance, methods, case IDs, materials and all six
    actions remain operands. This function receives no client fingerprint/result.
    """

    def normalized(value: object) -> object:
        if isinstance(value, list):
            return [normalized(item) for item in value]
        if not isinstance(value, dict):
            return value
        if set(value) == {"value", "unit"}:
            try:
                unit = Unit(value["unit"])
            except ValueError:
                return value
            quantity = PhysicalQuantity.of(value["value"], unit)
            return {
                "physical_dimension": quantity.dimension.value,
                "canonical_magnitude": canonical_decimal_string(quantity.canonical_magnitude),
            }
        return {key: normalized(item) for key, item in value.items()}

    return cast(dict[str, Any], normalized(deepcopy(inputs)))
