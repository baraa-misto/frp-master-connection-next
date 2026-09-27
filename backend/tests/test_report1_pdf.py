"""REPORT1 security and native-content tests using actual backend PDF bytes."""

from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass, replace
from typing import Any, cast

import httpx
import pytest
from pypdf import PdfReader

from frp_master_connection.api.app import create_app
from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.ssmc import illustrative_ssmc
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.reporting.reader_data import humanize
from frp_master_connection.reporting.snapshot import SnapshotError, SnapshotSigner
from frp_master_connection.security import TrustedIdentity
from tests.api.test_connector_materials import native_payload
from tests.api_fixtures import build_api_payload, build_j1_preview_api_payload


@dataclass(slots=True)
class _Resolver:
    account_id: str
    production_capable: bool = True

    async def resolve(self) -> TrustedIdentity:
        return TrustedIdentity(self.account_id, None, frozenset({"tester"}), "test")


def _run_report(
    *, paper: str = "LETTER", tamper: bool = False
) -> tuple[dict[str, object], httpx.Response]:
    async def run() -> tuple[dict[str, object], httpx.Response]:
        app = create_app(
            settings=AppSettings(environment=ApplicationEnvironment.TEST),
            identity_resolver=_Resolver("report-test-account"),
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            design = await client.post(
                "/api/v1/calculations/single-bolt/evaluate?report_snapshot=1",
                json=build_api_payload("J1-T"),
            )
            assert design.status_code == 200
            body: dict[str, object] = design.json()
            token = str(body["report_snapshot"])
            if tamper:
                token = token[:-8] + ("A" if token[-8] != "A" else "B") + token[-7:]
            response = await client.post(
                "/api/v1/reports/export",
                json={
                    "report_snapshot": token,
                    "paper": paper,
                    "connection_id": "J1-T",
                },
            )
            return body, response

    return asyncio.run(run())


@pytest.mark.parametrize(("paper", "width", "height"), [("LETTER", 612, 792), ("A4", 595, 842)])
def test_actual_report_contains_native_results_and_canonical_figure(
    paper: str, width: int, height: int
) -> None:
    body, response = _run_report(paper=paper)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "no-store, private"
    assert response.content.startswith(b"%PDF-")
    pdf = PdfReader(io.BytesIO(response.content))
    assert len(pdf.pages) > 1
    assert pdf.root_object.get("/Lang") == "en-US"
    assert pdf.outline
    assert any(
        annotation.get_object().get("/Subtype") == "/Link"
        and annotation.get_object().get("/Dest") is not None
        for page in pdf.pages
        for annotation in page.get("/Annots", [])
    )
    assert round(float(pdf.pages[0].mediabox.width)) == width
    assert round(float(pdf.pages[0].mediabox.height)) == height
    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    assert "Isometric - not to scale" in text
    assert "bolt-1" in text
    assert "FRP pin bearing" in text
    assert "R_n = t(0.375 in) x d(0.5 in)" in text.replace("\n", "")
    assert "Native cleavage branch A substitution" in text
    assert str(body["calculation_fingerprint"]) in text.replace("\n", "")
    assert "0.345679012345679" in text.replace("\n", "")


def test_ordinary_route_response_remains_deterministic_without_report_opt_in() -> None:
    async def run() -> tuple[bytes, bytes]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            payload = build_api_payload("J1-T")
            first = await client.post("/api/v1/calculations/single-bolt/evaluate", json=payload)
            second = await client.post("/api/v1/calculations/single-bolt/evaluate", json=payload)
            return first.content, second.content

    first, second = asyncio.run(run())
    assert first == second
    assert b"report_snapshot" not in first


def test_snapshot_middleware_rejects_oversize_and_passes_invalid_json_to_validation() -> None:
    async def run() -> list[httpx.Response]:
        app = create_app()
        bodies = (
            b'{"padding":"' + b"x" * 8_000_000 + b'"}',
            b"{",
            b"\xff",
            b"[]",
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return [
                await client.post(
                    "/api/v1/calculations/single-bolt/evaluate",
                    content=body,
                    headers={"Content-Type": "application/json"},
                )
                for body in bodies
            ]

    oversized, invalid_json, invalid_utf8, non_object = asyncio.run(run())
    assert oversized.status_code == 413
    assert oversized.json()["detail"] == "REPORT1 request size limit exceeded"
    for response in (invalid_json, invalid_utf8, non_object):
        assert response.status_code in {400, 422}
        assert "X-Report-Handle" not in response.headers


def test_snapshot_middleware_reports_signer_failure_without_replacing_native_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_issue(self: SnapshotSigner, **_: object) -> str:
        raise SnapshotError("forced snapshot failure")

    monkeypatch.setattr(SnapshotSigner, "issue", fail_issue)

    async def run() -> tuple[httpx.Response, httpx.Response]:
        app = create_app()
        payload = build_api_payload("J1-T")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            ordinary = await client.post("/api/v1/calculations/single-bolt/evaluate", json=payload)
            opted_in = await client.post(
                "/api/v1/calculations/single-bolt/evaluate?report_snapshot=1", json=payload
            )
            return ordinary, opted_in

    ordinary, opted_in = asyncio.run(run())
    assert ordinary.status_code == opted_in.status_code == 200
    assert ordinary.headers["X-Report-Error"] == "snapshot-unavailable"
    assert "X-Report-Handle" not in ordinary.headers
    assert opted_in.json()["report_snapshot_error"] == "forced snapshot failure"
    assert "X-Report-Handle" not in opted_in.headers
    signed = opted_in.json()
    del signed["report_snapshot_error"]
    assert signed == ordinary.json()


def test_signed_snapshot_opt_in_changes_no_native_calculation_field() -> None:
    payload = build_api_payload("J1-T")

    async def run() -> tuple[dict[str, Any], dict[str, Any]]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            ordinary = await client.post("/api/v1/calculations/single-bolt/evaluate", json=payload)
            signed = await client.post(
                "/api/v1/calculations/single-bolt/evaluate?report_snapshot=1", json=payload
            )
            assert ordinary.status_code == signed.status_code == 200
            return ordinary.json(), signed.json()

    ordinary, signed = asyncio.run(run())
    assert isinstance(signed.pop("report_snapshot"), str)
    assert signed == ordinary


@pytest.mark.parametrize(
    "family",
    tuple(
        name
        for name in FAMILIES
        if name not in {"single-bolt", "multi-row", "stair-stringer-miter"}
    ),
)
def test_report_opt_in_preserves_every_native_family_result(family: str) -> None:
    payload = native_payload(family)

    async def run() -> tuple[dict[str, Any], dict[str, Any]]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            route = f"/api/v1/calculations/{family}/design-check"
            ordinary = await client.post(route, json=payload)
            signed = await client.post(f"{route}?report_snapshot=1", json=payload)
            assert ordinary.status_code == signed.status_code == 200
            return ordinary.json(), signed.json()

    ordinary, signed = asyncio.run(run())
    assert isinstance(signed.pop("report_snapshot"), str)
    assert signed == ordinary


def test_executed_method_without_report_adapter_fails_export(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from frp_master_connection.reporting import generic
    from frp_master_connection.reporting.pdf import ReportingCoverageError, ReportOptions

    signer = SnapshotSigner(b"x" * 32)
    token = signer.issue(
        family="tee-connector",
        kind="design",
        request={},
        result={
            "result": {
                "checks": [
                    {
                        "result_id": "NATIVE-1",
                        "equation_method": "PIN_BEARING",
                        "availability": "CALCULATED",
                        "equation_trace": {"adjusted_property": "1"},
                    }
                ]
            }
        },
        account_id="report-test-account",
    )
    snapshot = signer.verify(token, account_id="report-test-account")
    monkeypatch.setattr(generic, "_MULTIROW_METHODS", {})
    with pytest.raises(ReportingCoverageError, match="no REPORT1 report adapter"):
        generic.render_generic_pdf(snapshot, ReportOptions())


def test_axial_single_bolt_pdf_shows_both_executed_pull_through_branches() -> None:
    payload = cast(dict[str, Any], build_api_payload("J1-T"))
    payload["explicit_resolved_demand"]["bolt_axis_tensile_demand"]["value"] = "0.1"

    async def run() -> tuple[dict[str, Any], httpx.Response]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            design = await client.post("/api/v1/calculations/single-bolt/evaluate", json=payload)
            assert design.status_code == 200
            report = await client.post(
                "/api/v1/reports/export",
                json={"report_handle": design.headers["X-Report-Handle"]},
            )
            return design.json(), report

    native, report = asyncio.run(run())
    assert report.status_code == 200
    text = "".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(report.content)).pages
    )
    compact = text.replace("\n", "")
    pulls = [check for check in native["results"] if check["plan"]["limit_state"] == "PULL_THROUGH"]
    assert len(pulls) == 2
    for check in pulls:
        assert check["availability"] == "CALCULATED"
        assert check["plan"]["check_id"] in text
        assert check["equation_trace"]["branch_8_4a_nominal"]["value"] in compact
        assert check["equation_trace"]["branch_8_4b_nominal"]["value"] in compact
    assert "Native pull-through branch 8-4a" in text
    assert "Native pull-through branch 8-4b" in text
    assert "D_w(1 in)" in text


def test_invalid_preview_exports_only_sealed_inputs_and_validation_issues() -> None:
    invalid = build_j1_preview_api_payload(brace_view_length="0")

    async def run() -> tuple[httpx.Response, httpx.Response]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            preview = await client.post("/api/v1/calculations/single-bolt/preview", json=invalid)
            assert preview.status_code == 422
            report = await client.post(
                "/api/v1/reports/export",
                json={"report_handle": preview.headers["X-Report-Handle"]},
            )
            return preview, report

    preview, report = asyncio.run(run())
    assert preview.headers["X-Report-Kind"] == "input_only"
    assert report.status_code == 200
    text = "".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(report.content)).pages
    )
    assert "Inputs and model report - design not evaluated" in text
    assert "INPUT_VALIDATION_FAILED" in text
    assert "design_evaluated" in text
    assert "Isometric" not in text
    assert "Native utilization" not in text


def test_ordinary_response_handle_exports_same_result_and_is_account_bound() -> None:
    async def run() -> tuple[int, str, int, int]:
        resolver = _Resolver("account-a")
        app = create_app(
            settings=AppSettings(environment=ApplicationEnvironment.TEST),
            identity_resolver=resolver,
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            design = await client.post(
                "/api/v1/calculations/single-bolt/evaluate",
                json=build_api_payload("J1-T"),
            )
            handle = design.headers["X-Report-Handle"]
            exported = await client.post(
                "/api/v1/reports/export",
                json={
                    "report_handle": handle,
                    "connection_id": "J1-T",
                },
            )
            resolver.account_id = "account-b"
            forbidden = await client.post(
                "/api/v1/reports/export",
                json={
                    "report_handle": handle,
                    "connection_id": "J1-T",
                },
            )
            return design.status_code, handle, exported.status_code, forbidden.status_code

    design_status, handle, export_status, forbidden_status = asyncio.run(run())
    assert design_status == 200
    assert len(handle) == 32
    assert export_status == 200
    assert forbidden_status == 409


def test_tampered_snapshot_is_rejected_before_rendering() -> None:
    _, response = _run_report(tamper=True)
    assert response.status_code == 409
    assert response.headers["content-type"] == "application/json"


def test_signed_snapshot_is_account_bound_and_expires() -> None:
    signer = SnapshotSigner(b"x" * 32)
    token = signer.issue(
        family="single-bolt",
        kind="design",
        request={"case": "A"},
        result={"status": "SOURCE_REQUIRED"},
        account_id="account-a",
        now=1_000,
    )
    assert (
        signer.verify(token, account_id="account-a", now=1_001).result["status"]
        == "SOURCE_REQUIRED"
    )
    with pytest.raises(SnapshotError, match="identity"):
        signer.verify(token, account_id="account-b", now=1_001)
    with pytest.raises(SnapshotError, match="expired"):
        signer.verify(token, account_id="account-a", now=2_000)


def test_browser_supplied_result_and_markup_are_rejected() -> None:
    async def run() -> httpx.Response:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            design = await client.post(
                "/api/v1/calculations/single-bolt/evaluate?report_snapshot=1",
                json=build_api_payload("J1-T"),
            )
            return await client.post(
                "/api/v1/reports/export",
                json={
                    "report_snapshot": design.json()["report_snapshot"],
                    "result": {"overall_status": "PASS"},
                    "project_name": "<script>alert(1)</script>",
                },
            )

    response = asyncio.run(run())
    assert response.status_code == 422


@pytest.mark.parametrize("operation", ["design-check", "preview"])
def test_multirow_real_pdf_has_native_path_inventory_and_input_only_boundary(
    operation: str,
) -> None:
    payload = native_payload("multi-row")

    async def run() -> tuple[dict[str, object], httpx.Response]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            native = await client.post(f"/api/v1/calculations/multi-row/{operation}", json=payload)
            assert native.status_code == 200
            response = await client.post(
                "/api/v1/reports/export",
                json={
                    "report_handle": native.headers["X-Report-Handle"],
                    "connection_id": "MR-1",
                },
            )
            return native.json(), response

    body, response = asyncio.run(run())
    assert response.status_code == 200
    pdf = PdfReader(io.BytesIO(response.content))
    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    assert "B_R1_L1" in text
    assert "Isometric - not to scale" in text
    assert "Page 1 of " in text
    if operation == "preview":
        assert "design not evaluated" in text.lower()
        assert "Native utilization" not in text
    else:
        calculation = body["calculation_result"]
        assert isinstance(calculation, dict)
        calculated = calculation["results"]
        first_bearing = next(check for check in calculated if check["limit_state"] == "PIN_BEARING")
        assert first_bearing["result_id"] in text
        assert first_bearing["utilization"] in text.replace("\n", "")
        assert "First-row net tension" in text


@pytest.mark.parametrize(
    "family",
    tuple(
        name
        for name in FAMILIES
        if name not in {"single-bolt", "multi-row", "stair-stringer-miter"}
    ),
)
def test_each_native_family_exports_an_actual_canonical_pdf(family: str) -> None:
    payload = native_payload(family)

    async def run() -> tuple[httpx.Response, httpx.Response]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            design = await client.post(f"/api/v1/calculations/{family}/design-check", json=payload)
            assert design.status_code == 200, design.text
            export = await client.post(
                "/api/v1/reports/export",
                json={
                    "report_handle": design.headers["X-Report-Handle"],
                    "connection_id": family,
                },
            )
            return design, export

    design, export = asyncio.run(run())
    assert export.status_code == 200
    assert export.content.startswith(b"%PDF-")
    pdf = PdfReader(io.BytesIO(export.content))
    assert len(pdf.pages) > 1
    first = pdf.pages[0].extract_text() or ""
    assert family in first
    assert "Canonical isometric" in " ".join(page.extract_text() or "" for page in pdf.pages[:6])
    assert design.headers["X-Report-Kind"] == "design"
    if family == "tee-connector":
        # Tee resistance lives in a nested design under the preview envelope.
        # It must survive compaction and retain the exact native value.
        native = design.json()["result"]["preview"]["interface_a"]["design"]
        bearing = native["automatic_handoff_results"][0]["checks"][1]["resistance_result"]
        resistance = bearing["design_resistance"]["value"]
        text = "".join(page.extract_text() or "" for page in pdf.pages)
        assert bearing["result_id"] in text
        assert resistance in text.replace("\n", "")
        assert "Executed equation methods and worked native traces" in text
        assert "R_n = t d F_br C_thread" in text
        layer = native["preview"]["visualization"]["layers"][0]
        assert f"t({layer['thickness']['value']} in)" in text
        assert "d(0.5 in)" in text
        assert f"canonical {layer['thickness']['canonical_value']} mm" in text
        assert "Native bolt-axis stack; schematic, not to scale" in text
        assert "tee-bolt-group-a / B_R1_L1" in text
        demand = native["automatic_demand_result"]
        scenario = demand["scenarios"][0]
        assert "Worked native eccentric bolt-group load assignment" in text
        assert scenario["residual_moment"]["value"] in text
        assert scenario["per_bolt"][0]["moment_force"]["u"]["value"] in text


def test_ssmc_analytical_pdf_keeps_its_source_limits_and_native_geometry() -> None:
    payload = {
        "physical": illustrative_ssmc().model_dump(mode="json"),
        "action": {
            "basis": "FACTORED_LRFD",
            "combination_id": "REPORT1_TEST",
            "combination_source": "TEST_FIXTURE",
            "already_factored": True,
            "time_effect_category": "OTHER_LIVE",
            "time_effect_reference": "TEST_FIXTURE",
        },
        "single_lap": {
            "external_actions_at_faying_interface": True,
            "independent_normal_force": {"value": "0", "unit": "N"},
            "independent_out_of_plane_moment": {"value": "0", "unit": "N-mm"},
            "imposed_separation": False,
            "non_contact_gap": False,
            "friction_or_preload_credit": False,
            "miter_bearing_credit": False,
        },
    }

    async def run() -> tuple[dict[str, Any], httpx.Response]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            design = await client.post(
                "/api/v1/calculations/stair-stringer-miter/analytical-design-check",
                json=payload,
            )
            assert design.status_code == 200
            report = await client.post(
                "/api/v1/reports/export",
                json={
                    "report_handle": design.headers["X-Report-Handle"],
                },
            )
            return design.json(), report

    design, report = asyncio.run(run())
    assert report.status_code == 200
    pdf = PdfReader(io.BytesIO(report.content))
    cover = pdf.pages[0].extract_text() or ""
    assert humanize("ENGINEERING_REVIEW_REQUIRED") in cover
    early_text = " ".join(page.extract_text() or "" for page in pdf.pages[:6])
    assert "Canonical isometric" in early_text
    assert "MITER_WEB_PLATE" in early_text
    assert design["whole_connection_status"] == "ENGINEERING_REVIEW_REQUIRED"
    full_text = "".join(page.extract_text() or "" for page in pdf.pages).replace("\n", "")
    assert "ENGINEERING_REVIEW_REQUIRED" in full_text
    first_cut = design["result"]["cuts"]["cuts"][0]
    assert "SSMC_ACTUAL_POLYGON_CUT_FREE_BODY_RC1" in full_text
    assert "sigma_edge=N/A_net+M(y_edge-y_c)/I_net" in full_text
    assert str(first_cut["net_area_mm2"]) in full_text
    assert "Finite cut coverage is not a proof" in full_text


def test_conditional_stainless_pdf_uses_its_native_status_and_selection() -> None:
    payload = native_payload("clip-angle")

    async def run() -> tuple[dict[str, object], httpx.Response]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            design = await client.post(
                "/api/v1/calculations/clip-angle/design-check?connector_body_material=SS316",
                json=payload,
            )
            assert design.status_code == 200
            report = await client.post(
                "/api/v1/reports/export",
                json={"report_handle": design.headers["X-Report-Handle"]},
            )
            return design.json(), report

    native, report = asyncio.run(run())
    assert report.status_code == 200
    pdf = PdfReader(io.BytesIO(report.content))
    cover = pdf.pages[0].extract_text() or ""
    assert "Numerical design status" in cover
    assert isinstance(native["status"], str)
    assert humanize(native["status"]) in cover
    assert "SS316" in cover
    report_text = "".join(page.extract_text() or "" for page in pdf.pages)
    assert "_calculation_query_parameters.connector_body_material" in report_text.replace("\n", "")
    assert native["connector_body_material"] == "SS316"


@pytest.mark.parametrize(
    "family",
    [
        "wi-major-axis-moment-splice",
        "wi-beam-frp-support-moment",
        "double-channel-truss-node",
    ],
)
def test_non_multirow_executed_methods_show_their_exact_native_values(family: str) -> None:
    payload = native_payload(family)

    async def run() -> tuple[dict[str, Any], bytes]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            design = await client.post(f"/api/v1/calculations/{family}/design-check", json=payload)
            assert design.status_code == 200
            export = await client.post(
                "/api/v1/reports/export",
                json={"report_handle": design.headers["X-Report-Handle"]},
            )
            assert export.status_code == 200, export.text
            return design.json(), export.content

    native, pdf_bytes = asyncio.run(run())
    report_text = "".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_bytes)).pages
    ).replace("\n", "")
    result = native["result"]
    if family == "wi-major-axis-moment-splice":
        plate = result["flange_plate_bodies"][0]["tension_strength"]
        web = result["web_body"]
        assert "N_i=P A_i/A+M A_i y_i/I" in report_text
        assert "F_o=(M_local-e_i F)/(e_o-e_i)" in report_text
        assert "R_n=0.7 A_net,eff F_t,L,adjusted" in report_text
        assert plate["nominal_strength"]["value"] in report_text
        assert plate["design_strength"]["value"] in report_text
        assert "U=|sigma|/F_normal,d+|tau|/F_shear,d" in report_text
        assert web["critical_sections"][0]["rational_utilization"] in report_text
    elif family == "wi-beam-frp-support-moment":
        instep = result["connector_results"][0]["detail"]["instep"]
        bearing = result["support_local_checks"][0]
        assert "R_n=L_eff t F_sh,LT,adjusted" in report_text
        assert "M_target=M_source+(r_source-r_target)cross F" in report_text
        assert instep["factors"]["design_resistance"]["value"] in report_text
        assert "R_n=t d F_br C_thread" in report_text
        assert bearing["resistance"]["value"] in report_text
    else:
        response = result["preview"]["historical_preview"]["response"]
        row = response["rows"][0]
        shaft = response["shafts"][0]
        assert "P_row=f_row P_member" in report_text
        assert row["signed_row_force"]["value"] in report_text
        assert shaft["shear_plane_demands"][0]["value"] in report_text


def test_dctn_3b_transverse_demand_is_reported_without_response_qualification() -> None:
    from frp_master_connection.api.double_channel_truss_node import serialize_dctn_value
    from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
    from frp_master_connection.domain.dctn3b import default_dctn3b_request

    request = default_dctn3b_request()
    request = replace(
        request,
        members=(
            replace(request.members[0], Qp=PhysicalQuantity.of(2, Unit.KIP)),
            *request.members[1:],
        ),
    )

    async def run() -> tuple[dict[str, Any], bytes]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            native = await client.post(
                "/api/v1/calculations/double-channel-truss-node/design-check",
                json=serialize_dctn_value(request),
            )
            assert native.status_code == 200
            report = await client.post(
                "/api/v1/reports/export",
                json={"report_handle": native.headers["X-Report-Handle"]},
            )
            assert report.status_code == 200, report.text
            return native.json(), report.content

    native, pdf_bytes = asyncio.run(run())
    preview = native["result"]["preview"]
    first = preview["demand"]["members"][0]
    text = "".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_bytes)).pages
    ).replace("\n", "")
    assert "DCTN-3B exact member action transport" in text
    assert "F=P u+Qp p+Qq q" in text
    assert first["at_member_end"]["force"]["x"]["value"] in text
    assert preview["trusted_response"]["status"] == "UNRESOLVED"
    assert "DCTN_TRUSTED_RESPONSE_NOT_BOUND" in text


@pytest.mark.parametrize(
    ("display_units", "native_equivalent"),
    [
        ("US_CUSTOMARY", "25.4 mm; canonical 25.4 mm; US_CUSTOMARY equivalent 1 in"),
        ("SI", "0.5 in; SI equivalent 12.70 mm"),
    ],
)
def test_generic_pdf_shows_native_and_requested_unit_equivalents(
    display_units: str, native_equivalent: str
) -> None:
    payload = native_payload("tee-connector")

    async def run() -> bytes:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            design = await client.post(
                "/api/v1/calculations/tee-connector/design-check", json=payload
            )
            assert design.status_code == 200
            export = await client.post(
                "/api/v1/reports/export",
                json={
                    "report_handle": design.headers["X-Report-Handle"],
                    "display_units": display_units,
                },
            )
            assert export.status_code == 200, export.text
            return export.content

    text = "".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(asyncio.run(run()))).pages
    ).replace("\n", "")
    assert native_equivalent in text


def test_mat1_session_material_remains_in_pdf_without_catalog_persistence() -> None:
    from tests.api.test_mat1_routes import condition

    legacy = cast(dict[str, Any], build_api_payload("P1"))
    legacy["time_effect_category"] = "OTHER_LIVE"
    design_conditions = condition("OTHER_LIVE")
    design_conditions["sustained_temperature"] = {"value": "60", "unit": "degC"}
    design_conditions["maximum_temperature"] = {"value": "60", "unit": "degC"}
    request = {
        "contract": "MAT1-SINGLE-BOLT-RC0",
        "legacy_request": legacy,
        "assignments": {
            "default_material": {
                "kind": "SESSION",
                "id": "SESSION:report-qa",
                "revision": "1",
                "display_name": "Synthetic coupon",
                "company": "Test only",
                "resin": "VINYL_ESTER",
                "properties": {
                    "tensile_strength_L": {
                        "label": "Tension",
                        "symbol": "Ft,L",
                        "value": "42",
                        "unit": "ksi",
                        "basis": "CHARACTERISTIC",
                    }
                },
            },
            "default_conditions": design_conditions,
        },
    }

    async def run() -> tuple[dict[str, Any], bytes, bool]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            before = (await client.get("/api/v1/frp-materials/catalog")).json()
            design = await client.post(
                "/api/v1/frp-materials/single-bolt/design-check", json=request
            )
            assert design.status_code == 200
            report = await client.post(
                "/api/v1/reports/export",
                json={
                    "report_handle": design.headers["X-Report-Handle"],
                    "connection_id": "SYNTHETIC QA FIXTURE",
                    "display_units": "US_CUSTOMARY",
                },
            )
            assert report.status_code == 200, report.text
            after = (await client.get("/api/v1/frp-materials/catalog")).json()
            return design.json(), report.content, before == after

    native, pdf_bytes, catalog_unchanged = asyncio.run(run())
    pdf = PdfReader(io.BytesIO(pdf_bytes))
    text = "".join(page.extract_text() or "" for page in pdf.pages).replace("\n", "")
    ledger = native["material_ledgers"][0]
    assert catalog_unchanged
    assert native["overall_status"] == "SOURCE_REQUIRED"
    assert ledger["record_id"] == "SESSION:report-qa"
    assert ledger["original"] == "42"
    assert ledger["ct"] == "0.580"
    assert ledger["adjusted_candidate"] == "24.360"
    assert ledger["adjusted_candidate"] in text
    assert "60 degC = 140 degF" in text
    assert ledger["record_id"] in text
    assert "TG_REQUIRED" in text
    assert all("SYNTHETIC QA FIXTURE" in (page.extract_text() or "") for page in pdf.pages)


@pytest.mark.parametrize("family", ["single-bolt", "multi-row", "clip-angle"])
def test_unrun_client_draft_exports_as_unvalidated_input_only_pdf(family: str) -> None:
    async def run() -> tuple[httpx.Response, httpx.Response]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            draft = await client.post(
                "/api/v1/reports/input-only-snapshot",
                json={
                    "family": family,
                    "draft": {"connected_length": {"value": "-1", "unit": "in"}},
                },
            )
            assert draft.status_code == 201
            report = await client.post(
                "/api/v1/reports/export",
                json={"report_handle": draft.json()["report_handle"]},
            )
            return draft, report

    draft, report = asyncio.run(run())
    assert draft.headers["cache-control"] == "no-store, private"
    assert report.status_code == 200, report.text
    text = "\n".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(report.content)).pages
    )
    assert "Submitted inputs - design not evaluated" in text
    assert "INPUT_NOT_EVALUATED" in text
    assert "unvalidated user draft" in text
    assert "Client draft captured without native validation or calculation" in (
        PdfReader(io.BytesIO(report.content)).pages[0].extract_text() or ""
    )
    assert "7  Executed calculation methods and substitutions" not in text
    assert "result.client_draft" not in text
    assert "request.client_draft.connected_length" in text
    assert "No native geometry was calculated" in text
    assert "Highest native numerical ratio" in text


@pytest.mark.parametrize(
    ("changes", "expected_methods"),
    [
        ({"first_row_method": "ASCE_COMMENTARY_FULL"}, ("FIRST_ROW_COMMENTARY_FULL",)),
        ({"row_count": 3}, ("INTERROW_ASCE_EQ_8_13",)),
        (
            {"row_count": 4, "first_row_method": "RATIONAL_MULTIROW_LOWER_ENVELOPE"},
            (
                "FIRST_ROW_RATIONAL_LOWER_ENVELOPE",
                "INTERROW_RATIONAL_EXTENSION_EQ_8_13",
            ),
        ),
    ],
)
def test_actual_multirow_method_variants_have_executed_report_adapters(
    changes: dict[str, object], expected_methods: tuple[str, ...]
) -> None:
    payload = native_payload("multi-row")
    payload.update(changes)

    async def run() -> tuple[dict[str, Any], bytes]:
        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            design = await client.post("/api/v1/calculations/multi-row/design-check", json=payload)
            assert design.status_code == 200
            report = await client.post(
                "/api/v1/reports/export",
                json={"report_handle": design.headers["X-Report-Handle"]},
            )
            assert report.status_code == 200, report.text
            return design.json(), report.content

    native, pdf_bytes = asyncio.run(run())
    checks = native["calculation_result"]["results"]
    report_text = "".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_bytes)).pages
    ).replace("\n", "")
    for method in expected_methods:
        matching = [
            check
            for check in checks
            if check["equation_method"] == method and check["availability"] == "CALCULATED"
        ]
        assert matching, method
        assert method in report_text
        assert matching[0]["equation_nominal_resistance"]["value"] in report_text
