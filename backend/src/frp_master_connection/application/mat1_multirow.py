"""Versioned MAT1 successor request for the native multi-row engine."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace

from frp_master_connection.application.f593_catalog import CatalogBinding
from frp_master_connection.application.multirow_orchestration import MultiRowOrchestrationRequest
from frp_master_connection.calculation.properties import FastenerSnapshot, MaterialPropertySnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class MAT1MultiRowRequest(MultiRowOrchestrationRequest):
    """Carry one explicitly bound FRP source without changing legacy request bytes."""

    mat1_material: MaterialPropertySnapshot
    or1_fastener: FastenerSnapshot | None = None
    f593_catalog_binding: CatalogBinding | None = None


def bind_multirow_material(
    legacy: MultiRowOrchestrationRequest,
    material: MaterialPropertySnapshot,
    fastener: FastenerSnapshot | None = None,
    catalog_binding: CatalogBinding | None = None,
) -> MAT1MultiRowRequest:
    """Construct a successor request; legacy fields and mechanics remain identical."""

    if not isinstance(material, MaterialPropertySnapshot):
        raise TypeError("MAT1 multi-row material must be a typed snapshot.")
    values = {field.name: getattr(legacy, field.name) for field in fields(legacy)}
    values["layers"] = tuple(replace(layer, material_id=material.id) for layer in legacy.layers)
    if catalog_binding is not None and not legacy.direct_finalization_mode:
        raise ValueError("F4 catalog binding requires the Direct finalization contract.")
    return MAT1MultiRowRequest(
        **values,
        mat1_material=material,
        or1_fastener=fastener,
        f593_catalog_binding=catalog_binding,
    )
