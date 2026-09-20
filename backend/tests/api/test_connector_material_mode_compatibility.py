"""Native expanded profile/support adapters use actual accepted fixture builders."""

from typing import Any

import pytest
from tests.api.test_connector_materials import http
from tests.clip_angle_fixtures import build_clip_angle_c2_payload
from tests.column_base_profile_fixtures import build_column_base_profile_payload
from tests.paired_clip_angle_fixtures import build_paired_clip_angle_c3_payload
from tests.tee_fixtures import build_tee_c2_payload
from tests.test_wi_frp_support_moment_api import payload as support_payload

from frp_master_connection.api.connector_material_native import (
    FAMILIES,
    NativeFamilyInput,
    native_family_providers,
)
from frp_master_connection.application.connector_material_assembly import (
    canonical_material_assembly,
)
from frp_master_connection.calculation.connector_material_provider import (
    dispatch_connector_provider,
)
from frp_master_connection.domain.connector_materials import ComponentRole
from frp_master_connection.domain.wi_frp_support_moment import SupportMode

PROFILES = (
    "FLAT_PLATE",
    "ANGLE",
    "CHANNEL",
    "WIDE_FLANGE_I",
    "RECTANGULAR_HOLLOW_SECTION",
    "SOLID_RECTANGULAR_SECTION",
)
SUPPORTS = (
    "W_COLUMN_FLANGE",
    "W_BEAM_FLANGE",
    "W_COLUMN_WEB",
    "CHANNEL_COLUMN_WEB",
    "ANGLE_COLUMN_LEG",
    "RECTANGULAR_HOLLOW_COLUMN_WALL",
    "SOLID_RECTANGULAR_COLUMN_FACE",
)
BUILDERS = {
    "tee-connector": build_tee_c2_payload,
    "clip-angle": build_clip_angle_c2_payload,
    "paired-clip-angle": build_paired_clip_angle_c3_payload,
}


def verify_native(route: str, wire: dict[str, Any]) -> None:
    family = FAMILIES[route]
    before = family.preview(wire)
    registry = native_family_providers()
    provider = registry["NATIVE_FRP:" + route]
    expected = family.design(wire)
    assert provider.evaluate(NativeFamilyInput(route, wire)) == expected
    # These existing fixture builders do not promise every Cartesian geometry is
    # applicable. Preserve a native INVALID result; do not invent a valid body.
    geometry = getattr(before, "geometry", None)
    status = str(getattr(geometry or before, "geometry_status", getattr(geometry, "status", "")))
    if "INVALID" in status:
        with pytest.raises(ValueError, match="valid native canonical assembly"):
            canonical_material_assembly(route, before)
        rejected = http(
            "POST",
            "/api/v1/connector-materials/plan",
            {
                "route_id": route,
                "product_id": family.product_id,
                "native_input": wire,
            },
        )
        assert rejected.status_code == 422
        assert family.preview(wire) == before
        return
    assembly = canonical_material_assembly(route, before)
    assert all(c.role is not ComponentRole.UNCLASSIFIED for c in assembly.components)
    component = next(c for c in assembly.components if c.role is ComponentRole.CONNECTOR_BODY)
    result = dispatch_connector_provider(
        component,
        component.material,
        provider.capability.provider_id,
        provider.capability.method,
        NativeFamilyInput(route, wire),
        registry,
    )
    assert result.status == "NATIVE_RESULT_UNMODIFIED"
    assert result.native_result == expected
    assert family.preview(wire) == before


@pytest.mark.parametrize("route", tuple(BUILDERS))
@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("support", SUPPORTS)
def test_expanded_connected_support_matrix_native_identity(
    route: str,
    profile: str,
    support: str,
) -> None:
    verify_native(route, BUILDERS[route](connected_profile_family=profile, support_target=support))


@pytest.mark.parametrize("mode", tuple(SupportMode))
@pytest.mark.parametrize("si", [False, True])
def test_all_receiving_support_moment_modes_native_identity(mode: SupportMode, si: bool) -> None:
    verify_native("wi-beam-frp-support-moment", support_payload(mode, si=si))


@pytest.mark.parametrize("shape", ["WI", "RHS", "SRS"])
@pytest.mark.parametrize("layout", ["TWO_X", "TWO_Y", "FOUR_XY"])
@pytest.mark.parametrize("unit", ["US_CUSTOMARY", "SI"])
def test_column_moment_profile_layout_units_native_identity(
    shape: str, layout: str, unit: str
) -> None:
    route = "wi-rhs-srs-column-moment-base"
    response = http(
        "GET",
        f"/api/v1/calculations/{route}/defaults?preset={shape}&layout={layout}&unit_system={unit}",
    )
    assert response.status_code == 200
    verify_native(route, response.json())


@pytest.mark.parametrize(
    "profile", ["WIDE_FLANGE_I", "RECTANGULAR_HOLLOW_SECTION", "SOLID_RECTANGULAR_SECTION", "ANGLE"]
)
@pytest.mark.parametrize("assembly", ["SINGLE_BASE_ANGLE", "DOUBLE_BASE_ANGLES"])
def test_column_shear_profiles_assemblies_native_identity(profile: str, assembly: str) -> None:
    verify_native(
        "column-base-web-angles",
        build_column_base_profile_payload(
            profile_family=profile,
            assembly=assembly,
        ),
    )
