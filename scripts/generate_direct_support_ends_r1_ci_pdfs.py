"""Actual signed Direct supporting-W end reports on each CI operating system."""

from __future__ import annotations

import argparse
from copy import deepcopy
from decimal import Decimal, localcontext
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tests.api.test_direct_support_ends_r1 import r1_design, r1_preview, r1_request
from tests.direct_or2_fixtures import owner_body
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
    baseline = r1_preview(r1_request(angle="45"))["direct_support_end_authority"]
    offset = next(Decimal(r["canonical_reference_offset"]) for r in baseline["bolt_records"] if r["bolt_id"] == "B_R1_L1")
    with localcontext() as context:
        context.prec = 100
        exact = str(offset + 1)
        near = str(offset + Decimal("0.086"))
    cases = {
        "continuous-45": r1_request(angle="45"),
        "continuous-135": r1_request(),
        "owner-starter": r1_request(),
        "si-owner-starter": r1_request(si=True),
        "finite-far": r1_request("FINITE_BOTH_ENDS"),
        "finite-exact": r1_request("FINITE_POSITIVE_END_ONLY", angle="45", above=exact),
        "finite-0086-fail": r1_request("FINITE_POSITIVE_END_ONLY", angle="45", above=near),
        "one-sided-below": r1_request("FINITE_NEGATIVE_END_ONLY"),
        "numerical-red": r1_request(),
        "unspecified": r1_request("UNSPECIFIED"),
    }
    cases["numerical-red"]["physical_connection"]["joint_assembly"]["member_end_actions"][0]["force"]["x"] = "7"
    signer = SnapshotSigner(b"DIRECT-SUPPORT-END-R1-PLATFORM-32-BYTES")
    manifest = []
    for name, request in cases.items():
        body = owner_body(si=request["source_length_unit"] == "mm")
        body["legacy_request"] = request
        result = r1_design(request)
        preview = result["native_design"]["preview"]
        assert preview["geometry_status"] == ("INVALID_GEOMETRY" if name == "finite-0086-fail" else "VALID")
        assert preview["design_check_ready"] == (name not in {"finite-0086-fail", "unspecified"})
        if name == "numerical-red":
            assert result["overall_status"] == "FAIL"
        if name.startswith("continuous"):
            assert all(r["loaded_end_distance"] is None for r in preview["direct_support_end_authority"]["bolt_records"])
        snapshot = signer.verify(signer.issue(family="multi-row", kind="design", request=body, result=result, account_id="r1-platform"), account_id="r1-platform")
        original = deepcopy((snapshot.request, snapshot.result))
        modes = ("ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT") if name == "owner-starter" else ("ENGINEER_REPORT",)
        for mode in modes:
            pdf = render_report_pdf(snapshot, ReportOptions(mode=mode))
            filename = f"direct-support-r1-{name}-{mode.lower()}.pdf"
            (output / filename).write_bytes(pdf)
            pages = PdfReader(io.BytesIO(pdf)).pages
            text = " ".join(" ".join(p.extract_text() or "" for p in pages).split())
            assert "Supporting W longitudinal condition" in text
            assert "Angle e1 does not supply W end authority" in text
            if name == "finite-0086-fail":
                assert "physical W end above connection" in text and "0.086" in text
            if mode == "FULL_TECHNICAL_AUDIT":
                assert "presentation_crop_member_local_stations" in "".join(text.split())
                assert "NO_FINITE_END_IN_DIRECTION" in text
            (output / (filename + ".txt")).write_text(text, encoding="utf-8")
            manifest.append({"candidate_sha": sha, "working_tree_modified": dirty, "platform": platform.platform(), "case": name, "mode": mode, "file": filename, "pages": len(pages), "bytes": len(pdf), "sha256": hashlib.sha256(pdf).hexdigest().upper(), "snapshot_digest": snapshot.digest, "geometry_status": preview["geometry_status"]})
            print(f"{filename}: {len(pages)} pages")
        assert (snapshot.request, snapshot.result) == original
        (output / (name + "-signed-request.json")).write_text(json.dumps(snapshot.request, indent=2), encoding="utf-8")
        (output / (name + "-signed-result.json")).write_text(json.dumps(snapshot.result, indent=2), encoding="utf-8")
    (output / "DIRECT_SUPPORT_END_R1_PLATFORM_PDF_QA.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
