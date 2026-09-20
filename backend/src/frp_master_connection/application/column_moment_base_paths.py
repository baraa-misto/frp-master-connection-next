"""Native connected-leaf paths only after the actual coupled response proves applicability."""

from dataclasses import replace
from fractions import Fraction
from typing import cast

from frp_master_connection.application.angle_column_base_local import connector_group_mapping
from frp_master_connection.application.angle_column_base_preview import (
    AngleBasePreview,
    AngleBaseTransfer,
)
from frp_master_connection.application.column_moment_base_preview import (
    ColumnMomentPreview,
    ColumnMomentTransfer,
)
from frp_master_connection.application.multirow_orchestration import _execution_bundle, _resolve
from frp_master_connection.application.wi_frp_support_local_checks import SupportLocalCheck
from frp_master_connection.calculation import PublishedCodeUnitBasis
from frp_master_connection.calculation.angle_column_base_response import ZERO
from frp_master_connection.calculation.angle_connector_core import components
from frp_master_connection.calculation.multirow_engine import (
    MultiRowCheckFamily,
    calculate_multirow_connection,
)
from frp_master_connection.calculation.quantities import create_standard_hole
from frp_master_connection.domain.column_moment_base import Face


def connector_paths(
    preview: ColumnMomentPreview, transfer: ColumnMomentTransfer
) -> tuple[SupportLocalCheck, ...]:
    record = preview.response.response
    if record is None:
        return ()
    angle = next(a for a in preview.geometry.angles if a.connector_id == transfer.connector_id)
    spec = preview.input.physical_connector(cast(Face, transfer.connector_id)).angle
    solution = transfer.in_plane_reference_candidate.solution
    actions = tuple(
        layer.action
        for bolt in record.bolts
        for layer in bolt.layers
        if layer.layer_id == transfer.connector_id + "_MEMBER_LEG"
    )
    plane = tuple(
        tuple(
            sum(
                (f * Fraction(v) for f, v in zip(components(action.force), axis, strict=True)),
                Fraction(0),
            )
            for axis in (angle.frame.a, angle.frame.b)
        )
        for action in actions
    )
    # This gate never substitutes an elastic candidate for the source response.
    # Constant, concentric, extrusion-directed qualified forces must match it.
    compatible = bool(plane) and all(
        p == plane[0] and components(a.moment) == ZERO for p, a in zip(plane, actions, strict=True)
    )
    result = []
    reason = "OBLIQUE_COUPLED_OR_HEEL_DIRECTED_PATH_APPLICABILITY_REQUIRED"
    if (
        compatible
        and solution.force[0] != 0
        and solution.force[1] == 0
        and solution.centroid_moment == 0
        and spec.member_pattern.across == 2
        and plane[0] == (solution.force[0] / len(plane), Fraction(0))
    ):
        if (
            spec.fastener.hole_diameter
            != create_standard_hole(
                spec.fastener.bolt_diameter, PublishedCodeUnitBasis.US_CUSTOMARY_PRINTED
            ).hole_diameter
        ):
            reason = "NONSTANDARD_HOLE_LOCAL_PATH_AUTHORITY_REQUIRED"
        else:
            # Structural reuse of the physical leaf mapper (angles/specification,
            # connector ID and core member action only), not the Stage 4.4 solver.
            mapping = connector_group_mapping(
                cast(AngleBasePreview, preview), cast(AngleBaseTransfer, transfer)
            )
            mapping = replace(
                mapping,
                request_id="stage45:" + transfer.connector_id,
                connection_id="STAGE45",
                load_combination_id="STAGE45_QUALIFIED_MEMBER_ACTION",
                provenance=replace(
                    mapping.provenance,
                    source_method="STAGE45_QUALIFIED_CONSTANT_MEMBER_PLANE",
                    source_document_or_calculation="STAGE45_RC1",
                    load_combination="STAGE45_QUALIFIED_MEMBER_ACTION",
                ),
            )
            native = calculate_multirow_connection(_execution_bundle(mapping, _resolve(mapping)))
            for check in native.results:
                if check.limit_state in {
                    MultiRowCheckFamily.FIRST_ROW_NET_TENSION,
                    MultiRowCheckFamily.INTERROW_SHEAR_OUT,
                }:
                    result.append(
                        SupportLocalCheck(
                            check.result_id,
                            transfer.connector_id,
                            transfer.connector_id + "_MEMBER_LEG",
                            None,
                            check.limit_state.value,
                            check.numerical_comparison.value,
                            check.demand,
                            check.design_resistance,
                            check,
                            None,
                            "NATIVE_ACTUAL_CONNECTED_LEAF_NOT_COMPLETE_ANGLE",
                            preview.response.fingerprint,
                            "LONGITUDINAL",
                        )
                    )
            reason = "HEEL_JUNCTION_CLEAVAGE_BLOCK_PATHS_REQUIRE_QUALIFIED_COVERAGE"
    result.append(
        SupportLocalCheck(
            "CONNECTOR_PATH_SCOPE:" + transfer.connector_id,
            transfer.connector_id,
            transfer.connector_id + "_MEMBER_LEG",
            None,
            "LOCAL_PATH_APPLICABILITY",
            "SOURCE_REQUIRED",
            None,
            None,
            None,
            None,
            reason,
            preview.response.fingerprint,
            "ACTUAL_R14B_REGION_BASES",
        )
    )
    return tuple(result)
