"""Executed isolated D2 endpoint/report examples. Imported by the governed PDF job."""

import asyncio
import io
import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import httpx
from pypdf import PdfReader

from frp_master_connection.api.hyb2_d2_review import create_d2_review_app
from frp_master_connection.application.hyb1_contract import Alignment
from frp_master_connection.application.hyb2_d2 import HardwareEvidence, SourceConditions
from frp_master_connection.reporting.hyb2_d2_service import D2ReviewService
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.rhm_direct_r3 import R3Geometry, geometry_digest
from frp_master_connection.reporting.hyb2_d2_review import render_d2
from frp_master_connection.reporting.snapshot import SnapshotSigner
from tests.application.test_hyb2_d2_review import Resolver
from tests.hyb1_fixtures import q
from tests.hyb2_d2_fixtures import actual_native_source, support_source


def generate_d2(output: Path) -> list[dict]:
    s = support_source()
    a = s.actions
    heavy = replace(a.asd[0], components=(q("60"), *a.asd[0].components[1:]))
    invalid = R3Geometry(hole=q("3", Unit.IN))
    sources = {
        "d2-source-partial": s,
        "d2-overload": replace(s, actions=replace(a, asd=(heavy,))),
        "d2-invalid-geometry": replace(s, geometry=invalid, actions=replace(a,
            identity=replace(a.identity, geometry=geometry_digest(invalid)))),
        "d2-source-properties-unmatched": replace(s, conditions=SourceConditions(resin="UNAPPROVED_PRODUCT")),
        "d2-missing-asd": replace(s, actions=replace(a, asd=())),
        "d2-confirmed-washer-no-fit": replace(s, actions=replace(a,
            identity=replace(a.identity, connection="HYB2_D2_HYPOTHETICAL_HARDWARE_TEST_ONLY")),
            hardware=HardwareEvidence("R3_BRACE_END_FREE_EDGE", q("1", Unit.IN),
                sha256(b"TEST_ONLY_HAND_DEFINED_FACE_NOT_FIELD_EVIDENCE").hexdigest())),
        "d2-brace-fixed-placement-no-fit": replace(s, actions=replace(a,
            identity=replace(a.identity, alignment=Alignment.BRACE))),
    }
    native_signer, native_source, original = actual_native_source()
    sources["d2-native-brace-unchanged"] = native_source
    records = []
    for name, source in sources.items():
        service = D2ReviewService(native_signer if source.native_token else SnapshotSigner())
        revision = service.register(name, source)
        app = create_d2_review_app(service, Resolver(source.actions.identity.account))

        async def execute():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated-review") as client:
                response = await client.post("/review/assess", json={"case_key": name, "revision": revision})
                assert response.status_code == 200, response.text
                handle = response.json()["report_handle"]
                pdf = await client.get("/review/report/" + handle)
                view = await client.get("/review/view/" + handle)
                assert pdf.status_code == view.status_code == 200
                html = view.text.replace("/review/report/" + handle, name + ".pdf")
                assert handle not in html
                return response.json()["record"], pdf.content, html

        record, pdf, html = asyncio.run(execute())
        (output / (name + ".html")).write_text(html, encoding="utf-8")
        variants = [(name, pdf)]
        if name == "d2-source-partial":
            variants.append(("d2-source-technical-audit", render_d2(record, technical=True)))
        for stem, data in variants:
            text = " ".join(" ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages).split())
            assert "Complete connection verification is not established" in text
            assert record["assessment"]["evaluated_outcome"] in text
            assert source.actions.identity.account not in text
            (output / (stem + ".pdf")).write_bytes(data)
            (output / (stem + ".json")).write_text(json.dumps(record, indent=2), encoding="utf-8")
            (output / (stem + ".txt")).write_text(text, encoding="utf-8")
            records.append({"file": stem + ".pdf", "sha256": sha256(data).hexdigest(),
                "pages": len(PdfReader(io.BytesIO(data)).pages), "scope": "D2_INACTIVE_REVIEW",
                "comparison": record["assessment"]["evaluated_outcome"], "public_activation": False})
            print(stem + ": " + str(records[-1]["pages"]) + " pages", flush=True)
    (output / "D2_NATIVE_ORIGINAL_UNCHANGED.json").write_text(json.dumps(original, indent=2), encoding="utf-8")
    assert len(records) == 9
    return records
