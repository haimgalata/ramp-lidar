import { OrbitControls } from "@react-three/drei";
import { Canvas, type ThreeEvent, useThree } from "@react-three/fiber";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { useCameraStore } from "../state/cameraStore";
import type { PointCloudGeometryData } from "../hooks/usePointCloudGeometry";

export interface Viewer3DPoint {
  x: number;
  y: number;
  z: number;
  color?: [number, number, number];
}

interface RoiBox {
  min: [number, number, number];
  max: [number, number, number];
}

interface Viewer3DProps {
  geometry: PointCloudGeometryData;
  label?: string;
  roi?: RoiBox | null;
  showRoiBox?: boolean;
  showBoundingBox?: boolean;
  showAxes?: boolean;
  onPointClick?: (point: Viewer3DPoint) => void;
  syncCameras?: boolean;
  pointSize?: number;
  height?: number | string;
}

/** One point-cloud panel: Canvas + points + axes/bbox/ROI helpers + orbit
 * controls, optionally synced with other Viewer3D instances via cameraStore. */
export default function Viewer3D({
  geometry,
  label,
  roi,
  showRoiBox = true,
  showBoundingBox = true,
  showAxes = true,
  onPointClick,
  syncCameras = false,
  pointSize,
  height = 420,
}: Viewer3DProps) {
  const controlsRef = useRef<any>(null);
  const [resetTick, setResetTick] = useState(0);

  // Pick a sensible default camera distance / picking threshold from bounds.
  const diag = geometry.bounds
    ? Math.hypot(
        geometry.bounds.max[0] - geometry.bounds.min[0],
        geometry.bounds.max[1] - geometry.bounds.min[1],
        geometry.bounds.max[2] - geometry.bounds.min[2]
      )
    : 2;
  const center: [number, number, number] = geometry.bounds
    ? [
        (geometry.bounds.min[0] + geometry.bounds.max[0]) / 2,
        (geometry.bounds.min[1] + geometry.bounds.max[1]) / 2,
        (geometry.bounds.min[2] + geometry.bounds.max[2]) / 2,
      ]
    : [0, 0, 0];
  const camDistance = Math.max(diag * 1.5, 0.5);
  const resolvedPointSize = pointSize ?? Math.max(diag / 400, 0.002);
  const pickThreshold = Math.max(diag / 250, 0.003);

  return (
    <div style={{ position: "relative", width: "100%", height }}>
      {label && (
        <div className="viewer-label">
          {label} <span className="viewer-count">{geometry.count.toLocaleString()} pts</span>
        </div>
      )}
      <button
        className="viewer-reset-btn"
        title="Reset camera"
        onClick={() => setResetTick((t) => t + 1)}
      >
        ⤾ Reset
      </button>
      <Canvas
        key={resetTick /* remounting is the simplest reliable "reset camera" */}
        camera={{ position: [center[0] + camDistance, center[1] + camDistance, center[2] + camDistance], fov: 50, near: 0.001, far: camDistance * 100 }}
        onCreated={({ raycaster }) => {
          raycaster.params.Points = { threshold: pickThreshold };
        }}
      >
        <ambientLight intensity={1.0} />
        <directionalLight position={[10, 10, 10]} intensity={0.4} />

        {geometry.count > 0 && (
          <PointCloudLayer geometry={geometry} pointSize={resolvedPointSize} onPointClick={onPointClick} />
        )}

        {showAxes && <axesHelper args={[Math.max(diag * 0.6, 0.2)]} />}

        {showBoundingBox && geometry.bounds && <BoundsBox bounds={geometry.bounds} color="#5b7a99" />}

        {showRoiBox && roi && <BoundsBox bounds={roi} color="#f2a93b" dashed />}

        <OrbitControls
          ref={controlsRef}
          makeDefault
          target={center}
          minDistance={diag * 0.01 || 0.01}
          maxDistance={diag * 20 || 50}
        />

        {syncCameras && <CameraSync controlsRef={controlsRef} />}
      </Canvas>
    </div>
  );
}

function PointCloudLayer({
  geometry,
  pointSize,
  onPointClick,
}: {
  geometry: PointCloudGeometryData;
  pointSize: number;
  onPointClick?: (point: Viewer3DPoint) => void;
}) {
  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    if (!onPointClick || e.index === undefined) return;
    const i = e.index;
    // Only report a color if it came from real per-point RGB data -- not the
    // uniform fallback tint used purely for rendering clouds without color.
    const color = geometry.hasRealColor && geometry.colors
      ? ([geometry.colors[i * 3], geometry.colors[i * 3 + 1], geometry.colors[i * 3 + 2]] as [number, number, number])
      : undefined;
    onPointClick({
      x: geometry.positions[i * 3],
      y: geometry.positions[i * 3 + 1],
      z: geometry.positions[i * 3 + 2],
      color,
    });
  };

  return (
    <points onClick={handleClick}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[geometry.positions, 3]} />
        {geometry.colors && <bufferAttribute attach="attributes-color" args={[geometry.colors, 3]} />}
      </bufferGeometry>
      <pointsMaterial size={pointSize} vertexColors={!!geometry.colors} sizeAttenuation />
    </points>
  );
}

function BoundsBox({
  bounds,
  color,
  dashed = false,
}: {
  bounds: { min: [number, number, number]; max: [number, number, number] };
  color: string;
  dashed?: boolean;
}) {
  const box = new THREE.Box3(new THREE.Vector3(...bounds.min), new THREE.Vector3(...bounds.max));
  const size = new THREE.Vector3();
  const center = new THREE.Vector3();
  box.getSize(size);
  box.getCenter(center);
  return (
    <lineSegments position={center.toArray()}>
      <edgesGeometry args={[new THREE.BoxGeometry(size.x || 0.001, size.y || 0.001, size.z || 0.001)]} />
      <lineBasicMaterial color={color} linewidth={1} transparent opacity={dashed ? 0.9 : 0.6} />
    </lineSegments>
  );
}

/** Publishes this viewer's camera pose to the shared store on user
 * interaction, and applies any incoming pose from other synced viewers.
 * A guard flag prevents the applied update from re-publishing (feedback loop). */
function CameraSync({ controlsRef }: { controlsRef: React.MutableRefObject<any> }) {
  const { camera } = useThree();
  const publish = useCameraStore((s) => s.publish);
  const pose = useCameraStore((s) => s.pose);
  const applyingRemote = useRef(false);
  const lastAppliedVersion = useRef(0);

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls) return;
    const handleChange = () => {
      if (applyingRemote.current) return;
      publish({
        position: camera.position.toArray() as [number, number, number],
        target: controls.target.toArray() as [number, number, number],
        zoom: camera.zoom,
      });
    };
    controls.addEventListener("change", handleChange);
    return () => controls.removeEventListener("change", handleChange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [controlsRef.current]);

  useEffect(() => {
    if (!pose || pose.version === lastAppliedVersion.current) return;
    const controls = controlsRef.current;
    if (!controls) return;
    lastAppliedVersion.current = pose.version;
    applyingRemote.current = true;
    camera.position.set(...pose.position);
    camera.zoom = pose.zoom;
    camera.updateProjectionMatrix();
    controls.target.set(...pose.target);
    controls.update();
    // Release the guard after this synchronous update cycle.
    requestAnimationFrame(() => {
      applyingRemote.current = false;
    });
  }, [pose, camera, controlsRef]);

  return null;
}
