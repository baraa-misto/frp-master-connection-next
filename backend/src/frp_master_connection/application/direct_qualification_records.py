"""Framework-independent immutable qualification identity and canonical content."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


def canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def content_digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest().upper()


@dataclass(frozen=True, slots=True)
class ImmutableQualificationRecord:
    """Only a canonical string is retained; callers receive detached trees."""

    canonical: str

    @property
    def data(self) -> dict[str, Any]:
        return dict(json.loads(self.canonical))

    @property
    def digest(self) -> str:
        return str(self.data["digest"])


__all__ = ("ImmutableQualificationRecord", "canonical_json", "content_digest")
