import { useCallback, useEffect, useRef, useState } from "react";

import {
  EvaluationTransportError,
  previewSingleBolt,
} from "../api/client";
import type {
  ConnectionViewExtentsDTO,
  SingleBoltEvaluationRequest,
  SingleBoltPreviewRequest,
  SingleBoltPreviewResponse,
} from "../api/contracts";

export const PREVIEW_DEBOUNCE_MS = 200;

export type EngineeringInputClassification =
  | "PREVIEW_AFFECTING_ENGINEERING_INPUT"
  | "DESIGN_ONLY_ENGINEERING_INPUT"
  | "PREVIEW_ONLY_VIEW_EXTENT"
  | "PRESENTATION_ONLY_INPUT";

export type PreviewScheduling = "IMMEDIATE" | "DEBOUNCED" | "NONE";

export function requirePreviewScheduling(
  scheduling: PreviewScheduling,
): Exclude<PreviewScheduling, "NONE"> {
  if (scheduling === "NONE") {
    throw new Error("Preview-affecting input requires scheduling.");
  }
  return scheduling;
}

export const INPUT_CLASSIFICATION = {
  geometry: "PREVIEW_AFFECTING_ENGINEERING_INPUT",
  memberAction: "PREVIEW_AFFECTING_ENGINEERING_INPUT",
  resolvedDemand: "PREVIEW_AFFECTING_ENGINEERING_INPUT",
  designFactor: "DESIGN_ONLY_ENGINEERING_INPUT",
  demandMode: "PREVIEW_AFFECTING_ENGINEERING_INPUT",
  viewExtent: "PREVIEW_ONLY_VIEW_EXTENT",
  caseLabel: "PRESENTATION_ONLY_INPUT",
  camera: "PRESENTATION_ONLY_INPUT",
  selection: "PRESENTATION_ONLY_INPUT",
  overlay: "PRESENTATION_ONLY_INPUT",
  inspector: "PRESENTATION_ONLY_INPUT",
} as const satisfies Readonly<Record<string, EngineeringInputClassification>>;

export type PreviewState =
  | "IDLE"
  | "WAITING"
  | "PREVIEWING"
  | "CURRENT_VALID"
  | "CURRENT_INVALID"
  | "CURRENT_INCOMPLETE"
  | "PREVIEW_ERROR";

export interface CanonicalPreviewInput {
  readonly request: SingleBoltEvaluationRequest;
  readonly viewExtents: ConnectionViewExtentsDTO;
  readonly revision: number;
  readonly scheduling: Exclude<PreviewScheduling, "NONE">;
  readonly validationMessage: string | null;
}

export interface CanonicalPreviewState {
  readonly state: PreviewState;
  readonly response: SingleBoltPreviewResponse | null;
  readonly error: EvaluationTransportError | null;
  readonly outdated: boolean;
  readonly currentRevision: number | null;
  readonly retry: () => void;
}

export function buildSingleBoltPreviewRequest(
  request: SingleBoltEvaluationRequest,
  viewExtents: ConnectionViewExtentsDTO,
): SingleBoltPreviewRequest {
  return {
    calculation_id: request.calculation_id,
    joint_assembly: request.joint_assembly,
    ...(request.geometry === undefined ? {} : { geometry: request.geometry }),
    ...(request.geometry_template === undefined
      ? {}
      : { geometry_template: request.geometry_template }),
    ...(request.geometry_template === undefined ? {} : { view_extents: viewExtents }),
    interface_id: request.interface_id,
    bolt_group_id: request.bolt_group_id,
    bolt_location_id: request.bolt_location_id,
    load_combination_id: request.load_combination_id,
    source_action_id: request.source_action_id,
    explicit_resolved_demand: request.explicit_resolved_demand,
    material_snapshots: request.material_snapshots,
    material_assignments: request.material_assignments,
    fastener_snapshot: {
      id: request.fastener_snapshot.id,
      washer_geometry: request.fastener_snapshot.washer_geometry,
    },
    bolt_diameter: request.bolt_diameter,
    lap_configuration: request.lap_configuration,
  };
}

export function previewStateFromResponse(response: SingleBoltPreviewResponse): PreviewState {
  if (response.geometry_status === "PREVIEW_VALID") return "CURRENT_VALID";
  if (response.geometry_status === "PREVIEW_INVALID_GEOMETRY") return "CURRENT_INVALID";
  return "CURRENT_INCOMPLETE";
}

export function isIntentionalAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export function useCanonicalPreview(input: CanonicalPreviewInput): CanonicalPreviewState {
  const [state, setState] = useState<PreviewState>("IDLE");
  const [response, setResponse] = useState<SingleBoltPreviewResponse | null>(null);
  const [error, setError] = useState<EvaluationTransportError | null>(null);
  const [outdated, setOutdated] = useState(false);
  const [currentRevision, setCurrentRevision] = useState<number | null>(null);
  const [retryNonce, setRetryNonce] = useState(0);
  const responseRef = useRef<SingleBoltPreviewResponse | null>(null);
  const sequence = useRef(0);
  const abortController = useRef<AbortController | null>(null);

  useEffect(() => {
    const requestSequence = sequence.current + 1;
    sequence.current = requestSequence;
    abortController.current?.abort();
    abortController.current = null;
    if (input.validationMessage !== null) {
      queueMicrotask(() => {
        if (sequence.current !== requestSequence) return;
        setState("CURRENT_INCOMPLETE");
        setError(null);
        setOutdated(responseRef.current !== null);
      });
      return undefined;
    }

    let timer: ReturnType<typeof setTimeout> | null = null;
    let disposed = false;
    const execute = async () => {
      const controller = new AbortController();
      abortController.current = controller;
      setState("PREVIEWING");
      setError(null);
      setOutdated(responseRef.current !== null);
      try {
        const result = await previewSingleBolt(
          buildSingleBoltPreviewRequest(input.request, input.viewExtents),
          controller.signal,
        );
        if (disposed || sequence.current !== requestSequence) return;
        responseRef.current = result;
        setResponse(result);
        setState(previewStateFromResponse(result));
        setCurrentRevision(input.revision);
        setOutdated(false);
      } catch (caught) {
        if (disposed || sequence.current !== requestSequence || isIntentionalAbort(caught)) return;
        setState("PREVIEW_ERROR");
        setError(
          caught instanceof EvaluationTransportError
            ? caught
            : new EvaluationTransportError(
                "RESPONSE",
                null,
                "Unexpected canonical preview response handling failure.",
                caught,
              ),
        );
        setOutdated(responseRef.current !== null);
      }
    };

    if (input.scheduling === "DEBOUNCED") {
      queueMicrotask(() => {
        if (disposed || sequence.current !== requestSequence) return;
        setState("WAITING");
        setError(null);
        setOutdated(responseRef.current !== null);
      });
      timer = setTimeout(() => { void execute(); }, PREVIEW_DEBOUNCE_MS);
    } else {
      void execute();
    }
    return () => {
      disposed = true;
      if (timer !== null) clearTimeout(timer);
      abortController.current?.abort();
    };
  }, [input, retryNonce]);

  const retry = useCallback(() => { setRetryNonce((value) => value + 1); }, []);
  return { state, response, error, outdated, currentRevision, retry };
}
