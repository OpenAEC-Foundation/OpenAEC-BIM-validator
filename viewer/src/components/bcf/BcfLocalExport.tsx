/**
 * BcfLocalExport — BCF ZIP download section.
 */

import { useState } from "react";
import { useStore } from "../../store";

export function BcfLocalExport() {
  const issues = useStore((s) => s.bcfIssues);
  const downloadZip = useStore((s) => s.bcfDownloadZip);
  const [downloading, setDownloading] = useState(false);

  const queuedCount = issues.filter((i) => i.pushState === "queued" || i.pushState === "failed").length;

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await downloadZip();
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="bcf-panel__section">
      <h4 className="bcf-panel__heading">Lokale export</h4>
      <button
        type="button"
        className="bcf-panel__btn bcf-panel__btn--primary"
        disabled={queuedCount === 0 || downloading}
        onClick={handleDownload}
        style={{ width: "100%" }}
      >
        {downloading ? (
          <span style={{ display: "flex", alignItems: "center", gap: "6px", justifyContent: "center" }}>
            <span className="bcf-panel__spinner" />
            Genereren...
          </span>
        ) : (
          `Download als BCF ZIP (${queuedCount} issues)`
        )}
      </button>
    </div>
  );
}
