"""Signed Direct F2 geometry, temperature and catalog evidence on both CI platforms."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner
from tests.api.test_mat1_routes import call, selection
from tests.direct_or2_fixtures import owner_body


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    signer = SnapshotSigner(b"DIRECT-OR2-F2-PLATFORM-PDF-AUTHORITY-32")
    manifest: list[dict[str, Any]] = []
    cases = ["owner-2x1", "near-edge", "temperature-roles", "tg-missing", "tg-pass", "tg-fail",
             "f593-catalog", "material-catalog", "red-2x1", "si-owner"]
    for name in cases:
        body = owner_body(si=name == "si-owner")
        conditions = body["assignments"]["default_conditions"]
        if name == "near-edge":
            body["legacy_request"]["unloaded_end_e1"]["value"] = "4.77"
            body["legacy_request"]["physical_connection"]["geometry_template"][
                "bolt_to_brace_end_distance"]["value"] = "4.77"
        if name in {"temperature-roles", "tg-pass", "tg-fail"}:
            conditions["sustained_temperature"]["value"] = "120"
            conditions["maximum_temperature"]["value"] = "130"
            if name != "temperature-roles":
                conditions["glass_transition_temperature"] = {
                    "value": "170" if name == "tg-pass" else "169.999999", "unit": "degF"}
        if name == "material-catalog":
            record = call("GET", "/api/v1/frp-materials/catalog").json()["records"][1]
            body["assignments"]["default_material"] = selection(record)
        if name == "red-2x1":
            body["legacy_request"]["physical_connection"]["joint_assembly"][
                "member_end_actions"][0]["force"]["x"] = "7"
        input_only = name == "near-edge"
        route = ("/api/v1/calculations/multi-row/preview" if input_only
                 else "/api/v1/frp-materials/multi-row/design-check")
        response = call("POST", route, body["legacy_request"] if input_only else body)
        assert response.status_code == 200, f"{name}: {response.text[:600]}"
        result = response.json()
        preview = result if input_only else result["native_design"]["preview"]
        assert len(preview["direct_clearance_provenance"]) == 4
        if input_only:
            assert preview["geometry_status"] == "INVALID_GEOMETRY"
            assert not preview["design_check_ready"]
            invalid = next(r for r in preview["direct_clearance_provenance"] if not r["valid"])
            assert abs(float(invalid["center_to_boundary"]) - .086047263146894) < .0001
        else:
            assert preview["geometry_status"] == "VALID"
            assert result["design_check_performed"]
            assert result["fastener_source"]["fnt"] is None
            assert result["material_sources"]["default"]["property_basis"] == "DEVELOPMENT_NOMINAL"
            state = result["material_sources"]["temperature_applicability"]["default"]
            assert state == ("PASS" if name == "tg-pass" else "FAIL" if name == "tg-fail" else "NOT_CONFIRMED")
        if name == "red-2x1":
            assert result["overall_status"] == "FAIL"
        token = signer.issue(family="multi-row", kind="input_only" if input_only else "design",
                             request=body, result=result, account_id="f2-platform-qa")
        snapshot = signer.verify(token, account_id="f2-platform-qa")
        original = deepcopy((snapshot.request, snapshot.result))
        modes = ("ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT") if name == "owner-2x1" else ("ENGINEER_REPORT",)
        for mode in modes:
            pdf = render_report_pdf(snapshot, ReportOptions(mode=mode))
            reader = PdfReader(io.BytesIO(pdf))
            text = " ".join(" ".join(p.extract_text() or "" for p in reader.pages).split())
            assert "Direct angle-to-W connection" in text
            assert len(reader.pages) <= 10 if mode == "ENGINEER_REPORT" else len(reader.pages) > 100
            if input_only:
                assert "design not evaluated" in text.lower()
                assert "Chapter 8 physical free-edge distance" in text and "0.086" in text
            else:
                assert "Sustained operating material temperature" in text
                assert "Maximum expected material temperature" in text
                assert "Tg applicability" in text and state.replace("_", " ") in text
                assert "DEVELOPMENT_NOMINAL" in text
                assert "NUMERICAL CHECKS" in text and "DESIGN COMPLETENESS" in text
            if name == "red-2x1":
                assert "2.22699" in text and "FAIL" in text
            filename = f"direct-or2-f2-{name}-{mode.lower()}.pdf"
            (output / filename).write_bytes(pdf)
            for suffix, value in (("request", snapshot.request), ("result", snapshot.result)):
                (output / f"{name}-signed-{suffix}.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
            manifest.append({"candidate_sha": sha, "platform": platform.platform(), "case": name,
                             "mode": mode, "file": filename, "pages": len(reader.pages), "bytes": len(pdf),
                             "sha256": hashlib.sha256(pdf).hexdigest().upper(),
                             "signed_snapshot_digest": snapshot.digest})
            assert (snapshot.request, snapshot.result) == original
            print(f"{filename}: {len(reader.pages)} pages")
    (output / "DIRECT_OR2_F2_PLATFORM_PDF_QA.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
