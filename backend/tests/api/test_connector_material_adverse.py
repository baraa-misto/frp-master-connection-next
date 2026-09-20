"""Adversarial server-record and source-domain validation, including tamper probes."""

from dataclasses import dataclass, replace
from typing import Any, cast

import pytest
from tests.api.test_connector_materials import native_payload
from tests.calculation.test_connector_material_foundation import (
    BODY,
    SS,
    plan,
    property_record,
    signature,
    source_record,
)

from frp_master_connection.api.connector_material_native import FAMILIES
from frp_master_connection.application.connector_material_assembly import (
    canonical_material_assembly,
)
from frp_master_connection.application.visualization import VisualizationComponent
from frp_master_connection.calculation.connector_material_plan import MaterialAssignment
from frp_master_connection.calculation.quantities import PhysicalQuantity, Unit
from frp_master_connection.domain import ComponentMaterialKind
from frp_master_connection.domain.connector_materials import revalidate_response


@dataclass(frozen=True)
class SceneProbe:
    visualization: object | None
    engineering_fingerprint: str | None = "TEST_ONLY"
    geometry_status: str = "VALID"


def test_server_record_validation_rejects_incomplete_ambiguous_and_nonfrp_primary() -> None:
    for probe in (SceneProbe(None), SceneProbe((), geometry_status="INVALID")):
        with pytest.raises(ValueError, match="valid native"):
            canonical_material_assembly("test-only", probe)
    with pytest.raises(ValueError, match="no classified"):
        canonical_material_assembly("test-only", SceneProbe(()))
    native: Any = FAMILIES["single-bolt"].preview(native_payload("single-bolt"))
    member: VisualizationComponent = native.visualization.components[0]
    with pytest.raises(ValueError, match="PRIMARY_MEMBER_FRP_ONLY"):
        canonical_material_assembly(
            "single-bolt", SceneProbe((replace(member, material_kind=ComponentMaterialKind.STEEL),))
        )
    with pytest.raises(ValueError, match="identity policy"):
        canonical_material_assembly("single-bolt", SceneProbe((member,), None))
    base: Any = FAMILIES["wi-rhs-srs-column-moment-base"].preview(
        native_payload("wi-rhs-srs-column-moment-base")
    )
    box = base.geometry.parts[0].box
    unclassified = canonical_material_assembly(
        "test-only", SceneProbe((replace(box, component_id="unknown"),))
    )
    with pytest.raises(ValueError, match="UNCLASSIFIED"):
        plan(unclassified.components, (MaterialAssignment("unknown", SS),))
    with pytest.raises(ValueError, match="Conflicting native physical role"):
        canonical_material_assembly(
            "test-only",
            SceneProbe((replace(member, id="FOUNDATION"), replace(box, component_id="FOUNDATION"))),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("material", "316"),
        ("properties", []),
        ("properties", ("not-a-property",)),
        ("assembly_restrictions", []),
        ("content_sha256", None),
    ],
)
def test_source_records_reject_untyped_mutable_domains(field: str, value: object) -> None:
    with pytest.raises(TypeError, match=r"typed|immutable|SHA-256"):
        replace(source_record(), **{field: cast(Any, value)})


def test_canonical_material_and_response_types_are_not_coerced() -> None:
    with pytest.raises(TypeError, match="typed"):
        replace(BODY, material=cast(Any, "316"))
    with pytest.raises(TypeError, match="typed"):
        replace(signature(), materials=(("ANGLE_1", cast(Any, "316")),))
    assert not revalidate_response(
        signature(), replace(signature(), environment_domain="HIGH_TEMPERATURE")
    ).applicable


def test_nonoverlapping_source_domains_are_distinct_and_original_units_are_retained() -> None:
    first = property_record()
    second = replace(
        first,
        lower_size=PhysicalQuantity.of(3, Unit.IN),
        upper_size=PhysicalQuantity.of(4, Unit.IN),
    )
    source = source_record((first, second))
    assert source.properties == (first, second)
    assert source_record((first, replace(first, property_name="ANOTHER_PROPERTY"))).properties
    with pytest.raises(ValueError, match="size domain"):
        replace(
            first,
            lower_size=PhysicalQuantity.of(1, Unit.KIP),
            upper_size=PhysicalQuantity.of(2, Unit.KIP),
        )


@pytest.mark.parametrize("value", [True, False, "NaN", "Infinity", "-Infinity"])
def test_nonfinite_and_boolean_properties_are_rejected_by_native_quantity_contract(
    value: object,
) -> None:
    with pytest.raises((TypeError, ValueError), match=r"finite|bool|Boolean|numeric|decimal"):
        PhysicalQuantity.of(cast(Any, value), Unit.KSI)
