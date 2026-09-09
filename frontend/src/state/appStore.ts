import { create } from "zustand";
import type { AlgorithmDef, AlgorithmStep, Experiment, ProcessingResult } from "../api/types";

export type Tab = "viewer" | "parallel" | "pipeline" | "results";

export interface PickedPoint {
  x: number;
  y: number;
  z: number;
  color?: [number, number, number];
  sourceLabel: string;
}

interface AppState {
  experiment: Experiment | null;
  algorithms: AlgorithmDef[];
  results: ProcessingResult[];
  activeTab: Tab;

  // Viewer / inspection
  pickedPoint: PickedPoint | null;
  roiDraft: { min: [number, number, number]; max: [number, number, number] } | null;
  showRoiBox: boolean;
  showBoundingBox: boolean;
  showAxes: boolean;

  // Pipeline builder (Mode A)
  pipelineSteps: AlgorithmStep[];
  // Parallel comparison (Mode B)
  parallelStepIds: string[]; // algorithm ids selected for independent parallel runs
  parallelAlgoParams: Record<string, Record<string, number>>;

  // Which result each of the multi-viewer slots is showing (parallel tab)
  parallelViewerResultIds: string[];
  syncCameras: boolean;

  // Results table
  sortKey: keyof ProcessingResult | null;
  sortDir: "asc" | "desc";
  selectedResultIdForCompare: string | null;

  setExperiment: (e: Experiment | null) => void;
  setAlgorithms: (a: AlgorithmDef[]) => void;
  setResults: (r: ProcessingResult[]) => void;
  upsertResult: (r: ProcessingResult) => void;
  removeResult: (id: string) => void;
  setActiveTab: (t: Tab) => void;
  setPickedPoint: (p: PickedPoint | null) => void;
  setRoiDraft: (roi: AppState["roiDraft"]) => void;
  toggleShowRoiBox: () => void;
  toggleShowBoundingBox: () => void;
  toggleShowAxes: () => void;
  addPipelineStep: (step: AlgorithmStep) => void;
  removePipelineStep: (index: number) => void;
  movePipelineStep: (index: number, direction: -1 | 1) => void;
  updatePipelineStepParams: (index: number, params: Record<string, number>) => void;
  clearPipeline: () => void;
  toggleParallelAlgo: (algorithmId: string) => void;
  setParallelAlgoParams: (algorithmId: string, params: Record<string, number>) => void;
  setParallelViewerResultIds: (ids: string[]) => void;
  toggleSyncCameras: () => void;
  setSort: (key: keyof ProcessingResult) => void;
  setSelectedResultIdForCompare: (id: string | null) => void;
  reset: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  experiment: null,
  algorithms: [],
  results: [],
  activeTab: "viewer",

  pickedPoint: null,
  roiDraft: null,
  showRoiBox: true,
  showBoundingBox: true,
  showAxes: true,

  pipelineSteps: [],
  parallelStepIds: [],
  parallelAlgoParams: {},

  parallelViewerResultIds: [],
  syncCameras: true,

  sortKey: "slope_error",
  sortDir: "asc",
  selectedResultIdForCompare: null,

  setExperiment: (e) => set({ experiment: e }),
  setAlgorithms: (a) => set({ algorithms: a }),
  setResults: (r) => set({ results: r }),
  upsertResult: (r) =>
    set((s) => ({
      results: [...s.results.filter((x) => x.id !== r.id), r],
    })),
  removeResult: (id) => set((s) => ({ results: s.results.filter((r) => r.id !== id) })),
  setActiveTab: (t) => set({ activeTab: t }),
  setPickedPoint: (p) => set({ pickedPoint: p }),
  setRoiDraft: (roi) => set({ roiDraft: roi }),
  toggleShowRoiBox: () => set((s) => ({ showRoiBox: !s.showRoiBox })),
  toggleShowBoundingBox: () => set((s) => ({ showBoundingBox: !s.showBoundingBox })),
  toggleShowAxes: () => set((s) => ({ showAxes: !s.showAxes })),

  addPipelineStep: (step) => set((s) => ({ pipelineSteps: [...s.pipelineSteps, step] })),
  removePipelineStep: (index) =>
    set((s) => ({ pipelineSteps: s.pipelineSteps.filter((_, i) => i !== index) })),
  movePipelineStep: (index, direction) =>
    set((s) => {
      const steps = [...s.pipelineSteps];
      const target = index + direction;
      if (target < 0 || target >= steps.length) return {};
      [steps[index], steps[target]] = [steps[target], steps[index]];
      return { pipelineSteps: steps };
    }),
  updatePipelineStepParams: (index, params) =>
    set((s) => {
      const steps = [...s.pipelineSteps];
      steps[index] = { ...steps[index], parameters: params };
      return { pipelineSteps: steps };
    }),
  clearPipeline: () => set({ pipelineSteps: [] }),

  toggleParallelAlgo: (algorithmId) =>
    set((s) => ({
      parallelStepIds: s.parallelStepIds.includes(algorithmId)
        ? s.parallelStepIds.filter((id) => id !== algorithmId)
        : [...s.parallelStepIds, algorithmId],
    })),
  setParallelAlgoParams: (algorithmId, params) =>
    set((s) => ({ parallelAlgoParams: { ...s.parallelAlgoParams, [algorithmId]: params } })),
  setParallelViewerResultIds: (ids) => set({ parallelViewerResultIds: ids }),
  toggleSyncCameras: () => set((s) => ({ syncCameras: !s.syncCameras })),

  setSort: (key) =>
    set((s) => ({
      sortKey: key,
      sortDir: s.sortKey === key && s.sortDir === "asc" ? "desc" : "asc",
    })),
  setSelectedResultIdForCompare: (id) => set({ selectedResultIdForCompare: id }),

  reset: () =>
    set({
      experiment: null,
      results: [],
      pickedPoint: null,
      roiDraft: null,
      pipelineSteps: [],
      parallelStepIds: [],
      parallelAlgoParams: {},
      parallelViewerResultIds: [],
      selectedResultIdForCompare: null,
    }),
}));
