"""Production controls, exact unit identities and original structural station IDs."""

from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace

import pytest
from tests.api.test_direct_two_bolt import quantity, sab2_body
from tests.direct_sab2_cases import sab2_cases

import frp_master_connection.application.direct_two_bolt_display as display
from frp_master_connection.api.direct_two_bolt import TwoBoltRequestDTO, geometry_response


@pytest.mark.parametrize("name", list(sab2_cases()))
def test_actual_production_review_controls_preserve_independent_fit_and_route(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = sab2_cases()[name]
    saved = deepcopy(body)
    data = geometry_response(TwoBoltRequestDTO.model_validate(body))
    expected = (
        "DOES_NOT_FIT"
        if name in {"narrow-i-fixed-brace-no-fit", "smaller-angle-no-fit", "known-neighbor-no-fit"}
        else "CONDITIONAL"
    )
    assert data["geometry"]["aggregate_state"] == expected
    assert data["structural_eligible"] is (name == "exact-mc1-brace")
    assert data["resistance_evaluated"] is False
    assert data["qualification_activated"] is False
    assert body == saved
    assert data["visualization"]["automatic_bolt_demands"] == []
    assert "result" not in data
    for station in ("B1", "B2"):
        points = [p for p in data["geometry"]["face_points"] if p["station"] == station]
        assert len(points) == 2
        assert points[0]["global_center"] == points[1]["global_center"]
    if name == "known-neighbor-no-fit":
        assert data["geometry"]["washer_state"] == "CONDITIONAL"
        assert data["geometry"]["obstruction_state"] == "DOES_NOT_FIT"
    if name == "finite-cut-root-contact-unknown-access":
        assert data["geometry"]["hardware_state"] == "CONDITIONAL"
        assert data["geometry"]["installation_state"] == "NOT_EVALUATED"
        assert data["direct_support_end_authority"]["condition"] == "FINITE_BOTH_ENDS"
        # Poison only the new display module's former libm dependency. The
        # unchanged native engine retains its own imports. This regression
        # fails for the original platform-dependent mesh and checks the whole
        # result, including every mesh point and all independent fit evidence.
        monkeypatch.setattr(
            display,
            "math",
            SimpleNamespace(cos=lambda _: float("nan"), sin=lambda _: float("nan"), tau=6.0),
            raising=False,
        )
        assert geometry_response(TwoBoltRequestDTO.model_validate(body)) == data


def test_fresh_compatible_visualization_keeps_original_bolt_identity_and_exact_mapping() -> None:
    data = geometry_response(TwoBoltRequestDTO.model_validate(sab2_body()))
    proof = data["legacy_mapping_proof"]
    accepted = proof["accepted_physical_stations"]
    assert data["visualization"]["physical_bolts"] == accepted
    assert {p["legacy_bolt_id"] for p in proof["neutral_to_legacy_station_mapping"]} == {
        p["bolt_id"] for p in accepted
    }
    for mapping in proof["neutral_to_legacy_station_mapping"]:
        assert tuple(
            Decimal(mapping["raw_legacy_global_center"][a]) for a in ("x", "y", "z")
        ) == tuple(Decimal(v) for v in mapping["canonical_global_center_inches"])


def test_inch_mm_spacing_and_signed_offset_are_exact_same_physical_geometry() -> None:
    body = sab2_body(alignment="SUPPORT", spacing=quantity("2.25"))
    body["offset"] = {
        "support_longitudinal": quantity(".125"),
        "support_transverse": quantity("-.25"),
    }
    millimeters = deepcopy(body)
    for q in (millimeters["spacing"], *millimeters["offset"].values()):
        q["value"] = str(Decimal(q["value"]) * Decimal("25.4"))
        q["unit"] = "mm"
    inch_data = geometry_response(TwoBoltRequestDTO.model_validate(body))
    mm_data = geometry_response(TwoBoltRequestDTO.model_validate(millimeters))
    for field in ("pair_input", "geometry", "moment_diagnostic", "comparison", "structural_route"):
        assert inch_data[field] == mm_data[field]
