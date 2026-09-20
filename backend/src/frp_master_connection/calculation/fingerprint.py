"""Canonical SHA-256 fingerprints for Stage 2.1A engineering inputs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import cast

from frp_master_connection.calculation.inputs import ResolvedSingleBoltDemand
from frp_master_connection.calculation.properties import (
    FastenerSnapshot,
    MaterialPropertySnapshot,
)
from frp_master_connection.calculation.quantities import (
    PhysicalQuantity,
    canonical_decimal_string,
    decimal_from_finite_real,
)
from frp_master_connection.geometry.spatial import CartesianFrame3D, UnitVector3D, Vector3D

type CanonicalValue = str | bool | dict[str, "CanonicalValue"] | list["CanonicalValue"] | None


@dataclass(frozen=True, slots=True)
class UnorderedFingerprintCollection:
    """A semantically unordered collection sorted by each item's stable ID."""

    items: tuple[object, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.items, tuple):
            raise TypeError("Unordered fingerprint items must be an immutable tuple.")
        ids = [_stable_id(item) for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Unordered fingerprint collection IDs must be unique.")


@dataclass(frozen=True, slots=True)
class CalculationFingerprintInput:
    """Explicit calculation-relevant fields included in the Stage 2.1A digest."""

    standard: str
    edition: str
    errata: str
    interpretation_ids: tuple[str, ...]
    project_schema_version: str
    calculation_contract_version: str
    calculation_engine_version: str
    material_snapshot: MaterialPropertySnapshot
    fastener_snapshot: FastenerSnapshot
    physical_geometry: object
    code_variable_mapping: object
    demand: ResolvedSingleBoltDemand | object
    factor_selections: object
    lap_configuration: object
    thread_statuses: object
    published_code_unit_bases: tuple[object, ...]
    readiness_decisions: object

    def __post_init__(self) -> None:
        text = (
            self.standard,
            self.edition,
            self.errata,
            self.project_schema_version,
            self.calculation_contract_version,
            self.calculation_engine_version,
        )
        if any(not value.strip() for value in text):
            raise ValueError("Fingerprint version/source identities must be nonempty.")


@dataclass(frozen=True, slots=True)
class FingerprintEnvelope:
    """Calculation input plus explicitly excluded presentation/commercial metadata."""

    calculation_input: CalculationFingerprintInput
    display_unit_profile: str | None = None
    display_rounding: str | None = None
    formatted_strings: tuple[str, ...] = ()
    camera: object | None = None
    color: str | None = None
    visibility: object | None = None
    selected_ui_tab: str | None = None
    report_profile: str | None = None
    project_owner: str | None = None
    organization: str | None = None
    entitlement: str | None = None
    billing: str | None = None
    nonengineering_timestamp: str | None = None


def _stable_id(item: object) -> str:
    identity = item.get("id") if isinstance(item, Mapping) else getattr(item, "id", None)
    if not isinstance(identity, str) or not identity:
        raise ValueError("An unordered fingerprint item requires a nonempty string ID.")
    return identity


def _vector_payload(vector: Vector3D | UnitVector3D) -> CanonicalValue:
    return cast(
        CanonicalValue,
        {
            "x": canonical_decimal_string(decimal_from_finite_real(vector.x)),
            "y": canonical_decimal_string(decimal_from_finite_real(vector.y)),
            "z": canonical_decimal_string(decimal_from_finite_real(vector.z)),
        },
    )


def _frame_payload(frame: CartesianFrame3D) -> CanonicalValue:
    return cast(
        CanonicalValue,
        {
            "origin": {
                "x": canonical_decimal_string(decimal_from_finite_real(frame.origin.x)),
                "y": canonical_decimal_string(decimal_from_finite_real(frame.origin.y)),
                "z": canonical_decimal_string(decimal_from_finite_real(frame.origin.z)),
            },
            "x_axis": _vector_payload(frame.x_axis),
            "y_axis": _vector_payload(frame.y_axis),
            "z_axis": _vector_payload(frame.z_axis),
        },
    )


def _material_payload(snapshot: MaterialPropertySnapshot) -> CanonicalValue:
    return cast(
        CanonicalValue,
        {
            "id": snapshot.id,
            "locked": snapshot.locked,
            "basis": snapshot.basis.value,
            "qualification_statuses": [status.value for status in snapshot.qualification_statuses],
            "properties": [
                {
                    "kind": entry.kind.value,
                    "value": _canonicalize(entry.value),
                    "behavior": entry.behavior.value,
                    "source_classification": entry.source_classification.value,
                    "qualification_status": entry.qualification_status.value,
                    "source_document": entry.source_document,
                    "source_revision": entry.source_revision,
                    "applicability_metadata": list(entry.applicability_metadata),
                    "use_in_chapter_8_equations": entry.use_in_chapter_8_equations,
                }
                for entry in snapshot.properties
            ],
            "explicitly_missing": [kind.value for kind in snapshot.explicitly_missing],
        },
    )


def _fastener_payload(snapshot: FastenerSnapshot) -> CanonicalValue:
    return cast(
        CanonicalValue,
        {
            "id": snapshot.id,
            "locked": snapshot.locked,
            "bolt_specification": snapshot.bolt_specification,
            "alloy_group": snapshot.alloy_group,
            "alloys": list(snapshot.alloys),
            "condition": snapshot.condition,
            "nut_specification": snapshot.nut_specification,
            "washer_material_basis": snapshot.washer_material_basis,
            "installation_condition": snapshot.installation_condition,
            "diameter_min": _canonicalize(snapshot.diameter_min),
            "diameter_max": _canonicalize(snapshot.diameter_max),
            "fnt": _canonicalize(snapshot.fnt),
            "fnt_source_classification": snapshot.fnt_source_classification.value,
            "fnt_qualification_status": snapshot.fnt_qualification_status.value,
            "shear_plane_thread_statuses": _canonicalize(snapshot.shear_plane_thread_statuses),
            "bearing_layer_thread_statuses": _canonicalize(snapshot.bearing_layer_thread_statuses),
            "number_of_shear_planes": str(snapshot.number_of_shear_planes),
            "washer_geometry": _canonicalize(snapshot.washer_geometry),
        },
    )


def _demand_payload(demand: ResolvedSingleBoltDemand) -> CanonicalValue:
    return cast(
        CanonicalValue,
        {
            "id": demand.id,
            "load_combination_id": demand.load_combination_id,
            "source_member_id": demand.source_member_id,
            "source_action_id": demand.source_action_id,
            "source_kind": demand.source_kind.value,
            "factored_action_confirmed": demand.factored_action_confirmed,
            "coordinate_frame_reference": demand.coordinate_frame_reference,
            "resolved_frame": _frame_payload(demand.resolved_frame),
            "source_reference_point_id": demand.source_reference_point_id,
            "resolved_global_reference_point": {
                "x": canonical_decimal_string(
                    decimal_from_finite_real(demand.resolved_global_reference_point.x)
                ),
                "y": canonical_decimal_string(
                    decimal_from_finite_real(demand.resolved_global_reference_point.y)
                ),
                "z": canonical_decimal_string(
                    decimal_from_finite_real(demand.resolved_global_reference_point.z)
                ),
            },
            "in_plane_force_vector": _vector_payload(demand.in_plane_force_vector),
            "force_vector_unit": demand.force_vector_unit.value,
            "in_plane_force_magnitude": _canonicalize(demand.in_plane_force_magnitude),
            "bolt_axis_tensile_demand": _canonicalize(demand.bolt_axis_tensile_demand),
            "externally_supplied_prying_demand": _canonicalize(
                demand.externally_supplied_prying_demand
            ),
            "loading_sense": demand.loading_sense.value,
            "provenance": list(demand.provenance),
            "distribution_status": demand.distribution_status.value,
        },
    )


def _canonicalize(value: object) -> CanonicalValue:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, PhysicalQuantity):
        return {
            "dimension": value.dimension.value,
            "unit": value.canonical_unit.value,
            "value": value.canonical_string,
        }
    if isinstance(value, Decimal):
        return canonical_decimal_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        raise TypeError("Raw floating-point values are prohibited in fingerprint payloads.")
    if isinstance(value, Enum):
        if not isinstance(value.value, str):
            raise TypeError("Fingerprint enum values must be stable strings.")
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, MaterialPropertySnapshot):
        return _material_payload(value)
    if isinstance(value, FastenerSnapshot):
        return _fastener_payload(value)
    if isinstance(value, ResolvedSingleBoltDemand):
        return _demand_payload(value)
    if isinstance(value, CartesianFrame3D):
        return _frame_payload(value)
    if isinstance(value, (Vector3D, UnitVector3D)):
        return _vector_payload(value)
    if isinstance(value, UnorderedFingerprintCollection):
        return [_canonicalize(item) for item in sorted(value.items, key=_stable_id)]
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("Fingerprint object keys must be strings.")
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _canonicalize(getattr(value, field.name)) for field in fields(value)}
    raise TypeError(f"Unsupported fingerprint value type: {type(value).__name__}.")


def canonical_fingerprint_json(
    value: CalculationFingerprintInput | FingerprintEnvelope,
) -> str:
    """Return compact sorted UTF-8 JSON content used by the digest."""

    calculation_input = value.calculation_input if isinstance(value, FingerprintEnvelope) else value
    if not isinstance(calculation_input, CalculationFingerprintInput):
        raise TypeError("Fingerprinting requires a CalculationFingerprintInput or envelope.")
    payload = _canonicalize(calculation_input)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def calculation_fingerprint(
    value: CalculationFingerprintInput | FingerprintEnvelope,
) -> str:
    """Return lowercase SHA-256 over canonical UTF-8 JSON."""

    content = canonical_fingerprint_json(value).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


__all__ = (
    "CalculationFingerprintInput",
    "FingerprintEnvelope",
    "UnorderedFingerprintCollection",
    "calculation_fingerprint",
    "canonical_fingerprint_json",
)
