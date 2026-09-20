import { useCallback, useEffect, useRef, useState } from "react";

import {
  EvaluationTransportError,
  previewTeeConnector,
} from "../api/client";
import type {
  TeeConnectorPreviewResponse,
  TeeConnectorRequest,
} from "../api/teeContracts";
import { isIntentionalAbort, PREVIEW_DEBOUNCE_MS } from "./previewWorkflow";

export interface TeePreviewInput {
  readonly request: TeeConnectorRequest;
  readonly revision: number;
  readonly immediate: boolean;
  readonly validationMessage: string | null;
}

export type TeePreviewDisplayState =
  | "CURRENT_VALID"
  | "PREVIEW_PENDING"
  | "CURRENT_INVALID_SHOWING_LAST_VALID"
  | "PREVIEW_FAILED_SHOWING_LAST_VALID"
  | "NO_VALID_PREVIEW";

interface SettledPreviewFailure {
  readonly revision: number;
  readonly kind: "INVALID" | "ERROR";
  readonly error: EvaluationTransportError | null;
  readonly detail: string | null;
}

export interface TeePreviewWorkflowState {
  readonly state: TeePreviewDisplayState;
  /** The most recent backend-accepted valid preview, never a rejected current request. */
  readonly response: TeeConnectorPreviewResponse | null;
  readonly error: EvaluationTransportError | null;
  readonly invalidDetail: string | null;
  readonly outdated: boolean;
  readonly acceptedRevision: number | null;
  readonly retry: () => void;
}

function nonemptyText(value: unknown): string | null {
  return typeof value === "string" && value.trim() !== "" ? value.trim() : null;
}

/** Extract backend-owned validation detail without inventing a client explanation. */
export function teePreviewErrorDetail(error: EvaluationTransportError | null): string | null {
  if (error === null || typeof error.detail !== "object" || error.detail === null) return null;
  const payload = error.detail as Record<string, unknown>;
  const detail = payload.detail;
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

export function useTeePreview(input: TeePreviewInput): TeePreviewWorkflowState {
  const [response, setResponse] = useState<TeeConnectorPreviewResponse | null>(null);
  const [acceptedRevision, setAcceptedRevision] = useState<number | null>(null);
  const [settledFailure, setSettledFailure] = useState<SettledPreviewFailure | null>(null);
  const [retryNonce, setRetryNonce] = useState(0);
  const sequence = useRef(0);

  useEffect(() => {
    const current = sequence.current + 1;
    sequence.current = current;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const controller = new AbortController();
    if (input.validationMessage !== null) {
      return () => { disposed = true; };
    }
    const execute = async () => {
      setSettledFailure(null);
      try {
        const result = await previewTeeConnector(input.request, controller.signal);
        if (disposed || sequence.current !== current) return;
        if (result.assembly_status === "INVALID_GEOMETRY") {
          setSettledFailure({
            revision: input.revision,
            kind: "INVALID",
            error: null,
            detail: result.result.warnings[0] ?? null,
          });
          return;
        }
        setResponse(result);
        setAcceptedRevision(input.revision);
        setSettledFailure(null);
      } catch (caught) {
        if (disposed || sequence.current !== current || isIntentionalAbort(caught)) return;
        const error = caught instanceof EvaluationTransportError
          ? caught
          : new EvaluationTransportError(
              "RESPONSE",
              null,
              "Unexpected Tee preview handling failure.",
              caught,
            );
        setSettledFailure({
          revision: input.revision,
          kind: error.kind === "VALIDATION" ? "INVALID" : "ERROR",
          error,
          detail: teePreviewErrorDetail(error),
        });
      }
    };
    if (input.immediate) {
      void execute();
    } else {
      timer = setTimeout(() => { void execute(); }, PREVIEW_DEBOUNCE_MS);
    }
    return () => {
      disposed = true;
      if (timer !== null) clearTimeout(timer);
      controller.abort();
    };
  }, [input, retryNonce]);

  const currentFailure = settledFailure?.revision === input.revision ? settledFailure : null;
  const hasLastValid = response !== null;
  let state: TeePreviewDisplayState;
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
