"""SSMC approved numerical oracles; independent of the new geometry builder."""

import hashlib
import json
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

from frp_master_connection.application.ssmc import vector
from frp_master_connection.calculation.angle_connector_core import (
    AngleWrench,
    exact_decimal,
    shift_angle_wrench,
)
from frp_master_connection.calculation.eccentric_demand import ExactQuantityVector3D
from frp_master_connection.calculation.in_plane_wrench_demand import (
    InPlaneWrenchRequest,
    WrenchBolt,
    calculate_in_plane_wrench_demand,
)
from frp_master_connection.calculation.quantities import Unit

GOLDEN = Path(__file__).parents[1] / "golden/SSMC_2_GOLDEN_BENCHMARKS_RC1.json"
DATA = json.loads(GOLDEN.read_bytes())


def test_approved_ssmc_golden_identity_and_complete_case_counts() -> None:
    assert (
        hashlib.sha256(GOLDEN.read_bytes()).hexdigest().upper()
        == "492D1FCCD21A4CFF6184174067865A6BDE24F85141299A7FD0381D701120CD3B"
    )
    assert tuple(len(DATA[k]) for k in ("positive_cases", "negative_cases", "invariants")) == (
        32,
        40,
        22,
    )


@pytest.mark.parametrize("case", DATA["positive_cases"][:6], ids=lambda c: c["id"])
def test_approved_slice8_vectors_verbatim(case: dict[str, Any]) -> None:
    i = case["input"]
    result = calculate_in_plane_wrench_demand(
        InPlaneWrenchRequest(
            tuple(WrenchBolt(str(n), str(a), str(b)) for n, (a, b) in enumerate(i["bolts"])),
            ("0", "0"),
            i["Fx"],
            i["Fz"],
            str(-Decimal(i["My"])),
            Unit.IN,
            Unit.KIP,
            Unit.KIP_IN,
        )
    )
    exact = result.solution.in_units(Unit.IN, Unit.KIP)
    assert exact.proof is not None
    assert exact.proof.passed
    assert tuple(b.total for b in exact.bolts) == tuple(
        tuple(Fraction(v) for v in row) for row in case["expected"]["vectors"]
    )
    assert -exact.reference_moment == Fraction(i["My"])


@pytest.mark.parametrize("case", DATA["positive_cases"][6:11], ids=lambda c: c["id"])
def test_approved_full_wrench_transport_verbatim(case: dict[str, Any]) -> None:
    i = case["input"]

    def v(key: str, unit: Unit) -> ExactQuantityVector3D:
        return vector(tuple(exact_decimal(Fraction(x)) for x in i[key]), unit)

    result = shift_angle_wrench(
        AngleWrench(v("A", Unit.IN), v("F", Unit.KIP), v("M_A", Unit.KIP_IN)), v("C", Unit.IN)
    )
    assert tuple(
        q.to(Unit.KIP_IN).magnitude for q in (result.moment.x, result.moment.y, result.moment.z)
    ) == tuple(Decimal(x) for x in case["expected"]["M_C"])
