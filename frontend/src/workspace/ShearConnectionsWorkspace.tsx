import { useState } from "react";

import { SingleBoltEngineeringWorkspace } from "./SingleBoltEngineeringWorkspace";
import { ClipAngleConnectorWorkspace } from "./ClipAngleConnectorWorkspace";
import { PairedClipAngleConnectorWorkspace } from "./PairedClipAngleConnectorWorkspace";
import { TeeConnectorWorkspace } from "./TeeConnectorWorkspace";
import { MultiMemberTeeWorkspace } from "./MultiMemberTeeWorkspace";
import { BeamConcretePairedAngleWorkspace } from "./BeamConcretePairedAngleWorkspace";
import { DirectSideLapConcreteWorkspace } from "./DirectSideLapConcreteWorkspace";
import { ColumnBaseWebAngleWorkspace } from "./ColumnBaseWebAngleWorkspace";
import { WebSpliceWorkspace } from "./WebSpliceWorkspace";
import { DoubleChannelTrussNodeWorkspace } from "./DoubleChannelTrussNodeWorkspace";

type ConnectionTemplate = "DIRECT_REFERENCE" | "FRP_TEE" | "SINGLE_CLIP_ANGLE" | "SYMMETRIC_PAIRED_CLIP_ANGLES" | "MULTI_MEMBER_TEE" | "BEAM_CONCRETE_PAIRED_ANGLE" | "DIRECT_SIDE_LAP_CONCRETE" | "COLUMN_BASE_WEB_ANGLES_CONCRETE" | "SYMMETRIC_DOUBLE_WEB_SPLICE" | "DOUBLE_CHANNEL_TRUSS_NODE_CONNECTION";

export function ShearConnectionsWorkspace() {
  const [template, setTemplate] = useState<ConnectionTemplate>("DIRECT_REFERENCE");
  return (
    <>
      <div className="connection-type-selector">
        <label htmlFor="connection-type">Connection type</label>
        <select
          id="connection-type"
          value={template}
          onChange={(event) => {
            setTemplate(event.currentTarget.value as ConnectionTemplate);
          }}
        >
          <optgroup label="Brace/beam connections">
            <option value="DIRECT_REFERENCE">Brace/beam connection — Direct</option>
            <option value="FRP_TEE">Brace/beam connection — Tee connector</option>
            <option value="SINGLE_CLIP_ANGLE">Brace/beam connection — Single clip angle</option>
            <option value="SYMMETRIC_PAIRED_CLIP_ANGLES">Brace/beam connection — Symmetric paired clip angles</option>
            <option value="MULTI_MEMBER_TEE">Brace/beam node — Multi-member Tee connector</option>
            <option value="DOUBLE_CHANNEL_TRUSS_NODE_CONNECTION">Double-Channel Truss Node</option>
          </optgroup>
          <optgroup label="Beam connections">
            <option value="SYMMETRIC_DOUBLE_WEB_SPLICE">Beam connection — Symmetric double web splice plates</option>
            <option value="BEAM_CONCRETE_PAIRED_ANGLE">Beam connection — Paired clip angles to concrete wall</option>
            <option value="DIRECT_SIDE_LAP_CONCRETE">Brace/beam connection — Direct side-lap Angle/Channel to concrete wall</option>
          </optgroup>
          <optgroup label="Column connections">
            <option value="COLUMN_BASE_WEB_ANGLES_CONCRETE">Column connection — Single/double base angles to concrete</option>
          </optgroup>
        </select>
      </div>
      {template === "DIRECT_REFERENCE" ? <SingleBoltEngineeringWorkspace /> : null}
      {template === "FRP_TEE" ? <TeeConnectorWorkspace /> : null}
      {template === "SINGLE_CLIP_ANGLE" ? <ClipAngleConnectorWorkspace /> : null}
      {template === "SYMMETRIC_PAIRED_CLIP_ANGLES" ? <PairedClipAngleConnectorWorkspace /> : null}
      {template === "MULTI_MEMBER_TEE" ? <MultiMemberTeeWorkspace /> : null}
      {template === "BEAM_CONCRETE_PAIRED_ANGLE" ? <BeamConcretePairedAngleWorkspace /> : null}
      {template === "DIRECT_SIDE_LAP_CONCRETE" ? <DirectSideLapConcreteWorkspace /> : null}
      {template === "COLUMN_BASE_WEB_ANGLES_CONCRETE" ? <ColumnBaseWebAngleWorkspace /> : null}
      {template === "SYMMETRIC_DOUBLE_WEB_SPLICE" ? <WebSpliceWorkspace /> : null}
      {template === "DOUBLE_CHANNEL_TRUSS_NODE_CONNECTION" ? <DoubleChannelTrussNodeWorkspace /> : null}
    </>
  );
}
