"""Versioned fastener selection for the shared bolted-workspace workflow."""

from __future__ import annotations

from dataclasses import replace
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import Field, StrictStr, model_validator

from frp_master_connection.api.calculation_mapping import _fastener_snapshot
from frp_master_connection.api.dependencies import build_trusted_identity_dependency
from frp_master_connection.api.schemas import FastenerSnapshotDTO, _StrictModel
from frp_master_connection.calculation import (
    FastenerSnapshot,
    QualificationStatus,
    SourceClassification,
    create_locked_f593_fastener_snapshot,
)
from frp_master_connection.security import TrustedIdentityResolver

FASTENER_CONTRACT = "FASTENER-OR1-RC1"
F593_REVISION: Literal["ASTM-F593-17-G2-316-316L-SOURCE-PENDING-RC0"] = (
    "ASTM-F593-17-G2-316-316L-SOURCE-PENDING-RC0"
)


class DefaultFastenerSelectionDTO(_StrictModel):
    kind: Literal["DEFAULT"]
    contract: Literal["FASTENER-OR1-RC1"]
    revision: Literal["ASTM-F593-17-G2-316-316L-SOURCE-PENDING-RC0"]


class SessionFastenerSelectionDTO(_StrictModel):
    kind: Literal["SESSION"]
    contract: Literal["FASTENER-OR1-RC1"]
    revision: Annotated[StrictStr, Field(min_length=1, max_length=128)]
    source_label: Annotated[StrictStr, Field(min_length=1, max_length=256)]
    fnt_source_basis: StrictStr
    snapshot: FastenerSnapshotDTO

    @model_validator(mode="after")
    def validate_source(self) -> SessionFastenerSelectionDTO:
        if self.snapshot.locked:
            raise ValueError("A session fastener cannot claim locked F593 identity.")
        if self.snapshot.id == create_locked_f593_fastener_snapshot().id:
            raise ValueError("A session fastener cannot reuse the controlled F593 ID.")
        if self.snapshot.fnt is not None and not self.fnt_source_basis.strip():
            raise ValueError("Custom Fnt requires an explicit source basis.")
        if self.snapshot.fnt is None:
            if (
                self.snapshot.fnt_source_classification is not SourceClassification.SOURCE_PENDING
                or self.snapshot.fnt_qualification_status is not QualificationStatus.SOURCE_PENDING
            ):
                raise ValueError("Custom fastener without Fnt must remain source pending.")
        elif (
            self.snapshot.fnt_source_classification is not SourceClassification.USER_DEFINED
            or self.snapshot.fnt_qualification_status is not QualificationStatus.DEVELOPMENT_ONLY
        ):
            raise ValueError("Custom Fnt is numerical user data, not qualified F593 source.")
        return self


FastenerSelectionDTO = Annotated[
    DefaultFastenerSelectionDTO | SessionFastenerSelectionDTO,
    Field(discriminator="kind"),
]


def resolve_fastener_selection(selection: FastenerSelectionDTO) -> FastenerSnapshot | None:
    """None means the native controlled F593 source-pending preset remains in force."""

    if isinstance(selection, DefaultFastenerSelectionDTO):
        return None
    snapshot = _fastener_snapshot(selection.snapshot)
    return replace(
        snapshot,
        source_notes=(
            *snapshot.source_notes,
            f"Session source: {selection.source_label}",
            f"Fnt basis: {selection.fnt_source_basis or 'SOURCE_PENDING'}",
            f"Session revision: {selection.revision}",
        ),
    )


def fastener_source_record(selection: FastenerSelectionDTO) -> dict[str, object]:
    if isinstance(selection, DefaultFastenerSelectionDTO):
        preset = create_locked_f593_fastener_snapshot()
        return {
            "kind": "DEFAULT",
            "contract": FASTENER_CONTRACT,
            "revision": F593_REVISION,
            "id": preset.id,
            "display_name": preset.display_name,
            "specification": preset.bolt_specification,
            "alloy_group": preset.alloy_group,
            "alloys": list(preset.alloys),
            "condition": preset.condition,
            "nut": preset.nut_specification,
            "washer_basis": preset.washer_material_basis,
            "installation": preset.installation_condition,
            "fnt": None,
            "fnt_state": "SOURCE_PENDING",
            "qualification": "SOURCE_PENDING",
            "source_requirement": (
                "Catalog source-data gap: controlled ASTM F593-17 mechanical-property table "
                "for Group 2 316/316L, cold-worked condition and selected diameter is missing. "
                "Per-connection supplier certification is not required by this workflow."
            ),
            "specification_note": "Specified hardware shall conform to ASTM F593 Group 2 316/316L.",
        }
    return {
        "kind": "SESSION",
        "contract": FASTENER_CONTRACT,
        "revision": selection.revision,
        "source_label": selection.source_label,
        "fnt_source_basis": selection.fnt_source_basis,
        "snapshot": selection.snapshot.model_dump(mode="json"),
    }


def build_fastener_router(identity_resolver: TrustedIdentityResolver) -> APIRouter:
    router = APIRouter(prefix="/api/v1/fasteners")
    identity = build_trusted_identity_dependency(identity_resolver)

    @router.get("/catalog", dependencies=[Depends(identity)])
    async def catalog() -> dict[str, object]:
        return {
            "contract": FASTENER_CONTRACT,
            "records": [
                fastener_source_record(
                    DefaultFastenerSelectionDTO(
                        kind="DEFAULT", contract="FASTENER-OR1-RC1", revision=F593_REVISION
                    )
                )
            ],
        }

    return router
