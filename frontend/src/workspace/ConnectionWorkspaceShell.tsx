import type { ReactNode } from "react";
import type { UnityView } from "./unityRatio";
import { UnityRatioIndicator } from "./UnityRatioIndicator";
import { UnityViewerContext } from "./UnityViewerContext";

interface ConnectionWorkspaceShellProps {
  readonly banner: ReactNode;
  readonly children: ReactNode;
  readonly className?: string;
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

export function ConnectionWorkspaceShell({
  banner,
  children,
  className = "",
}: ConnectionWorkspaceShellProps) {
  return (
    <div className={`engineering-workspace connection-first-workspace${className === "" ? "" : ` ${className}`}`}>
      {banner}
      <div className="workspace-body">{children}</div>
    </div>
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
  return <UnityViewerContext.Provider value={unity ?? null}><div className="persistent-connection-viewer">
    {children}
    {unity === undefined ? null : <div className="unity-viewer-fallback"><UnityRatioIndicator value={unity} /></div>}
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
