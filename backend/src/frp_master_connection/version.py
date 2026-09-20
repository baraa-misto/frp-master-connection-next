"""Controlled application and engineering-capability metadata."""

from typing import Final

PRODUCT_ID: Final = "frp-master-connection"
APPLICATION_VERSION: Final = "0.0.0.dev0"
PROJECT_SCHEMA_VERSION: Final = "0.1.0-draft"
CALCULATION_ENGINE_VERSION: Final = "0.1.0.dev1"
ENGINEERING_RULE_SET_VERSION: Final = "asce74-23-ch8-single-bolt-rc2.dev1"
CODE_BASIS: Final = "ASCE/SEI 74-23"
ERRATA_STATUS: Final = "Erratum 1 verified; effective 2026-01-13"

ENGINEERING_CALCULATIONS_AVAILABLE: Final = True
REPORT_GENERATION_AVAILABLE: Final = False

__all__ = (
    "APPLICATION_VERSION",
    "CALCULATION_ENGINE_VERSION",
    "CODE_BASIS",
    "ENGINEERING_CALCULATIONS_AVAILABLE",
    "ENGINEERING_RULE_SET_VERSION",
    "ERRATA_STATUS",
    "PRODUCT_ID",
    "PROJECT_SCHEMA_VERSION",
    "REPORT_GENERATION_AVAILABLE",
)
