"""Server-owned D2 sources and short-lived exports; no public-route integration."""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from threading import RLock
from typing import Any, cast

from frp_master_connection.application.hyb1_contract import PairedActions
from frp_master_connection.application.hyb1_review import NativeCapture
from frp_master_connection.application.hyb2_d2 import (
    DEFAULT_CONDITIONS,
    DEFAULT_HARDWARE,
    D2Assessment,
    HardwareEvidence,
    SourceConditions,
    assess_d2,
)
from frp_master_connection.calculation.rhm_direct_r3 import R3Geometry
from frp_master_connection.reporting.hyb1_review import capture_signed_native
from frp_master_connection.reporting.snapshot import (
    ReportSnapshotStore,
    SnapshotError,
    SnapshotSigner,
)


@dataclass(frozen=True, slots=True)
class ReviewSource:
    actions: PairedActions
    geometry: R3Geometry | None = None
    conditions: SourceConditions = DEFAULT_CONDITIONS
    hardware: HardwareEvidence = DEFAULT_HARDWARE
    native_token: str = ""
    native_case_id: str = ""

    @property
    def fingerprint(self) -> str:
        # Ephemeral signature bytes are not physical inputs. The native result has
        # its own verified payload digest; every registration still advances revision.
        operands = (
            self.actions,
            self.geometry,
            self.conditions,
            self.hardware,
            bool(self.native_token),
            self.native_case_id,
        )
        return sha256(repr(operands).encode()).hexdigest()


def assessment_record(
    result: D2Assessment, source: ReviewSource, native_payload: bytes
) -> dict[str, Any]:
    """Sanitized complete machine/audit record; raw handles, accounts and signatures omitted."""
    if sha256(native_payload).hexdigest() != result.native_payload_sha256:
        raise ValueError("Native audit payload does not match its assessed identity.")
    actions = asdict(source.actions)
    actions["identity"]["account"] = "REDACTED_ACCOUNT_BOUND"
    parsed = json.loads(
        json.dumps(
            {
                "title": "Direct hybrid - engineering adoption review",
                "assessment": asdict(result),
                "actions": actions,
                "source_conditions": asdict(source.conditions),
                "hardware_evidence": asdict(source.hardware),
                "source_fingerprint": source.fingerprint,
                "qualification": result.qualification,
                "authority": "REVIEW_ONLY_NO_ADOPTION_GRANTED",
                "native_result": json.loads(native_payload),
            },
            default=str,
        )
    )
    return cast(dict[str, Any], parsed)


class D2ReviewService:
    """Only trusted server code registers inputs; no HTTP source/approval upload exists.

    Native capture reuses the existing authenticated snapshot verifier. Calculations
    commit only if the registered revision is still current after computation.
    """

    def __init__(self, native_signer: SnapshotSigner) -> None:
        self._native_signer = native_signer
        self._signer = SnapshotSigner()
        self._store = ReportSnapshotStore()
        self._sources: dict[str, tuple[int, ReviewSource]] = {}
        self._lock = RLock()

    def register(self, key: str, source: ReviewSource) -> int:
        if not key or len(key) > 100:
            raise ValueError("Bounded nonempty review case key required.")
        with self._lock:
            revision = self._sources[key][0] + 1 if key in self._sources else 1
            self._sources[key] = (revision, source)
            return revision

    def _current(self, key: str, revision: int, account: str) -> ReviewSource:
        entry = self._sources.get(key)
        if entry is None or entry[1].actions.identity.account != account:
            raise SnapshotError("Review source is unavailable for this authenticated account.")
        if revision != entry[0]:
            raise SnapshotError(
                "Review source is stale; select the current revision and recalculate."
            )
        return entry[1]

    def calculate(self, key: str, revision: int, account: str) -> tuple[str, dict[str, Any]]:
        with self._lock:
            source = self._current(key, revision, account)
        actions = source.actions
        if source.native_token:
            native = capture_signed_native(
                self._native_signer, source.native_token, actions, source.native_case_id
            )
        else:
            payload = b'{"native_authority":"NOT_SUPPLIED_NO_RESULTS_INFERRED"}'
            native = NativeCapture(
                actions.identity,
                actions.digest,
                payload,
                sha256(payload).hexdigest(),
                (),
                "NO_NATIVE_ASCE",
                "SERVER_SOURCE_REFERENCE_ONLY",
            )
        result = assess_d2(
            actions,
            native,
            geometry=source.geometry,
            conditions=source.conditions,
            hardware=source.hardware,
            today=datetime.now(UTC).date(),
        )
        record = assessment_record(result, source, native.immutable_payload)
        with self._lock:
            # Registration always increments the revision under this same lock.
            # The frozen source cannot change while retaining this revision.
            self._current(key, revision, account)
            token = self._signer.issue(
                family="HYB2_D2_ISOLATED_REVIEW",
                kind="design",
                request={
                    "case_key": key,
                    "revision": revision,
                    "fingerprint": source.fingerprint,
                    "assessment_date": datetime.now(UTC).date().isoformat(),
                },
                result=record,
                account_id=account,
            )
            return self._store.put(token), record

    def export_record(self, handle: str, account: str) -> dict[str, Any]:
        snapshot = self._signer.verify(self._store.get(handle), account_id=account)
        request = snapshot.request
        with self._lock:
            source = self._current(str(request["case_key"]), int(request["revision"]), account)
            if request["fingerprint"] != source.fingerprint or request["assessment_date"] != (
                datetime.now(UTC).date().isoformat()
            ):
                raise SnapshotError("Review evidence/date changed; recalculate before export.")
            if source.native_token:
                self._native_signer.verify(source.native_token, account_id=account)
            return snapshot.result
