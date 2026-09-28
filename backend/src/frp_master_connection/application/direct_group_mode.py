"""Direct-only adapter for two penetrated layers on each physical bolt line.

The inherited group-mode engine accepts one inter-row check per physical line.
Partitioning the Direct check inventory by physical layer lets that unchanged
engine evaluate each layer against the same accepted bolt demand scenario.
"""

from __future__ import annotations

from dataclasses import replace

from frp_master_connection.calculation import (
    EccentricGroupModeCompatibilityInput,
    EccentricGroupModeCompatibilityResult,
    EccentricResistanceHandoffInput,
    EccentricResistanceHandoffResult,
    MultiRowRequiredCheckContract,
    calculate_eccentric_group_mode_compatibility,
    calculate_eccentric_resistance_handoff,
)


def evaluate_direct_layered_group_modes(
    handoff_input: EccentricResistanceHandoffInput,
    trace_layers: tuple[str, ...],
) -> tuple[tuple[EccentricResistanceHandoffResult, EccentricGroupModeCompatibilityResult], ...]:
    """Run the accepted handoff and group-mode engines once per Direct layer.

    The parent demand, physical bolt inventory, layer properties and equations
    remain untouched. Global bolt checks run once; layer checks run only for
    their own layer. This prevents either physical shear-out path from being
    silently discarded by the inherited one-check-per-line interface.
    """

    bundle = handoff_input.execution_bundle
    layer_ids = tuple(layer.layer_id for layer in bundle.layers)
    if len(layer_ids) != 2:
        raise ValueError("Direct layered group mode requires exactly two physical layers.")
    results = []
    for index, layer_id in enumerate(layer_ids):
        checks = tuple(
            check
            for check in bundle.checks
            if check.layer_id == layer_id or (index == 0 and check.layer_id is None)
        )
        required = tuple(
            check.check_id
            for check in checks
            if check.check_id in bundle.required_checks.required_check_ids
        )
        layer_bundle = replace(
            bundle,
            required_checks=MultiRowRequiredCheckContract(required),
            checks=checks,
        )
        layer_input = replace(handoff_input, execution_bundle=layer_bundle)
        handoff = calculate_eccentric_resistance_handoff(layer_input)
        group = calculate_eccentric_group_mode_compatibility(
            EccentricGroupModeCompatibilityInput(layer_input, handoff, trace_layers)
        )
        results.append((handoff, group))
    return tuple(results)
