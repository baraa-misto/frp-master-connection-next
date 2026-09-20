"""AST-enforced dependency rules for framework-independent engineering-core packages."""

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

CORE_PACKAGES = (
    "actions",
    "calculation",
    "capabilities",
    "domain",
    "engineering_basis",
    "geometry",
    "topology",
    "units",
)
FORBIDDEN_EXTERNAL = {
    "alembic",
    "fastapi",
    "httpx",
    "psycopg",
    "pydantic",
    "pydantic_settings",
    "sqlalchemy",
    "starlette",
    "uvicorn",
}
FORBIDDEN_OUTER = {"api", "application", "infrastructure", "reporting", "security"}


@dataclass(frozen=True, slots=True)
class ImportViolation:
    """One exact forbidden import location."""

    path: str
    line: int
    statement: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.statement}"


def _resolved_import_from(
    package_root: Path,
    source_file: Path,
    node: ast.ImportFrom,
) -> str:
    relative_path = source_file.relative_to(package_root)
    current_package = [package_root.name, *relative_path.parent.parts]
    if node.level:
        levels_up = node.level - 1
        anchor = current_package[: len(current_package) - levels_up]
    else:
        anchor = []
    module_parts = node.module.split(".") if node.module else []
    return ".".join([*anchor, *module_parts])


def _is_forbidden(module_name: str) -> bool:
    parts = module_name.split(".")
    if parts[0] in FORBIDDEN_EXTERNAL:
        return True
    return len(parts) > 1 and parts[0] == "frp_master_connection" and parts[1] in FORBIDDEN_OUTER


def find_forbidden_imports(package_root: Path) -> list[ImportViolation]:
    """Recursively return exact forbidden imports from engineering-core files."""
    violations: list[ImportViolation] = []
    for core_package in CORE_PACKAGES:
        for source_file in sorted((package_root / core_package).rglob("*.py")):
            tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
            display_path = source_file.relative_to(package_root.parent).as_posix()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if _is_forbidden(alias.name):
                            violations.append(
                                ImportViolation(display_path, node.lineno, f"import {alias.name}")
                            )
                elif isinstance(node, ast.ImportFrom):
                    resolved = _resolved_import_from(package_root, source_file, node)
                    imported_targets = [resolved]
                    imported_targets.extend(
                        f"{resolved}.{alias.name}" for alias in node.names if resolved
                    )
                    if any(_is_forbidden(target) for target in imported_targets):
                        violations.append(
                            ImportViolation(
                                display_path,
                                node.lineno,
                                ast.unparse(node),
                            )
                        )
    return violations


def test_engineering_core_has_no_forbidden_imports() -> None:
    package_root = Path(__file__).parents[1] / "src" / "frp_master_connection"

    violations = find_forbidden_imports(package_root)

    assert not violations, "\n".join(str(violation) for violation in violations)


def test_application_orchestration_imports_only_inward_and_never_frameworks() -> None:
    package_root = Path(__file__).parents[1] / "src" / "frp_master_connection"
    allowed_project_packages = {"actions", "application", "calculation", "domain", "geometry"}
    violations: list[str] = []

    for source_file in sorted((package_root / "application").rglob("*.py")):
        tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = (node.module,)
            else:
                continue
            for name in names:
                parts = name.split(".")
                if parts[0] in FORBIDDEN_EXTERNAL or (
                    len(parts) > 1
                    and parts[0] == "frp_master_connection"
                    and parts[1] not in allowed_project_packages | {"version"}
                ):
                    violations.append(f"{source_file.name}:{node.lineno}:{name}")

    assert violations == []


def test_api_calculation_transport_uses_orchestration_without_direct_equation_access() -> None:
    package_root = Path(__file__).parents[1] / "src" / "frp_master_connection"
    api_root = package_root / "api"
    prohibited_symbols = {
        "calculate_multirow_connection",
        "calculate_single_bolt",
        "bolt_body_area",
        "bolt_tension_resistance",
        "bolt_shear_resistance",
        "combined_bolt_tension_shear_resistance",
        "pull_through_resistance",
        "pin_bearing_resistance",
        "net_tension_resistance",
        "shear_out_resistance",
        "cleavage_resistance",
    }
    violations: list[str] = []
    for source_file in sorted(api_root.glob("*.py")):
        tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = {alias.name for alias in node.names}
                if module.endswith(("calculation.equations", "calculation.evaluation")) or (
                    names & prohibited_symbols
                ):
                    violations.append(f"{source_file.name}:{node.lineno}:{ast.unparse(node)}")

    routes = ast.parse((api_root / "routes.py").read_text(encoding="utf-8"))
    single_bolt_calls = [
        node
        for node in ast.walk(routes)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "evaluate_single_bolt_connection"
    ]
    multirow_design_calls = [
        node
        for node in ast.walk(routes)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "evaluate_multirow_connection"
    ]
    multirow_preview_calls = [
        node
        for node in ast.walk(routes)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "preview_multirow_connection"
    ]
    assert violations == []
    assert len(single_bolt_calls) == 1
    assert len(multirow_design_calls) == 1
    assert len(multirow_preview_calls) == 1


def test_stage_1_3_modules_use_only_standard_library_and_project_imports() -> None:
    package_root = Path(__file__).parents[1] / "src" / "frp_master_connection"
    source_files = (
        *tuple(sorted((package_root / "calculation").glob("*.py"))),
        package_root / "geometry" / "spatial.py",
        package_root / "geometry" / "section.py",
        package_root / "geometry" / "placement.py",
        package_root / "geometry" / "surfaces.py",
        package_root / "geometry" / "interface_targeting.py",
        package_root / "actions" / "transforms.py",
    )
    section_allowed_standard_library_roots = {"dataclasses", "enum", "math"}
    unexpected: list[str] = []

    for source_file in source_files:
        tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                module_names = [alias.name for alias in node.names]
                line_number = node.lineno
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                module_names = [node.module]
                line_number = node.lineno
            else:
                continue
            for module_name in module_names:
                root_name = module_name.partition(".")[0]
                allowed_standard_library = (
                    root_name in section_allowed_standard_library_roots
                    if source_file.name == "section.py"
                    else root_name in sys.stdlib_module_names
                )
                if not allowed_standard_library and root_name != "frp_master_connection":
                    unexpected.append(
                        f"{source_file.relative_to(package_root.parent).as_posix()}:"
                        f"{line_number}: {ast.unparse(node)}"
                    )

    assert unexpected == []


def test_architecture_failure_reports_exact_file_line_and_import(tmp_path: Path) -> None:
    package_root = tmp_path / "frp_master_connection"
    domain_root = package_root / "domain"
    domain_root.mkdir(parents=True)
    source_file = domain_root / "offending.py"
    source_file.write_text(
        "import fastapi\n"
        "import httpx\n"
        "from frp_master_connection.api import app\n"
        "from ..security import TrustedIdentity\n"
        "from frp_master_connection import api\n"
        "from .. import security\n",
        encoding="utf-8",
    )

    violations = [str(violation) for violation in find_forbidden_imports(package_root)]

    assert violations == [
        "frp_master_connection/domain/offending.py:1: import fastapi",
        "frp_master_connection/domain/offending.py:2: import httpx",
        "frp_master_connection/domain/offending.py:3: from frp_master_connection.api import app",
        "frp_master_connection/domain/offending.py:4: from ..security import TrustedIdentity",
        "frp_master_connection/domain/offending.py:5: from frp_master_connection import api",
        "frp_master_connection/domain/offending.py:6: from .. import security",
    ]


@pytest.mark.parametrize(
    "relative_statement",
    ["from .helpers import value", "from ..domain import value"],
)
def test_architecture_allows_relative_core_imports(
    tmp_path: Path,
    relative_statement: str,
) -> None:
    package_root = tmp_path / "frp_master_connection"
    domain_root = package_root / "domain"
    domain_root.mkdir(parents=True)
    (domain_root / "allowed.py").write_text(relative_statement, encoding="utf-8")

    assert find_forbidden_imports(package_root) == []
