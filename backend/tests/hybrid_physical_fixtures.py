"""P4 current-input controlled specimens; no expected production outputs."""

from copy import deepcopy
from typing import Any

from tests.hybrid_same_connection_fixtures import same_connection


def physical_case() -> dict[str, Any]:
    body = deepcopy(same_connection())
    body["workspace_id"] = "p4-current-physical"
    body["geometry"]["xb"]["value"] = "1"
    case = body["lrfd_cases"][0]
    case["case_id"] = "p4-receiving-longitudinal"
    case["frame"] = "DIRECT_RECEIVING_LW_CW_TT"
    for i, q in enumerate(case["components"]):
        q["value"] = ".1" if i == 0 else "0"
    body["physical_context"] = {
        "contract": "HYB2-D3-P4-PHYSICAL/1",
        "positive_end": {"condition": "FREE", "distance": {"value": "5", "unit": "in"}},
        "negative_end": {"condition": "CONTINUOUS", "distance": None},
        "hole_source": "US_CUSTOMARY_PRINTED",
        "clear_flat_outstand": {"value": "1.5", "unit": "in"},
        "interface_gap": {"value": "0", "unit": "in"},
        "receiving_actions": [
            {
                "case_id": case["case_id"],
                "components": [
                    {"value": "0", "unit": "kip" if i < 3 else "kip-in"} for i in range(6)
                ],
            }
        ],
    }
    return body
