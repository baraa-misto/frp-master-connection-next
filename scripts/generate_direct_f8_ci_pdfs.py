"""Real F8 PDFs/statistical evidence on each OS; synthetic previews never activate."""
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
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend/src"), str(ROOT / "backend")]
import numpy
import scipy
from pypdf import PdfReader
from tests.api.test_direct_f6_first_row import f6_cases
from tests.api.test_f593_f4 import design, supported
from tests.direct_f8_fixtures import qa_design, specimen_series, statistical_protocol, synthetic_record
from frp_master_connection.api.direct_qualification import evaluate_record, qualification_snapshot_provenance
from frp_master_connection.infrastructure.direct_qualification_records import canonical_record, QualificationRecordProvider
from frp_master_connection.application.direct_qualification_statistics import connection_t, recompute_statistics
from frp_master_connection.reporting.pdf import ReportOptions, render_report_pdf
from frp_master_connection.reporting.snapshot import SnapshotSigner


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True))
    signer = SnapshotSigner(b"DIRECT-F8-PLATFORM-AUTHENTICATED-REPORT-KEY")
    matrix = []
    cases = f6_cases()
    qa = qa_design()
    for name in ("owner-no-record", "si-owner-no-record", "synthetic-exact", "geometry-mismatch", "action-mismatch", "statistics-invalid", "capacity-fail"):
        if name.endswith("no-record"):
            body = cases["si-owner" if name.startswith("si-") else "owner-135"]
            result = design(body)
            provenance = qualification_snapshot_provenance(result)
            assert len(supported(result)) == 8
            assert result["qualification_evaluation"]["record_digest"] is None
        else:
            body, native, scope, required, ledgers, context = qa
            with tempfile.TemporaryDirectory(prefix="direct-f8-synthetic-qa-") as tmp:
                evidence_dir = Path(tmp)
                payload = synthetic_record(scope, evidence_dir, strength="100" if name == "capacity-fail" else "10000")
                record_scope = deepcopy(scope)
                if name == "geometry-mismatch":
                    record_scope["geometry_scope"]["row_count"] = 3
                elif name == "action-mismatch":
                    record_scope["action_scope"]["Mx"] = "1"
                elif name == "statistics-invalid":
                    payload["statistical_protocol"]["lab_reported_cov"]["value"] = ".15"
                    payload["digest"] = ""
                record = canonical_record(payload)
                assert not QualificationRecordProvider(evidence_dir, (record,)).read()[0]
                public, audit = evaluate_record(record, record_scope, required, ledgers, context, qa_preview=True)
            result = {**native, "qualification_evaluation": public}
            provenance = {"direct_qualification_audit": audit}
            assert public["synthetic"] is True
            assert public["activation_permitted"] is False
            assert public["ordinary_pass_allowed"] is False
            assert public["capacity_state"] == ("CAPACITY_PASS" if name == "synthetic-exact" else "CAPACITY_FAIL" if name == "capacity-fail" else "UNEVALUATED")
        snapshot = signer.verify(signer.issue(family="multi-row", kind="design", request=body, result=result, input_provenance=provenance, account_id="f8-platform"), account_id="f8-platform")
        before = deepcopy((snapshot.request, snapshot.result, snapshot.input_provenance))
        for mode in (("ENGINEER_REPORT", "FULL_TECHNICAL_AUDIT") if name == "synthetic-exact" else ("ENGINEER_REPORT",)):
            pdf = render_report_pdf(snapshot, ReportOptions(mode=mode))
            filename = f"direct-f8-{name}-{mode.lower()}.pdf"
            (output / filename).write_bytes(pdf)
            pages = PdfReader(io.BytesIO(pdf)).pages
            text = " ".join(" ".join(p.extract_text() or "" for p in pages).split())
            assert "Section 2.3.2" in text
            if name.endswith("no-record"):
                assert "8 supported checks evaluated" in text
                assert "6 required checks/evidence items unresolved" in text
                assert "Required — no approved matching record" in text
            else:
                assert "SYNTHETIC QA — CANNOT QUALIFY PRODUCTION DESIGN" in text
                assert result["qualification_evaluation"]["capacity_state"] in text
                if mode == "FULL_TECHNICAL_AUDIT":
                    assert "SYNTHETIC_QA_10" in text
                    assert audit["design_snapshot_digest"] in text.replace(" ", "")
                    assert public["evaluation_digest"] in text.replace(" ", "")
            (output / (filename + ".txt")).write_text(text, encoding="utf-8")
            matrix.append(dict(candidate_sha=sha, platform=platform.platform(), tracked_working_tree_modified=dirty, case=name, mode=mode, file=filename, pages=len(pages), bytes=len(pdf), sha256=hashlib.sha256(pdf).hexdigest().upper(), snapshot_digest=snapshot.digest, evaluation=result["qualification_evaluation"], checks=supported(result)))
            print(f"{filename}: {len(pages)} pages; {result['qualification_evaluation']['capacity_state']}", flush=True)
        assert before == (snapshot.request, snapshot.result, snapshot.input_provenance)
        for kind, payload in (("request", snapshot.request), ("result", snapshot.result), ("provenance", snapshot.input_provenance)):
            (output / (name + "-signed-" + kind + ".json")).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    # Same nonzero-COV source benchmark used by the independent statistical tests.
    # This is QA evidence only; no record is installed and no design is qualified.
    with localcontext() as context:
        context.prec = 80
        deviation = Decimal("0.9").sqrt() * Decimal(1500)
        specimens = specimen_series()
        for i, specimen in enumerate(specimens):
            specimen["test_strength"] = str(Decimal(10000) + (deviation if i < 5 else -deviation))
        benchmark = recompute_statistics(specimens, statistical_protocol("10000", "1500", "0.15"))
        assert not benchmark.blockers
        assert benchmark.phi_p is not None and benchmark.phi_p.quantize(Decimal(".01")) == Decimal(".51")
    metadata = dict(candidate_sha=sha, platform=platform.platform(), scipy=scipy.__version__, numpy=numpy.__version__, connection_quantiles={str(n): str(connection_t(n)) for n in (10,11,20,30,50,100,500)}, asce_reference_synthetic_nonactivating=benchmark.trace(), reports=matrix)
    (output / "DIRECT_F8_PLATFORM_QA.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
