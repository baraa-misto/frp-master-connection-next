"""Verify exact installed security/statistical pins and audit every locked package."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from importlib.metadata import distributions, version
import json
from pathlib import Path
import re
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from tests.direct_f8_g1_governance import authority, f7_lock, pre_g1_bootstrap, pre_g1_workflow

from tests.direct_f9_governance import pre_f9_workflow


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    installed = {name: version(name) for name in ("Mako", "pip", "scipy", "numpy")}
    assert installed == {"Mako": "1.4.2", "pip": "26.2", "scipy": "1.18.1", "numpy": "2.5.3"} or installed == {"Mako": "1.4.2", "pip": "26.2.0", "scipy": "1.18.1", "numpy": "2.5.3"}
    for name in ("mako", "pip"):
        copies = [item.version for item in distributions() if item.metadata["Name"].lower() == name]
        assert len(copies) == 1
    lock = (ROOT / "backend/requirements/requirements-dev-py314.lock.txt").read_bytes()
    f7_lock(lock)
    pre_g1_workflow(pre_f9_workflow((ROOT / ".github/workflows/ci.yml").read_bytes()))
    pre_g1_bootstrap((ROOT / "scripts/backend-bootstrap.ps1").read_bytes())
    packages = re.findall(r"(?m)^([a-z][a-z0-9-]+)==([^ \\\n]+)", lock.decode())
    payload = {"queries": [{"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v in packages]}
    response = None
    for attempt in range(3):
        try:
            request = urllib.request.Request("https://api.osv.dev/v1/querybatch", json.dumps(payload).encode(), {"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=45) as http:
                response = json.loads(http.read())
            break
        except (OSError, ValueError):
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    assert response is not None and len(response["results"]) == len(packages)
    findings = [{"package": n, "version": v, "advisories": r["vulns"]} for (n, v), r in zip(packages, response["results"], strict=True) if r.get("vulns")]
    evidence = {"queried_at_utc": datetime.now(timezone.utc).isoformat(), "source": "https://api.osv.dev/v1/querybatch", "installed_versions": installed, "pip_authorized_pin": "26.2.0", "pip_published_metadata": "26.2", "pip_version_identity": "PEP440 zero-patch equality; exact hash-locked release", "packages": [{"name": n, "version": v} for n, v in packages], "result": response, "findings": findings, "status": "PASS" if not findings else "UNRESOLVED", "governance": "Exact reverse security successors and F8 additions restore accepted F7 lock", "direct_added": authority()["direct_added"], "transitive_added": authority()["transitive_added"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({"installed_versions": installed, "authorized_pip": "26.2.0", "all_locked_packages": len(packages), "unresolved_findings": len(findings), "status": evidence["status"]}, indent=2), flush=True)
    assert not findings, "STOP: full backend dependency audit is not clean"


if __name__ == "__main__":
    main()
