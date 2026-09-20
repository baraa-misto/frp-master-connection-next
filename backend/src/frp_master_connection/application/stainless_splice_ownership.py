"""CME-3 ownership of frozen splice summaries, using reviewed native identities.

Native summary IDs are not arbitrary client labels. Each accepted namespace is
enumerated from its frozen builder and then resolved against the physical scene.
Unknown IDs fail closed. An absent failure ID is *not* promoted to numerical PASS;
the frozen summary does not serialize each non-failing check's comparison.
"""

from __future__ import annotations

from dataclasses import dataclass

from frp_master_connection.application.channel_moment_splice_orchestration import (
    ChannelMomentSpliceDesignResult,
)
from frp_master_connection.application.connector_material_assembly import MaterialAssembly
from frp_master_connection.application.stainless_native_results import (
    physical_hardware_owner,
    physical_owner,
)
from frp_master_connection.application.web_splice_orchestration import (
    WebSpliceDesignResult,
    WebSplicePreviewResult,
    WebSpliceRC2DesignResult,
)
from frp_master_connection.application.wi_moment_splice_orchestration import (
    WIMomentSpliceDesignResult,
)
from frp_master_connection.calculation.angle_connector_core import angle_fingerprint
from frp_master_connection.calculation.web_splice_resistance import WebSpliceDoubleShearResult
from frp_master_connection.calculation.wi_moment_splice_resistance import (
    AsymmetricTwoPlaneBoltResult,
)
from frp_master_connection.domain.connector_materials import CanonicalComponent, ComponentRole


@dataclass(frozen=True, slots=True)
class OwnedSpliceCheck:
    check_id: str
    owner: CanonicalComponent
    failed: bool
    native_fingerprints: tuple[str, ...]
    native_comparison: str | None = None
    native_record: object = None

    @property
    def comparison(self) -> str:
        return self.native_comparison or (
            "FAIL" if self.failed else "NATIVE_COMPARISON_NOT_SERIALIZED"
        )


@dataclass(frozen=True, slots=True)
class SplicePartition:
    retained_non_body: tuple[OwnedSpliceCheck, ...]
    superseded_frp_body: tuple[OwnedSpliceCheck, ...]
    native_warnings: tuple[str, ...]
    fingerprint: str


def _web_checks(
    assembly: MaterialAssembly,
    preview: WebSplicePreviewResult,
    ids: tuple[str, ...],
    failed: tuple[str, ...],
    fingerprints: tuple[str, ...],
) -> tuple[OwnedSpliceCheck, ...]:
    owners = {
        f"{group.group_id}:{layer.layer_id}:": physical_owner(assembly, layer.layer_id)
        for group in (preview.beam_a_group, preview.beam_b_group)
        for layer in group.layer_demands
    }
    if not set(failed).issubset(ids):
        raise ValueError("STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED:ORPHAN_FAILURE")
    checks: list[OwnedSpliceCheck] = []
    for check_id in ids:
        matches = tuple(owner for prefix, owner in owners.items() if check_id.startswith(prefix))
        if len(matches) != 1:
            raise ValueError("STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED:" + check_id)
        checks.append(OwnedSpliceCheck(check_id, matches[0], check_id in failed, fingerprints))
    return tuple(checks)


def _wi_owner_map() -> dict[str, str]:
    # Exactly the frozen flange-face/plate namespaces; no broad 'BEAM_*' rule.
    owners: dict[str, str] = {}
    method = "RATIONAL_BALANCED_FLANGE_FACE_SUBLAYER_TRANSFER_RC1"
    for beam in ("BEAM_A", "BEAM_B"):
        for flange in ("TOP", "BOTTOM"):
            owners[f"{beam}_{flange}_OUTER:OUTER_PLATE"] = f"{flange}_OUTER_FLANGE_SPLICE_PLATE"
            owners[f"{beam}_{flange}_OUTER:BEAM_FLANGE_OUTER_FACE:{method}"] = beam
            owners[f"{beam}_{flange}:BEAM_FLANGE_INNER_FACE:{method}"] = beam
            for side in ("POSITIVE", "NEGATIVE"):
                owners[f"{beam}_{flange}_INNER_{side}:INNER_PLATE"] = (
                    f"{flange}_{side}_INNER_FLANGE_SPLICE_PLATE"
                )
    return owners


def _channel_owner_map() -> dict[str, str]:
    owners: dict[str, str] = {}
    for beam in ("BEAM_A", "BEAM_B"):
        for side in ("BACK", "OPENING"):
            owners[f"{side}_WEB_SPLICE_PLATE"] = f"{side}_WEB_SPLICE_PLATE"
            owners[
                f"{beam}_{side}_CHANNEL_WEB_FACE:RATIONAL_CHANNEL_WEB_FACE_SUBLAYER_TRANSFER_RC1"
            ] = beam
        for flange in ("TOP", "BOTTOM"):
            for side in ("OUTER", "INNER"):
                owners[f"{flange}_{side}_FLANGE_SPLICE_PLATE"] = (
                    f"{flange}_{side}_FLANGE_SPLICE_PLATE"
                )
                owners[f"{beam}_{flange}_{side}_CHANNEL_FLANGE_FACE"] = beam
    return owners


def splice_check_partition(assembly: MaterialAssembly, design: object) -> SplicePartition:
    checks: list[OwnedSpliceCheck] = []
    warnings: list[str] = []
    if isinstance(design, WebSpliceDesignResult):
        checks.extend(
            _web_checks(
                assembly,
                design.preview,
                design.local_check_ids,
                design.failed_local_check_ids,
                design.local_resistance_fingerprints,
            )
        )
        warnings.extend(design.local_resistance_warnings)
    elif isinstance(design, (WIMomentSpliceDesignResult, ChannelMomentSpliceDesignResult)):
        owners = (
            _wi_owner_map()
            if isinstance(design, WIMomentSpliceDesignResult)
            else _channel_owner_map()
        )
        for summary in design.local_checks:
            warnings.extend(summary.warnings)
            if (
                isinstance(design, WIMomentSpliceDesignResult)
                and summary.component_id == "WEB_SUBSYSTEM"
            ):
                checks.extend(
                    _web_checks(
                        assembly,
                        design.preview.web_preview,
                        summary.required_check_ids,
                        summary.failed_check_ids,
                        summary.result_fingerprints,
                    )
                )
                continue
            target = owners.get(summary.component_id)
            if target is None:
                raise ValueError(
                    "STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED:" + summary.component_id
                )
            owner = physical_owner(assembly, target)
            if not set(summary.failed_check_ids).issubset(summary.required_check_ids):
                raise ValueError("STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED:ORPHAN_FAILURE")
            checks.extend(
                OwnedSpliceCheck(
                    check_id,
                    owner,
                    check_id in summary.failed_check_ids,
                    summary.result_fingerprints,
                )
                for check_id in summary.required_check_ids
            )
    else:
        raise ValueError("STAINLESS_NATIVE_SPLICE_FAMILY_NOT_REVIEWED")
    hardware = (
        design.double_shear_results
        if isinstance(design, WebSpliceRC2DesignResult)
        else (*design.flange_bolts, *design.web_bolts)
        if isinstance(design, ChannelMomentSpliceDesignResult)
        else (*design.flange_bolts, *design.web_double_shear)
        if isinstance(design, WIMomentSpliceDesignResult)
        else ()
    )
    for bolt in hardware:
        if not isinstance(bolt, (WebSpliceDoubleShearResult, AsymmetricTwoPlaneBoltResult)):
            raise ValueError("STAINLESS_NATIVE_CHECK_OWNERSHIP_NOT_RESOLVED:BOLT_RECORD")
        owner = physical_hardware_owner(assembly, bolt.bolt_id)
        checks.append(
            OwnedSpliceCheck(
                "NATIVE_BOLT:" + owner.physical_id,
                owner,
                bolt.status == "FAIL",
                (bolt.result_fingerprint,),
                bolt.status.value,
                bolt,
            )
        )
    if len({c.check_id for c in checks}) != len(checks):
        raise ValueError("STAINLESS_ACTIVATION_DUPLICATE_REQUIRED_CHECK")
    retained = tuple(c for c in checks if c.owner.role is not ComponentRole.CONNECTOR_BODY)
    superseded = tuple(c for c in checks if c.owner.role is ComponentRole.CONNECTOR_BODY)
    return SplicePartition(
        retained,
        superseded,
        tuple(warnings),
        angle_fingerprint((retained, superseded, tuple(warnings))),
    )
