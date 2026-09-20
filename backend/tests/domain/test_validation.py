"""Tests for stable validation metadata and primitive guards."""

from dataclasses import FrozenInstanceError

import pytest

from frp_master_connection.domain import (
    DomainValidationError,
    ValidationCode,
    ValidationIssue,
)
from frp_master_connection.domain.validation import (
    MAX_ENTITY_ID_LENGTH,
    MAX_LABEL_LENGTH,
    order_issues,
    require_enum,
    require_tuple,
    validate_identifier,
    validate_label,
)


def test_validation_issue_is_immutable_and_domain_error_preserves_issues() -> None:
    issue = ValidationIssue(
        ValidationCode.MEMBER_REQUIRED,
        "A member is required.",
        "members",
        "member-1",
    )

    with pytest.raises(FrozenInstanceError):
        issue.path = "changed"  # type: ignore[misc]
    error = DomainValidationError((issue,))

    assert error.issues == (issue,)
    assert str(error) == "Contract invalid with 1 validation issue(s): MEMBER_REQUIRED at members"


def test_validation_issue_accepts_no_related_entity_and_orders_deterministically() -> None:
    later = ValidationIssue(ValidationCode.MEMBER_REQUIRED, "Later", "z")
    with_related = ValidationIssue(ValidationCode.DUPLICATE_ID, "Second", "a", "entity-2")
    without_related = ValidationIssue(ValidationCode.DUPLICATE_ID, "First", "a")

    assert order_issues([later, with_related, without_related]) == (
        without_related,
        with_related,
        later,
    )


def test_domain_validation_error_rejects_empty_issue_tuple() -> None:
    with pytest.raises(ValueError, match="at least one"):
        DomainValidationError(())


@pytest.mark.parametrize(
    ("value", "expected_exception"),
    [
        (None, TypeError),
        ("", ValueError),
        (" surrounded ", ValueError),
        ("a" * (MAX_ENTITY_ID_LENGTH + 1), ValueError),
        ("bad/id", ValueError),
    ],
)
def test_identifier_validation_rejects_noncanonical_values(
    value: object,
    expected_exception: type[Exception],
) -> None:
    with pytest.raises(expected_exception):
        validate_identifier(value, "field")


def test_identifier_validation_accepts_documented_ascii_alphabet() -> None:
    validate_identifier("A0-b_c.d:e", "field")


@pytest.mark.parametrize(
    ("value", "expected_exception"),
    [
        (None, TypeError),
        ("   ", ValueError),
        ("a" * (MAX_LABEL_LENGTH + 1), ValueError),
        ("line\nbreak", ValueError),
    ],
)
def test_label_validation_rejects_invalid_values(
    value: object,
    expected_exception: type[Exception],
) -> None:
    with pytest.raises(expected_exception):
        validate_label(value, "field")


def test_label_and_helper_guards_accept_valid_values() -> None:
    validate_label("Human-readable label", "field")
    require_enum(ValidationCode.DUPLICATE_ID, ValidationCode, "code")
    require_tuple(("immutable",), "values")


def test_enum_and_tuple_helpers_reject_wrong_runtime_types() -> None:
    with pytest.raises(TypeError, match="ValidationCode"):
        require_enum("DUPLICATE_ID", ValidationCode, "code")
    with pytest.raises(TypeError, match="immutable tuple"):
        require_tuple(["mutable"], "values")


@pytest.mark.parametrize(
    "arguments",
    [
        ("MEMBER_REQUIRED", "message", "path", None),
        (ValidationCode.MEMBER_REQUIRED, "", "path", None),
        (ValidationCode.MEMBER_REQUIRED, "message", "", None),
        (ValidationCode.MEMBER_REQUIRED, "message", "path", "bad/id"),
    ],
)
def test_validation_issue_rejects_invalid_metadata(arguments: tuple[object, ...]) -> None:
    with pytest.raises((TypeError, ValueError)):
        ValidationIssue(*arguments)  # type: ignore[arg-type]
