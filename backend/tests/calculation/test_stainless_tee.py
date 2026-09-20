"""All sixteen core invariants, with I11's explicit owner/EOR replacement."""

from dataclasses import replace
from decimal import Decimal, localcontext

import pytest

from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.stainless_response import MODES
from tests.calculation.test_stainless_angle import (
    G,
    evaluate,
    q,
    record,
    request,
    values,
)
from tests.calculation.test_stainless_angle import (
    test_i11_owner_supersedes_original_without_changing_artifact as i11,
)
from tests.calculation.test_stainless_response import evaluate as revaluate
from tests.calculation.test_stainless_response import fixture as rfixture
from tests.calculation.test_stainless_response import record as rrecord
from tests.calculation.test_stainless_response import request as rrequest

D = Decimal


@pytest.mark.parametrize("identity", [x["id"] for x in G["invariants"]])
def test_all_sixteen_invariants(identity: str) -> None:
    r = request("TEE", ("COMPRESSION", "FLEXURE", "TENSION", "SHEAR"))
    result = evaluate(r)
    if identity == "I01":
        rr = rrequest()
        assert revaluate(rr).authority == rrecord(rr)
        assert not revaluate(rr, replace(rrecord(rr), material_dependence_resolved=False)).demands
    elif identity == "I02":
        for name in ("R_ROW_FRP_STEEL_2", "R_ROW_FRP_STEEL_3"):
            rr = rfixture(name)
            rec = rrecord(rr)
            assert rec.native is not None
            assert sum(rec.native.row_fractions) == 1
            assert revaluate(rr).status == "QUALIFIED_RESPONSE"
    elif identity == "I03":
        rr = rfixture("R_COMMON_SHAFT_CONSERVATION")
        assert revaluate(rr).shaft_status == "QUALIFIED"
        assert not revaluate(replace(rr, shafts=rr.shafts * 2)).demands
    elif identity == "I04":
        rr = rfixture("R_PRYING_TOTAL_TENSION_NO_DOUBLE_ADD")
        assert revaluate(rr).contact_prying_status == "QUALIFIED"
        assert not revaluate(
            replace(rr, prying=(replace(rr.prying[0], extra_increment=D(3)),))
        ).demands
    elif identity == "I05":
        for changed in (
            replace(r, product=replace(r.product, id="NEW_PRODUCT")),
            replace(r, section=replace(r.section, geometry_sha256="e" * 64)),
            replace(r, demand=replace(r.demand, id="NEW_ACTION")),
        ):
            assert evaluate(changed).fingerprint != result.fingerprint
            assert evaluate(changed, record(r)).status != "ISOLATED_COVERED_CHECKS_PASS"
    elif identity == "I06":
        converted = replace(
            r,
            product=replace(r.product, fy=r.product.fy.to(Unit.MPA)),
            section=replace(r.section, area=r.section.area.to(Unit.MM2)),
        )
        assert evaluate(converted).fingerprint == result.fingerprint
        with localcontext() as ctx:
            ctx.prec = 6
            assert evaluate(r) == result
    elif identity == "I07":
        for fe in ("100000", "400", "25", "15", ".1"):
            trial = evaluate(replace(r, e4_fe=q(fe, Unit.KSI)))
            assert values(trial, "E4")["Fn_used"] <= 25
            assert values(trial, "E4")["Fn_used"] <= values(trial, "E4")["Fn_raw"]
    elif identity == "I08":
        for width in (1, 10, 30, 100):
            s = replace(r.shear_elements[0], width=q(width), thickness=q(1))
            trial = evaluate(replace(r, checks=("SHEAR",), shear_elements=(s,)))
            v = values(trial, "G6:SHEAR")
            assert 0 < v["Cv2"] <= D("1.2")
            larger = replace(s, width=q(width * 2), thickness=q(2))
            assert (
                values(
                    evaluate(replace(r, checks=("SHEAR",), shear_elements=(larger,))), "G6:SHEAR"
                )["available"]
                > v["available"]
            )
    elif identity == "I09":
        for lb in (0, 20, 40, 60, 80):
            st = replace(r.stability[0], lb=q(lb), fcr=q(1000, Unit.KSI))
            v = values(evaluate(replace(r, stability=(st, r.stability[1]))), "F10:w")
            assert v["nominal"] <= v["My"]
    elif identity == "I10":
        capacities = []
        for lb in range(20, 61):
            st = replace(r.stability[0], lb=q(lb))
            capacities.append(
                values(evaluate(replace(r, stability=(st, r.stability[1]))), "F10:w")["available"]
            )
        assert capacities == sorted(capacities, reverse=True)
    elif identity == "I11":
        i11()
    elif identity == "I12":
        a = request()
        assert a.shear_lag is not None
        for count in (2, 3, 4, 5):
            lag = replace(a.shear_lag, fasteners_per_line=count, x=q(".5"), length=q(4))
            assert 0 < values(evaluate(replace(a, shear_lag=lag)), "D2_D3")["U"] <= 1
            assert not evaluate(replace(r, checks=("TENSION",), shear_lag=lag)).traces
    elif identity == "I13":
        for demand in (
            replace(r.demand, torsion=q(1, Unit.KIP_IN)),
            replace(r.demand, axial=q(1, Unit.KIP), shear=q(1, Unit.KIP)),
        ):
            assert not evaluate(replace(r, demand=demand)).traces
    elif identity == "I14":
        rr = rrequest(MODES[2])
        rec = rrecord(rr)
        assert rec.native is not None
        assert not revaluate(
            rr, replace(rec, native=replace(rec.native, qualified_slip_contact_fixture=False))
        ).demands
    elif identity == "I15":
        # Calls frozen tests' fixture evaluators without any production cross-import.
        from tests.calculation.test_stainless_plate import evaluate as p1
        from tests.calculation.test_stainless_plate import request as p1_request
        from tests.calculation.test_stainless_plate_clear_body import evaluate as p2
        from tests.calculation.test_stainless_plate_clear_body import request as p2_request

        before1, before2 = p1(p1_request()), p2(p2_request())
        evaluate(r)
        assert p1(p1_request()) == before1
        assert p2(p2_request()) == before2
    else:
        assert identity == "I16"
        assert len(G["invariants"]) == 16
        assert not result.family_activation
        assert "FOUNDATION_ANCHOR_EXTERNAL" in result.external_scopes
        assert not revaluate(rrequest()).family_activation
