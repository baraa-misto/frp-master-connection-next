"""Actual signed-snapshot owner starter reports on Windows and Ubuntu."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner
from tests.api.test_mat1_routes import call
from tests.direct_or2_fixtures import owner_body


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output: Path = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    signer = SnapshotSigner(b"DIRECT-OR2-F1-PLATFORM-PDF-AUTHORITY-32")
    manifest: list[dict[str, Any]] = []
    cases = [
        "owner-2x1-partial",
        "missing-basic-input",
        "f593-source-required",
        "invalid-geometry",
        "red-1x1",
        "si-owner",
        "unknown-exposure",
    ]
    for name in cases:
        body = owner_body(si=name == "si-owner", one_row=name == "red-1x1")
        conditions = body["assignments"]["default_conditions"]
        if name == "unknown-exposure":
            conditions.update(moisture="UNKNOWN", chemical="UNKNOWN")
        if name == "missing-basic-input":
            conditions["sustained_temperature"]["value"] = ""
            conditions["maximum_temperature"]["value"] = ""
            conditions["time_effect_category"] = ""
        if name == "invalid-geometry":
            body["legacy_request"]["unloaded_end_e1"]["value"] = "6"
            body["legacy_request"]["physical_connection"]["geometry_template"][
                "bolt_to_brace_end_distance"
            ]["value"] = "6"
        input_only = name in {"missing-basic-input", "invalid-geometry"}
        route = (
            "/api/v1/calculations/multi-row/preview"
            if input_only
            else "/api/v1/frp-materials/multi-row/design-check"
        )
        response = call("POST", route, body["legacy_request"] if input_only else body)
        assert response.status_code == 200, f"{name}: {response.text[:600]}"
        result = response.json()
        token = signer.issue(
            family="multi-row",
            kind="input_only" if input_only else "design",
            request=body,
            result=result,
            account_id="or2-qa",
        )
        snapshot = signer.verify(token, account_id="or2-qa")
        original = deepcopy((snapshot.request, snapshot.result))
        modes = (
            ("ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT")
            if name == "owner-2x1-partial"
            else ("ENGINEER_REPORT",)
        )
        for mode in modes:
            pdf = render_report_pdf(snapshot, ReportOptions(mode=mode))
            reader = PdfReader(io.BytesIO(pdf))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            normalized = " ".join(text.split())
            assert "Direct angle-to-W connection" in text
            assert (
                len(reader.pages) <= 10
                if mode == "ENGINEER_REPORT"
                else len(reader.pages) > 100
            )
            if input_only:
                assert "design not evaluated" in text.lower()
            else:
                assert "NUMERICAL CHECKS" in text and "DESIGN COMPLETENESS" in text
                assert result["design_check_performed"] is True
                assert result["fastener_source"]["fnt"] is None
            if name == "red-1x1":
                assert result["overall_status"] == "FAIL"
                assert "FAIL" in text
                assert "1.22684" in text
            if name == "unknown-exposure":
                assert (
                    "Diagnostic only" in text
                    and "adjusted resistance unavailable" in normalized
                )
            filename = f"direct-or2-{name}-{mode.lower()}.pdf"
            (output / filename).write_bytes(pdf)
            (output / f"{name}-signed-request.json").write_text(
                json.dumps(snapshot.request, indent=2), encoding="utf-8"
            )
            (output / f"{name}-signed-result.json").write_text(
                json.dumps(snapshot.result, indent=2), encoding="utf-8"
            )
            manifest.append(
                {
                    "candidate_sha": sha,
                    "case": name,
                    "mode": mode,
                    "file": filename,
                    "pages": len(reader.pages),
                    "bytes": len(pdf),
                    "sha256": hashlib.sha256(pdf).hexdigest().upper(),
                    "signed_snapshot_digest": snapshot.digest,
                }
            )
            assert (snapshot.request, snapshot.result) == original
            print(f"{filename}: {len(reader.pages)} pages")
    (output / "DIRECT_OR2_PLATFORM_PDF_QA.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
