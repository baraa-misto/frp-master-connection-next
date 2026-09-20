import { useEffect, useRef, useState } from "react";
import type { DCTN3BMember, DCTN3BRequest, DCTN3BResponse, DCTNMember, DCTNRequest, DCTNResponse } from "../api/dctnContracts";
import { requestDCTN } from "../api/dctnClient";
import { requestDCTN3B } from "../api/dctn3bClient";
import { isIntentionalAbort, PREVIEW_DEBOUNCE_MS } from "./previewWorkflow";

export function dctnKey(request: DCTNRequest | DCTN3BRequest): string {
  return JSON.stringify({ ...request, request_id: "" });
}
export function clearDCTNQualification(request: DCTNRequest | DCTN3BRequest): void {
  request.channel.material_source_reference = "";
  request.fastener.source_reference = "";
  request.shared_channel_source_reference = "";
  for (const member of request.members) {
    member.material_source_reference = "";
    member.local_path_source_reference = "";
  }
}
export function editDCTNMember<M extends DCTNMember | DCTN3BMember>(request: { members: M[] }, slot: M["slot"], change: (member: M) => void, linked: boolean): void {
  const target = request.members.find(m => m.slot === slot);
  if (target === undefined) throw new Error("DCTN active member is missing.");
  change(target);
  if (linked) {
    const partner = request.members.find(m => m.slot === (slot === "D1" ? "D2" : "D1"));
    if (partner !== undefined) partner.section = { ...structuredClone(target.section), length: partner.section.length };
  }
}
export function finiteDCTNRequest(request: DCTNRequest | DCTN3BRequest): boolean {
  const visit = (v: unknown): boolean => {
    if (typeof v === "number") return Number.isFinite(v);
    if (v !== null && typeof v === "object") {
      if ("value" in v) return typeof v.value === "string" && v.value.trim() !== "" && Number.isFinite(Number(v.value));
      return Object.values(v).every(visit);
    }
    return true;
  };
  return visit(request) && request.members.every(m => m.inclination_deg.trim() !== "" && Number.isFinite(Number(m.inclination_deg)));
}
export function useDCTNPreview(request: DCTNRequest, revision: number) {
  return useVersionedDCTNPreview(request, revision, requestDCTN);
}
export function useDCTN3BPreview(request: DCTN3BRequest, revision: number) {
  return useVersionedDCTNPreview(request, revision, requestDCTN3B);
}
function useVersionedDCTNPreview<R extends DCTNRequest | DCTN3BRequest, S extends DCTNResponse | DCTN3BResponse>(
  request: R, revision: number, evaluate: (kind: "preview" | "design-check", request: R, signal: AbortSignal) => Promise<S>,
) {
  const [accepted, setAccepted] = useState<{ revision: number; response: S } | null>(null);
  const [failure, setFailure] = useState<{ revision: number; message: string } | null>(null);
  const sequence = useRef(0);
  const invalid = !finiteDCTNRequest(request);
  useEffect(() => {
    const serial = ++sequence.current, controller = new AbortController();
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const execute = async () => {
      try {
        const response = await evaluate("preview", request, controller.signal);
        if (disposed || serial !== sequence.current) return;
        if (response.geometry_status !== "VALID") setFailure({ revision, message: response.geometry_invalid_reasons.join("; ") || response.geometry_status });
        else { setAccepted({ revision, response }); setFailure(null); }
      } catch (error) {
        if (!disposed && serial === sequence.current && !isIntentionalAbort(error)) setFailure({ revision, message: error instanceof Error ? error.message : "DCTN preview unavailable." });
      }
    };
    if (!invalid) {
      if (revision === 0) void execute();
      else timer = setTimeout(() => { void execute(); }, PREVIEW_DEBOUNCE_MS);
    }
    return () => { disposed = true; if (timer !== undefined) clearTimeout(timer); controller.abort(); };
  }, [request, revision, invalid, evaluate]);
  const error = invalid ? "Enter finite numeric values before previewing." : failure?.revision === revision ? failure.message : null;
  return { response: accepted?.response ?? null, current: !invalid && error === null && accepted?.revision === revision, error };
}
