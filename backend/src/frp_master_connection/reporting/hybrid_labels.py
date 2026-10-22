"""Human-readable presentation only. Stored identifiers and ratios are untouched."""

import re
from decimal import Decimal

LABELS = {
    "brace_leg": "Angle connected-leg width",
    "brace_near_v_edge_distance": "Angle near-edge distance in source V direction",
    "brace_thickness": "Angle thickness",
    "column_flange": "Receiving I flange width",
    "column_thickness": "Receiving I flange thickness",
    "diameter": "Bolt diameter",
    "hole": "Hole diameter",
    "phi": "Brace angle to source horizontal (degrees)",
    "vertical_bolt_pitch": "Actual vertical bolt center spacing",
    "xb": "Brace edge to bolt-column centerline (Xb)",
    "xc": "Receiving-member common-edge distance (Xc)",
    "UNCHANGED_NATIVE_ASCE": "Existing ASCE calculation",
    "HYB2_DIRECT_REFERENCE": "RHM reference calculation",
    "DIRECT_SHARED_BOLTS": "Shared bolts - shear",
    "DIRECT_BRACE_BEARING": "Angle connected leg - bearing",
    "DIRECT_BRACE_LOCAL": "Angle connected leg - local shear paths",
    "DIRECT_BRACE_GLOBAL": "Angle - global block shear reference",
    "DIRECT_COLUMN_BEARING": "Receiving I flange - bearing",
    "DIRECT_COLUMN_LOCAL": "Receiving I flange - local shear paths",
    "DIRECT_COLUMN_GLOBAL": "Receiving I flange - global block shear reference",
    "NOT_ESTABLISHED_SECTION_2_3_2": "Not established; Section 2.3.2 remains open",
    "DIRECT_USER_HYBRID": "Current Direct connection",
    "NO_NATIVE_ASCE": "ASCE LRFD not evaluated for this physical layout",
    "RHM_POLYESTER_100F_SF4": "RHM polyester, 100 F, listed strengths / safety factor 4",
    "UNMATCHED": "No matching source property profile",
    "layer-A": "Angle connected leg",
    "layer-B": "Receiving I flange",
}


def label(value: str) -> str:
    parts = []
    for part in value.split(":"):
        bolt = re.fullmatch(r"B_R(\d+)_L(\d+)", part)
        parts.append(
            f"Bolt row {bolt[1]}, line {bolt[2]}"
            if bolt
            else LABELS.get(part, part.replace("_", " ").capitalize())
        )
    return " - ".join(parts)


def utilization(value: object, *, technical: bool) -> str:
    if value is None:
        return "Not evaluated"
    return str(value) if technical else format(Decimal(str(value)), ".3f")
