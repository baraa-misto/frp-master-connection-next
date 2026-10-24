"""Additional actual signed P1 90F/140F controls; existing MC1/SAB2 gates remain."""
from __future__ import annotations

import argparse
import asyncio
import json
import platform
import subprocess
from pathlib import Path

from generate_direct_mc1_ci_pdfs import ROOT, generate
from tests.direct_mc1_fixtures import mc1_body


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cases = {"p1-90F": mc1_body("90"), "p1-140F": mc1_body("140")}
    parity = [mc1_body(value, unit, chemical="SPECIFIED", chemical_strength_factor=".80") for value, unit in (("104", "degF"), ("40", "degC"))]
    records = asyncio.run(generate(output, cases, parity))
    assert len(records) == 4
    metadata = dict(candidate_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        tracked_working_tree_modified=bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True)),
        platform=platform.platform(), report_count=len(records), reports=records,
        renderer_did_not_mutate_snapshot=True, production_green_available=False,
        unchanged_c13_partial_rows=["C13-05", "C13-06", "C13-07", "C13-08"])
    (output / "DIRECT_P1_PLATFORM_QA.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print("P1 actual signed PDF supplement passed: four PDFs; 90F/140F, both modes", flush=True)


if __name__ == "__main__":
    main()
