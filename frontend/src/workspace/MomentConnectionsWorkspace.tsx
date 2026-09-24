import { useState } from "react";
import { ColumnMomentBaseWorkspace } from "./ColumnMomentBaseWorkspace";
import { AngleColumnMomentBaseWorkspace } from "./AngleColumnMomentBaseWorkspace";

import { ChannelMomentSpliceWorkspace } from "./ChannelMomentSpliceWorkspace";
import { WIMomentSpliceWorkspace } from "./WIMomentSpliceWorkspace";
import { WIFrpSupportMomentWorkspace } from "./WIFrpSupportMomentWorkspace";
import { WIWallMomentWorkspace } from "./WIWallMomentWorkspace";
import { StairStringerMiterWorkspace } from "./StairStringerMiterWorkspace";

export function MomentConnectionsWorkspace() {
  const [connectionType, setConnectionType] = useState<"WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE" | "CHANNEL_BEAM_MAJOR_AXIS_MOMENT_SPLICE" | "WI_BEAM_CONCRETE_WALL_MAJOR_AXIS_MOMENT_CONNECTION" | "WI_BEAM_FRP_SUPPORT_MAJOR_AXIS_MOMENT_CONNECTION" | "ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_CONNECTION" | "WI_RHS_SRS_COLUMN_MOMENT_BASE_CONNECTION" | "STAIR_STRINGER_MITER_CONNECTION">("WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE");
  return <><div className="connection-type-selector"><label htmlFor="moment-connection-type">Connection type</label><select id="moment-connection-type" value={connectionType} onChange={(event) => { setConnectionType(event.currentTarget.value as typeof connectionType); }}><optgroup label="Beam moment connections"><option value="WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE">W/I Beam Moment Splice</option><option value="CHANNEL_BEAM_MAJOR_AXIS_MOMENT_SPLICE">Channel Beam Moment Splice</option><option value="WI_BEAM_CONCRETE_WALL_MAJOR_AXIS_MOMENT_CONNECTION">W/I Beam to Concrete Wall Moment Connection</option><option value="WI_BEAM_FRP_SUPPORT_MAJOR_AXIS_MOMENT_CONNECTION">W/I Beam to FRP Support Moment Connection</option></optgroup><optgroup label="Column moment connections"><option value="ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_CONNECTION">Angle Column Two-Leg Moment Base</option><option value="WI_RHS_SRS_COLUMN_MOMENT_BASE_CONNECTION">W/I, RHS and SRS Column Moment Base</option></optgroup><optgroup label="Stair connections"><option value="STAIR_STRINGER_MITER_CONNECTION">Stair Stringer Miter Connection</option></optgroup></select></div>{connectionType === "STAIR_STRINGER_MITER_CONNECTION" ? <StairStringerMiterWorkspace /> : connectionType === "WI_BEAM_MAJOR_AXIS_MOMENT_SPLICE" ? <WIMomentSpliceWorkspace /> : connectionType === "CHANNEL_BEAM_MAJOR_AXIS_MOMENT_SPLICE" ? <ChannelMomentSpliceWorkspace /> : connectionType === "WI_BEAM_CONCRETE_WALL_MAJOR_AXIS_MOMENT_CONNECTION" ? <WIWallMomentWorkspace /> : connectionType === "ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_CONNECTION" ? <AngleColumnMomentBaseWorkspace /> : connectionType === "WI_RHS_SRS_COLUMN_MOMENT_BASE_CONNECTION" ? <ColumnMomentBaseWorkspace /> : <WIFrpSupportMomentWorkspace />}</>;
}
