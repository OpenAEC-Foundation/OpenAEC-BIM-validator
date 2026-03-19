/**
 * RightPanel — tabbed panel for validation, clashes, BCF.
 *
 * Properties panel is now in the left panel.
 */

import { useStore } from "../../store";
import type { RightPanelTab } from "../../types/project";
import { ValidationPanel } from "../validation/ValidationPanel";

/** Tab configuration */
const TABS: { id: RightPanelTab; label: string }[] = [
  { id: "validation", label: "Validatie" },
  { id: "clashes", label: "Clashes" },
  { id: "bcf", label: "BCF" },
];

export function RightPanel() {
  const activeTab = useStore((s) => s.activeRightTab);
  const setActiveTab = useStore((s) => s.setActiveRightTab);

  return (
    <div className="panel">
      {/* Tab bar */}
      <div className="tab-bar">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`tab-bar__tab ${
              activeTab === tab.id ? "tab-bar__tab--active" : ""
            }`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="panel__content">
        {activeTab === "validation" && <ValidationPanel />}

        {activeTab === "clashes" && (
          <div className="empty-state">
            <p className="empty-state__text">
              Clash detection — binnenkort beschikbaar
            </p>
          </div>
        )}

        {activeTab === "bcf" && (
          <div className="empty-state">
            <p className="empty-state__text">
              BCF export — binnenkort beschikbaar
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
