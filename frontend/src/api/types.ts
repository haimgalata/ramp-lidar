// Mirrors backend/app/models/schemas.py. Keep in sync manually -- this is a
// small enough surface that a codegen step would be more overhead than value
// for a one-day prototype.

export interface BoundingBox {
  min: [number, number, number];
  max: [number, number, number];
}

export interface CloudInfo {
  file_name: string | null;
  file_format: string | null;
  point_count: number;
  min_x: number; max_x: number;
  min_y: number; max_y: number;
  min_z: number; max_z: number;
  width: number;
  length: number;
  height_range: number;
  bounding_box: BoundingBox;
  has_color: boolean;
  has_intensity: boolean;
  has_normals: boolean;
  point_density: number | null;
}

export interface Experiment {
  id: string;
  name: string;
  created_at: string;
  has_cloud: boolean;
  cloud_info: CloudInfo | null;
  ground_truth_slope_deg: number | null;
  roi: BoundingBox | null;
  result_ids: string[];
}

export interface PointCloudPoints {
  positions: number[];
  colors: number[] | null;
  full_point_count: number;
  sent_point_count: number;
  subsampled: boolean;
}

export interface ParameterSpec {
  key: string;
  label: string;
  type: "float" | "int";
  default: number;
  min: number;
  max: number;
  step: number;
}

export interface AlgorithmDef {
  id: string;
  name: string;
  description: string;
  parameters: ParameterSpec[];
}

export interface AlgorithmStep {
  algorithm_id: string;
  parameters: Record<string, number>;
}

export interface PlaneFitParams {
  distance_threshold: number;
  num_iterations: number;
  min_inliers: number;
}

export interface ProcessingResult {
  id: string;
  experiment_id: string;
  parent_result_id: string | null;
  name: string;
  source_type: "original" | "roi" | "result";
  algorithm_name: string | null;
  algorithm_parameters: Record<string, number>;
  pipeline_steps: AlgorithmStep[];
  point_count: number;
  calculated_slope: number | null;
  plane_a: number | null;
  plane_b: number | null;
  plane_c: number | null;
  plane_d: number | null;
  plane_normal: [number, number, number] | null;
  ground_truth_slope: number | null;
  slope_error: number | null;
  plane_rmse: number | null;
  mean_point_to_plane_distance: number | null;
  inlier_count: number | null;
  outlier_count: number | null;
  points_removed_pct: number | null;
  improvement_pct: number | null;
  processing_time_ms: number | null;
  created_at: string;
}

export interface DiffPayload {
  positions: number[];
  colors: number[];
  distances_mm: number[];
  point_count: number;
  mean_distance_mm: number;
  max_distance_mm: number;
  min_mm: number;
  max_mm: number;
  bin_counts: { label: string; min_mm: number; max_mm: number | null; count: number }[];
}
