"""Offline engineering-admin validator. Approval is supplied evidence, never inferred."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

from frp_master_connection.application.direct_qualification_statistics import recompute_statistics
from frp_master_connection.infrastructure.direct_qualification_records import (
    ProviderIndex,
    canonical_record,
    evidence_blockers,
)


def validate_package(package: Path, output: Path) -> int:
    """Write a validation receipt and, only if complete, an exclusive immutable file."""
    payload = json.loads(package.read_text(encoding="utf-8"))
    record = canonical_record(payload)
    blockers = evidence_blockers(record, package.parent)
    data = record.data
    receipt = {
        "qualification_record_id": data["qualification_record_id"],
        "revision": data["revision"],
        "record_digest": record.digest,
        "configured_status": data["status"],
        "blockers": list(blockers),
        "statistics": recompute_statistics(data["specimens"], data["statistical_protocol"]).trace(),
        "professional_seal_validation": (
            "NOT_PERFORMED; controlled metadata and document bytes only"
        ),
        "canonical_record": data,
    }
    output.mkdir(parents=True, exist_ok=True)
    receipt_name = f"{data['qualification_record_id']}.r{data['revision']}.validation-receipt.json"
    with (output / receipt_name).open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
    if not blockers:
        name = (
            f"{data['qualification_record_id']}.r{data['revision']}."
            f"{record.digest}.qualification.json"
        )
        with (output / name).open("x", encoding="utf-8") as stream:
            stream.write(record.canonical)
        for document in data["source_documents"]:
            source = package.parent / document["package_file"]
            target = output / document["package_file"]
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                with target.open("xb") as stream:
                    stream.write(source.read_bytes())
            elif target.read_bytes() != source.read_bytes():
                raise ValueError("INSTALLED_EVIDENCE_DOCUMENT_IMMUTABLE_BYTES_CONFLICT")
        index_path = output / "catalog.qualification-index.json"
        index = (
            ProviderIndex.model_validate(json.loads(index_path.read_text(encoding="utf-8")))
            if index_path.exists()
            else ProviderIndex(contract="DIRECT-QUALIFICATION-INDEX-F8", generation=1, entries=())
        )
        updated = {
            "contract": index.contract,
            "generation": index.generation + 1,
            "entries": [
                *(entry.model_dump() for entry in index.entries),
                {
                    "filename": name,
                    "file_sha256": hashlib.sha256(record.canonical.encode()).hexdigest().upper(),
                },
            ],
        }
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output, delete=False
        ) as temporary:
            json.dump(updated, temporary, sort_keys=True)
            temporary_path = Path(temporary.name)
        temporary_path.replace(index_path)
    return 1 if blockers else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate_package(args.package.resolve(), args.output.resolve())
    except (OSError, ValueError) as error:
        sys.stderr.write(f"Qualification package invalid: {error}\n")
        result = 2
    raise SystemExit(result)


if __name__ == "__main__":
    main()
