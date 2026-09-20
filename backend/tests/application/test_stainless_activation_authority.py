"""CME-3 successor dependency direction and exact frozen-source protection."""

import ast
import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2] / "src/frp_master_connection"
FROZEN = {
    "domain/stainless_material.py": (
        "01781d188a8f6ce88b0ea4fa878314888a9fe3ed9a1d38eef6b532c0ad1dbed2"
    ),
    "calculation/stainless_plate.py": (
        "4d65a75e4801db59e9611eda573c888773554446315a951498c0864e2a00d58c"
    ),
    "calculation/stainless_plate_clear_body.py": (
        "b005f3a783559e8c0761c872ee6a395d0a7053c211773a21138b5b8e95c78cc4"
    ),
    "domain/stainless_shape.py": "48842950d4332c401cb370caa2b997e85e24a7be013a66722102e3f5ce56dee4",
    "calculation/stainless_response.py": (
        "4eccca043ba01ae984fc7f773fb85dc2a02105d53695f367aed9386d7da3d35c"
    ),
    "calculation/stainless_angle.py": (
        "87f42e71ba0e40aa8b2fa76bbab0aa12f497b2ccb15d287b6b06cadbed5483fb"
    ),
    "calculation/stainless_tee.py": (
        "4676adb8b27a5d30e6a4fd4114e5ebe5b0feaca5f977e386add9d5cbc3838dd1"
    ),
}
ADAPTERS = {"application/stainless_family_activation.py"}
MODULES = {"frp_master_connection." + p[:-3].replace("/", ".") for p in FROZEN}


def verify_source(path: str, raw: bytes) -> None:
    # These authority pins are canonical LF Git blob bytes from 2e33c562.
    # Universal newline reading only handles the repository's existing checkout
    # conversion; the old expected digest is never replaced by a successor hash.
    assert hashlib.sha256(raw).hexdigest() == FROZEN[path], "frozen C2 source changed"


def verify_imports(path: str, source: str) -> None:
    for node in ast.walk(ast.parse(source)):
        modules = []
        if isinstance(node, ast.Import):
            modules = [item.name for item in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or "", *((node.module or "") + "." + x.name for x in node.names)]
        if path in FROZEN:
            assert not any("stainless_family_activation" in x for x in modules), (
                "reverse dependency"
            )
        elif path not in ADAPTERS:
            assert not any(m in MODULES for m in modules), "unreviewed C2 consumer"
        if path in ADAPTERS:
            assert not any(m == "importlib" or m.startswith("importlib.") for m in modules)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"__import__", "exec", "eval"}


@pytest.mark.parametrize("path", tuple(FROZEN))
def test_frozen_provider_source_is_exact_and_tamper_detected(path: str) -> None:
    source = (ROOT / path).read_text(encoding="utf-8")
    verify_source(path, source.encode("utf-8"))
    with pytest.raises(AssertionError, match="frozen C2 source changed"):
        verify_source(path, (source + "# unauthorized\n").encode())
    verify_imports(path, source)


def test_only_reviewed_adapter_can_consume_c2_and_no_reverse_import_is_allowed() -> None:
    for path in ROOT.rglob("*.py"):
        verify_imports(path.relative_to(ROOT).as_posix(), path.read_text(encoding="utf-8"))
    source = (
        "from frp_master_connection.calculation.stainless_angle import evaluate_stainless_angle"
    )
    verify_imports("application/stainless_family_activation.py", source)
    with pytest.raises(AssertionError, match="unreviewed C2 consumer"):
        verify_imports("application/unrelated_family.py", source)
    with pytest.raises(AssertionError, match="reverse dependency"):
        verify_imports(
            "calculation/stainless_angle.py",
            (
                "from frp_master_connection.application.stainless_family_activation "
                "import canonical_material"
            ),
        )


@pytest.mark.parametrize(
    "source", ["import importlib", "__import__('module')", "exec('code')", "eval('1')"]
)
def test_adapter_dynamic_import_or_runtime_code_bypass_is_rejected(source: str) -> None:
    with pytest.raises(AssertionError):
        verify_imports("application/stainless_family_activation.py", source)
