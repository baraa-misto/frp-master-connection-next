"""REPORT1 route inventory and same-response snapshot capture."""

from __future__ import annotations

from typing import Literal

_CALCULATION_FAMILIES = frozenset(
    {
        "single-bolt",
        "multi-row",
        "tee-connector",
        "clip-angle",
        "paired-clip-angle",
        "multi-member-tee",
        "beam-concrete-paired-angle",
        "direct-side-lap-concrete",
        "column-base-web-angles",
        "beam-web-splice",
        "wi-major-axis-moment-splice",
        "channel-major-axis-moment-splice",
        "wi-beam-concrete-wall-moment",
        "wi-beam-frp-support-moment",
        "angle-column-two-leg-moment-base",
        "wi-rhs-srs-column-moment-base",
        "double-channel-truss-node",
        "stair-stringer-miter",
    }
)
_MAT1_FAMILIES = {
    "single-bolt": "single-bolt",
    "multi-row": "multi-row",
    "tee-connector": "tee-connector",
    "stair-stringer-miter": "stair-stringer-miter",
}


def reportable_route(
    path: str, request: dict[str, object]
) -> tuple[str, Literal["design", "input_only"]] | None:
    """Only known native routes may issue REPORT1 authority."""

    parts = path.strip("/").split("/")
    if parts[:3] == ["api", "v1", "calculations"] and len(parts) == 5:
        family, operation = parts[3:]
        if family not in _CALCULATION_FAMILIES:
            return None
        if operation == "preview":
            return family, "input_only"
        if operation in {"design-check", "analytical-design-check"} or (
            family == "single-bolt" and operation == "evaluate"
        ):
            return family, "design"
    if parts[:3] == ["api", "v1", "frp-materials"] and parts[-1] in {
        "design-check",
        "analytical-design-check",
    }:
        if parts[3:-1] == ["family"]:
            family_id = request.get("family_id")
            if isinstance(family_id, str) and family_id in _CALCULATION_FAMILIES:
                return family_id, "design"
        if len(parts) == 5 and parts[3] in _MAT1_FAMILIES:
            return _MAT1_FAMILIES[parts[3]], "design"
    return None


__all__ = ("reportable_route",)
