import { useRef, useState } from "react";
import { api } from "../api/client";
import { useAppStore } from "../state/appStore";

/** Top bar: experiment identity, upload, and destructive/reset actions. */
export default function TopBar() {
  const experiment = useAppStore((s) => s.experiment);
  const setExperiment = useAppStore((s) => s.setExperiment);
  const setResults = useAppStore((s) => s.setResults);
  const resetStore = useAppStore((s) => s.reset);
  const [nameDraft, setNameDraft] = useState("Ramp Test 001");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChosen = async (file: File) => {
    setBusy(true);
    setError(null);
    try {
      let exp = experiment;
      if (!exp) {
        exp = await api.createExperiment(nameDraft || "Untitled Experiment");
      }
      const updated = await api.uploadPointCloud(exp.id, file);
      setExperiment(updated);
      setResults([]);
    } catch (e: any) {
      setError(e.message ?? "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  const handleReset = async () => {
    if (!experiment) return;
    setBusy(true);
    try {
      const exp = await api.resetExperiment(experiment.id);
      setExperiment(exp);
      setResults([]);
    } finally {
      setBusy(false);
    }
  };

  const handleNewExperiment = () => {
    resetStore();
  };

  return (
    <div className="topbar">
      <div className="topbar-left">
        <span className="brand">Ramp Point Cloud Analysis</span>
        {experiment ? (
          <span className="exp-name">{experiment.name}</span>
        ) : (
          <input
            className="exp-name-input"
            value={nameDraft}
            onChange={(e) => setNameDraft(e.target.value)}
            placeholder="Experiment name"
          />
        )}
      </div>
      <div className="topbar-right">
        {error && <span className="error-text">{error}</span>}
        <input
          ref={fileInputRef}
          type="file"
          accept=".ply,.pcd"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFileChosen(f);
            e.target.value = "";
          }}
        />
        <button disabled={busy} onClick={() => fileInputRef.current?.click()}>
          {experiment ? "Upload New Cloud" : "Upload Ramp (.ply/.pcd)"}
        </button>
        <button disabled={busy || !experiment} onClick={handleReset}>
          Reset Results
        </button>
        <button disabled={busy || !experiment} onClick={handleNewExperiment}>
          New Experiment
        </button>
      </div>
    </div>
  );
}
