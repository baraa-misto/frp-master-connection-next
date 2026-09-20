"""Explicit qualification, shared-hole and malformed-boundary regressions for DCTN."""

from dataclasses import replace
from decimal import Decimal

import pytest

from frp_master_connection.application.double_channel_truss_node import (
    dctn_mechanism_binding,
    design_check_dctn,
    preview_dctn,
)
from frp_master_connection.calculation.dctn_local_resistance import evaluate_native_dctn_plane
from frp_master_connection.calculation.dctn_sources import DCTNQualifiedMechanism
from frp_master_connection.calculation.double_channel_truss_node import DCTNRequiredCheck
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.calculation.sources import QualificationStatus
from frp_master_connection.domain.double_channel_truss_node import (
    DCTNArrangement,
    DCTNForm,
    DCTNRequest,
    change_dctn_arrangement,
    default_dctn_request,
)
from tests.calculation.test_dctn_sources_and_native import (
    q,
    registry,
    sourced_request,
    synthetic_source,
)


def parallel_request(rows: int = 2) -> DCTNRequest:
    value = default_dctn_request(DCTNArrangement.TWO_INCLINED)
    return replace(
        value,
        channel=replace(value.channel, material_source_reference="MATERIAL_FIXTURE"),
        fastener=replace(value.fastener, source_reference="HARDWARE_FIXTURE"),
        members=tuple(
            replace(
                m,
                start=(q("-5", Unit.IN), q("0", Unit.IN), q(y, Unit.IN)),
                inclination_deg=Decimal(0),
                pattern=replace(m.pattern, rows=rows),
                material_source_reference="MATERIAL_FIXTURE",
            )
            for m, y in zip(value.members, ("-2.5", "2.5"), strict=True)
        ),
    )


@pytest.mark.parametrize("rows", [1, 2, 3])
def test_parallel_shared_channel_checks_use_all_holes_and_native_first_row(rows: int) -> None:
    value = parallel_request(rows)
    p = preview_dctn(value)
    assert p.geometry.status == "VALID"
    sources = registry(p)
    design = design_check_dctn(value, sources)
    for review in p.shared_channel_review:
        assert len(review.hole_ids) == rows * 2
        plan = review.common_force_plan
        assert plan is not None
        assert len(plan.geometry.rows[0].bolts) == 2
        source = next(s for s in sources.materials if s.owner_id == review.owner_id)
        demands = tuple(
            (
                b.id,
                q(str(Decimal(1) / Decimal(2)))
                if rows == 1
                else next(c.demand for c in design.checks if c.check_id == "PIN_BEARING:" + b.id),
            )
            for b in plan.geometry.group.bolts
        )
        assert all(d is not None for _, d in demands)
        native = evaluate_native_dctn_plane(
            value, plan, source, tuple((identity, d) for identity, d in demands if d is not None)
        )
        combined = [c for c in native.checks if not c.check_id.startswith("PIN_BEARING:")]
        assert combined
        assert all(c in design.checks for c in combined)
        assert any(c.check_id.startswith("FIRST_ROW:") for c in combined)
        assert not any(c.check_id.startswith("NET_TENSION:") for c in combined)
        assert (
            sum(
                c.check_id.startswith("PIN_BEARING:") and c.owner_id == review.owner_id
                for c in design.checks
            )
            == rows * 2
        )
    assert len({c.check_id for c in design.checks}) == len(design.checks)


@pytest.mark.parametrize("form", list(DCTNForm))
@pytest.mark.parametrize("failure", [False, True])
def test_exact_bound_test_only_mechanisms_retain_all_numerical_results(
    form: DCTNForm, failure: bool
) -> None:
    value = sourced_request(form, "1")
    value = replace(
        value,
        shared_channel_source_reference="MECHANISM",
        members=tuple(replace(m, local_path_source_reference="MECHANISM") for m in value.members),
    )
    p = preview_dctn(value)
    sources = registry(p)
    before = design_check_dctn(value, sources)
    mechanisms = []
    for owner in ("V", "CHORD_NEG", "CHORD_POS"):
        requirements = tuple(
            b.removeprefix(owner + ":") for b in before.blockers if b.startswith(owner + ":")
        )
        if not requirements:
            continue
        check = DCTNRequiredCheck(
            "QUALIFIED_TEST_ONLY:" + owner,
            owner,
            "FAIL" if failure else "PASS",
            q("2" if failure else "1"),
            q("1" if failure else "2"),
            (),
            "MECHANISM",
        )
        mechanisms.append(
            DCTNQualifiedMechanism(
                "MECHANISM",
                owner,
                synthetic_source(),
                dctn_mechanism_binding(p, owner),
                requirements,
                (check,),
                "TEST_ONLY_NOT_PRODUCTION_QUALIFICATION",
            )
        )
    assert mechanisms
    after = design_check_dctn(value, replace(sources, mechanisms=tuple(mechanisms)))
    assert all(c in after.checks for c in before.checks)
    assert all(m.checks[0] in after.checks for m in mechanisms)
    assert after.whole_connection_status == ("FAIL" if failure else "PASS")
    assert not after.global_chord_design_evaluated
    assert after.blockers == ()


@pytest.mark.parametrize("mode", ["missing", "not_usable", "unqualified", "width", "hole_set"])
def test_native_plane_refuses_missing_property_and_incomplete_demand(mode: str) -> None:
    value = sourced_request()
    p = preview_dctn(value)
    plan = next(x for x in p.local_plans if x.owner_id == "V")
    source = registry(p).materials[-1]
    demands = tuple((b.id, q("1")) for b in plan.geometry.group.bolts)
    if mode == "hole_set":
        with pytest.raises(ValueError, match="actual physical hole set exactly"):
            evaluate_native_dctn_plane(value, plan, source, demands * 2)
        return
    if mode == "width":
        plan = replace(plan, first_row=replace(plan.first_row, effective_width=None))
    elif mode == "missing":
        source = replace(source, material=replace(source.material, properties=()))
    else:
        source = replace(
            source,
            material=replace(
                source.material,
                properties=tuple(
                    replace(prop, use_in_chapter_8_equations=False)
                    if mode == "not_usable"
                    else replace(prop, qualification_status=QualificationStatus.SOURCE_PENDING)
                    for prop in source.material.properties
                ),
            ),
        )
    result = evaluate_native_dctn_plane(value, plan, source, demands)
    assert (
        "DCTN_NATIVE_EFFECTIVE_WIDTH_NOT_QUALIFIED"
        if mode == "width"
        else "DCTN_FRP_LOCAL_STRENGTH_SOURCE_NOT_QUALIFIED"
    ) in result.reasons
    if mode in {"missing", "not_usable"}:
        assert not result.checks


def test_solid_full_depth_qualification_requires_usable_native_bearing_property() -> None:
    value = sourced_request(DCTNForm.SOLID_RECTANGLE)
    p = preview_dctn(value)
    sources = registry(p)
    for modified in (
        replace(sources.materials[-1], full_depth_solid_bearing=False),
        replace(
            sources.materials[-1], material=replace(sources.materials[-1].material, properties=())
        ),
    ):
        result = design_check_dctn(
            value, replace(sources, materials=(*sources.materials[:-1], modified))
        )
        assert "V:DCTN_SOLID_FULL_DEPTH_PIN_BEARING_SOURCE_NOT_QUALIFIED" in result.blockers
        assert not any(c.check_id.startswith("FULL_DEPTH_PIN_BEARING:") for c in result.checks)


def test_arrangement_edit_links_new_diagonal_section_not_independent_position_or_length() -> None:
    value = default_dctn_request(DCTNArrangement.ONE_INCLINED)
    first = replace(
        value.members[0],
        section=replace(
            value.members[0].section,
            form=DCTNForm.W_I,
            width=q("5", Unit.IN),
            length=q("30", Unit.IN),
        ),
    )
    value = replace(value, members=(first,))
    changed = change_dctn_arrangement(value, DCTNArrangement.VERTICAL_TWO_INCLINED)
    assert changed.members[1] is first
    assert (
        changed.members[1].section.linked_section() == changed.members[2].section.linked_section()
    )
    assert changed.members[2].section.length == q("24", Unit.IN)
    assert changed.members[1].start != changed.members[2].start
    assert change_dctn_arrangement(changed, changed.arrangement) == changed


@pytest.mark.parametrize("invalid", ["0", "-1", "NaN"])
def test_source_time_factor_cannot_be_nonpositive_or_nonfinite(invalid: str) -> None:
    record = registry(preview_dctn(sourced_request())).materials[0]
    with pytest.raises(ValueError, match="positive authority"):
        replace(record, lambda_factor=Decimal(invalid))


def test_source_hardware_strength_and_required_check_identity_are_validated() -> None:
    record = registry(preview_dctn(sourced_request())).hardware[0]
    with pytest.raises(ValueError, match="strength must be positive"):
        replace(record, nominal_shear_stress=q("0", Unit.KSI))
    with pytest.raises(ValueError, match="identified local checks"):
        DCTNRequiredCheck("", "V", "PASS", q("1"), q("2"), (), "TEST_ONLY")
    with pytest.raises(ValueError, match="numerical demand and resistance"):
        DCTNRequiredCheck("X", "V", "PASS", None, None, (), "TEST_ONLY")
