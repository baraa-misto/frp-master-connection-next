"""Generate signed-snapshot Direct F1 PDFs for Windows/Ubuntu candidate QA.

This is a review artifact generator. It reads native calculation results and
does not author engineering values, status, or qualification.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from frp_master_connection.api.multirow_mapping import (
    serialize_multirow_design,
)
from frp_master_connection.application import evaluate_multirow_connection
from frp_master_connection.reporting.pdf import (
    ReportOptions,
    render_multirow_pdf,
)
from frp_master_connection.reporting.snapshot import SnapshotSigner
from tests.application.test_direct_f1_safety import (
    _direct_payload,
    _one_row_payload,
    _request,
)


def cases() -> list[tuple[str, dict[str, object]]]:
    selected = [
        ("valid-1x1", _one_row_payload(1)),
        ("valid-1x2", _one_row_payload(2)),
        ("valid-1x3", _one_row_payload(3)),
        ("valid-2x2", _direct_payload()),
        ("red-1x3", _one_row_payload(3, force="70")),
        ("invalid-containment", _direct_payload(physically_contained=False)),
    ]
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output: Path = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()
    signer = SnapshotSigner(b"direct-f1-r2-cross-platform-review-only-32")
    records: list[dict[str, object]] = []

    for name, payload in cases():
        assert payload["lap_configuration"] == "SINGLE_LAP"
        physical = payload["physical_connection"]
        assert isinstance(physical, dict)
        assert physical["lap_configuration"] == "SINGLE_LAP"
        result = serialize_multirow_design(
            evaluate_multirow_connection(_request(payload))
        ).model_dump()
        original = deepcopy(result)
        token = signer.issue(
            family="multi-row",
            kind="design",
            request=payload,
            result=result,
            account_id="qa",
        )
        snapshot = signer.verify(token, account_id="qa")
        signed_original = deepcopy(snapshot.result)
        variants = [("US_CUSTOMARY", "ENGINEER_REPORT")]
        if name in {"valid-1x2", "valid-2x2"}:
            variants += [
                ("US_CUSTOMARY", "FULL_TECHNICAL_AUDIT"),
                ("SI", "ENGINEER_REPORT"),
                ("SI", "FULL_TECHNICAL_AUDIT"),
            ]
        for system, mode in variants:
            pdf = render_multirow_pdf(
                snapshot, ReportOptions(display_units=system, mode=mode)
            )
            reader = PdfReader(io.BytesIO(pdf))
            preview_pages = [page.extract_text() or "" for page in reader.pages[:10]]
            first_text = "\n".join(preview_pages)
            assert all(len(text.strip()) > 40 for text in preview_pages)
            assert "Direct angle-to-W connection" in first_text
            assert "SINGLE_LAP" in first_text
            if name.startswith("valid-1"):
                assert "Canonical single-row bolt layout" in first_text
                assert "Not applicable — one row" in first_text
                assert "Pitch / gauge" not in first_text
                assert "c lap: 0.6" in first_text
            if name == "invalid-containment":
                assert "SUBMITTED GEOMETRY — NOT VALIDATED" in first_text
            if name == "red-1x3":
                assert "FAIL" in first_text
            if mode == "ENGINEER_REPORT":
                assert len(reader.pages) <= 10
                assert "TECHNICAL AUDIT APPENDIX" not in first_text
            else:
                assert len(reader.pages) > 100
                assert "TECHNICAL AUDIT APPENDIX" in first_text
            filename = f"direct-f1-r2-{name}-{system.lower()}-{mode.lower()}.pdf"
            (output / filename).write_bytes(pdf)
            records.append(
                {
                    "candidate_sha": commit,
                    "case": name,
                    "display_units": system,
                    "mode": mode,
                    "filename": filename,
                    "pages": len(reader.pages),
                    "bytes": len(pdf),
                    "sha256": hashlib.sha256(pdf).hexdigest(),
                    "signed_snapshot_digest": snapshot.digest,
                    "geometry_status": result["preview"]["geometry_status"],
                }
            )
            print(f"{filename}: {len(reader.pages)} pages")
        assert result == original
        assert snapshot.result == signed_original
    (output / "DIRECT_F1_PLATFORM_PDF_QA.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )
    print(f"{len(records)} signed-snapshot PDFs generated at {commit}")


if __name__ == "__main__":
    main()
