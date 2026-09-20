"""Immutable engineering-source identity for Stage 2.1A contracts."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class SourceClassification(StrEnum):
    """Controlled provenance classification for engineering values."""

    CODE_CHARACTERISTIC = "CODE_CHARACTERISTIC"
    QUALIFIED_TEST_DATA = "QUALIFIED_TEST_DATA"
    MANUFACTURER_CHARACTERISTIC = "MANUFACTURER_CHARACTERISTIC"
    MANUFACTURER_NOMINAL = "MANUFACTURER_NOMINAL"
    ENGINEER_APPROVED_DEVELOPMENT = "ENGINEER_APPROVED_DEVELOPMENT"
    USER_DEFINED = "USER_DEFINED"
    SOURCE_PENDING = "SOURCE_PENDING"


class QualificationStatus(StrEnum):
    """Controlled qualification state, independent from source classification."""

    QUALIFIED = "QUALIFIED"
    DEVELOPMENT_ONLY = "DEVELOPMENT_ONLY"
    SOURCE_PENDING = "SOURCE_PENDING"
    ENGINEERING_REVIEW_REQUIRED = "ENGINEERING_REVIEW_REQUIRED"
    SECTION_2_3_2_QUALIFICATION_REQUIRED = "SECTION_2_3_2_QUALIFICATION_REQUIRED"


@dataclass(frozen=True, slots=True)
class CalculationSourceSnapshot:
    """Citation/provenance metadata without licensed source text."""

    standard_name: str
    edition: str
    chapter: str
    section: str
    equation_reference: str | None
    errata_identifier: str
    errata_effective_date: date
    chapter_affected_by_errata: bool
    interpretation_id: str | None
    source_classification: SourceClassification
    source_revision: str
    engineer_approval_authority: str | None = None
    engineer_approval_date: date | None = None

    def __post_init__(self) -> None:
        required = {
            "standard_name": self.standard_name,
            "edition": self.edition,
            "chapter": self.chapter,
            "section": self.section,
            "errata_identifier": self.errata_identifier,
            "source_revision": self.source_revision,
        }
        if any(not value.strip() for value in required.values()):
            raise ValueError("Source identity text must be nonempty.")
        if not isinstance(self.errata_effective_date, date):
            raise TypeError("errata_effective_date must be a date.")
        if not isinstance(self.source_classification, SourceClassification):
            raise TypeError("source_classification must be a SourceClassification.")
        approval_values = (self.engineer_approval_authority, self.engineer_approval_date)
        if (approval_values[0] is None) is not (approval_values[1] is None):
            raise ValueError("Engineer approval authority and date must appear together.")


ASCE_74_23_STANDARD_NAME = "ASCE/SEI 74-23"
ASCE_74_23_EDITION = "2023"
ASCE_74_23_ERRATUM = "Erratum 1"
ASCE_74_23_ERRATUM_EFFECTIVE_DATE = date(2026, 1, 13)
TRANSVERSE_ENDPOINT_INTERPRETATION_ID = "TRANSVERSE_ENDPOINT_INCLUDED"


def asce_74_23_chapter_8_source(
    *,
    section: str,
    equation_reference: str | None = None,
    interpretation_id: str | None = None,
) -> CalculationSourceSnapshot:
    """Create a canonical Chapter 8 source locator with reviewed errata state."""

    return CalculationSourceSnapshot(
        standard_name=ASCE_74_23_STANDARD_NAME,
        edition=ASCE_74_23_EDITION,
        chapter="8",
        section=section,
        equation_reference=equation_reference,
        errata_identifier=ASCE_74_23_ERRATUM,
        errata_effective_date=ASCE_74_23_ERRATUM_EFFECTIVE_DATE,
        chapter_affected_by_errata=False,
        interpretation_id=interpretation_id,
        source_classification=SourceClassification.CODE_CHARACTERISTIC,
        source_revision="RC2_VERIFIED_2026-08-08",
        engineer_approval_authority=("Baraa Misto" if interpretation_id is not None else None),
        engineer_approval_date=(date(2026, 8, 8) if interpretation_id is not None else None),
    )


def asce_74_23_chapter_7_source(
    *,
    section: str,
    equation_reference: str | None = None,
) -> CalculationSourceSnapshot:
    """Create the canonical Slice 4 Chapter 7 source locator."""

    return CalculationSourceSnapshot(
        standard_name=ASCE_74_23_STANDARD_NAME,
        edition=ASCE_74_23_EDITION,
        chapter="7",
        section=section,
        equation_reference=equation_reference,
        errata_identifier=ASCE_74_23_ERRATUM,
        errata_effective_date=ASCE_74_23_ERRATUM_EFFECTIVE_DATE,
        chapter_affected_by_errata=False,
        interpretation_id=None,
        source_classification=SourceClassification.CODE_CHARACTERISTIC,
        source_revision="CALCULATION_SLICE_4_RC1_VERIFIED_2026-08-30",
    )


__all__ = (
    "ASCE_74_23_EDITION",
    "ASCE_74_23_ERRATUM",
    "ASCE_74_23_ERRATUM_EFFECTIVE_DATE",
    "ASCE_74_23_STANDARD_NAME",
    "TRANSVERSE_ENDPOINT_INTERPRETATION_ID",
    "CalculationSourceSnapshot",
    "QualificationStatus",
    "SourceClassification",
    "asce_74_23_chapter_7_source",
    "asce_74_23_chapter_8_source",
)
