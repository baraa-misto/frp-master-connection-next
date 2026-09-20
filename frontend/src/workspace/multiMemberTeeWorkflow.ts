import { useCallback, useEffect, useRef, useState } from "react";

import { EvaluationTransportError, previewMultiMemberTee } from "../api/client";
import type { MultiMemberTeePreviewResponse, MultiMemberTeeRequest } from "../api/multiMemberTeeContracts";
import { isIntentionalAbort, PREVIEW_DEBOUNCE_MS } from "./previewWorkflow";

export interface MultiMemberTeePreviewState {
  state: "CURRENT_VALID" | "PREVIEW_PENDING" | "CURRENT_INVALID_SHOWING_LAST_VALID" | "PREVIEW_FAILED_SHOWING_LAST_VALID" | "NO_VALID_PREVIEW";
  response: MultiMemberTeePreviewResponse | null;
  detail: string | null;
  acceptedRevision: number | null;
  retry: () => void;
}

export function useMultiMemberTeePreview(request: MultiMemberTeeRequest, revision: number): MultiMemberTeePreviewState {
  const [response, setResponse] = useState<MultiMemberTeePreviewResponse | null>(null);
  const [acceptedRevision, setAcceptedRevision] = useState<number | null>(null);
  const [failure, setFailure] = useState<{ revision: number; invalid: boolean; detail: string } | null>(null);
  const [retryNonce, setRetryNonce] = useState(0);
  const sequence = useRef(0);
  useEffect(() => {
    const current = ++sequence.current;
    const controller = new AbortController();
    let disposed = false;
    const timer = setTimeout(() => {
      void previewMultiMemberTee(request, controller.signal).then((result) => {
        if (disposed || sequence.current !== current) return;
        if (result.assembly_status === "INVALID_GEOMETRY") {
          setFailure({ revision, invalid: true, detail: result.result.warnings[0] ?? "Backend rejected current geometry." });
          return;
        }
        setResponse(result);
        setAcceptedRevision(revision);
        setFailure(null);
      }).catch((caught: unknown) => {
        if (disposed || sequence.current !== current || isIntentionalAbort(caught)) return;
        const error = caught instanceof EvaluationTransportError ? caught : null;
        setFailure({ revision, invalid: error?.kind === "VALIDATION", detail: error?.message ?? "Preview failed." });
      });
    }, revision === 0 ? 0 : PREVIEW_DEBOUNCE_MS);
    return () => { disposed = true; clearTimeout(timer); controller.abort(); };
  }, [request, revision, retryNonce]);
  const current = failure?.revision === revision ? failure : null;
  const state = acceptedRevision === revision ? "CURRENT_VALID"
    : current?.invalid === true ? (response === null ? "NO_VALID_PREVIEW" : "CURRENT_INVALID_SHOWING_LAST_VALID")
      : current === null ? "PREVIEW_PENDING"
        : response === null ? "NO_VALID_PREVIEW" : "PREVIEW_FAILED_SHOWING_LAST_VALID";
  const retry = useCallback(() => { setFailure(null); setRetryNonce((value) => value + 1); }, []);
  return { state, response, detail: current?.detail ?? null, acceptedRevision, retry };
}
