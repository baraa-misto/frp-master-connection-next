"""Server-owned HYB1 physical coverage inventory; no adopted new method."""

from dataclasses import dataclass

from .hyb1_contract import Alignment

MISSING_IDS = (
    "FIRST_ROW:layer-A",
    "FIRST_ROW:layer-B",
    "INTERROW:layer-B:BOLT_LINE_1",
    "BLOCK_SHEAR:layer-B:BLOCK_L_LEFT_ROW_1_BOLT_LINE_1",
    "BLOCK_SHEAR:layer-B:BLOCK_L_RIGHT_ROW_1_BOLT_LINE_1",
)
EXISTING_IDS = (
    "BOLT_SHEAR:B_R1_L1",
    "BOLT_SHEAR:B_R2_L1",
    "PIN_BEARING:layer-A:B_R1_L1",
    "PIN_BEARING:layer-A:B_R2_L1",
    "PIN_BEARING:layer-B:B_R1_L1",
    "PIN_BEARING:layer-B:B_R2_L1",
    "INTERROW:layer-A:BOLT_LINE_1",
    "BLOCK_SHEAR:layer-A:BLOCK_L_LEFT_ROW_1_BOLT_LINE_1",
)
HEEL = "BLOCK_SHEAR:layer-A:BLOCK_L_RIGHT_ROW_1_BOLT_LINE_1"
ADDITIONAL_3D = ("ANGLE_HEEL_3D", "W_FLANGE_WEB_JUNCTION_3D", "OUT_OF_PLANE_CONTACT_PRYING")
REQUIRED_IDS = (*EXISTING_IDS, *MISSING_IDS, HEEL, *ADDITIONAL_3D)


@dataclass(frozen=True, slots=True)
class MethodMapping:
    alignment: Alignment
    target_key: str
    native_id: str
    disposition: str
    equation_locator: str
    physical_path: str
    hole_thickness_policy: str
    demand_domain: str
    property_basis: str
    interactions: str
    exclusion: str
    decision_id: str


def direct_mappings(alignment: Alignment) -> tuple[MethodMapping, ...]:
    if not isinstance(alignment, Alignment):
        raise TypeError("Mapping requires an actual governed alignment.")
    direction = (
        "Angle LW aligned bolts; W oblique/staggered paths; retained eccentric moments"
        if alignment is Alignment.BRACE
        else "W LW aligned bolts; Angle staggered transverse projection; Route C geometry-only"
    )
    specifications = (
        (
            "ANGLE_FIRST_ROW",
            MISSING_IDS[0],
            "EXACT_METHOD_QUESTION",
            "No companion first-row equation",
            "Angle leg net cut, integral heel continuity; true submitted loaded end e1=3 in",
            "Q1",
            "Beam global tensile term is not first-row bearing/bypass stress capacity",
        ),
        (
            "W_FIRST_ROW",
            MISSING_IDS[1],
            "EXACT_METHOD_QUESTION",
            "No companion first-row equation",
            "W flange net cut with continuous web; remote N/V/M unknown",
            "Q2",
            "Column bearing D168 cannot replace first-row net tension",
        ),
        (
            "W_INTERROW",
            MISSING_IDS[2],
            "REFERENCE_ONLY",
            "Calcs D59:D80 beam-local reference",
            "W inter-hole shear surfaces require its own signed direction and transfer domain",
            "Q2",
            "Beam per-bolt P/n,V/n tear-out is not W inter-row applicability",
        ),
        (
            "W_BLOCK_LEFT",
            MISSING_IDS[3],
            "REFERENCE_ONLY",
            "Calcs D87:D112; PulTex Ch4 p104",
            (
                "Negative W-CW outstand: BRACE two-hole triangular release "
                "candidate; SUPPORT needs true end"
            ),
            "Q2",
            "Native L_LEFT is not a verified W free-end release or receiving-member block model",
        ),
        (
            "W_BLOCK_RIGHT",
            MISSING_IDS[4],
            "REFERENCE_ONLY",
            "Calcs D87:D112; PulTex Ch4 p104",
            "Positive W-CW side crosses integral web; independent 3D release needed",
            "Q2",
            "Do not replace integral web with free edge or use display crop as end",
        ),
    )
    rows = tuple(
        MethodMapping(
            alignment,
            key,
            native,
            disposition,
            source,
            path,
            (
                "Actual hole 0.563 in; no imported ASCE 0.063 allowance; unresolved "
                "net/gross and doubler engagement Q3"
            ),
            direction + "; no P/n or V/n eccentric shortcut; all six signed actions retained Q4",
            (
                "Actual ASCE minimum characteristic material unchanged; RHM "
                "polyester listed/SF4 table is reference only Q5"
            ),
            (
                "Simultaneous actions of each independent ASD case; no "
                "double-counted tensile/shear capacity"
            ),
            exclusion,
            question,
        )
        for key, native, disposition, source, path, question, exclusion in specifications
    )
    if alignment is Alignment.SUPPORT:
        rows += tuple(
            MethodMapping(
                alignment,
                "CHANGED_ANGLE_LAYOUT",
                native,
                "EXACT_METHOD_QUESTION",
                "Existing ASCE aligned-row calculation domain",
                "Staggered Angle cut/contact path",
                "Same physical holes; preserve true member ends and heel continuity",
                direction,
                "Existing characteristic properties retained",
                "Must freshly establish applicable row/path mapping",
                "No copied BRACE result or inherited heel N/A",
                "Q4",
            )
            for native in (EXISTING_IDS[6], EXISTING_IDS[7], HEEL)
        )
    return rows + tuple(
        MethodMapping(
            alignment,
            "ADDITIONAL_3D",
            native,
            "EXACT_METHOD_QUESTION",
            "No RHM contact/3D companion equation supplied",
            native,
            "True solid/junction and reinforcement engagement required",
            direction,
            "No adopted 3D or environmental ASD policy",
            "Transported out-of-plane action remains active",
            (
                "Bolt equilibrium alone does not prove FRP stress transfer or "
                "Section 2.3.2 qualification"
            ),
            "Q4",
        )
        for native in ADDITIONAL_3D
    )


def clip_tee_reference_uses(alignment: Alignment) -> tuple[MethodMapping, ...]:
    """Additional source leads only; the original Direct mappings are unchanged."""
    rows = direct_mappings(alignment)
    locators = {
        "ANGLE_FIRST_ROW": "Clip Tee Calcs!D54:D66: global tension term, no first-row law",
        "W_FIRST_ROW": "Clip Tee Calcs!D149:D231: flange flexure/bearing, no net section",
        "W_INTERROW": "Clip Tee Calcs!D41:D52: brace end tear-out, not receiving W inter-row",
        "W_BLOCK_LEFT": "Clip Tee Calcs!D54:D66: brace global path, not W LEFT release",
        "W_BLOCK_RIGHT": "Clip Tee Calcs!D54:D66: brace global path, not integral-web W RIGHT",
        "CHANGED_ANGLE_LAYOUT": "Clip Tee Calcs!D41:D66: uniform six-bolt brace path only",
        "ANGLE_HEEL_3D": "Clip Tee Calcs!D127:D144: Tee flange plate interaction only",
        "W_FLANGE_WEB_JUNCTION_3D": (
            "Clip Tee Calcs!D149:D179: selected reinforced-flange reference only"
        ),
        "OUT_OF_PLANE_CONTACT_PRYING": (
            "Clip Tee Calcs!D233:D248: aggregate bolts, no prying/contact law"
        ),
    }
    return tuple(
        MethodMapping(
            alignment,
            row.target_key,
            row.native_id,
            "REFERENCE_ONLY",
            locators.get(row.native_id, locators.get(row.target_key, "")),
            row.physical_path,
            (
                "Actual Direct geometry untouched; gross source lengths and selected SS "
                "reinforcement are not transferred"
            ),
            row.demand_domain + "; source P/n and N/2 are not an eccentric solver",
            "Separate vinyl-ester source/SF4 and 316SS reference groups; no MAT1 or F593 changes",
            "Tee combined flange uses D144; no global tension term counted as separate net tension",
            row.exclusion + "; no actual Direct mechanism discharged by this supplementary source",
            row.decision_id,
        )
        for row in rows
    )
