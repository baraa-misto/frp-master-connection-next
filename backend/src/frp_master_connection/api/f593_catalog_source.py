"""Strict source validation at the API boundary; framework-free catalog values go inward."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, StrictStr, model_validator

from frp_master_connection.application.f593_catalog import (
    CATALOG_DIGEST,
    CatalogData,
    CatalogRowData,
)
from frp_master_connection.calculation import PhysicalQuantity, Unit


class CatalogRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    row_id: StrictStr
    condition: Literal["AF", "A", "CW1", "CW2"]
    marking: StrictStr
    diameter_min: StrictStr
    diameter_max: StrictStr
    tensile_min: StrictStr
    tensile_max: StrictStr
    design_fnt: StrictStr
    yield_min: StrictStr
    hardness_basis: StrictStr

    @model_validator(mode="after")
    def validate_row(self) -> Self:
        quantities = [
            PhysicalQuantity.of(v, Unit.KSI).magnitude
            for v in (self.tensile_min, self.tensile_max, self.design_fnt, self.yield_min)
        ]
        low = PhysicalQuantity.of(self.diameter_min, Unit.IN).magnitude
        high = PhysicalQuantity.of(self.diameter_max, Unit.IN).magnitude
        if low <= 0 or high < low or min(quantities) <= 0:
            raise ValueError("Invalid F593 property or diameter range.")
        if quantities[1] < quantities[0] or quantities[2] != quantities[0]:
            raise ValueError("F593 design Fnt must be the lower specified tensile bound.")
        markings = {"AF": "F593E", "A": "F593F", "CW1": "F593G", "CW2": "F593H"}
        if self.row_id != f"G2-{self.condition}" or self.marking != markings[self.condition]:
            raise ValueError("F593 row identity/condition/marking mismatch.")
        if not self.hardness_basis.strip():
            raise ValueError("F593 hardness provenance is required.")
        return self


class ControlledCatalog(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    id: Literal["ASTM_F593_17_GROUP_2_316_316L_RC1"]
    specification: Literal["ASTM F593"]
    edition: Literal["17"]
    alloy_group: Literal["2"]
    alloys: tuple[Literal["316"], Literal["316L"]]
    alloy_type: Literal["Austenitic"]
    source_classification: Literal["OWNER_APPROVED_ASTMF593_TABLE_TRANSCRIPTION_RC1"]
    source_revision: Literal["SHEAR01-DIRECT-OR2-F4"]
    owner_approval: StrictStr
    catalog_revision: Literal["RC1"]
    diameter_unit: Literal["in"]
    stress_unit: Literal["ksi"]
    rows: tuple[CatalogRow, ...]

    @model_validator(mode="after")
    def validate_rows(self) -> Self:
        if not self.owner_approval.strip():
            raise ValueError("F593 owner approval provenance is required.")
        if len(self.rows) != 4 or {r.condition for r in self.rows} != {"AF", "A", "CW1", "CW2"}:
            raise ValueError("F593 requires exactly four unique controlled rows.")
        cw = sorted(
            (r for r in self.rows if r.condition.startswith("CW")),
            key=lambda r: Decimal(r.diameter_min),
        )
        if Decimal(cw[0].diameter_max) >= Decimal(cw[1].diameter_min):
            raise ValueError("F593 cold-worked diameter rows overlap.")
        return self


def catalog_digest(data: object) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def validate_catalog(data: object, expected_digest: str = CATALOG_DIGEST) -> CatalogData:
    # Validate structure before digest so malformed, even internally rehashed, data fails closed.
    parsed = ControlledCatalog.model_validate_json(json.dumps(data))
    if catalog_digest(data) != expected_digest or expected_digest != CATALOG_DIGEST:
        raise ValueError("F593 controlled catalog digest mismatch.")
    record = parsed.model_dump()
    record["rows"] = tuple(CatalogRowData(**row) for row in record["rows"])
    return CatalogData(**record)


def controlled_catalog() -> CatalogData:
    data = json.loads(
        Path(__file__)
        .parent.parent.joinpath("data/astm_f593_group2_rc1.json")
        .read_text(encoding="utf-8")
    )
    return validate_catalog(data)
