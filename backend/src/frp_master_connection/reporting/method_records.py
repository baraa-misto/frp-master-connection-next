"""Read-only presentations for executed native records outside multi-row checks.

The expressions are reviewed against the frozen calculation methods. Numerical
values are read from the signed response, never recalculated by the report.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MethodRecord:
    title: str
    expression: str
    explanation: str


EXECUTED_METHODS: dict[str, MethodRecord] = {
    "RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1": MethodRecord(
        "W/I region resultant decomposition",
        "A=sum(A_i); I=sum(I_i+A_i y_i^2); N_i=P A_i/A+M A_i y_i/I; "
        "M_local,i=M I_i/I; M_global,i=y_i N_i+M_local,i",
        "The controlled demand-only W/I integration allocates signed member actions "
        "to top flange, web and bottom flange. The native record proves exact recovery.",
    ),
    "RATIONAL_ELASTIC_CHANNEL_REGION_RESULTANT_DECOMPOSITION_RC1": MethodRecord(
        "Channel region resultant decomposition",
        "A=sum(A_i); I_major=sum(I_major,i+A_i v_i^2); "
        "N_i=P A_i/A+M_major A_i v_i/I_major; "
        "M_local,i=M_major I_major,i/I_major",
        "The controlled demand-only Channel integration retains centroid and shear-center "
        "references, signed component forces, free torsion and exact recovery.",
    ),
    "RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1": MethodRecord(
        "Thin-wall channel shear center",
        "h_m=d-t_f; b_m=b_f-t_w/2; "
        "I_m=t_w h_m^3/12+2 t_f b_m(h_m/2)^2; "
        "e=t_f h_m^2 b_m^2/(4 I_m); t_sc=t_web-e",
        "This is the native rational thin-wall shear-center calculation. The section "
        "record retains the alternate closed expression and method provenance.",
    ),
    "RATIONAL_BALANCED_FLANGE_FACE_COUPLE_DECOMPOSITION_RC1": MethodRecord(
        "Balanced flange-face force lines",
        "e_o=v_o-v_f; e_i=v_i-v_f; "
        "F_o=(M_local-e_i F)/(e_o-e_i); "
        "F_i=(e_o F-M_local)/(e_o-e_i); F_each-inner=F_i/2",
        "The native branch solves force and moment equilibrium at two physical force "
        "lines and proves both residuals; it does not assume an arbitrary stiffness share.",
    ),
    "RATIONAL_CHANNEL_WEB_FACE_SHEAR_CENTER_COUPLE_DECOMPOSITION_RC1": MethodRecord(
        "Channel web-face shear-center couple",
        "e_b=t_b-t_web; e_o=t_o-t_web; "
        "V_b=(T_free+e_o V_web)/(e_o-e_b); V_o=V_web-V_b; "
        "N_each=N_web/2; M_each=M_local/2",
        "The native branch resolves both web-face shear forces from signed free "
        "torsion and checks force, major moment and torsion recovery.",
    ),
    "ANGLE_CONNECTOR_INTERFACE_WRENCH_CORE_RC1": MethodRecord(
        "Angle connector interface wrench transport",
        "F_target=F_source; M_target=M_source+(r_source-r_target) cross F; reaction=-handoff",
        "The native core transports the full six-component wrench among member, "
        "heel and support references and retains the equilibrium proof.",
    ),
    "RATIONAL_ELASTIC_IN_PLANE_BOLT_GROUP_WRENCH_DEMAND_RC1": MethodRecord(
        "Exact in-plane bolt-group wrench distribution",
        "c=mean(r_i); J=sum|r_i-c|^2; M_c=M_ref+(r_ref-c) cross F; "
        "F_i=F/n+(M_c/J)(-delta_b,i,delta_a,i)",
        "The native exact-rational solution includes each bolt vector and four "
        "force/moment recovery identities. A zero polar sum with nonzero moment is unsupported.",
    ),
    "ASCE74_EQ_7_12_LONGITUDINAL_PLATE_TENSION": MethodRecord(
        "Longitudinal plate tension",
        "R_n=0.7 A_net,eff F_t,L,adjusted; R_d=phi lambda R_n",
        "The native Chapter 7 plate engine consumes the adjusted property once. "
        "The area is per unit width and the result is force per unit width.",
    ),
    "RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1": MethodRecord(
        "Rational web-splice plate-body interaction",
        "sigma=N_plate/A +/- M_plate c/I; tau=V_plate/A; U=|sigma|/F_normal,d+|tau|/F_shear,d",
        "Two symmetric plate shares and both signed extreme fibers are evaluated. "
        "The tensile or compressive design stress follows the sign of each native fiber.",
    ),
    "ASCE_74_23_EQ_8_15_CLIP_ANGLE_INSTEP_SHEAR_RC1": MethodRecord(
        "Clip-angle instep shear",
        "L_eff=L-sum(heel-end reliefs); R_n=L_eff t F_sh,LT,adjusted; "
        "R_d=0.70 R_n; U=|F_heel,x|/R_d",
        "The native connector provider uses the existing adjusted shear property once. "
        "This check does not qualify the entire angle-body wrench envelope.",
    ),
    "NATIVE_ASCE_8_5": MethodRecord(
        "Support-side FRP bearing",
        "R_n=t d F_br C_thread; R_d=phi lambda C_lap C_delta R_n",
        "The signed support-local trace records the actual property, factors and "
        "result for the identified support-side bolt and layer.",
    ),
    "DCTN_AXIAL_SYMMETRIC_HALF_SHARE_RESPONSE_RC1": MethodRecord(
        "Symmetric axial double-channel response",
        "P_row=f_row P_member; P_side=P_row/2; "
        "cut_j=sum(layer transfers through j); V_plane=|cut_j|",
        "The native response retains signed row loads, both channel shares, "
        "physical shaft cuts, plane demands and conservation proofs. Its symmetry "
        "qualification does not imply global member design.",
    ),
    "SSMC_3_ANALYTICAL_SINGLE_LAP_RC1": MethodRecord(
        "Stair-stringer miter analytical single-lap orchestration",
        "At each physical interface, action and reaction are equal and opposite; "
        "signed group actions are transported to actual member cuts",
        "The analytical response retains serial member and plate actions, cut candidates, "
        "source-limited checks and blockers. Finite cut coverage is not a proof of "
        "continuous-path or global-stair adequacy.",
    ),
    "SSMC_ACTUAL_POLYGON_CUT_FREE_BODY_RC1": MethodRecord(
        "Actual-polygon member cut demand",
        "A_net=t sum(interval widths); sigma_edge=N/A_net+M(y_edge-y_c)/I_net; tau_average=V/A_net",
        "The native cut method clips the actual polygon and hole intervals, transports "
        "signed shaft loads, and prints demand-only stresses at finite candidate cuts. "
        "No qualified resistance or continuous-path proof is inferred.",
    ),
}


_EXECUTED_STATUSES = frozenset(
    {
        "CALCULATED",
        "CALCULATED_DEMAND_ONLY",
        "PASS",
        "FAIL",
        "PASS_RATIONAL_METHOD",
        "FAIL_RATIONAL_METHOD",
        "QUALIFIED",
    }
)
_NO_STATUS_METHODS = frozenset(
    {
        "RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1",
        "RATIONAL_ELASTIC_CHANNEL_REGION_RESULTANT_DECOMPOSITION_RC1",
        "RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1",
        "RATIONAL_BALANCED_FLANGE_FACE_COUPLE_DECOMPOSITION_RC1",
        "RATIONAL_CHANNEL_WEB_FACE_SHEAR_CENTER_COUPLE_DECOMPOSITION_RC1",
        "ANGLE_CONNECTOR_INTERFACE_WRENCH_CORE_RC1",
        "ASCE74_EQ_7_12_LONGITUDINAL_PLATE_TENSION",
        "ASCE_74_23_EQ_8_15_CLIP_ANGLE_INSTEP_SHEAR_RC1",
        "SSMC_3_ANALYTICAL_SINGLE_LAP_RC1",
    }
)


def executed_records(value: object) -> dict[str, tuple[str, dict[str, Any]]]:
    """Find one worked native record per method with a result-bearing contract."""

    examples: dict[str, tuple[str, dict[str, Any]]] = {}

    def walk(
        item: object,
        path: str,
        parent: dict[str, Any] | None = None,
        grandparent: dict[str, Any] | None = None,
    ) -> None:
        if isinstance(item, dict):
            method = item.get("method")
            status = item.get("status")
            executed = (isinstance(status, str) and status in _EXECUTED_STATUSES) or (
                isinstance(method, str) and method in _NO_STATUS_METHODS
            )
            if (
                isinstance(method, str)
                and executed
                and method != "RATIONAL_ELASTIC_BOLT_GROUP_ECCENTRICITY"
                and method not in examples
            ):
                presented = item
                if (
                    method
                    in {
                        "RATIONAL_ELASTIC_WI_REGION_RESULTANT_DECOMPOSITION_RC1",
                        "RATIONAL_ELASTIC_CHANNEL_REGION_RESULTANT_DECOMPOSITION_RC1",
                    }
                    and parent is not None
                ):
                    presented = parent
                elif method == "RATIONAL_THIN_WALL_CHANNEL_SHEAR_CENTER_RC1" and (
                    grandparent is not None and isinstance(grandparent.get("shear_center"), dict)
                ):
                    presented = grandparent["shear_center"]
                examples[method] = (path, presented)
            for key, child in item.items():
                if key not in {"visualization", "geometry"}:
                    walk(child, f"{path}.{key}", item, parent)
        elif isinstance(item, list):
            for index, child in enumerate(item):
                walk(child, f"{path}[{index}]", parent, grandparent)

    walk(value, "result")
    return examples


__all__ = ("EXECUTED_METHODS", "MethodRecord", "executed_records")
