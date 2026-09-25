"""MAT1 typed-source and physical-owner adapter regression tests."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import cast

import pytest

from frp_master_connection.api.multirow_mapping import map_multirow_request
from frp_master_connection.api.multirow_schemas import MultiRowConnectionRequestDTO
from frp_master_connection.application import multirow_orchestration, web_splice_orchestration
from frp_master_connection.application.mat1_materials import (
    DesignConditions,
    MaterialProperty,
    predefined_catalog,
    session_record,
)
from frp_master_connection.application.mat1_multirow import bind_multirow_material
from frp_master_connection.application.mat1_native import adapt_native_material
from frp_master_connection.application.mat1_scope import (
    MAT1Scope,
    bind_mat1_scope,
    bind_mat1_tee_slot,
    current_scope,
    material_for_owner,
    time_category_for_case,
)
from frp_master_connection.calculation.inputs import TimeEffectCategory
from frp_master_connection.calculation.mat1_flange_body import (
    evaluate_material_flange_plate_body,
)
from frp_master_connection.calculation.properties import MaterialPropertySnapshot
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.calculation.wi_moment_splice_resistance import FlangePlateBodyResult
from frp_master_connection.domain import (
    WEB_SPLICE_SUCCESSOR_CONTRACT_VERSION,
    default_web_splice_request,
)
from tests.test_multirow_api import _payload as multirow_payload


def conditions() -> DesignConditions:
    return DesignConditions(
        Decimal(90),
        Decimal(90),
        Decimal(180),
        "REFERENCE",
        "NONE_DECLARED",
        "SYNTHETIC-1",
        TimeEffectCategory.OTHER_LIVE,
        "REFERENCE",
        uv_weathering="NONE_DECLARED",
        freeze_thaw="NONE_DECLARED",
    )


def test_adapter_rejects_adjusted_source_and_ignores_unknown_property_kind() -> None:
    record = predefined_catalog()[0]
    with pytest.raises(ValueError, match="ALREADY_ADJUSTED_SOURCE"):
        adapt_native_material(
            "FRP", record, replace(conditions(), source_reference_condition="ALREADY_ADJUSTED")
        )
    tensile = record.property("tensile_strength_L")
    assert tensile is not None
    with pytest.raises(ValueError, match="ALREADY_ADJUSTED_PROPERTY"):
        adapt_native_material(
            "FRP",
            replace(record, properties=(replace(tensile, basis="ALREADY_ADJUSTED"),)),
            conditions(),
        )
    unknown = MaterialProperty(
        "synthetic_unmapped_test",
        "Synthetic",
        "SYN",
        Decimal(1),
        "ksi",
        "UNKNOWN",
        "test-only",
        (),
    )
    adapted = adapt_native_material("FRP", replace(record, properties=(unknown,)), conditions())
    assert adapted.adjusted_snapshot.properties == ()
    assert adapted.ledgers == ()
    assert adapted.adjusted_snapshot.explicitly_missing


def test_scope_resolves_physical_aliases_and_restores_request_local_context() -> None:
    record = predefined_catalog()[0]
    base = (record, conditions())
    scope = MAT1Scope(base, {}, "multi-member-tee", frozenset({"BRACE-1"}))
    assert current_scope() is None
    with bind_mat1_scope(scope):
        assert current_scope() is scope
        with pytest.raises(ValueError, match="REQUIRES_ACTIVE_SLOT"):
            scope.material("tee-brace")
        with bind_mat1_tee_slot("BRACE-1"):
            resolved = scope.material("tee-brace")
            assert resolved.id == record.id
            assert scope.material("tee-brace") is resolved
        assert material_for_owner("BRACE-1", resolved) is resolved
        assert time_category_for_case(TimeEffectCategory.DEAD_ONLY) == TimeEffectCategory.OTHER_LIVE
    assert current_scope() is None
    assert material_for_owner("BRACE-1", resolved) is resolved
    assert time_category_for_case(TimeEffectCategory.DEAD_ONLY) == TimeEffectCategory.DEAD_ONLY
    assert scope.unconsumed_overrides() == ()

    support = MAT1Scope(
        base, {}, "wi-beam-frp-support-moment", frozenset({"WI_BEAM", "FRP_SUPPORT"})
    )
    assert support.material("SUPPORT") is support.material("FRP_SUPPORT")
    assert support.material("WI_TOP_FLANGE") is support.material("WI_BEAM")
    concrete_wall = MAT1Scope(base, {}, "wi-beam-concrete-wall-moment", frozenset({"WI_BEAM"}))
    with pytest.raises(ValueError, match="UNMAPPED_PHYSICAL_OWNER"):
        concrete_wall.material("SUPPORT")
    paired = MAT1Scope(
        base,
        {"NEGATIVE_CLIP_ANGLE": (predefined_catalog()[1], conditions())},
        "paired-clip-angle",
        frozenset({"POSITIVE_CLIP_ANGLE", "NEGATIVE_CLIP_ANGLE"}),
    )
    with pytest.raises(ValueError, match="PAIRED_CLIP_ANGLE_MATERIALS_MUST_MATCH"):
        paired.material("single-clip-angle-connector")
    concrete = MAT1Scope(base, {}, "beam-concrete-paired-angle", frozenset({"BEAM"}))
    with pytest.raises(ValueError, match="CONCRETE_INTERFACE_NON_FRP"):
        concrete.material("clip-angle-support")
    with pytest.raises(ValueError, match="UNMAPPED_PHYSICAL_OWNER"):
        concrete.material("NOT_A_COMPONENT")

    # RC2's symmetric plate-body path must reject conflicting physical material
    # selections before reporting a numerical resistance.
    web_request = default_web_splice_request(
        orchestration_contract_version=WEB_SPLICE_SUCCESSOR_CONTRACT_VERSION,
    )
    web_preview = web_splice_orchestration.preview_web_splice(web_request)
    assert isinstance(web_preview, web_splice_orchestration.WebSpliceRC2PreviewResult)
    web_scope = MAT1Scope(
        base,
        {"NEGATIVE_WEB_SPLICE_PLATE": (predefined_catalog()[1], conditions())},
        "beam-web-splice",
        frozenset({"POSITIVE_WEB_SPLICE_PLATE", "NEGATIVE_WEB_SPLICE_PLATE"}),
    )
    with (
        bind_mat1_scope(web_scope),
        pytest.raises(ValueError, match="SYMMETRIC_WEB_SPLICE_PLATE_MATERIALS_MUST_MATCH"),
    ):
        web_splice_orchestration._evaluate_body_interaction(web_request, web_preview)


def test_multirow_successor_keeps_legacy_fields_and_requires_typed_snapshot() -> None:
    dto = MultiRowConnectionRequestDTO.model_validate(multirow_payload())
    legacy = map_multirow_request(dto)
    snapshot = adapt_native_material("ROW", predefined_catalog()[0], conditions()).adjusted_snapshot
    successor = bind_multirow_material(legacy, snapshot)
    assert successor.mat1_material is snapshot
    assert {layer.material_id for layer in successor.layers} == {snapshot.id}
    assert legacy.layers != successor.layers
    with pytest.raises(TypeError, match="typed snapshot"):
        bind_multirow_material(legacy, cast(MaterialPropertySnapshot, object()))

    # The request-local scope must replace the legacy layer identity before the
    # native plans read material fields, while keeping the original request intact.
    scoped = MAT1Scope(
        (predefined_catalog()[0], conditions()),
        {},
        "multi-row",
        frozenset(layer.component_id for layer in legacy.layers),
    )
    with bind_mat1_scope(scoped):
        resolved = multirow_orchestration._resolve(legacy)
    assert all(layer.material.id == snapshot.id for layer in resolved.layer_contexts)
    assert all(layer.material_id != snapshot.id for layer in legacy.layers)

    malformed = replace(successor, mat1_material=cast(MaterialPropertySnapshot, object()))
    with pytest.raises(TypeError, match="typed snapshot"):
        multirow_orchestration._resolve(malformed)

    misbound = replace(successor, layers=legacy.layers)
    with pytest.raises(ValueError, match="material identity must match"):
        multirow_orchestration._resolve(misbound)

    second = replace(legacy.layers[0], layer_id="LAYER-2", component_id="COMPONENT-2")
    doubled = replace(legacy, layers=(legacy.layers[0], second))
    incompatible = MAT1Scope(
        (predefined_catalog()[0], conditions()),
        {second.component_id: (predefined_catalog()[1], conditions())},
        "multi-row",
        frozenset(layer.component_id for layer in doubled.layers),
    )
    with (
        bind_mat1_scope(incompatible),
        pytest.raises(ValueError, match="LINKED_LAYER_MATERIAL_OR_CONDITIONS_REQUIRED"),
    ):
        multirow_orchestration._resolve(doubled)


def test_flange_successor_reuses_zero_force_path_and_rejects_missing_strength() -> None:
    record = predefined_catalog()[0]
    snapshot = adapt_native_material("PLATE", record, conditions()).adjusted_snapshot

    def flange(force: str, material: MaterialPropertySnapshot | None) -> FlangePlateBodyResult:
        return evaluate_material_flange_plate_body(
            component_id="PLATE",
            width=PhysicalQuantity.of("5", Unit.IN),
            thickness=PhysicalQuantity.of("0.5", Unit.IN),
            clear_body_length=PhysicalQuantity.of("6", Unit.IN),
            time_effect_category=TimeEffectCategory.OTHER_LIVE,
            signed_force=PhysicalQuantity.of(force, Unit.KIP),
            material_snapshot=material,
        )

    zero = flange("0", snapshot)
    assert zero.design_capacity is None
    legacy = flange("1", None)
    assert legacy.design_capacity is not None
    sparse = session_record(
        "SESSION:modulus-only",
        "1",
        "Synthetic",
        "Test only",
        "VINYL_ESTER",
        {
            "tensile_modulus_L": {
                "label": "Longitudinal modulus",
                "symbol": "Et,L",
                "value": "3000",
                "unit": "ksi",
                "basis": "MEAN",
            }
        },
    )
    missing = adapt_native_material("PLATE", sparse, conditions()).adjusted_snapshot
    with pytest.raises(ValueError, match="requires FT_L"):
        flange("1", missing)
