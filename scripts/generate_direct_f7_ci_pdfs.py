"""Generate actual authenticated F7 review PDFs and native evidence on each CI OS."""
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

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend/src"), str(ROOT / "backend")]
from tests.api.test_direct_f6_first_row import f6_cases
from tests.api.test_direct_f7_angle_block import block_result, magnitude
from tests.api.test_f593_f4 import design, supported
from frp_master_connection.calculation import Unit
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner


def cases() -> dict:
    controls = f6_cases()
    result = {key: controls[key] for key in ("owner-135", "control-45", "zero-eccentricity", "si-owner", "finite-w", "three-row")}
    result["heel-na"] = deepcopy(controls["owner-135"])
    result["block-red"] = deepcopy(controls["owner-135"])
    result["block-red"]["legacy_request"]["physical_connection"]["joint_assembly"]["member_end_actions"][0]["force"]["x"] = "4"
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True))
    signer = SnapshotSigner(b"DIRECT-F7-PLATFORM-AUTHENTICATED-REPORT-KEY")
    manifest = []
    for name, body in cases().items():
        result = design(body)
        block = block_result(result)
        check = block["supported_results"][0]
        integration = result["native_design"]["automatic_group_mode_integration"]
        assert check["numerical_comparison"] == ("FAIL" if name == "block-red" else "PASS")
        assert integration["qualification"] == "SECTION_2_3_2_QUALIFICATION_REQUIRED"
        assert block["history_results"][0]["availability"] == "NOT_APPLICABLE"
        assert block["history_results"][0]["demand"] is None
        assert len(supported(result)) == (11 if name == "three-row" else 8)
        snapshot = signer.verify(signer.issue(family="multi-row", kind="design", request=body, result=result, account_id="f7-platform"), account_id="f7-platform")
        before = deepcopy((snapshot.request, snapshot.result))
        for mode in (("ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT") if name == "owner-135" else ("ENGINEER_REPORT",)):
            pdf = render_report_pdf(snapshot, ReportOptions(mode=mode))
            filename = f"direct-f7-{name}-{mode.lower()}.pdf"
            (output / filename).write_bytes(pdf)
            pages = PdfReader(io.BytesIO(pdf)).pages
            text = " ".join(" ".join(p.extract_text() or "" for p in pages).split())
            assert "Angle heel side NOT APPLICABLE" in text
            assert "perpendicular leg remains continuous" in text
            assert "Section 2.3.2" in text
            if mode == "FULL_TECHNICAL_AUDIT":
                assert block["method_id"] in text
            else:
                assert block["method_id"] not in text
                equation = "8-14a" if "8_14A" in block["method_id"] else "8-14b"
                assert f"ASCE Eq. {equation}" in text
            if name != "three-row":
                assert "8 supported checks evaluated" in text
                assert "6 required checks/evidence items unresolved" in text
            if name == "block-red":
                assert integration["overall_disposition"] == "FAIL"
            (output / (filename + ".txt")).write_text(text, encoding="utf-8")
            manifest.append(dict(candidate_sha=sha, platform=platform.platform(), tracked_working_tree_modified=dirty, case=name, mode=mode, file=filename, pages=len(pages), bytes=len(pdf), sha256=hashlib.sha256(pdf).hexdigest().upper(), snapshot_digest=snapshot.digest, block=block, checks=supported(result), integration={k: integration[k] for k in ("required_check_ids", "unsupported_required_check_ids", "incomplete_required_check_ids", "not_required_check_ids", "failed_check_ids", "governing_supported_check_ids", "overall_disposition", "qualification")}, demand=result["native_design"]["automatic_demand_result"]))
            print(f"{filename}: {len(pages)} pages; Rd={magnitude(check['design_resistance'],Unit.KIP)} kip; {check['numerical_comparison']}", flush=True)
        assert before == (snapshot.request, snapshot.result)
        for kind, payload in (("request", snapshot.request), ("result", snapshot.result), ("api-request", body)):
            (output / (name + "-signed-" + kind + ".json")).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (output / "DIRECT_F7_PLATFORM_PDF_QA.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
