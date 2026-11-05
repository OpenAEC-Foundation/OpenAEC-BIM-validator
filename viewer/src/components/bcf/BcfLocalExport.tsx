import { Banner, Button as OaButton } from "@openaec/ui-react";
/**
 * BcfLocalExport — BCF ZIP download section.
 */

import { useTranslation } from "react-i18next";
import { useState } from "react";
import { useStore } from "../../store";

export function BcfLocalExport() {
  const { t } = useTranslation("bcf");
  const issues = useStore((s) => s.bcfIssues);
  const downloadZip = useStore((s) => s.bcfDownloadZip);
  const [downloading, setDownloading] = useState(false);

  const issueCount = issues.length;
  const error = useStore(s => s.bcfError);

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
      <h4 className="bcf-panel__heading">{t("localExport")}</h4>
      <OaButton kind="primary"
        type="button"
        className="bcf-panel__btn bcf-panel__btn--primary"
        disabled={issueCount === 0 || downloading}
        onClick={handleDownload}
        style={{ width: "100%" }}
      >
        {downloading ? (
          <span style={{ display: "flex", alignItems: "center", gap: "6px", justifyContent: "center" }}>
            <span className="bcf-panel__spinner" />
            {t("downloading")}
          </span>
        ) : (
          t("download", { count: issueCount })
        )}
      </OaButton>
      {error && <Banner tone="error" word={t("error")}>{error}</Banner>}
    </div>
  );
}
