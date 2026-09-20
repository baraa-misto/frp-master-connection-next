"""CME-3 native check ownership; no resistance or demand arithmetic.

The owner is obtained from canonical physical assembly/layer data. The native
result object is retained verbatim. Connector-body results are partitioned out,
not relabelled as steel and not included in the stainless summary.
"""

from __future__ import annotations

from dataclasses import dataclass

from frp_master_connection.application.beam_concrete_paired_angle_orchestration import (
    BeamConcretePairedAngleDesignResult,
)
from frp_master_connection.application.clip_angle_orchestration import ClipAngleDesignResult
from frp_master_connection.application.column_base_profile_orchestration import (
    ColumnBaseProfileDesignResult,
)
from frp_master_connection.application.column_base_web_angle_orchestration import (
    ColumnBaseDesignResult,
)
from frp_master_connection.application.connector_material_assembly import MaterialAssembly
from frp_master_connection.application.multi_member_tee_orchestration import (
    MultiMemberTeeDesignResult,
)
from frp_master_connection.application.multirow_orchestration import MultiRowOrchestrationResponse
from frp_master_connection.application.paired_clip_angle_orchestration import (
    PairedClipAngleDesignResult,
)
from frp_master_connection.application.tee_orchestration import TeeConnectorDesignResult
from frp_master_connection.calculation.angle_connector_core import angle_fingerprint
from frp_master_connection.calculation.multirow_engine import MultiRowCheckResult
from frp_master_connection.domain.column_base_web_angles import ColumnBaseSide
from frp_master_connection.domain.connector_materials import CanonicalComponent, ComponentRole


@dataclass(frozen=True, slots=True)
class OwnedNativeCheck:
    scope: str
    owner: CanonicalComponent
    result: MultiRowCheckResult

    @property
    def identity(self) -> tuple[str, str, str]:
        return self.scope, self.owner.physical_id, self.result.result_id

    @property
    def governs_stainless_body(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class NativeCheckPartition:
    retained_non_body: tuple[OwnedNativeCheck, ...]
    superseded_frp_body: tuple[OwnedNativeCheck, ...]
    fingerprint: str


def physical_owner(assembly: MaterialAssembly, identity: str) -> CanonicalComponent:
    matches = tuple(c for c in assembly.components if identity in (c.physical_id, *c.aliases))
    if len(matches) != 1 or matches[0].role is ComponentRole.UNCLASSIFIED:
        raise ValueError("STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED:" + identity)
    return matches[0]


def physical_hardware_owner(assembly: MaterialAssembly, bolt_id: str) -> CanonicalComponent:
    """Match a native physical bolt ID to exactly one canonical hardware item."""
    matches = tuple(
        c
        for c in assembly.components
        if c.role is ComponentRole.FASTENER_OR_HARDWARE and c.physical_id.endswith(":" + bolt_id)
    )
    if len(matches) != 1:
        raise ValueError("STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED:NO_HARDWARE")
    return matches[0]


def partition_native_checks(checks: tuple[OwnedNativeCheck, ...]) -> NativeCheckPartition:
    """Reject duplicates/unknown roles rather than quietly count or discard them."""
    if len({c.identity for c in checks}) != len(checks):
        raise ValueError("STAINLESS_ACTIVATION_DUPLICATE_REQUIRED_CHECK")
    if any(c.owner.role is ComponentRole.UNCLASSIFIED for c in checks):
        raise ValueError("STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED")
    retained = tuple(c for c in checks if c.owner.role is not ComponentRole.CONNECTOR_BODY)
    superseded = tuple(c for c in checks if c.owner.role is ComponentRole.CONNECTOR_BODY)
    return NativeCheckPartition(retained, superseded, angle_fingerprint((retained, superseded)))


def authoritative_multirow_results(
    response: MultiRowOrchestrationResponse,
) -> tuple[tuple[str, MultiRowCheckResult], ...]:
    """Select the native final handoff/group-mode path once, not its legacy copies.

    Distinct design scenarios retain distinct identities. The caller binds the
    physical interface/branch separately; equal results on distinct bodies are
    not deduplicated merely because their numerical values coincide.
    """
    integration = response.automatic_group_mode_integration
    if integration is not None:
        return tuple(
            (scenario.scenario_id, result)
            for scenario in integration.scenario_results
            for result in scenario.supported_results
        )
    if response.automatic_handoff_results:
        return tuple(
            (str(index), result)
            for index, handoff in enumerate(response.automatic_handoff_results)
            for result in handoff.supported_results
        )
    if response.calculation_result is None:
        return ()
    return tuple(("NATIVE_LEGACY", result) for result in response.calculation_result.results)


def own_multirow_results(
    assembly: MaterialAssembly,
    scope: str,
    response: MultiRowOrchestrationResponse,
    *,
    bolt_group_id: str,
    component_aliases: tuple[tuple[str, str], ...] = (),
) -> tuple[OwnedNativeCheck, ...]:
    """Alias overrides come only from a native shared-template branch/slot.

    Both alias endpoints must be supplied by a reviewed family adapter, never a
    client role label. The target is verified against the active physical scene.
    """
    aliases = dict(component_aliases)
    if len(aliases) != len(component_aliases):
        raise ValueError("STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED:DUPLICATE_ALIAS")
    scene = response.preview.visualization
    if scene is None:
        if authoritative_multirow_results(response):
            raise ValueError("STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED:NO_LAYER_SCENE")
        return ()
    layers = {layer.layer_id: layer.component_id for layer in scene.layers}
    if len(layers) != len(scene.layers):
        raise ValueError("STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED:DUPLICATE_LAYER")
    owned: list[OwnedNativeCheck] = []
    for scenario, result in authoritative_multirow_results(response):
        if result.layer_id is None:
            # Native BOLT_SHEAR has no material layer. It cannot become a body
            # check simply because the bolt passes through a steel connector.
            if result.limit_state.value != "BOLT_SHEAR" or result.bolt_id is None:
                raise ValueError("STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED:NO_LAYER")
            hardware = tuple(
                c
                for c in assembly.components
                if c.role is ComponentRole.FASTENER_OR_HARDWARE
                and c.physical_id == "HARDWARE:" + bolt_group_id + ":" + result.bolt_id
            )
            if not hardware:
                # Older canonical geometry omits a group field but retains
                # interface-qualified bolt IDs. Accept only a unique physical
                # identity; never synthesize a body/shaft or select a first hit.
                hardware = tuple(
                    c
                    for c in assembly.components
                    if c.role is ComponentRole.FASTENER_OR_HARDWARE
                    and c.physical_id.endswith(":" + result.bolt_id)
                )
            if len(hardware) != 1:
                raise ValueError("STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED:NO_HARDWARE")
            owner = hardware[0]
        else:
            component = layers.get(result.layer_id)
            if component is None:
                raise ValueError("STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED:" + result.layer_id)
            owner = physical_owner(assembly, aliases.get(component, component))
        owned.append(OwnedNativeCheck(scope + ":" + scenario, owner, result))
    return tuple(owned)


def native_row_partition(assembly: MaterialAssembly, design: object) -> NativeCheckPartition:
    """Reviewed family paths exclude preview copies and preserve physical branches."""
    checks: list[OwnedNativeCheck] = []

    def add(
        group: str,
        response: MultiRowOrchestrationResponse | None,
        aliases: tuple[tuple[str, str], ...] = (),
    ) -> None:
        if response is not None:
            checks.extend(
                own_multirow_results(
                    assembly,
                    group,
                    response,
                    bolt_group_id=group,
                    component_aliases=aliases,
                )
            )

    if isinstance(design, ClipAngleDesignResult):
        for interface in (design.interface_a, design.interface_b):
            add(interface.bolt_group_id, interface.resistance)
    elif isinstance(design, TeeConnectorDesignResult):
        for tee_interface in (design.interface_a, design.interface_b):
            add(tee_interface.bolt_group_id, tee_interface.design)
    elif isinstance(design, PairedClipAngleDesignResult):
        p = design.preview
        add(p.common_member_group.group_id, p.common_member_group.resistance)
        add(
            p.positive_support_group.group_id,
            p.positive_support_group.resistance,
            (("single-clip-angle-connector", "POSITIVE_CLIP_ANGLE"),),
        )
        add(
            p.negative_support_group.group_id,
            p.negative_support_group.resistance,
            (("single-clip-angle-connector", "NEGATIVE_CLIP_ANGLE"),),
        )
    elif isinstance(design, BeamConcretePairedAngleDesignResult):
        beam_group = design.preview.common_beam_group
        add(beam_group.group_id, beam_group.resistance)
    elif isinstance(design, MultiMemberTeeDesignResult):
        for slot in design.slots:
            add(
                slot.bolt_group_id,
                slot.design,
                (("tee-brace", slot.connected_member_id),),
            )
        add(design.support.bolt_group_id, design.support.design)
    elif isinstance(design, (ColumnBaseDesignResult, ColumnBaseProfileDesignResult)):
        response = design.web_group_resistance
        if response is not None:
            if not isinstance(response, MultiRowOrchestrationResponse):
                raise ValueError("STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED:WEB_GROUP")
            aliases = (
                (("single-clip-angle-connector", "positive-base-angle"),)
                if design.preview.single_side is ColumnBaseSide.POSITIVE_T_C
                else (("single-clip-angle-connector", "negative-base-angle"),)
            )
            add("NATIVE", response, aliases)
    else:
        raise ValueError("STAINLESS_NATIVE_ROW_FAMILY_NOT_REVIEWED")
    return partition_native_checks(tuple(checks))
