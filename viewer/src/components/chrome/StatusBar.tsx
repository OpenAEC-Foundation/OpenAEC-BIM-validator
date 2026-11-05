import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../../store";
import { StatusBar as BlueprintStatusBar } from "@openaec/ui-react";

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

  return <BlueprintStatusBar message={t("ready")} items={[
    `${t("statusModels")}: ${modelCount}`,
    `${t("statusIssues")}: ${issueCount}`,
    online ? t("statusOnline") : t("statusOffline"),
  ]} />;
}
