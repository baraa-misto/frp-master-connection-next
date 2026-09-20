"""CME-1 immutable connector-only material and source-applicability contracts.

These records describe readiness, not stainless mechanical properties or capacity.
Approval is supplied by a trusted application catalogue, never by a request label.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction

from frp_master_connection.calculation.quantities import Dimension, PhysicalQuantity


class ComponentRole(StrEnum):
    PRIMARY_MEMBER = "PRIMARY_MEMBER"
    CONNECTOR_BODY = "CONNECTOR_BODY"
    MEMBER_REINFORCEMENT = "MEMBER_REINFORCEMENT"
    FASTENER_OR_HARDWARE = "FASTENER_OR_HARDWARE"
    FOUNDATION = "FOUNDATION"
    UNCLASSIFIED = "UNCLASSIFIED"


class ConnectorMaterial(StrEnum):
    FRP = "FRP"
    SS316 = "SS316"


class Fabrication(StrEnum):
    PULTRUDED = "PULTRUDED"
    PLATE_CUT = "PLATE_CUT"
    FORMED_BENT = "FORMED_BENT"
    HOT_FINISHED = "HOT_FINISHED"
    EXTRUDED = "EXTRUDED"
    WELDED_BUILT_UP = "WELDED_BUILT_UP"
    LASER_WELDED = "LASER_WELDED"
    SOURCE_DEFINED = "SOURCE_DEFINED"
    NOT_SPECIFIED = "NOT_SPECIFIED"


class Readiness(StrEnum):
    METADATA_IDENTIFIED = "METADATA_IDENTIFIED"
    NORMATIVE_CONTENT_VERIFIED = "NORMATIVE_CONTENT_VERIFIED"
    PROPERTY_RECORD_VERIFIED = "PROPERTY_RECORD_VERIFIED"
    METHOD_VERIFIED = "METHOD_VERIFIED"
    FAMILY_ADAPTER_VERIFIED = "FAMILY_ADAPTER_VERIFIED"
    RESPONSE_APPLICABLE = "RESPONSE_APPLICABLE"
    REQUIRED_COVERAGE_COMPLETE = "REQUIRED_COVERAGE_COMPLETE"


def text_required(*values: str) -> None:
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("Nonempty source/physical identity text is required")


@dataclass(frozen=True, slots=True)
class MaterialDescriptor:
    family: ConnectorMaterial = ConnectorMaterial.FRP
    grade: str = "PULTRUDED_FRP"
    stock_specification: str = "EXISTING_NATIVE_FRP_AUTHORITY"
    edition: str = "NATIVE"
    fabrication: Fabrication = Fabrication.PULTRUDED
    condition: str = "NATIVE_LOCKED_RECORD"
    source_reference: str | None = None
    method_version: str = "NATIVE_FRP"

    def __post_init__(self) -> None:
        if not isinstance(self.family, ConnectorMaterial) or not isinstance(
            self.fabrication, Fabrication
        ):
            raise TypeError("Material family and fabrication require declared enum values")
        text_required(
            self.grade, self.stock_specification, self.edition, self.condition, self.method_version
        )
        if self.source_reference is not None:
            text_required(self.source_reference)
        if self.family is ConnectorMaterial.SS316 and self.grade not in {
            "316",
            "316L",
            "316/316L_DUAL_CERTIFIED",
        }:
            raise ValueError(
                "316, 316L and explicitly dual-certified are distinct grade identities"
            )
        if self.family is ConnectorMaterial.FRP and self.grade != "PULTRUDED_FRP":
            raise ValueError("CME-1 does not change the native FRP material identity")
        if self.family is ConnectorMaterial.SS316 and self.fabrication is Fabrication.PULTRUDED:
            raise ValueError("Stainless fabrication cannot be FRP pultrusion")


@dataclass(frozen=True, slots=True)
class CanonicalComponent:
    physical_id: str
    role: ComponentRole
    body_form: str
    aliases: tuple[str, ...] = ()
    applicability: str = "NATIVE_SCOPE_ONLY"
    material: MaterialDescriptor = MaterialDescriptor()

    def __post_init__(self) -> None:
        text_required(self.physical_id, self.body_form, self.applicability, *self.aliases)
        if not isinstance(self.role, ComponentRole):
            raise TypeError("Canonical role must be explicit")
        if not isinstance(self.material, MaterialDescriptor):
            raise TypeError("Canonical connector-material metadata must be typed")
        if not isinstance(self.aliases, tuple) or len(set(self.aliases)) != len(self.aliases):
            raise ValueError("Aliases must be an immutable unique tuple")
        if (
            self.role is not ComponentRole.CONNECTOR_BODY
            and self.material.family is not ConnectorMaterial.FRP
        ):
            raise ValueError("Connector material metadata cannot convert another component role")


@dataclass(frozen=True, slots=True)
class PropertyDomain:
    """One original source-table value; display units never select another table."""

    property_name: str
    value: PhysicalQuantity
    lower_size: PhysicalQuantity
    upper_size: PhysicalQuantity
    original_table_unit: str

    def __post_init__(self) -> None:
        text_required(self.property_name, self.original_table_unit)
        if not all(
            isinstance(q, PhysicalQuantity) for q in (self.value, self.lower_size, self.upper_size)
        ):
            raise TypeError("Properties and bounds require native finite physical quantities")
        if self.original_table_unit != self.value.unit.value:
            raise ValueError("The original source-table unit must match the stored value")
        if (
            self.lower_size.dimension is not Dimension.LENGTH
            or self.upper_size.dimension is not Dimension.LENGTH
            or self.lower_size.canonical_magnitude <= 0
            or self.lower_size.canonical_magnitude > self.upper_size.canonical_magnitude
        ):
            raise ValueError("Invalid positive closed size domain")
        if self.value.canonical_magnitude <= 0:
            raise ValueError("A missing property is unavailable, never a zero strength")


@dataclass(frozen=True, slots=True)
class SourceDescriptor:
    source_id: str
    revision: str
    document_edition: str
    clause: str
    approval_scope: str
    content_sha256: str
    material: MaterialDescriptor
    readiness: tuple[Readiness, ...]
    properties: tuple[PropertyDomain, ...] = ()
    environment_domain: str = "NOT_QUALIFIED"
    assembly_restrictions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        text_required(
            self.source_id,
            self.revision,
            self.document_edition,
            self.clause,
            self.approval_scope,
            self.environment_domain,
        )
        if not isinstance(self.material, MaterialDescriptor):
            raise TypeError("Source material must be typed")
        if not isinstance(self.properties, tuple) or any(
            not isinstance(p, PropertyDomain) for p in self.properties
        ):
            raise TypeError("Source properties must be an immutable typed tuple")
        if not isinstance(self.assembly_restrictions, tuple):
            raise TypeError("Assembly restrictions must be immutable")
        text_required(*self.assembly_restrictions)
        if not isinstance(self.content_sha256, str):
            raise TypeError("Source SHA-256 must be text")
        if len(self.content_sha256) != 64 or any(
            c not in "0123456789abcdefABCDEF" for c in self.content_sha256
        ):
            raise ValueError(
                "A source identity requires its exact SHA-256; a hash alone is not approval"
            )
        if not isinstance(self.readiness, tuple) or any(
            not isinstance(v, Readiness) for v in self.readiness
        ):
            raise TypeError("Readiness requires explicit immutable provenance states")
        if self.properties and Readiness.PROPERTY_RECORD_VERIFIED not in self.readiness:
            raise ValueError("Publisher metadata cannot supply numerical property authority")
        for i, a in enumerate(self.properties):
            for b in self.properties[i + 1 :]:
                if (
                    a.property_name == b.property_name
                    and a.lower_size.dimension == b.lower_size.dimension
                    and max(a.lower_size.canonical_magnitude, b.lower_size.canonical_magnitude)
                    <= min(a.upper_size.canonical_magnitude, b.upper_size.canonical_magnitude)
                ):
                    raise ValueError("Ambiguous overlapping property domains")


@dataclass(frozen=True, slots=True)
class ResponseSignature:
    """Exact source domain, independent of a display-unit or viewer state."""

    materials: tuple[tuple[str, MaterialDescriptor], ...]
    geometry: str
    attachment: str
    boundary_conditions: str
    load_sign_domain: str
    method_version: str
    environment_domain: str = "NATIVE_ENVIRONMENT_DOMAIN"

    def __post_init__(self) -> None:
        text_required(
            self.geometry,
            self.attachment,
            self.boundary_conditions,
            self.load_sign_domain,
            self.method_version,
            self.environment_domain,
        )
        ids = tuple(key for key, _ in self.materials)
        text_required(*ids)
        if not isinstance(self.materials, tuple) or len(set(ids)) != len(ids):
            raise ValueError("Response material signatures require unique physical identities")
        if any(not isinstance(material, MaterialDescriptor) for _, material in self.materials):
            raise TypeError("Response materials must be typed")


@dataclass(frozen=True, slots=True)
class ResponseRevalidation:
    applicable: bool
    derived_response_available: bool
    known_external_action_preserved: bool = True
    branch_force: None = None
    contact_force: None = None
    prying_force: None = None


def revalidate_response(
    source: ResponseSignature, actual: ResponseSignature
) -> ResponseRevalidation:
    """Compare every source-bound field; no material substitution or allocation solver."""
    material_equal = dict(source.materials) == dict(actual.materials)
    matches = material_equal and (
        source.geometry,
        source.attachment,
        source.boundary_conditions,
        source.load_sign_domain,
        source.method_version,
        source.environment_domain,
    ) == (
        actual.geometry,
        actual.attachment,
        actual.boundary_conditions,
        actual.load_sign_domain,
        actual.method_version,
        actual.environment_domain,
    )
    return ResponseRevalidation(matches, matches)


def exact_ratio(value: PhysicalQuantity) -> Fraction:
    """Identity-preserving provenance utility, never a second numeric projection."""
    return Fraction(value.canonical_magnitude)
