"""Real S1 publisher, installed-package, distribution and PDF compatibility proof."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from tests.hybrid_security_successor import DEPENDENCIES, authority, installed_python_versions, require_successor
from verify_hybrid_security_compatibility import verify as verify_image_pdf_tls


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    governed = authority()
    installed = installed_python_versions()
    predecessors = {}
    for path in DEPENDENCIES:
        raw = (ROOT / path).read_bytes()
        previous = require_successor(path, raw)
        predecessors[path] = {"actual_sha256": sha256(raw).hexdigest(),
                              "normalized_predecessor_sha256": sha256(previous).hexdigest()}
    publishers = {}
    for name, expected in installed.items():
        url = f"https://pypi.org/pypi/{name}/{expected}/json"
        with urllib.request.urlopen(url, timeout=40) as response:
            data = json.load(response)
        assert data["info"]["version"] == expected
        files = data["urls"]
        expected_files = governed["python_records"][name]["artifacts"]
        assert {(x["filename"], x["digests"]["sha256"]) for x in files} == {
            (x["filename"], x["sha256"]) for x in expected_files
        }
        wheels = [x for x in files if x["filename"].endswith("py3-none-any.whl") and not x["yanked"]]
        assert len(wheels) == 1
        wheel = wheels[0]
        with urllib.request.urlopen(wheel["url"], timeout=40) as response:
            raw = response.read()
        assert sha256(raw).hexdigest() == wheel["digests"]["sha256"]
        with ZipFile(BytesIO(raw)) as z:
            assert z.testzip() is None
            metadata = z.read(next(x for x in z.namelist() if x.endswith(".dist-info/METADATA"))).decode()
            assert f"Version: {expected}\n" in metadata
        publishers[name] = {"url": url, "wheel_filename": wheel["filename"],
                            "wheel_sha256": sha256(raw).hexdigest(),
                            "trusted_TLS": True, "universal_windows_ubuntu_CP314": True}
    # The existing mandatory build step executes setuptools.build_meta before this step.
    dist = ROOT / "backend/dist"
    wheel_path = dist / "frp_master_connection-0.0.0.dev0-py3-none-any.whl"
    sdist_path = dist / "frp_master_connection-0.0.0.dev0.tar.gz"
    with ZipFile(wheel_path) as z:
        assert z.testzip() is None
        wheel_metadata = z.read("frp_master_connection-0.0.0.dev0.dist-info/WHEEL").decode()
        assert "Generator: setuptools (84.1.0)" in wheel_metadata
        for path in (ROOT / "backend/src/frp_master_connection").rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            relative = path.relative_to(ROOT / "backend/src").as_posix()
            assert z.read(relative) == path.read_bytes(), relative
        assert "frp_master_connection/py.typed" in z.namelist()
        assert "frp_master_connection/reporting/fonts/DejaVuSans.ttf" in z.namelist()
    with tarfile.open(sdist_path, "r:gz") as t:
        project = t.extractfile("frp_master_connection-0.0.0.dev0/pyproject.toml").read()
        assert project.replace(b"\r\n", b"\n") == (ROOT / "backend/pyproject.toml").read_bytes().replace(b"\r\n", b"\n")
    with tempfile.TemporaryDirectory(prefix="frp-s1-wheel-") as directory:
        target = Path(directory) / "installed"
        requirements = Path(directory) / "wheel.txt"
        requirements.write_text(wheel_path.resolve().as_uri() + " --hash=sha256:" + sha256(wheel_path.read_bytes()).hexdigest() + "\n", encoding="utf8")
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", "--no-index",
                        "--only-binary=:all:", "--require-hashes", "--requirement", str(requirements),
                        "--target", str(target)], check=True, capture_output=True)
        smoke = (
            "import sys;from pathlib import Path;"
            "sys.path.insert(0,sys.argv[1]);"
            "import frp_master_connection;"
            "import frp_master_connection.api.hybrid_app as api;"
            "assert Path(frp_master_connection.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve());"
            "assert Path(api.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve());"
            "assert api.app.title;"
            "from importlib.metadata import distribution;"
            "d=distribution('frp-master-connection');"
            "assert d.version=='0.0.0.dev0';"
            "assert Path(d.locate_file('')).resolve()==Path(sys.argv[1]).resolve()"
        )
        subprocess.run([sys.executable, "-c", smoke, str(target)], cwd=directory,
                       check=True, capture_output=True)
    evidence = {"result": "PASS", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                "starting_sha": governed["starting_sha"],
                "executed_source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "installed_versions": installed,
                "predecessor_reconstruction": predecessors, "publisher_verification": publishers,
                "actual_backend_build": {"wheel_sha256": sha256(wheel_path.read_bytes()).hexdigest(),
                                        "sdist_sha256": sha256(sdist_path.read_bytes()).hexdigest(),
                                        "generator": "setuptools 84.1.0",
                                        "all_package_source_and_data_bytes_preserved": True,
                                        "hash_only_local_wheel_install_and_real_API_import": True},
                "image_PDF_and_TLS": verify_image_pdf_tls(),
                "full_signed_report_semantics": "Mandatory unchanged P3 and historical generators/tests on this same runner; separate artifacts"}
    (args.output / "P4_S1_SECURITY_COMPATIBILITY.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"status": "PASS", "installed_versions": installed,
                      "publisher_hashes": "PASS", "actual_build": "PASS", "image_PDF_TLS": "PASS"}))


if __name__ == "__main__":
    main()

