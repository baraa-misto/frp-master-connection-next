"""Live current-input user workflow acceptance; no fixture-selection endpoint."""

import asyncio
from decimal import Decimal
from typing import Self

import httpx
import pytest
from tests.hybrid_workflow_fixtures import live_native, live_source

from frp_master_connection.api.hybrid_app import create_hybrid_app

BASE = "/api/v1/direct-hybrid"


class LiveTransport:
    def __init__(self) -> None:
        self.app = create_hybrid_app()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def post(self, path: str, *, json: object) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self.app), base_url="http://testserver"
            ) as client:
                return await client.post(path, json=json)

        return asyncio.run(send())

    def get(self, path: str) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self.app), base_url="http://testserver"
            ) as client:
                return await client.get(path)

        return asyncio.run(send())


def test_p01_03_04_05_live_source_current_values() -> None:
    with LiveTransport() as client:
        body = live_source()
        preview = client.post(BASE + "/preview", json=body)
        assert preview.status_code == 200, preview.text
        assert len(preview.json()["scene"]["cylinders"]) == 4
        result = client.post(BASE + "/assess", json=body)
        assert result.status_code == 200, result.text
        data = result.json()
        a = data["record"]["assessment"]
        assert a["evaluated_outcome"] == "PASS"
        assert a["coverage_state"] == "NOT_ESTABLISHED"
        assert data["record"]["requested_computation"]["rhm_comparisons_executed"] == 7
        assert Decimal(a["governing_asd"]["ratio"]) == Decimal(
            "0.100892136239327322431541891418946393327249809999530689928570"
        )
        expected_source = {
            "DIRECT_SHARED_BOLTS": (
                "0.0184795429992093549893761220646632354580905561532877782871121"
            ),
            "DIRECT_BRACE_BEARING": (
                "0.0407966166858900422914263744713571703191080353710111495578623"
            ),
            "DIRECT_BRACE_LOCAL": "0.100892136239327322431541891418946393327249809999530689928570",
            "DIRECT_BRACE_GLOBAL": (
                "0.0234936537320611359430299734327552571148644967226116148287834"
            ),
            "DIRECT_COLUMN_BEARING": (
                "0.0731677559912854030501089324618736383442265795206971677559913"
            ),
            "DIRECT_COLUMN_LOCAL": (
                "0.0563657758337437219656366206338664915119745428377541967970386"
            ),
            "DIRECT_COLUMN_GLOBAL": (
                "0.0541613236340862838180997223460814434573363221728272650945376"
            ),
        }
        assert {r["mechanism"]: r["ratio"] for r in a["comparisons"]} == expected_source
        assert not a["public_activation"]
        assert not a["analytical_complete"]
        assert data["workflow_available"]
        assert not data["structural_method_activation"]
        body["revision"] += 1
        body["asd_cases"][0]["case_id"] = "user-varied"
        body["asd_cases"][0]["components"][0]["value"] = ".18310"
        body["geometry"]["xb"]["value"] = ".5"
        changed = client.post(BASE + "/assess", json=body)
        assert changed.status_code == 200, changed.text
        assert changed.json()["fingerprint"] != data["fingerprint"]
        assert (
            changed.json()["record"]["assessment"]["source_domain"]
            == "PARAMETRIC_ARITHMETIC_OUTSIDE_SOURCE_DOMAIN"
        )
        assert (
            changed.json()["record"]["assessment"]["governing_asd"]["ratio"]
            != a["governing_asd"]["ratio"]
        )


def test_p02_07_native_eight_checks_unchanged() -> None:
    with LiveTransport() as client:
        body = live_native()
        original = client.post("/api/v1/direct-two-bolt/design-check", json=body["native_request"])
        assert original.status_code == 200, original.text
        result = client.post(BASE + "/assess", json=body)
        assert result.status_code == 200, result.text
        record = result.json()["record"]
        assert record["native_result"] == original.json()["result"]
        assert record["requested_computation"]["native_checks_executed"] == 8
        assert record["assessment"]["native_status"] == "YELLOW"
        assert record["assessment"]["evaluated_outcome"] == "PASS"
        assert record["assessment"]["coverage_state"] == "PARTIAL"


def test_p09_13_units_and_signed_frame_preserve_current_values() -> None:
    with LiveTransport() as client:
        body = live_source()
        original = client.post(BASE + "/assess", json=body).json()["record"]["assessment"]
        body["washer_od"] = {"value": "1", "unit": "in"}
        converted = client.post(BASE + "/units", json={"inputs": body, "system": "mm"})
        assert converted.status_code == 200
        si = converted.json()
        si["revision"] = 1
        assert si["geometry"]["vertical_bolt_pitch"]["value"] == "50.8"
        assert Decimal(si["geometry"]["xb"]["value"]) == Decimal("11.1125")
        current = client.post(BASE + "/assess", json=si)
        assert current.status_code == 200, current.text
        assert current.json()["record"]["assessment"]["comparisons"] == original["comparisons"]
        si["revision"] = 2
        si["asd_cases"][0]["frame"] = "DIRECT_P_POSITIVE_N_CENTROID"
        si["asd_cases"][0]["components"][1]["value"] = (
            "-" + si["asd_cases"][0]["components"][1]["value"]
        )
        positive_n = client.post(BASE + "/assess", json=si)
        assert positive_n.status_code == 200
        assert positive_n.json()["record"]["assessment"]["comparisons"] == original["comparisons"]


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "moment",
        "reverse",
        "unknown",
        "out-of-plane",
        "reference",
        "global",
        "profile",
        "brace",
        "overlap",
    ],
)
def test_p08_10_11_18_21_29_affected_source_withheld(change: str) -> None:
    with LiveTransport() as client:
        body = live_source()
        if change == "missing":
            body["asd_cases"] = []
        elif change == "moment":
            body["asd_cases"][0]["components"][5]["value"] = "1"
        elif change == "reverse":
            body["asd_cases"][0]["components"][0]["value"] = "-.09155"
        elif change == "unknown":
            body["asd_cases"][0]["components"][3] = None
        elif change == "out-of-plane":
            body["asd_cases"][0]["components"][2]["value"] = ".1"
        elif change == "reference":
            body["asd_cases"][0]["reference"][0]["value"] = "1"
        elif change == "global":
            body["asd_cases"][0]["frame"] = "GLOBAL"
        elif change == "profile":
            body["source_profile"] = "UNMATCHED"
        elif change == "brace":
            body["alignment"] = "BRACE"
        else:
            body["geometry"]["hole"]["value"] = "3"
        response = client.post(BASE + "/assess", json=body)
        assert response.status_code == 200, response.text
        record = response.json()["record"]
        assert record["assessment"]["evaluated_outcome"] == "NOT_EVALUATED"
        assert record["inputs"] == body
        assert not record["assessment"]["analytical_complete"]
        assert record["qualification"] == "NOT_ESTABLISHED_SECTION_2_3_2"
        if change in ("brace", "overlap"):
            assert record["assessment"]["fit"]["state"] == "NOT_FIT"
            assert "Bolt-hole containment/placement fails" in record["assessment"]["fit"]["action"]


@pytest.mark.parametrize(
    ("edge", "od", "face", "state", "overhang"),
    [
        (".4375", "1", "DECLARED_STRAIGHT_FREE_EDGE", "NOT_FIT", ".0625"),
        (".5", "1", "DECLARED_STRAIGHT_FREE_EDGE", "PHYSICAL_FIT_UNVERIFIED", "0"),
        (".6", "1", "DECLARED_STRAIGHT_FREE_EDGE", "PHYSICAL_FIT_UNVERIFIED", "0"),
        (".4375", "1", "UNKNOWN", "PHYSICAL_FIT_UNVERIFIED", None),
        (".4375", None, "UNKNOWN", "PHYSICAL_FIT_UNVERIFIED", None),
    ],
)
def test_p14_15_16_declared_washer_does_not_disable_calculation(
    edge: str, od: str | None, face: str, state: str, overhang: str | None
) -> None:
    with LiveTransport() as client:
        body = live_source()
        body["geometry"]["xb"]["value"] = edge
        body["washer_od"] = None if od is None else {"value": od, "unit": "in"}
        body["bearing_face"] = face
        response = client.post(BASE + "/assess", json=body)
        assert response.status_code == 200, response.text
        a = response.json()["record"]["assessment"]
        assert a["evaluated_outcome"] == "PASS"
        assert a["fit"]["state"] == state
        assert a["fit"]["actual_overhang_in"] == (
            None if overhang is None else str(Decimal(overhang))
        )
        assert response.json()["record"]["data_provenance"].startswith("USER_DECLARED")


def test_p20_real_overload_remains_scoped_fail() -> None:
    with LiveTransport() as client:
        body = live_source()
        body["asd_cases"][0]["components"][0]["value"] = "60"
        result = client.post(BASE + "/assess", json=body)
        assert result.status_code == 200
        a = result.json()["record"]["assessment"]
        assert a["evaluated_outcome"] == "FAIL"
        assert a["tone"] == "red"
        assert Decimal(a["governing_asd"]["ratio"]) > 1


@pytest.mark.parametrize(
    "change",
    [
        "result",
        "approval",
        "domain",
        "graft",
        "missing-geometry",
        "nonfinite",
        "bad-angle",
        "negative-washer",
        "negative-edge",
        "native-alignment",
        "native-lrfd-graft",
    ],
)
def test_p06_18_24_strict_inputs_reject_injection_and_inconsistent_geometry(change: str) -> None:
    with LiveTransport() as client:
        body = live_source()
        if change == "result":
            body["results"] = [{"capacity": "999999", "status": "PASS"}]
        elif change == "approval":
            body["approved"] = True
        elif change == "domain":
            body["asd_cases"][0]["case_id"] = "HYB2_D2_TEST_DOMAIN"
            assert client.post(BASE + "/assess", json=body).status_code == 422
            body["asd_cases"][0]["case_id"] = "source-ASD"
            body["workspace_id"] = "HYB2_D2_SYNTHETIC_TEST_DOMAIN"
        elif change == "graft":
            body["native_request"] = live_native()["native_request"]
        elif change == "missing-geometry":
            body["geometry"] = None
        elif change == "nonfinite":
            body["geometry"]["hole"]["value"] = "NaN"
        elif change == "bad-angle":
            body["geometry"]["phi"] = "Infinity"
        elif change == "negative-washer":
            body["washer_od"] = {"value": "0", "unit": "in"}
        elif change == "negative-edge":
            body["native_edge_distance"] = {"value": "-1", "unit": "in"}
        elif change == "native-alignment":
            body = live_native()
            body["alignment"] = "SUPPORT"
        else:
            body = live_native()
            body["lrfd_cases"] = live_source()["asd_cases"]
        assert client.post(BASE + "/assess", json=body).status_code == 422


def test_p25_27_positive_pdf_and_stale_handle_without_recalculation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import io

    from pypdf import PdfReader

    import frp_master_connection.api.hybrid_workflow as module

    with LiveTransport() as client:
        body = live_source()
        response = client.post(BASE + "/assess", json=body)
        assert response.status_code == 200
        handle = response.json()["report_handle"]

        def forbidden(*args: object, **kwargs: object) -> None:
            raise AssertionError("Export must not execute engineering")

        monkeypatch.setattr(module, "assess_d2", forbidden)
        pdf = client.get(BASE + "/reports/" + handle)
        assert pdf.status_code == 200
        text = " ".join(
            " ".join(
                p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf.content)).pages
            ).split()
        )
        assert "Hybrid Connection Calculation Report" in text
        assert "0.101" in text
        assert "Actual vertical bolt center spacing" in text
        assert "Brace edge to bolt-column centerline (Xb)" in text
        assert "Current calculation trace:" not in text
        assert "Not established; Section 2.3.2 remains open" in text
        assert "field-use history, not physical load-test evidence" in text
        assert client.get(BASE + "/reports/" + handle + "?technical=true").status_code == 200
        assert (
            client.post(
                BASE + "/invalidate", json={"workspace_id": body["workspace_id"], "revision": 1}
            ).status_code
            == 200
        )
        assert client.get(BASE + "/reports/" + handle).status_code == 409
        assert client.post(BASE + "/preview", json=body).status_code == 409
