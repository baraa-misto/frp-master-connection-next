import type {
  SingleBoltEvaluationRequest,
  SingleBoltEvaluationResponse,
  SingleBoltPreviewRequest,
  SingleBoltPreviewResponse,
} from "./contracts";
import type {
  ClipAngleDesignResponse,
  ClipAnglePreviewResponse,
  ClipAngleRequest,
} from "./clipAngleContracts";
import type {
  MultiRowConnectionRequest,
  MultiRowDesignResponse,
  MultiRowPreviewResponse,
} from "./multirowContracts";
import type {
  PairedClipAngleDesignResponse,
  PairedClipAnglePreviewResponse,
  PairedClipAngleRequest,
} from "./pairedClipAngleContracts";
import type {
  TeeConnectorDesignResponse,
  TeeConnectorPreviewResponse,
  TeeConnectorRequest,
} from "./teeContracts";
import type {
  MultiMemberTeeDesignResponse,
  MultiMemberTeePreviewResponse,
  MultiMemberTeeRequest,
} from "./multiMemberTeeContracts";
import type {
  BeamConcretePairedAngleDesignResponse,
  BeamConcretePairedAnglePreviewResponse,
  BeamConcretePairedAngleRequest,
} from "./beamConcretePairedAngleContracts";
import type {
  DirectSideLapConcreteRequest,
  DirectSideLapDesignResponse,
  DirectSideLapPreviewResponse,
} from "./directSideLapConcreteContracts";
import type {
  ColumnBaseDesignResponse,
  ColumnBasePreviewResponse,
  ColumnBaseWebAngleRequest,
} from "./columnBaseWebAngleContracts";
import type { WebSpliceDesignResponse, WebSplicePreviewResponse, WebSpliceRequest } from "./webSpliceContracts";
import type { WIMomentSpliceDesignResponse, WIMomentSplicePreviewResponse, WIMomentSpliceRequest } from "./wiMomentSpliceContracts";
import type { ChannelMomentSpliceDesignResponse, ChannelMomentSplicePreviewResponse, ChannelMomentSpliceRequest } from "./channelMomentSpliceContracts";

export const SINGLE_BOLT_EVALUATION_PATH = "/api/v1/calculations/single-bolt/evaluate";
export const SINGLE_BOLT_PREVIEW_PATH = "/api/v1/calculations/single-bolt/preview";
export const MULTIROW_PREVIEW_PATH = "/api/v1/calculations/multi-row/preview";
export const MULTIROW_DESIGN_PATH = "/api/v1/calculations/multi-row/design-check";
export const TEE_CONNECTOR_PREVIEW_PATH = "/api/v1/calculations/tee-connector/preview";
export const TEE_CONNECTOR_DESIGN_PATH = "/api/v1/calculations/tee-connector/design-check";
export const CLIP_ANGLE_PREVIEW_PATH = "/api/v1/calculations/clip-angle/preview";
export const CLIP_ANGLE_DESIGN_PATH = "/api/v1/calculations/clip-angle/design-check";
export const PAIRED_CLIP_ANGLE_PREVIEW_PATH = "/api/v1/calculations/paired-clip-angle/preview";
export const PAIRED_CLIP_ANGLE_DESIGN_PATH = "/api/v1/calculations/paired-clip-angle/design-check";
export const MULTI_MEMBER_TEE_PREVIEW_PATH = "/api/v1/calculations/multi-member-tee/preview";
export const MULTI_MEMBER_TEE_DESIGN_PATH = "/api/v1/calculations/multi-member-tee/design-check";
export const BEAM_CONCRETE_PAIRED_ANGLE_PREVIEW_PATH = "/api/v1/calculations/beam-concrete-paired-angle/preview";
export const BEAM_CONCRETE_PAIRED_ANGLE_DESIGN_PATH = "/api/v1/calculations/beam-concrete-paired-angle/design-check";
export const DIRECT_SIDE_LAP_CONCRETE_PREVIEW_PATH = "/api/v1/calculations/direct-side-lap-concrete/preview";
export const DIRECT_SIDE_LAP_CONCRETE_DESIGN_PATH = "/api/v1/calculations/direct-side-lap-concrete/design-check";
export const COLUMN_BASE_WEB_ANGLE_PREVIEW_PATH = "/api/v1/calculations/column-base-web-angles/preview";
export const COLUMN_BASE_WEB_ANGLE_DESIGN_PATH = "/api/v1/calculations/column-base-web-angles/design-check";
export const WEB_SPLICE_PREVIEW_PATH = "/api/v1/calculations/beam-web-splice/preview";
export const WEB_SPLICE_DESIGN_PATH = "/api/v1/calculations/beam-web-splice/design-check";
export const WI_MOMENT_SPLICE_PREVIEW_PATH = "/api/v1/calculations/wi-major-axis-moment-splice/preview";
export const WI_MOMENT_SPLICE_DESIGN_PATH = "/api/v1/calculations/wi-major-axis-moment-splice/design-check";
export const CHANNEL_MOMENT_SPLICE_PREVIEW_PATH = "/api/v1/calculations/channel-major-axis-moment-splice/preview";
export const CHANNEL_MOMENT_SPLICE_DESIGN_PATH = "/api/v1/calculations/channel-major-axis-moment-splice/design-check";

export type EvaluationErrorKind = "NETWORK" | "VALIDATION" | "IDENTITY" | "HTTP" | "RESPONSE";

export class EvaluationTransportError extends Error {
  constructor(
    readonly kind: EvaluationErrorKind,
    readonly status: number | null,
    message: string,
    readonly detail: unknown = null,
  ) {
    super(message);
    this.name = "EvaluationTransportError";
  }
}

function isEvaluationResponse(value: unknown): value is SingleBoltEvaluationResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as {
    api_transport_schema_version?: unknown;
    results?: unknown;
    visualization?: unknown;
  };
  const visualization = candidate.visualization as { frames?: unknown } | null | undefined;
  return (
    candidate.api_transport_schema_version === "0.5.0-draft" &&
    Array.isArray(candidate.results) &&
    typeof visualization === "object" &&
    visualization !== null &&
    Array.isArray(visualization.frames)
  );
}

function isPreviewResponse(value: unknown): value is SingleBoltPreviewResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as {
    preview_schema_version?: unknown;
    geometry_status?: unknown;
    visualization?: unknown;
    design_check_ready?: unknown;
  };
  const statuses = new Set([
    "PREVIEW_VALID",
    "PREVIEW_INVALID_GEOMETRY",
    "PREVIEW_INCOMPLETE_INPUT",
    "PREVIEW_UNSUPPORTED",
  ]);
  return (
    candidate.preview_schema_version === "0.2.0-draft" &&
    typeof candidate.geometry_status === "string" &&
    statuses.has(candidate.geometry_status) &&
    (candidate.visualization === null || typeof candidate.visualization === "object") &&
    typeof candidate.design_check_ready === "boolean"
  );
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function evaluateSingleBolt(
  request: SingleBoltEvaluationRequest,
  signal?: AbortSignal,
): Promise<SingleBoltEvaluationResponse> {
  let response: Response;
  try {
    response = await fetch(SINGLE_BOLT_EVALUATION_PATH, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      credentials: "same-origin",
      ...(signal === undefined ? {} : { signal }),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new EvaluationTransportError(
      "NETWORK",
      null,
      "The calculation service could not be reached.",
      error,
    );
  }
  const payload = await readJson(response);
  if (!response.ok) {
    const kind: EvaluationErrorKind =
      response.status === 422
        ? "VALIDATION"
        : response.status === 401 || response.status === 403
          ? "IDENTITY"
          : "HTTP";
    throw new EvaluationTransportError(
      kind,
      response.status,
      kind === "VALIDATION"
        ? "The server rejected one or more request fields."
        : kind === "IDENTITY"
          ? "The server did not accept the trusted identity context."
          : `The calculation service returned HTTP ${String(response.status)}.`,
      payload,
    );
  }
  if (!isEvaluationResponse(payload)) {
    throw new EvaluationTransportError(
      "RESPONSE",
      response.status,
      "The server returned an unsupported calculation response contract.",
      payload,
    );
  }
  return payload;
}

export async function previewSingleBolt(
  request: SingleBoltPreviewRequest,
  signal: AbortSignal,
): Promise<SingleBoltPreviewResponse> {
  let response: Response;
  try {
    response = await fetch(SINGLE_BOLT_PREVIEW_PATH, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      credentials: "same-origin",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new EvaluationTransportError(
      "NETWORK",
      null,
      "The canonical preview service could not be reached.",
      error,
    );
  }
  const payload = await readJson(response);
  if (!response.ok) {
    const kind: EvaluationErrorKind =
      response.status === 422
        ? "VALIDATION"
        : response.status === 401 || response.status === 403
          ? "IDENTITY"
          : "HTTP";
    throw new EvaluationTransportError(
      kind,
      response.status,
      kind === "VALIDATION"
        ? "The server rejected one or more preview fields."
        : kind === "IDENTITY"
          ? "The server did not accept the trusted identity context."
          : `The preview service returned HTTP ${String(response.status)}.`,
      payload,
    );
  }
  if (!isPreviewResponse(payload)) {
    throw new EvaluationTransportError(
      "RESPONSE",
      response.status,
      "The server returned an unsupported preview response contract.",
      payload,
    );
  }
  return payload;
}

function isMultiRowPreviewResponse(value: unknown): value is MultiRowPreviewResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<MultiRowPreviewResponse>;
  return (
    candidate.api_transport_schema_version === "0.3.0-draft" &&
    candidate.orchestration_contract_version === "2.5C-RC1" &&
    candidate.resistance_evaluated === false &&
    typeof candidate.preview_fingerprint === "string"
  );
}

function isMultiRowDesignResponse(value: unknown): value is MultiRowDesignResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as {
    api_transport_schema_version?: unknown;
    orchestration_contract_version?: unknown;
    preview?: unknown;
  };
  return (
    candidate.api_transport_schema_version === "0.3.0-draft" &&
    candidate.orchestration_contract_version === "2.5C-RC1" &&
    typeof candidate.preview === "object" &&
    candidate.preview !== null
  );
}

async function postMultiRow(
  path: string,
  request: MultiRowConnectionRequest,
  signal: AbortSignal,
): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      credentials: "same-origin",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new EvaluationTransportError(
      "NETWORK",
      null,
      "The multi-row service could not be reached.",
      error,
    );
  }
  const payload = await readJson(response);
  if (!response.ok) {
    const kind: EvaluationErrorKind =
      response.status === 422
        ? "VALIDATION"
        : response.status === 401 || response.status === 403
          ? "IDENTITY"
          : "HTTP";
    throw new EvaluationTransportError(
      kind,
      response.status,
      kind === "VALIDATION"
        ? "The server rejected one or more multi-row fields."
        : kind === "IDENTITY"
          ? "The server did not accept the trusted identity context."
          : `The multi-row service returned HTTP ${String(response.status)}.`,
      payload,
    );
  }
  return payload;
}

export async function previewMultiRow(
  request: MultiRowConnectionRequest,
  signal: AbortSignal,
): Promise<MultiRowPreviewResponse> {
  const payload = await postMultiRow(MULTIROW_PREVIEW_PATH, request, signal);
  if (!isMultiRowPreviewResponse(payload)) {
    throw new EvaluationTransportError(
      "RESPONSE",
      200,
      "The server returned an unsupported multi-row preview contract.",
      payload,
    );
  }
  return payload;
}

export async function evaluateMultiRow(
  request: MultiRowConnectionRequest,
  signal: AbortSignal,
): Promise<MultiRowDesignResponse> {
  const payload = await postMultiRow(MULTIROW_DESIGN_PATH, request, signal);
  if (!isMultiRowDesignResponse(payload)) {
    throw new EvaluationTransportError(
      "RESPONSE",
      200,
      "The server returned an unsupported multi-row design contract.",
      payload,
    );
  }
  return payload;
}

function isTeePreviewResponse(value: unknown): value is TeeConnectorPreviewResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as {
    api_transport_schema_version?: unknown;
    orchestration_contract_version?: unknown;
    preview_schema_version?: unknown;
    resistance_evaluated?: unknown;
    engineering_fingerprint?: unknown;
    result?: unknown;
  };
  const result = candidate.result as {
    orchestration_contract_version?: unknown;
    preview_schema_version?: unknown;
    rectangular_full_through_paths?: unknown;
  } | null | undefined;
  return (
    candidate.api_transport_schema_version === "0.1.0-draft" &&
    candidate.orchestration_contract_version === "3.3C2-RC1" &&
    candidate.preview_schema_version === "0.3.0-draft" &&
    candidate.resistance_evaluated === false &&
    typeof candidate.engineering_fingerprint === "string" &&
    typeof result === "object" &&
    result !== null &&
    result.orchestration_contract_version === "3.3C2-RC1" &&
    result.preview_schema_version === "0.3.0-draft" &&
    hasPhysicalThroughBoltEndpoints(result.rectangular_full_through_paths)
  );
}

function isDecimalPoint(value: unknown): boolean {
  if (typeof value !== "object" || value === null) return false;
  const point = value as Record<string, unknown>;
  return [point.x, point.y, point.z].every(
    (coordinate) =>
      typeof coordinate === "string" &&
      coordinate.trim() !== "" &&
      Number.isFinite(Number(coordinate)),
  );
}

function hasPhysicalThroughBoltEndpoints(value: unknown): boolean {
  return Array.isArray(value) && value.every((item) => {
    if (typeof item !== "object" || item === null) return false;
    const trace = item as Record<string, unknown>;
    return isDecimalPoint(trace.physical_start_point) && isDecimalPoint(trace.physical_end_point);
  });
}

function isTeeDesignResponse(value: unknown): value is TeeConnectorDesignResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as {
    api_transport_schema_version?: unknown;
    orchestration_contract_version?: unknown;
    ordinary_pass_allowed?: unknown;
    result_fingerprint?: unknown;
    result?: unknown;
  };
  const result = candidate.result as { preview?: unknown } | null | undefined;
  const preview = result?.preview as {
    orchestration_contract_version?: unknown;
    preview_schema_version?: unknown;
  } | null | undefined;
  return (
    candidate.api_transport_schema_version === "0.1.0-draft" &&
    candidate.orchestration_contract_version === "3.3C2-RC1" &&
    candidate.ordinary_pass_allowed === false &&
    typeof candidate.result_fingerprint === "string" &&
    preview?.orchestration_contract_version === "3.3C2-RC1" &&
    preview.preview_schema_version === "0.3.0-draft"
  );
}

async function postTeeConnector(
  path: string,
  request: TeeConnectorRequest,
  signal: AbortSignal,
): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      credentials: "same-origin",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new EvaluationTransportError(
      "NETWORK",
      null,
      "The Tee connector service could not be reached.",
      error,
    );
  }
  const payload = await readJson(response);
  if (!response.ok) {
    const kind: EvaluationErrorKind =
      response.status === 422
        ? "VALIDATION"
        : response.status === 401 || response.status === 403
          ? "IDENTITY"
          : "HTTP";
    throw new EvaluationTransportError(
      kind,
      response.status,
      kind === "VALIDATION"
        ? "The server rejected one or more Tee engineering fields."
        : `The Tee connector service returned HTTP ${String(response.status)}.`,
      payload,
    );
  }
  return payload;
}

export async function previewTeeConnector(
  request: TeeConnectorRequest,
  signal: AbortSignal,
): Promise<TeeConnectorPreviewResponse> {
  const payload = await postTeeConnector(TEE_CONNECTOR_PREVIEW_PATH, request, signal);
  if (!isTeePreviewResponse(payload)) {
    throw new EvaluationTransportError(
      "RESPONSE",
      200,
      "The server returned an unsupported Tee preview contract.",
      payload,
    );
  }
  return payload;
}

export async function evaluateTeeConnector(
  request: TeeConnectorRequest,
  signal: AbortSignal,
): Promise<TeeConnectorDesignResponse> {
  const payload = await postTeeConnector(TEE_CONNECTOR_DESIGN_PATH, request, signal);
  if (!isTeeDesignResponse(payload)) {
    throw new EvaluationTransportError(
      "RESPONSE",
      200,
      "The server returned an unsupported Tee design contract.",
      payload,
    );
  }
  return payload;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isMultiMemberTeeVisualization(value: unknown): boolean {
  if (!isRecord(value) || value.schema_version !== "0.1.0-draft" || !Array.isArray(value.slots)) {
    return false;
  }
  return value.slots.length > 0 && value.slots.every((item) => {
    if (!isRecord(item) || !isRecord(item.visualization)) return false;
    const slotId = item.slot_id;
    return (slotId === "UPPER_BRACE" || slotId === "MIDDLE_BEAM" || slotId === "LOWER_BRACE")
      && typeof item.connected_member_id === "string"
      && typeof item.bolt_group_id === "string"
      && isRecord(item.visualization.base_connection)
      && isRecord(item.visualization.connected_member_profile);
  });
}

function isMultiMemberTeePreviewResult(value: unknown): boolean {
  if (!isRecord(value) || !Array.isArray(value.active_slot_ids) || !Array.isArray(value.slots)) {
    return false;
  }
  return value.visualization === null || isMultiMemberTeeVisualization(value.visualization);
}

function isMultiMemberTeePreview(value: unknown): value is MultiMemberTeePreviewResponse {
  if (!isRecord(value)) return false;
  const candidate = value;
  return candidate.api_transport_schema_version === "0.1.0-draft"
    && (candidate.orchestration_contract_version === "3.4A-RC1"
      || candidate.orchestration_contract_version === "3.4B-RC1")
    && candidate.preview_schema_version === "0.1.0-draft"
    && candidate.resistance_evaluated === false
    && typeof candidate.engineering_fingerprint === "string"
    && isMultiMemberTeePreviewResult(candidate.result);
}

function isMultiMemberTeeDesign(value: unknown): value is MultiMemberTeeDesignResponse {
  if (!isRecord(value)) return false;
  const candidate = value;
  const result = candidate.result;
  return candidate.api_transport_schema_version === "0.1.0-draft"
    && (candidate.orchestration_contract_version === "3.4A-RC1"
      || candidate.orchestration_contract_version === "3.4B-RC1")
    && candidate.ordinary_pass_allowed === false
    && typeof candidate.result_fingerprint === "string"
    && isRecord(result)
    && isMultiMemberTeePreviewResult(result.preview)
    && Array.isArray(result.required_limitations);
}

async function postMultiMemberTee(
  path: string,
  request: MultiMemberTeeRequest,
  signal: AbortSignal,
): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(request),
      credentials: "same-origin",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new EvaluationTransportError("NETWORK", null, "The Multi-Member Tee service could not be reached.", error);
  }
  const payload = await readJson(response);
  if (!response.ok) {
    throw new EvaluationTransportError(
      response.status === 422 ? "VALIDATION" : "HTTP",
      response.status,
      response.status === 422 ? "The server rejected one or more node fields." : `The Multi-Member Tee service returned HTTP ${String(response.status)}.`,
      payload,
    );
  }
  return payload;
}

export async function previewMultiMemberTee(request: MultiMemberTeeRequest, signal: AbortSignal): Promise<MultiMemberTeePreviewResponse> {
  const payload = await postMultiMemberTee(MULTI_MEMBER_TEE_PREVIEW_PATH, request, signal);
  if (!isMultiMemberTeePreview(payload)) throw new EvaluationTransportError("RESPONSE", 200, "The server returned an unsupported Multi-Member Tee preview contract.", payload);
  return payload;
}

export async function evaluateMultiMemberTee(request: MultiMemberTeeRequest, signal: AbortSignal): Promise<MultiMemberTeeDesignResponse> {
  const payload = await postMultiMemberTee(MULTI_MEMBER_TEE_DESIGN_PATH, request, signal);
  if (!isMultiMemberTeeDesign(payload)) throw new EvaluationTransportError("RESPONSE", 200, "The server returned an unsupported Multi-Member Tee design contract.", payload);
  return payload;
}

function isClipAnglePreviewResponse(value: unknown): value is ClipAnglePreviewResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  const result = candidate.result as Record<string, unknown> | null;
  return (
    candidate.api_transport_schema_version === "0.1.0-draft" &&
    candidate.orchestration_contract_version === "3.3C2-RC1" &&
    candidate.preview_schema_version === "0.1.0-draft" &&
    (candidate.geometry_status === "VALID" || candidate.geometry_status === "INVALID_GEOMETRY") &&
    Array.isArray(candidate.geometry_invalid_reasons) &&
    candidate.geometry_invalid_reasons.every((item) => typeof item === "string") &&
    candidate.resistance_evaluated === false &&
    typeof candidate.engineering_fingerprint === "string" &&
    typeof result === "object" &&
    result !== null &&
    hasPhysicalThroughBoltEndpoints(result.rectangular_full_through_paths)
  );
}

function isClipAngleDesignResponse(value: unknown): value is ClipAngleDesignResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    candidate.api_transport_schema_version === "0.1.0-draft" &&
    candidate.orchestration_contract_version === "3.3C2-RC1" &&
    candidate.ordinary_pass_allowed === false &&
    candidate.connector_body_status === "NOT_EVALUATED" &&
    typeof candidate.result_fingerprint === "string" &&
    typeof candidate.result === "object" &&
    candidate.result !== null
  );
}

async function postClipAngle(
  path: string,
  request: ClipAngleRequest | PairedClipAngleRequest,
  signal: AbortSignal,
): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      credentials: "same-origin",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new EvaluationTransportError(
      "NETWORK",
      null,
      "The clip-angle service could not be reached.",
      error,
    );
  }
  const payload = await readJson(response);
  if (!response.ok) {
    const kind: EvaluationErrorKind =
      response.status === 422
        ? "VALIDATION"
        : response.status === 401 || response.status === 403
          ? "IDENTITY"
          : "HTTP";
    throw new EvaluationTransportError(
      kind,
      response.status,
      kind === "VALIDATION"
        ? "The server rejected one or more clip-angle engineering fields."
        : `The clip-angle service returned HTTP ${String(response.status)}.`,
      payload,
    );
  }
  return payload;
}

export async function previewClipAngle(
  request: ClipAngleRequest,
  signal: AbortSignal,
): Promise<ClipAnglePreviewResponse> {
  const payload = await postClipAngle(CLIP_ANGLE_PREVIEW_PATH, request, signal);
  if (!isClipAnglePreviewResponse(payload)) {
    throw new EvaluationTransportError(
      "RESPONSE",
      200,
      "The server returned an unsupported clip-angle preview contract.",
      payload,
    );
  }
  return payload;
}

export async function evaluateClipAngle(
  request: ClipAngleRequest,
  signal: AbortSignal,
): Promise<ClipAngleDesignResponse> {
  const payload = await postClipAngle(CLIP_ANGLE_DESIGN_PATH, request, signal);
  if (!isClipAngleDesignResponse(payload)) {
    throw new EvaluationTransportError(
      "RESPONSE",
      200,
      "The server returned an unsupported clip-angle design contract.",
      payload,
    );
  }
  return payload;
}

function isPairedClipAnglePreviewResponse(
  value: unknown,
): value is PairedClipAnglePreviewResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return candidate.api_transport_schema_version === "0.1.0-draft"
    && (candidate.orchestration_contract_version === "3.3B-RC1"
      || candidate.orchestration_contract_version === "3.3C3-RC1")
    && candidate.preview_schema_version === "0.1.0-draft"
    && (candidate.geometry_status === "VALID" || candidate.geometry_status === "INVALID_GEOMETRY")
    && candidate.resistance_evaluated === false
    && candidate.ordinary_pass_allowed === false
    && typeof candidate.result === "object"
    && candidate.result !== null;
}

function isPairedClipAngleDesignResponse(
  value: unknown,
): value is PairedClipAngleDesignResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return candidate.api_transport_schema_version === "0.1.0-draft"
    && (candidate.orchestration_contract_version === "3.3B-RC1"
      || candidate.orchestration_contract_version === "3.3C3-RC1")
    && candidate.required_check_status === "NOT_EVALUATED"
    && candidate.ordinary_pass_allowed === false
    && typeof candidate.result_fingerprint === "string"
    && typeof candidate.result === "object"
    && candidate.result !== null;
}

export async function previewPairedClipAngle(
  request: PairedClipAngleRequest,
  signal: AbortSignal,
): Promise<PairedClipAnglePreviewResponse> {
  const payload = await postClipAngle(PAIRED_CLIP_ANGLE_PREVIEW_PATH, request, signal);
  if (!isPairedClipAnglePreviewResponse(payload)) {
    throw new EvaluationTransportError(
      "RESPONSE",
      200,
      "The server returned an unsupported paired clip-angle preview contract.",
      payload,
    );
  }
  return payload;
}

export async function evaluatePairedClipAngle(
  request: PairedClipAngleRequest,
  signal: AbortSignal,
): Promise<PairedClipAngleDesignResponse> {
  const payload = await postClipAngle(PAIRED_CLIP_ANGLE_DESIGN_PATH, request, signal);
  if (!isPairedClipAngleDesignResponse(payload)) {
    throw new EvaluationTransportError(
      "RESPONSE",
      200,
      "The server returned an unsupported paired clip-angle design contract.",
      payload,
    );
  }
  return payload;
}

function isBeamConcretePairedAnglePreview(
  value: unknown,
): value is BeamConcretePairedAnglePreviewResponse {
  if (!isRecord(value)) return false;
  return value.api_transport_schema_version === "0.1.0-draft"
    && (value.orchestration_contract_version === "3.5A-RC1" || value.orchestration_contract_version === "3.5A-R1-RC1" || value.orchestration_contract_version === "3.5A-R2-RC1")
    && value.preview_schema_version === "0.1.0-draft"
    && value.resistance_evaluated === false
    && value.external_design_required === true
    && typeof value.engineering_fingerprint === "string"
    && isRecord(value.result);
}

function isBeamConcretePairedAngleDesign(
  value: unknown,
): value is BeamConcretePairedAngleDesignResponse {
  if (!isRecord(value)) return false;
  return value.api_transport_schema_version === "0.1.0-draft"
    && (value.orchestration_contract_version === "3.5A-RC1" || value.orchestration_contract_version === "3.5A-R1-RC1" || value.orchestration_contract_version === "3.5A-R2-RC1")
    && value.required_check_status === "NOT_EVALUATED"
    && value.ordinary_pass_allowed === false
    && value.external_design_required === true
    && typeof value.result_fingerprint === "string"
    && isRecord(value.result);
}

async function postBeamConcretePairedAngle(
  path: string,
  request: BeamConcretePairedAngleRequest,
  signal: AbortSignal,
): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(request),
      credentials: "same-origin",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new EvaluationTransportError(
      "NETWORK",
      null,
      "The beam-to-concrete paired-angle service could not be reached.",
      error,
    );
  }
  const payload = await readJson(response);
  if (!response.ok) {
    throw new EvaluationTransportError(
      response.status === 422 ? "VALIDATION" : "HTTP",
      response.status,
      response.status === 422
        ? "The server rejected one or more beam-to-concrete engineering fields."
        : `The beam-to-concrete service returned HTTP ${String(response.status)}.`,
      payload,
    );
  }
  return payload;
}

export async function previewBeamConcretePairedAngle(
  request: BeamConcretePairedAngleRequest,
  signal: AbortSignal,
): Promise<BeamConcretePairedAnglePreviewResponse> {
  const payload = await postBeamConcretePairedAngle(
    BEAM_CONCRETE_PAIRED_ANGLE_PREVIEW_PATH,
    request,
    signal,
  );
  if (!isBeamConcretePairedAnglePreview(payload)) {
    throw new EvaluationTransportError("RESPONSE", 200, "The server returned an unsupported beam-to-concrete preview contract.", payload);
  }
  return payload;
}

export async function evaluateBeamConcretePairedAngle(
  request: BeamConcretePairedAngleRequest,
  signal: AbortSignal,
): Promise<BeamConcretePairedAngleDesignResponse> {
  const payload = await postBeamConcretePairedAngle(
    BEAM_CONCRETE_PAIRED_ANGLE_DESIGN_PATH,
    request,
    signal,
  );
  if (!isBeamConcretePairedAngleDesign(payload)) {
    throw new EvaluationTransportError("RESPONSE", 200, "The server returned an unsupported beam-to-concrete design contract.", payload);
  }
  return payload;
}

function isDirectSideLapPreview(value: unknown): value is DirectSideLapPreviewResponse {
  if (!isRecord(value)) return false;
  return value.api_transport_schema_version === "0.1.0-draft"
    && value.orchestration_contract_version === "3.5B-RC1"
    && value.preview_schema_version === "0.1.0-draft"
    && value.resistance_evaluated === false
    && value.external_design_required === true
    && typeof value.engineering_fingerprint === "string"
    && isRecord(value.result);
}

function isDirectSideLapDesign(value: unknown): value is DirectSideLapDesignResponse {
  if (!isRecord(value)) return false;
  return value.api_transport_schema_version === "0.1.0-draft"
    && value.orchestration_contract_version === "3.5B-RC1"
    && value.required_check_status === "NOT_EVALUATED"
    && value.ordinary_pass_allowed === false
    && value.external_design_required === true
    && typeof value.result_fingerprint === "string"
    && isRecord(value.result);
}

async function postDirectSideLapConcrete(
  path: string,
  request: DirectSideLapConcreteRequest,
  signal: AbortSignal,
): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(request),
      credentials: "same-origin",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new EvaluationTransportError("NETWORK", null, "The direct side-lap service could not be reached.", error);
  }
  const payload = await readJson(response);
  if (!response.ok) {
    throw new EvaluationTransportError(
      response.status === 422 ? "VALIDATION" : "HTTP",
      response.status,
      response.status === 422
        ? "The server rejected one or more direct side-lap engineering fields."
        : `The direct side-lap service returned HTTP ${String(response.status)}.`,
      payload,
    );
  }
  return payload;
}

export async function previewDirectSideLapConcrete(
  request: DirectSideLapConcreteRequest,
  signal: AbortSignal,
): Promise<DirectSideLapPreviewResponse> {
  const payload = await postDirectSideLapConcrete(DIRECT_SIDE_LAP_CONCRETE_PREVIEW_PATH, request, signal);
  if (!isDirectSideLapPreview(payload)) throw new EvaluationTransportError("RESPONSE", 200, "The server returned an unsupported direct side-lap preview contract.", payload);
  return payload;
}

export async function evaluateDirectSideLapConcrete(
  request: DirectSideLapConcreteRequest,
  signal: AbortSignal,
): Promise<DirectSideLapDesignResponse> {
  const payload = await postDirectSideLapConcrete(DIRECT_SIDE_LAP_CONCRETE_DESIGN_PATH, request, signal);
  if (!isDirectSideLapDesign(payload)) throw new EvaluationTransportError("RESPONSE", 200, "The server returned an unsupported direct side-lap design contract.", payload);
  return payload;
}

function isColumnBasePreview(value: unknown): value is ColumnBasePreviewResponse {
  if (!isRecord(value)) return false;
  return value.api_transport_schema_version === "0.1.0-draft"
    && (value.orchestration_contract_version === "3.5C-RC1" || value.orchestration_contract_version === "3.5C-R2-RC1" || value.orchestration_contract_version === "3.7A-RC1")
    && value.preview_schema_version === "0.1.0-draft"
    && value.resistance_evaluated === false
    && value.external_design_required === true
    && typeof value.engineering_fingerprint === "string"
    && isRecord(value.result);
}

function isColumnBaseDesign(value: unknown): value is ColumnBaseDesignResponse {
  if (!isRecord(value)) return false;
  return value.api_transport_schema_version === "0.1.0-draft"
    && (value.orchestration_contract_version === "3.5C-RC1" || value.orchestration_contract_version === "3.5C-R2-RC1" || value.orchestration_contract_version === "3.7A-RC1")
    && value.required_check_status === "NOT_EVALUATED"
    && value.ordinary_pass_allowed === false
    && value.external_design_required === true
    && typeof value.result_fingerprint === "string"
    && isRecord(value.result);
}

async function postColumnBaseWebAngle(
  path: string,
  request: ColumnBaseWebAngleRequest,
  signal: AbortSignal,
): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(request),
      credentials: "same-origin",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new EvaluationTransportError("NETWORK", null, "The column-base web-angle service could not be reached.", error);
  }
  const payload = await readJson(response);
  if (!response.ok) {
    throw new EvaluationTransportError(
      response.status === 422 ? "VALIDATION" : "HTTP",
      response.status,
      response.status === 422
        ? "The server rejected one or more column-base engineering fields."
        : `The column-base service returned HTTP ${String(response.status)}.`,
      payload,
    );
  }
  return payload;
}

export async function previewColumnBaseWebAngle(
  request: ColumnBaseWebAngleRequest,
  signal: AbortSignal,
): Promise<ColumnBasePreviewResponse> {
  const payload = await postColumnBaseWebAngle(COLUMN_BASE_WEB_ANGLE_PREVIEW_PATH, request, signal);
  if (!isColumnBasePreview(payload)) {
    throw new EvaluationTransportError("RESPONSE", 200, "The server returned an unsupported column-base preview contract.", payload);
  }
  return payload;
}

export async function evaluateColumnBaseWebAngle(
  request: ColumnBaseWebAngleRequest,
  signal: AbortSignal,
): Promise<ColumnBaseDesignResponse> {
  const payload = await postColumnBaseWebAngle(COLUMN_BASE_WEB_ANGLE_DESIGN_PATH, request, signal);
  if (!isColumnBaseDesign(payload)) {
    throw new EvaluationTransportError("RESPONSE", 200, "The server returned an unsupported column-base design contract.", payload);
  }
  return payload;
}

function isWebSplicePreview(value: unknown): value is WebSplicePreviewResponse {
  if (!isRecord(value)) return false;
  const versionPair = (value.orchestration_contract_version === "3.6A-RC1" && value.preview_schema_version === "0.1.0-draft")
    || (value.orchestration_contract_version === "3.6B-RC2" && value.preview_schema_version === "0.2.0-draft");
  return value.api_transport_schema_version === "0.1.0-draft"
    && versionPair
    && value.resistance_evaluated === false
    && value.ordinary_pass_allowed === false
    && typeof value.engineering_fingerprint === "string"
    && isRecord(value.result);
}

function isWebSpliceDesign(value: unknown): value is WebSpliceDesignResponse {
  if (!isRecord(value)) return false;
  return value.api_transport_schema_version === "0.1.0-draft"
    && (value.orchestration_contract_version === "3.6A-RC1" || value.orchestration_contract_version === "3.6B-RC2")
    && value.ordinary_pass_allowed === false
    && typeof value.supported_local_checks_executed === "boolean"
    && Array.isArray(value.local_check_ids)
    && Array.isArray(value.failed_local_check_ids)
    && Array.isArray(value.local_resistance_warnings)
    && typeof value.result_fingerprint === "string"
    && isRecord(value.result);
}

async function postWebSplice(path: string, request: WebSpliceRequest, signal: AbortSignal): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(request), credentials: "same-origin", signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new EvaluationTransportError("NETWORK", null, "The beam web-splice service could not be reached.", error);
  }
  const payload = await readJson(response);
  if (!response.ok) throw new EvaluationTransportError(response.status === 422 ? "VALIDATION" : "HTTP", response.status, response.status === 422 ? "The server rejected one or more beam web-splice fields." : `The beam web-splice service returned HTTP ${String(response.status)}.`, payload);
  return payload;
}

export async function previewWebSplice(request: WebSpliceRequest, signal: AbortSignal): Promise<WebSplicePreviewResponse> {
  const payload = await postWebSplice(WEB_SPLICE_PREVIEW_PATH, request, signal);
  if (!isWebSplicePreview(payload)) throw new EvaluationTransportError("RESPONSE", 200, "The server returned an unsupported web-splice preview contract.", payload);
  return payload;
}

export async function evaluateWebSplice(request: WebSpliceRequest, signal: AbortSignal): Promise<WebSpliceDesignResponse> {
  const payload = await postWebSplice(WEB_SPLICE_DESIGN_PATH, request, signal);
  if (!isWebSpliceDesign(payload)) throw new EvaluationTransportError("RESPONSE", 200, "The server returned an unsupported web-splice design contract.", payload);
  return payload;
}

function isWIMomentSplicePreview(value: unknown): value is WIMomentSplicePreviewResponse {
  if (!isRecord(value)) return false;
  return value.api_transport_schema_version === "4.1A-API-RC1"
    && value.orchestration_contract_version === "4.1A-RC1"
    && value.preview_schema_version === "4.1A-PREVIEW-RC1"
    && value.resistance_evaluated === false
    && value.ordinary_pass_allowed === false
    && typeof value.engineering_fingerprint === "string"
    && isRecord(value.result);
}

function isWIMomentSpliceDesign(value: unknown): value is WIMomentSpliceDesignResponse {
  if (!isRecord(value)) return false;
  return value.api_transport_schema_version === "4.1A-API-RC1"
    && value.orchestration_contract_version === "4.1A-RC1"
    && value.ordinary_pass_allowed === false
    && Array.isArray(value.failed_check_ids)
    && Array.isArray(value.unavailable_check_ids)
    && typeof value.result_fingerprint === "string"
    && isRecord(value.result);
}

async function postWIMomentSplice(path: string, request: WIMomentSpliceRequest, signal: AbortSignal): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(request), credentials: "same-origin", signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new EvaluationTransportError("NETWORK", null, "The W/I moment-splice service could not be reached.", error);
  }
  const payload = await readJson(response);
  if (!response.ok) throw new EvaluationTransportError(response.status === 422 ? "VALIDATION" : "HTTP", response.status, response.status === 422 ? "The server rejected one or more W/I moment-splice fields." : `The W/I moment-splice service returned HTTP ${String(response.status)}.`, payload);
  return payload;
}

export async function previewWIMomentSplice(request: WIMomentSpliceRequest, signal: AbortSignal): Promise<WIMomentSplicePreviewResponse> {
  const payload = await postWIMomentSplice(WI_MOMENT_SPLICE_PREVIEW_PATH, request, signal);
  if (!isWIMomentSplicePreview(payload)) throw new EvaluationTransportError("RESPONSE", 200, "The server returned an unsupported W/I moment-splice preview contract.", payload);
  return payload;
}

export async function evaluateWIMomentSplice(request: WIMomentSpliceRequest, signal: AbortSignal): Promise<WIMomentSpliceDesignResponse> {
  const payload = await postWIMomentSplice(WI_MOMENT_SPLICE_DESIGN_PATH, request, signal);
  if (!isWIMomentSpliceDesign(payload)) throw new EvaluationTransportError("RESPONSE", 200, "The server returned an unsupported W/I moment-splice design contract.", payload);
  return payload;
}

function isChannelMomentSpliceReference(value: unknown): boolean {
  if (!isRecord(value)) return false;
  return [value.l, value.v, value.t].every((quantity) => isRecord(quantity)
    && typeof quantity.value === "string" && typeof quantity.unit === "string");
}

function isChannelMomentSplicePreview(value: unknown): value is ChannelMomentSplicePreviewResponse {
  if (!isRecord(value) || !isRecord(value.result) || !isRecord(value.result.visualization)) return false;
  const visualization = value.result.visualization;
  return value.api_transport_schema_version === "4.1B-API-RC1"
    && value.orchestration_contract_version === "4.1B-RC1"
    && value.preview_schema_version === "4.1B-PREVIEW-RC1"
    && value.resistance_evaluated === false
    && value.ordinary_pass_allowed === false
    && typeof value.engineering_fingerprint === "string"
    && ["joint_reference_l_v_t", "channel_centroid_l_v_t", "channel_shear_center_l_v_t", "action_reference_l_v_t"]
      .every((key) => isChannelMomentSpliceReference(visualization[key]));
}

function isChannelMomentSpliceDesign(value: unknown): value is ChannelMomentSpliceDesignResponse {
  if (!isRecord(value)) return false;
  return value.api_transport_schema_version === "4.1B-API-RC1"
    && value.orchestration_contract_version === "4.1B-RC1"
    && value.ordinary_pass_allowed === false
    && Array.isArray(value.failed_check_ids)
    && Array.isArray(value.unavailable_check_ids)
    && typeof value.result_fingerprint === "string"
    && isRecord(value.result);
}

async function postChannelMomentSplice(path: string, request: ChannelMomentSpliceRequest, signal: AbortSignal): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(request), credentials: "same-origin", signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new EvaluationTransportError("NETWORK", null, "The Channel moment-splice service could not be reached.", error);
  }
  const payload = await readJson(response);
  if (!response.ok) throw new EvaluationTransportError(response.status === 422 ? "VALIDATION" : "HTTP", response.status, response.status === 422 ? "The server rejected one or more Channel moment-splice fields." : `The Channel moment-splice service returned HTTP ${String(response.status)}.`, payload);
  return payload;
}

export async function previewChannelMomentSplice(request: ChannelMomentSpliceRequest, signal: AbortSignal): Promise<ChannelMomentSplicePreviewResponse> {
  const payload = await postChannelMomentSplice(CHANNEL_MOMENT_SPLICE_PREVIEW_PATH, request, signal);
  if (!isChannelMomentSplicePreview(payload)) throw new EvaluationTransportError("RESPONSE", 200, "The server returned an unsupported Channel moment-splice preview contract.", payload);
  return payload;
}

export async function evaluateChannelMomentSplice(request: ChannelMomentSpliceRequest, signal: AbortSignal): Promise<ChannelMomentSpliceDesignResponse> {
  const payload = await postChannelMomentSplice(CHANNEL_MOMENT_SPLICE_DESIGN_PATH, request, signal);
  if (!isChannelMomentSpliceDesign(payload)) throw new EvaluationTransportError("RESPONSE", 200, "The server returned an unsupported Channel moment-splice design contract.", payload);
  return payload;
}
