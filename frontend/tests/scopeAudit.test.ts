import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const root = process.cwd();

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    return statSync(path).isDirectory() ? sourceFiles(path) : path.endsWith(".ts") || path.endsWith(".tsx") ? [path] : [];
  });
}

describe("Stage 2.3R2 frontend scope and accessibility audits", () => {
  it("contains no persistence, alternate API host, or frontend resistance formula", () => {
    const sources = sourceFiles(join(root, "src"));
    const content = sources.map((path) => readFileSync(path, "utf8")).join("\n");
    expect(content).not.toMatch(/localStorage|sessionStorage/);
    expect(content).not.toMatch(/https?:\/\/[^"']+\/api\/v1/);
    expect(content).not.toMatch(/\bR(?:br|nt|sh|cl|tt)\b|C_delta\s*=|C_lap\s*=|phi\s*=/);
    expect(content).not.toContain("expected_capacity");
    expect(content).not.toContain("expected_utilization");
    expect(content).not.toMatch(/RAM Connection|IDEA StatiCa/);
  });

  it("uses the approved renderer and no forbidden frontend framework", () => {
    const packageJson = JSON.parse(readFileSync(join(root, "package.json"), "utf8")) as {
      dependencies: Record<string, string>;
      devDependencies: Record<string, string>;
    };
    expect(packageJson.dependencies).toMatchObject({
      three: "0.185.1",
      "@react-three/fiber": "9.7.0",
    });
    expect(packageJson.devDependencies["@types/three"]).toBe("0.185.3");
    expect(packageJson.dependencies).not.toHaveProperty("@react-three/drei");
    expect(packageJson.dependencies).not.toHaveProperty("axios");
    expect(packageJson.dependencies).not.toHaveProperty("zustand");
  });

  it("sends template parameters without authoritative frontend placement trigonometry", () => {
    const templateSources = [
      readFileSync(join(root, "src", "fixtures", "j1Benchmarks.ts"), "utf8"),
      readFileSync(join(root, "src", "workspace", "SingleBoltEngineeringWorkspace.tsx"), "utf8"),
    ].join("\n");
    expect(templateSources).not.toMatch(/Math\.(?:sin|cos|acos|asin|atan|tan)\s*\(/u);
    expect(templateSources).not.toContain("member_placements");
    expect(templateSources).toContain("geometry_template");
  });

  it("retains reduced-motion, focus, responsive, and horizontal-table safeguards", () => {
    const styles = readFileSync(join(root, "src", "styles.css"), "utf8");
    expect(styles).toContain("@media (prefers-reduced-motion: reduce)");
    expect(styles).toContain(":focus-visible");
    expect(styles).toContain("@media (max-width: 760px)");
    expect(styles).toMatch(/\.table-scroll\s*{[^}]*overflow-x:\s*auto/s);
    expect(styles).toMatch(/\.workspace-body\s*{[^}]*grid-template-columns:\s*340px\s+minmax\(0,\s*1fr\)/s);
    expect(styles).toMatch(/\.properties-sidebar\s*{[^}]*overflow-y:\s*auto/s);
    expect(styles).toMatch(/\.properties-sidebar\s*{[^}]*overflow-x:\s*hidden/s);
    expect(styles).toMatch(/\.persistent-connection-viewer\s*{[^}]*position:\s*sticky/s);
    expect(styles).toMatch(/@media \(max-width:\s*820px\)[\s\S]*\.persistent-connection-viewer\s*{[^}]*position:\s*static/s);
    expect(styles).not.toMatch(/overscroll-behavior(?:-y)?:\s*contain/u);
    expect(styles).toMatch(/\.canvas-shell,[^}]*\.canvas-loading\s*{[^}]*min-height:\s*clamp\(/s);
  });

  it("reuses one connection shell and one sidebar group for direct and Tee workspaces", () => {
    const shell = readFileSync(join(root, "src", "workspace", "ConnectionWorkspaceShell.tsx"), "utf8");
    const selector = readFileSync(join(root, "src", "workspace", "ShearConnectionsWorkspace.tsx"), "utf8");
    const direct = readFileSync(join(root, "src", "workspace", "SingleBoltEngineeringWorkspace.tsx"), "utf8");
    const tee = readFileSync(join(root, "src", "workspace", "TeeConnectorWorkspace.tsx"), "utf8");

    expect(shell).toContain("export function ConnectionWorkspaceShell");
    expect(shell).toContain("export function SidebarGroup");
    expect(direct).toContain("<ConnectionWorkspaceShell");
    expect(tee).toContain("<ConnectionWorkspaceShell");
    expect(direct).toContain("<SidebarGroup");
    expect(tee).toContain("<SidebarGroup");
    expect(selector).toMatch(/<select\s+id="connection-type"/u);
    expect(selector).toContain('<optgroup label="Brace/beam connections">');
    expect(selector).not.toContain("connection-template-switcher");
  });

  it("keeps R4 navigation presentation-only, bounded, and free of render-loop state", () => {
    const scene = readFileSync(join(root, "src", "visualization", "EngineeringScene.tsx"), "utf8");
    const panel = readFileSync(join(root, "src", "visualization", "VisualizationPanel.tsx"), "utf8");
    const navigation = readFileSync(join(root, "src", "visualization", "viewportNavigation.ts"), "utf8");
    const styles = readFileSync(join(root, "src", "styles.css"), "utf8");

    expect(scene.match(/new OrbitControls\(/gu)).toHaveLength(1);
    expect(scene).toContain("onPointerUp");
    expect(scene).toContain("completeSelectionGesture");
    expect(scene).not.toContain("useFrame");
    expect(scene).not.toContain("requestAnimationFrame");
    expect(scene).not.toMatch(/onDrag(?:Start|End)?=/u);
    expect(panel).not.toContain("setCameraOrientation");
    expect(panel).toContain("updateCornerGlobalTriad");
    expect(panel).toContain("3D navigation: left-drag rotate \\u00b7 right-drag pan \\u00b7 wheel zoom");
    expect(navigation).toContain("controls.mouseButtons.LEFT = MOUSE.ROTATE");
    expect(navigation).toContain("controls.mouseButtons.RIGHT = MOUSE.PAN");
    expect(navigation).toContain("controls.mouseButtons.MIDDLE = MOUSE.DOLLY");
    expect(styles).toMatch(/\.selection-legend\s*{[^}]*pointer-events:\s*none/s);
    expect(styles).toMatch(/\.corner-global-triad\s*{[^}]*pointer-events:\s*none/s);
  });

  it("keeps R3 fastener hardware solid, canonical, and frontend-presentation-only", () => {
    const scene = readFileSync(join(root, "src", "visualization", "EngineeringScene.tsx"), "utf8");
    const model = readFileSync(join(root, "src", "visualization", "sceneModel.ts"), "utf8");
    const hardware = readFileSync(
      join(root, "src", "visualization", "fastenerPresentation.ts"),
      "utf8",
    );
    const backendContracts = readFileSync(
      join(root, "..", "backend", "src", "frp_master_connection", "api", "schemas.py"),
      "utf8",
    );

    expect(scene).toContain("canonicalCylinderRadius(value.diameter)");
    expect(scene).toContain('raycast={() => null}');
    expect(scene).toContain("depthTest={false}");
    expect(scene).toContain('value.kind !== "HOLE" ? null');
    expect(scene).toContain("<cylinderGeometry args={[radius, radius, geometry.length, 32]} />");
    expect(scene).toContain("<cylinderGeometry args={[geometry.radius, geometry.radius, geometry.length, 6]} />");
    expect(scene).toContain("<FastenerPrimitive");
    expect(scene).not.toMatch(/value\.kind\s*===\s*["']BOLT["'][\s\S]{0,160}wireframe/u);
    expect(scene).not.toMatch(/camera.*diameter|diameter.*camera/iu);
    expect(model).toContain("return diameter / 2;");
    expect(hardware).toContain("SCHEMATIC_HEAD_ACROSS_FLATS_RATIO = 1.5");
    expect(hardware).toContain("SCHEMATIC_HEAD_HEIGHT_RATIO = 0.625");
    expect(hardware).toContain("SCHEMATIC_NUT_ACROSS_FLATS_RATIO = 1.5");
    expect(hardware).toContain("SCHEMATIC_NUT_THICKNESS_RATIO = 0.875");
    expect(hardware).toContain('washer.hardwareLocation === "UNDER_HEAD"');
    expect(hardware).toContain('washer.hardwareLocation === "UNDER_NUT"');
    expect(hardware).not.toMatch(/import[^;]*(?:fingerprint|interference|resistance|utilization|capacity)/iu);
    expect(hardware).not.toMatch(/\b(?:calculate|resolve)(?:Fingerprint|Interference|Resistance|Utilization|Capacity)\b/u);
    expect(backendContracts).not.toMatch(/SCHEMATIC_(?:HEAD|NUT)_/u);
  });

  it("keeps R7 action labels projected, presentation-only, and pointer-isolated", () => {
    const scene = readFileSync(join(root, "src", "visualization", "EngineeringScene.tsx"), "utf8");
    const panel = readFileSync(join(root, "src", "visualization", "VisualizationPanel.tsx"), "utf8");
    const projection = readFileSync(
      join(root, "src", "visualization", "actionLabelProjection.ts"),
      "utf8",
    );
    const styles = readFileSync(join(root, "src", "styles.css"), "utf8");

    expect(scene).toContain("projectActionLabels");
    expect(scene).not.toContain("useFrame");
    expect(scene).not.toContain("requestAnimationFrame");
    expect(panel).toContain('className="action-label-layer"');
    expect(panel).not.toContain("applied-action-labels");
    expect(projection).toContain("point.project(camera)");
    expect(projection).not.toMatch(/signedValue|sense|Math\.sign|resistance|utilization/u);
    expect(styles).toMatch(/\.action-label-layer\s*{[^}]*pointer-events:\s*none/s);
    expect(styles).toMatch(/\.applied-action-label,[^{]*\.applied-action-editor\s*{[^}]*pointer-events:\s*auto/s);
    expect(styles).toMatch(/\.positive-action-label\s*{[^}]*pointer-events:\s*none/s);
  });

  it("keeps the R8 moment attachment and badge refinement presentation-only", () => {
    const scene = readFileSync(join(root, "src", "visualization", "EngineeringScene.tsx"), "utf8");
    const geometry = readFileSync(
      join(root, "src", "visualization", "actionPrimitiveGeometry.ts"),
      "utf8",
    );
    const panel = readFileSync(join(root, "src", "visualization", "VisualizationPanel.tsx"), "utf8");
    const styles = readFileSync(join(root, "src", "styles.css"), "utf8");

    expect(scene).toContain("calculateMomentArrowGeometry");
    expect(scene).toContain("position={vector(object.dimensions.headCenter)}");
    expect(scene).toContain("rotation={[0, 0, object.dimensions.headRotationZ]}");
    expect(scene).not.toContain("position={[-object.radius, -object.radius * 0.15, 0]}");
    expect(geometry).toContain("headBaseCenter");
    expect(geometry).toContain("headHeight / 2 - headOverlap");
    expect(geometry).not.toMatch(/signedValue|sense|resistance|utilization|right.hand/iu);
    expect(panel).toContain("minimumFractionDigits: 2");
    expect(panel).toContain("maximumFractionDigits: 2");
    expect(styles).toMatch(/\.applied-action-label\s*\{[^}]*background:\s*rgb\(255 252 250 \/ 20%\)/s);
    expect(styles).toMatch(/\.applied-action-editor\s*\{[^}]*background:\s*rgb\(255 252 250 \/ 94%\)/s);
  });

  it("uses one presentation-only region-embedded material-axis renderer without floating labels", () => {
    const scene = readFileSync(join(root, "src", "visualization", "EngineeringScene.tsx"), "utf8");
    const model = readFileSync(join(root, "src", "visualization", "sceneModel.ts"), "utf8");
    const presentation = readFileSync(
      join(root, "src", "visualization", "materialAxisPresentation.ts"),
      "utf8",
    );
    const panel = readFileSync(join(root, "src", "visualization", "VisualizationPanel.tsx"), "utf8");
    const direct = readFileSync(join(root, "src", "workspace", "SingleBoltEngineeringWorkspace.tsx"), "utf8");
    const tee = readFileSync(join(root, "src", "workspace", "TeeConnectorWorkspace.tsx"), "utf8");

    expect(scene).toContain("function RegionEmbeddedMaterialAxes");
    expect(scene).toContain("function BidirectionalMaterialAxis");
    expect(scene).toContain("function ThroughThicknessNormalMarker");
    expect(scene).toContain('materialAxisRepresentation: "REGION_EMBEDDED"');
    expect(scene).toContain('materialAxisRepresentation: "BIDIRECTIONAL"');
    expect(scene).toContain('materialAxisRepresentation: "NORMAL_MARKER"');
    expect(scene).toContain("presentation.origin");
    expect(scene).toContain("registerTTMarkerFacingUpdater");
    expect(scene).not.toContain("function MaterialAxes(");
    expect(scene).not.toContain('text="LW"');
    expect(scene).not.toContain('text="CW"');
    expect(scene).not.toContain('text="TT"');
    expect(scene).not.toContain("useFrame");
    expect(model).toContain("buildRegionEmbeddedMaterialAxisPresentation(axes, boxes, meshes)");
    expect(presentation).not.toMatch(/WIDE_FLANGE|I_SECTION|CHANNEL|ANGLE|TEE|RECTANGULAR_TUBE|FLAT_PLATE/u);
    expect(presentation).not.toMatch(/fingerprint|resistance|utilization|capacity|demand/iu);
    expect(panel).toContain("visibility.materialAxes ? <MaterialAxesLegend /> : null");
    expect(panel).toContain('aria-label="Material axes legend"');
    expect(panel).not.toContain("Web · CW");
    expect(direct).toContain("<VisualizationPanel");
    expect(tee).toContain("<VisualizationPanel");
  });
});
