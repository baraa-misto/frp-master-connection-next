"""Bounded Certifi/Pillow successor compatibility, executed on each CI platform."""
from __future__ import annotations

from hashlib import sha256
from importlib.metadata import version
from io import BytesIO
import json
from pathlib import Path
import ssl
import sys
import urllib.request

import certifi
from PIL import Image, ImageDraw
from pypdf import PdfReader
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from tests.hybrid_workflow_governance import backend_security_authority, pre_d3_backend_dependency


def verify() -> dict[str, object]:
    installed = {name: version(name) for name in ("certifi", "pillow")}
    assert installed == {"certifi": "2026.10.19", "pillow": "13.0.0"}
    governed = backend_security_authority()
    raw = (ROOT / str(governed["file"])).read_bytes()
    assert pre_d3_backend_dependency(raw) != raw
    context = ssl.create_default_context(cafile=certifi.where())
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    tls = []
    for package in ("certifi", "pillow"):
        url = f"https://pypi.org/pypi/{package}/{installed[package]}/json"
        with urllib.request.urlopen(url, context=context, timeout=40) as response:
            data = json.loads(response.read())
            assert response.status == 200 and data["info"]["version"] == installed[package]
        allowed = {row["sha256"] for row in governed["packages"][package]["artifacts"]}
        assert {row["digests"]["sha256"] for row in data["urls"]} == allowed
        filenames = [row["filename"] for row in data["urls"]]
        if package == "pillow":
            assert any("cp314-cp314-win_amd64.whl" in name for name in filenames)
            assert any("cp314-cp314-manylinux" in name and "x86_64" in name for name in filenames)
        else:
            assert any(name.endswith("py3-none-any.whl") for name in filenames)
        tls.append({"url": url, "status": 200, "certifi_CA_validation": True,
                    "published_artifact_hashes_match": True, "windows_ubuntu_CP314_wheels": True})
    image = Image.new("RGBA", (160, 100), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 150, 90), fill=(30, 90, 150, 255))
    draw.ellipse((65, 35, 95, 65), fill=(255, 255, 255, 255))
    original_pixels = image.tobytes()
    formats = []
    for mode in ("PNG", "TIFF"):
        buffer = BytesIO()
        image.save(buffer, format=mode)
        buffer.seek(0)
        with Image.open(buffer) as decoded:
            decoded.load()
            assert decoded.size == image.size and decoded.convert("RGBA").tobytes() == original_pixels
            assert decoded.resize((80, 50), Image.Resampling.LANCZOS).size == (80, 50)
        formats.append(mode)
    png = BytesIO()
    image.save(png, format="PNG")
    document = BytesIO()
    pdf = canvas.Canvas(document, invariant=1)
    pdf.drawString(40, 800, "Pillow 13 compatibility: image and drawing")
    pdf.drawImage(ImageReader(BytesIO(png.getvalue())), 40, 650, width=160, height=100, mask="auto")
    pdf.save()
    reader = PdfReader(BytesIO(document.getvalue()))
    assert len(reader.pages) == 1 and "Pillow 13 compatibility" in reader.pages[0].extract_text()
    embedded = list(reader.pages[0].images)
    assert embedded and embedded[0].image.convert("RGBA").tobytes() == original_pixels
    return {"result": "PASS", "installed_versions": installed,
            "TLS": tls, "certificate_bundle_sha256": sha256(Path(certifi.where()).read_bytes()).hexdigest(),
            "image_round_trip_formats": formats, "RGBA_pixels_preserved": True,
            "resampling": "LANCZOS", "reportlab_image_embedding_and_pypdf_pixel_readback": True,
            "full_connection_report_visual_numerical_QA": "Separate actual platform PDF artifacts and owner-review evidence; this smoke check does not replace them."}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
