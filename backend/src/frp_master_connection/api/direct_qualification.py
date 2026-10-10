"""Direct-only qualification adapter; engineering/F7 aggregates stay untouched."""

from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal, localcontext
from threading import RLock
from typing import Any, Literal, cast

from pydantic import StrictStr

from frp_master_connection.api.schemas import QuantityDTO
from frp_master_connection.application.direct_qualification_matching import (
    COVERED_RESPONSES,
    match_scope,
    response_coverage,
)
from frp_master_connection.application.direct_qualification_statistics import recompute_statistics
from frp_master_connection.application.mat1_materials import PropertyLedger
from frp_master_connection.calculation.quantities import (
    Dimension,
    PhysicalQuantity,
    Unit,
    canonical_decimal_string,
    decimal_value,
)
from frp_master_connection.infrastructure.direct_qualification_records import (
    EvidenceModel,
    ImmutableQualificationRecord,
    Text,
    content_digest,
    production_provider,
)
from frp_master_connection.reporting.snapshot import SnapshotError


class ActualProductIdentity(EvidenceModel):
    mat1_record_id: Text
    manufacturer: Text
    product: Text
    resin: Text
    fiber_architecture: Text
    profile_product_revision: Text
    material_qualification_id: Text
    profile_kind: Literal["FLAT_L", "MANUFACTURED_FILLETED_ANGLE", "WIDE_FLANGE"]
    heel_radius: QuantityDTO


class QualificationDesignContext(EvidenceModel):
    """Project declarations are match inputs; they grant no source approval."""

    products: dict[StrictStr, ActualProductIdentity]
    bolt_length: QuantityDTO
    grip: QuantityDTO
    installation: Text
    washer_count: Text
    fixture_id: Text
    fixture_stiffness: Text
    support_restraints: Text
    member_load_introduction: Text
    loading_type: Literal["GRAVITY_D_L", "WIND", "TORNADO", "SEISMIC", "OTHER"]
    loading_history: Literal["MONOTONIC_STATIC", "CYCLIC", "REVERSED", "FATIGUE", "NONPROPORTIONAL"]
    loading_rate: Text
    protocol_id: Text
    dead_load: QuantityDTO | None = None
    live_load: QuantityDTO | None = None


def normalized(value: object) -> object:
    """Exact existing unit conversion; no engineering or coordinate tolerance."""
    if isinstance(value, dict):
        if "value" in value and value.get("unit") in {unit.value for unit in Unit}:
            quantity = PhysicalQuantity.of(value["value"], Unit(value["unit"]))
            return {"value": quantity.canonical_string, "unit": quantity.canonical_unit.value}
        if all(axis in value for axis in ("x", "y", "z")) and value.get("unit") in {
            unit.value for unit in Unit
        }:
            return {
                **{
                    axis: PhysicalQuantity.of(value[axis], Unit(value["unit"])).canonical_string
                    for axis in ("x", "y", "z")
                },
                "unit": PhysicalQuantity.of("1", Unit(value["unit"])).canonical_unit.value,
            }
        return {key: normalized(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalized(item) for item in value]
    return value


def authenticated_scope(
    legacy: dict[str, Any],
    material_sources: dict[str, Any],
    fastener_source: dict[str, Any],
    context: QualificationDesignContext | None,
    preview: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Decimal | None]:
    """Use validated native inputs and resolved MAT1/hardware, never client results."""
    physical = legacy["physical_connection"]
    joint = physical["joint_assembly"]
    actions = joint["member_end_actions"]
    ctx = {} if context is None else context.model_dump(mode="json")
    products = ctx.get("products", {})
    conditions = dict(material_sources["qualification_conditions"])
    if conditions["chemical"] == "NONE_DECLARED":
        for field in (
            "chemical_substance",
            "chemical_concentration",
            "chemical_contact_form",
            "chemical_duration",
        ):
            if not conditions[field]:
                conditions[field] = "NOT_APPLICABLE_NO_CHEMICAL_EXPOSURE"
    if conditions["time_category"] in {
        "DEAD_ONLY",
        "WIND_TORNADO_SEISMIC",
        "SNOW_RAIN_FLOOD_ATMOSPHERIC_ICE",
    }:
        conditions["live_load_subtype"] = "NOT_APPLICABLE_TO_SELECTED_LOAD_CATEGORY"
    if not conditions.get("fatigue_cycles") and ctx.get("loading_history") == "MONOTONIC_STATIC":
        conditions["fatigue_cycles"] = "NONE_DECLARED_FOR_MONOTONIC_PROTOCOL"
    material_identity = {}
    for layer in legacy["layers"]:
        component = layer["component_id"]
        material = material_sources["overrides"].get(component, material_sources["default"])
        product = products.get(component)
        material_identity[component] = {
            "mat1_record_id": material["id"],
            "mat1_record_revision": material["revision"],
            "mat1_digest": material["content_digest"],
            "resin": material["resin"],
            "actual_product": product
            if product is not None
            and product["mat1_record_id"] == material["id"]
            and product["resin"] == material["resin"]
            else None,
        }
    source = actions[0] if len(actions) == 1 else None
    action_scope: dict[str, Any] = {
        "capacity_measure": "FORCE_RESULTANT_N",
        "action_count": len(actions),
        "frame_kind": None if source is None else source["coordinate_frame_kind"],
        "frame_owner": None if source is None else source["coordinate_frame_owner_id"],
        "reference_point": None if source is None else normalized(source["reference_point"]),
        "convention": None if source is None else source["convention"],
        "loading_type": ctx.get("loading_type"),
        "loading_history": ctx.get("loading_history"),
        "loading_rate": ctx.get("loading_rate"),
        "protocol_id": ctx.get("protocol_id"),
        "demand_source": legacy["demand_source"],
    }
    if source is not None and action_scope["reference_point"]["position"] is None:
        kind = action_scope["reference_point"]["kind"]
        if kind in {"MEMBER_CONNECTED_END", "BOLT_GROUP_ORIGIN"}:
            action_scope["reference_point"]["position"] = "DEFINED_BY_" + kind
    required = None
    if source is not None and legacy["demand_source"] == "AUTOMATIC_MEMBER_END_FORCE":
        for prefix, key in (("F", "force"), ("M", "moment")):
            for axis in ("x", "y", "z"):
                action_scope[prefix + axis] = PhysicalQuantity.of(
                    source[key][axis], Unit(source[key]["unit"])
                ).canonical_string
        with localcontext() as decimal_context:
            decimal_context.prec = 80
            required = sum(
                (decimal_value(action_scope["F" + axis]) ** 2 for axis in ("x", "y", "z")),
                Decimal(0),
            ).sqrt()
    geometry_fields = (
        "row_count",
        "bolts_per_row",
        "bolt_diameter",
        "hole_basis",
        "pitch",
        "gauge",
        "unloaded_end_e1",
        "loaded_boundary_to_row_1_distance",
        "negative_side_distance",
        "positive_side_distance",
        "force_line_offset",
    )
    scope = {
        "connection_scope": {
            "family": "DIRECT_SINGLE_ANGLE_TO_W",
            "lap": legacy["lap_configuration"],
            "material_pair": legacy["material_pair"],
            "selected_faces": physical["geometry_template"],
        },
        "material_identity": material_identity,
        "fastener_identity": {
            "controlled_hardware": {
                key: fastener_source.get(key)
                for key in (
                    "id",
                    "catalog_digest",
                    "catalog_revision",
                    "specification",
                    "alloy_group",
                    "alloys",
                    "condition",
                    "marking",
                    "nut",
                    "washer_basis",
                    "installation",
                )
            },
            "thread_planes": [
                {"plane_id": plane["plane_id"], "thread_status": plane["thread_status"]}
                for plane in fastener_source.get("shear_planes", [])
            ],
            "washer_geometry": physical["fastener_snapshot"].get("washer_geometry"),
            "bolt_length": ctx.get("bolt_length"),
            "grip": ctx.get("grip"),
            "installation": ctx.get("installation"),
            "washer_count": ctx.get("washer_count"),
        },
        "geometry_scope": {
            **{key: legacy[key] for key in geometry_fields},
            "canonical_bolt_layout": None
            if preview is None
            else {
                "bolts": [
                    {
                        **bolt,
                        **{
                            axis: PhysicalQuantity.of(
                                bolt[axis], Unit(preview["visualization"]["source_length_unit"])
                            ).canonical_string
                            for axis in ("x", "y")
                        },
                    }
                    for bolt in preview["visualization"]["bolts"]
                ],
                "length_unit": "mm",
            },
            "members": [
                {
                    "role": member["role"],
                    "section": member["section"],
                    "material_orientation": member["material_orientation"],
                }
                for member in joint["members"]
            ],
        },
        "action_scope": action_scope,
        "environmental_scope": {"conditions": conditions},
        "support_scope": {
            "longitudinal_ends": legacy.get("supporting_w_longitudinal_ends"),
            "fixture_id": ctx.get("fixture_id"),
            "fixture_stiffness": ctx.get("fixture_stiffness"),
            "support_restraints": ctx.get("support_restraints"),
            "member_load_introduction": ctx.get("member_load_introduction"),
        },
    }
    ends = scope["support_scope"]["longitudinal_ends"]
    if isinstance(ends, dict) and ends["condition"] != "UNSPECIFIED":
        for field in ("negative_end_distance", "positive_end_distance"):
            if ends.get(field) is None:
                ends[field] = "CONTINUOUS_NO_FINITE_END"
    return cast(dict[str, Any], normalized(scope)), required


def qualification_capacity(
    record: dict[str, Any],
    scope: dict[str, Any],
    ledgers: list[PropertyLedger],
    ro: Decimal,
    phi: Decimal,
) -> tuple[Decimal | None, list[dict[str, Any]], tuple[str, ...]]:
    """Consume MAT1-resolved coefficients and lambda, each at most once."""
    protocol = record["statistical_protocol"]
    baseline = protocol["baseline"]
    blockers: list[str] = []
    trace: list[dict[str, Any]] = []
    strength = next(
        (ledger for ledger in ledgers if ledger.property_id == "tensile_strength_L"), None
    )
    if strength is None or strength.lambda_factor is None:
        return None, trace, ("EXISTING_MAT1_STRENGTH_AND_LOAD_FACTOR_REQUIRED",)
    if any(
        (item.cm, item.ct, item.cch, item.lambda_factor)
        != (strength.cm, strength.ct, strength.cch, strength.lambda_factor)
        for item in ledgers
        if item.property_id == "tensile_strength_L"
    ):
        return None, trace, ("WHOLE_JOINT_MULTIPLE_MATERIAL_FACTOR_BASIS_UNRESOLVED",)
    conditioned = set(protocol["conditioned_factor_ids"])
    if baseline == "UNKNOWN" or (baseline == "REFERENCE_CONDITION_STRENGTH" and conditioned):
        blockers.append("QUALIFICATION_TEST_BASELINE_UNRESOLVED")
    condition_fields = {
        "CM": ("moisture",),
        "CT": ("sustained_f", "maximum_f"),
        "CCH": (
            "chemical",
            "chemical_substance",
            "chemical_concentration",
            "chemical_contact_form",
            "chemical_duration",
        ),
    }
    tested_env = record["environmental_scope"]["conditions"]
    project_env = scope["environmental_scope"]["conditions"]
    with localcontext() as ctx:
        ctx.prec = 80
        nominal = ro
        for name, value in (("CM", strength.cm), ("CT", strength.ct), ("CCH", strength.cch)):
            included = baseline == "ALREADY_CONDITIONED_STRENGTH" and name in conditioned
            if included and any(
                tested_env.get(field) != project_env.get(field) for field in condition_fields[name]
            ):
                blockers.append("ALREADY_CONDITIONED_BASELINE_DOES_NOT_MATCH_PROJECT:" + name)
            applied = Decimal(1) if included else value
            trace.append(
                {
                    "factor": name,
                    "MAT1_candidate": None if value is None else str(value),
                    "applied": None if applied is None else str(applied),
                    "state": "ALREADY_IN_TEST_BASELINE" if included else "APPLIED_ONCE_FROM_MAT1",
                    "MAT1_record": strength.record_id,
                    "MAT1_revision": strength.record_revision,
                    "MAT1_digest": strength.content_digest,
                    "baseline_approval": protocol["baseline_approval_document_id"],
                }
            )
            if applied is None:
                blockers.append("MAT1_FACTOR_SOURCE_REQUIRED:" + name)
            else:
                nominal *= applied
        trace.extend(
            (
                {
                    "factor": "lambda",
                    "applied": str(strength.lambda_factor),
                    "source": "Existing current MAT1 project/load classification, ASCE Table 2-1",
                },
                {"factor": "Rn", "value": str(nominal), "unit": "N"},
                {"factor": "phi_p", "applied": str(phi), "source": "Section 2.3.2 Eq. 2-3"},
            )
        )
        design = strength.lambda_factor * phi * nominal
    return (None if blockers else design), trace, tuple(dict.fromkeys(blockers))


def compare_strength(
    design: Decimal,
    required: Decimal,
    context: QualificationDesignContext | None,
    gravity_protocol: bool,
) -> dict[str, Any]:
    gravity = "UNAVAILABLE_D_OR_L_OR_GRAVITY_PROTOCOL"
    gravity_required = None
    if (
        context is not None
        and context.loading_type == "GRAVITY_D_L"
        and gravity_protocol
        and context.dead_load is not None
        and context.live_load is not None
    ):
        dead = PhysicalQuantity.of(context.dead_load.value, context.dead_load.unit)
        live = PhysicalQuantity.of(context.live_load.value, context.live_load.unit)
        if (
            dead.dimension is Dimension.FORCE
            and live.dimension is Dimension.FORCE
            and dead.magnitude >= 0
            and live.magnitude >= 0
        ):
            with localcontext() as ctx:
                ctx.prec = 80
                gravity_required = (
                    Decimal("1.2") * dead.canonical_magnitude
                    + Decimal("1.6") * live.canonical_magnitude
                )
            gravity = "PASS" if design > gravity_required else "NOT_PASS"
    with localcontext() as ctx:
        ctx.prec = 80
        utilization = required / design
    return {
        "capacity_state": "CAPACITY_PASS" if required <= design else "CAPACITY_FAIL",
        "utilization": str(utilization),
        "gravity_eq_2_2_state": gravity,
        "gravity_required_strength": None if gravity_required is None else str(gravity_required),
    }


def evaluate_record(
    record: ImmutableQualificationRecord,
    scope: dict[str, Any],
    required: Decimal | None,
    ledgers: list[PropertyLedger],
    context: QualificationDesignContext | None,
    *,
    qa_preview: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    data = record.data
    statistics = recompute_statistics(data["specimens"], data["statistical_protocol"])
    mismatches, comparisons = match_scope(data, scope)
    covered, coverage_blockers = response_coverage(data)
    reasons = [*mismatches, *coverage_blockers]
    synthetic = data["synthetic"] or data["evidence_origin"] == "SYNTHETIC_QA"
    state_available = (
        data["status"] == "AVAILABLE_FOR_MATCH"
        and not data["withdrawn"]
        and data["activation_permitted"]
        and not synthetic
    )
    if not state_available and not (qa_preview and synthetic and not data["activation_permitted"]):
        reasons.append("APPROVED_AVAILABLE_RECORD_REQUIRED")
    if statistics.blockers:
        reasons.append("STATISTICS INVALID")
    design = None
    factors: list[dict[str, Any]] = []
    if statistics.ro_n is not None and statistics.phi_p is not None:
        design, factors, factor_blockers = qualification_capacity(
            data, scope, ledgers, statistics.ro_n, statistics.phi_p
        )
        reasons.extend(factor_blockers)
    if required is None or required < 0:
        reasons.append("QUALIFICATION_LOAD_SCOPE_UNRESOLVED")
    public: dict[str, Any] = {
        "qualification_required": True,
        "available_record_ids": [],
        "selected_record_id": data["qualification_record_id"],
        "record_revision": data["revision"],
        "record_digest": record.digest,
        "record_state": data["status"],
        "statistics_state": "INVALID" if statistics.blockers else "VALID",
        "scope_match_state": "MISMATCH" if mismatches else "MATCHED",
        "coverage_state": "QUALIFICATION_COVERAGE_MISSING"
        if coverage_blockers
        else "COVERED_BY_QUALIFICATION",
        "capacity_state": "UNEVALUATED",
        "Rd_q": None,
        "Ru": None if required is None else {"value": str(required), "unit": "N"},
        "utilization": None,
        "gravity_eq_2_2_state": "UNAVAILABLE",
        "mismatch_reasons": list(dict.fromkeys(reasons)),
        "covered_response_ids": list(covered),
        "statistics": statistics.trace(),
        "laboratory": data["laboratory"]["legal_identity"],
        "rdp_approval": data["engineer_approval"]["engineer_identity"],
        "factor_trace": factors,
        "synthetic": synthetic,
        "activation_permitted": False,
        "final_status_integration_pending": True,
        "ordinary_pass_allowed": False,
    }
    if not reasons and design is not None and required is not None:
        public["Rd_q"] = {"value": str(design), "unit": "N"}
        public.update(
            compare_strength(
                design, required, context, data["statistical_protocol"]["gravity_protocol_approved"]
            )
        )
    audit = {
        "record": data,
        "statistics": statistics.trace(),
        "lab_reported_statistics": data["statistical_protocol"],
        "scope_comparison": comparisons,
        "factor_trace": factors,
        "covered_response_ids": list(covered),
        "response_coverage": {
            identifier: "COVERED_BY_QUALIFICATION"
            if identifier in covered
            else "QUALIFICATION_COVERAGE_MISSING"
            for identifier in COVERED_RESPONSES
        },
        "mismatch_reasons": public["mismatch_reasons"],
        "design_scope": scope,
        "design_snapshot_digest": content_digest(scope),
        "evaluation": public.copy(),
    }
    public["evaluation_digest"] = content_digest(audit)
    return public, audit


_AUDITS: OrderedDict[str, dict[str, Any]] = OrderedDict()
_AUDIT_LOCK = RLock()


def remember_audit(public: dict[str, Any], audit: dict[str, Any]) -> None:
    with _AUDIT_LOCK:
        _AUDITS[str(public["evaluation_digest"])] = audit
        while len(_AUDITS) > 64:
            _AUDITS.popitem(last=False)


def qualification_snapshot_provenance(result: dict[str, Any]) -> dict[str, Any]:
    evaluation = result.get("qualification_evaluation")
    if not isinstance(evaluation, dict):
        return {}
    with _AUDIT_LOCK:
        audit = _AUDITS.get(str(evaluation.get("evaluation_digest")))
        if audit is None:
            raise SnapshotError("Qualification audit snapshot is unavailable; rerun Design Check")
        return {"direct_qualification_audit": audit}


def qualification_snapshot_current(result: dict[str, Any]) -> bool:
    evaluation = result.get("qualification_evaluation")
    if not isinstance(evaluation, dict) or evaluation.get("record_digest") is None:
        return True
    records, _issues = production_provider().read()
    return any(
        record.digest == evaluation["record_digest"]
        and record.data["qualification_record_id"] == evaluation["selected_record_id"]
        and record.data["revision"] == evaluation["record_revision"]
        for record in records
    )


def qualification_catalog() -> dict[str, Any]:
    records, issues = production_provider().read()
    return {
        "contract": "DIRECT-QUALIFICATION-F8",
        "available_record_ids": [record.data["qualification_record_id"] for record in records],
        "records": [
            {
                "record_id": record.data["qualification_record_id"],
                "revision": record.data["revision"],
                "digest": record.digest,
                "laboratory": record.data["laboratory"]["legal_identity"],
                "rdp": record.data["engineer_approval"]["engineer_identity"],
            }
            for record in records
        ],
        "provider_state": "RECORD_VALIDATION_BLOCKERS" if issues else "READY",
        "next_step": (
            "Select an approved qualification record installed by the engineering administrator."
        ),
        "final_status_integration_pending": True,
    }


def attach_qualification(
    result: dict[str, Any],
    legacy: dict[str, Any],
    context: QualificationDesignContext | None,
    selected_id: str | None,
    conditions: dict[str, Any],
    ledgers: list[PropertyLedger],
) -> dict[str, Any]:
    if legacy.get("direct_finalization_contract_version") != "SHEAR01-DIRECT-F1":
        if context is not None or selected_id is not None:
            raise ValueError("QUALIFICATION_SCOPE_IS_DIRECT_ANGLE_TO_W_ONLY")
        return result
    provider = production_provider()
    available, provider_issues = provider.read()
    scope, required = authenticated_scope(
        legacy,
        {**result["material_sources"], "qualification_conditions": conditions},
        result["fastener_source"],
        context,
        result["native_design"]["preview"],
    )
    selected = next(
        (record for record in available if record.data["qualification_record_id"] == selected_id),
        None,
    )
    if selected is None:
        public: dict[str, Any] = {
            "qualification_required": True,
            "available_record_ids": [
                record.data["qualification_record_id"] for record in available
            ],
            "selected_record_id": selected_id,
            "record_revision": None,
            "record_digest": None,
            "record_state": "NO_APPROVED_RECORD"
            if selected_id is None
            else "UNAVAILABLE_OR_INVALID",
            "statistics_state": "UNEVALUATED",
            "scope_match_state": "UNEVALUATED",
            "coverage_state": "QUALIFICATION_COVERAGE_MISSING",
            "capacity_state": "UNEVALUATED",
            "Rd_q": None,
            "Ru": None
            if required is None
            else {"value": canonical_decimal_string(required), "unit": "N"},
            "utilization": None,
            "gravity_eq_2_2_state": "UNAVAILABLE",
            "mismatch_reasons": [
                "No approved Section 2.3.2 qualification record matches this Direct connection."
            ],
            "covered_response_ids": [],
            "synthetic": False,
            "activation_permitted": False,
            "final_status_integration_pending": True,
            "ordinary_pass_allowed": False,
        }
        audit = {
            "design_scope": scope,
            "design_snapshot_digest": content_digest(scope),
            "provider_issues": list(provider_issues),
            "record": None,
            "evaluation": public.copy(),
        }
        public["evaluation_digest"] = content_digest(audit)
    else:
        public, audit = evaluate_record(selected, scope, required, ledgers, context)
        public["available_record_ids"] = [
            record.data["qualification_record_id"] for record in available
        ]
    audit["independent_analytical_fail_ids"] = (
        result["native_design"]
        .get("automatic_group_mode_integration", {})
        .get("failed_check_ids", [])
        if result["native_design"].get("automatic_group_mode_integration") is not None
        else []
    )
    audit["evaluation"] = {
        key: value for key, value in public.items() if key != "evaluation_digest"
    }
    public["evaluation_digest"] = content_digest(audit)
    remember_audit(public, audit)
    return {**result, "qualification_evaluation": public}


__all__ = (
    "QualificationDesignContext",
    "attach_qualification",
    "authenticated_scope",
    "compare_strength",
    "evaluate_record",
    "normalized",
    "qualification_capacity",
    "qualification_snapshot_provenance",
)
