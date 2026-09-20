from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from frp_master_connection.api import routes
from frp_master_connection.api.app import create_app
from frp_master_connection.api.web_splice_schemas import WebSpliceRequestDTO
from frp_master_connection.application import web_splice_orchestration as service
from frp_master_connection.calculation import PhysicalQuantity, Unit
from frp_master_connection.calculation.eccentric_demand import (
    EccentricDemandInput,
    EccentricDemandResult,
    calculate_eccentric_bolt_group_demand,
)
from frp_master_connection.config import ApplicationEnvironment, AppSettings
from frp_master_connection.domain import (
    EngineeringUnitSystem,
    WebSpliceBeamGeometry,
    WebSpliceBoltGroupLayout,
    WebSpliceForce,
    WebSplicePlateGeometry,
    WebSpliceRequest,
    WebSpliceStatus,
    default_web_splice_request,
)

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = (
    ROOT / "backend/tests/golden/stage_3_6a_symmetric_double_web_splice_golden_benchmarks_rc1.json"
)


def _values(vector: service.WebSpliceVector, unit: Unit) -> tuple[Decimal, Decimal, Decimal]:
    return (
        vector.l.to(unit).magnitude,
        vector.v.to(unit).magnitude,
        vector.t.to(unit).magnitude,
    )


def _dto(system: EngineeringUnitSystem = EngineeringUnitSystem.US_CUSTOMARY) -> dict[str, object]:
    request = default_web_splice_request(unit_system=system)
    length = request.source_length_unit.value
    moment = request.user_moment_l_v_t[0].unit.value

    def quantity(item: PhysicalQuantity) -> dict[str, str]:
        return {"value": str(item.magnitude), "unit": item.unit.value}

    return {
        "orchestration_contract_version": "3.6A-RC1",
        "request_id": request.request_id,
        "unit_system": system.value,
        "source_length_unit": length,
        "beam": {
            "profile_family": "WIDE_FLANGE_I",
            "depth": quantity(request.beam.depth),
            "flange_width": quantity(request.beam.flange_width),
            "web_thickness": quantity(request.beam.web_thickness),
            "flange_thickness": quantity(request.beam.flange_thickness),
            "display_length_each_side": quantity(request.beam.display_length_each_side),
        },
        "beam_end_gap": quantity(request.beam_end_gap),
        "splice_plate": {
            "length": quantity(request.splice_plate.length),
            "height": quantity(request.splice_plate.height),
            "thickness": quantity(request.splice_plate.thickness),
            "count": 2,
            "locked_identical": True,
        },
        "bolt_group": {
            "rows": request.group.rows,
            "bolts_per_row": request.group.bolts_per_row,
            "vertical_pitch": quantity(request.group.vertical_pitch),
            "longitudinal_gauge": quantity(request.group.longitudinal_gauge),
            "centroid_offset": quantity(request.group.centroid_offset),
            "locked_identical_mirror": True,
        },
        "bolt_diameter": quantity(request.bolt_diameter),
        "hole_diameter": quantity(request.hole_diameter),
        "transfer_force": {
            "axial_force": quantity(request.transfer_force.axial),
            "major_shear": quantity(request.transfer_force.major_shear),
            "minor_shear": quantity(request.transfer_force.minor_shear),
        },
        "user_moment_l_v_t": {"x": "0", "y": "0", "z": "0", "unit": moment},
        "flange_splice_enabled": False,
    }


def _post(path: str, payload: dict[str, object]) -> httpx.Response:
    async def send() -> httpx.Response:
        application = create_app(settings=AppSettings(environment=ApplicationEnvironment.TEST))
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)

    return asyncio.run(send())


def test_controlled_artifact_hashes_and_golden_g1_through_g43() -> None:
    expected = {
        "docs/governance/STAGE_3_6A_SYMMETRIC_DOUBLE_WEB_SPLICE_SELECTION_DECISION.md": "0A1E2AEC21C9946B3FAC4A2803FDA43BAE39C85273E77199C0D40DEE0F0CFBB7",  # noqa: E501
        "docs/engineering/STAGE_3_6A_SYMMETRIC_DOUBLE_WEB_SPLICE_ENGINEERING_SPECIFICATION_RC1.md": "0483595B4C8A6BCB844A0A9894E49673F220332F6A64E5D893D3D86DAD05084B",  # noqa: E501
        "backend/tests/golden/stage_3_6a_symmetric_double_web_splice_golden_benchmarks_rc1.json": "D3CF8E452732E1DA187FF2BFCB2AB9CFF7BD30044945552230E3A23518476EDB",  # noqa: E501
        "docs/qa/STAGE_3_6A_SYMMETRIC_DOUBLE_WEB_SPLICE_AUTHORITY_LEDGER_RC1.md": "DDFB0FE514123A8D6B0E879759EE89FB7617551640F1CB8CD9347CBEEBDEAD0F",  # noqa: E501
    }
    for path, digest in expected.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest().upper() == digest
    fixture = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert fixture["contract"] == "3.6A-RC1"
    assert [item["id"] for item in fixture["benchmarks"]] == [
        f"G{index}_{item['id'].split('_', 1)[1]}"
        for index, item in enumerate(fixture["benchmarks"], start=1)
    ]
    assert len(fixture["benchmarks"]) == 43


def test_default_geometry_wrenches_paths_material_axes_and_limitations() -> None:
    preview = service.preview_web_splice(default_web_splice_request())
    assert preview.geometry_status is WebSpliceStatus.VALID
    assert preview.assembly_status is WebSpliceStatus.NOT_EVALUATED
    assert preview.design_check_ready
    assert not preview.resistance_evaluated
    assert _values(preview.beam_a_group.wrench.force_l_v_t, Unit.KIP) == tuple(
        Decimal(item) for item in ("0", "-10", "0")
    )
    assert _values(preview.beam_b_group.wrench.force_l_v_t, Unit.KIP) == tuple(
        Decimal(item) for item in ("0", "10", "0")
    )
    assert _values(preview.beam_a_group.wrench.moment_l_v_t, Unit.KIP_IN) == tuple(
        Decimal(item) for item in ("0", "0", "-40")
    )
    assert _values(preview.beam_b_group.wrench.moment_l_v_t, Unit.KIP_IN) == tuple(
        Decimal(item) for item in ("0", "0", "-40")
    )
    coordinates_a = tuple(
        _values(item, Unit.IN) for item in preview.beam_a_group.bolt_coordinates_l_v_t
    )
    coordinates_b = tuple(
        _values(item, Unit.IN) for item in preview.beam_b_group.bolt_coordinates_l_v_t
    )
    assert coordinates_a == tuple(
        tuple(Decimal(str(item)) for item in coordinate)
        for coordinate in ((-5.5, -1.5, 0), (-2.5, -1.5, 0), (-5.5, 1.5, 0), (-2.5, 1.5, 0))
    )
    assert coordinates_b == tuple(
        tuple(Decimal(str(item)) for item in coordinate)
        for coordinate in ((2.5, -1.5, 0), (5.5, -1.5, 0), (2.5, 1.5, 0), (5.5, 1.5, 0))
    )
    assert (
        preview.beam_a_group.demand.action_source_id != preview.beam_b_group.demand.action_source_id
    )
    assert all(
        item.reverse_path_resolved_independently for item in preview.beam_b_group.layer_demands
    )
    assert [item.fraction_of_interface_demand for item in preview.beam_a_group.layer_demands] == [
        Decimal("0.5"),
        Decimal("1"),
        Decimal("0.5"),
    ]
    assert preview.plate_pair_system_fraction == 1
    assert len(preview.visualization.bolts) == 8
    assert len({item.bolt_id for item in preview.visualization.bolts}) == 8
    assert all(
        item.path_layers[0].startswith("POSITIVE") and item.path_layers[-1].startswith("NEGATIVE")
        for item in preview.visualization.bolts
    )
    assert all(
        item.internal_hardware_count == 0 and item.washer_count == 2
        for item in preview.visualization.bolts
    )
    assert preview.visualization.beam_end_planes_l[0].to(Unit.IN).magnitude == Decimal("-0.25")
    assert preview.visualization.beam_end_planes_l[1].to(Unit.IN).magnitude == Decimal("0.25")
    assert len(preview.visualization.material_regions) == 8
    assert set(preview.limitations) == set(service.WEB_SPLICE_API_LIMITATIONS)


@pytest.mark.parametrize(
    ("axial", "major", "expected_a", "expected_b", "expected_moment"),
    [
        ("10", "0", (10, 0, 0), (-10, 0, 0), (0, 0, 0)),
        ("-10", "0", (-10, 0, 0), (10, 0, 0), (0, 0, 0)),
        ("5", "-10", (5, -10, 0), (-5, 10, 0), (0, 0, -40)),
    ],
)
def test_signed_transfer_matrix(
    axial: str,
    major: str,
    expected_a: tuple[int, int, int],
    expected_b: tuple[int, int, int],
    expected_moment: tuple[int, int, int],
) -> None:
    base = default_web_splice_request()
    force = replace(
        base.transfer_force,
        axial=PhysicalQuantity.of(axial, Unit.KIP),
        major_shear=PhysicalQuantity.of(major, Unit.KIP),
    )
    preview = service.preview_web_splice(replace(base, transfer_force=force))
    assert _values(preview.beam_a_group.wrench.force_l_v_t, Unit.KIP) == tuple(
        Decimal(item) for item in expected_a
    )
    assert _values(preview.beam_b_group.wrench.force_l_v_t, Unit.KIP) == tuple(
        Decimal(item) for item in expected_b
    )
    assert _values(preview.beam_a_group.wrench.moment_l_v_t, Unit.KIP_IN) == tuple(
        Decimal(item) for item in expected_moment
    )
    assert _values(preview.beam_b_group.wrench.moment_l_v_t, Unit.KIP_IN) == tuple(
        Decimal(item) for item in expected_moment
    )


def test_minor_shear_is_retained_with_explicit_limitation() -> None:
    base = default_web_splice_request()
    force = replace(base.transfer_force, minor_shear=PhysicalQuantity.of(3, Unit.KIP))
    preview = service.preview_web_splice(replace(base, transfer_force=force))
    assert _values(preview.beam_a_group.wrench.force_l_v_t, Unit.KIP) == tuple(
        Decimal(item) for item in ("0", "-10", "3")
    )
    assert "WEB_SPLICE_MINOR_SHEAR_BOLT_AXIS_RESPONSE" in preview.limitations
    pure_minor = replace(
        base.transfer_force,
        major_shear=PhysicalQuantity.of(0, Unit.KIP),
        minor_shear=PhysicalQuantity.of(3, Unit.KIP),
    )
    design = service.design_check_web_splice(replace(base, transfer_force=pure_minor))
    assert not design.supported_local_checks_executed
    assert any(
        "LOCAL_RESISTANCE_MAPPING_NOT_AVAILABLE" in item
        for item in design.local_resistance_warnings
    )


def test_local_handoff_fails_closed_for_nonstandard_hole_and_combined_row_mapping() -> None:
    base = default_web_splice_request()
    hole = service.design_check_web_splice(
        replace(base, hole_diameter=PhysicalQuantity.of("0.6", Unit.IN))
    )
    assert hole.local_resistance_warnings == (
        "LOCAL_RESISTANCE_STANDARD_HOLE_MAPPING_NOT_AVAILABLE",
    )
    combined = replace(
        base.transfer_force,
        axial=PhysicalQuantity.of(5, Unit.KIP),
    )
    design = service.design_check_web_splice(replace(base, transfer_force=combined))
    assert not design.supported_local_checks_executed
    assert any("Declared row count" in item for item in design.local_resistance_warnings)


def test_us_si_equivalence_and_presentation_exclusion() -> None:
    us = service.preview_web_splice(default_web_splice_request())
    si_request = default_web_splice_request(unit_system=EngineeringUnitSystem.SI)
    si = service.preview_web_splice(si_request)
    assert us.canonical_input_fingerprint == si.canonical_input_fingerprint
    assert us.connector_geometry_fingerprint == si.connector_geometry_fingerprint
    assert us.engineering_fingerprint == si.engineering_fingerprint
    longer = replace(
        us_request := default_web_splice_request(),
        beam=replace(us_request.beam, display_length_each_side=PhysicalQuantity.of(30, Unit.IN)),
    )
    changed = service.preview_web_splice(longer)
    assert changed.engineering_fingerprint == us.engineering_fingerprint
    assert changed.visualization.boxes[0].size_l_v_t.l.magnitude == 30
    assert len(changed.visualization.boxes) == 8
    assert {box.component_id for box in changed.visualization.boxes} >= {
        "BEAM_A_WEB",
        "BEAM_A_TOP_FLANGE",
        "BEAM_A_BOTTOM_FLANGE",
        "BEAM_B_WEB",
        "BEAM_B_TOP_FLANGE",
        "BEAM_B_BOTTOM_FLANGE",
    }


def test_geometry_invalidity_precedes_design_limitations() -> None:
    base = default_web_splice_request()
    tall_plate = replace(base.splice_plate, height=PhysicalQuantity.of(10, Unit.IN))
    invalid = service.preview_web_splice(replace(base, splice_plate=tall_plate))
    assert invalid.geometry_status is WebSpliceStatus.INVALID_GEOMETRY
    assert "SPLICE_PLATE_FLANGE_POSITIVE_VOLUME_INTERFERENCE" in invalid.geometry_invalid_reasons
    assert not invalid.design_check_ready
    design = service.design_check_web_splice(replace(base, splice_plate=tall_plate))
    assert design.assembly_status is WebSpliceStatus.INVALID_GEOMETRY


def test_complete_hole_containment_and_supported_failure_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = default_web_splice_request()
    wide_pitch = replace(base.group, vertical_pitch=PhysicalQuantity.of(9, Unit.IN))
    invalid = service.preview_web_splice(replace(base, group=wide_pitch))
    assert "COMPLETE_HOLE_NOT_CONTAINED_IN_BEAM_WEB" in invalid.geometry_invalid_reasons
    monkeypatch.setattr(
        service,
        "_evaluate_supported_local_resistance",
        lambda _request, _preview: (
            ("BEAM_A_WEB:PIN_BEARING",),
            ("BEAM_A_WEB:PIN_BEARING",),
            (),
            ("f" * 64,),
        ),
    )
    design = service.design_check_web_splice(base)
    assert design.assembly_status is WebSpliceStatus.FAIL
    assert design.required_check_status == "FAIL"
    assert design.supported_local_failure_present


def test_explicit_design_executes_existing_local_handoff_and_retains_limitations() -> None:
    design = service.design_check_web_splice(default_web_splice_request())
    assert design.supported_local_checks_executed
    assert design.local_check_ids
    assert design.local_resistance_fingerprints
    assert not design.ordinary_pass_allowed
    assert design.preview.limitations == service.WEB_SPLICE_API_LIMITATIONS
    assert all("BOLT_SHEAR" not in item for item in design.local_check_ids)
    base = default_web_splice_request()
    low_force = replace(
        base.transfer_force,
        major_shear=PhysicalQuantity.of("-0.1", Unit.KIP),
    )
    limited = service.design_check_web_splice(replace(base, transfer_force=low_force))
    assert limited.supported_local_checks_executed
    assert not limited.supported_local_failure_present
    assert limited.assembly_status is WebSpliceStatus.NOT_EVALUATED


def test_two_independent_stage_2_5a_calls_and_preview_zero_resistance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    original = calculate_eccentric_bolt_group_demand

    def wrapped(value: EccentricDemandInput) -> EccentricDemandResult:
        calls.append(value.action_source_id)
        return original(value)

    monkeypatch.setattr(service, "calculate_eccentric_bolt_group_demand", wrapped)
    preview = service.preview_web_splice(default_web_splice_request())
    assert calls == [
        "STAGE_3_6A_BEAM_A_WEB_SPLICE_GROUP_ACTION",
        "STAGE_3_6A_BEAM_B_WEB_SPLICE_GROUP_ACTION",
    ]
    assert not preview.resistance_evaluated


def test_request_fail_closed_guards() -> None:
    base = default_web_splice_request()
    with pytest.raises(ValueError, match="beam_end_gap must be positive"):
        replace(base, beam_end_gap=PhysicalQuantity.of(0, Unit.IN))
    with pytest.raises(ValueError, match="MOMENT_TRANSFER_NOT_AUTHORIZED"):
        replace(
            base,
            user_moment_l_v_t=(
                PhysicalQuantity.of(0, Unit.KIP_IN),
                PhysicalQuantity.of(0, Unit.KIP_IN),
                PhysicalQuantity.of(1, Unit.KIP_IN),
            ),
        )
    with pytest.raises(ValueError, match="FLANGE_SPLICE"):
        replace(base, flange_splice_enabled=True)
    with pytest.raises(ValueError, match="SYMMETRIC_DOUBLE"):
        replace(base, splice_plate=replace(base.splice_plate, count=1))
    with pytest.raises(ValueError, match="mirrored"):
        replace(base, group=replace(base.group, locked_identical_mirror=False))
    with pytest.raises(ValueError, match="Hole diameter"):
        replace(base, hole_diameter=PhysicalQuantity.of("0.4", Unit.IN))
    with pytest.raises(TypeError, match="length quantity"):
        WebSpliceBeamGeometry(
            PhysicalQuantity.of(10, Unit.KIP),
            base.beam.flange_width,
            base.beam.web_thickness,
            base.beam.flange_thickness,
            base.beam.display_length_each_side,
        )
    with pytest.raises(ValueError, match="WIDE_FLANGE_I"):
        replace(base, beam=replace(base.beam, profile_family="CHANNEL"))
    with pytest.raises(ValueError, match="web thickness"):
        replace(base, beam=replace(base.beam, web_thickness=PhysicalQuantity.of(8, Unit.IN)))
    with pytest.raises(ValueError, match="positive clear web"):
        replace(base, beam=replace(base.beam, flange_thickness=PhysicalQuantity.of(5, Unit.IN)))
    with pytest.raises(ValueError, match="positive row"):
        replace(base, group=replace(base.group, rows=0))
    with pytest.raises(ValueError, match="request_id"):
        replace(base, request_id=" ")
    with pytest.raises(ValueError, match="Unsupported"):
        replace(base, orchestration_contract_version="bad")
    with pytest.raises(ValueError, match="source_length_unit"):
        replace(base, source_length_unit=Unit.KIP)
    with pytest.raises(ValueError, match="exactly three"):
        replace(
            base,
            user_moment_l_v_t=base.user_moment_l_v_t[:2],  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="force quantity"):
        replace(
            base,
            transfer_force=WebSpliceForce(
                PhysicalQuantity.of(1, Unit.IN),
                base.transfer_force.major_shear,
                base.transfer_force.minor_shear,
            ),
        )
    with pytest.raises(ValueError, match="positive"):
        replace(
            base, splice_plate=replace(base.splice_plate, thickness=PhysicalQuantity.of(0, Unit.IN))
        )
    assert isinstance(base.beam, WebSpliceBeamGeometry)
    assert isinstance(base.splice_plate, WebSplicePlateGeometry)
    assert isinstance(base.group, WebSpliceBoltGroupLayout)
    assert isinstance(base, WebSpliceRequest)


def test_defensive_preview_type_and_blank_transport_identity() -> None:
    with pytest.raises(TypeError, match="WebSpliceRequest"):
        service.preview_web_splice(object())  # type: ignore[arg-type]
    blank = _dto()
    blank["request_id"] = " "
    with pytest.raises(ValueError, match="request_id"):
        WebSpliceRequestDTO.model_validate(blank)


def test_api_strict_preview_design_and_rejections() -> None:
    payload = _dto()
    preview = _post("/api/v1/calculations/beam-web-splice/preview", payload)
    assert preview.status_code == 200
    assert preview.json()["geometry_status"] == "VALID"
    assert preview.json()["resistance_evaluated"] is False
    design = _post("/api/v1/calculations/beam-web-splice/design-check", payload)
    assert design.status_code == 200
    assert design.json()["assembly_status"] == "FAIL"
    assert design.json()["supported_local_checks_executed"] is True
    assert design.json()["supported_local_failure_present"] is True
    assert design.json()["failed_local_check_ids"]
    numeric = json.loads(json.dumps(payload))
    numeric["beam_end_gap"]["value"] = 0.5
    assert _post("/api/v1/calculations/beam-web-splice/preview", numeric).status_code == 422
    moment = json.loads(json.dumps(payload))
    moment["user_moment_l_v_t"]["z"] = "1"
    response = _post("/api/v1/calculations/beam-web-splice/preview", moment)
    assert response.status_code == 422


def test_design_route_maps_canonical_errors_to_422(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(_request: WebSpliceRequestDTO) -> None:
        raise ValueError("controlled mapping failure")

    monkeypatch.setattr(routes, "map_web_splice_request", reject)
    response = _post(
        "/api/v1/calculations/beam-web-splice/design-check",
        _dto(),
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CANONICAL_WEB_SPLICE_MAPPING_INVALID"


def test_production_does_not_read_stage_3_6a_golden() -> None:
    golden_marker = "stage_3_6a_symmetric_double_web_splice_golden_benchmarks_rc1"
    production = ROOT / "backend/src"
    assert not any(
        golden_marker in path.read_text(encoding="utf-8") for path in production.rglob("*.py")
    )
