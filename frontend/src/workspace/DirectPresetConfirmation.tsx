export function DirectPresetConfirmation({ onConfirm, onCancel }: { readonly onConfirm: () => void; readonly onCancel: () => void }) {
  return <div className="hybrid-preset-backdrop"><section role="alertdialog" aria-modal="true" aria-labelledby="preset-confirm-title" aria-describedby="preset-confirm-description" className="hybrid-preset-confirm" onKeyDown={(event) => {
    if (event.key === "Escape") { event.preventDefault(); onCancel(); }
    if (event.key === "Tab") {
      event.preventDefault();
      const buttons = event.currentTarget.querySelectorAll("button");
      buttons.item(event.target === buttons.item(0) ? 1 : 0).focus();
    }
  }}><h3 id="preset-confirm-title">Replace current connection inputs?</h3><p id="preset-confirm-description">Geometry, source properties and actions will be replaced. Current inputs are saved for Restore previous inputs. Native MAT1 selections and project conditions remain in the session. Results and report handles will be invalidated.</p><button type="button" onClick={onConfirm}>Confirm replacement</button><button type="button" autoFocus onClick={onCancel}>Keep current inputs</button></section></div>;
}
