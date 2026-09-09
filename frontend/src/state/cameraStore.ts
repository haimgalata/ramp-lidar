import { create } from "zustand";

export interface CameraPose {
  position: [number, number, number];
  target: [number, number, number];
  zoom: number;
  // Monotonically increasing so subscribers can tell "this is a new pose" even
  // if the numeric values happen to repeat.
  version: number;
}

interface CameraState {
  pose: CameraPose | null;
  publish: (pose: Omit<CameraPose, "version">) => void;
}

/** Shared camera pose used by the Parallel Comparison viewers when
 * "Sync Cameras" is ON. Whichever viewer the user is dragging publishes its
 * pose here; every other viewer (see Viewer3D's `syncPose` prop) copies it. */
export const useCameraStore = create<CameraState>((set, get) => ({
  pose: null,
  publish: (pose) => set({ pose: { ...pose, version: (get().pose?.version ?? 0) + 1 } }),
}));
