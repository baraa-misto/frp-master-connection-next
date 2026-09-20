"""Strict request validation, authenticated source boundary and direct native transport."""

import asyncio
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI

from frp_master_connection.api.angle_column_moment_base import (
    AngleBaseRequestDTO,
    map_angle_base_request,
    serialize_angle_base,
)
from frp_master_connection.api.app import create_app
from frp_master_connection.api.wi_wall_moment_mapping import serialize_wall_moment_value
from frp_master_connection.application.angle_column_base_design import (
    evaluate_angle_column_moment_base,
)
from frp_master_connection.application.angle_column_base_preview import (
    preview_angle_column_moment_base,
)
from frp_master_connection.domain.angle_column_moment_base import (
    default_angle_column_moment_base_request,
)
from frp_master_connection.domain.connection_workspace_defaults import (
    angle_column_workspace_default,
)

BASE = "/api/v1/calculations/angle-column-two-leg-moment-base"


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("actions.axial.value", "30"),
        ("column.leg_x.value", "9"),
        ("leg_1.angle.geometry.length.value", "6.5"),
        ("leg_1.angle.member_pattern.across", 1),
        ("leg_1.angle.member_pattern.along", 1),
        ("leg_1.angle.member_pattern.gauge.value", "2.5"),
        ("leg_1.angle.member_pattern.pitch.value", "1.5"),
        ("leg_1.angle.member_pattern.center.value", "3.25"),
        ("leg_1.angle.support_pattern.across", 1),
        ("leg_1.angle.support_pattern.along", 1),
        ("leg_1.angle.support_pattern.gauge.value", "2.5"),
        ("leg_1.angle.support_pattern.pitch.value", "1.5"),
        ("leg_1.angle.support_pattern.center.value", "3.25"),
        ("leg_1.angle.fastener.bolt_diameter.value", "0.45"),
        ("leg_1.angle.fastener.hole_diameter.value", "0.6"),
        ("leg_1.angle.anchors.nominal_diameter.value", "0.45"),
        ("leg_1.angle.anchors.hole_diameter.value", "0.6"),
        ("leg_2.angle.geometry.length.value", "6.5"),
        ("leg_2.angle.member_pattern.across", 1),
        ("leg_2.angle.member_pattern.along", 1),
        ("leg_2.angle.member_pattern.gauge.value", "2.5"),
        ("leg_2.angle.member_pattern.pitch.value", "1.5"),
        ("leg_2.angle.member_pattern.center.value", "3.25"),
        ("leg_2.angle.support_pattern.across", 1),
        ("leg_2.angle.support_pattern.along", 1),
        ("leg_2.angle.support_pattern.gauge.value", "2.5"),
        ("leg_2.angle.support_pattern.pitch.value", "1.5"),
        ("leg_2.angle.support_pattern.center.value", "3.25"),
        ("leg_2.angle.fastener.bolt_diameter.value", "0.45"),
        ("leg_2.angle.fastener.hole_diameter.value", "0.6"),
        ("leg_2.angle.anchors.nominal_diameter.value", "0.45"),
        ("leg_2.angle.anchors.hole_diameter.value", "0.6"),
    ],
)
def test_owner_review_valid_individual_edits_return_current_native_preview(
    path: str, value: str | int
) -> None:
    client = TestClient(create_app())
    # Preserve the accepted owner-review request independently of later startup defaults.
    data = AngleBaseRequestDTO.model_validate(
        serialize_wall_moment_value(default_angle_column_moment_base_request())
    ).model_dump(mode="json")
    before = client.post(f"{BASE}/preview", json=data).json()
    target = data
    keys = path.split(".")
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = value
    answer = client.post(f"{BASE}/preview", json=data)
    assert answer.status_code == 200, answer.text
    current = answer.json()
    assert current["geometry_status"] == "VALID", current["geometry_invalid_reasons"]
    assert current["engineering_fingerprint"] != before["engineering_fingerprint"]
    assert (
        current["engineering_fingerprint"]
        == current["result"]["preview"]["engineering_fingerprint"]
    )
    native = preview_angle_column_moment_base(
        map_angle_base_request(AngleBaseRequestDTO.model_validate(data))
    )
    assert current == serialize_angle_base(native).model_dump(mode="json")
    assert not current["resistance_evaluated"]
    assert current["result"]["design"] is None
    if path.startswith("actions"):
        # The native geometry fingerprint binds the complete input, including loads;
        # physical records themselves must remain exact on a load-only edit.
        assert {
            k: v for k, v in current["result"]["preview"]["geometry"].items() if k != "fingerprint"
        } == {
            k: v for k, v in before["result"]["preview"]["geometry"].items() if k != "fingerprint"
        }
        assert (
            current["result"]["preview"]["column_on_base"]
            != before["result"]["preview"]["column_on_base"]
        )
    else:
        assert current["result"]["preview"]["geometry"] != before["result"]["preview"]["geometry"]


def test_owner_review_short_column_with_unchanged_hardware_is_genuinely_invalid() -> None:
    client = TestClient(create_app())
    data = AngleBaseRequestDTO.model_validate(
        serialize_wall_moment_value(default_angle_column_moment_base_request())
    ).model_dump(mode="json")
    data["column"]["leg_x"]["value"] = "4"
    data["column"]["leg_y"]["value"] = "3"
    for name, value in zip(
        ("axial", "shear_x", "shear_y", "moment_x", "moment_y"),
        ("30", "-8", "5", "-45", "35"),
        strict=True,
    ):
        data["actions"][name]["value"] = value
    answer = client.post(f"{BASE}/preview", json=data)
    assert answer.status_code == 200
    current = answer.json()
    assert current["geometry_status"] == "INVALID_GEOMETRY"
    assert set(current["geometry_invalid_reasons"]) == {
        "MEMBER_BOLT_PATH:OUTSIDE_SELECTED_LEG_SURFACE",
        "COLUMN_HOLE_WASHER_NOT_ON_EXPOSED_MATCHING_LEG",
    }
    assert not current["design_check_ready"]
    assert not current["resistance_evaluated"]
    # Correct only the two dimensions; no validator or hardware placement changes.
    data["column"]["leg_x"]["value"] = "8"
    data["column"]["leg_y"]["value"] = "8"
    recovered = client.post(f"{BASE}/preview", json=data).json()
    assert recovered["geometry_status"] == "VALID"
    assert recovered["result"]["preview"]["input"]["actions"] == data["actions"]


class TestClient:
    """Use the repository's installed HTTPX/ASGI path, not Starlette's new wrapper."""

    __test__ = False

    def __init__(self, app: FastAPI) -> None:
        self.app = app

    def call(
        self, method: str, url: str, *, params: dict[str, str] | None = None, json: object = None
    ) -> httpx.Response:
        async def run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self.app), base_url="http://testserver"
            ) as client:
                return await client.request(method, url, params=params, json=json)

        return asyncio.run(run())

    def get(self, url: str, *, params: dict[str, str] | None = None) -> httpx.Response:
        return self.call("GET", url, params=params)

    def post(self, url: str, *, json: object = None) -> httpx.Response:
        return self.call("POST", url, json=json)


@pytest.mark.parametrize("si", [False, True])
@pytest.mark.parametrize("unequal", [False, True])
def test_presets_round_trip_through_native_backend_preview_and_design(
    si: bool, unequal: bool
) -> None:
    client = TestClient(create_app())
    r = angle_column_workspace_default(si=si, unequal=unequal)
    response = client.get(
        f"{BASE}/defaults",
        params={"unit_system": "SI" if si else "US_CUSTOMARY", "unequal": str(unequal).lower()},
    )
    assert response.status_code == 200, response.text
    dto = AngleBaseRequestDTO.model_validate(response.json())
    assert map_angle_base_request(dto) == r
    for kind, value in (
        ("preview", preview_angle_column_moment_base(r)),
        ("design-check", evaluate_angle_column_moment_base(r)),
    ):
        answer = client.post(f"{BASE}/{kind}", json=dto.model_dump(mode="json"))
        assert answer.status_code == 200, answer.text
        assert answer.json() == serialize_angle_base(value).model_dump(mode="json")
        assert not answer.json()["resistance_evaluated"]
        assert answer.json()["assembly_status"] == "SOURCE_REQUIRED"


@pytest.mark.parametrize("path", ["preview", "design-check"])
@pytest.mark.parametrize(
    "bad", ["torque", "provider", "nan", "strength", "source_record", "contract", "request_id"]
)
def test_invalid_scope_cannot_be_submitted_or_self_qualified(path: str, bad: str) -> None:
    client = TestClient(create_app())
    data = client.get(f"{BASE}/defaults").json()
    if bad == "torque":
        data["actions"]["applied_torque_z"]["value"] = "1"
    elif bad == "provider":
        data["leg_1"]["angle"]["provider_id"] = "316SS"
    elif bad == "nan":
        data["actions"]["axial"]["value"] = "NaN"
    elif bad == "strength":
        data["leg_1"]["angle"]["fastener"]["nominal_shear_stress"] = {"value": "100", "unit": "MPa"}
    elif bad == "source_record":
        data["qualified_source"] = {"approved": True}
    elif bad == "contract":
        data["contract"] = "3.7-RC1"
    else:
        data["request_id"] = " "
    assert client.post(f"{BASE}/{path}", json=data).status_code == 422


def test_preview_never_invokes_resistance_and_invalid_geometry_retains_total_only() -> None:
    client = TestClient(create_app())
    data = client.get(f"{BASE}/defaults").json()
    with patch(
        "frp_master_connection.application.angle_column_base_design.evaluate_angle_provider",
        side_effect=AssertionError("Preview called resistance"),
    ):
        assert client.post(f"{BASE}/preview", json=data).status_code == 200
    data["leg_1"]["extrusion_center"]["value"] = "-50"
    result = client.post(f"{BASE}/design-check", json=data).json()
    assert result["geometry_status"] == "INVALID_GEOMETRY"
    assert result["assembly_status"] == "INVALID_GEOMETRY"
    assert not result["design_check_ready"]
    assert not result["result"]["preview"]["transfers"]
    assert result["result"]["preview"]["required_total_foundation_action"] is not None


@pytest.mark.parametrize("path", ["preview", "design-check"])
@pytest.mark.parametrize("exception", [ArithmeticError, KeyError, TypeError, ValueError])
def test_mapping_errors_remain_422(path: str, exception: type[Exception]) -> None:
    client = TestClient(create_app())
    data = client.get(f"{BASE}/defaults").json()
    with patch(
        "frp_master_connection.api.angle_column_moment_base.map_angle_base_request",
        side_effect=exception("Invalid record"),
    ):
        assert client.post(f"{BASE}/{path}", json=data).status_code == 422
