/**
 * QualityPanel — data-quality checks on a loaded model.
 *
 * Runs the /api/v1/quality checks (duplicate GlobalIds, proxies, generic
 * names, missing materials/storeys/psets, unhosted openings) and lists
 * the findings; clicking a finding selects the element in 3D.
 */

import { useCallback, useMemo, useState } from "react";

import { useStore } from "../../store";
import { getModelBytes } from "../../engine/modelCache";
import { runQualityChecks, type QualityReport } from "../../api/toolsApi";

import "./QualityPanel.css";

const SEVERITY_LABEL: Record<string, string> = {
  error: "Fout",
  warning: "Waarschuwing",
  info: "Info",
};

export function QualityPanel() {
  const project = useStore((s) => s.project);
  const selectElement = useStore((s) => s.selectElement);

  const loadedModels = useMemo(
    () => project?.models.filter((m) => m.loadState === "loaded") ?? [],
    [project]
  );

  const [model, setModel] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<QualityReport | null>(null);
  const [openCheck, setOpenCheck] = useState<string | null>(null);

  const effectiveModel = model || loadedModels[0]?.fileName || "";

  const handleRun = useCallback(async () => {
    if (!effectiveModel) return;
    setRunning(true);
    setError(null);
    setReport(null);
    try {
      const bytes = await getModelBytes(effectiveModel);
      if (!bytes) throw new Error(`Geen bytes voor ${effectiveModel}`);
      setReport(await runQualityChecks(bytes, effectiveModel));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Kwaliteitscontrole mislukt"
      );
    } finally {
      setRunning(false);
    }
  }, [effectiveModel]);

  if (loadedModels.length === 0) {
    return (
      <div className="empty-state">
        <p className="empty-state__text">
          Upload eerst een IFC model voor kwaliteitscontroles
        </p>
      </div>
    );
  }

  return (
    <div className="quality-panel">
      <div className="quality-panel__config">
        <h3 className="quality-panel__heading">DATA-KWALITEIT</h3>

        {loadedModels.length > 1 && (
          <label className="quality-panel__label">
            Model
            <select
              className="quality-panel__select"
              value={effectiveModel}
              onChange={(e) => setModel(e.target.value)}
            >
              {loadedModels.map((m) => (
                <option key={m.id} value={m.fileName}>
                  {m.fileName}
                </option>
              ))}
            </select>
          </label>
        )}

        <button
          type="button"
          className="quality-panel__btn quality-panel__btn--primary"
          onClick={handleRun}
          disabled={running || !effectiveModel}
        >
          {running ? "Bezig met controleren…" : "Controleer kwaliteit"}
        </button>

        {error && <p className="quality-panel__error">{error}</p>}
      </div>

      {report && (
        <div className="quality-panel__results">
          <p className="quality-panel__summary">
            {report.error_count} fout(en), {report.warning_count}{" "}
            waarschuwing(en)
          </p>

          <ul className="quality-panel__list">
            {report.checks.map((check) => (
              <li key={check.id} className="quality-panel__check">
                <button
                  type="button"
                  className={`quality-panel__check-header quality-panel__check-header--${
                    check.passed ? "pass" : check.severity
                  }`}
                  onClick={() =>
                    setOpenCheck(openCheck === check.id ? null : check.id)
                  }
                >
                  <span className="quality-panel__check-status">
                    {check.passed ? "✓" : "✗"}
                  </span>
                  <span className="quality-panel__check-title">
                    {check.title}
                  </span>
                  <span className="quality-panel__check-count">
                    {check.passed
                      ? "OK"
                      : `${check.finding_count} × ${
                          SEVERITY_LABEL[check.severity]
                        }`}
                  </span>
                </button>

                {openCheck === check.id && check.findings.length > 0 && (
                  <ul className="quality-panel__findings">
                    {check.findings.map((finding, i) => (
                      <li key={`${finding.global_id ?? "x"}-${i}`}>
                        {finding.global_id ? (
                          <button
                            type="button"
                            className="quality-panel__finding-link"
                            onClick={() =>
                              selectElement(finding.global_id, true)
                            }
                          >
                            {finding.entity_type}:{" "}
                            {finding.entity_name || finding.global_id}
                          </button>
                        ) : (
                          <span>
                            {finding.entity_type}: {finding.message}
                          </span>
                        )}
                      </li>
                    ))}
                    {check.findings_omitted > 0 && (
                      <li className="quality-panel__omitted">
                        … en {check.findings_omitted} meer
                      </li>
                    )}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
