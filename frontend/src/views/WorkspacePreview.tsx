import type { PrimaryCategoryId } from "../domain/designCategories";
import { ShearConnectionsWorkspace } from "../workspace/ShearConnectionsWorkspace";
import { MomentConnectionsWorkspace } from "../workspace/MomentConnectionsWorkspace";

interface WorkspacePreviewProps {
  readonly selectedCategory: PrimaryCategoryId | null;
}

export function WorkspacePreview({ selectedCategory }: WorkspacePreviewProps) {
  if (selectedCategory === "shear") {
    return <ShearConnectionsWorkspace />;
  }
  if (selectedCategory === "moment") {
    return <MomentConnectionsWorkspace />;
  }

  return (
    <section className="workspace" aria-labelledby="workspace-title">
      <div className="section-heading workspace-heading">
        <p className="section-number">02</p>
        <div>
          <h2 id="workspace-title">No primary category selected</h2>
          <p>Select Shear Connections or Moment Connections to open an engineering workspace.</p>
        </div>
      </div>
    </section>
  );
}
