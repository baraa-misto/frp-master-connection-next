"""Immutable review-only paired actions; no load generator or basis conversion."""

from dataclasses import dataclass
from decimal import localcontext
from enum import StrEnum
from hashlib import sha256

from frp_master_connection.calculation.quantities import (
    PhysicalQuantity,
    Unit,
    canonical_decimal_string,
)


class ActionBasis(StrEnum):
    LRFD = "LRFD"
    ASD = "ASD"


class Alignment(StrEnum):
    BRACE = "BRACE"
    SUPPORT = "SUPPORT"


@dataclass(frozen=True, slots=True)
class PhysicalIdentity:
    account: str
    connection: str
    geometry: str
    material: str
    actions: str
    alignment: Alignment

    def __post_init__(self) -> None:
        if not all((self.account, self.connection, self.geometry, self.material, self.actions)):
            raise ValueError("All physical, account and action-set identities are required.")
        if not isinstance(self.alignment, Alignment):
            raise TypeError("Alignment must retain its governed identity.")


@dataclass(frozen=True, slots=True)
class ActionCase:
    basis: ActionBasis
    case_id: str
    source_id: str
    scenario_family: str
    frame: str
    reference: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity]
    components: tuple[
        PhysicalQuantity | None,
        PhysicalQuantity | None,
        PhysicalQuantity | None,
        PhysicalQuantity | None,
        PhysicalQuantity | None,
        PhysicalQuantity | None,
    ]

    def __post_init__(self) -> None:
        if not isinstance(self.basis, ActionBasis):
            raise TypeError("Independent LRFD/ASD basis is mandatory.")
        if not all((self.case_id, self.source_id, self.scenario_family, self.frame)):
            raise ValueError("Case/source/scenario/frame identities are mandatory.")
        if len(self.components) != 6 or len(self.reference) != 3:
            raise ValueError("Retain all three forces, three moments and reference coordinates.")
        for coordinate in self.reference:
            coordinate.to(Unit.MM)
        for index, value in enumerate(self.components):
            if value is not None:
                value.to(Unit.N if index < 3 else Unit.N_MM)

    @property
    def complete(self) -> bool:
        return all(value is not None for value in self.components)

    @property
    def digest(self) -> str:
        content = (
            self.basis,
            self.case_id,
            self.source_id,
            self.scenario_family,
            self.frame,
            tuple(canonical_decimal_string(q.to(Unit.MM).magnitude) for q in self.reference),
            tuple(
                None
                if q is None
                else canonical_decimal_string(q.to(Unit.N if i < 3 else Unit.N_MM).magnitude)
                for i, q in enumerate(self.components)
            ),
        )
        return sha256(repr(content).encode()).hexdigest()

    def transport(
        self,
        reference: tuple[PhysicalQuantity, PhysicalQuantity, PhysicalQuantity],
        *,
        frame: str,
    ) -> ActionCase:
        """M_new=M_old+(old-new) cross F, same frame; never discard a component."""
        if frame != self.frame or not self.complete:
            raise ValueError("Reference transport needs known actions in the same explicit frame.")
        with localcontext() as context:
            context.prec = 100
            forces = tuple(q.to(Unit.N).magnitude for q in self.components[:3] if q is not None)
            moments = tuple(q.to(Unit.N_MM).magnitude for q in self.components[3:] if q is not None)
            delta = tuple(
                a.to(Unit.MM).magnitude - b.to(Unit.MM).magnitude
                for a, b in zip(self.reference, reference, strict=True)
            )
            cross = (
                delta[1] * forces[2] - delta[2] * forces[1],
                delta[2] * forces[0] - delta[0] * forces[2],
                delta[0] * forces[1] - delta[1] * forces[0],
            )
            result = tuple(PhysicalQuantity.of(x, Unit.N) for x in forces) + tuple(
                PhysicalQuantity.of(m + c, Unit.N_MM) for m, c in zip(moments, cross, strict=True)
            )
        return ActionCase(
            self.basis,
            self.case_id,
            self.source_id,
            self.scenario_family,
            frame,
            reference,
            (result[0], result[1], result[2], result[3], result[4], result[5]),
        )


@dataclass(frozen=True, slots=True)
class CaseManifest:
    required_lrfd: tuple[str, ...]
    required_asd: tuple[str, ...]
    lrfd_declared_complete: bool
    asd_declared_complete: bool
    declaration_source: str

    def __post_init__(self) -> None:
        if not self.declaration_source:
            raise ValueError("Combination completeness declaration needs its provenance.")
        for cases in (self.required_lrfd, self.required_asd):
            if len(cases) != len(set(cases)) or any(not key for key in cases):
                raise ValueError("Required case identities must be unique and nonempty.")


@dataclass(frozen=True, slots=True)
class PairedActions:
    identity: PhysicalIdentity
    lrfd: tuple[ActionCase, ...]
    asd: tuple[ActionCase, ...]
    manifest: CaseManifest
    transport_trace: tuple[ActionCase, ...] = ()

    def __post_init__(self) -> None:
        for basis, cases in ((ActionBasis.LRFD, self.lrfd), (ActionBasis.ASD, self.asd)):
            if any(case.basis is not basis for case in cases):
                raise ValueError("Case entered in the wrong basis; basis conversion is prohibited.")
            if len(cases) != len({case.case_id for case in cases}):
                raise ValueError("Duplicate combination identity.")
        if len({case.scenario_family for case in (*self.lrfd, *self.asd)}) > 1:
            raise ValueError("Both sets must describe one declared physical scenario family.")
        for original in self.transport_trace:
            mapped = next(
                (
                    case
                    for case in (*self.lrfd, *self.asd)
                    if case.basis is original.basis and case.case_id == original.case_id
                ),
                None,
            )
            if mapped is None or mapped.source_id != original.source_id:
                raise ValueError(
                    "Transport audit must retain its original combination/source identity."
                )
            if (
                original.transport(mapped.reference, frame=mapped.frame).components
                != mapped.components
            ):
                raise ValueError("Transport audit disagrees with the retained full action vector.")

    @property
    def complete(self) -> bool:
        return (
            self.manifest.lrfd_declared_complete
            and self.manifest.asd_declared_complete
            and bool(self.manifest.required_lrfd)
            and bool(self.manifest.required_asd)
            and set(self.manifest.required_lrfd) == {c.case_id for c in self.lrfd}
            and set(self.manifest.required_asd) == {c.case_id for c in self.asd}
            and all(c.complete for c in (*self.lrfd, *self.asd))
        )

    @property
    def digest(self) -> str:
        return sha256(
            repr(
                (
                    self.identity,
                    self.manifest,
                    tuple(c.digest for c in (*self.lrfd, *self.asd, *self.transport_trace)),
                )
            ).encode()
        ).hexdigest()
