"""Current native previews for real edits, strict boundary and unit conversion."""

from copy import deepcopy
from typing import Any, cast
from unittest.mock import patch

import pytest
from tests.api.test_angle_column_moment_base_api import TestClient

from frp_master_connection.api.app import create_app
from frp_master_connection.api.column_moment_base import (
    ColumnMomentBaseRequestDTO,
    map_column_moment_base_request,
    serialize_column_moment_base,
)
from frp_master_connection.application.column_moment_base_preview import preview_column_moment_base

BASE = "/api/v1/calculations/wi-rhs-srs-column-moment-base"
EDITS: list[tuple[str, str | int]] = [
    ("actions.axial.value", "30"),
    ("actions.shear_x.value", "-8"),
    ("actions.shear_y.value", "5"),
    ("actions.moment_x.value", "-45"),
    ("actions.moment_y.value", "35"),
    ("column.width.value", "13"),
    ("column.depth.value", "13"),
    ("column.web_thickness.value", ".6"),
    ("column.flange_thickness.value", ".6"),
    ("column.offset_x.value", "1"),
    ("column.offset_y.value", "-1"),
    ("foundation.width_x.value", "42"),
    ("foundation.width_y.value", "42"),
    ("foundation.depth.value", "14"),
]
for face in ("x_positive", "x_negative", "y_positive", "y_negative"):
    EDITS.extend(
        (face + "." + p, cast(str | int, v))
        for p, v in [
            ("angle.geometry.length.value", "6.5"),
            ("angle.geometry.member_leg.value", "8.5"),
            ("angle.geometry.support_leg.value", "6.5"),
            ("angle.geometry.thickness.value", ".6"),
            ("angle.geometry.inside_radius.value", ".3"),
            ("angle.support_pattern.across", 1),
            ("angle.support_pattern.along", 1),
            ("angle.support_pattern.gauge.value", "2.5"),
            ("angle.support_pattern.pitch.value", "1.5"),
            ("angle.support_pattern.center.value", "3.25"),
            ("angle.anchors.nominal_diameter.value", ".45"),
            ("angle.anchors.hole_diameter.value", ".6"),
            ("angle.anchors.specified_embedment.value", "5"),
            ("angle.anchors.washer_outside_diameter.value", "1.4"),
            ("angle.anchors.washer_thickness.value", ".15"),
        ]
    )
    if face != "x_negative":
        EDITS.extend(
            (face + "." + p, cast(str | int, v))
            for p, v in [
                ("extrusion_center.value", ".1"),
                ("angle.member_pattern.along", 1),
                ("angle.member_pattern.gauge.value", "2.5"),
                ("angle.member_pattern.pitch.value", "1.5"),
                ("angle.member_pattern.center.value", "3.25" if face == "x_positive" else "6.25"),
                ("angle.fastener.bolt_diameter.value", ".45"),
                ("angle.fastener.hole_diameter.value", ".6"),
                ("member_hardware.washer_diameter.value", "1.4"),
                ("member_hardware.washer_thickness.value", ".15"),
                ("member_hardware.head_across_flats.value", ".8"),
                ("member_hardware.nut_across_flats.value", ".8"),
                ("member_hardware.head_height.value", ".4"),
                ("member_hardware.nut_height.value", ".5"),
                ("member_hardware.end_extension.value", ".2"),
            ]
        )
        if face == "x_positive":
            EDITS.append((face + ".angle.member_pattern.across", 1))


def changed(data: dict[str, Any], path: str, value: str | int) -> dict[str, Any]:
    result = deepcopy(data)
    target = result
    keys = path.split(".")
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = value
    return result


@pytest.mark.parametrize(("path", "value"), EDITS)
def test_each_valid_edit_returns_current_native_geometry(path: str, value: str | int) -> None:
    client = TestClient(create_app())
    data = client.get(BASE + "/defaults?preset=WI12").json()
    baseline = client.post(BASE + "/preview", json=data).json()
    data = changed(data, path, value)
    answer = client.post(BASE + "/preview", json=data)
    assert answer.status_code == 200, answer.text
    current = answer.json()
    assert current["geometry_status"] == "VALID", current["geometry_invalid_reasons"]
    assert current["engineering_fingerprint"] != baseline["engineering_fingerprint"]
    native = preview_column_moment_base(
        map_column_moment_base_request(ColumnMomentBaseRequestDTO.model_validate(data))
    )
    assert current == serialize_column_moment_base(native).model_dump(mode="json")
    assert (
        map_column_moment_base_request(
            ColumnMomentBaseRequestDTO.model_validate(current["result"]["preview"]["input"])
        )
        == native.input
    )
    assert current["resistance_evaluated"] is False


@pytest.mark.parametrize("preset", ["WI12", "RHS8", "RHS10X8", "SRS8", "SRS10X8"])
def test_unit_switch_preserves_edited_geometry_holes_sources_and_fingerprint(preset: str) -> None:
    client = TestClient(create_app())
    data = client.get(BASE + "/defaults?preset=" + preset).json()
    data["column"]["width"]["value"] = "13"
    data["x_positive"]["angle"]["fastener"]["hole_diameter"]["value"] = ".593"
    data["response_source_reference"] = "not-registered"
    original = client.post(BASE + "/preview", json=data).json()
    si = client.post(BASE + "/convert-units?unit_system=SI", json=data)
    assert si.status_code == 200
    converted = si.json()
    assert converted["column"]["width"] == {"value": "330.2", "unit": "mm"}
    assert converted["x_positive"]["angle"]["fastener"]["hole_diameter"] == {
        "value": "15.0622",
        "unit": "mm",
    }
    assert converted["response_source_reference"] == "not-registered"
    assert (
        client.post(BASE + "/preview", json=converted).json()["engineering_fingerprint"]
        == original["engineering_fingerprint"]
    )
    back = client.post(BASE + "/convert-units?unit_system=US_CUSTOMARY", json=converted).json()
    assert (
        client.post(BASE + "/preview", json=back).json()["engineering_fingerprint"]
        == original["engineering_fingerprint"]
    )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("column.family", "CHANNEL"),
        ("layout", "ONE_X"),
        ("actions.applied_torque_z.value", "1"),
        ("column.material_id", "316SS"),
        ("actions.axial.value", "NaN"),
        ("column.width.value", ""),
        ("x_positive.angle.provider_id", "316SS"),
        ("x_positive.angle.material_id", "CUSTOM"),
    ],
)
def test_strict_domain_rejects_unsupported_or_invalid_input(path: str, value: str) -> None:
    client = TestClient(create_app())
    data = changed(client.get(BASE + "/defaults?preset=WI12").json(), path, value)
    for endpoint in ("/preview", "/design-check"):
        assert client.post(BASE + endpoint, json=data).status_code == 422


def test_preview_never_designs_and_crossing_edit_recovers_without_defaults() -> None:
    client = TestClient(create_app())
    data = client.get(BASE + "/defaults?preset=RHS10X8").json()
    with patch(
        "frp_master_connection.application.column_moment_base_design.evaluate_angle_provider",
        side_effect=AssertionError("Resistance in preview"),
    ):
        good = client.post(BASE + "/preview", json=data).json()
        invalid = changed(data, "y_positive.angle.member_pattern.center.value", "3")
        bad = client.post(BASE + "/preview", json=invalid).json()
        assert bad["geometry_status"] == "INVALID_GEOMETRY"
        assert not bad["design_check_ready"]
        assert not bad["resistance_evaluated"]
        assert not bad["result"]["preview"]["transfers"]
        recovered = client.post(BASE + "/preview", json=data).json()
        assert recovered["engineering_fingerprint"] == good["engineering_fingerprint"]
    check = client.post(BASE + "/design-check", json=data).json()
    assert check["result"]["design"]["status"] == "SOURCE_REQUIRED"
    assert check["result"]["design"]["failed_check_ids"] == []
    data["qualified_source"] = {"qualified": True}
    assert client.post(BASE + "/preview", json=data).status_code == 422


@pytest.mark.parametrize("face", ["y_positive", "y_negative"])
def test_single_centered_wi_flange_bolt_is_rejected_at_physical_web(face: str) -> None:
    client = TestClient(create_app())
    data = changed(
        client.get(BASE + "/defaults?preset=WI12").json(), face + ".angle.member_pattern.across", 1
    )
    invalid = client.post(BASE + "/preview", json=data).json()
    assert invalid["geometry_status"] == "INVALID_GEOMETRY"
    assert any("COLUMN_WEB" in reason for reason in invalid["geometry_invalid_reasons"])
    # An explicit tangential relocation, not an automatic silent move, resolves it.
    data = changed(data, face + ".extrusion_center.value", "2")
    accepted = client.post(BASE + "/preview", json=data).json()
    assert accepted["geometry_status"] == "VALID", accepted["geometry_invalid_reasons"]


@pytest.mark.parametrize(
    ("preset", "path", "value", "reason"),
    [
        ("WI12", "x_positive.angle.fastener.bolt_diameter.value", ".25", "BOLT_DIAMETER"),
        ("WI12", "x_positive.angle.geometry.heel_end_reliefs.0.value", ".1", "HEEL_END_RELIEF"),
        ("WI12", "x_positive.angle.member_pattern.center.value", ".5", "FILLET_SEATING"),
        (
            "WI12",
            "x_positive.angle.member_pattern.gauge.value",
            ".5",
            "MEMBER_HOLE_WASHER_ENVELOPES",
        ),
        ("WI12", "x_positive.angle.anchors.specified_embedment.value", "20", "EMBEDMENT"),
        (
            "WI12",
            "x_positive.angle.support_pattern.center.value",
            ".5",
            "FOUNDATION_HOLE_WASHER_FILLET",
        ),
        (
            "WI12",
            "x_positive.angle.support_pattern.gauge.value",
            ".5",
            "FOUNDATION_HOLE_WASHER_ENVELOPES",
        ),
        ("WI12", "foundation.width_x.value", "8", "OUTSIDE"),
        ("WI12", "x_positive.angle.geometry.length.value", "20", "SOLID_INTERFERENCE"),
        ("RHS8", "x_positive.extrusion_center.value", "20", "FULL_THROUGH_CONTAINMENT"),
    ],
)
def test_invalid_physical_envelopes_are_fail_closed(
    preset: str,
    path: str,
    value: str,
    reason: str,
) -> None:
    client = TestClient(create_app())
    data = client.get(BASE + "/defaults?preset=" + preset).json()
    if ".0." in path:
        data["x_positive"]["angle"]["geometry"]["heel_end_reliefs"][0]["value"] = value
    else:
        data = changed(data, path, value)
    response = client.post(BASE + "/preview", json=data)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["geometry_status"] == "INVALID_GEOMETRY", result
    assert any(reason in r for r in result["geometry_invalid_reasons"]), result
    assert not result["design_check_ready"]


@pytest.mark.parametrize("family", ["WI", "RHS", "SRS"])
@pytest.mark.parametrize("layout", ["TWO_X", "TWO_Y", "FOUR_XY"])
def test_r2_generic_defaults_active_hardware_and_exact_unit_roundtrip(
    family: str, layout: str
) -> None:
    client = TestClient(create_app())
    data = client.get(BASE + f"/defaults?preset={family}&layout={layout}").json()
    for name in ("x_positive", "x_negative", "y_positive", "y_negative"):
        angle = data[name]["angle"]
        assert (angle["member_pattern"]["across"], angle["member_pattern"]["along"]) == (2, 1)
        assert data[name]["extrusion_center"]["value"] == "0"
        assert (angle["support_pattern"]["across"], angle["support_pattern"]["along"]) == (1, 1)
    response = client.post(BASE + "/preview", json=data).json()
    assert response["geometry_status"] == "VALID"
    p = response["result"]["preview"]
    expected_active = 4 if layout == "FOUR_XY" else 2
    assert len(p["geometry"]["angles"]) == expected_active
    assert len(p["geometry"]["foundation_attachments"]) == expected_active
    for angle in p["geometry"]["angles"]:
        group = angle["connector_id"]
        assert (
            sum(
                any(binding[0] == group for binding in bolt["connector_bolt_ids"])
                for bolt in p["geometry"]["member_bolts"]
            )
            == 2
        )
        assert (
            len(
                [
                    b
                    for b in p["geometry"]["foundation_attachments"]
                    if b["group_id"].startswith(group)
                ]
            )
            == 1
        )
    assert response["assembly_status"] == "SOURCE_REQUIRED"
    assert not response["resistance_evaluated"]
    si = client.post(BASE + "/convert-units?unit_system=SI", json=data).json()
    back = client.post(BASE + "/convert-units?unit_system=US_CUSTOMARY", json=si).json()
    for converted in (si, back):
        assert converted["column"]["family"] == family
        assert converted["layout"] == layout
        assert (
            client.post(BASE + "/preview", json=converted).json()["engineering_fingerprint"]
            == response["engineering_fingerprint"]
        )

    for offset in (".25", "-.25"):
        shifted = changed(data, "x_positive.extrusion_center.value", offset)
        shifted = changed(shifted, "y_positive.extrusion_center.value", offset)
        shifted_response = client.post(BASE + "/preview", json=shifted).json()
        assert shifted_response["geometry_status"] == "VALID"
        si = client.post(BASE + "/convert-units?unit_system=SI", json=shifted).json()
        back = client.post(BASE + "/convert-units?unit_system=US_CUSTOMARY", json=si).json()
        for converted in (si, back):
            assert (
                client.post(BASE + "/preview", json=converted).json()["engineering_fingerprint"]
                == shifted_response["engineering_fingerprint"]
            )


@pytest.mark.parametrize("family", ["WI", "RHS", "SRS"])
@pytest.mark.parametrize("layout", ["TWO_X", "TWO_Y", "FOUR_XY"])
def test_r2_overlong_centered_angle_fails_without_auto_relocation(family: str, layout: str) -> None:
    client = TestClient(create_app())
    data = client.get(BASE + f"/defaults?preset={family}&layout={layout}").json()
    owner = "y_positive" if layout == "TWO_Y" else "x_positive"
    original = client.post(BASE + "/preview", json=data).json()
    invalid = changed(data, owner + ".angle.geometry.length.value", "20")
    result = client.post(BASE + "/preview", json=invalid).json()
    assert result["geometry_status"] == "INVALID_GEOMETRY"
    assert any(
        "ANGLE_EXTRUSION_OUTSIDE_SELECTED_FACE" in s for s in result["geometry_invalid_reasons"]
    )
    assert result["result"]["preview"]["input"][owner]["extrusion_center"]["value"] == "0"
    assert not result["design_check_ready"]
    assert not result["resistance_evaluated"]
    assert (
        client.post(BASE + "/preview", json=data).json()["engineering_fingerprint"]
        == original["engineering_fingerprint"]
    )


@pytest.mark.parametrize("family", ["WI", "RHS", "SRS"])
@pytest.mark.parametrize("layout", ["TWO_X", "TWO_Y", "FOUR_XY"])
@pytest.mark.parametrize(
    ("field", "kind", "axis"),
    [
        ("shear_x", "force", "x"),
        ("shear_y", "force", "y"),
        ("axial", "force", "z"),
        ("moment_x", "moment", "x"),
        ("moment_y", "moment", "y"),
    ],
)
@pytest.mark.parametrize("value", ["4", "-4", "0"])
def test_r1_current_column_wrench_signs(
    family: str, layout: str, field: str, kind: str, axis: str, value: str
) -> None:
    client = TestClient(create_app())
    data = client.get(BASE + f"/defaults?preset={family}&layout={layout}").json()
    for action in data["actions"].values():
        action["value"] = "0"
    data["actions"][field]["value"] = value
    response = client.post(BASE + "/preview", json=data).json()
    assert response["geometry_status"] == "VALID"
    p = response["result"]["preview"]
    assert p["column_on_base"][kind][axis] == data["actions"][field]
    assert p["input"]["actions"] == data["actions"]
    assert not response["resistance_evaluated"]
