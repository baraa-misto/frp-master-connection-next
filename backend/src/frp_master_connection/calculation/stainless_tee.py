"""C2-T isolated monolithic hot Tee provider; no public or historical Tee integration."""

from frp_master_connection.calculation.stainless_angle import ShapeResult, evaluate_shape
from frp_master_connection.domain.stainless_shape import ShapeContext, ShapeRequest

PROVIDER = "C2_T_AISC_370_25_A276_A484_HOT_SHAPE_LRFD_RC1"


def evaluate_stainless_tee(r: ShapeRequest, context: ShapeContext) -> ShapeResult:
    return evaluate_shape(r, context, "TEE", PROVIDER)
