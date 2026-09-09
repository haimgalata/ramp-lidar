import { useEffect, useState } from "react";
import { api } from "./api/client";
import type { PointCloudPoints } from "./api/types";
import AlgorithmLibrary from "./components/AlgorithmLibrary";
import BeforeAfterViewer from "./components/BeforeAfterViewer";
import CloudInfoPanel from "./components/CloudInfoPanel";
import DiffViewer from "./components/DiffViewer";
import GroundTruthPanel from "./components/GroundTruthPanel";
import Leaderboard from "./components/Leaderboard";
import ParallelViewers from "./components/ParallelViewers";
import PipelineBuilder from "./components/PipelineBuilder";
import PointInspector from "./components/PointInspector";
import ResultsTable from "./components/ResultsTable";
import ROIPanel from "./components/ROIPanel";
import SlopePanel from "./components/SlopePanel";
import Tabs from "./components/Tabs";
import TopBar from "./components/TopBar";
import Viewer3D, { type Viewer3DPoint } from "./components/Viewer3D";
import { usePointCloudGeometry } from "./hooks/usePointCloudGeometry";
import { useAppStore } from "./state/appStore";

export default function App() {
  const experiment = useAppStore((s) => s.experiment);
  const setExperiment = useAppStore((s) => s.setExperiment);
  const setAlgorithms = useAppStore((s) => s.setAlgorithms);
  const setResults = useAppStore((s) => s.setResults);
  const activeTab = useAppStore((s) => s.activeTab);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const pickedPoint = useAppStore((s) => s.pickedPoint);
  const setPickedPoint = useAppStore((s) => s.setPickedPoint);
  const roiDraft = useAppStore((s) => s.roiDraft);
  const showRoiBox = useAppStore((s) => s.showRoiBox);
  const showBoundingBox = useAppStore((s) => s.showBoundingBox);
  const showAxes = useAppStore((s) => s.showAxes);
  const results = useAppStore((s) => s.results);

  const [source, setSource] = useState<"original" | "roi">("original");
  const [viewerPoints, setViewerPoints] = useState<PointCloudPoints | null>(null);
  const [pipelineResultId, setPipelineResultId] = useState<string | null>(null);

  // Load algorithm library once.
  useEffect(() => {
    api.listAlgorithms().then(setAlgorithms);
  }, [setAlgorithms]);

  // Whenever an experiment appears/changes, refresh its result list.
  useEffect(() => {
    if (!experiment) return;
    api.listResults(experiment.id).then(setResults);
  }, [experiment?.id, experiment?.result_ids.length, setResults]);

  // Default the processing source to ROI once one has been set.
  useEffect(() => {
    if (experiment?.roi) setSource("roi");
  }, [experiment?.roi]);

  // Load the main viewer's point cloud whenever the experiment or source changes.
  useEffect(() => {
    if (!experiment?.has_cloud) {
      setViewerPoints(null);
      return;
    }
    if (source === "roi" && !experiment.roi) {
      setViewerPoints(null);
      return;
    }
    let cancelled = false;
    api.getExperimentPoints(experiment.id, source).then((p) => !cancelled && setViewerPoints(p));
    return () => {
      cancelled = true;
    };
  }, [experiment?.id, experiment?.has_cloud, experiment?.roi, source]);

  const geometry = usePointCloudGeometry(viewerPoints);

  const handlePointClick = (p: Viewer3DPoint) => {
    setPickedPoint({ ...p, sourceLabel: source === "roi" ? "ROI" : "Original" });
  };

  const baseline = results.find((r) => r.algorithm_name === null);

  return (
    <div className="app-shell">
      <TopBar />
      {!experiment?.has_cloud ? (
        <div className="empty-state">
          <h2>Upload a ramp point cloud to begin</h2>
          <p className="muted">Supported formats: PLY, PCD</p>
        </div>
      ) : (
        <div className="app-body">
          <aside className="sidebar-left">
            <AlgorithmLibrary source={source} />
          </aside>

          <main className="center-area">
            <div className="center-toolbar">
              <Tabs active={activeTab} onChange={setActiveTab} />
              <div className="source-toggle">
                <span>Process from:</span>
                <button className={source === "original" ? "toggle-on" : ""} onClick={() => setSource("original")}>
                  Original
                </button>
                <button
                  className={source === "roi" ? "toggle-on" : ""}
                  disabled={!experiment.roi}
                  onClick={() => setSource("roi")}
                  title={!experiment.roi ? "Set an ROI first" : ""}
                >
                  ROI
                </button>
              </div>
            </div>

            {activeTab === "viewer" && (
              <div className="panel">
                <Viewer3D
                  geometry={geometry}
                  label={source === "roi" ? "ROI Selection" : "Original Cloud"}
                  roi={roiDraft}
                  showRoiBox={showRoiBox && source === "original"}
                  showBoundingBox={showBoundingBox}
                  showAxes={showAxes}
                  onPointClick={handlePointClick}
                  height={520}
                />
              </div>
            )}

            {activeTab === "parallel" && <ParallelViewers experimentId={experiment.id} source={source} />}

            {activeTab === "pipeline" && (
              <>
                <PipelineBuilder experimentId={experiment.id} source={source} onResult={setPipelineResultId} />
                <BeforeAfterViewer experimentId={experiment.id} source={source} resultId={pipelineResultId} />
              </>
            )}

            {activeTab === "results" && (
              <>
                <ResultsTable />
                <Leaderboard />
                <DiffViewer />
              </>
            )}
          </main>

          <aside className="sidebar-right">
            <CloudInfoPanel info={experiment.cloud_info} />
            <PointInspector point={pickedPoint} />
            <GroundTruthPanel experiment={experiment} onUpdated={setExperiment} />
            {activeTab === "viewer" && (
              <>
                <ROIPanel experiment={experiment} cloudInfo={experiment.cloud_info} onUpdated={setExperiment} />
                <SlopePanel experimentId={experiment.id} source={source} baseline={baseline} />
              </>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
