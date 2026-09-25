import { createContext, useContext } from "react";
import type { ReactNode } from "react";
import { mat1FamilyKey, useMAT1 } from "../state/mat1Session";
import { viewerUnity } from "./unityRatio";
import type { UnityFamily, UnityView } from "./unityRatio";
import { MAT1MaterialsPanel } from "../features/MAT1MaterialsPanel";
import { UnityRatioIndicator } from "./UnityRatioIndicator";
import { UnityViewerContext } from "./UnityViewerContext";

interface ConnectionWorkspaceShellProps {
  readonly banner: ReactNode;
  readonly children: ReactNode;
  readonly className?: string;
  readonly family?: string;
}

interface ConnectionWorkspaceSidebarProps {
  readonly ariaLabel: string;
  readonly children: ReactNode;
}

interface ConnectionWorkspaceMainProps {
  readonly children: ReactNode;
}

interface PersistentConnectionViewerProps {
  readonly children: ReactNode;
  readonly unity?: UnityView;
}

interface SidebarGroupProps {
  readonly title: string;
  readonly summary: string;
  readonly children: ReactNode;
  readonly defaultOpen?: boolean;
  readonly selected?: boolean;
  readonly onSelect?: (() => void) | undefined;
  readonly onFocusCapture?: (() => void) | undefined;
}

const MAT1FamilyContext = createContext<string | null>(null);
const unityFamily: Readonly<Record<string, UnityFamily>> = {
  "single-bolt": "single-bolt", "multi-row": "multirow", "tee-connector": "tee",
  "clip-angle": "clip-angle", "paired-clip-angle": "paired-clip-angle",
  "multi-member-tee": "multi-member-tee", "beam-concrete-paired-angle": "beam-concrete-paired-angle",
  "direct-side-lap-concrete": "direct-side-lap", "column-base-web-angles": "column-base-web-angle",
  "beam-web-splice": "web-splice", "wi-major-axis-moment-splice": "wi-moment-splice",
  "channel-major-axis-moment-splice": "channel-moment-splice",
  "wi-beam-concrete-wall-moment": "wi-wall-moment",
  "wi-beam-frp-support-moment": "wi-frp-support-moment",
  "angle-column-two-leg-moment-base": "angle-column-moment-base",
  "wi-rhs-srs-column-moment-base": "column-moment-base",
  "double-channel-truss-node": "dctn", "stair-stringer-miter": "ssmc",
};

export function ConnectionWorkspaceShell({
  banner,
  children,
  className = "",
  family,
}: ConnectionWorkspaceShellProps) {
  return (
    <MAT1FamilyContext.Provider value={family ?? null}><div className={`engineering-workspace connection-first-workspace${className === "" ? "" : ` ${className}`}`}>
      {banner}
      {family === undefined ? null : <MAT1MaterialsPanel family={family} />}
      <div className="workspace-body">{children}</div>
    </div></MAT1FamilyContext.Provider>
  );
}

export function ConnectionWorkspaceSidebar({
  ariaLabel,
  children,
}: ConnectionWorkspaceSidebarProps) {
  return <aside className="properties-sidebar" aria-label={ariaLabel}>{children}</aside>;
}

export function ConnectionWorkspaceMain({ children }: ConnectionWorkspaceMainProps) {
  return <main className="connection-view-column">{children}</main>;
}

export function PersistentConnectionViewer({ children, unity }: PersistentConnectionViewerProps) {
  const family = useContext(MAT1FamilyContext);
  const mat1 = useMAT1();
  const gateTrace = family === null ? undefined : mat1.designTraces[family] as { overall_status?: string } | undefined;
  const gateStatus = family !== null && mat1.designKeys[family] === mat1FamilyKey(family)
    ? gateTrace?.overall_status ?? "SOURCE_REQUIRED" : "STALE";
  let presented = unity;
  if (unity !== undefined && family !== null && mat1.active) {
    const trace = mat1.designTraces[family] as { client_design?: unknown; native_design?: unknown; overall_status?: string; material_issues?: string[] } | undefined;
    if (mat1.designKeys[family] !== mat1FamilyKey(family) || trace === undefined) {
      presented = { tone: "gray", ratio: null, ratioText: "—", status: "STALE", governing: null, explanation: "FRP material or design conditions changed. Run Design Check." };
    } else {
      const mapped = unityFamily[family];
      const inspected = mapped === undefined ? unity : viewerUnity(mapped, trace.client_design ?? trace.native_design);
      presented = {
        ...inspected,
        tone: inspected.tone === "red" ? "red" : "yellow",
        status: trace.overall_status ?? "SOURCE_REQUIRED",
        explanation: trace.material_issues?.[0] ?? "Material source and qualification remain unresolved.",
      };
    }
  }
  return <UnityViewerContext.Provider value={presented ?? null}><div className="persistent-connection-viewer">
    {family !== null && mat1.active ? <div className="mat1-result-gate" role="status">
      <strong>MAT1 connection status: {gateStatus}</strong>
      <span> Detailed native checks are numerical diagnostics on declared material data. Source and qualification gates govern the connection status.</span>
    </div> : null}
    {children}
    {presented === undefined ? null : <div className="unity-viewer-fallback"><UnityRatioIndicator value={presented} /></div>}
  </div></UnityViewerContext.Provider>;
}

export function SidebarGroup({
  title,
  summary,
  children,
  defaultOpen = false,
  selected = false,
  onSelect,
  onFocusCapture,
}: SidebarGroupProps) {
  return (
    <details
      className={`sidebar-group${selected ? " sidebar-group-selected" : ""}`}
      open={defaultOpen || selected || undefined}
      onFocusCapture={onFocusCapture}
    >
      <summary onClick={() => { onSelect?.(); }}>
        <span>{title}</span>
        <small>{summary}</small>
      </summary>
      <div className="sidebar-group-body">{children}</div>
    </details>
  );
}
