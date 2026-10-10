"""Independent statistical and strict load-comparison contracts."""

from __future__ import annotations

import math
from copy import deepcopy
from decimal import Decimal, localcontext

import pytest
from tests.direct_f8_fixtures import qa_context, specimen_series, statistical_protocol

from frp_master_connection.api.direct_qualification import compare_strength
from frp_master_connection.api.schemas import QuantityDTO
from frp_master_connection.application.direct_qualification_statistics import (
    connection_t,
    recompute_statistics,
)
from frp_master_connection.calculation.quantities import Unit

# Recorded independently using mpmath 1.3.0, 90-digit incomplete-beta CDF inversion.
# Full 80-digit references and solver receipt are in the F8 review package.
REFERENCES = {
    10: "4.2968056627299184860556407515364450686929120605918867",
    11: "4.1437004940465896662087300198297504956636689939359521",
    20: "3.5794001489547159362749690264499654216844623079692221",
    30: "3.3962402883568029909338847324455564567274999655932686",
    50: "3.2650791729288589223835961072224482788185513604796142",
    100: "3.1746038497557522243572098165513120075290805475611689",
    500: "3.1066446079462324652832486077251112922702591633066212",
}


@pytest.mark.parametrize("n", list(REFERENCES))
def test_independently_recorded_student_t(n: int) -> None:
    # Four binary64 ULPs governs inverse-CDF representation QA only. It grants
    # no engineering tolerance to strength, scope, proportionality or strict >.
    expected = Decimal(REFERENCES[n])
    quantum = Decimal(str(4 * math.ulp(float(expected))))
    assert abs(connection_t(n) - expected) <= quantum


@pytest.mark.parametrize("n", [0, 9, True])
def test_connection_quantile_requires_derived_population(n: int) -> None:
    with pytest.raises(ValueError, match="TEN"):
        connection_t(n)


@pytest.mark.parametrize("n", [9, 10, 11, 20])
def test_raw_derived_n_mean_and_zero_cov(n: int) -> None:
    result = recompute_statistics(specimen_series(n), statistical_protocol())
    assert result.accepted_n == n
    if n < 10:
        assert result.phi_p is None
        assert result.blockers
    else:
        assert result.ro_n == 10000
        assert result.sd_n == result.vr == 0
        assert result.phi_p == 1
        assert not result.blockers
        assert result.trace()["degrees_of_freedom"] == n - 1


def test_asce_commentary_example_and_executed_sample_estimator() -> None:
    with localcontext() as ctx:
        ctx.prec = 80
        deviation = Decimal("0.9").sqrt() * Decimal(1500)
        specimens = specimen_series()
        for i, specimen in enumerate(specimens):
            specimen["test_strength"] = str(Decimal(10000) + (deviation if i < 5 else -deviation))
        result = recompute_statistics(specimens, statistical_protocol("10000", "1500", "0.15"))
        assert not result.blockers
        assert result.ro_n == Decimal(10000)
        assert result.sd_n is not None
        assert abs(result.sd_n - Decimal(1500)) < Decimal("1e-73")
        assert result.vr is not None
        assert abs(result.vr - Decimal(".15")) < Decimal("1e-76")
        assert result.phi_p is not None
        assert Decimal(".50865") < result.phi_p < Decimal(".50867")
        assert result.phi_p.quantize(Decimal(".01")) == Decimal(".51")


@pytest.mark.parametrize("strength", ["0", "-1", "NaN", "Infinity", "-Infinity"])
def test_invalid_strengths_never_qualify(strength: str) -> None:
    specimens = specimen_series()
    specimens[0]["test_strength"] = strength
    assert recompute_statistics(specimens, statistical_protocol()).blockers


@pytest.mark.parametrize(
    "change", ["duplicate", "unit", "fixture", "protocol", "condition", "exclude"]
)
def test_raw_population_and_exclusions(change: str) -> None:
    specimens = specimen_series()
    if change == "duplicate":
        specimens[1]["specimen_id"] = specimens[0]["specimen_id"]
    elif change == "unit":
        specimens[0]["unit"] = "mm"
    elif change == "exclude":
        specimens[0]["accepted_or_excluded"] = "EXCLUDED"
    else:
        specimens[0][
            {"fixture": "fixture_id", "protocol": "protocol_id", "condition": "test_condition"}[
                change
            ]
        ] = "different"
    assert recompute_statistics(specimens, statistical_protocol()).blockers


def test_approved_exclusion_retained_and_mixed_units_normalized() -> None:
    specimens = specimen_series(11)
    specimens[0].update(
        accepted_or_excluded="EXCLUDED",
        exclusion_rationale="SYNTHETIC QA documented fixture malfunction",
        exclusion_approval_document_id="RDP",
    )
    specimens[1].update(test_strength="10", unit="kN")
    original = deepcopy(specimens)
    result = recompute_statistics(specimens, statistical_protocol())
    assert result.accepted_n == 10
    assert result.ro_n == 10000
    assert not result.blockers
    assert original == specimens


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("estimator_convention", "POPULATION_SD_N"),
        ("connection_probability", "0.99"),
        ("lab_reported_mean", None),
        ("lab_reported_sd", None),
        ("lab_reported_cov", None),
        ("lab_reported_mean", {"value": "999", "unit": "N", "decimal_quantum": None}),
        ("lab_reported_mean", {"value": "10", "unit": "mm", "decimal_quantum": "0.001"}),
        ("lab_reported_cov", {"value": "0", "decimal_quantum": "0"}),
        ("lab_reported_cov", {"value": "0", "decimal_quantum": "0.15"}),
        ("lab_reported_cov", {"value": "NaN", "decimal_quantum": "0.001"}),
    ],
)
def test_statistical_authority_and_report_reconciliation(field: str, value: object) -> None:
    protocol = statistical_protocol()
    protocol[field] = value
    assert recompute_statistics(specimen_series(), protocol).blockers


def test_client_asserted_mean_phi_count_t_are_not_operands() -> None:
    protocol = statistical_protocol()
    protocol.update(Ro="1", phi_p="1", N=100, t="0")
    actual = recompute_statistics(specimen_series(), protocol)
    expected = recompute_statistics(specimen_series(), statistical_protocol())
    assert actual == expected


@pytest.mark.parametrize(
    ("design", "required", "expected"),
    [
        ("10.000001", "10", "CAPACITY_PASS"),
        ("10", "10", "CAPACITY_PASS"),
        ("9.999999", "10", "CAPACITY_FAIL"),
    ],
)
def test_general_strength_boundary(design: str, required: str, expected: str) -> None:
    assert (
        compare_strength(Decimal(design), Decimal(required), None, False)["capacity_state"]
        == expected
    )


@pytest.mark.parametrize(
    ("design", "expected"), [("2.800001", "PASS"), ("2.8", "NOT_PASS"), ("2.799999", "NOT_PASS")]
)
def test_literal_gravity_boundary(design: str, expected: str) -> None:
    context = qa_context("QA")
    context = context.model_copy(
        update={
            "loading_type": "GRAVITY_D_L",
            "dead_load": QuantityDTO(value="1", unit=Unit.N),
            "live_load": QuantityDTO(value="1", unit=Unit.N),
        }
    )
    assert (
        compare_strength(Decimal(design), Decimal(1), context, True)["gravity_eq_2_2_state"]
        == expected
    )
