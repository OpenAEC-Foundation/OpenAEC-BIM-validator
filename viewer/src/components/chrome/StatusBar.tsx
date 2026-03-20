import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../../store";
import "./StatusBar.css";

export default function StatusBar() {
  const { t } = useTranslation();
  const project = useStore((s) => s.project);
  const bcfIssues = useStore((s) => s.bcfIssues);
  const [online, setOnline] = useState(navigator.onLine);

  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  const modelCount = project?.models.length ?? 0;
  const issueCount = bcfIssues?.length ?? 0;

  return (
    <div className="status-bar">
      <div className="status-bar-left">
        <div className="status-item">
          <span className="status-item-label">{t("ready")}</span>
        </div>
        <div className="status-separator" />
        <div className="status-item">
          <span className="status-item-label">{t("statusModels")}:</span>
          <span className="status-item-value">{modelCount}</span>
        </div>
        <div className="status-separator" />
        <div className="status-item">
          <span className="status-item-label">{t("statusElements")}:</span>
          <span className="status-item-value">&mdash;</span>
        </div>
        <div className="status-separator" />
        <div className="status-item">
          <span className="status-item-label">{t("statusIssues")}:</span>
          <span className="status-item-value">{issueCount}</span>
        </div>
      </div>

      <div className="status-bar-center" />

      <div className="status-bar-right">
        <div className="status-item">
          <span
            className={`status-connection-dot ${online ? "online" : "offline"}`}
          />
          <span className="status-item-label">
            {online ? t("statusOnline") : t("statusOffline")}
          </span>
        </div>
      </div>
    </div>
  );
}
