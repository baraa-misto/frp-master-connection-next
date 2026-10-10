"""Isolated hypothetical decision inputs; no laboratory evidence or provider record."""

from decimal import Decimal

from frp_master_connection.application.direct_qualification_matching import COVERED_RESPONSES
from frp_master_connection.application.direct_status import (
    WHOLE_CONNECTION,
    DirectDecisionInput,
    RequiredCheck,
)


def authoritative_input() -> DirectDecisionInput:
    checks = (
        RequiredCheck(
            "BOLT_SHEAR:B_R1_L1",
            "Bolt shear",
            "ANALYTICALLY_EVALUATED",
            "PASS",
            Decimal(".5"),
            {"value": "2", "unit": "N"},
            {"value": "4", "unit": "N"},
        ),
        *(RequiredCheck(i, i, "REQUIRED_UNRESOLVED") for i in COVERED_RESPONSES),
        RequiredCheck(WHOLE_CONNECTION, "Whole connection", "REQUIRED_UNRESOLVED"),
        RequiredCheck(
            "HEEL",
            "Bounded heel mechanism",
            "NOT_APPLICABLE",
            reason="Source-backed bounded two-cut mechanism",
        ),
        RequiredCheck("MATERIAL", "Neutral information", "NEUTRAL_INFORMATION"),
    )
    return DirectDecisionInput(
        "A" * 64,
        checks,
        {
            "record_state": "AVAILABLE_FOR_MATCH",
            "statistics_state": "VALID",
            "scope_match_state": "MATCHED",
            "coverage_state": "COVERED_BY_QUALIFICATION",
            "covered_response_ids": list(COVERED_RESPONSES),
            "capacity_state": "CAPACITY_PASS",
            "gravity_eq_2_2_state": "PASS",
            "mismatch_reasons": [],
            "synthetic": False,
            "selected_record_id": "HYPOTHETICAL_DECISION_INPUT_ONLY",
            "record_revision": 1,
            "record_digest": "B" * 64,
            "evaluation_digest": "C" * 64,
            "Ru": {"value": "2", "unit": "N"},
            "Rd_q": {"value": "4", "unit": "N"},
            "utilization": ".5",
        },
        True,
        False,
        True,
    )
