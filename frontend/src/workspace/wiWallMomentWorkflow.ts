import { useCallback, useEffect, useRef, useState } from "react";
import type { WIWallMomentPreview, WIWallMomentRequest, WIWallMomentResponse } from "../api/wiWallMomentContracts";
import { previewWIWallMoment } from "../api/wiWallMomentClient";
import { isIntentionalAbort, PREVIEW_DEBOUNCE_MS } from "./previewWorkflow";

export function useWIWallMomentPreview(request: WIWallMomentRequest, revision: number, immediate: boolean, invalid: string | null) {
  const [response,setResponse] = useState<WIWallMomentResponse<WIWallMomentPreview> | null>(null);
  const [accepted,setAccepted] = useState<number | null>(null);
  const [failure,setFailure] = useState<{ revision: number; message: string; kind: "GEOMETRY" | "REQUEST" } | null>(null);
  const [retryCount,setRetryCount] = useState(0);
  const sequence = useRef(0);
  useEffect(() => {
    const current = ++sequence.current;
    const controller = new AbortController();
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    if (invalid !== null) return () => { disposed = true; };
    const execute = async () => {
      try {
        const next = await previewWIWallMoment(request,controller.signal);
        if (disposed || current !== sequence.current) return;
        if (next.geometry_status !== "VALID") setFailure({ revision, message: next.geometry_invalid_reasons.join("; ") || next.geometry_status, kind: "GEOMETRY" });
        else { setResponse(next); setAccepted(revision); setFailure(null); }
      } catch (error) {
        if (!disposed && current === sequence.current && !isIntentionalAbort(error)) setFailure({ revision, message: error instanceof Error ? error.message : "Preview request failed.", kind: "REQUEST" });
      }
    };
    if (immediate) void execute(); else timer = setTimeout(() => { void execute(); },PREVIEW_DEBOUNCE_MS);
    return () => { disposed = true; if (timer !== null) clearTimeout(timer); controller.abort(); };
  },[request,revision,immediate,invalid,retryCount]);
  const error = invalid ?? (failure?.revision === revision ? failure.message : null);
  const current = error === null && accepted === revision;
  const state = current ? "Current backend preview" : error === null ? "Updating backend preview…" : invalid === null && failure?.kind === "REQUEST" ? "Preview request failed — showing last valid model if available" : response === null ? "No valid preview" : "Current input invalid — showing last valid model";
  return { response, current, error, state, retry: useCallback(() => { setRetryCount(v => v+1); },[]) };
}
