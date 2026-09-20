"""Stage 3.2-R14B exact region-specific material-basis regression."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import frp_master_connection.application.multirow_orchestration as multirow_module
import frp_master_connection.application.tee_orchestration as tee_module
from frp_master_connection.application import (
    MultiRowPreviewResult,
    TeeConnectorOrchestrationRequest,
    TeeConnectorPreviewResult,
    design_check_tee_connector,
    preview_tee_connector,
    resolve_tee_connector_request,
)
from frp_master_connection.domain import (
    PlanarFixedMaterialOrientation,
    PrincipalAxisFamily,
    SectionFamily,
    SectionTopology,
    canonical_connection_platform_json,
    connection_platform_fingerprint,
    create_standard_section_topology,
)
from frp_master_connection.geometry import UnitVector3D
from tests.tee_fixtures import build_tee_r2_request, build_tee_request

_ROOT = Path(__file__).resolve().parents[3]
_GOLDEN = (
    _ROOT
    / "backend"
    / "tests"
    / "golden"
    / "stage_3_2_r14b_region_specific_material_basis_golden_benchmarks_rc1.json"
)
_SPECIFICATION = (
    _ROOT
    / "docs"
    / "engineering"
    / "FRP_MASTER_CONNECTION_STAGE_3_2_R14B_REGION_SPECIFIC_MATERIAL_BASIS_"
    "ENGINEERING_CORRECTION_SPECIFICATION_RC1.md"
)
_LEDGER = (
    _ROOT / "docs" / "qa" / "STAGE_3_2_R14B_REGION_SPECIFIC_MATERIAL_BASIS_AUTHORITY_LEDGER_RC1.md"
)

_CONTROLLED_HASHES = {
    _SPECIFICATION: "db3dfa722aa08b44ad95f8d789178699ca8e9bee5fadb99306867c69e9b8a74c",
    _GOLDEN: "182516497cb9d789f5aa4adf050641240dc106f1a30f5ebdcc6af1d05c413236",
    _LEDGER: "0fff79c4b6bfdb0c6ded1f2f551ce421d7e2e684bd75b6b84a0ec3154b87ec05",
}

_PREVIEW_TRANSITIONS = {
    "DEFAULT_COLUMN": (
        "b0dd56d48a497eacc7990a37a7b3810fd437d88999464a04e9db5cdc88b0b3d4",
        "552b502f700c0e0d87699e3bb180126e643a5e08a8ddf0b1682fe8b50dbbaf97",
        "5d1b9038b75a641b5065eb023572c3919d5282683689f3c002f4973d13aa6567",
        "709e6ab3c9092f37eba34f12310af21adad3a077ac5360e93e111f7dd4770191",
    ),
    "DEFAULT_BEAM": (
        "2c73c4e2fd30868076d15c2a1a99897b7af910c7fd6b02b0fc2d7193af806c04",
        "8f01be2c104ec11d451d06c7669346c6f2b4eb282dd1e1f7f534aa582a903561",
        "aafaaf5789ad3541535e52d5c7f188e13640b7fe0bc713066e86737e8842942c",
        "050c5f144320275390448a18ad5c0cc4a5b99c782fd30e07435866c5f9e4481e",
    ),
    "ANGLE": (
        "5dda37a9ab8a76efeb069cd5978836635c2bc8c1e75a9f8828245aaff5f76e30",
        "ffe1c6903b79b2b1823a0d925f9ed230c38410b3b3d6f08081b336239dcc5674",
        "c23effca7201b03e3a29b40db4790efe231646e9be5f0be7890d13f651a37d34",
        "28e55f348274faab6e9bc89048d7c05ffba45e24ea5d23a65f89a9cbde4f5570",
    ),
    "CHANNEL": (
        "66fdaefb57e47ff049fe4bac0718dc6cf7d97866c5f293771e0e855a60593aa2",
        "919e1778b78e5b169c84469c6766bdc57c44baa1c2eb425baefc347c94d2c99a",
        "7b258e6650c33b8fbc604d08d2c1896e647130e683ee790e058c750bce607855",
        "cf65ea1c674ff042a77290b56eb02e83d7317e92690ac531ee9c43aa81a5e568",
    ),
    "CONNECTED_W": (
        "1b0eefd6f6d824e740edab2a5a6b34f8df32eb2e367ea40891d30afe5e5304f2",
        "39dff7bae028874bfcfe172fd9ee4304e0d4c077279297e913afb0ff3c37f94b",
        "2331aa4b1ffef3d8aa0a495ffc90f0edb06b92395b129fbc86659484026d4f8b",
        "674efe16644601186bd82a5aee27d58863af8afbc65969b57fa5b645b5f0bec7",
    ),
    "RHS": (
        "f4c216fd08d594484b48093efc14f2b27d0e2d5227e82e9c4a659f0ed132f14a",
        "905abc09065b207978e273669b705927fb7698eb2350bd3673eabcc1fb46bae1",
        "bf983f5293ad841bfc449e7caff8ef265b47b6d55a487e65c3703d47d642bd7f",
        "a89104f1cd308820aa6c4b12a83456c4eb173a4e1b5e0c15d186c6b0a587d7cd",
    ),
    "FLAT": (
        "b0dd56d48a497eacc7990a37a7b3810fd437d88999464a04e9db5cdc88b0b3d4",
        "552b502f700c0e0d87699e3bb180126e643a5e08a8ddf0b1682fe8b50dbbaf97",
        "5d1b9038b75a641b5065eb023572c3919d5282683689f3c002f4973d13aa6567",
        "709e6ab3c9092f37eba34f12310af21adad3a077ac5360e93e111f7dd4770191",
    ),
}

_UNCHANGED_IDENTITIES = {
    "DEFAULT_COLUMN": (
        "b30c12b1eb16143ba1823d434c0d400b0b5275b4ffd88a77a350d109d1d99821",
        "4a10fc65cc3fd818782e8d1fc1e012e5f3dd2d7470bea9f92e6491634329e9e8",
        "dc2a33aaf8459c450912610d4ae8a7c25e38046c4ca45d75952d77a3cfbfe4fd",
        "19eaaa4e57b703e9c9f0a52ddbf2b31a7b1135f7c21388e4de67fef5ea55cd9b",
    ),
    "DEFAULT_BEAM": (
        "280c986ac305428c7f2f0ac9c9940d394dea856fa663ef0fc7dbcb585c9bcf81",
        "cb3fecc9eda7aea44422f70cb23bf23b633539834febd6dcffee6b361091bc47",
        "11176f9a9254da1840bde4e7cb708cbbcd63fdc32fb77762c08e7da085065ac9",
        "3b96e2ce974555ecb7007d6e529c71b14e11c34acf6ec14f9de91175f21b7d38",
    ),
    "ANGLE": (
        "70e2a2f8f02dddbee5648295da21097edce9a41842a6d6419578d8e30a39f2f6",
        "e989b3bc7dbf7c2e04df74ca96563cb8764f28be11bb19ed6ec6b9e5aa7a2e49",
        "dc2a33aaf8459c450912610d4ae8a7c25e38046c4ca45d75952d77a3cfbfe4fd",
        "a3302c815263f6078365f6a3be05eb1205ac74f12f965421d819f8a48c74626f",
    ),
    "CHANNEL": (
        "ca4489f859f4bba24acce0dc880e6cf102156681d1b0e996baa6a8669df81106",
        "ba2267725ea4b1c82c116d0d3cfa7e9aab973ed3474b1c337f7cc2961b87bbb6",
        "dc2a33aaf8459c450912610d4ae8a7c25e38046c4ca45d75952d77a3cfbfe4fd",
        "255b73fa8f091c85d32f4e791360ffddd9a39ff4213480ac0fc833d85282084a",
    ),
    "CONNECTED_W": (
        "0863a69cdae2143a694b3c06c774938e0ece232e2d8a984ba113df8284ced971",
        "b059c2fb814188d177e55eceb6ba687e7e1fa495ecd8462c2b5d04c8b212d012",
        "dc2a33aaf8459c450912610d4ae8a7c25e38046c4ca45d75952d77a3cfbfe4fd",
        "0787c5b83d7da34c4e93e9a7f04763b353b9129529d024cf9ba9ee17ee225738",
    ),
    "RHS": (
        "cbb32000a9d4401d42116623a4d6ff43089fed59d3ff3b899ccc15c49c67131a",
        "b0a5c00ae183eaaa832ddea410578a0e4ee1c80bbf83ad02a9a2b8565849bead",
        "dc2a33aaf8459c450912610d4ae8a7c25e38046c4ca45d75952d77a3cfbfe4fd",
        "12985b7de8b671bedaa131d08963d5e04a29810d3d57728424992d76c32f4d51",
    ),
    "FLAT": (
        "e93e83c5e231d533be29f36f19086c09b0e5b89a3b0388ef3f3ab5e842b8174b",
        "f04bfb8de541656eacfc3ea928ac6a002b524de8d9625f9391fc0605c61f039f",
        "dc2a33aaf8459c450912610d4ae8a7c25e38046c4ca45d75952d77a3cfbfe4fd",
        "2a5bc88b765d8c4c0dc23d98f0af517ce15f4a6c1050a12f265a781f9e456982",
    ),
}


def _cases() -> dict[str, TeeConnectorOrchestrationRequest]:
    return {
        "DEFAULT_COLUMN": build_tee_request(),
        "DEFAULT_BEAM": build_tee_request(role="BEAM"),
        "ANGLE": build_tee_r2_request(),
        "CHANNEL": build_tee_r2_request(profile_family="CHANNEL"),
        "CONNECTED_W": build_tee_r2_request(profile_family="WIDE_FLANGE_I"),
        "RHS": build_tee_r2_request(profile_family="RECTANGULAR_HOLLOW_SECTION"),
        "FLAT": build_tee_r2_request(profile_family="FLAT_PLATE"),
    }


def _legacy_oriented_topology(
    family: SectionFamily,
    lengthwise: PrincipalAxisFamily = PrincipalAxisFamily.X,
) -> SectionTopology:
    source = create_standard_section_topology(family)
    remaining = [axis for axis in PrincipalAxisFamily if axis is not lengthwise]
    return create_standard_section_topology(
        family,
        orientations={
            region.role: PlanarFixedMaterialOrientation(remaining[0], remaining[1])
            for region in source.material_regions
        },
    )


def _tuple(vector: UnitVector3D) -> tuple[float, float, float]:
    return (vector.x, vector.y, vector.z)


def _axes(
    request: TeeConnectorOrchestrationRequest,
) -> dict[tuple[str, str], tuple[tuple[float, float, float], ...]]:
    preview = preview_tee_connector(request)
    assert preview.visualization is not None
    return {
        (item.component_id, item.physical_element_id): (
            _tuple(item.lengthwise),
            _tuple(item.crosswise),
            _tuple(item.through_thickness),
        )
        for item in preview.visualization.base_connection.material_directions
        if item.lengthwise is not None
        and item.crosswise is not None
        and item.through_thickness is not None
    }


def _dot(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> float:
    return sum(a * b for a, b in zip(first, second, strict=True))


def _cross(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _topologies(value: object) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if "standard_family" in value and "material_regions" in value:
            yield value
        for item in value.values():
            yield from _topologies(item)
    elif isinstance(value, list):
        for item in value:
            yield from _topologies(item)


def _canonical_payload(
    resolved: tee_module._TeeResolvedAssembly,
    preview: TeeConnectorPreviewResult,
    interface: str,
) -> str:
    request = resolved.interface_a_request if interface == "A" else resolved.interface_b_request
    result = preview.interface_a.preview if interface == "A" else preview.interface_b.preview
    assert result.visualization is not None
    base_snapshot = replace(result.visualization, automatic_bolt_demands=())
    return multirow_module._canonical_multirow_preview_json(request, base_snapshot)


def _composed_preview_fingerprint(payload: str, preview: MultiRowPreviewResult) -> str:
    base = hashlib.sha256(payload.encode()).hexdigest()
    automatic = preview.automatic_demand_result
    if automatic is None:
        return base
    return hashlib.sha256(
        f"{base}:{automatic.input_fingerprint}:{automatic.result_fingerprint}".encode("ascii")
    ).hexdigest()


def _geometry_projection(resolved: tee_module._TeeResolvedAssembly) -> tuple[object, ...]:
    basis = resolved.context.basis
    placed = (*basis.placed_members, *basis.placed_connectors)
    return (
        tuple((item.component.id, item.global_frame, item.extent) for item in placed),
        tuple(
            (
                item.component.id,
                tuple(
                    (physical.source_element.id, physical.extrusions)
                    for physical in item.physical_elements
                ),
            )
            for item in placed
        ),
        basis.resolved_interfaces,
        tuple(
            (
                group.bolt_group.id,
                tuple(
                    (
                        center.bolt_location.id,
                        center.local_position,
                        center.global_position,
                    )
                    for center in group.master_centers
                ),
                tuple(
                    (axis.bolt_location.id, axis.point, axis.direction) for axis in group.bolt_axes
                ),
                tuple(
                    (
                        path.definition.bolt_location_id,
                        path.center.global_position,
                        path.axis,
                        tuple(
                            (
                                layer.definition.physical_element_id,
                                layer.entry.point,
                                layer.exit.point,
                                layer.raw_thickness,
                                layer.raw_minimum_patch_clearance,
                            )
                            for layer in path.layers
                        ),
                    )
                    for path in group.paths
                ),
            )
            for group in resolved.context.resolved_bolt_groups
        ),
        resolved.interface_a_placement,
        resolved.interface_b_placement,
        resolved.connected_member_end_trim,
        resolved.tee_longitudinal_placement,
    )


def test_controlled_artifacts_are_byte_exact_and_golden_is_test_only() -> None:
    for path, expected in _CONTROLLED_HASHES.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    golden = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    assert golden["artifact"].endswith("GOLDEN_BENCHMARKS_RC1")
    assert golden["common_expected"]["geometry_change"] == "NONE"
    assert golden["common_expected"]["numerical_engineering_result_change"] == "NONE"


def test_golden_after_bases_are_exact_orthogonal_right_handed_and_plane_correct() -> None:
    golden = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    angle = _axes(build_tee_r2_request())
    channel = _axes(build_tee_r2_request(profile_family="CHANNEL"))
    connected_w = _axes(build_tee_r2_request(profile_family="WIDE_FLANGE_I"))
    rhs = _axes(build_tee_r2_request(profile_family="RECTANGULAR_HOLLOW_SECTION"))
    actual = {
        "W_I_WEB": angle[("tee-support", "WEB")],
        "TEE_STEM": angle[("tee-connector", "STEM")],
        "ANGLE_LEG_2": angle[("tee-brace", "LEG_2")],
        "CHANNEL_WEB": channel[("tee-brace", "WEB")],
        "RHS_SIDE_WALL_1_2": rhs[("tee-brace", "SIDE_WALL_1")],
    }
    assert connected_w[("tee-brace", "WEB")] == ((1, 0, 0), (0, 0, 1), (0, -1, 0))
    assert rhs[("tee-brace", "SIDE_WALL_2")] == actual["RHS_SIDE_WALL_1_2"]

    for case in golden["defective_region_corrections"]:
        after = tuple(
            (
                int(case["after"][axis][0]),
                int(case["after"][axis][1]),
                int(case["after"][axis][2]),
            )
            for axis in ("LW", "CW", "TT")
        )
        plane = tuple(
            (int(vector[0]), int(vector[1]), int(vector[2]))
            for vector in case["physical_plane_basis"]
        )
        thickness = (
            int(case["thickness_direction"][0]),
            int(case["thickness_direction"][1]),
            int(case["thickness_direction"][2]),
        )
        basis = actual[case["region_class"]]
        assert basis == after
        lw, cw, tt = basis
        assert _dot(lw, cw) == _dot(lw, tt) == _dot(cw, tt) == 0
        assert _cross(lw, cw) == tt == thickness
        normal = _cross(plane[0], plane[1])
        assert _dot(lw, normal) == _dot(cw, normal) == 0


def test_audited_correct_regions_retain_exact_pre_correction_bases() -> None:
    angle = _axes(build_tee_r2_request())
    channel = _axes(build_tee_r2_request(profile_family="CHANNEL"))
    rhs = _axes(build_tee_r2_request(profile_family="RECTANGULAR_HOLLOW_SECTION"))
    flat = _axes(build_tee_r2_request(profile_family="FLAT_PLATE"))
    assert angle[("tee-connector", "FLANGE")] == ((0, 0, 1), (0, 1, 0), (-1, 0, 0))
    assert angle[("tee-support", "TOP_FLANGE")] == (
        (0, 0, 1),
        (0, -1, 0),
        (1, 0, 0),
    )
    assert angle[("tee-support", "BOTTOM_FLANGE")] == angle[("tee-support", "TOP_FLANGE")]
    assert angle[("tee-brace", "LEG_1")] == ((1, 0, 0), (0, 0, -1), (0, 1, 0))
    assert channel[("tee-brace", "TOP_FLANGE")] == ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    assert channel[("tee-brace", "BOTTOM_FLANGE")] == channel[("tee-brace", "TOP_FLANGE")]
    assert rhs[("tee-brace", "TOP_WALL")] == ((1, 0, 0), (0, -1, 0), (0, 0, -1))
    assert rhs[("tee-brace", "BOTTOM_WALL")] == rhs[("tee-brace", "TOP_WALL")]
    assert flat[("tee-brace", "PLATE")] == ((1, 0, 0), (0, 0, -1), (0, 1, 0))


def test_column_and_beam_global_transforms_retain_exact_local_material_semantics() -> None:
    column = _axes(build_tee_r2_request(role="COLUMN"))
    beam = _axes(build_tee_r2_request(role="BEAM"))
    assert column[("tee-support", "WEB")] == ((0, 0, 1), (-1, 0, 0), (0, -1, 0))
    assert beam[("tee-support", "WEB")] == ((1, 0, 0), (0, 0, -1), (0, 1, 0))
    assert column[("tee-connector", "STEM")] == ((0, 0, 1), (1, 0, 0), (0, 1, 0))
    assert beam[("tee-connector", "STEM")] == ((1, 0, 0), (0, 0, 1), (0, -1, 0))


@pytest.mark.parametrize("case_id", tuple(_PREVIEW_TRANSITIONS))
def test_fingerprint_transitions_are_exact_and_all_other_engineering_is_invariant(
    case_id: str,
) -> None:
    request = _cases()[case_id]
    current_resolved = resolve_tee_connector_request(request)
    current_preview = preview_tee_connector(request)
    current_design = design_check_tee_connector(request)
    with patch.object(tee_module, "_oriented_topology", _legacy_oriented_topology):
        legacy_resolved = resolve_tee_connector_request(request)
        legacy_preview = preview_tee_connector(request)
        legacy_design = design_check_tee_connector(request)

    expected_a_before, expected_b_before, expected_a_after, expected_b_after = _PREVIEW_TRANSITIONS[
        case_id
    ]
    assert legacy_preview.interface_a.preview.preview_fingerprint == expected_a_before
    assert legacy_preview.interface_b.preview.preview_fingerprint == expected_b_before
    assert current_preview.interface_a.preview.preview_fingerprint == expected_a_after
    assert current_preview.interface_b.preview.preview_fingerprint == expected_b_after

    expected_engineering, expected_interface_a, expected_interface_b, expected_result = (
        _UNCHANGED_IDENTITIES[case_id]
    )
    for preview in (legacy_preview, current_preview):
        assert preview.engineering_fingerprint == expected_engineering
        assert preview.interface_a.interface_fingerprint == expected_interface_a
        assert preview.interface_b.interface_fingerprint == expected_interface_b
    assert legacy_design.result_fingerprint == current_design.result_fingerprint == expected_result
    assert legacy_design.assembly_status is current_design.assembly_status
    assert legacy_design.ordinary_pass_allowed is current_design.ordinary_pass_allowed
    assert legacy_design.interface_a.design is not None
    assert current_design.interface_a.design is not None
    assert legacy_design.interface_b.design is not None
    assert current_design.interface_b.design is not None
    for legacy, current in (
        (legacy_design.interface_a.design, current_design.interface_a.design),
        (legacy_design.interface_b.design, current_design.interface_b.design),
    ):
        assert legacy.calculation_result == current.calculation_result
        assert legacy.automatic_demand_result == current.automatic_demand_result
        assert legacy.automatic_handoff_results == current.automatic_handoff_results
        assert legacy.automatic_group_mode_integration == current.automatic_group_mode_integration
    assert _geometry_projection(legacy_resolved) == _geometry_projection(current_resolved)

    for interface in ("A", "B"):
        before_payload = _canonical_payload(legacy_resolved, legacy_preview, interface)
        after_payload = _canonical_payload(current_resolved, current_preview, interface)
        legacy_interface_preview = (
            legacy_preview.interface_a.preview
            if interface == "A"
            else legacy_preview.interface_b.preview
        )
        current_interface_preview = (
            current_preview.interface_a.preview
            if interface == "A"
            else current_preview.interface_b.preview
        )
        assert _composed_preview_fingerprint(before_payload, legacy_interface_preview) == (
            expected_a_before if interface == "A" else expected_b_before
        )
        assert _composed_preview_fingerprint(after_payload, current_interface_preview) == (
            expected_a_after if interface == "A" else expected_b_after
        )
        before_topologies = tuple(_topologies(json.loads(before_payload)))
        after_topologies = tuple(_topologies(json.loads(after_payload)))
        assert len(before_topologies) == len(after_topologies)
        for before, after in zip(before_topologies, after_topologies, strict=True):
            assert before["standard_family"] == after["standard_family"]
            before_regions = {
                item["role"]: item["orientation"] for item in before["material_regions"]
            }
            after_regions = {
                item["role"]: item["orientation"] for item in after["material_regions"]
            }
            corrected = {
                "ANGLE": {"LEG_2"},
                "CHANNEL": {"WEB"},
                "I_SECTION": {"WEB"},
                "RECTANGULAR_TUBE": {"WALL_PAIR_2"},
                "TEE": {"STEM"},
                "WIDE_FLANGE": {"WEB"},
            }.get(after["standard_family"], set())
            for role, orientation in after_regions.items():
                if role in corrected:
                    assert before_regions[role] == {
                        "crosswise_axis": "Y",
                        "through_thickness_axis": "Z",
                    }
                    assert orientation == {
                        "crosswise_axis": "Z",
                        "crosswise_sign": -1,
                        "through_thickness_axis": "Y",
                    }
                else:
                    assert orientation == before_regions[role]


def test_connector_and_scaffold_payload_transitions_are_exact_and_tee_stem_only() -> None:
    request = build_tee_request()
    current = resolve_tee_connector_request(request)
    with patch.object(tee_module, "_oriented_topology", _legacy_oriented_topology):
        legacy = resolve_tee_connector_request(request)
    before_connector = legacy.scaffold.connector_components[0]
    after_connector = current.scaffold.connector_components[0]
    assert connection_platform_fingerprint(before_connector) == (
        "a572003ce54e68ffc0ac68423895eacfeabe9a1c2819e4335451c453bfcd5f72"
    )
    assert connection_platform_fingerprint(after_connector) == (
        "79866e0ba97cc4b2beab2881650b093e5cdfb623afa91e549901756dacef51fe"
    )
    assert connection_platform_fingerprint(legacy.scaffold) == (
        "5719b093cd3101a7325ec2327fe3d306c5027114fc885c1e9051b81034c6367b"
    )
    assert connection_platform_fingerprint(current.scaffold) == (
        "d8376c36c5bfe0245cf8536b1d4ae7b677226a731385ce58870ca66675b8e838"
    )
    before = json.loads(canonical_connection_platform_json(before_connector))
    after = json.loads(canonical_connection_platform_json(after_connector))
    before_regions = before["identity"]["section_topology"]["material_regions"]
    after_regions = after["identity"]["section_topology"]["material_regions"]
    assert {item["id"] for item in before_regions} == {item["id"] for item in after_regions}
    assert next(item for item in before_regions if item["role"] == "FLANGE") == next(
        item for item in after_regions if item["role"] == "FLANGE"
    )
    assert next(item for item in before_regions if item["role"] == "STEM")["orientation"] == {
        "crosswise_axis": "Y",
        "kind": "PLANAR_FIXED",
        "through_thickness_axis": "Z",
    }
    assert next(item for item in after_regions if item["role"] == "STEM")["orientation"] == {
        "crosswise_axis": "Z",
        "crosswise_sign": -1,
        "kind": "PLANAR_FIXED",
        "through_thickness_axis": "Y",
    }


def test_tee_canonicalizer_serializes_only_nondefault_orientation_signs() -> None:
    orientation = PlanarFixedMaterialOrientation(
        PrincipalAxisFamily.Y,
        PrincipalAxisFamily.Z,
        through_thickness_sign=-1,
    )
    assert tee_module._canonical(orientation) == {
        "crosswise_axis": "Y",
        "through_thickness_axis": "Z",
        "through_thickness_sign": -1,
    }
