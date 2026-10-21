"Account/revision-bound successor workflow exports, using existing signing/storage."

from threading import RLock
from typing import Any

from frp_master_connection.reporting.hyb1_review import request_digest
from frp_master_connection.reporting.snapshot import (
    ReportSnapshotStore,
    SnapshotError,
    SnapshotSigner,
)

FAMILY = "HYB2_D3_P1_CURRENT_CALCULATION"


class HybridStore:
    def __init__(self) -> None:
        self.signer = SnapshotSigner()
        self.store = ReportSnapshotStore()
        self.current: dict[tuple[str, str], tuple[int, str]] = {}
        self.lock = RLock()

    def invalidate(self, account: str, key: str, revision: int) -> None:
        with self.lock:
            old = self.current.get((account, key))
            if old is None or revision > old[0]:
                if old is None and len(self.current) >= 256:
                    raise SnapshotError(
                        "Hybrid workspace limit reached; restart only this isolated "
                        "candidate or reuse a current workspace."
                    )
                self.current[account, key] = (revision, "")
            elif revision < old[0]:
                raise SnapshotError("Superseded hybrid revision.")

    def register(self, account: str, key: str, revision: int, inputs: dict[str, Any]) -> str:
        fingerprint = request_digest(inputs)
        with self.lock:
            self.invalidate(account, key, revision)
            old = self.current[account, key]
            if old[1] and old[1] != fingerprint:
                raise SnapshotError("Changed inputs require a new revision.")
            self.current[account, key] = (revision, fingerprint)
        return fingerprint

    def seal(
        self, account: str, key: str, revision: int, fingerprint: str, record: dict[str, Any]
    ) -> str:
        with self.lock:
            if self.current.get((account, key)) != (revision, fingerprint):
                raise SnapshotError("Late/superseded hybrid result cannot become current.")
            context = record["native_report_context"]
            issued = None if context is None else context["issued_at"]
            token = self.signer.issue(
                family=FAMILY,
                kind="design",
                request={"workspace_id": key, "revision": revision, "fingerprint": fingerprint},
                result=record,
                account_id=account,
                now=issued,
            )
            return self.store.put(token, now=issued)

    def export(self, handle: str, account: str) -> dict[str, Any]:
        snap = self.signer.verify(self.store.get(handle), account_id=account)
        q = snap.request
        with self.lock:
            if snap.family != FAMILY or self.current.get((account, str(q["workspace_id"]))) != (
                q["revision"],
                q["fingerprint"],
            ):
                raise SnapshotError(
                    "Hybrid report is stale or belongs to another report family; recalculate."
                )
            return snap.result
