"""CME-1 pure, atomic material planning. No resistance, I/O or force allocation."""

from __future__ import annotations

from dataclasses import dataclass, replace

from frp_master_connection.calculation.angle_connector_core import angle_fingerprint
from frp_master_connection.domain.connector_materials import (
    CanonicalComponent,
    ComponentRole,
    ConnectorMaterial,
    MaterialDescriptor,
    ResponseSignature,
    SourceDescriptor,
    text_required,
)

CONTRACT = "CME-1-RC1"


@dataclass(frozen=True, slots=True)
class MaterialAssignment:
    component_id: str
    material: MaterialDescriptor

    def __post_init__(self) -> None:
        text_required(self.component_id)
        if not isinstance(self.material, MaterialDescriptor):
            raise TypeError("A typed connector material descriptor is required")


@dataclass(frozen=True, slots=True)
class MaterialTarget:
    physical_id: str
    role: ComponentRole
    body_form: str
    material: MaterialDescriptor
    provider_status: str
    source_status: str
    source_revision: str | None
    material_axes: str
    capacity: None = None
    utilization: None = None


@dataclass(frozen=True, slots=True)
class ConnectorMaterialPlan:
    product: str
    mode: str
    targets: tuple[MaterialTarget, ...]
    excluded_physical_ids: tuple[str, ...]
    invalidated_response_ids: tuple[str, ...]
    required_future_coverage: tuple[str, ...]
    fingerprint: str
    disposition: str
    contract: str = CONTRACT
    resistance_evaluated: bool = False
    design_status: None = None
    derived_branch_forces: None = None
    known_external_actions_preserved: bool = True
    persisted: bool = False


def _index(components: tuple[CanonicalComponent, ...]) -> dict[str, CanonicalComponent]:
    found: dict[str, CanonicalComponent] = {}
    for component in components:
        for name in (component.physical_id, *component.aliases):
            if name in found:
                raise ValueError("Ambiguous canonical physical identity or alias")
            found[name] = component
    return found


def plan_connector_materials(
    product: str,
    mode: str,
    components: tuple[CanonicalComponent, ...],
    assignments: tuple[MaterialAssignment, ...],
    *,
    geometry_identity: str,
    apply_all: MaterialDescriptor | None = None,
    trusted_sources: tuple[SourceDescriptor, ...] = (),
    responses: tuple[tuple[str, ResponseSignature], ...] = (),
) -> ConnectorMaterialPlan:
    """Validate the complete transaction before producing a target plan.

    The application supplies components and sources from native canonical builders;
    an HTTP caller cannot supply either. Retaining a wrench is not retaining a
    material-dependent response source or certifying member/anchor capacity.
    """
    text_required(product, mode, geometry_identity)
    indexed = _index(components)
    proposed: dict[str, MaterialDescriptor] = {}
    for item in assignments:
        if item.component_id not in indexed:
            raise ValueError(f"Unknown physical component: {item.component_id}")
        component = indexed[item.component_id]
        if component.role is ComponentRole.MEMBER_REINFORCEMENT:
            raise ValueError("FRP_REINFORCEMENT_RESTRICTED: QUALIFIED_ALTERNATIVE_REQUIRED")
        if component.role is not ComponentRole.CONNECTOR_BODY:
            raise ValueError(f"ROLE_SUBSTITUTION_FORBIDDEN:{component.role.value}")
        previous = proposed.get(component.physical_id)
        if previous is not None and previous != item.material:
            raise ValueError("CONFLICTING_SHARED_PHYSICAL_ASSIGNMENTS")
        proposed[component.physical_id] = item.material
    sources = {s.source_id: s for s in trusted_sources}
    if len(sources) != len(trusted_sources):
        raise ValueError("Ambiguous trusted source reference")
    targets: list[MaterialTarget] = []
    changed: set[str] = set()
    for component in sorted(components, key=lambda item: item.physical_id):
        if component.role is not ComponentRole.CONNECTOR_BODY:
            continue
        material = proposed.get(component.physical_id, apply_all or component.material)
        source = sources.get(material.source_reference or "")
        if material != component.material:
            changed.add(component.physical_id)
        stainless = material.family is ConnectorMaterial.SS316
        targets.append(
            MaterialTarget(
                component.physical_id,
                component.role,
                component.body_form,
                material,
                "PROVIDER_NOT_IMPLEMENTED" if stainless else "NATIVE_FRP_DELEGATION_AVAILABLE",
                "SOURCE_UNVERIFIED"
                if source is None
                else "SOURCE_METADATA_ONLY_NO_NUMERICAL_ACTIVATION",
                None if source is None else source.revision,
                "GEOMETRIC_LOCAL_AXES_NOT_PULTRUSION" if stainless else "NATIVE_COMPONENT_LW_CW_TT",
            )
        )
    invalidated = tuple(
        sorted(
            name for name, response in responses if changed.intersection(dict(response.materials))
        )
    )
    # Even without a registered response, a changed material requires future
    # validation. Absence of a source is never an implicit rigid/equal-sharing model.
    required = (
        (
            "MATERIAL_FABRICATION_PROPERTY_AND_METHOD_AUTHORITY",
            "ASSEMBLY_COMPATIBILITY_SHARING_CONTACT_PRYING_REVALIDATION",
            "FRP_MEMBER_AND_INDEPENDENT_FASTENER_CHECKS_REMAIN",
            "FAMILY_ADAPTER_AND_REQUIRED_CHECK_COMPLETENESS",
        )
        if changed
        else ()
    )
    response_identity = tuple(
        sorted(
            (name, replace(response, materials=tuple(sorted(response.materials))))
            for name, response in responses
        )
    )
    excluded = tuple(
        sorted(c.physical_id for c in components if c.role is not ComponentRole.CONNECTOR_BODY)
    )
    identity = (
        CONTRACT,
        product,
        mode,
        geometry_identity,
        tuple(targets),
        tuple(
            replace(c, aliases=tuple(sorted(c.aliases)))
            for c in sorted(components, key=lambda c: c.physical_id)
        ),
        response_identity,
        tuple(
            sources[name]
            for name in sorted(
                {
                    t.material.source_reference
                    for t in targets
                    if t.material.source_reference in sources
                }
            )
        ),
    )
    return ConnectorMaterialPlan(
        product,
        mode,
        tuple(targets),
        excluded,
        invalidated,
        required,
        angle_fingerprint(identity),
        "NO_CONNECTOR_BODY" if not targets else "PLANNING_ONLY",
    )
