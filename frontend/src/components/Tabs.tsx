import type { Tab } from "../state/appStore";

const TABS: { key: Tab; label: string }[] = [
  { key: "viewer", label: "Viewer" },
  { key: "parallel", label: "Parallel Compare" },
  { key: "pipeline", label: "Pipeline" },
  { key: "results", label: "Results" },
];

export default function Tabs({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  return (
    <div className="tabs">
      {TABS.map((t) => (
        <button key={t.key} className={`tab-btn ${active === t.key ? "active" : ""}`} onClick={() => onChange(t.key)}>
          {t.label}
        </button>
      ))}
    </div>
  );
}
