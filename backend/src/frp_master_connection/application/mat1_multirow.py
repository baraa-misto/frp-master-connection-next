"""Versioned MAT1 successor request for the native multi-row engine."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace

from frp_master_connection.application.multirow_orchestration import MultiRowOrchestrationRequest
from frp_master_connection.calculation.properties import MaterialPropertySnapshot


@dataclass(frozen=True, slots=True, kw_only=True)
class MAT1MultiRowRequest(MultiRowOrchestrationRequest):
    """Carry one explicitly bound FRP source without changing legacy request bytes."""

    mat1_material: MaterialPropertySnapshot


def bind_multirow_material(
    legacy: MultiRowOrchestrationRequest, material: MaterialPropertySnapshot
) -> MAT1MultiRowRequest:
    """Construct a successor request; legacy fields and mechanics remain identical."""

    if not isinstance(material, MaterialPropertySnapshot):
        raise TypeError("MAT1 multi-row material must be a typed snapshot.")
    values = {field.name: getattr(legacy, field.name) for field in fields(legacy)}
    values["layers"] = tuple(replace(layer, material_id=material.id) for layer in legacy.layers)
    return MAT1MultiRowRequest(**values, mat1_material=material)
