"""Owner-approved F593 transcription; trusted catalog inputs, never a bolt calculator."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from typing import Any, Literal, cast

from frp_master_connection.calculation import (
    FastenerSnapshot,
    PhysicalQuantity,
    QualificationStatus,
    SourceClassification,
    ThreadStatus,
    ThreadStatusAssignment,
    Unit,
    create_locked_f593_fastener_snapshot,
)
from frp_master_connection.calculation.equations import f593_nominal_shear_stress
from frp_master_connection.calculation.quantities import canonical_decimal_string

CATALOG_ID = "ASTM_F593_17_GROUP_2_316_316L_RC1"
CATALOG_DIGEST = "ecb9ca81764f33f5926b2404870322d82325558855ba03f5b077b692e1c7b9ec"
SOURCE_CLASSIFICATION = "OWNER_APPROVED_ASTMF593_TABLE_TRANSCRIPTION_RC1"
Condition = Literal["COLD_WORKED", "AF", "A", "CW1", "CW2"]


@dataclass(frozen=True, slots=True)
class CatalogRowData:
    row_id: str
    condition: Literal["AF", "A", "CW1", "CW2"]
    marking: str
    diameter_min: str
    diameter_max: str
    tensile_min: str
    tensile_max: str
    design_fnt: str
    yield_min: str
    hardness_basis: str

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CatalogData:
    id: Literal["ASTM_F593_17_GROUP_2_316_316L_RC1"]
    specification: Literal["ASTM F593"]
    edition: Literal["17"]
    alloy_group: Literal["2"]
    alloys: tuple[Literal["316"], Literal["316L"]]
    alloy_type: Literal["Austenitic"]
    source_classification: Literal["OWNER_APPROVED_ASTMF593_TABLE_TRANSCRIPTION_RC1"]
    source_revision: Literal["SHEAR01-DIRECT-OR2-F4"]
    owner_approval: str
    catalog_revision: Literal["RC1"]
    diameter_unit: Literal["in"]
    stress_unit: Literal["ksi"]
    rows: tuple[CatalogRowData, ...]

    def model_dump(self, *, mode: str = "json") -> dict[str, Any]:
        """Serialize immutable source values for the server trace."""
        return cast(dict[str, Any], json.loads(json.dumps(asdict(self))))


@dataclass(frozen=True, slots=True)
class CatalogPlane:
    plane_id: str
    thread_status: Literal["EXCLUDED", "INCLUDED", "UNKNOWN"]


@dataclass(frozen=True, slots=True)
class CatalogBinding:
    """Produced only from server catalog data and physical request selectors."""

    fastener: FastenerSnapshot
    source_record: dict[str, object]


def bind_f593_catalog(
    diameter: PhysicalQuantity,
    planes: tuple[CatalogPlane, ...],
    *,
    catalog: CatalogData,
    revision: str = CATALOG_ID,
    alloy_group: str = "2",
    alloy: str = "316",
    condition: str = "COLD_WORKED",
) -> CatalogBinding:
    if (
        not planes
        or len({p.plane_id for p in planes}) != len(planes)
        or any(
            not p.plane_id or p.thread_status not in {"EXCLUDED", "INCLUDED", "UNKNOWN"}
            for p in planes
        )
    ):
        raise ValueError("F593 requires unique physical shear planes and valid thread states.")
    if diameter.dimension.value != "LENGTH" or diameter.magnitude <= 0:
        raise ValueError("F593 nominal diameter must be a positive length.")
    selectors_valid = (
        revision == catalog.id
        and alloy_group == catalog.alloy_group
        and alloy in catalog.alloys
        and condition in {"COLD_WORKED", "AF", "A", "CW1", "CW2"}
    )
    rows = [
        row
        for row in catalog.rows
        if selectors_valid
        and (
            row.condition.startswith("CW")
            if condition == "COLD_WORKED"
            else row.condition == condition
        )
        and PhysicalQuantity.of(row.diameter_min, Unit.IN)
        <= diameter
        <= PhysicalQuantity.of(row.diameter_max, Unit.IN)
    ]
    row = rows[0] if len(rows) == 1 else None
    fnt = PhysicalQuantity.of(row.design_fnt, Unit.KSI) if row is not None else None
    preset = create_locked_f593_fastener_snapshot()
    fastener = replace(
        preset,
        condition=row.condition if row is not None else condition,
        alloys=(alloy,),
        diameter_min=PhysicalQuantity.of(".250", Unit.IN),
        diameter_max=PhysicalQuantity.of("1.500", Unit.IN),
        fnt=fnt,
        fnt_source_classification=(
            SourceClassification.ENGINEER_APPROVED_DEVELOPMENT
            if fnt is not None
            else SourceClassification.SOURCE_PENDING
        ),
        fnt_qualification_status=(
            QualificationStatus.DEVELOPMENT_ONLY
            if fnt is not None
            else QualificationStatus.SOURCE_PENDING
        ),
        shear_plane_thread_statuses=tuple(
            ThreadStatusAssignment(p.plane_id, ThreadStatus(p.thread_status))
            for p in planes
            if p.thread_status != "UNKNOWN"
        ),
        number_of_shear_planes=sum(p.thread_status != "UNKNOWN" for p in planes),
        source_notes=(
            catalog.source_classification,
            catalog.source_revision,
            CATALOG_DIGEST,
            "Owner-approved table transcription; minimum tensile bound; "
            "no whole-connection qualification activation.",
        ),
    )
    plane_records = []
    display_stress_unit = Unit.MPA if diameter.unit is Unit.MM else Unit.KSI
    for plane in planes:
        stress = (
            f593_nominal_shear_stress(fnt, ThreadStatus(plane.thread_status))
            if fnt is not None and plane.thread_status != "UNKNOWN"
            else None
        )
        plane_records.append(
            {
                "plane_id": plane.plane_id,
                "thread_status": plane.thread_status,
                "fnv": None
                if stress is None
                else {"value": str(stress.magnitude), "unit": stress.unit.value},
                "display_fnv": None
                if stress is None
                else {
                    "value": str(stress.to(display_stress_unit).magnitude),
                    "unit": display_stress_unit.value,
                },
                "fnv_rule": "UNRESOLVED"
                if plane.thread_status == "UNKNOWN"
                else "0.6 Fnt"
                if plane.thread_status == "EXCLUDED"
                else "0.5 Fnt",
            }
        )
    reason = (
        ""
        if row is not None
        else (
            "No controlled cold-worked ASTM F593 table row for selected diameter."
            if selectors_valid and condition == "COLD_WORKED"
            else "No controlled ASTM F593 table row for the specification, alloy, "
            "condition and diameter selectors."
        )
    )
    trace: dict[str, object] = {
        "kind": "CATALOG",
        "contract": "FASTENER-F4-RC1",
        "revision": catalog.id,
        "id": preset.id,
        "display_name": "ASTM F593-17 Group 2 — " + alloy,
        "specification": "ASTM F593-17",
        "alloy_group": catalog.alloy_group,
        "alloys": [alloy],
        "condition": fastener.condition,
        "marking": row.marking if row is not None else None,
        "nut": preset.nut_specification,
        "washer_basis": preset.washer_material_basis,
        "installation": preset.installation_condition,
        "fnt": None if fnt is None else {"value": str(fnt.magnitude), "unit": "ksi"},
        "display_fnt": None
        if fnt is None
        else {
            "value": str(fnt.to(display_stress_unit).magnitude),
            "unit": display_stress_unit.value,
        },
        "fnt_state": "CATALOG_SOURCE_RESOLVED" if row is not None else "SOURCE_REQUIRED",
        "qualification": "NUMERICAL_SOURCE_RESOLVED_CONNECTION_QUALIFICATION_UNCHANGED",
        "source_requirement": reason,
        "catalog_record_id": catalog.id,
        "catalog_revision": catalog.catalog_revision,
        "catalog_digest": CATALOG_DIGEST,
        "source_classification": catalog.source_classification,
        "source_revision": catalog.source_revision,
        "owner_approval": catalog.owner_approval,
        "selected_row": row.model_dump() if row is not None else None,
        "nominal_diameter": {"value": str(diameter.magnitude), "unit": diameter.unit.value},
        "exact_diameter_mm": canonical_decimal_string(diameter.to(Unit.MM).magnitude),
        "range_comparison": "INCLUSIVE_MATCH" if row is not None else "NO_CONTROLLED_MATCH",
        "requested_selectors": {
            "revision": revision,
            "alloy_group": alloy_group,
            "alloy": alloy,
            "condition": condition,
        },
        "design_rule": "Minimum/lower specified tensile bound; "
        "ASCE/SEI 74-23 Chapter 8 F593 reference.",
        "shear_planes": plane_records,
        "specification_note": (
            "Specified fastener shall conform to ASTM F593-17, Alloy Group 2, "
            + alloy
            + ", "
            + (
                f"{row.condition}/{row.marking}."
                if row is not None
                else "a controlled condition/marking."
            )
            + " Delivered hardware conformance is procurement/project QA responsibility. "
            "No per-connection supplier certification required."
        ),
    }
    return CatalogBinding(fastener, trace)
