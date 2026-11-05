import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button, Banner } from "@openaec/ui-react";
import { importBcfArchive } from "../../lib/bcfArchive";
import { useStore } from "../../store";
import { BcfIssueQueue } from "./BcfIssueQueue";
import { BcfLocalExport } from "./BcfLocalExport";
import "./BcfPanel.css";

export function BcfPanel() {
  const { t } = useTranslation("bcf");
  const issues = useStore(s => s.bcfIssues);
  const fileInput = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ count: number; skipped: number } | null>(null);
  const [error, setError] = useState("");
  const openFile = async (file: File) => {
    setBusy(true); setError(""); setResult(null);
    try {
      if (file.size > 50 * 1024 * 1024) throw new Error(t("tooLarge"));
      const imported = await importBcfArchive(await file.arrayBuffer());
      const added = useStore.getState().bcfImportIssues(imported);
      setResult({ count: added, skipped: imported.length - added });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("failed"));
    } finally { setBusy(false); }
  };
  return <div className="bcf-panel">
    <div className="bcf-import">
      <Button icon="file.import" disabled={busy} onClick={() => fileInput.current?.click()}>{t(busy ? "opening" : "import")}</Button>
      <input ref={fileInput} type="file" accept=".bcf,.bcfzip" hidden aria-label={t("file")}
        onChange={event => { const file = event.target.files?.[0]; event.target.value = ""; if (file) void openFile(file); }} />
      {result && <Banner tone="success" word={t("success")}>{t("imported", result)}</Banner>}
      {error && <Banner tone="error" word={t("error")}>{error}</Banner>}
    </div>
    <BcfIssueQueue />
    {issues.length > 0 && <><div className="bcf-panel__divider" /><BcfLocalExport /></>}
  </div>;
}
