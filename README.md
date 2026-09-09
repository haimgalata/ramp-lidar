# Ramp Point Cloud Analysis

A local web application for uploading, visualizing, processing, and comparing
LiDAR point clouds of a **ramp** -- calculate the ramp slope via RANSAC plane
fitting, compare it against a manually-measured Ground Truth, run cleanup
algorithms individually or as a pipeline, and see which processing approach
gets closest to the truth.

This is scoped specifically to the ramp-slope use case (not a generic point
cloud platform).

---

## Architecture

```
ramp-lidar/
  backend/     FastAPI + Open3D + NumPy -- all point cloud math and in-memory state
  frontend/    React + TypeScript + React Three Fiber -- 3D viewer and UI
```

**Key design decision -- no files after every algorithm run.** The pipeline is:

```
Uploaded File --(parsed once)--> Open3D PointCloud (original, immutable, in RAM)
             --(algorithm/pipeline run)--> ProcessingResult (in RAM: cloud + metrics)
             --(user clicks Export)--> real PLY/PCD file on disk
```

The backend is a single in-memory `ExperimentStore` (see
`backend/app/core/store.py`) -- no database, no implicit disk writes. The
*only* place a file is ever written is `POST /results/{id}/export`.

**Visualization vs. processing resolution.** All algorithms (SOR, RANSAC,
voxel downsampling, ...) always run on the full-resolution cloud on the
backend. The frontend viewer receives a capped, randomly-subsampled point set
(`VIZ_MAX_POINTS`, default 150k) purely for smooth rendering -- this cap never
affects any calculation.

**Why React Three Fiber over Potree.** The project only ever shows one
uploaded ramp at a time (plus a handful of derived results), needs custom
per-point coloring (difference heatmaps, ROI highlighting), point picking,
and several simultaneously-rendered, camera-synced viewers. R3F gives direct
control over all of that with plain three.js primitives, with far less
integration work than wiring Potree's tiled-LOD viewer (built for
massive/street-scale scans) into a custom multi-viewer comparison UI.

---

## Backend

```
backend/app/
  main.py              FastAPI app, CORS, router wiring
  config.py            env-driven settings (viz point cap, upload limit)
  core/store.py         in-memory Experiment/Result store (the RAM boundary)
  algorithms/           one module per algorithm, common Algorithm interface
    base.py             Algorithm / AlgorithmContext / AlgorithmOutput
    statistical_outlier.py, radius_outlier.py, voxel_downsample.py,
    ransac_plane.py, normal_estimation.py, smoothing.py
    registry.py          id -> Algorithm lookup used everywhere
  services/
    point_cloud_io.py    load/save PLY & PCD, ROI crop, viz payload builder
    slope.py             RANSAC plane fit -> ramp slope (heavily commented)
    metrics.py           slope error, improvement %, points-removed %
    pipeline.py          single / pipeline / parallel run orchestration
    difference.py        cloud-to-cloud distance heatmap
    result_view.py        ResultRecord -> API schema (ground-truth-aware)
  api/                  experiments.py, algorithms.py, processing.py, results.py
  models/schemas.py     Pydantic request/response models
tests/                  pytest unit tests for slope math, metrics, algorithms,
                         plus a full end-to-end API smoke test
```

### API summary

| Endpoint | Purpose |
|---|---|
| `POST /experiments` | create an experiment ("Ramp Test 001") |
| `POST /experiments/{id}/upload` | upload a PLY/PCD, parse it once |
| `GET /experiments/{id}` | experiment + cloud info + ROI + ground truth |
| `GET /experiments/{id}/points` | subsampled geometry for the viewer |
| `POST /experiments/{id}/roi` / `DELETE .../roi` | set/clear the ROI bounding box |
| `POST /experiments/{id}/ground-truth` | set the manually measured slope |
| `POST /experiments/{id}/analyze-slope` | RANSAC slope on Original/ROI (the baseline) |
| `GET /algorithms` | algorithm library (id, description, parameter specs) |
| `POST /processing/single` | run one algorithm on Original/ROI/a prior result |
| `POST /processing/pipeline` | run an ordered chain of algorithms (Mode A) |
| `POST /processing/parallel` | run several algorithms independently (Mode B) |
| `GET /results/{id}` / `.../points` | result metadata / viewer geometry |
| `GET /results/{id}/diff` | cloud-to-cloud distance heatmap vs. another cloud |
| `POST /results/{id}/export` | **the only file-writing endpoint** (PLY/PCD) |
| `DELETE /results/{id}` | free a result from memory |
| `GET /experiments/{id}/results` | full comparison table |
| `GET /experiments/{id}/results/export` | comparison table as CSV/JSON |

Interactive docs at `http://localhost:8000/docs` once the server is running.

### Run it

Requires **Python 3.10 or 3.11** (Open3D 0.18 does not ship wheels for 3.12+).

```bash
cd backend
py -3.10 -m venv .venv          # or: python3.10 -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Copy `.env.example` to `.env` to override defaults (viz point cap, upload
size limit, CORS origin).

### Run the tests

```bash
cd backend
.venv\Scripts\python -m pytest -v
```

22 tests cover: slope/plane geometry (including a synthetic tilted-ramp
recovery test across several known angles), every algorithm module, the
metrics functions (including the spec's worked 81.25% improvement example and
the divide-by-zero guard), and a full end-to-end API smoke test exercising
the entire spec workflow (upload -> ROI -> ground truth -> slope -> single /
pipeline / parallel processing -> results table -> diff -> export).

---

## Frontend

```
frontend/src/
  api/            typed client (client.ts) + types.ts mirroring the backend schemas
  state/          appStore.ts (zustand: experiment/results/pipeline/parallel state)
                  cameraStore.ts (shared camera pose for synced multi-viewers)
  hooks/          usePointCloudGeometry.ts (API payload -> typed arrays for three.js)
  components/     Viewer3D, AlgorithmLibrary, ROIPanel, SlopePanel, GroundTruthPanel,
                  PipelineBuilder, ParallelViewers, BeforeAfterViewer, DiffViewer,
                  ResultsTable, Leaderboard, CloudInfoPanel, PointInspector, TopBar, Tabs
  App.tsx         layout: top bar, algorithm library sidebar, tabbed center, info sidebar
```

### Run it

Requires Node 18+.

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Copy `.env.example` to `.env` to point at a
non-default backend URL.

### UI layout

- **Top bar** -- experiment name, upload, reset results, new experiment.
- **Left sidebar** -- Algorithm Library: every algorithm's parameters plus
  "Run Now", "+ Pipeline", "+ Parallel Set".
- **Center** -- tabs:
  - **Viewer** -- single 3D viewer (rotate/zoom/pan/reset, axes, bounding
    box, ROI box), point picking, ROI editor and slope analysis in the right
    sidebar.
  - **Parallel Compare** -- Mode B: run selected algorithms independently on
    the same source cloud, view all results in synced-camera viewers side by
    side.
  - **Pipeline** -- Mode A: build/reorder/run a sequential algorithm chain,
    then a Before/After (side-by-side or overlay) view of the final result.
  - **Results** -- the comparison table (sortable), the leaderboard, and the
    difference (cloud-to-cloud distance) heatmap viewer.
- **Right sidebar** -- cloud info, point inspector, ground truth entry (and,
  on the Viewer tab, the ROI and slope-analysis panels).

---

## Notes / deliberate simplifications

- **ROI** is an axis-aligned bounding box (numeric min/max per axis, with
  live visual feedback in the viewer) rather than a free-form lasso --
  reliable and fast to use, as the spec allows.
- **Intensity** is read (via Open3D's tensor point cloud reader) and shown
  for the original/ROI cloud, but is not propagated through Voxel
  Downsampling, since voxelization merges points and there is no 1:1 index
  mapping to carry a per-point scalar through. This is called out in
  `voxel_downsample.py`.
- **Smoothing** is a simple k-nearest-neighbor centroid average (not a full
  Moving-Least-Squares reconstruction) -- fast, easy to reason about, good
  enough to demonstrate the effect on slope accuracy.
- The in-memory store is a single process-wide dict -- perfectly fine for a
  local single-user prototype; swapping in Redis/SQLite would only touch
  `core/store.py`.

---

## Try it immediately with sample data

`sample_data/generate_sample_ramp.py` generates a synthetic ~7° ramp (with a
side wall, a railing, and noise/outliers so ROI selection and outlier removal
have something to do) and writes `ramp_sample.ply`:

```bash
cd sample_data
../backend/.venv/Scripts/python generate_sample_ramp.py
```

Upload the resulting file, set ROI to roughly `X[0,3] Y[0,1.15] Z[-1,1.2]`
(printed by the script), set Ground Truth to `7.00`, and calculate slope.

## Docker (optional, untested in this session)

`docker-compose.yml` + per-service `Dockerfile`s are included per the spec's
"if useful" suggestion, but the plain `uvicorn` / `npm run dev` workflow above
is the verified, fast path -- it's what this whole app was built and tested
against. The Docker images were not built/run here (Open3D's image is large
and slow to build); treat them as a starting point, not a validated path.
