import { useCallback, useEffect, useRef, useState } from "react";

import {
  EvaluationTransportError,
  previewClipAngle,
} from "../api/client";
import type {
  ClipAnglePreviewResponse,
  ClipAngleRequest,
} from "../api/clipAngleContracts";
import { isIntentionalAbort, PREVIEW_DEBOUNCE_MS } from "./previewWorkflow";

export type ClipAnglePreviewDisplayState =
  | "CURRENT_VALID"
  | "PREVIEW_PENDING"
  | "CURRENT_INVALID_SHOWING_LAST_VALID"
  | "PREVIEW_FAILED_SHOWING_LAST_VALID"
  | "NO_VALID_PREVIEW";

export interface ClipAnglePreviewInput {
  readonly request: ClipAngleRequest;
  readonly revision: number;
  readonly immediate: boolean;
  readonly validationMessage: string | null;
}

interface SettledFailure {
  readonly revision: number;
  readonly kind: "INVALID" | "ERROR";
  readonly error: EvaluationTransportError | null;
  readonly detail: string | null;
}

export interface ClipAnglePreviewWorkflowState {
  readonly state: ClipAnglePreviewDisplayState;
  readonly response: ClipAnglePreviewResponse | null;
  readonly error: EvaluationTransportError | null;
  readonly invalidDetail: string | null;
  readonly outdated: boolean;
  readonly acceptedRevision: number | null;
  readonly retry: () => void;
}

function nonemptyText(value: unknown): string | null {
  return typeof value === "string" && value.trim() !== "" ? value.trim() : null;
}

export function clipAnglePreviewErrorDetail(
  error: EvaluationTransportError | null,
): string | null {
  if (error === null || typeof error.detail !== "object" || error.detail === null) return null;
  const detail = (error.detail as Record<string, unknown>).detail;
  const direct = nonemptyText(detail);
  if (direct !== null) return direct;
  if (typeof detail === "object" && detail !== null && !Array.isArray(detail)) {
    return nonemptyText((detail as Record<string, unknown>).message);
  }
  if (!Array.isArray(detail)) return null;
  for (const item of detail) {
    if (typeof item !== "object" || item === null) continue;
    const record = item as Record<string, unknown>;
    const message = nonemptyText(record.msg);
    if (message === null) continue;
    const location = Array.isArray(record.loc)
      ? record.loc.filter((part): part is string | number => (
          typeof part === "string" || typeof part === "number"
        )).join(" → ")
      : "";
    return location === "" ? message : `${location}: ${message}`;
  }
  return null;
}

/** Stage 3.3A adapter over the accepted debounced, abortable preview lifecycle. */
export function useClipAnglePreview(
  input: ClipAnglePreviewInput,
): ClipAnglePreviewWorkflowState {
  const [response, setResponse] = useState<ClipAnglePreviewResponse | null>(null);
  const [acceptedRevision, setAcceptedRevision] = useState<number | null>(null);
  const [settledFailure, setSettledFailure] = useState<SettledFailure | null>(null);
  const [retryNonce, setRetryNonce] = useState(0);
  const sequence = useRef(0);

  useEffect(() => {
    const current = sequence.current + 1;
    sequence.current = current;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const controller = new AbortController();
    if (input.validationMessage !== null) return () => { disposed = true; };
    const execute = async () => {
      setSettledFailure(null);
      try {
        const result = await previewClipAngle(input.request, controller.signal);
        if (disposed || sequence.current !== current) return;
        if (result.geometry_status === "INVALID_GEOMETRY") {
          setSettledFailure({
            revision: input.revision,
            kind: "INVALID",
            error: null,
            detail: result.geometry_invalid_reasons[0] ?? null,
          });
          return;
        }
        setResponse(result);
        setAcceptedRevision(input.revision);
      } catch (caught) {
        if (disposed || sequence.current !== current || isIntentionalAbort(caught)) return;
        const error = caught instanceof EvaluationTransportError
          ? caught
          : new EvaluationTransportError(
              "RESPONSE",
              null,
              "Unexpected clip-angle preview handling failure.",
              caught,
            );
        setSettledFailure({
          revision: input.revision,
          kind: error.kind === "VALIDATION" ? "INVALID" : "ERROR",
          error,
          detail: clipAnglePreviewErrorDetail(error),
        });
      }
    };
    if (input.immediate) void execute();
    else timer = setTimeout(() => { void execute(); }, PREVIEW_DEBOUNCE_MS);
    return () => {
      disposed = true;
      if (timer !== null) clearTimeout(timer);
      controller.abort();
    };
  }, [input, retryNonce]);

  const currentFailure = settledFailure?.revision === input.revision ? settledFailure : null;
  const hasLastValid = response !== null;
  let state: ClipAnglePreviewDisplayState;
  if (input.validationMessage !== null) {
    state = hasLastValid ? "CURRENT_INVALID_SHOWING_LAST_VALID" : "NO_VALID_PREVIEW";
  } else if (acceptedRevision === input.revision) {
    state = "CURRENT_VALID";
  } else if (currentFailure?.kind === "INVALID") {
    state = hasLastValid ? "CURRENT_INVALID_SHOWING_LAST_VALID" : "NO_VALID_PREVIEW";
  } else if (currentFailure?.kind === "ERROR") {
    state = hasLastValid ? "PREVIEW_FAILED_SHOWING_LAST_VALID" : "NO_VALID_PREVIEW";
  } else {
    state = "PREVIEW_PENDING";
  }

  const retry = useCallback(() => {
    setSettledFailure(null);
    setRetryNonce((value) => value + 1);
  }, []);
  return {
    state,
    response,
    error: currentFailure?.error ?? null,
    invalidDetail: currentFailure?.detail ?? null,
    outdated: hasLastValid && state !== "CURRENT_VALID",
    acceptedRevision,
    retry,
  };
}
