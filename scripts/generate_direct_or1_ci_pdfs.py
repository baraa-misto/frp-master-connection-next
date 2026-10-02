"""Generate signed-snapshot OR1 Direct PDFs on each backend CI runner."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner
from tests.api.test_direct_or1_material_parity import _session as material_session
from tests.api.test_fastener_or1 import _session as fastener_session
from tests.api.test_mat1_routes import call, condition, selection
from tests.application.test_direct_f1_safety import _direct_payload, _one_row_payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output: Path = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    candidate_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()
    records = call("GET", "/api/v1/frp-materials/catalog").json()["records"]
    cases: list[tuple[str, dict[str, Any], dict[str, Any], dict[str, Any] | None]] = [
        ("iso-default-valid", _direct_payload(), selection(records[0]), None),
        ("vinyl-default-valid", _direct_payload(), selection(records[1]), None),
        (
            "custom-material-valid",
            _direct_payload(),
            material_session(records[0]),
            None,
        ),
        (
            "iso-custom-fastener-valid",
            _direct_payload(),
            selection(records[0]),
            fastener_session(),
        ),
        (
            "iso-default-invalid-geometry",
            _direct_payload(physically_contained=False),
            selection(records[0]),
            None,
        ),
        (
            "iso-custom-fastener-red",
            _one_row_payload(3, force="70"),
            selection(records[0]),
            fastener_session(),
        ),
    ]
    signer = SnapshotSigner(b"OR1-R1-WINDOWS-UBUNTU-REPORT-QA-KEY-32")
    manifest: list[dict[str, object]] = []
    for name, legacy, material, fastener in cases:
        body: dict[str, Any] = {
            "contract": "MAT1-MULTI-ROW-RC0",
            "legacy_request": deepcopy(legacy),
            "assignments": {
                "default_material": material,
                "default_conditions": condition(legacy["time_effect_category"]),
            },
        }
        if fastener is not None:
            body["fastener"] = deepcopy(fastener)
        response = call("POST", "/api/v1/frp-materials/multi-row/design-check", body)
        assert response.status_code == 200, f"{name}: {response.text[:500]}"
        result = response.json()
        token = signer.issue(
            family="multi-row",
            kind="design",
            request=body,
            result=result,
            account_id="or1-qa",
        )
        snapshot = signer.verify(token, account_id="or1-qa")
        original_request, original_result = (
            deepcopy(snapshot.request),
            deepcopy(snapshot.result),
        )
        for mode in ("ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT"):
            pdf = render_report_pdf(snapshot, ReportOptions(mode=mode))
            reader = PdfReader(io.BytesIO(pdf))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            normalized = " ".join(text.split())
            material_source = result["material_sources"]["default"]
            fastener_source = result["fastener_source"]
            fastener_name = fastener_source.get("snapshot", fastener_source)[
                "display_name"
            ]
            assert material_source["display_name"] in text, name
            assert fastener_name in text, name
            assert (
                "ICE Locked Pultruded FRP" not in text or mode == "FULL_TECHNICAL_AUDIT"
            )
            assert "lambda=source required" not in text
            if mode == "FULL_TECHNICAL_AUDIT":
                assert material_source["id"] in text
                assert material_source["content_digest"] in "".join(text.split())
                assert "internal compatibility adapter" in normalized
                assert len(reader.pages) > 100
            else:
                assert len(reader.pages) <= 10
            if name.endswith("invalid-geometry"):
                assert "SUBMITTED GEOMETRY" in text
            if name.endswith("red"):
                assert "FAIL" in text
            filename = f"direct-or1-{name}-{mode.lower()}.pdf"
            (output / filename).write_bytes(pdf)
            manifest.append(
                {
                    "candidate_sha": candidate_sha,
                    "case": name,
                    "mode": mode,
                    "file": filename,
                    "sha256": hashlib.sha256(pdf).hexdigest().upper(),
                    "bytes": len(pdf),
                    "pages": len(reader.pages),
                    "signed_snapshot_digest": snapshot.digest,
                    "material_id": material_source["id"],
                    "fastener_kind": fastener_source["kind"],
                    "geometry_status": result["native_design"]["preview"][
                        "geometry_status"
                    ],
                }
            )
            assert snapshot.request == original_request
            assert snapshot.result == original_result
            print(f"{filename}: {len(reader.pages)} pages")
    (output / "DIRECT_OR1_PLATFORM_PDF_QA.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(
        f"{len(manifest)} signed-snapshot Direct OR1 PDFs generated at {candidate_sha}"
    )


if __name__ == "__main__":
    main()
