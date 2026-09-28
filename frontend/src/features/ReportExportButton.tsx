import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import {
  currentReportSnapshot,
  reportGeneration,
  subscribeReportSession,
} from "../state/reportSession";
import { mat1FamilyKey, mat1Snapshot } from "../state/mat1Session";

interface Metadata {
  project_name: string;
  project_number: string;
  connection_id: string;
  location: string;
  revision: string;
  prepared_by: string;
  checked_by: string;
  notes: string;
}

const initial: Metadata = {
  project_name: "", project_number: "", connection_id: "", location: "",
  revision: "", prepared_by: "", checked_by: "", notes: "",
};

const fields: readonly { key: keyof Metadata; label: string; max: number }[] = [
  { key: "project_name", label: "Project name", max: 150 },
  { key: "project_number", label: "Project number", max: 80 },
  { key: "connection_id", label: "Connection ID", max: 80 },
  { key: "location", label: "Location", max: 150 },
  { key: "revision", label: "Report revision", max: 40 },
  { key: "prepared_by", label: "Prepared by", max: 120 },
  { key: "checked_by", label: "Checked by", max: 120 },
  { key: "notes", label: "Notes", max: 1500 },
];

function safeFilename(disposition: string | null): string {
  const match = /filename="([A-Za-z0-9_.-]+\.pdf)"/.exec(disposition ?? "");
  return match?.[1] ?? "connection-report.pdf";
}

export function ReportExportButton({ family, draft }: { readonly family: string; readonly draft?: unknown }) {
  const snapshot = useSyncExternalStore(
    subscribeReportSession,
    () => currentReportSnapshot(family),
  );
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"design" | "draft">("design");
  const [metadata, setMetadata] = useState<Metadata>(initial);
  const [paper, setPaper] = useState<"LETTER" | "A4">("LETTER");
  const [displayUnits, setDisplayUnits] = useState<"INHERIT" | "US_CUSTOMARY" | "SI">("INHERIT");
  const [reportType, setReportType] = useState<"ENGINEER_REPORT" | "FULL_TECHNICAL_AUDIT">("ENGINEER_REPORT");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const activeExport = useRef<AbortController | null>(null);
  const draftRef = useRef(draft);
  useEffect(() => { draftRef.current = draft; }, [draft]);

  function currentDraft(): unknown {
    const current = draftRef.current;
    if (!mat1Snapshot().active) return current;
    return { legacy_request: current, mat1_assignment: JSON.parse(mat1FamilyKey(family)) as unknown };
  }

  async function exportReport(): Promise<void> {
    const authority = currentReportSnapshot(family);
    if (mode === "design" && (authority.token === null || authority.dirty)) return;
    if (mode === "draft" && draftRef.current === undefined) return;
    const draftAtStart = mode === "draft" ? JSON.stringify(currentDraft()) : null;
    const generationAtStart = reportGeneration(family);
    const controller = new AbortController();
    activeExport.current = controller;
    const timeout = window.setTimeout(() => { controller.abort(); }, 120_000);
    setBusy(true);
    setError("");
    try {
      let handle = authority.token;
      if (mode === "draft") {
        const capture = await fetch("/api/v1/reports/input-only-snapshot", {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ family, draft: currentDraft() }),
          credentials: "same-origin",
          signal: controller.signal,
        });
        if (!capture.ok) {
          const body = await capture.json().catch(() => null) as { detail?: unknown } | null;
          throw new Error(typeof body?.detail === "string" ? body.detail : "Input snapshot failed.");
        }
        const captured = await capture.json() as { report_handle?: unknown };
        if (typeof captured.report_handle !== "string") throw new Error("Input snapshot has no report handle.");
        handle = captured.report_handle;
      }
      controller.signal.throwIfAborted();
      if (reportGeneration(family) !== generationAtStart ||
          (draftAtStart !== null && JSON.stringify(currentDraft()) !== draftAtStart)) {
        throw new Error("Inputs changed during export. Reopen the report dialog.");
      }
      const response = await fetch("/api/v1/reports/export", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/pdf" },
        body: JSON.stringify({ report_handle: handle, paper, display_units: displayUnits, mode: reportType, ...metadata }),
        credentials: "same-origin",
        signal: controller.signal,
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null) as { detail?: unknown } | null;
        throw new Error(typeof body?.detail === "string" ? body.detail : "PDF export failed.");
      }
      const file = await response.blob();
      if (controller.signal.aborted) throw new Error("PDF export was cancelled or timed out. Try again.");
      if (file.type !== "application/pdf") throw new Error("Server returned a non-PDF response.");
      if (reportGeneration(family) !== generationAtStart ||
          (draftAtStart !== null && JSON.stringify(currentDraft()) !== draftAtStart)) {
        throw new Error("Inputs changed during export. Reopen the report dialog.");
      }
      const url = URL.createObjectURL(file);
      const link = document.createElement("a");
      link.href = url;
      link.download = safeFilename(response.headers.get("Content-Disposition"));
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => { URL.revokeObjectURL(url); }, 60_000);
      setOpen(false);
    } catch (cause) {
      setError(controller.signal.aborted ? "PDF export was cancelled or timed out. Try again." :
        cause instanceof Error ? cause.message : "PDF export failed.");
    } finally {
      window.clearTimeout(timeout);
      activeExport.current = null;
      setBusy(false);
    }
  }

  const directReport = family === "multi-row" && typeof draft === "object" && draft !== null &&
    "direct_finalization_contract_version" in draft &&
    draft.direct_finalization_contract_version === "SHEAR01-DIRECT-F1";
  return <div className="report-export">
    <button type="button" onClick={() => {
      const current = currentReportSnapshot(family);
      setMode(current.token !== null && !current.dirty ? "design" : "draft");
      setOpen(true);
    }} disabled={(snapshot.token === null || snapshot.dirty) && draft === undefined}>
      Export PDF Report
    </button>
    {snapshot.dirty ? <span aria-live="polite">Inputs changed. Export submitted inputs only, or run Design Check for a current calculation report.</span> : null}
    {snapshot.token === null && !snapshot.dirty && draft === undefined ? <span aria-live="polite">Run a preview or design check to create a report snapshot.</span> : null}
    {open ? <div role="dialog" aria-modal="true" aria-label="Export PDF Report" className="report-export-dialog">
      <h2>{mode === "draft" ? "Submitted inputs report" : snapshot.kind === "input_only" ? "Inputs and model report" : "Full calculation report"}</h2>
      <p>{mode === "draft" ? "Current user inputs only; no native validation or calculation has run." : snapshot.kind === "input_only" ? "Inputs and model only; design not evaluated." : "Current backend calculation snapshot."}</p>
      {fields.map(({ key, label, max }) => <label key={key}>{label}
        <input value={metadata[key]} maxLength={max} onChange={event => { setMetadata({ ...metadata, [key]: event.target.value }); }} />
      </label>)}
      <label>Paper size <select value={paper} onChange={event => { setPaper(event.target.value as "LETTER" | "A4"); }}>
        <option value="LETTER">US Letter</option><option value="A4">A4</option>
      </select></label>
      <label>Display units <select value={displayUnits} onChange={event => { setDisplayUnits(event.target.value as "INHERIT" | "US_CUSTOMARY" | "SI"); }}>
        <option value="INHERIT">Calculation units</option><option value="US_CUSTOMARY">U.S. equivalents</option><option value="SI">S.I. equivalents</option>
      </select></label>
      {directReport && mode === "design" ? <label>Report detail <select value={reportType} onChange={event => { setReportType(event.target.value as "ENGINEER_REPORT" | "FULL_TECHNICAL_AUDIT"); }}>
        <option value="ENGINEER_REPORT">Engineer Report</option><option value="FULL_TECHNICAL_AUDIT">Full Technical Audit</option>
      </select></label> : null}
      {error ? <p role="alert">{error}</p> : null}
      <button type="button" onClick={() => { void exportReport(); }} disabled={busy || (mode === "design" && snapshot.dirty)}>
        {busy ? "Creating PDF…" : "Download PDF"}
      </button>
      <button type="button" onClick={() => { activeExport.current?.abort(); setOpen(false); }}>Cancel</button>
    </div> : null}
  </div>;
}
