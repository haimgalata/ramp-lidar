import type {
  AlgorithmDef,
  AlgorithmStep,
  DiffPayload,
  Experiment,
  PlaneFitParams,
  PointCloudPoints,
  ProcessingResult,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: options.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore parse failure, keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json();
}

export const api = {
  // Experiments -------------------------------------------------------
  createExperiment: (name: string) =>
    request<Experiment>("/experiments", { method: "POST", body: JSON.stringify({ name }) }),

  getExperiment: (id: string) => request<Experiment>(`/experiments/${id}`),

  deleteExperiment: (id: string) => request<{ deleted: boolean }>(`/experiments/${id}`, { method: "DELETE" }),

  resetExperiment: (id: string) => request<Experiment>(`/experiments/${id}/reset`, { method: "POST" }),

  uploadPointCloud: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Experiment>(`/experiments/${id}/upload`, { method: "POST", body: form });
  },

  getExperimentPoints: (id: string, source: "original" | "roi", maxPoints?: number) => {
    const qs = new URLSearchParams({ source });
    if (maxPoints) qs.set("max_points", String(maxPoints));
    return request<PointCloudPoints>(`/experiments/${id}/points?${qs.toString()}`);
  },

  setRoi: (id: string, min: number[], max: number[]) =>
    request<Experiment>(`/experiments/${id}/roi`, { method: "POST", body: JSON.stringify({ min, max }) }),

  clearRoi: (id: string) => request<Experiment>(`/experiments/${id}/roi`, { method: "DELETE" }),

  setGroundTruth: (id: string, slopeDeg: number) =>
    request<Experiment>(`/experiments/${id}/ground-truth`, {
      method: "POST",
      body: JSON.stringify({ slope_deg: slopeDeg }),
    }),

  analyzeSlope: (id: string, source: "original" | "roi", params: PlaneFitParams) =>
    request<ProcessingResult>(`/experiments/${id}/analyze-slope`, {
      method: "POST",
      body: JSON.stringify({ source, params }),
    }),

  listResults: (id: string) => request<ProcessingResult[]>(`/experiments/${id}/results`),

  exportResultsTable: (id: string, format: "csv" | "json") => {
    window.open(`${BASE_URL}/experiments/${id}/results/export?format=${format}`, "_blank");
  },

  // Algorithms ----------------------------------------------------------
  listAlgorithms: () => request<AlgorithmDef[]>("/algorithms"),

  // Processing ------------------------------------------------------------
  runSingle: (params: {
    experiment_id: string;
    source: "original" | "roi";
    source_result_id?: string | null;
    algorithm_id: string;
    parameters: Record<string, number>;
    name?: string;
  }) => request<ProcessingResult>("/processing/single", { method: "POST", body: JSON.stringify(params) }),

  runPipeline: (params: {
    experiment_id: string;
    source: "original" | "roi";
    steps: AlgorithmStep[];
    name?: string;
  }) => request<ProcessingResult>("/processing/pipeline", { method: "POST", body: JSON.stringify(params) }),

  runParallel: (params: { experiment_id: string; source: "original" | "roi"; algorithms: AlgorithmStep[] }) =>
    request<ProcessingResult[]>("/processing/parallel", { method: "POST", body: JSON.stringify(params) }),

  // Results ------------------------------------------------------------
  getResult: (id: string) => request<ProcessingResult>(`/results/${id}`),

  getResultPoints: (id: string, maxPoints?: number) => {
    const qs = maxPoints ? `?max_points=${maxPoints}` : "";
    return request<PointCloudPoints>(`/results/${id}/points${qs}`);
  },

  getResultDiff: (id: string, otherResultId: string | null, minMm: number, maxMm: number) => {
    const qs = new URLSearchParams({ min_mm: String(minMm), max_mm: String(maxMm) });
    if (otherResultId) qs.set("other_result_id", otherResultId);
    return request<DiffPayload>(`/results/${id}/diff?${qs.toString()}`);
  },

  exportResult: (id: string, format: "ply" | "pcd", downloadName: string) => {
    return fetch(`${BASE_URL}/results/${id}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format }),
    })
      .then((res) => {
        if (!res.ok) throw new ApiError(res.status, res.statusText);
        return res.blob();
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${downloadName}.${format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      });
  },

  deleteResult: (id: string) => request<{ deleted: boolean }>(`/results/${id}`, { method: "DELETE" }),
};

export { ApiError };
