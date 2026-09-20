"""C2-M internal flat-product authority; not a family material-selection API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit

SOURCE_SHA256 = "A9C3440C127866626F633E9B5426E830E035857135FA1A38A2424757625AFCF1"
METHOD = "C2_P1_AISC_370_25_FLAT_PLATE_LRFD_RC1_R1"
BRIDGE = "ASCE_74_23_FRP_AISC_370_25_STAINLESS_OWNER_2026_09_12"
FY = PhysicalQuantity.of("25", Unit.KSI)
FU = PhysicalQuantity.of("70", Unit.KSI)


class StainlessGrade(StrEnum):
    GENERIC = "GENERIC_316SS_CONSERVATIVE_BASIS"
    S31600 = "S31600_316"
    S31603 = "S31603_316L"
    DUAL = "S31600_S31603_DUAL_CERTIFIED"


@dataclass(frozen=True, slots=True)
class StainlessMaterial:
    """Server-owned snapshot. Certification affects provenance, never credited strength."""

    grade: StainlessGrade
    commercial_label: str = "316 Stainless Steel"
    snapshot: str = "GENERIC_316SS_CONSERVATIVE_BASIS_US_SOURCE"
    source_system: str = "US_CUSTOMARY"
    product_specification: str = "ASTM A240/A240M-24"
    general_requirements: str = "ASTM A480/A480M-24"
    source: str = "ANSI/AISC 370-25, December 8, 2025"
    source_sha256: str = SOURCE_SHA256
    bridge: str = BRIDGE
    method: str = METHOD
    fy: PhysicalQuantity = FY
    fu: PhysicalQuantity = FU
    mtr_strength_credit: bool = False
    cold_work_credit: bool = False

    @property
    def future_welding_eligibility(self) -> str:
        if self.grade in (StainlessGrade.S31603, StainlessGrade.DUAL):
            return "FUTURE_SEPARATE_WELDING_AUTHORITY_REQUIRED"
        return "WELDING_NOT_ESTABLISHED_OR_PROHIBITED"


_MATERIALS = tuple(StainlessMaterial(grade) for grade in StainlessGrade)


def stainless_material(
    alias: str, certified_grade: StainlessGrade | None = None
) -> StainlessMaterial:
    """Resolve a label through a closed catalogue, not client-provided strengths."""
    if alias.strip().upper() not in {
        "316 STAINLESS STEEL",
        "316SS",
        "316 SS",
        "316",
        "316L",
        "316L SS",
        "316/316L",
    }:
        raise ValueError("STAINLESS_GRADE_IDENTITY_INCOMPLETE")
    grade = StainlessGrade.GENERIC if certified_grade is None else certified_grade
    for material in _MATERIALS:
        if material.grade is grade:
            return material
    raise ValueError("STAINLESS_GRADE_IDENTITY_INCOMPLETE")


def is_trusted_material(material: StainlessMaterial) -> bool:
    """Exact catalogue content, including properties/source/domain; labels alone cannot approve."""
    return material in _MATERIALS
