"""Framework-independent validation primitives for engineering-domain contracts."""

import re
from dataclasses import dataclass
from enum import Enum, StrEnum

MAX_ENTITY_ID_LENGTH = 128
MAX_LABEL_LENGTH = 256

_ENTITY_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*\Z")


class ValidationCode(StrEnum):
    """Stable machine-readable aggregate validation codes."""

    DUPLICATE_ID = "DUPLICATE_ID"
    DUPLICATE_MATERIAL_REGION_ID = "DUPLICATE_MATERIAL_REGION_ID"
    DUPLICATE_SECTION_ELEMENT_ID = "DUPLICATE_SECTION_ELEMENT_ID"
    DUPLICATE_GLOBAL_ID = "DUPLICATE_GLOBAL_ID"
    INSUFFICIENT_RESOLVED_PARTICIPANTS = "INSUFFICIENT_RESOLVED_PARTICIPANTS"
    INTERFACE_REQUIRED = "INTERFACE_REQUIRED"
    MEMBER_REQUIRED = "MEMBER_REQUIRED"
    MOMENT_CATEGORY_REQUIRES_MOMENT_INTERFACE = "MOMENT_CATEGORY_REQUIRES_MOMENT_INTERFACE"
    INVALID_STANDARD_SECTION_TOPOLOGY = "INVALID_STANDARD_SECTION_TOPOLOGY"
    ORPHAN_MATERIAL_REGION = "ORPHAN_MATERIAL_REGION"
    SHEAR_CATEGORY_MOMENT_INTERFACE = "SHEAR_CATEGORY_MOMENT_INTERFACE"
    ACTION_MEMBER_END_MISMATCH = "ACTION_MEMBER_END_MISMATCH"
    UNRESOLVED_ACTION_MEMBER = "UNRESOLVED_ACTION_MEMBER"
    UNRESOLVED_BOLT_GROUP_INTERFACE = "UNRESOLVED_BOLT_GROUP_INTERFACE"
    UNRESOLVED_FRAME_OWNER = "UNRESOLVED_FRAME_OWNER"
    UNRESOLVED_LOAD_COMBINATION = "UNRESOLVED_LOAD_COMBINATION"
    UNRESOLVED_MATERIAL_REGION = "UNRESOLVED_MATERIAL_REGION"
    UNRESOLVED_PARTICIPANT = "UNRESOLVED_PARTICIPANT"
    UNRESOLVED_REFERENCE_POINT_OWNER = "UNRESOLVED_REFERENCE_POINT_OWNER"
    DUPLICATE_MEMBER_LOAD_COMBINATION_ACTION = "DUPLICATE_MEMBER_LOAD_COMBINATION_ACTION"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One deterministic contract-validation issue."""

    code: ValidationCode
    message: str
    path: str
    related_entity_id: str | None = None

    def __post_init__(self) -> None:
        """Reject malformed issue metadata before it can cross a boundary."""
        require_enum(self.code, ValidationCode, "ValidationIssue.code")
        validate_label(self.message, "ValidationIssue.message")
        validate_label(self.path, "ValidationIssue.path")
        if self.related_entity_id is not None:
            validate_identifier(self.related_entity_id, "ValidationIssue.related_entity_id")


class DomainValidationError(ValueError):
    """Raised when an aggregate is required to be contract-valid but is not."""

    issues: tuple[ValidationIssue, ...]

    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        if not issues:
            raise ValueError("DomainValidationError requires at least one validation issue.")
        self.issues = issues
        summary = "; ".join(f"{issue.code.value} at {issue.path}" for issue in issues)
        super().__init__(f"Contract invalid with {len(issues)} validation issue(s): {summary}")


def validate_identifier(value: object, field_name: str) -> None:
    """Validate a stable, case-sensitive, JSON-safe entity identifier in place."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be nonempty and contain no surrounding whitespace.")
    if len(value) > MAX_ENTITY_ID_LENGTH:
        raise ValueError(f"{field_name} must be at most {MAX_ENTITY_ID_LENGTH} characters.")
    if _ENTITY_ID_PATTERN.fullmatch(value) is None:
        raise ValueError(
            f"{field_name} must start with an ASCII letter or digit and contain only "
            "ASCII letters, digits, hyphens, underscores, periods, or colons."
        )


def validate_label(value: object, field_name: str) -> None:
    """Validate a separate human-readable label without rewriting it."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    if not value.strip():
        raise ValueError(f"{field_name} must be nonempty after trimming.")
    if len(value) > MAX_LABEL_LENGTH:
        raise ValueError(f"{field_name} must be at most {MAX_LABEL_LENGTH} characters.")
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"{field_name} must not contain control characters.")


def require_enum[EnumT: Enum](
    value: object,
    enum_type: type[EnumT],
    field_name: str,
) -> None:
    """Require an actual controlled-vocabulary member rather than an arbitrary string."""
    if not isinstance(value, enum_type):
        raise TypeError(f"{field_name} must be a {enum_type.__name__} value.")


def require_tuple(value: object, field_name: str) -> None:
    """Require an immutable tuple collection without silently coercing caller data."""
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be an immutable tuple.")


def order_issues(issues: list[ValidationIssue]) -> tuple[ValidationIssue, ...]:
    """Return issues in stable logical-path, code, entity, and message order."""
    return tuple(
        sorted(
            issues,
            key=lambda issue: (
                issue.path,
                issue.code.value,
                issue.related_entity_id or "",
                issue.message,
            ),
        )
    )


__all__ = (
    "MAX_ENTITY_ID_LENGTH",
    "MAX_LABEL_LENGTH",
    "DomainValidationError",
    "ValidationCode",
    "ValidationIssue",
)
