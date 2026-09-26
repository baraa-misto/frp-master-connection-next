"""Transient, authenticated REPORT1 calculation snapshots.

The envelope contains bytes returned by the native route after its response model
has validated them. A report verifies this envelope and never accepts a browser
supplied result object as engineering authority.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import zlib
from collections import OrderedDict
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Literal

MAX_SNAPSHOT_JSON_BYTES = 8_000_000
MAX_TOKEN_BYTES = 10_000_000
SNAPSHOT_LIFETIME_SECONDS = 15 * 60
SNAPSHOT_VERSION = "R1"
MAX_STORED_SNAPSHOT_BYTES = 64_000_000


class SnapshotError(ValueError):
    """A report token has no usable server authority."""


@dataclass(frozen=True, slots=True)
class ReportSnapshot:
    family: str
    kind: Literal["design", "input_only"]
    request: dict[str, Any]
    result: dict[str, Any]
    issued_at: int
    digest: str
    input_provenance: dict[str, Any] = field(default_factory=dict)


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _base64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unbase64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class SnapshotSigner:
    """Per-process key by default; deployments may provide a shared server secret."""

    def __init__(self, key: bytes | None = None) -> None:
        self._key = secrets.token_bytes(32) if key is None else key
        if len(self._key) < 32:
            raise ValueError("REPORT1 signing key must contain at least 32 bytes")

    def issue(
        self,
        *,
        family: str,
        kind: Literal["design", "input_only"],
        request: dict[str, Any],
        result: dict[str, Any],
        input_provenance: dict[str, Any] | None = None,
        account_id: str,
        now: int | None = None,
    ) -> str:
        if not family or not account_id:
            raise ValueError("REPORT1 family and trusted account must be present")
        issued = int(time.time()) if now is None else now
        content = {
            "family": family,
            "kind": kind,
            "request": request,
            "result": result,
            "input_provenance": input_provenance or {},
        }
        content_bytes = _canonical_json(content)
        if len(content_bytes) > MAX_SNAPSHOT_JSON_BYTES:
            raise SnapshotError("REPORT1 calculation exceeds the snapshot size limit")
        payload = _canonical_json(
            {
                "content": content,
                "content_sha256": hashlib.sha256(content_bytes).hexdigest(),
                "issued_at": issued,
                "account_id": account_id,
                "version": SNAPSHOT_VERSION,
            }
        )
        packed = _base64(zlib.compress(payload, level=9))
        mac = _base64(hmac.digest(self._key, packed.encode("ascii"), "sha256"))
        token = f"{SNAPSHOT_VERSION}.{packed}.{mac}"
        if len(token) > MAX_TOKEN_BYTES:
            raise SnapshotError("REPORT1 token exceeds the transport size limit")
        return token

    def verify(self, token: str, *, account_id: str, now: int | None = None) -> ReportSnapshot:
        if len(token) > MAX_TOKEN_BYTES:
            raise SnapshotError("REPORT1 token exceeds the transport size limit")
        try:
            version, packed, supplied_mac = token.split(".")
            if version != SNAPSHOT_VERSION:
                raise SnapshotError("REPORT1 token version is unsupported")
            expected_mac = _base64(hmac.digest(self._key, packed.encode("ascii"), "sha256"))
            if not hmac.compare_digest(supplied_mac, expected_mac):
                raise SnapshotError("REPORT1 token authentication failed")
            decompressor = zlib.decompressobj()
            payload_bytes = decompressor.decompress(
                _unbase64(packed), MAX_SNAPSHOT_JSON_BYTES + 1024
            )
            if decompressor.unconsumed_tail or not decompressor.eof:
                raise SnapshotError("REPORT1 snapshot is incomplete or oversized")
            payload = json.loads(payload_bytes)
            content = payload["content"]
            if payload["version"] != SNAPSHOT_VERSION or payload["account_id"] != account_id:
                raise SnapshotError("REPORT1 snapshot identity does not match")
            issued = payload["issued_at"]
            current = int(time.time()) if now is None else now
            if not isinstance(issued, int) or issued > current + 30:
                raise SnapshotError("REPORT1 snapshot time is invalid")
            if current - issued > SNAPSHOT_LIFETIME_SECONDS:
                raise SnapshotError("REPORT1 snapshot expired; run an explicit design check")
            digest = hashlib.sha256(_canonical_json(content)).hexdigest()
            if digest != payload["content_sha256"]:
                raise SnapshotError("REPORT1 snapshot content digest does not match")
            family = content["family"]
            kind = content["kind"]
            request = content["request"]
            result = content["result"]
            input_provenance = content["input_provenance"]
            if (
                not isinstance(family, str)
                or kind not in {"design", "input_only"}
                or not isinstance(request, dict)
                or not isinstance(result, dict)
                or not isinstance(input_provenance, dict)
            ):
                raise SnapshotError("REPORT1 snapshot shape is invalid")
            return ReportSnapshot(family, kind, request, result, issued, digest, input_provenance)
        except (KeyError, TypeError, ValueError, zlib.error) as error:
            if isinstance(error, SnapshotError):
                raise
            raise SnapshotError("REPORT1 token is invalid") from error


class ReportSnapshotStore:
    """Bounded transient handles to exact signed responses on one service process."""

    def __init__(self) -> None:
        self._entries: OrderedDict[str, tuple[int, str]] = OrderedDict()
        self._size = 0
        self._lock = RLock()

    def put(self, token: str, *, now: int | None = None) -> str:
        issued = int(time.time()) if now is None else now
        if len(token) > MAX_STORED_SNAPSHOT_BYTES:
            raise SnapshotError("REPORT1 snapshot exceeds transient storage capacity")
        with self._lock:
            self._prune(issued)
            while self._entries and self._size + len(token) > MAX_STORED_SNAPSHOT_BYTES:
                _, (_, removed) = self._entries.popitem(last=False)
                self._size -= len(removed)
            handle = secrets.token_urlsafe(24)
            self._entries[handle] = (issued + SNAPSHOT_LIFETIME_SECONDS, token)
            self._size += len(token)
            return handle

    def get(self, handle: str, *, now: int | None = None) -> str:
        current = int(time.time()) if now is None else now
        with self._lock:
            self._prune(current)
            entry = self._entries.get(handle)
            if entry is None:
                raise SnapshotError("REPORT1 snapshot is unavailable; run an explicit design check")
            return entry[1]

    def _prune(self, current: int) -> None:
        for handle, (expiry, token) in tuple(self._entries.items()):
            if expiry <= current:
                del self._entries[handle]
                self._size -= len(token)
