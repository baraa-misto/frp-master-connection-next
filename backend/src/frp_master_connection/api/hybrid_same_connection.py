"""P3 materials-only bridge; no second geometry or uploaded calculation results."""

from dataclasses import asdict
from typing import Self

from pydantic import model_validator

from frp_master_connection.api.fasteners import (
    CatalogFastenerSelectionDTO,
    FastenerSelectionDTO,
    fastener_source_record,
    resolve_catalog_selection,
    resolve_fastener_selection,
)
from frp_master_connection.api.mat1 import (
    MaterialAssignmentsDTO,
    resolve_conditions,
    resolve_material,
)
from frp_master_connection.api.schemas import QuantityDTO, _StrictModel
from frp_master_connection.application.hybrid_same_connection import SameConnectionMaterials
from frp_master_connection.application.mat1_native import adapt_native_material
from frp_master_connection.calculation.properties import FastenerSnapshot
from frp_master_connection.calculation.rhm_direct_r3 import R3Geometry


class SameConnectionLRFD(_StrictModel):
    assignments: MaterialAssignmentsDTO
    fastener: FastenerSelectionDTO

    @model_validator(mode="after")
    def same_physical_owners(self) -> Self:
        a = self.assignments
        if not (set(a.material_overrides) | set(a.condition_overrides)) <= {"member-a", "member-b"}:
            raise ValueError("R3 materials must name the actual Angle/member-a and I/member-b.")
        default = a.default_conditions
        if default.direct_policy != "SHEAR01-DIRECT-MC1" or any(
            c != default for c in a.condition_overrides.values()
        ):
            raise ValueError("Same-connection ASCE requires the existing shared MC1 conditions.")
        return self

    def resolve(self, geometry: R3Geometry) -> SameConnectionMaterials:
        a = self.assignments
        conditions = resolve_conditions(a.default_conditions)
        adapters = [
            adapt_native_material(
                owner,
                resolve_material(a.material_overrides.get(owner, a.default_material)),
                conditions,
                shape_binding_verified=True,
            )
            for owner in ("member-a", "member-b")
        ]
        fastener: FastenerSnapshot | None
        if isinstance(self.fastener, CatalogFastenerSelectionDTO):
            binding = resolve_catalog_selection(
                self.fastener,
                QuantityDTO(
                    value=str(geometry.diameter.magnitude),
                    unit=geometry.diameter.unit,
                ),
            )
            fastener, hardware = binding.fastener, binding.source_record
        else:
            fastener = resolve_fastener_selection(self.fastener)
            hardware = fastener_source_record(self.fastener)
        return SameConnectionMaterials(
            adapters[0],
            adapters[1],
            conditions.time_category,
            fastener,
            {
                "assignments": self.assignments.model_dump(mode="json"),
                "conditions": asdict(conditions),
                "fastener": hardware,
                "resolved_materials": [asdict(x) for x in adapters],
            },
        )
