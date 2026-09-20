import { Canvas, useThree } from "@react-three/fiber";
import { useCallback, useEffect, useMemo, useRef } from "react";
import {
  ArrowHelper,
  BufferGeometry,
  CanvasTexture,
  Color,
  ConeGeometry,
  DoubleSide,
  type Group,
  LineBasicMaterial,
  LineLoop,
  Matrix4,
  type Mesh,
  MeshBasicMaterial,
  Quaternion,
  TorusGeometry,
  Vector3,
} from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

import type { ProjectedActionLabel } from "./actionLabelContract";
import { projectActionLabels } from "./actionLabelProjection";
import { calculateMomentArrowGeometry } from "./actionPrimitiveGeometry";
import {
  buildFastenerPresentations,
  type FastenerPresentation,
  type SchematicHexHardware,
} from "./fastenerPresentation";
import type {
  SceneArrow,
  SceneBox,
  SceneCylinder,
  SceneFrame,
  SceneMaterialAxes,
  SceneMarker,
  SceneTriangleMesh,
  SceneViewId,
  SceneZone,
  SingleBoltSceneModel,
  Vec3,
} from "./sceneModel";
import {
  SCENE_VIEWS,
  calculateCameraClippingPlanes,
  calculateOrthographicZoom,
  calculatePerspectiveDistance,
  canonicalCylinderRadius,
} from "./sceneModel";
import {
  buildThroughThicknessMarkerBasis,
  classifyThroughThicknessMarkerFacing,
  materialAxisDepthTest,
} from "./materialAxisPresentation";
import {
  beginSelectionGesture,
  cancelSelectionGesture,
  completeSelectionGesture,
  createSelectionGestureState,
  installViewportNavigation,
} from "./viewportNavigation";
import type { SelectionGestureState } from "./viewportNavigation";

export type SceneDisplayMode = "SOLID" | "XRAY";

export interface SceneVisibility {
  readonly physicalGeometry: boolean;
  readonly deferredGeometry: boolean;
  readonly interfaceZones: boolean;
  readonly selectedContactSurface: boolean;
  readonly boltAndHoles: boolean;
  readonly cornerGlobalTriad: boolean;
  readonly globalAxes: boolean;
  readonly memberAxes: "OFF" | "SELECTED" | "ALL";
  readonly connectorAxes: boolean;
  readonly interfaceAxes: boolean;
  readonly boltGroupAxes: boolean;
  readonly materialAxes: boolean;
  readonly referencePoints: boolean;
  readonly boltAxis: boolean;
  readonly positiveDirections: boolean;
  readonly appliedDirections: boolean;
  readonly actionValues: boolean;
  readonly zeroActions: boolean;
  readonly perBoltDemands: boolean;
}

export type SceneSelection =
  | { readonly kind: "MEMBER"; readonly id: string }
  | { readonly kind: "BOLT"; readonly id: string }
  | { readonly kind: "CONTACT"; readonly id: string };

export interface SceneInterfaceHighlight {
  readonly interfaceId: string;
  readonly label: string;
}

export interface CameraOrientation2D {
  readonly x: readonly [number, number];
  readonly y: readonly [number, number];
  readonly z: readonly [number, number];
}

interface EngineeringSceneProps {
  readonly model: SingleBoltSceneModel;
  readonly view: SceneViewId;
  readonly visibility: SceneVisibility;
  readonly resetNonce: number;
  readonly displayMode: SceneDisplayMode;
  readonly selection: SceneSelection;
  readonly onSelect: (selection: SceneSelection) => void;
  readonly interfaceHighlight: SceneInterfaceHighlight | null;
  readonly onCameraOrientationChange: (orientation: CameraOrientation2D) => void;
  readonly onActionLabelProjectionChange: (
    projections: readonly ProjectedActionLabel[],
  ) => void;
}

function vector(value: Vec3): Vector3 {
  return new Vector3(value.x, value.y, value.z);
}

function setCameraZoom(camera: { zoom: number }, zoom: number): void {
  camera.zoom = zoom;
}

function setCameraClipping(
  camera: { far: number; near: number },
  clipping: { readonly far: number; readonly near: number },
): void {
  camera.near = clipping.near;
  camera.far = clipping.far;
}

function basisQuaternion(basis: readonly [Vec3, Vec3, Vec3]): Quaternion {
  const matrix = new Matrix4().makeBasis(vector(basis[0]), vector(basis[1]), vector(basis[2]));
  return new Quaternion().setFromRotationMatrix(matrix);
}

function midpoint(first: Vec3, second: Vec3): Vector3 {
  return vector(first).add(vector(second)).multiplyScalar(0.5);
}

function BoxPrimitive({ value, displayMode, selected, onSelect, selectionGesture }: {
  readonly value: SceneBox;
  readonly displayMode: SceneDisplayMode;
  readonly selected: boolean;
  readonly onSelect: (selection: SceneSelection) => void;
  readonly selectionGesture: SelectionGestureState;
}) {
  const quaternion = useMemo(() => basisQuaternion(value.basis), [value.basis]);
  const xray = displayMode === "XRAY";
  const color = value.deferred
    ? "#b48945"
    : value.ownerRole === "BRACE"
      ? "#245f8f"
      : value.ownerRole === "COLUMN"
        ? "#8b9dad"
        : "#6f8192";
  return (
    <mesh
      position={vector(value.center)}
      quaternion={quaternion}
      userData={{ selectionPriority: 1 }}
      onPointerDown={(event) => {
        beginSelectionGesture(
          selectionGesture,
          event.pointerId,
          event.nativeEvent.clientX,
          event.nativeEvent.clientY,
        );
      }}
      onPointerCancel={() => { cancelSelectionGesture(selectionGesture); }}
      onPointerUp={(event) => {
        if (event.intersections.some((intersection) => Number(intersection.object.userData.selectionPriority ?? 0) > 1)) return;
        if (!completeSelectionGesture(
          selectionGesture,
          event.pointerId,
          event.nativeEvent.clientX,
          event.nativeEvent.clientY,
        )) return;
        event.stopPropagation();
        onSelect({ kind: "MEMBER", id: value.ownerId });
      }}
    >
      <boxGeometry args={[value.size.x, value.size.y, value.size.z]} />
      <meshStandardMaterial
        color={color}
        opacity={value.deferred ? 0.2 : xray ? 0.32 : 1}
        transparent={value.deferred || xray}
        roughness={0.68}
        metalness={0.08}
        wireframe={value.deferred}
        emissive={selected ? "#ffe08a" : value.interference ? "#d64032" : "#000000"}
        emissiveIntensity={selected ? 0.35 : value.interference ? 0.5 : 0}
      />
    </mesh>
  );
}

function TriangleMeshPrimitive({ value, displayMode, selected, onSelect, selectionGesture }: {
  readonly value: SceneTriangleMesh;
  readonly displayMode: SceneDisplayMode;
  readonly selected: boolean;
  readonly onSelect: (selection: SceneSelection) => void;
  readonly selectionGesture: SelectionGestureState;
}) {
  const geometry = useMemo(() => {
    const result = new BufferGeometry().setFromPoints(value.points.map(vector));
    result.computeVertexNormals();
    return result;
  }, [value.points]);
  useEffect(() => () => { geometry.dispose(); }, [geometry]);
  const xray = displayMode === "XRAY";
  const color = value.ownerRole === "BRACE"
    ? "#245f8f"
    : value.ownerRole === "COLUMN"
      ? "#8b9dad"
      : "#6f8192";
  return (
    <mesh
      geometry={geometry}
      userData={{ selectionPriority: 1 }}
      onPointerDown={(event) => {
        beginSelectionGesture(
          selectionGesture,
          event.pointerId,
          event.nativeEvent.clientX,
          event.nativeEvent.clientY,
        );
      }}
      onPointerCancel={() => { cancelSelectionGesture(selectionGesture); }}
      onPointerUp={(event) => {
        if (!completeSelectionGesture(
          selectionGesture,
          event.pointerId,
          event.nativeEvent.clientX,
          event.nativeEvent.clientY,
        )) return;
        event.stopPropagation();
        onSelect({ kind: "MEMBER", id: value.ownerId });
      }}
    >
      <meshStandardMaterial
        color={color}
        opacity={xray ? 0.32 : 1}
        transparent={xray}
        roughness={0.68}
        metalness={0.08}
        side={DoubleSide}
        emissive={selected ? "#ffe08a" : "#000000"}
        emissiveIntensity={selected ? 0.35 : 0}
      />
    </mesh>
  );
}

function CylinderPrimitive({ value, selected, onSelect, selectionGesture }: {
  readonly value: SceneCylinder;
  readonly selected: boolean;
  readonly onSelect: (selection: SceneSelection) => void;
  readonly selectionGesture: SelectionGestureState;
}) {
  const geometry = useMemo(() => {
    const start = vector(value.start);
    const end = vector(value.end);
    const direction = end.clone().sub(start);
    const length = direction.length();
    const quaternion = new Quaternion().setFromUnitVectors(
      new Vector3(0, 1, 0),
      direction.normalize(),
    );
    return { length, quaternion, position: midpoint(value.start, value.end) };
  }, [value]);
  const radius = canonicalCylinderRadius(value.diameter);
  const diameterOutline = value.kind !== "HOLE" ? null : (
    <mesh
      position={geometry.position}
      quaternion={geometry.quaternion}
      renderOrder={12}
      raycast={() => null}
    >
      <cylinderGeometry args={[radius, radius, geometry.length, 32, 1, true]} />
      <meshBasicMaterial
        color="#8b4b00"
        depthTest={false}
        depthWrite={false}
        opacity={0.9}
        transparent
        wireframe
      />
    </mesh>
  );
  return (
    <>
      <mesh
        position={geometry.position}
        quaternion={geometry.quaternion}
        userData={{ selectionPriority: 3, fastenerPart: value.kind, ownerBoltId: value.ownerBoltId }}
        onPointerDown={(event) => {
          beginSelectionGesture(
            selectionGesture,
            event.pointerId,
            event.nativeEvent.clientX,
            event.nativeEvent.clientY,
          );
        }}
        onPointerCancel={() => { cancelSelectionGesture(selectionGesture); }}
        onPointerUp={(event) => {
          if (!completeSelectionGesture(
            selectionGesture,
            event.pointerId,
            event.nativeEvent.clientX,
            event.nativeEvent.clientY,
          )) return;
          event.stopPropagation();
          onSelect({ kind: "BOLT", id: value.ownerBoltId });
        }}
      >
        <cylinderGeometry args={[radius, radius, geometry.length, 32]} />
        <meshStandardMaterial
          color={value.kind === "HOLE" ? "#f0ad3d" : "#d88919"}
          emissive={selected ? "#ffe08a" : value.kind === "HOLE" ? "#000000" : "#6a3600"}
          emissiveIntensity={selected ? 0.7 : value.kind === "HOLE" ? 0 : 0.28}
          opacity={value.kind === "HOLE" ? 0.22 : 1}
          transparent
          wireframe={value.kind === "HOLE"}
        />
      </mesh>
      {diameterOutline}
    </>
  );
}

function SchematicHexPrimitive({ value, selected, onSelect, selectionGesture }: {
  readonly value: SchematicHexHardware;
  readonly selected: boolean;
  readonly onSelect: (selection: SceneSelection) => void;
  readonly selectionGesture: SelectionGestureState;
}) {
  const geometry = useMemo(() => {
    const start = vector(value.start);
    const end = vector(value.end);
    const direction = end.clone().sub(start);
    const length = direction.length();
    const quaternion = new Quaternion().setFromUnitVectors(
      new Vector3(0, 1, 0),
      direction.normalize(),
    );
    return {
      length,
      position: midpoint(value.start, value.end),
      quaternion,
      // cylinderGeometry uses circumradius; this conversion retains exact across-flats.
      radius: value.acrossFlats / Math.sqrt(3),
    };
  }, [value]);
  return (
    <mesh
      position={geometry.position}
      quaternion={geometry.quaternion}
      userData={{ selectionPriority: 3, fastenerPart: value.kind, ownerBoltId: value.ownerBoltId }}
      onPointerDown={(event) => {
        beginSelectionGesture(
          selectionGesture,
          event.pointerId,
          event.nativeEvent.clientX,
          event.nativeEvent.clientY,
        );
      }}
      onPointerCancel={() => { cancelSelectionGesture(selectionGesture); }}
      onPointerUp={(event) => {
        if (!completeSelectionGesture(
          selectionGesture,
          event.pointerId,
          event.nativeEvent.clientX,
          event.nativeEvent.clientY,
        )) return;
        event.stopPropagation();
        onSelect({ kind: "BOLT", id: value.ownerBoltId });
      }}
    >
      <cylinderGeometry args={[geometry.radius, geometry.radius, geometry.length, 6]} />
      <meshStandardMaterial
        color={value.kind === "HEAD" ? "#c87813" : "#a85e0a"}
        emissive={selected ? "#ffe08a" : "#5c2e00"}
        emissiveIntensity={selected ? 0.7 : 0.2}
        metalness={0.18}
        roughness={0.52}
      />
    </mesh>
  );
}

function FastenerPrimitive({ value, selected, onSelect, selectionGesture }: {
  readonly value: FastenerPresentation;
  readonly selected: boolean;
  readonly onSelect: (selection: SceneSelection) => void;
  readonly selectionGesture: SelectionGestureState;
}) {
  return (
    <>
      <CylinderPrimitive value={value.shank} selected={selected} onSelect={onSelect} selectionGesture={selectionGesture} />
      {value.washers.map((washer) => (
        <CylinderPrimitive key={washer.id} value={washer} selected={selected} onSelect={onSelect} selectionGesture={selectionGesture} />
      ))}
      {value.renderedHardware.map((hardware) => (
        <SchematicHexPrimitive key={hardware.id} value={hardware} selected={selected} onSelect={onSelect} selectionGesture={selectionGesture} />
      ))}
    </>
  );
}

function ArrowObject({ origin, axis, color, length, depthTest }: {
  readonly origin: Vec3;
  readonly axis: Vec3;
  readonly color: string;
  readonly length: number;
  readonly depthTest?: boolean;
}) {
  const arrow = useMemo(() => {
    const result = new ArrowHelper(
        vector(axis).normalize(),
        vector(origin),
        length,
        new Color(color),
        length * 0.22,
        length * 0.1,
    );
    if (depthTest !== undefined) {
      const materials = [result.line.material, result.cone.material].flat();
      for (const material of materials) {
        material.depthTest = depthTest;
        material.depthWrite = false;
      }
      result.line.renderOrder = 14;
      result.cone.renderOrder = 14;
    }
    return result;
  }, [axis, color, depthTest, length, origin]);
  useEffect(() => () => { arrow.dispose(); }, [arrow]);
  return <primitive object={arrow} />;
}

function AxisLabel({ origin, axis, length, text, color }: {
  readonly origin: Vec3;
  readonly axis: Vec3;
  readonly length: number;
  readonly text: string;
  readonly color: string;
}) {
  const texture = useMemo(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 128;
    canvas.height = 64;
    const context = canvas.getContext("2d");
    if (context !== null) {
      context.clearRect(0, 0, canvas.width, canvas.height);
      context.font = "700 42px system-ui";
      context.textAlign = "center";
      context.textBaseline = "middle";
      context.fillStyle = "rgba(255,255,255,0.92)";
      context.fillRect(34, 5, 60, 54);
      context.fillStyle = color;
      context.fillText(text, 64, 32);
    }
    return new CanvasTexture(canvas);
  }, [color, text]);
  useEffect(() => () => { texture.dispose(); }, [texture]);
  const position = vector(origin).add(vector(axis).normalize().multiplyScalar(length * 1.12));
  return (
    <sprite position={position} scale={[length * 0.56, length * 0.28, 1]}>
      <spriteMaterial map={texture} transparent depthTest={false} />
    </sprite>
  );
}

function MomentArrow({ value, length, color }: {
  readonly value: SceneArrow;
  readonly length: number;
  readonly color: string;
}) {
  const object = useMemo(() => {
    const quaternion = new Quaternion().setFromUnitVectors(
      new Vector3(0, 0, 1),
      vector(value.axis).normalize(),
    );
    const dimensions = calculateMomentArrowGeometry(length);
    const geometry = new TorusGeometry(
      dimensions.radius,
      dimensions.tubeRadius,
      10,
      44,
      dimensions.arcAngle,
    );
    const material = new MeshBasicMaterial({ color });
    const coneGeometry = new ConeGeometry(
      dimensions.headRadius,
      dimensions.headHeight,
      14,
    );
    const coneMaterial = new MeshBasicMaterial({ color });
    return { quaternion, geometry, material, coneGeometry, coneMaterial, dimensions };
  }, [color, length, value.axis]);
  useEffect(
    () => () => {
      object.geometry.dispose();
      object.material.dispose();
      object.coneGeometry.dispose();
      object.coneMaterial.dispose();
    },
    [object],
  );
  return (
    <group position={vector(value.origin)} quaternion={object.quaternion}>
      <mesh geometry={object.geometry} material={object.material} />
      <mesh
        geometry={object.coneGeometry}
        material={object.coneMaterial}
        position={vector(object.dimensions.headCenter)}
        rotation={[0, 0, object.dimensions.headRotationZ]}
      />
    </group>
  );
}

function ActionArrow({ value, radius, positive }: {
  readonly value: SceneArrow;
  readonly radius: number;
  readonly positive: boolean;
}) {
  const color = positive ? "#304f75" : value.isZero ? "#777f87" : "#b44432";
  const length = radius * (positive ? 0.45 : 0.55);
  return value.kind === "ROTATIONAL" ? (
    <MomentArrow value={value} length={length} color={color} />
  ) : (
    <ArrowObject origin={value.origin} axis={value.axis} color={color} length={length} />
  );
}

function FrameAxes({ value, length }: { readonly value: SceneFrame; readonly length: number }) {
  const labels = value.kind === "GLOBAL" ? (["X", "Y", "Z"] as const) : (["x", "y", "z"] as const);
  return (
    <group>
      <ArrowObject origin={value.origin} axis={value.xAxis} color="#c83838" length={length} />
      <ArrowObject origin={value.origin} axis={value.yAxis} color="#32824d" length={length} />
      <ArrowObject origin={value.origin} axis={value.zAxis} color="#3468b2" length={length} />
      <AxisLabel origin={value.origin} axis={value.xAxis} length={length} text={labels[0]} color="#9f2020" />
      <AxisLabel origin={value.origin} axis={value.yAxis} length={length} text={labels[1]} color="#1f6c39" />
      <AxisLabel origin={value.origin} axis={value.zAxis} length={length} text={labels[2]} color="#24559c" />
    </group>
  );
}

function negate(value: Vec3): Vec3 {
  return { x: -value.x, y: -value.y, z: -value.z };
}

function BidirectionalMaterialAxis({ origin, axis, color, length, depthTest, kind }: {
  readonly origin: Vec3;
  readonly axis: Vec3;
  readonly color: string;
  readonly length: number;
  readonly depthTest: boolean;
  readonly kind: "LW" | "CW";
}) {
  return (
    <group userData={{ materialAxisKind: kind, materialAxisRepresentation: "BIDIRECTIONAL" }}>
      <ArrowObject origin={origin} axis={axis} color={color} length={length / 2} depthTest={depthTest} />
      <ArrowObject origin={origin} axis={negate(axis)} color={color} length={length / 2} depthTest={depthTest} />
    </group>
  );
}

type TTMarkerFacingUpdater = (cameraPosition: Vec3) => void;
type RegisterTTMarkerFacingUpdater = (
  id: string,
  updater: TTMarkerFacingUpdater | null,
) => void;

function ThroughThicknessNormalMarker({ value, depthTest, registerFacingUpdater }: {
  readonly value: SceneMaterialAxes;
  readonly depthTest: boolean;
  readonly registerFacingUpdater: RegisterTTMarkerFacingUpdater;
}) {
  const presentation = value.presentation;
  const dotRef = useRef<Mesh>(null);
  const crossRef = useRef<Group>(null);
  const tangentRef = useRef<Mesh>(null);
  const updateFacing = useCallback<TTMarkerFacingUpdater>((cameraPosition) => {
    if (presentation === null) return;
    const facing = classifyThroughThicknessMarkerFacing(
      presentation.origin,
      value.throughThickness,
      cameraPosition,
    );
    if (dotRef.current !== null) dotRef.current.visible = facing === "DOT";
    if (crossRef.current !== null) crossRef.current.visible = facing === "CROSS";
    if (tangentRef.current !== null) tangentRef.current.visible = facing === "TANGENT";
  }, [presentation, value.throughThickness]);
  useEffect(() => {
    registerFacingUpdater(value.id, updateFacing);
    return () => { registerFacingUpdater(value.id, null); };
  }, [registerFacingUpdater, updateFacing, value.id]);
  if (presentation === null) return null;
  const radius = presentation.markerRadius;
  const quaternion = basisQuaternion(buildThroughThicknessMarkerBasis(value.throughThickness));
  return (
    <group
      position={vector(presentation.origin)}
      quaternion={quaternion}
      userData={{ materialAxisKind: "TT", materialAxisRepresentation: "NORMAL_MARKER" }}
    >
      <mesh renderOrder={14}>
        <torusGeometry args={[radius, radius * 0.14, 8, 28]} />
        <meshBasicMaterial color="#15858a" depthTest={depthTest} depthWrite={false} />
      </mesh>
      <mesh ref={dotRef} position={[0, 0, radius * 0.05]} renderOrder={14}>
        <sphereGeometry args={[radius * 0.27, 14, 10]} />
        <meshBasicMaterial color="#15858a" depthTest={depthTest} depthWrite={false} />
      </mesh>
      <group ref={crossRef} visible={false}>
        <mesh rotation={[0, 0, Math.PI / 4]} renderOrder={14}>
          <boxGeometry args={[radius * 1.05, radius * 0.16, radius * 0.08]} />
          <meshBasicMaterial color="#15858a" depthTest={depthTest} depthWrite={false} />
        </mesh>
        <mesh rotation={[0, 0, -Math.PI / 4]} renderOrder={14}>
          <boxGeometry args={[radius * 1.05, radius * 0.16, radius * 0.08]} />
          <meshBasicMaterial color="#15858a" depthTest={depthTest} depthWrite={false} />
        </mesh>
      </group>
      <mesh ref={tangentRef} visible={false} renderOrder={14}>
        <torusGeometry args={[radius * 0.55, radius * 0.09, 8, 24]} />
        <meshBasicMaterial color="#15858a" depthTest={depthTest} depthWrite={false} />
      </mesh>
    </group>
  );
}

function RegionEmbeddedMaterialAxes({ value, displayMode, registerFacingUpdater }: {
  readonly value: SceneMaterialAxes;
  readonly displayMode: SceneDisplayMode;
  readonly registerFacingUpdater: RegisterTTMarkerFacingUpdater;
}) {
  const presentation = value.presentation;
  if (presentation === null) return null;
  const depthTest = materialAxisDepthTest(displayMode);
  return (
    <group
      userData={{
        componentId: value.componentId,
        elementId: value.elementId,
        materialRegionId: value.materialRegionId,
        materialAxisRepresentation: "REGION_EMBEDDED",
      }}
    >
      <BidirectionalMaterialAxis
        origin={presentation.origin}
        axis={value.lengthwise}
        color="#7a3fa0"
        length={presentation.lengthwiseLength}
        depthTest={depthTest}
        kind="LW"
      />
      <BidirectionalMaterialAxis
        origin={presentation.origin}
        axis={value.crosswise}
        color="#c67b20"
        length={presentation.crosswiseLength}
        depthTest={depthTest}
        kind="CW"
      />
      <ThroughThicknessNormalMarker
        value={value}
        depthTest={depthTest}
        registerFacingUpdater={registerFacingUpdater}
      />
    </group>
  );
}

function Marker({ value, radius }: { readonly value: SceneMarker; readonly radius: number }) {
  return (
    <mesh position={vector(value.position)}>
      <sphereGeometry args={[radius, 16, 12]} />
      <meshBasicMaterial color={value.connected ? "#d35236" : "#f0c14d"} />
    </mesh>
  );
}

function ZoneOutline({ value }: { readonly value: SceneZone }) {
  const line = useMemo(() => {
    const geometry = new BufferGeometry().setFromPoints(value.corners.map(vector));
    const material = new LineBasicMaterial({ color: value.side === "FIRST" ? "#d99614" : "#47a6a8" });
    return new LineLoop(geometry, material);
  }, [value]);
  useEffect(
    () => () => {
      line.geometry.dispose();
      line.material.dispose();
    },
    [line],
  );
  return <primitive object={line} />;
}

function ContactSurface({ value, emphasized, onSelect, selectionGesture }: {
  readonly value: SceneZone;
  readonly emphasized: boolean;
  readonly onSelect: (selection: SceneSelection) => void;
  readonly selectionGesture: SelectionGestureState;
}) {
  const geometry = useMemo(() => {
    const result = new BufferGeometry().setFromPoints(value.corners.map(vector));
    result.setIndex([0, 1, 2, 0, 2, 3]);
    result.computeVertexNormals();
    return result;
  }, [value]);
  useEffect(() => () => { geometry.dispose(); }, [geometry]);
  if (value.corners.length !== 4) return null;
  return (
    <mesh
      geometry={geometry}
      userData={{ selectionPriority: 2 }}
      onPointerDown={(event) => {
        beginSelectionGesture(
          selectionGesture,
          event.pointerId,
          event.nativeEvent.clientX,
          event.nativeEvent.clientY,
        );
      }}
      onPointerCancel={() => { cancelSelectionGesture(selectionGesture); }}
      onPointerUp={(event) => {
        if (event.intersections.some((intersection) => Number(intersection.object.userData.selectionPriority ?? 0) > 2)) return;
        if (!completeSelectionGesture(
          selectionGesture,
          event.pointerId,
          event.nativeEvent.clientX,
          event.nativeEvent.clientY,
        )) return;
        event.stopPropagation();
        onSelect({ kind: "CONTACT", id: value.patchId });
      }}
    >
      <meshBasicMaterial
        color={emphasized ? "#ff9f1c" : "#f7c846"}
        opacity={emphasized ? 0.68 : 0.46}
        transparent
        side={DoubleSide}
        depthWrite={false}
        polygonOffset
        polygonOffsetFactor={-2}
      />
    </mesh>
  );
}

function CameraControls({
  model,
  view,
  visibility,
  resetNonce,
  onCameraOrientationChange,
  onCameraPositionChange,
  onActionLabelProjectionChange,
}: {
  readonly model: SingleBoltSceneModel;
  readonly view: SceneViewId;
  readonly visibility: SceneVisibility;
  readonly resetNonce: number;
  readonly onCameraOrientationChange: (orientation: CameraOrientation2D) => void;
  readonly onCameraPositionChange: (position: Vec3) => void;
  readonly onActionLabelProjectionChange: (
    projections: readonly ProjectedActionLabel[],
  ) => void;
}) {
  const { camera, gl, invalidate, size } = useThree();
  const fitCenterX = model.fitCenter.x;
  const fitCenterY = model.fitCenter.y;
  const fitCenterZ = model.fitCenter.z;
  const viewportWidth = size.width;
  const viewportHeight = size.height;
  const projectLabels = useCallback(() => {
    const positive = visibility.positiveDirections
      ? projectActionLabels(
          model.positiveArrows,
          model.boundsRadius,
          "POSITIVE",
          camera,
          viewportWidth,
          viewportHeight,
        )
      : [];
    const applied = visibility.appliedDirections && visibility.actionValues
      ? projectActionLabels(
          model.appliedArrows.filter((value) => visibility.zeroActions || !value.isZero),
          model.boundsRadius,
          "APPLIED",
          camera,
          viewportWidth,
          viewportHeight,
        )
      : [];
    onActionLabelProjectionChange([...positive, ...applied]);
  }, [camera, model.appliedArrows, model.boundsRadius, model.positiveArrows, onActionLabelProjectionChange, viewportHeight, viewportWidth, visibility.actionValues, visibility.appliedDirections, visibility.positiveDirections, visibility.zeroActions]);
  const projectLabelsRef = useRef(projectLabels);
  useEffect(() => {
    projectLabelsRef.current = projectLabels;
    projectLabels();
  }, [projectLabels]);
  useEffect(() => {
    const definition = SCENE_VIEWS[view];
    const direction = vector(definition.cameraDirection).normalize();
    const center = new Vector3(fitCenterX, fitCenterY, fitCenterZ);
    const distance = definition.orthographic
      ? model.fitRadius * 3.2
      : calculatePerspectiveDistance(model.fitRadius, 38);
    const clipping = calculateCameraClippingPlanes(distance, model.fitRadius);
    camera.position.copy(center.clone().add(direction.multiplyScalar(distance)));
    camera.up.copy(vector(definition.up));
    setCameraClipping(camera, clipping);
    if ("zoom" in camera) {
      setCameraZoom(
        camera,
        definition.orthographic
          ? calculateOrthographicZoom(Math.min(viewportWidth, viewportHeight), model.fitRadius)
          : 1,
      );
    }
    camera.lookAt(center);
    camera.updateProjectionMatrix();
    onCameraPositionChange({
      x: camera.position.x,
      y: camera.position.y,
      z: camera.position.z,
    });
    const disposeControls = installViewportNavigation({
      cameraQuaternion: camera.quaternion,
      createControls: () => new OrbitControls(camera, gl.domElement),
      invalidate,
      onCameraOrientationChange: (orientation) => {
        onCameraOrientationChange(orientation);
        onCameraPositionChange({
          x: camera.position.x,
          y: camera.position.y,
          z: camera.position.z,
        });
        projectLabelsRef.current();
      },
      target: center,
    });
    return disposeControls;
  }, [camera, fitCenterX, fitCenterY, fitCenterZ, gl.domElement, invalidate, model.fitRadius, onCameraOrientationChange, onCameraPositionChange, resetNonce, view, viewportHeight, viewportWidth]);
  return null;
}

function shouldShowFrame(
  value: SceneFrame,
  visibility: SceneVisibility,
  selection: SceneSelection,
): boolean {
  if (value.kind === "GLOBAL") return visibility.globalAxes;
  if (value.kind === "MEMBER_LOCAL") {
    return (
      visibility.memberAxes === "ALL" ||
      (visibility.memberAxes === "SELECTED" &&
        value.ownerId === (selection.kind === "MEMBER" ? selection.id : "member-a"))
    );
  }
  if (value.kind === "CONNECTOR_LOCAL") return visibility.connectorAxes;
  if (value.kind === "INTERFACE_LOCAL") return visibility.interfaceAxes;
  return value.kind === "BOLT_GROUP_LOCAL" && visibility.boltGroupAxes;
}

function SceneContents({ model, view, visibility, resetNonce, displayMode, selection, onSelect, interfaceHighlight, onCameraOrientationChange, onActionLabelProjectionChange }: EngineeringSceneProps) {
  const axisLength = model.boundsRadius * 0.28;
  const selectionGesture = useMemo(() => createSelectionGestureState(), []);
  const fasteners = useMemo(() => buildFastenerPresentations(model.cylinders), [model.cylinders]);
  const ttMarkerFacingUpdatersRef = useRef(new Map<string, TTMarkerFacingUpdater>());
  const lastCameraPositionRef = useRef<Vec3 | null>(null);
  const registerTTMarkerFacingUpdater = useCallback<RegisterTTMarkerFacingUpdater>(
    (id, updater) => {
      if (updater === null) {
        ttMarkerFacingUpdatersRef.current.delete(id);
        return;
      }
      ttMarkerFacingUpdatersRef.current.set(id, updater);
      if (lastCameraPositionRef.current !== null) updater(lastCameraPositionRef.current);
    },
    [],
  );
  const updateTTMarkerFacing = useCallback((cameraPosition: Vec3) => {
    lastCameraPositionRef.current = cameraPosition;
    for (const updater of ttMarkerFacingUpdatersRef.current.values()) {
      updater(cameraPosition);
    }
  }, []);
  return (
    <>
      <color attach="background" args={["#f4f7fa"]} />
      <ambientLight intensity={1.15} />
      <directionalLight position={[8, -10, 12]} intensity={2.1} />
      {visibility.selectedContactSurface
        ? model.zones
            .filter((value) => value.selectedContact || value.interfaceId === interfaceHighlight?.interfaceId)
            .map((value) => <ContactSurface key={`contact:${value.id}`} value={value} emphasized={value.interfaceId === interfaceHighlight?.interfaceId} onSelect={onSelect} selectionGesture={selectionGesture} />)
        : null}
      {visibility.physicalGeometry
        ? model.boxes
            .filter((value) => visibility.deferredGeometry || !value.deferred)
            .map((value) => (
              <BoxPrimitive
                key={value.id}
                value={value}
                displayMode={displayMode}
                selected={selection.kind === "MEMBER" && selection.id === value.ownerId}
                onSelect={onSelect}
                selectionGesture={selectionGesture}
              />
            ))
        : null}
      {visibility.physicalGeometry
        ? model.meshes.map((value) => (
            <TriangleMeshPrimitive
              key={value.id}
              value={value}
              displayMode={displayMode}
              selected={selection.kind === "MEMBER" && selection.id === value.ownerId}
              onSelect={onSelect}
              selectionGesture={selectionGesture}
            />
          ))
        : null}
      {visibility.boltAndHoles ? fasteners.map((value) => (
        <FastenerPrimitive
          key={value.id}
          value={value}
          selected={(selection.kind === "BOLT" && selection.id === value.ownerBoltId) || value.shank.interfaceId === interfaceHighlight?.interfaceId}
          onSelect={onSelect}
          selectionGesture={selectionGesture}
        />
      )) : null}
      {visibility.boltAndHoles ? model.cylinders.map((value) =>
        value.kind === "HOLE" && visibility.boltAxis ? (
          <CylinderPrimitive
            key={value.id}
            value={value}
            selected={(selection.kind === "BOLT" && selection.id === value.ownerBoltId) || value.interfaceId === interfaceHighlight?.interfaceId}
            onSelect={onSelect}
            selectionGesture={selectionGesture}
          />
        ) : null,
      ) : null}
      {visibility.interfaceZones
        ? model.zones.map((value) => <ZoneOutline key={value.id} value={value} />)
        : null}
      {model.frames.filter((value) => shouldShowFrame(value, visibility, selection)).map((value) => (
        <FrameAxes key={value.id} value={value} length={axisLength} />
      ))}
      {visibility.materialAxes
        ? model.materialAxes.map((value) => (
            <RegionEmbeddedMaterialAxes
              key={value.id}
              value={value}
              displayMode={displayMode}
              registerFacingUpdater={registerTTMarkerFacingUpdater}
            />
          ))
        : null}
      {visibility.referencePoints
        ? model.markers.map((value) => (
            <Marker key={value.id} value={value} radius={model.boundsRadius * 0.025} />
          ))
        : null}
      {visibility.positiveDirections
        ? model.positiveArrows.map((value) => (
            <ActionArrow key={`positive:${value.id}`} value={value} radius={model.boundsRadius} positive />
          ))
        : null}
      {visibility.appliedDirections
        ? model.appliedArrows
            .filter((value) => visibility.zeroActions || !value.isZero)
            .map((value) => (
              <ActionArrow key={`applied:${value.id}`} value={value} radius={model.boundsRadius} positive={false} />
            ))
        : null}
      {visibility.appliedDirections
        ? model.connectionDemandArrows.map((value) => (
            <ActionArrow key={`connection-demand:${value.id}`} value={value} radius={model.boundsRadius} positive={false} />
          ))
        : null}
      {visibility.perBoltDemands
        ? model.perBoltDemandArrows.map((value) => (
            <ActionArrow key={`per-bolt-demand:${value.id}`} value={value} radius={model.boundsRadius} positive={false} />
          ))
        : null}
      <CameraControls
        model={model}
        view={view}
        visibility={visibility}
        resetNonce={resetNonce}
        onCameraOrientationChange={onCameraOrientationChange}
        onCameraPositionChange={updateTTMarkerFacing}
        onActionLabelProjectionChange={onActionLabelProjectionChange}
      />
    </>
  );
}

export default function EngineeringScene(props: EngineeringSceneProps) {
  return (
    <Canvas
      key={props.view}
      orthographic={SCENE_VIEWS[props.view].orthographic}
      frameloop="demand"
      dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: false }}
      camera={{ fov: 38, zoom: 1 }}
      data-engine="react-three-fiber"
    >
      <SceneContents {...props} />
    </Canvas>
  );
}
