import { useId } from "react";
import type { Alignment } from "../api/directTwoBolt";

export function DirectBoltAlignment({ alignment, onChange, calculationScope }: {
  alignment: Alignment;
  onChange: (alignment: Alignment) => void;
  calculationScope?: string;
}) {
  const id = useId();
  return <fieldset className="direct-bolt-alignment" aria-describedby={id}>
    <legend>Bolt alignment</legend>
    <div className="direct-bolt-alignment-options">
      <label><input type="radio" name={id} value="BRACE" checked={alignment === "BRACE"} onChange={() => { onChange("BRACE"); }} /><span>Along brace <small>(default)</small></span></label>
      <label><input type="radio" name={id} value="SUPPORT" checked={alignment === "SUPPORT"} onChange={() => { onChange("SUPPORT"); }} /><span>Along supporting member</span></label>
    </div>
    <p id={id} aria-label="Help: Bolt alignment">Alignment joins the two bolt centers. Bolt shafts remain normal to the selected interface.</p>
    <p>{calculationScope ?? (alignment === "BRACE" ? "Existing brace calculations require the current layout to satisfy the supported method guards." : "Geometry and constructability only. Structural design is not evaluated.")}</p>
  </fieldset>;
}
