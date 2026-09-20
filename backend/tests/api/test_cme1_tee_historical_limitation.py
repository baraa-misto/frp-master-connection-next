"""Owner-accepted historical invalid startup; never weaken native geometry guards."""

import hashlib
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
from tests.api.test_connector_materials import SS, envelope, http

from frp_master_connection.api.connector_materials import capabilities

ROOT = Path(__file__).parents[3]
TAG = "stage-3.2-tee-connection-freeze"
TARGET = "d16b354732c90bf3bf7847c62be652c230a9f91e"
MESSAGE = "Each connected-profile bolt path must select one finite opposing broad face."
PAYLOADS = {
    "historical": "E3D534451545A674A268B237F53AEE63E646EFD61E3BD794BEDD3AE7889073A8",
    "current": "F4C13BBF549D93A804A82B02195A2D897F90BDD10E056CADF410D45839F6D363",
}


def payload(name: str) -> dict[str, object]:
    path = ROOT / f"backend/tests/golden/cme1_tee_{name}_startup.json"
    # Derived JSON is ordinary Git-normalized test data, not an original controlled file.
    raw = path.read_text(encoding="utf-8").encode()
    assert hashlib.sha256(raw).hexdigest().upper() == PAYLOADS[name]
    value: dict[str, object] = json.loads(raw)
    return value


@pytest.mark.parametrize("name", tuple(PAYLOADS))
def test_historical_and_current_startups_preserve_native_422(name: str) -> None:
    value = payload(name)
    response = http("POST", "/api/v1/calculations/tee-connector/preview", value)
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "CANONICAL_TEE_MAPPING_INVALID",
        "message": MESSAGE,
    }
    plan = envelope("tee-connector")
    plan.update(native_input=value, apply_all=SS)
    rejected = http("POST", "/api/v1/connector-materials/plan", plan)
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["message"] == MESSAGE
    assert "capacity" not in rejected.text


def test_inventory_does_not_claim_invalid_default_is_ready_and_valid_fixture_still_works() -> None:
    rows = capabilities()["families"]
    assert isinstance(rows, list)
    assert any(isinstance(row, dict) and row["route_id"] == "tee-connector" for row in rows)
    assert capabilities()["SS316"] == "STAINLESS_CONDITIONAL_PROVIDER_AVAILABLE"
    # Existing accepted flat-plate benchmark, not an invented replacement startup.
    valid = envelope("tee-connector")
    assert (
        http(
            "POST", "/api/v1/calculations/tee-connector/preview", valid["native_input"]
        ).status_code
        == 200
    )
    assert http("POST", "/api/v1/connector-materials/plan", valid).status_code == 200


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=ROOT,
        check=check,
        capture_output=True,
    )


def test_frozen_oracle_when_present_and_explicit_offline_manifest_provenance(
    tmp_path: Path,
) -> None:
    manifest_raw = (
        ROOT / "docs/governance/STAGE_3_2_TEE_CONNECTION_FREEZE_MANIFEST.json"
    ).read_bytes()
    assert (
        hashlib.sha256(manifest_raw).hexdigest().upper()
        == "25A244EBFBC3AC7990B45657025FD6A1FD0C59544BE2ECB13738DFBCC34C9E7E"
    )
    assert (
        json.loads(manifest_raw)["source_trees"]["frontend_src"]
        == "fbbf52fa5ad719a6f3e434a19df74c236cd25dfb"
    )
    payload("historical")
    exists = git("rev-parse", "--verify", f"refs/tags/{TAG}^{{commit}}", check=False)
    if exists.returncode:
        # No hidden fetch in depth-one QA. Historical execution evidence is in the
        # owner-approved B report; offline mode proves its pinned request/manifest.
        assert not git("tag", "--list", TAG).stdout.strip()
        return
    assert exists.stdout.decode().strip() == TARGET
    assert (
        git("rev-parse", f"{TAG}:frontend/src").stdout.decode().strip()
        == "fbbf52fa5ad719a6f3e434a19df74c236cd25dfb"
    )
    with tarfile.open(fileobj=io.BytesIO(git("archive", TAG, "backend/src").stdout)) as archive:
        archive.extractall(tmp_path, filter="data")
    script = (
        "import sys,json;sys.path.insert(0,sys.argv[1]);"
        "from fastapi.testclient import TestClient;"
        "from frp_master_connection.api.app import create_app;"
        "r=TestClient(create_app()).post('/api/v1/calculations/tee-connector/preview',json=json.loads(sys.argv[2]));"
        "print(json.dumps({'status':r.status_code,'body':r.json()}))"
    )
    executed = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            script,
            str(tmp_path / "backend/src"),
            json.dumps(payload("historical")),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(executed.stdout)
    assert result == {
        "status": 422,
        "body": {"detail": {"code": "CANONICAL_TEE_MAPPING_INVALID", "message": MESSAGE}},
    }
