import { useEffect, useRef, useState } from "react";
import {
  evaluateStainlessActivation, type BodyRoute, type ConnectorBodyMaterial, type StainlessActivationResponse,
} from "../api/stainlessActivation";

interface MaterialState { readonly material: ConnectorBodyMaterial; readonly epoch: number }
interface BoundResult { readonly key: string; readonly response: StainlessActivationResponse }
interface BoundError { readonly key: string; readonly error: Error }

export function useConnectorBodyMaterial(
  route: BodyRoute, request: object, revision: string | number, invalidateNativeDesign: () => void,
) {
  const [selection, setSelection] = useState<MaterialState>({ material: "FRP", epoch: 0 });
  const [bound, setBound] = useState<BoundResult | null>(null);
  const [error, setError] = useState<BoundError | null>(null);
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  const key = JSON.stringify([route, revision, selection.epoch, selection.material, request]);
  useEffect(() => () => { controller.current?.abort(); }, [key]);
  const choose = (material: ConnectorBodyMaterial) => {
    if (material === selection.material) return;
    controller.current?.abort();
    sequence.current += 1;
    invalidateNativeDesign();
    setSelection(current => ({ material, epoch: current.epoch + 1 }));
    setBound(null);
    setError(null);
    setPendingKey(null);
  };
  const run = async () => {
    if (selection.material !== "SS316") return;
    controller.current?.abort();
    const signalOwner = new AbortController();
    controller.current = signalOwner;
    const runId = ++sequence.current;
    setPendingKey(key);
    setError(null);
    try {
      const response = await evaluateStainlessActivation(route, request, signalOwner.signal);
      if (!signalOwner.signal.aborted && sequence.current === runId) setBound({ key, response });
    } catch (caught) {
      if (!signalOwner.signal.aborted && sequence.current === runId) {
        setError({ key, error: caught instanceof Error ? caught : new Error("Unexpected stainless design failure.") });
      }
    } finally {
      if (sequence.current === runId) setPendingKey(null);
    }
  };
  return {
    material: selection.material, choose, run,
    busy: pendingKey === key,
    response: bound?.key === key ? bound.response : null,
    error: error?.key === key ? error.error : null,
    stale: bound !== null && bound.key !== key,
  };
}
