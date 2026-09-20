import { useCallback, useEffect, useRef, useState } from "react";

import { EvaluationTransportError, previewWIMomentSplice } from "../api/client";
import type { WIMomentSplicePreviewResponse, WIMomentSpliceRequest } from "../api/wiMomentSpliceContracts";
import { isIntentionalAbort, PREVIEW_DEBOUNCE_MS } from "./previewWorkflow";

export function useWIMomentSplicePreview(input: {
  readonly request: WIMomentSpliceRequest;
  readonly revision: number;
  readonly immediate: boolean;
  readonly validationMessage: string | null;
}) {
  const { request, revision, immediate, validationMessage } = input;
  const [response, setResponse] = useState<WIMomentSplicePreviewResponse | null>(null);
  const [acceptedRevision, setAcceptedRevision] = useState<number | null>(null);
  const [failure, setFailure] = useState<{ revision: number; kind: "INVALID" | "ERROR"; error: EvaluationTransportError | null; detail: string | null } | null>(null);
  const [retryNonce, setRetryNonce] = useState(0);
  const sequence = useRef(0);
  useEffect(() => {
    const current = sequence.current + 1;
    sequence.current = current;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const controller = new AbortController();
    if (validationMessage !== null) return () => { disposed = true; };
    const execute = async () => {
      setFailure(null);
      try {
        const result = await previewWIMomentSplice(request, controller.signal);
        if (disposed || sequence.current !== current) return;
        if (result.geometry_status === "INVALID_GEOMETRY") setFailure({ revision, kind: "INVALID", error: null, detail: result.geometry_invalid_reasons[0] ?? null });
        else { setResponse(result); setAcceptedRevision(revision); }
      } catch (caught) {
        if (disposed || sequence.current !== current || isIntentionalAbort(caught)) return;
        const error = caught instanceof EvaluationTransportError ? caught : new EvaluationTransportError("RESPONSE", null, "Unexpected W/I moment-splice preview failure.", caught);
        setFailure({ revision, kind: error.kind === "VALIDATION" ? "INVALID" : "ERROR", error, detail: error.message });
      }
    };
    if (immediate) void execute(); else timer = setTimeout(() => { void execute(); }, PREVIEW_DEBOUNCE_MS);
    return () => { disposed = true; if (timer !== null) clearTimeout(timer); controller.abort(); };
  }, [immediate, request, retryNonce, revision, validationMessage]);
  const currentFailure = failure?.revision === revision ? failure : null;
  const hasLastValid = response !== null;
  const state = validationMessage !== null || currentFailure?.kind === "INVALID"
    ? hasLastValid ? "CURRENT_INVALID_SHOWING_LAST_VALID" : "NO_VALID_PREVIEW"
    : currentFailure?.kind === "ERROR"
      ? hasLastValid ? "PREVIEW_FAILED_SHOWING_LAST_VALID" : "NO_VALID_PREVIEW"
      : acceptedRevision === revision ? "CURRENT_VALID" : "PREVIEW_PENDING";
  return { state, response, error: currentFailure?.error ?? null, invalidDetail: validationMessage ?? currentFailure?.detail ?? null, retry: useCallback(() => { setFailure(null); setRetryNonce((value) => value + 1); }, []) };
}
