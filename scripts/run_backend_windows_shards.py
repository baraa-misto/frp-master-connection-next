"""Run the complete backend test authority in deterministic concurrent Windows shards.

The hosted Windows runner cannot complete the serial coverage run inside the job's
25-minute ceiling.  This runner collects the canonical pytest node IDs once,
partitions every node exactly once, runs four isolated coverage processes, and
combines their data before enforcing the repository's 100% coverage requirement.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shards", type=int, default=4)
    parser.add_argument("--expected-tests", type=int)
    return parser.parse_args()


def _collect_node_ids() -> list[str]:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        sys.stdout.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        raise SystemExit(completed.returncode)

    node_ids = [line.strip() for line in completed.stdout.splitlines() if "::" in line]
    if not node_ids:
        sys.stdout.write(completed.stdout)
        raise SystemExit("pytest collection produced no test node IDs")
    if len(node_ids) != len(set(node_ids)):
        raise SystemExit("pytest collection produced duplicate node IDs")
    return node_ids


def _assignment_digest(node_ids: list[str]) -> str:
    canonical = "\n".join(node_ids).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest().upper()


def main() -> int:
    args = _parse_args()
    if args.shards < 2:
        raise SystemExit("--shards must be at least 2")

    node_ids = _collect_node_ids()
    if args.expected_tests is not None and len(node_ids) != args.expected_tests:
        raise SystemExit(
            f"expected {args.expected_tests} collected tests, found {len(node_ids)}"
        )

    assignments = [node_ids[index :: args.shards] for index in range(args.shards)]
    assigned = [node_id for shard in assignments for node_id in shard]
    if len(assigned) != len(node_ids) or set(assigned) != set(node_ids):
        raise SystemExit("shard assignment is not an exact partition of collected tests")

    print(f"Collected backend tests: {len(node_ids)}")
    print(f"Canonical node-ID SHA-256: {_assignment_digest(node_ids)}")
    print(f"Shard counts: {[len(shard) for shard in assignments]}")

    with tempfile.TemporaryDirectory(prefix="frp-backend-windows-shards-") as temp_name:
        temp_dir = Path(temp_name)
        processes: list[tuple[int, subprocess.Popen[str], Path]] = []
        for index, shard in enumerate(assignments):
            args_file = temp_dir / f"shard-{index}.txt"
            args_file.write_text("\n".join(shard) + "\n", encoding="utf-8", newline="\n")
            log_file = temp_dir / f"shard-{index}.log"
            environment = os.environ.copy()
            environment["COVERAGE_FILE"] = str(temp_dir / f".coverage.win-shard-{index}")
            environment["PYTHONUNBUFFERED"] = "1"
            log_handle = log_file.open("w", encoding="utf-8", newline="\n")
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    f"@{args_file}",
                    "--cov=frp_master_connection",
                    "--cov-branch",
                    "--cov-report=",
                    "--cov-fail-under=0",
                ],
                env=environment,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
            log_handle.close()
            processes.append((index, process, log_file))

        failed = False
        for index, process, log_file in processes:
            return_code = process.wait()
            print(f"\n===== Windows backend shard {index} (exit {return_code}) =====")
            print(log_file.read_text(encoding="utf-8", errors="replace"), end="")
            failed = failed or return_code != 0
        if failed:
            return 1

        combined = subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "combine",
                "--keep",
                str(temp_dir),
            ],
            check=False,
        )
        if combined.returncode != 0:
            return combined.returncode
        report = subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "report",
                "--show-missing",
                "--fail-under=100",
            ],
            check=False,
        )
        return report.returncode


if __name__ == "__main__":
    raise SystemExit(main())
