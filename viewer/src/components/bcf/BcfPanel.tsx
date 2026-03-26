/**
 * BcfPanel — BCF issue management panel.
 *
 * Two sections:
 * 1. Issue Queue — local list of BCF issues with thumbnails + expandable detail
 * 2. Local Export — download as BCF ZIP
 *
 * Platform auth/push has moved to Backstage + Ribbon.
 */

import { useStore } from "../../store";
import { BcfIssueQueue } from "./BcfIssueQueue";
import { BcfLocalExport } from "./BcfLocalExport";
import "./BcfPanel.css";

export function BcfPanel() {
  const issues = useStore((s) => s.bcfIssues);

  return (
    <div className="bcf-panel">
      {/* Section 1: Issue Queue */}
      <BcfIssueQueue />

      {/* Section 2: Local Export (only if issues exist) */}
      {issues.length > 0 && (
        <>
          <div className="bcf-panel__divider" />
          <BcfLocalExport />
        </>
      )}
    </div>
  );
}
