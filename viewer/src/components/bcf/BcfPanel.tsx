/**
 * BcfPanel — BCF issue management panel.
 *
 * Three sections:
 * 1. Issue Queue — local list of BCF issues
 * 2. Local Export — download as BCF ZIP
 * 3. Platform — auth + project selection + push
 */

import { useEffect } from "react";
import { useStore } from "../../store";
import { BcfIssueQueue } from "./BcfIssueQueue";
import { BcfLocalExport } from "./BcfLocalExport";
import { BcfPlatformSection } from "./BcfPlatformSection";
import "./BcfPanel.css";

export function BcfPanel() {
  const bcfInitAuth = useStore((s) => s.bcfInitAuth);
  const issues = useStore((s) => s.bcfIssues);

  // Initialize auth on first mount (restore OIDC session or API key)
  useEffect(() => {
    void bcfInitAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

      {/* Section 3: Platform Push */}
      <div className="bcf-panel__divider" />
      <BcfPlatformSection />
    </div>
  );
}
