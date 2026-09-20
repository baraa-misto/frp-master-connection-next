"""Pinned owner-golden checks for the Stage 3.2-R2 member/profile slice."""

import hashlib
import json
from pathlib import Path
from typing import cast

from frp_master_connection.domain.member_profile import (
    DIRECT_TEE_CURVED_SURFACE_REASON,
    MemberProfileFamily,
    MemberProfileSurfaceId,
    selectable_profile_surfaces,
)

GOLDEN_PATH = Path(__file__).parents[1] / "golden" / "stage_3_2_r2_member_profile_rc1.json"
OWNER_SHA256 = "A93CAA62946D076A1A2B09354437A5556C6CA6DAF6DD1778DDF2E0ECD0FDBD87"


def _golden() -> dict[str, object]:
    value = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("The Stage 3.2-R2 owner golden must be a JSON object.")
    return cast(dict[str, object], value)


def test_repository_golden_is_byte_exact_owner_copy() -> None:
    raw = GOLDEN_PATH.read_bytes()

    assert len(raw) == 7899
    assert hashlib.sha256(raw).hexdigest().upper() == OWNER_SHA256
    assert raw.endswith(b"\n")
    assert b"\r\n" not in raw
    raw.decode("utf-8")


def test_owner_golden_has_complete_ordered_g1_to_g10_benchmark_set() -> None:
    golden = _golden()
    benchmarks = golden["benchmarks"]
    assert isinstance(benchmarks, list)

    assert golden["version"] == "RC1"
    assert golden["decimal_policy"] == "All engineering numeric values are exact decimal strings."
    assert [benchmark["id"] for benchmark in benchmarks] == [
        f"T32R2_G{index}_{suffix}"
        for index, suffix in enumerate(
            (
                "ANGLE_SURFACES",
                "CHANNEL_WEB_SURFACE",
                "WIDE_FLANGE_SURFACES",
                "RECTANGULAR_HOLLOW_SURFACES",
                "FLAT_PLATE_SURFACES",
                "ROUND_TUBE_DIRECT_TEE_REJECTION",
                "W_SUPPORT_ROLE_LOCAL_INVARIANCE",
                "SURFACE_FILTERING",
                "INTERFACE_LAYOUT_INDEPENDENCE",
                "STALE_AND_DISPLAY_ONLY_STATE",
            ),
            start=1,
        )
    ]


def test_owner_g8_surface_filter_matches_typed_domain_vocabulary() -> None:
    benchmarks = _golden()["benchmarks"]
    assert isinstance(benchmarks, list)
    expected = benchmarks[7]["expected_selectable_surfaces_by_profile"]
    assert isinstance(expected, dict)

    # This historical Stage 3.2-R2 golden owns only the families it names.  Later
    # dormant families are verified by their own controlled artifact and must not
    # rewrite the accepted R2 oracle.
    actual = {
        family_name: [
            surface.value
            for surface in selectable_profile_surfaces(MemberProfileFamily(family_name))
        ]
        for family_name in expected
    }
    assert actual == expected
    assert set(actual[MemberProfileFamily.ANGLE]) == {
        MemberProfileSurfaceId.LEG_Y_OUTER,
        MemberProfileSurfaceId.LEG_Z_OUTER,
    }


def test_owner_g6_requires_fail_closed_round_tube_direct_tee_rejection() -> None:
    benchmarks = _golden()["benchmarks"]
    assert isinstance(benchmarks, list)
    expected = benchmarks[5]["expected"]
    assert isinstance(expected, dict)

    assert expected == {
        "profile_geometry_identity_valid": True,
        "flat_direct_tee_stem_surface_available": False,
        "tee_template_selectable": False,
        "reason": DIRECT_TEE_CURVED_SURFACE_REASON,
    }


def test_owner_g9_and_g10_keep_independent_engineering_and_display_state_semantics() -> None:
    benchmarks = _golden()["benchmarks"]
    assert isinstance(benchmarks, list)
    independence = benchmarks[8]
    stale_state = benchmarks[9]

    assert independence["initial"]["interface_A"] is not independence["initial"]["interface_B"]
    assert independence["expected"]["interface_B_geometry_identity_unchanged"] is True
    assert independence["expected"]["interface_A_geometry_identity_changed"] is True
    assert "profile_dimensions" in stale_state["engineering_changes_that_stale"]
    assert "selected_profile_surface" in stale_state["engineering_changes_that_stale"]
    assert "camera_rotate" in stale_state["display_changes_that_do_not_stale"]
    assert "interface_highlight" in stale_state["display_changes_that_do_not_stale"]
