/**
 * RightPanel — tabbed panel for validation, clashes, BCF.
 *
 * Properties panel is now in the left panel.
 */

import { useStore } from "../../store";
import type { RightPanelTab } from "../../types/project";
import { ValidationPanel } from "../validation/ValidationPanel";
import { ClashPanel } from "../clash/ClashPanel";
import { QualityPanel } from "../quality/QualityPanel";
import { BcfPanel } from "../bcf/BcfPanel";

/** Tab configuration */
const TABS: { id: RightPanelTab; label: string }[] = [
  { id: "validation", label: "Validatie" },
  { id: "clashes", label: "Clashes" },
  { id: "quality", label: "Kwaliteit" },
  { id: "bcf", label: "BCF" },
];

export function RightPanel() {
  const activeTab = useStore((s) => s.activeRightTab);
  const setActiveTab = useStore((s) => s.setActiveRightTab);
  const bcfIssueCount = useStore((s) => s.bcfIssues.length);

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
            {tab.id === "bcf" && bcfIssueCount > 0 && (
              <span className="tab-bar__badge">{bcfIssueCount}</span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="panel__content">
        {activeTab === "validation" && <ValidationPanel />}

        {activeTab === "clashes" && <ClashPanel />}

        {activeTab === "quality" && <QualityPanel />}

        {activeTab === "bcf" && <BcfPanel />}
      </div>
    </div>
  );
}
