"""Actual R3 same-geometry checks and independent action/material authority."""

import asyncio
import io
import json
import math
from copy import deepcopy
from decimal import Decimal
from threading import Event
from typing import Any, cast

import pytest
from pypdf import PdfReader
from tests.api.test_hybrid_workflow import BASE, LiveTransport
from tests.hybrid_same_connection_fixtures import same_connection
from tests.hybrid_workflow_fixtures import live_native, live_source


def assessed(body: dict[str, Any]) -> dict[str, Any]:
    with LiveTransport() as c:
        response = c.post(BASE + "/assess", json=body)
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json()["record"])


def basis_rows(record: dict[str, Any], basis: str) -> list[dict[str, Any]]:
    return [x for x in record["assessment"]["comparisons"] if x["basis"] == basis]


def test_same_pair_executes_six_fresh_asce_and_seven_unchanged_rhm() -> None:
    r = assessed(same_connection())
    assert len(basis_rows(r, "LRFD")) == 6
    assert basis_rows(r, "ASD") == basis_rows(assessed(live_source()), "ASD")
    assert r["inputs"]["native_request"] is None
    actual = r["same_connection_lrfd"]
    assert actual["physical_centers_in"] == [["B1", ["0", "1"]], ["B2", ["0", "-1"]]]
    case = actual["cases"][0]
    assert case["geometry_digest"] == actual["geometry_digest"]
    proof = json.loads(case["demand"])["solution"]["proof"]
    assert all(x["recovered"] == x["target"] for x in proof.values())
    # Independent binary-math witness, not another call to the resistance adapter.
    angle = math.radians(30.9)
    fx, fy = (
        0.15 * math.cos(angle) - 0.02 * math.sin(angle),
        -0.15 * math.sin(angle) - 0.02 * math.cos(angle),
    )
    per_bolt = math.hypot(fx, fy) / 2
    pitch = 2 * abs(fy) / math.hypot(fx, fy)
    assert float(case["row_pitch_in"]) == pytest.approx(pitch)
    for check in case["checks"]:
        assert float(check["demand_kip"]) == pytest.approx(per_bolt)
        if check["mechanism"].startswith("PIN_BEARING"):
            factors = check["equation_trace"]["factor_trace"]
            assert Decimal(factors["c_lap"]) == Decimal(".6")
            assert Decimal(factors["c_delta"]) == Decimal(case["c_delta"])
            assert check["selected_property"] == "FBR_T"
    assert r["assessment"]["evaluated_outcome"] == "PASS"
    assert r["assessment"]["tone"] == "green"
    assert r["assessment"]["coverage_state"] == "PARTIAL"
    assert not r["assessment"]["analytical_complete"]
    assert not r["assessment"]["public_activation"]
    assert "NOT_ESTABLISHED" in r["qualification"]
    assert len(r["physical_mechanisms"]) == 9
    assert r["detailing_failures"]  # Numeric PASS is not acceptable installation.
    assert all(
        Decimal(x["actual_distance"]) < Decimal(x["required_distance"])
        for x in r["detailing_failures"]
    )


@pytest.mark.parametrize("basis", ["lrfd", "asd"])
def test_load_changes_never_create_or_rescale_the_other_basis(basis: str) -> None:
    original = same_connection()
    before = assessed(original)
    changed = deepcopy(original)
    changed[basis + "_cases"][0]["components"][0]["value"] = "20"
    after = assessed(changed)
    unchanged = "ASD" if basis == "lrfd" else "LRFD"
    assert basis_rows(before, unchanged) == basis_rows(after, unchanged)
    assert before["fingerprint"] != after["fingerprint"]
    assert after["assessment"]["evaluated_outcome"] == "FAIL"
    assert after["assessment"]["tone"] == "red"
    assert any(x["outcome"] == "FAIL" for x in basis_rows(after, basis.upper()))


@pytest.mark.parametrize(("removed", "expected"), [("lrfd", (0, 7)), ("asd", (6, 0))])
def test_missing_independent_set_keeps_other_valid_calculations(
    removed: str, expected: tuple[int, int]
) -> None:
    body = same_connection()
    body[removed + "_cases"] = []
    r = assessed(body)
    assert (len(basis_rows(r, "LRFD")), len(basis_rows(r, "ASD"))) == expected
    assert not r["assessment"]["case_sets_complete"]
    assert r["assessment"]["evaluated_outcome"] == "PASS"


def test_incomplete_asce_material_context_keeps_current_rhm_reference_available() -> None:
    body = same_connection()
    del body["same_connection_lrfd"]
    result = assessed(body)
    assert not basis_rows(result, "LRFD")
    assert len(basis_rows(result, "ASD")) == 7
    assert result["assessment"]["evaluated_outcome"] == "PASS"
    assert result["assessment"]["tone"] == "green"
    assert result["inputs"]["geometry"] == body["geometry"]
    assert result["inputs"]["lrfd_cases"] == body["lrfd_cases"]
    assert any(
        "Complete current MAT1 materials/conditions" in reason for _, reason in result["withheld"]
    )


@pytest.mark.parametrize(
    "change",
    [
        "alignment",
        "hole",
        "thin",
        "diameter",
        "temperature",
        "source",
        "hardware",
        "threads",
        "missing",
        "frame",
        "outofplane",
        "referencez",
        "moment",
        "reference",
        "zero",
        "puremoment",
        "spacing",
    ],
)
def test_bounded_domains_are_independent_and_never_borrow_another_geometry(change: str) -> None:
    b = same_connection()
    case = b["lrfd_cases"][0]
    if change == "alignment":
        b["alignment"] = "BRACE"
    elif change == "hole":
        b["geometry"]["hole"]["value"] = ".6"
    elif change == "thin":
        b["geometry"]["brace_thickness"]["value"] = ".15"
    elif change == "diameter":
        b["geometry"]["diameter"]["value"] = ".25"
        b["geometry"]["hole"]["value"] = ".313"
    elif change == "temperature":
        conditions = b["same_connection_lrfd"]["assignments"]["default_conditions"]
        for key in ("design_temperature", "sustained_temperature", "maximum_temperature"):
            conditions[key]["value"] = "150"
    elif change == "source":
        b["source_profile"] = "UNMATCHED"
    elif change == "hardware":
        b["same_connection_lrfd"]["fastener"] = {
            "kind": "DEFAULT",
            "contract": "FASTENER-OR1-RC1",
            "revision": "ASTM-F593-17-G2-316-316L-SOURCE-PENDING-RC0",
        }
    elif change == "threads":
        b["same_connection_lrfd"]["fastener"]["shear_thread_status"] = "UNKNOWN"
    elif change == "missing":
        case["components"][0] = None
    elif change == "frame":
        case["frame"] = "GLOBAL"
    elif change == "outofplane":
        case["components"][2]["value"] = ".001"
    elif change == "referencez":
        case["reference"][2]["value"] = ".001"
    elif change == "moment":
        case["components"][5]["value"] = ".012"
    elif change == "reference":
        case["reference"][0]["value"] = ".1"
    elif change in ("zero", "puremoment"):
        for x in case["components"]:
            x["value"] = "0"
        if change == "puremoment":
            case["components"][5]["value"] = ".012"
    else:
        b["geometry"]["vertical_bolt_pitch"]["value"] = "3"
    r = assessed(b)
    expected = {
        "alignment": 0,
        "hole": 2,
        "thin": 4,
        "diameter": 0,
        "temperature": 2,
        "hardware": 4,
        "threads": 4,
        "missing": 0,
        "frame": 0,
        "outofplane": 0,
        "referencez": 0,
        "zero": 2,
        "puremoment": 2,
    }.get(change, 6)
    assert len(basis_rows(r, "LRFD")) == expected
    assert len(basis_rows(r, "ASD")) == (0 if change in ("alignment", "source") else 7)
    assert not r["assessment"]["analytical_complete"]
    if change in ("moment", "reference"):
        checks = r["same_connection_lrfd"]["cases"][0]["checks"]
        assert checks[0]["demand_kip"] != checks[3]["demand_kip"]
    assert all(x["mechanism"] != "INTERROW:layer-A:BOLT_LINE_1" for x in basis_rows(r, "LRFD"))


def test_units_and_signed_p_v_frame_preserve_every_comparison() -> None:
    b = same_connection()
    with LiveTransport() as c:
        first = c.post(BASE + "/assess", json=b).json()
        si = c.post(BASE + "/units", json={"inputs": b, "system": "mm"}).json()
        si["revision"] = 1
        second = c.post(BASE + "/assess", json=si).json()
        assert (
            second["record"]["assessment"]["comparisons"]
            == first["record"]["assessment"]["comparisons"]
        )
        si["revision"] = 2
        for key in ("lrfd_cases", "asd_cases"):
            si[key][0]["frame"] = "DIRECT_P_POSITIVE_N_CENTROID"
            si[key][0]["components"][1]["value"] = "-" + si[key][0]["components"][1]["value"]
        third = c.post(BASE + "/assess", json=si).json()
        assert (
            third["record"]["assessment"]["comparisons"]
            == second["record"]["assessment"]["comparisons"]
        )


def test_positive_n_reference_preserves_the_physical_wrench_and_legacy_contract() -> None:
    from frp_master_connection.api.hybrid_workflow import ASDCase
    from frp_master_connection.application.hyb1_contract import ActionBasis

    body = same_connection()
    body["lrfd_cases"][0]["reference"][1]["value"] = ".25"
    first = assessed(body)
    declared = body["lrfd_cases"][0]
    declared["frame"] = "DIRECT_P_POSITIVE_N_CENTROID"
    declared["components"][1]["value"] = "-.02"
    declared["reference"][1]["value"] = "-.25"
    # Historical DTO behavior is preserved outside the explicitly new LRFD seam.
    legacy = ASDCase.model_validate(declared).case(ActionBasis.LRFD)
    assert legacy.reference[1].magnitude == Decimal("-.25")
    second = assessed(body)
    assert basis_rows(first, "LRFD") == basis_rows(second, "LRFD")
    a = first["same_connection_lrfd"]["cases"][0]
    b = second["same_connection_lrfd"]["cases"][0]
    assert a["demand"] == b["demand"]
    assert a["checks"][0]["demand_kip"] != a["checks"][3]["demand_kip"]
    assert Decimal(b["raw_actions"]["reference"][1]["magnitude"]) == Decimal(".25")
    assert second["inputs"]["lrfd_cases"][0]["reference"][1]["value"] == "-.25"
    assert second["inputs"]["lrfd_cases"][0]["frame"] == "DIRECT_P_POSITIVE_N_CENTROID"


@pytest.mark.parametrize("field", ["owner", "conditions", "native", "clientresult"])
def test_rejects_incompatible_or_forged_material_geometry_contracts(field: str) -> None:
    b = same_connection()
    a = b["same_connection_lrfd"]["assignments"]
    if field == "owner":
        a.setdefault("material_overrides", {})["different-solid"] = a["default_material"]
    elif field == "conditions":
        a.setdefault("condition_overrides", {})["member-a"] = {
            **a["default_conditions"],
            "chemical": "SPECIFIED",
            "chemical_strength_factor": ".8",
        }
    elif field == "native":
        b.update(
            connection="CURRENT_NATIVE",
            native_request=live_native()["native_request"],
            geometry=None,
        )
    else:
        b["same_connection_lrfd"]["result"] = {"outcome": "PASS"}
    with LiveTransport() as c:
        response = c.post(BASE + "/assess", json=b)
    assert response.status_code == 422


def test_reports_show_actual_calculations_and_reject_old_revision() -> None:
    b = same_connection()
    b["bearing_face"] = "DECLARED_STRAIGHT_FREE_EDGE"
    b["washer_od"] = {"value": "1", "unit": "in"}
    with LiveTransport() as c:
        response = c.post(BASE + "/assess", json=b).json()
        handle = response["report_handle"]
        r = response["record"]
        assert "Insufficient washer edge clearance" in r["assessment"]["fit"]["action"]
        assert r["assessment"]["fit"]["state"] == "NOT_FIT"
        pdf = c.get(BASE + "/reports/" + handle)
        assert pdf.status_code == 200
        text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
        for phrase in (
            "Same physical connection",
            "entered-LRFD-A",
            "source-ASD",
            "0.185",
            "0.101",
            "Insufficient washer edge clearance",
            "Section 2.3.2",
            "first-row",
        ):
            assert phrase in text
        assert c.get(BASE + "/records/" + handle).json() == r
        audit = c.get(BASE + "/reports/" + handle + "?technical=true")
        assert audit.status_code == 200
        audit_text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(audit.content)).pages)
        assert "Same-connection ASCE exact technical audit" in audit_text
        assert "material_context_digest" not in text  # Full hashes stay in exact JSON/audit data.
        assert "equation_trace" in audit_text
        b["revision"] = 1
        b["geometry"]["vertical_bolt_pitch"]["value"] = "3"
        assert c.post(BASE + "/preview", json=b).status_code == 200
        assert c.get(BASE + "/reports/" + handle).status_code == 409


def test_geometry_mismatch_fails_before_an_engine_can_execute() -> None:
    from frp_master_connection.api.hybrid_workflow import HybridInputs
    from frp_master_connection.application.hyb1_contract import (
        Alignment,
        CaseManifest,
        PairedActions,
        PhysicalIdentity,
    )
    from frp_master_connection.application.hybrid_same_connection import calculate_same_connection

    dto = HybridInputs.model_validate(same_connection())
    assert dto.geometry is not None
    assert dto.same_connection_lrfd is not None
    geometry = dto.geometry.geometry()
    physical = PhysicalIdentity(
        "test", "DIRECT_USER_HYBRID", "wrong-geometry", "source", "actions", Alignment.SUPPORT
    )
    actions = PairedActions(physical, (), (), CaseManifest((), (), False, False, "independent"))
    with pytest.raises(ValueError, match="geometry identity mismatch"):
        calculate_same_connection(actions, geometry, dto.same_connection_lrfd.resolve(geometry))


@pytest.mark.parametrize("washer", [".75", "1"])
def test_washer_requirements_do_not_disable_independent_calculations(washer: str) -> None:
    b = same_connection()
    b["bearing_face"] = "DECLARED_STRAIGHT_FREE_EDGE"
    b["washer_od"] = {"value": washer, "unit": "in"}
    r = assessed(b)
    assert len(r["assessment"]["comparisons"]) == 13
    assert r["assessment"]["evaluated_outcome"] == "PASS"
    failures = [x["check_kind"] for x in r["detailing_failures"]]
    assert ("WASHER_MINIMUM_OUTSIDE_DIAMETER" in failures) == (washer == ".75")
    assert "BRACE_END_DISTANCE_MINIMUM_LOWER_BOUND" in failures


def test_chemical_strength_factor_affects_only_asce_strengths_not_rhm_or_modulus() -> None:
    b = same_connection()
    before = assessed(b)
    b["same_connection_lrfd"]["assignments"]["default_conditions"].update(
        chemical="SPECIFIED", chemical_strength_factor=".8"
    )
    after = assessed(b)
    assert basis_rows(before, "ASD") == basis_rows(after, "ASD")
    assert (
        after["same_connection_lrfd"]["material_context_digest"]
        != before["same_connection_lrfd"]["material_context_digest"]
    )
    ledger = after["same_connection_lrfd"]["materials"]["resolved_materials"][0]["ledgers"]
    strengths = [x for x in ledger if x["property_id"].startswith("bearing_strength")]
    assert all(Decimal(x["cch"]) == Decimal(".8") for x in strengths)
    moduli = [x for x in ledger if "modulus" in x["property_id"]]
    assert all(x["adjusted_candidate"] is None for x in moduli)
    assert any("CHEMICAL_MODULUS_APPLICABILITY_UNRESOLVED" in x["issues"] for x in moduli)
    assert len(basis_rows(after, "LRFD")) == 6  # Bearing/bolt checks do not consume modulus.


def test_late_same_connection_work_cannot_seal_after_edit(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    import frp_master_connection.api.hybrid_workflow as bridge
    from frp_master_connection.api.hybrid_app import create_hybrid_app
    from frp_master_connection.application.hyb1_contract import PairedActions
    from frp_master_connection.application.hybrid_same_connection import (
        SameConnectionMaterials,
        SameConnectionResult,
        calculate_same_connection,
    )
    from frp_master_connection.calculation.rhm_direct_r3 import R3Geometry

    started, release = Event(), Event()

    def delayed(
        a: PairedActions, g: R3Geometry, m: SameConnectionMaterials
    ) -> SameConnectionResult:
        started.set()
        assert release.wait(10)
        return calculate_same_connection(a, g, m)

    monkeypatch.setattr(bridge, "calculate_same_connection", delayed)
    b = same_connection()

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_hybrid_app()), base_url="http://testserver"
        ) as c:
            task = asyncio.create_task(c.post(BASE + "/assess", json=b))
            try:
                assert await asyncio.to_thread(started.wait, 10)
                b["revision"] += 1
                b["geometry"]["vertical_bolt_pitch"]["value"] = "3"
                assert (await c.post(BASE + "/preview", json=b)).status_code == 200
            finally:
                release.set()
            old = await task
            assert old.status_code == 409
            assert "report_handle" not in old.json()

    asyncio.run(run())
