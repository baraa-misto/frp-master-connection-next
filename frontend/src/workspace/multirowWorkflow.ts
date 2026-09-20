import { useCallback, useEffect, useRef, useState } from "react";

import {
  EvaluationTransportError,
  previewMultiRow,
} from "../api/client";
import type {
  MultiRowConnectionRequest,
  MultiRowPreviewResponse,
} from "../api/multirowContracts";
import { isIntentionalAbort, PREVIEW_DEBOUNCE_MS } from "./previewWorkflow";

export interface MultiRowPreviewInput {
  readonly request: MultiRowConnectionRequest;
  readonly revision: number;
  readonly immediate: boolean;
  readonly validationMessage: string | null;
}

export type MultiRowPreviewState =
  | "WAITING"
  | "PREVIEWING"
  | "CURRENT_VALID"
  | "CURRENT_INVALID"
  | "CURRENT_INCOMPLETE"
  | "PREVIEW_ERROR";

export interface MultiRowPreviewWorkflowState {
  readonly state: MultiRowPreviewState;
  readonly response: MultiRowPreviewResponse | null;
  readonly error: EvaluationTransportError | null;
  readonly outdated: boolean;
  readonly retry: () => void;
}

export function useMultiRowPreview(
  input: MultiRowPreviewInput,
): MultiRowPreviewWorkflowState {
  const [state, setState] = useState<MultiRowPreviewState>("WAITING");
  const [response, setResponse] = useState<MultiRowPreviewResponse | null>(null);
  const [error, setError] = useState<EvaluationTransportError | null>(null);
  const [outdated, setOutdated] = useState(false);
  const [retryNonce, setRetryNonce] = useState(0);
  const responseRef = useRef<MultiRowPreviewResponse | null>(null);
  const sequence = useRef(0);

  useEffect(() => {
    const current = sequence.current + 1;
    sequence.current = current;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const controller = new AbortController();
    if (input.validationMessage !== null) {
      queueMicrotask(() => {
        if (disposed || sequence.current !== current) return;
        setState("CURRENT_INCOMPLETE");
        setError(null);
        setOutdated(responseRef.current !== null);
      });
      return () => { disposed = true; };
    }
    const execute = async () => {
      setState("PREVIEWING");
      setError(null);
      setOutdated(responseRef.current !== null);
      try {
        const result = await previewMultiRow(input.request, controller.signal);
        if (disposed || sequence.current !== current) return;
        responseRef.current = result;
        setResponse(result);
        setState(result.geometry_status === "VALID" ? "CURRENT_VALID" : "CURRENT_INVALID");
        setOutdated(false);
      } catch (caught) {
        if (disposed || sequence.current !== current || isIntentionalAbort(caught)) return;
        setState("PREVIEW_ERROR");
        setError(
          caught instanceof EvaluationTransportError
            ? caught
            : new EvaluationTransportError(
                "RESPONSE",
                null,
                "Unexpected multi-row preview handling failure.",
                caught,
              ),
        );
        setOutdated(responseRef.current !== null);
      }
    };
    if (input.immediate) {
      void execute();
    } else {
      queueMicrotask(() => {
        if (disposed || sequence.current !== current) return;
        setState("WAITING");
        setOutdated(responseRef.current !== null);
      });
      timer = setTimeout(() => { void execute(); }, PREVIEW_DEBOUNCE_MS);
    }
    return () => {
      disposed = true;
      if (timer !== null) clearTimeout(timer);
      controller.abort();
    };
  }, [input, retryNonce]);

  const retry = useCallback(() => { setRetryNonce((value) => value + 1); }, []);
  return { state, response, error, outdated, retry };
}
