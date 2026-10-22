"""Actual source geometry to region-specific axes; no new strength methods."""

import math

import pytest
from tests.api.test_hybrid_workflow import BASE, LiveTransport
from tests.hybrid_workflow_fixtures import live_source


@pytest.mark.parametrize("alignment", ["BRACE", "SUPPORT"])
@pytest.mark.parametrize("phi", ["30.9", "45", "60"])
def test_source_axes_follow_members_not_bolt_alignment(alignment: str, phi: str) -> None:
    body = live_source()
    body["alignment"] = alignment
    body["geometry"]["phi"] = phi
    with LiveTransport() as client:
        response = client.post(BASE + "/preview", json=body)
    assert response.status_code == 200, response.text
    scene = response.json()["scene"]
    axes = scene["materialAxes"]
    assert len(axes) == 5
    owned = {
        (p["ownerId"], p["elementId"], p["materialRegionId"])
        for p in scene["boxes"] + scene["meshes"]
    }
    assert {(a["componentId"], a["elementId"], a["materialRegionId"]) for a in axes} == owned
    assert {a["elementId"] for a in axes} == {
        "LEG_1",
        "LEG_2",
        "WEB",
        "TOP_FLANGE",
        "BOTTOM_FLANGE",
    }
    for a in axes:
        vectors = [list(a[key].values()) for key in ("lengthwise", "crosswise", "throughThickness")]
        for i, x in enumerate(vectors):
            assert math.hypot(*x) == pytest.approx(1)
            for y in vectors[i + 1 :]:
                assert sum(v * w for v, w in zip(x, y, strict=True)) == pytest.approx(0, abs=1e-15)
        if a["componentId"] == "member-b":
            assert a["lengthwise"] == {"x": 0, "y": 0, "z": 1}
            assert a["throughThickness"] == (
                {"x": 1, "y": 0, "z": 0} if a["elementId"] == "WEB" else {"x": 0, "y": 1, "z": 0}
            )
        else:
            assert abs(a["lengthwise"]["x"]) == pytest.approx(math.cos(math.radians(float(phi))))
            assert a["throughThickness"] == (
                {"x": 0, "y": 1, "z": 0}
                if a["elementId"] == "LEG_1"
                else {"x": a["lengthwise"]["z"], "y": 0, "z": -a["lengthwise"]["x"]}
            )
    # No root/fillet or junction triad is fabricated by these planar rules.
    assert all("ROOT" not in a["elementId"] for a in axes)
