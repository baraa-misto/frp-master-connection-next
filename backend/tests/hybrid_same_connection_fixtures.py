"""P3 input specimens: an independent LRFD action, never an ASD multiplier."""

from copy import deepcopy
from typing import Any

from tests.direct_mc1_fixtures import mc1_body
from tests.hybrid_workflow_fixtures import live_source, q


def same_connection() -> dict[str, Any]:
    body = live_source()
    material = mc1_body()
    body.update(
        workspace_id="same-connection-P3",
        include_native_lrfd=True,
        same_connection_lrfd={
            "assignments": material["assignments"],
            "fastener": material["fastener"],
        },
        lrfd_cases=[
            {
                **deepcopy(body["asd_cases"][0]),
                "case_id": "entered-LRFD-A",
                "components": [
                    q(".15", "kip"),
                    q(".02", "kip"),
                    q("0", "kip"),
                    q("0", "kip-in"),
                    q("0", "kip-in"),
                    q("0", "kip-in"),
                ],
            }
        ],
    )
    return body
