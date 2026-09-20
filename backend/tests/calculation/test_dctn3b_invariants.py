"""Executable backend portion of the 22 approved invariants; UI covers I17/I18."""

import ast
import json
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.api.dctn3b import DCTN3BMemberDTO, dctn3b_response
from frp_master_connection.api.double_channel_truss_node import dctn_response
from frp_master_connection.application.dctn3b import preview_dctn3b
from frp_master_connection.application.double_channel_truss_node import preview_dctn
from frp_master_connection.calculation.angle_connector_core import components, shift_angle_wrench
from frp_master_connection.calculation.dctn3b_demand import shear_presentation
from frp_master_connection.calculation.dctn3b_trusted_response import EMPTY_TRUSTED_RESPONSES
from frp_master_connection.calculation.double_channel_truss_node import (
    DCTNRequiredCheck,
    aggregate_dctn_checks,
)
from frp_master_connection.calculation.double_channel_truss_node_response import row_fractions
from frp_master_connection.calculation.quantities import PhysicalQuantity as Q
from frp_master_connection.calculation.quantities import Unit
from frp_master_connection.domain.dctn3b import default_dctn3b_request, migrate_dctn2
from frp_master_connection.domain.double_channel_truss_node import (
    DCTNArrangement,
    default_dctn_request,
)
from tests.api.test_dctn_api_and_parent import PARENT
from tests.api.test_dctn_api_and_parent import (
    test_exact_old_preview_design_geometry_defaults_and_material_plan as assert_old_route_identity,
)
from tests.calculation.test_dctn3b_native import GOLDEN
from tests.calculation.test_dctn3b_trusted import supplied

INVARIANTS = [
    c for c in json.loads(GOLDEN.read_bytes())["invariants"] if c["id"] not in {"I17", "I18"}
]
ROOT = Path(__file__).parents[2]


@pytest.mark.parametrize("case", INVARIANTS, ids=lambda c: c["id"])
def test_approved_invariant(case: dict[str, str]) -> None:
    number = int(case["id"][1:])
    request = default_dctn3b_request()
    preview = preview_dctn3b(request)
    if number == 1:
        assert "start" not in DCTN3BMemberDTO.model_fields
        assert {
            "chord_station",
            "end_center_above_lower_web",
        } <= DCTN3BMemberDTO.model_fields.keys()
        assert request.legacy_geometry_request().members[0].start[2] == Q.of(-5, Unit.IN)
    elif number == 2:
        for depth, status in ((12, "VALID"), (10, "VALID"), (8, "VALID"), (4, "INVALID_GEOMETRY")):
            changed = replace(request, channel=replace(request.channel, depth=Q.of(depth, Unit.IN)))
            assert changed.members == request.members
            assert preview_dctn3b(changed).geometry_status == status
    elif number == 3:
        member = preview.demand.members[0]
        channel_refs = [r for r in member.transported if r.reference_id.startswith("CHORD")]
        assert len(channel_refs) == 2
        assert all(r.wrench.reference != member.at_member_end.reference for r in channel_refs)
        assert all(r.interpretation.endswith("NOT_ALLOCATED_RESPONSE") for r in channel_refs)
    elif number == 4:
        old_preview = preview_dctn(default_dctn_request())
        assert dctn_response(old_preview)["contract"] == "DCTN-2-RC1"
        assert dctn3b_response(preview)["contract"] == "DCTN-3B-RC1"
    elif number == 5:
        old_request = default_dctn_request()
        with pytest.raises(ValueError, match="DCTN_LEGACY_PLACEMENT_NOT_MIGRATABLE"):
            migrate_dctn2(
                replace(
                    old_request,
                    members=(
                        replace(
                            old_request.members[0],
                            start=(
                                Q.of(0, Unit.IN),
                                Q.of(".00001", Unit.IN),
                                Q.of(-5, Unit.IN),
                            ),
                        ),
                    ),
                )
            )
    elif number in {6, 15, 16}:
        editable_member = replace(request.members[0], Qp=Q.of(2, Unit.KIP), Qq=Q.of(-3, Unit.KIP))
        mappings = []
        for width in ("4", "6", "8"):
            changed_member = replace(
                editable_member,
                section=replace(editable_member.section, width=Q.of(width, Unit.IN)),
            )
            labels = shear_presentation(changed_member.section)
            mappings.append(labels.major_component)
            assert (changed_member.P, changed_member.Qp, changed_member.Qq) == (
                editable_member.P,
                editable_member.Qp,
                editable_member.Qq,
            )
            if width == "6":
                assert labels.Qp_label == "Shear p (equal axes)"
                assert labels.Qq_label == "Shear q (equal axes)"
        assert mappings == ["Qq", None, "Qp"]
    elif number == 7:
        angled = preview_dctn3b(default_dctn3b_request(DCTNArrangement.VERTICAL_TWO_INCLINED))
        for member in angled.demand.members:
            u, p, q = member.u, member.p, member.q
            assert q == (Fraction(0), Fraction(1), Fraction(0))
            assert u[1] == p[1] == 0
            assert p == (u[2], Fraction(0), -u[0])
            # Preserve native trig representation: orientation, not renormalization.
            assert u[2] * p[0] - u[0] * p[2] > 0
    elif number == 8:
        request = replace(
            request,
            members=(replace(request.members[0], Qp=Q.of(2, Unit.KIP), Qq=Q.of(3, Unit.KIP)),),
        )
        member = preview_dctn3b(request).demand.members[0]
        for target in member.transported:
            assert (
                shift_angle_wrench(member.at_member_end, target.wrench.reference) == target.wrench
            )
        assert any(any(components(t.wrench.moment)) for t in member.transported)
    elif number == 9:
        assert preview.historical_preview == preview_dctn(request.legacy_geometry_request())
    elif number in {10, 11, 13}:
        request = replace(
            request,
            members=(
                replace(
                    request.members[0],
                    Qq=Q.of("1E-20", Unit.KIP),
                    material_source_reference="APPROVED",
                    local_path_source_reference="APPROVED",
                ),
            ),
            shared_channel_source_reference="APPROVED",
        )
        current = preview_dctn3b(request)
        assert current.historical_preview is None
        assert current.trusted_response is not None
        assert current.trusted_response.response is None
        assert current.response_status == "DCTN_TRANSVERSE_RESPONSE_NOT_QUALIFIED"
        assert EMPTY_TRUSTED_RESPONSES == ()
    elif number in {12, 19}:
        paths = [
            ROOT / "src/frp_master_connection/application/dctn3b.py",
            ROOT / "src/frp_master_connection/calculation/dctn3b_demand.py",
            ROOT / "src/frp_master_connection/calculation/dctn3b_trusted_response.py",
        ]
        for path in paths:
            imports = [
                node.module or ""
                for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
                if isinstance(node, ast.ImportFrom)
            ]
            assert not any(
                "in_plane_wrench_demand" in name or "stainless" in name or "cme3" in name
                for name in imports
            )
        assert tuple(Fraction(x) for x in row_fractions(3)) == (
            Fraction(2, 5),
            Fraction(1, 5),
            Fraction(2, 5),
        )
        assert preview.connector_body_count == 0
    elif number == 14:
        from frp_master_connection.calculation.dctn3b_trusted_response import (
            validate_complete_response,
        )

        request, supplied_preview, record = supplied()
        result = validate_complete_response(
            request, supplied_preview.geometry, supplied_preview.demand, record
        )
        assert result.response is record
        unresolved = preview_dctn3b(request).trusted_response
        assert unresolved is not None
        assert unresolved.response is None
    elif number == 20:
        assert len(FAMILIES) == 17
        with pytest.raises(AssertionError, match="DCTN_SUCCESSOR_INVENTORY_MISMATCH"):
            assert len(FAMILIES) + 1 == 17, "DCTN_SUCCESSOR_INVENTORY_MISMATCH"
    elif number == 21:
        for route in PARENT["routes"]:
            assert_old_route_identity(route)
        assert preview.historical_preview == preview_dctn(default_dctn_request())
    else:
        assert number == 22
        check = DCTNRequiredCheck(
            "SUPPORTED_NUMERICAL_CHECK",
            "MEMBER",
            "FAIL",
            Q.of(2, Unit.KIP),
            Q.of(1, Unit.KIP),
            (),
            "SYNTHETIC_STATUS_ONLY",
        )
        assert (
            aggregate_dctn_checks((check,), ("DCTN_TRANSVERSE_RESPONSE_NOT_QUALIFIED",)) == "FAIL"
        )
