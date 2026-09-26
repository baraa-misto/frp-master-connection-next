/** In-memory, per-workspace authority for exporting the current native response. */

export interface ReportSnapshotState {
  readonly token: string | null;
  readonly kind: "design" | "input_only" | null;
  readonly dirty: boolean;
}

const empty: ReportSnapshotState = { token: null, kind: null, dirty: false };
const snapshots = new Map<string, ReportSnapshotState>();
const generations = new Map<string, number>();
const listeners = new Set<() => void>();

function notify(): void {
  for (const listener of listeners) listener();
}

export function subscribeReportSession(listener: () => void): () => void {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

export function currentReportSnapshot(family: string): ReportSnapshotState {
  return snapshots.get(family) ?? empty;
}

export function reportGeneration(family: string): number {
  return generations.get(family) ?? 0;
}

export function invalidateReportSnapshot(family: string): void {
  generations.set(family, reportGeneration(family) + 1);
  const prior = currentReportSnapshot(family);
  snapshots.set(family, { ...prior, dirty: true });
  notify();
}

export function acceptReportSnapshot(
  family: string,
  token: unknown,
  kind: "design" | "input_only",
  generation: number,
): void {
  if (generation !== reportGeneration(family) || typeof token !== "string" || token === "") return;
  const current = currentReportSnapshot(family);
  if (kind === "input_only" && current.kind === "design" && !current.dirty) return;
  snapshots.set(family, { token, kind, dirty: false });
  notify();
}
