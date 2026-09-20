"""Separate trusted registries; arbitrary client labels never supply qualification."""

from dataclasses import dataclass, field

from frp_master_connection.application.wi_frp_support_moment_sources import (
    QualifiedZoneCheck,
    SupportFastenerSource,
)
from frp_master_connection.application.wi_wall_moment_sources import WallMomentSourceRegistry
from frp_master_connection.calculation.angle_column_base_response import QualifiedBaseResponse
from frp_master_connection.calculation.support_attachment_response import QualifiedSupportResponse
from frp_master_connection.domain.material_architecture import EngineeringPropertySource

ZONE_COVERAGE = (
    "TWO_COLUMN_LEG_COMMON_END_ZONE",
    "COMMON_NET_BLOCK_CLEAVAGE_PATHS",
    "LOCAL_BENDING_THROUGH_THICKNESS",
    "SIGNED_COMPLETE_BRANCH_AND_COLUMN_CONTACT_INTERACTION",
)


@dataclass(frozen=True, slots=True)
class QualifiedColumnBaseZone:
    reference: str
    source: EngineeringPropertySource
    exact_binding: str
    checks: tuple[QualifiedZoneCheck, ...]
    coverage: tuple[str, ...]
    applicability: str


@dataclass(frozen=True, slots=True)
class AngleBaseSourceRegistry:
    responses: tuple[QualifiedBaseResponse, ...] = ()
    connector_sources: WallMomentSourceRegistry = field(default_factory=WallMomentSourceRegistry)
    member_responses: tuple[QualifiedSupportResponse, ...] = ()
    fasteners: tuple[SupportFastenerSource, ...] = ()
    zones: tuple[QualifiedColumnBaseZone, ...] = ()

    def __post_init__(self) -> None:
        for records in (self.responses, self.member_responses, self.fasteners, self.zones):
            keys = [r.reference for r in records]
            if len(set(keys)) != len(keys) or any(not k.strip() for k in keys):
                raise ValueError("Trusted Stage 4.4 source references must be unique and nonempty")


EMPTY_SOURCES = AngleBaseSourceRegistry()
