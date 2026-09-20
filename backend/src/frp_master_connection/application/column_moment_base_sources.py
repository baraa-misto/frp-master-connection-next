"""Trusted, source-bound Stage 4.5 registries. Empty in production."""

from dataclasses import dataclass, field

from frp_master_connection.application.wi_frp_support_moment_sources import (
    QualifiedZoneCheck,
    SupportFastenerSource,
)
from frp_master_connection.application.wi_wall_moment_sources import WallMomentSourceRegistry
from frp_master_connection.calculation.column_moment_base_response import (
    QualifiedColumnBaseResponse,
)
from frp_master_connection.domain.material_architecture import EngineeringPropertySource

ZONE_COVERAGE = (
    "ACTUAL_COLUMN_PROFILE_COMBINED_END_ZONE",
    "COMMON_NET_BLOCK_CLEAVAGE_PATHS",
    "LOCAL_BENDING_THROUGH_THICKNESS",
    "SIGNED_BRANCH_CONTACT_AND_SHARED_BOLT_INTERACTION",
)
PROFILE_ZONE_COVERAGE = {
    "WI": ("WEB_FLANGE_JUNCTION_TRANSFER",),
    "RHS": ("NEAR_FAR_WALL_PARTICIPATION", "BOX_WALL_BENDING_CRUSHING_INTERACTION"),
    "SRS": ("THREE_DIMENSIONAL_BEARING_LOAD_SPREAD", "SOLID_LOCAL_SPLITTING_THROUGH_THICKNESS"),
}


@dataclass(frozen=True, slots=True)
class QualifiedColumnMomentZone:
    reference: str
    source: EngineeringPropertySource
    exact_binding: str
    checks: tuple[QualifiedZoneCheck, ...]
    coverage: tuple[str, ...]
    applicability: str


@dataclass(frozen=True, slots=True)
class ColumnMomentSourceRegistry:
    responses: tuple[QualifiedColumnBaseResponse, ...] = ()
    connector_sources: WallMomentSourceRegistry = field(default_factory=WallMomentSourceRegistry)
    fasteners: tuple[SupportFastenerSource, ...] = ()
    zones: tuple[QualifiedColumnMomentZone, ...] = ()

    def __post_init__(self) -> None:
        for records in (self.responses, self.fasteners, self.zones):
            refs = [r.reference for r in records]
            if len(set(refs)) != len(refs) or any(not r.strip() for r in refs):
                raise ValueError("Trusted Stage 4.5 source references must be unique and nonempty")


EMPTY_SOURCES = ColumnMomentSourceRegistry()
