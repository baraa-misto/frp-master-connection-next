"""Fail-closed native adapter boundaries, including in-memory corruption adversaries."""

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from typing import cast
from unittest.mock import patch

import pytest

from frp_master_connection.application.connector_material_assembly import (
    canonical_material_assembly,
)
from frp_master_connection.application.dctn_c3_geometry import _surface_pair
from frp_master_connection.application.dctn_native_local import dctn_plane_plans
from frp_master_connection.application.dctn_shared_channel import review_dctn_shared_channels
from frp_master_connection.application.double_channel_truss_node import (
    dctn_mechanism_binding,
    design_check_dctn,
    preview_dctn,
)
from frp_master_connection.application.double_channel_truss_node_geometry import (
    _shaft_intersects_element,
)
from frp_master_connection.calculation.angle_connector_core import quantity_vector
from frp_master_connection.calculation.dctn_local_resistance import (
    DCTNLocalEvaluation,
    evaluate_native_dctn_plane,
)
from frp_master_connection.calculation.dctn_sources import (
    DCTNMaterialSource,
    DCTNQualifiedMechanism,
)
from frp_master_connection.calculation.double_channel_truss_node import (
    DCTNRequiredCheck,
    aggregate_dctn_checks,
    evaluate_dctn_bearing,
)
from frp_master_connection.calculation.double_channel_truss_node_response import _row_pair
from frp_master_connection.calculation.properties import FRPPropertyKind, ThreadStatus
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.sources import QualificationStatus
from frp_master_connection.domain.dctn_geometry import DCTNPlanePlan
from frp_master_connection.domain.double_channel_truss_node import (
    DCTNForm,
    DCTNRequest,
    default_dctn_request,
)
from frp_master_connection.domain.values import PositionVector3D
from frp_master_connection.geometry.surfaces import create_component_surface_set
from tests.calculation.test_dctn_boundary_contracts import parallel_request
from tests.calculation.test_dctn_sources_and_native import (
    q,
    registry,
    sourced_request,
    synthetic_source,
)


def test_closed_domain_types_and_material_roles_reject_unknown_inputs() -> None:
    value = default_dctn_request()
    with pytest.raises(ValueError, match="requires RHS"):
        replace(value.members[0].section, form=cast(DCTNForm, "ANGLE"))
    with pytest.raises(ValueError, match="flag requires a boolean"):
        replace(value.members[0].pattern, staggered=cast(bool, 1))
    with pytest.raises(ValueError, match="valid canonical DCTN assembly"):
        canonical_material_assembly("double-channel-truss-node", object())


def test_opposing_native_surface_must_contain_the_actual_hardware_footprint() -> None:
    member = preview_dctn(default_dctn_request()).geometry.members[0]
    surfaces = create_component_surface_set(member.placement)
    with pytest.raises(ValueError, match="OPPOSING_PATCH_NOT_UNAMBIGUOUS"):
        _surface_pair(member.profile, surfaces, PositionVector3D(10000, 10000, 10000), 1)


def test_nonordinary_hole_keeps_geometry_but_does_not_invent_ordinary_hole_methods() -> None:
    value = default_dctn_request()
    value = replace(value, fastener=replace(value.fastener, hole_diameter=q(".57", Unit.IN)))
    preview = preview_dctn(value)
    assert preview.geometry.status == "VALID"
    assert preview.local_plans
    assert all("DCTN_ORDINARY_HOLE_METHOD_NOT_QUALIFIED" in p.reasons for p in preview.local_plans)
    assert all(p.block_paths is None for p in preview.local_plans)
    # The optional mapping input may be absent, but no native mapping is fabricated.
    without_mappings = dctn_plane_plans(value, preview.geometry)
    assert all(not p.native_bolt_mappings for p in without_mappings)


@pytest.mark.parametrize("failure", ["duplicate", "native", "exhausted"])
def test_complete_hole_review_fails_closed_on_invalid_native_grouping(failure: str) -> None:
    value = default_dctn_request()
    plans = preview_dctn(value).local_plans
    if failure == "duplicate":
        with pytest.raises(ValueError, match="duplicate physical holes"):
            review_dctn_shared_channels(value, plans + plans)
        return
    message = (
        "Declared row count does not match force-axis physical row resolution."
        if failure == "exhausted"
        else "native boundary invalid"
    )
    with (
        patch(
            "frp_master_connection.application.dctn_shared_channel.resolve_multirow_geometry",
            side_effect=ValueError(message),
        ),
        pytest.raises(
            ValueError, match="could not be resolved" if failure == "exhausted" else message
        ),
    ):
        review_dctn_shared_channels(value, plans)


def test_shared_group_missing_properties_remain_blocking_without_duplicate_bearing() -> None:
    value = parallel_request()
    preview = preview_dctn(value)
    absent = design_check_dctn(value)
    assert all(
        owner + ":DCTN_FRP_LOCAL_STRENGTH_SOURCE_NOT_QUALIFIED" in absent.blockers
        for owner in ("CHORD_NEG", "CHORD_POS")
    )
    sources = registry(preview)
    sources = replace(
        sources,
        materials=tuple(
            replace(s, material=replace(s.material, properties=())) for s in sources.materials
        ),
    )
    result = design_check_dctn(value, sources)
    assert all(
        owner + ":DCTN_FRP_LOCAL_STRENGTH_SOURCE_NOT_QUALIFIED" in result.blockers
        for owner in ("CHORD_NEG", "CHORD_POS", "D1", "D2")
    )
    assert not any(c.check_id.startswith("PIN_BEARING:") for c in result.checks)


def test_shared_group_preserves_successful_native_plan_without_invented_reasons() -> None:
    value = parallel_request()
    preview = preview_dctn(value)

    # Boundary contract only: the caller must also accept a native executor with
    # no unresolved reasons. Its numerical checks remain the actual native checks.
    def resolved(
        request: DCTNRequest,
        plan: DCTNPlanePlan,
        source: DCTNMaterialSource,
        demands: tuple[tuple[str, PhysicalQuantity], ...],
    ) -> DCTNLocalEvaluation:
        actual = evaluate_native_dctn_plane(request, plan, source, demands)
        # Test-only isolated orchestration scenario, not a production qualification.
        return replace(actual, reasons=())

    with patch(
        "frp_master_connection.application.double_channel_truss_node.evaluate_native_dctn_plane",
        side_effect=resolved,
    ) as native:
        result = design_check_dctn(value, registry(preview))
        assert native.call_count == len(preview.local_plans) + 2
    assert result.checks


def test_solid_full_depth_checks_are_per_member_not_all_node_rows() -> None:
    value = parallel_request(1)
    value = replace(
        value,
        members=tuple(
            replace(m, section=replace(m.section, form=DCTNForm.SOLID_RECTANGLE))
            for m in value.members
        ),
    )
    preview = preview_dctn(value)
    assert preview.geometry.status == "VALID"
    result = design_check_dctn(value, registry(preview))
    full = [c for c in result.checks if c.check_id.startswith("FULL_DEPTH_PIN_BEARING:")]
    assert len(full) == 2
    assert {c.owner_id for c in full} == {"D1", "D2"}
    assert all(c.demand == q("1") for c in full)


def test_qualified_mechanism_cannot_duplicate_an_existing_native_check() -> None:
    value = sourced_request(DCTNForm.W_I, "1")
    value = replace(value, members=(replace(value.members[0], local_path_source_reference="MECH"),))
    preview = preview_dctn(value)
    sources = registry(preview)
    native = design_check_dctn(value, sources)
    required = tuple(b.removeprefix("V:") for b in native.blockers if b.startswith("V:"))
    existing = next(c for c in native.checks if c.owner_id == "V")
    duplicate = replace(existing, source_reference="MECH")
    mechanism = DCTNQualifiedMechanism(
        "MECH",
        "V",
        synthetic_source(),
        dctn_mechanism_binding(preview, "V"),
        required,
        (duplicate,),
        "TEST_ONLY_NOT_PRODUCTION_QUALIFICATION",
    )
    with pytest.raises(ValueError, match="cannot duplicate a physical check"):
        design_check_dctn(value, replace(sources, mechanisms=(mechanism,)))


def test_rhs_reduction_is_rejected_for_non_rhs_ownership() -> None:
    source = registry(preview_dctn(sourced_request())).materials[0]
    with pytest.raises(ValueError, match="RHS_FACTOR_OWNER_MISMATCH"):
        evaluate_dctn_bearing(
            owner_id="V",
            bolt_id="V:1",
            incoming_form=DCTNForm.W_I,
            designated_rhs_wall=True,
            thickness=q(".375", Unit.IN),
            diameter=q(".5", Unit.IN),
            demand=q("1"),
            characteristic=q("20", Unit.KSI),
            property_kind=FRPPropertyKind.FBR_L,
            qualification=QualificationStatus.QUALIFIED,
            factors=source.factors,
            thread=ThreadStatus.EXCLUDED,
            c_delta=Decimal(1),
            lambda_factor=Decimal(1),
        )
    missing = DCTNRequiredCheck("MISSING", "V", "SOURCE_REQUIRED", None, None, (), "")
    assert aggregate_dctn_checks((missing,), ()) == "ENGINEERING_REVIEW_REQUIRED"


def test_same_sign_eccentricity_cannot_pass_the_exact_row_pair_closure() -> None:
    zero = (Fraction(0), Fraction(0), Fraction(0))
    ref = quantity_vector(zero, Unit.IN)
    with pytest.raises(ValueError, match="WI_ECCENTRICITY_RESPONSE_NOT_QUALIFIED"):
        _row_pair(
            "V",
            1,
            Decimal(1),
            Fraction(10),
            (Fraction(1), Fraction(0), Fraction(0)),
            (Fraction(2), Fraction(1), Fraction(-3)),
            (Fraction(2), Fraction(1), Fraction(3)),
            zero,
            Unit.IN,
            (ref, ref),
        )


def test_shaft_collision_guard_rejects_unknown_frames_and_primitives() -> None:
    preview = preview_dctn(default_dctn_request())
    shaft = preview.geometry.shafts[0]
    element = preview.geometry.members[0].placement.physical_elements[0]
    corrupted = deepcopy(element)
    # In-memory tamper probes only; native/frozen objects and source files untouched.
    frame = deepcopy(corrupted.global_frame)
    object.__setattr__(frame.x_axis, "y", 0.5)
    object.__setattr__(corrupted, "global_frame", frame)
    with pytest.raises(ValueError, match="native node-plane frame"):
        _shaft_intersects_element(shaft, corrupted, Decimal(".25"))
    corrupted = deepcopy(element)
    object.__setattr__(corrupted, "extrusions", (object(),))
    with pytest.raises(ValueError, match="native rectangular primitives"):
        _shaft_intersects_element(shaft, corrupted, Decimal(".25"))


def test_intersecting_foreign_member_is_not_silently_added_to_a_shaft() -> None:
    value = parallel_request()
    first, second = value.members
    value = replace(value, members=(first, replace(second, start=first.start)))
    result = design_check_dctn(value)
    assert any("UNINTENDED_SHAFT_LAYER" in r for r in result.blockers)
    assert result.preview.geometry.status == "INVALID_GEOMETRY"
    assert result.checks == ()
