import type { UnityView } from "./unityRatio";

export function UnityRatioIndicator({ value }: { readonly value: UnityView }) {
  return (
    <div className={`unity-indicator unity-indicator-${value.tone}`} role="group" aria-live="polite" aria-label={`Unity ratio: ${value.ratioText}. ${value.status}`} data-unity-tone={value.tone}>
      <div className="unity-indicator-main"><strong>{value.ratioText}</strong><span>{value.status}</span></div>
      <details className="unity-indicator-details">
        <summary aria-label="Unity ratio details">Details</summary>
        <div><p>{value.governing === null ? "Governing check: unavailable" : `Governing check: ${value.governing}`}</p><p>Coverage: {value.explanation}</p></div>
      </details>
    </div>
  );
}
